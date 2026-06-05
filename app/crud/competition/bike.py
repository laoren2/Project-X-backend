from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_, exists, case, tuple_, desc, asc, literal
from geoalchemy2.functions import ST_Distance, ST_SetSRID, ST_MakePoint
from geoalchemy2 import Geography
from app.schemas.training.common import RouteSortType
from app.db.models.competition import (
    BikeCareerStatisticData, Region, BikeEvent, BikeSeason, 
    BikeTrack, BikeRaceRecord, BikeTeam, BikeTeamMember, BikeTeamAppliedMember,
    CardBonusInBikeRecord, BikeLeaderboard, BikeCareerScore, BikeDailyTask,
    BikeDailyTaskRecord, BikeBonusByTeamMember
)
from app.db.models.user import UserSubscription, User
from app.db.models.asset import EquipmentCardDef, UserEquipmentCard
from app.schemas.competition.common import RecordStatus, TeamStatus, DailyTaskType, EventType
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import date, timedelta, datetime
from sqlalchemy.dialects.postgresql import insert
from app.schemas.user import Gender
from app.core.tools import get_today_hk_date, get_user_local_date
import uuid



async def create_season_crud(db: AsyncSession, season: BikeSeason) -> BikeSeason:
    db.add(season)
    await db.flush()
    await db.refresh(season)
    return season


async def update_season_crud(db: AsyncSession, season: BikeSeason, update_data: dict):
    for field, value in update_data.items():
        setattr(season, field, value)
    db.add(season)
    await db.flush()
    await db.refresh(season)


async def get_season_now(db: AsyncSession) -> BikeSeason | None:
    current_time = func.now()
    stmt = select(BikeSeason).where(
        and_(
            BikeSeason.start_date <= current_time,
            BikeSeason.end_date >= current_time
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def get_history_seasons(db: AsyncSession) -> List[BikeSeason]:
    result = await db.execute(
        select(BikeSeason).where(
            BikeSeason.start_date < func.now()
        )
        .order_by(BikeSeason.start_date.desc())
    )
    return result.scalars().all()

async def get_season_by_date(db: AsyncSession, start: datetime, end: datetime) -> BikeSeason | None:
    result = await db.execute(
        select(BikeSeason).where(
            BikeSeason.end_date > start,
            BikeSeason.start_date < end
        )
    )
    return result.scalar_one_or_none()

async def get_season_by_name(db: AsyncSession, zh_name: str) -> BikeSeason | None:
    result = await db.execute(
        select(BikeSeason).where(
            BikeSeason.name_i18n["zh-Hans"].astext == zh_name
        )
    )
    return result.scalar_one_or_none()

async def get_season_by_season_id(db: AsyncSession, season_id: str) -> BikeSeason | None:
    result = await db.execute(
        select(BikeSeason)
        .where(BikeSeason.season_id == season_id)
        .options(
            selectinload(BikeSeason.bike_events)
                .selectinload(BikeEvent.region),
            selectinload(BikeSeason.bike_events)
                .selectinload(BikeEvent.tracks)
        )
    )
    return result.scalar_one_or_none()


async def get_active_events_by_season_id(db: AsyncSession, season_id: uuid.UUID) -> List[BikeEvent]:
    result = await db.execute(
        select(BikeEvent)
        .options(
            selectinload(BikeEvent.tracks),
            selectinload(BikeEvent.region)
        )
        .where(
            BikeEvent.season_id == season_id,
            BikeEvent.start_date < func.now(),
            BikeEvent.end_date > func.now()
        )
    )
    return result.scalars().all()


async def get_event_by_event_id(db: AsyncSession, event_id: str) -> BikeEvent | None:
    result = await db.execute(
        select(BikeEvent)
        .options(
            selectinload(BikeEvent.season)
        )
        .where(BikeEvent.event_id == event_id)
    )
    return result.scalar_one_or_none()


async def get_event_by_name(db: AsyncSession, zh_name: str) -> BikeEvent | None:
    result = await db.execute(select(BikeEvent).where(BikeEvent.name_i18n["zh-Hans"] == zh_name))
    return result.scalar_one_or_none()


async def get_event_by_season_id_and_region_id(db: AsyncSession, season_id: uuid.UUID, region_id: uuid.UUID) -> List[BikeEvent]:
    result = await db.execute(
        select(BikeEvent).where(
            and_(
                BikeEvent.season_id == season_id,
                BikeEvent.region_id == region_id,
                BikeEvent.start_date <= func.now() + timedelta(days=3),
                BikeEvent.end_date >= func.now()
            )
        )
    )
    return result.scalars().all()

async def get_community_event(db: AsyncSession, season_id: uuid.UUID, region_id: uuid.UUID) -> BikeEvent | None:
    """取某 season+region 下承载热门路线转赛道的 community 赛事（唯一）。"""
    result = await db.execute(
        select(BikeEvent)
        .options(selectinload(BikeEvent.region), selectinload(BikeEvent.season))
        .where(
            BikeEvent.season_id == season_id,
            BikeEvent.region_id == region_id,
            BikeEvent.event_type == EventType.community,
            BikeEvent.start_date <= func.now(),
            BikeEvent.end_date >= func.now()
        )
    )
    return result.scalar_one_or_none()


async def create_event_crud(db: AsyncSession, event: BikeEvent) -> BikeEvent:
    db.add(event)
    await db.flush()
    await db.refresh(event)
    # 显式加载 region 和 season
    result = await db.execute(
        select(BikeEvent)
        .options(selectinload(BikeEvent.region), selectinload(BikeEvent.season))
        .where(BikeEvent.id == event.id)
    )
    return result.scalar_one()


async def update_event_crud(db: AsyncSession, event: BikeEvent, update_data: dict):
    for field, value in update_data.items():
        setattr(event, field, value)
    db.add(event)
    await db.flush()
    await db.refresh(event)


async def query_events_crud(
    db: AsyncSession,
    season_name: Optional[str],
    region_name: Optional[str],
    event_name: Optional[str],
    page: int,
    size: int
) -> List[BikeEvent]:
    stmt = select(BikeEvent).options(
        selectinload(BikeEvent.region),
        selectinload(BikeEvent.season)
    ).join(BikeEvent.region).join(BikeEvent.season)

    if season_name:
        stmt = stmt.filter(func.lower(BikeSeason.name_i18n["zh-Hans"]).contains(season_name.lower()))
    if event_name:
        stmt = stmt.filter(func.lower(BikeEvent.name_i18n["zh-Hans"]).contains(event_name.lower()))

    stmt = stmt.order_by(BikeEvent.created_at.asc()).offset((page - 1) * size).limit(size)

    result = await db.execute(stmt)
    return result.scalars().all()


async def get_track_by_track_id(db: AsyncSession, track_id: str) -> BikeTrack | None:
    result = await db.execute(
        select(BikeTrack)
        .where(BikeTrack.track_id == track_id)
        .options(
            selectinload(BikeTrack.event).selectinload(BikeEvent.season),
            selectinload(BikeTrack.event).selectinload(BikeEvent.region),
            selectinload(BikeTrack.single_register_card_def),
            selectinload(BikeTrack.team_register_card_def)
        )
    )
    return result.scalar_one_or_none()

async def get_tracks_by_track_ids(db: AsyncSession, track_ids: List[str]) -> List[BikeTrack]:
    """批量按 track_id 取赛道，供列表态信息一次性填充，避免逐条查询。"""
    if not track_ids:
        return []
    result = await db.execute(
        select(BikeTrack)
        .where(BikeTrack.track_id.in_(track_ids))
        .options(
            selectinload(BikeTrack.event).selectinload(BikeEvent.season),
            selectinload(BikeTrack.event).selectinload(BikeEvent.region),
            selectinload(BikeTrack.single_register_card_def),
            selectinload(BikeTrack.team_register_card_def)
        )
    )
    return list(result.scalars().all())

async def get_track_by_track_id_for_update(db: AsyncSession, track_id: str) -> BikeTrack | None:
    result = await db.execute(
        select(BikeTrack)
        .where(BikeTrack.track_id == track_id)
        .options(
            selectinload(BikeTrack.event).selectinload(BikeEvent.season),
            selectinload(BikeTrack.single_register_card_def),
            selectinload(BikeTrack.team_register_card_def)
        )
        .with_for_update()
    )
    return result.scalar_one_or_none()


async def get_track_by_name(db: AsyncSession, name: str) -> BikeTrack | None:
    result = await db.execute(select(BikeTrack).where(BikeTrack.name == name))
    return result.scalar_one_or_none()


async def get_track_by_event_id(db: AsyncSession, event_id: uuid.UUID) -> List[BikeTrack]:
    result = await db.execute(
        select(BikeTrack)
        .where(
            BikeTrack.event_id == event_id,
            BikeTrack.start_date <= func.now() + timedelta(days=3),
            BikeTrack.end_date >= func.now()
        )
        .options(
            selectinload(BikeTrack.single_register_card_def),
            selectinload(BikeTrack.team_register_card_def)
        )
        .order_by(BikeTrack.start_date.desc())
    )
    return result.scalars().all()


async def get_tracks_by_event_page_crud(
    db: AsyncSession,
    event_id: uuid.UUID,
    sort_type: RouteSortType,
    lat: float | None,
    lng: float | None,
    limit: int,
    cursor: dict | None
):
    base_where = [
        BikeTrack.event_id == event_id,
        BikeTrack.start_date <= func.now() + timedelta(days=3),
        BikeTrack.end_date >= func.now()
    ]
    options = [
        selectinload(BikeTrack.single_register_card_def),
        selectinload(BikeTrack.team_register_card_def)
    ]
    # 参与人数（热度）= 该赛道的报名/比赛记录数
    subq = (
        select(BikeRaceRecord.track_id, func.count().label("count"))
        .group_by(BikeRaceRecord.track_id)
        .subquery()
    )

    if sort_type == "participation":
        distance_expr = None
        if lat is not None and lng is not None:
            point = ST_SetSRID(ST_MakePoint(lng, lat), 4326)
            distance_expr = ST_Distance(BikeTrack.start_point.cast(Geography), point.cast(Geography))
        query = (
            select(
                BikeTrack,
                func.coalesce(subq.c.count, 0).label("count"),
                (distance_expr if distance_expr is not None else literal(None)).label("user_distance")
            )
            .outerjoin(subq, BikeTrack.id == subq.c.track_id)
            .where(*base_where).options(*options)
        )
        if cursor:
            count_expr = func.coalesce(subq.c.count, 0)
            query = query.where(
                (count_expr < cursor["count"]) |
                ((count_expr == cursor["count"]) & (BikeTrack.created_at > cursor["created_at"])) |
                ((count_expr == cursor["count"]) & (BikeTrack.created_at == cursor["created_at"]) & (BikeTrack.id > cursor["track_id"]))
            )
        query = query.order_by(desc("count"), asc(BikeTrack.created_at), asc(BikeTrack.id)).limit(limit)
    else:
        # distance 排序：冻结 cursor 中的 lat/lng 保证分页稳定
        if cursor and "lat" in cursor and "lng" in cursor:
            lat = cursor["lat"]
            lng = cursor["lng"]
        point = ST_SetSRID(ST_MakePoint(lng, lat), 4326)
        distance_expr = ST_Distance(BikeTrack.start_point.cast(Geography), point.cast(Geography))
        query = (
            select(
                BikeTrack,
                func.coalesce(subq.c.count, 0).label("count"),
                distance_expr.label("user_distance")
            )
            .outerjoin(subq, BikeTrack.id == subq.c.track_id)
            .where(*base_where).options(*options)
        )
        if cursor:
            query = query.where(
                (distance_expr > cursor["distance"]) |
                ((distance_expr == cursor["distance"]) & (BikeTrack.id > cursor["track_id"]))
            )
        query = query.order_by(asc("user_distance"), asc(BikeTrack.id)).limit(limit)

    result = await db.execute(query)
    return result.mappings().all()


async def create_track_crud(db: AsyncSession, track: BikeTrack) -> BikeTrack:
    db.add(track)
    await db.flush()
    await db.refresh(track)
    # 显式加载 region 和 season
    result = await db.execute(
        select(BikeTrack)
        .options(
            selectinload(BikeTrack.event).selectinload(BikeEvent.region),
            selectinload(BikeTrack.event).selectinload(BikeEvent.season)
        )
        .where(BikeTrack.id == track.id)
    )
    return result.scalar_one()


async def update_track_crud(db: AsyncSession, track: BikeTrack, update_data: dict):
    for field, value in update_data.items():
        setattr(track, field, value)
    db.add(track)
    await db.flush()
    await db.refresh(track)


async def query_tracks_crud(
    db: AsyncSession,
    track_name: Optional[str],
    event_name: Optional[str],
    season_name: Optional[str],
    region_name: Optional[str],
    page: int,
    size: int
):
    # EXISTS 子查询：判断某 track_id 是否在 BikeLeaderboard 里存在
    is_settled_subq = (
        exists().where(BikeLeaderboard.track_id == BikeTrack.id)
        .correlate(BikeTrack)
        .select()
        .label("is_settled")
    )

    stmt = (
        select(BikeTrack, is_settled_subq)
        .options(
            selectinload(BikeTrack.event).selectinload(BikeEvent.season),
            selectinload(BikeTrack.event).selectinload(BikeEvent.region)
        )
        .join(BikeTrack.event)
        .join(BikeEvent.season)
        .join(BikeEvent.region)
    )

    if event_name:
        stmt = stmt.filter(func.lower(BikeEvent.name_i18n["zh-Hans"]).contains(event_name.lower()))
    if season_name:
        stmt = stmt.filter(func.lower(BikeSeason.name_i18n["zh-Hans"]).contains(season_name.lower()))
    if track_name:
        stmt = stmt.filter(func.lower(BikeTrack.name_i18n["zh-Hans"]).contains(track_name.lower()))

    stmt = stmt.order_by(BikeTrack.created_at.asc()).offset((page - 1) * size).limit(size)

    result = await db.execute(stmt)
    rows = result.all()
    return [(track, is_settled) for track, is_settled in rows]

async def track_has_settled(db: AsyncSession, track_id: uuid.UUID) -> bool:
    stmt = select(
        exists().where(BikeLeaderboard.track_id == track_id)
    )
    result = await db.execute(stmt)
    return result.scalar()

async def create_record_crud(db: AsyncSession, record: BikeRaceRecord):
    db.add(record)
    await db.flush()
    await db.refresh(record)
    result = await db.execute(
        select(BikeRaceRecord)
        .options(
            selectinload(BikeRaceRecord.track).selectinload(BikeTrack.event).selectinload(BikeEvent.region),
            selectinload(BikeRaceRecord.team)
        )
        .where(BikeRaceRecord.id == record.id)
    )
    return result.scalar_one()

async def get_incompleted_records_by_user_id(
    db: AsyncSession, 
    user_id: uuid.UUID,
    page: int,
    size: int
) -> List[BikeRaceRecord]:
    stmt = (
        select(BikeRaceRecord)
        .where(BikeRaceRecord.user_id == user_id, BikeRaceRecord.status == RecordStatus.notStarted)
        .options(
            selectinload(BikeRaceRecord.track).selectinload(BikeTrack.event).selectinload(BikeEvent.region),
            selectinload(BikeRaceRecord.team)
        )
        .order_by(BikeRaceRecord.created_at.desc()).offset((page - 1) * size).limit(size)
    )
    result = await db.execute(stmt)
    return result.scalars().all()

async def get_completed_records_by_user_id(
    db: AsyncSession, 
    user_id: uuid.UUID,
    page: int,
    size: int
) -> List[BikeRaceRecord]:
    stmt = (
        select(BikeRaceRecord)
        .where(
            BikeRaceRecord.user_id == user_id, 
            BikeRaceRecord.status.in_([RecordStatus.completed, RecordStatus.expired, RecordStatus.toBeVerified, RecordStatus.invalid])
        )
        .options(
            selectinload(BikeRaceRecord.track).selectinload(BikeTrack.event).selectinload(BikeEvent.region),
            selectinload(BikeRaceRecord.team)
        )
        .order_by(BikeRaceRecord.created_at.desc()).offset((page - 1) * size).limit(size)
    )
    result = await db.execute(stmt)
    return result.scalars().all()

async def get_unverified_records(
    db: AsyncSession,
    page: int,
    size: int
) -> List[BikeRaceRecord]:
    subscription_priority = case(
        (UserSubscription.is_active == True, 1),
        else_=0
    )
    stmt = (
        select(BikeRaceRecord)
        .outerjoin(UserSubscription, UserSubscription.user_id == BikeRaceRecord.user_id)
        .where(
            BikeRaceRecord.status == RecordStatus.toBeVerified,
            BikeRaceRecord.end_time.is_not(None)
        )
        .options(
            selectinload(BikeRaceRecord.user).selectinload(User.subscription_info),
            selectinload(BikeRaceRecord.path)
        )
        .order_by(
            subscription_priority.desc(),
            BikeRaceRecord.end_time.desc()
        )
        .offset((page - 1) * size)
        .limit(size)
    )
    result = await db.execute(stmt)
    return result.scalars().all()

async def get_record_by_record_id(db: AsyncSession, record_id: str) -> BikeRaceRecord | None:
    record = await db.execute(
        select(BikeRaceRecord)
        .where(BikeRaceRecord.record_id == record_id)
        .options(
            selectinload(BikeRaceRecord.track)
                .selectinload(BikeTrack.single_register_card_def),
            selectinload(BikeRaceRecord.track)
                .selectinload(BikeTrack.team_register_card_def),
            selectinload(BikeRaceRecord.track)
                .selectinload(BikeTrack.event)
                .selectinload(BikeEvent.region),
            selectinload(BikeRaceRecord.user),
            selectinload(BikeRaceRecord.team)
                .selectinload(BikeTeam.members),
            selectinload(BikeRaceRecord.path),
            selectinload(BikeRaceRecord.card_bonus)
                .selectinload(CardBonusInBikeRecord.card)
                .selectinload(UserEquipmentCard.equipment_def),
            selectinload(BikeRaceRecord.card_bonus)
                .selectinload(CardBonusInBikeRecord.card)
                .selectinload(UserEquipmentCard.user)
        )
    )
    return record.scalar_one_or_none()

async def get_record_by_record_id_for_update(db: AsyncSession, record_id: str) -> BikeRaceRecord | None:
    record = await db.execute(
        select(BikeRaceRecord)
        .where(BikeRaceRecord.record_id == record_id)
        .options(
            selectinload(BikeRaceRecord.track),
            selectinload(BikeRaceRecord.user),
            selectinload(BikeRaceRecord.team)
                .selectinload(BikeTeam.members),
            selectinload(BikeRaceRecord.path),
            selectinload(BikeRaceRecord.card_bonus)
                .selectinload(CardBonusInBikeRecord.card)
                .selectinload(UserEquipmentCard.equipment_def)
        )
        .with_for_update()
    )
    return record.scalar_one_or_none()

async def get_records_by_team_id(db: AsyncSession, team_id: uuid.UUID) -> List[BikeRaceRecord]:
    result = await db.execute(
        select(BikeRaceRecord)
        .where(BikeRaceRecord.team_id == team_id)
        .options(
            selectinload(BikeRaceRecord.user),
            selectinload(BikeRaceRecord.track)
        )
    )
    return result.scalars().all()

async def get_records_by_team_id_for_update(db: AsyncSession, team_id: uuid.UUID) -> List[BikeRaceRecord]:
    result = await db.execute(
        select(BikeRaceRecord)
        .where(BikeRaceRecord.team_id == team_id)
        .options(
            selectinload(BikeRaceRecord.track)
                .selectinload(BikeTrack.event),
            selectinload(BikeRaceRecord.user),
            selectinload(BikeRaceRecord.team)
                .selectinload(BikeTeam.members),
            selectinload(BikeRaceRecord.path),
            selectinload(BikeRaceRecord.card_bonus)
                .selectinload(CardBonusInBikeRecord.card)
                .selectinload(UserEquipmentCard.equipment_def)
        )
        .order_by(BikeRaceRecord.id)        # 保证上锁顺序防止死锁
        .with_for_update()
    )
    return result.scalars().all()

async def get_record_by_team_id_and_user_id(db: AsyncSession, team_id: uuid.UUID, user_id: uuid.UUID) -> BikeRaceRecord | None:
    record = await db.execute(
        select(BikeRaceRecord)
        .where(BikeRaceRecord.team_id == team_id, BikeRaceRecord.user_id == user_id)
    )
    return record.scalar_one_or_none()

async def delete_record_crud(db: AsyncSession, record: BikeRaceRecord):
    await db.delete(record)
    await db.flush()

async def delete_records_by_team_id(db: AsyncSession, team_id: uuid.UUID):
    stmt = select(BikeRaceRecord).where(BikeRaceRecord.team_id == team_id)
    result = await db.execute(stmt)
    records = result.scalars().all()
    for record in records:
        await db.delete(record)
    await db.flush()

async def update_record_crud(db: AsyncSession, record: BikeRaceRecord, update_data: dict):
    for field, value in update_data.items():
        setattr(record, field, value)
    db.add(record)
    await db.flush()


async def create_team_crud(db: AsyncSession, team: BikeTeam) -> tuple[str, uuid.UUID]:
    db.add(team)
    await db.flush()
    await db.refresh(team)
    return team.team_code, team.id

async def create_team_member_crud(db: AsyncSession, member: BikeTeamMember):
    db.add(member)
    await db.flush()

async def get_team_id_by_record_id(db: AsyncSession, record_id: str) -> uuid.UUID | None:
    result = await db.execute(
        select(BikeRaceRecord)
        .where(BikeRaceRecord.record_id == record_id)
    )
    record = result.scalar_one_or_none()
    return record.team_id if record else None

async def get_team_by_code(db: AsyncSession, team_code: str) -> BikeTeam | None:
    team = await db.execute(
        select(BikeTeam)
        .where(BikeTeam.team_code == team_code)
        .options(
            selectinload(BikeTeam.track),
            selectinload(BikeTeam.members)
        )
    )
    return team.scalar_one_or_none()
# 加行级锁
async def get_active_team_by_code_for_update(db: AsyncSession, team_code: str) -> BikeTeam | None:
    team = await db.execute(
        select(BikeTeam)
        .where(
            BikeTeam.team_code == team_code,
            BikeTeam.status != TeamStatus.completed
        )
        .with_for_update()
        .options(
            selectinload(BikeTeam.track)
                .selectinload(BikeTrack.team_register_card_def),
            selectinload(BikeTeam.members)
        )
    )
    return team.scalar_one_or_none()

async def get_team_by_team_id(db: AsyncSession, team_id: str) -> BikeTeam | None:
    team = await db.execute(
        select(BikeTeam)
        .where(BikeTeam.team_id == team_id)
        .options(
            selectinload(BikeTeam.track)
                .selectinload(BikeTrack.event)
                .selectinload(BikeEvent.region),
            selectinload(BikeTeam.members)
                .selectinload(BikeTeamMember.user),
            selectinload(BikeTeam.applied_members)
                .selectinload(BikeTeamAppliedMember.user)
        )
    )
    return team.scalar_one_or_none()
# 加行级锁
async def get_team_by_team_id_for_update(db: AsyncSession, team_id: str) -> BikeTeam | None:
    team = await db.execute(
        select(BikeTeam)
        .where(BikeTeam.team_id == team_id)
        .with_for_update()
        .options(
            selectinload(BikeTeam.track)
                .selectinload(BikeTrack.event)
                .selectinload(BikeEvent.region),
            selectinload(BikeTeam.track)
                .selectinload(BikeTrack.team_register_card_def),
            selectinload(BikeTeam.members)
                .selectinload(BikeTeamMember.user),
            selectinload(BikeTeam.applied_members)
                .selectinload(BikeTeamAppliedMember.user)
        )
    )
    return team.scalar_one_or_none()
# 加行级锁
async def get_team_by_id_for_update(db: AsyncSession, team_id: uuid.UUID) -> BikeTeam | None:
    team = await db.execute(
        select(BikeTeam)
        .where(BikeTeam.id == team_id)
        .with_for_update()
        .options(
            selectinload(BikeTeam.track)
                .selectinload(BikeTrack.event)
                .selectinload(BikeEvent.region),
            selectinload(BikeTeam.members)
                .selectinload(BikeTeamMember.user),
            selectinload(BikeTeam.applied_members)
                .selectinload(BikeTeamAppliedMember.user)
        )
    )
    return team.scalar_one_or_none()

async def get_public_teams_by_track_id(db: AsyncSession, track_id: uuid.UUID, page: int, size: int) -> List[BikeTeam]:
    result = await db.execute(
        select(BikeTeam)
        .where(
            BikeTeam.track_id == track_id,
            BikeTeam.is_public == True,
            BikeTeam.status == TeamStatus.prepared
        )
        .options(
            selectinload(BikeTeam.members)
                .selectinload(BikeTeamMember.user)
        )
        .order_by(BikeTeam.created_at.desc(), BikeTeam.id)
        .offset((page - 1) * size)
        .limit(size)
    )
    teams = result.scalars().all()
    filtered_teams = [
        team for team in teams if len(team.members) < team.members_count_max
    ]
    return filtered_teams

async def get_created_teams_by_user_id(db: AsyncSession, user_id: uuid.UUID, page: int, size: int) -> List[BikeTeam]:
    result = await db.execute(
        select(BikeTeam)
        .join(BikeTeam.members)
        .where(
            BikeTeamMember.user_id == user_id,
            BikeTeamMember.is_leader == True,
            BikeTeam.status != TeamStatus.completed
        )
        .options(
            selectinload(BikeTeam.members),
            selectinload(BikeTeam.track)
                .selectinload(BikeTrack.event)
                .selectinload(BikeEvent.region)
        )
        .order_by(BikeTeam.created_at.desc(), BikeTeam.id)
        .offset((page - 1) * size)
        .limit(size)
    )
    return result.scalars().all()

async def get_joined_teams_by_user_id(db: AsyncSession, user_id: uuid.UUID, page: int, size: int) -> List[BikeTeam]:
    result = await db.execute(
        select(BikeTeam)
        .join(BikeTeam.members)
        .where(
            BikeTeamMember.user_id == user_id,
            BikeTeamMember.is_leader == False,
            BikeTeam.status != TeamStatus.completed
        )
        .options(
            selectinload(BikeTeam.members),
            selectinload(BikeTeam.track)
                .selectinload(BikeTrack.event)
                .selectinload(BikeEvent.region)
        )
        .order_by(BikeTeamMember.created_at.desc(), BikeTeam.id)
        .offset((page - 1) * size)
        .limit(size)
    )
    return result.scalars().all()

async def get_applied_teams_by_user_id(db: AsyncSession, user_id: uuid.UUID, page: int, size: int) -> List[BikeTeam]:
    result = await db.execute(
        select(BikeTeam)
        .join(BikeTeam.applied_members)
        .where(
            BikeTeamAppliedMember.user_id == user_id,
            BikeTeam.status != TeamStatus.completed
        )
        .options(
            selectinload(BikeTeam.members),
            selectinload(BikeTeam.track)
                .selectinload(BikeTrack.event)
                .selectinload(BikeEvent.region)
        )
        .order_by(BikeTeamAppliedMember.created_at.desc(), BikeTeam.id)
        .offset((page - 1) * size)
        .limit(size)
    )
    return result.scalars().all()

async def update_team_crud(db: AsyncSession, team: BikeTeam, update_data: dict):
    for field, value in update_data.items():
        setattr(team, field, value)
    db.add(team)
    await db.flush()
    await db.refresh(team)

async def get_leaderboad_record(
    db: AsyncSession, 
    track_id: uuid.UUID,
    user_id: uuid.UUID
) -> BikeLeaderboard | None:
    result = await db.execute(
        select(BikeLeaderboard)
        .where(
            BikeLeaderboard.track_id == track_id,
            BikeLeaderboard.user_id == user_id
        )
        .options(
            selectinload(BikeLeaderboard.record)
        )
    )
    return result.scalar_one_or_none()

# todo: 使用游标而不是offset，避免深分页问题
async def get_leaderboad_records_in_page(
    db: AsyncSession, 
    track_id: uuid.UUID,
    gender: Gender,
    page: int,
    size: int
) -> List[BikeLeaderboard]:
    result = await db.execute(
        select(BikeLeaderboard)
        .where(
            BikeLeaderboard.track_id == track_id,
            BikeLeaderboard.gender == gender
        )
        .options(
            selectinload(BikeLeaderboard.record),
            selectinload(BikeLeaderboard.user)
        )
        .order_by(BikeLeaderboard.rank_position.asc())
        .offset((page - 1) * size)
        .limit(size)
    )
    return result.scalars().all()

async def get_score_by_season_and_user(db: AsyncSession, user_id: uuid.UUID, season_id: uuid.UUID | None = None) -> BikeCareerScore | None:
    real_season_id = season_id
    if not real_season_id:
        season = await get_season_now(db)
        if not season:
            return None
        real_season_id = season.id
    result = await db.execute(
        select(BikeCareerScore)
        .where(
            BikeCareerScore.season_id == real_season_id,
            BikeCareerScore.user_id == user_id
        )
    )
    return result.scalar_one_or_none()

async def get_scores_in_page(
    db: AsyncSession, 
    season_id: uuid.UUID,
    gender: Gender,
    page: int,
    size: int
) -> List[BikeCareerScore]:
    result = await db.execute(
        select(BikeCareerScore)
        .where(
            BikeCareerScore.season_id == season_id,
            BikeCareerScore.gender == gender
        )
        .options(
            selectinload(BikeCareerScore.user)
        )
        .order_by(BikeCareerScore.score.desc(), BikeCareerScore.updated_at.asc())
        .offset((page - 1) * size)
        .limit(size)
    )
    return result.scalars().all()

async def get_score_and_rank_by_season_id_and_user(
    db: AsyncSession, 
    season_id: uuid.UUID,
    user_id: uuid.UUID,
    gender: Gender
) -> tuple[int | None, int | None, int | None, int | None]:
    rank_col = func.rank().over(
        partition_by=BikeCareerScore.gender,
        order_by=(BikeCareerScore.score.desc(), BikeCareerScore.updated_at.asc())
    )
    # 子查询：对整个赛季计算 rank
    subq = (
        select(
            BikeCareerScore.user_id,
            BikeCareerScore.score,
            BikeCareerScore.voucher_bonus,
            BikeCareerScore.xp,
            rank_col.label("rank")
        )
        .where(
            BikeCareerScore.season_id == season_id,
            BikeCareerScore.gender == gender
        )
        .subquery()
    )
    # 再查出目标用户
    stmt = select(subq.c.score, subq.c.rank, subq.c.voucher_bonus, subq.c.xp).where(subq.c.user_id == user_id)
    result = await db.execute(stmt)
    row = result.first()

    if row is None:
        return None, None, None, None
    score, rank, voucher_bonus, xp = row
    return score, rank, voucher_bonus, xp

async def add_or_update_career_score(
    db: AsyncSession, 
    season_id: uuid.UUID,
    gender: Gender, 
    user_id: uuid.UUID, 
    score: int,
    voucher: int
):
    stmt = insert(BikeCareerScore).values(
        season_id=season_id,
        gender=gender,
        user_id=user_id,
        score=score,
        voucher_bonus=voucher,
        xp=0
    ).on_conflict_do_update(
        index_elements=[BikeCareerScore.season_id, BikeCareerScore.user_id],
        set_={
            "score": BikeCareerScore.score + score,
            "voucher_bonus": BikeCareerScore.voucher_bonus + voucher,
            "gender": gender,  # 冲突时强制更新为新 gender
            "updated_at": func.now()
        }
    )
    await db.execute(stmt)

async def add_or_update_career_xp(
    db: AsyncSession, 
    season_id: uuid.UUID,
    gender: Gender, 
    user_id: uuid.UUID, 
    xp: int
):
    stmt = insert(BikeCareerScore).values(
        season_id=season_id,
        gender=gender,
        user_id=user_id,
        score=0,
        voucher_bonus=0,
        xp=xp
    ).on_conflict_do_update(
        index_elements=[BikeCareerScore.season_id, BikeCareerScore.user_id],
        set_={
            "xp": BikeCareerScore.xp + xp,
            "updated_at": func.now()
        }
    )
    await db.execute(stmt)

async def add_or_update_career_statistic_data(
    db: AsyncSession, 
    season_id: uuid.UUID,
    user_id: uuid.UUID, 
    distance: float,
    time: float
):
    stmt = insert(BikeCareerStatisticData).values(
        season_id=season_id,
        user_id=user_id,
        total_distance=distance,
        total_time=time
    ).on_conflict_do_update(
        index_elements=[BikeCareerStatisticData.season_id, BikeCareerStatisticData.user_id],
        set_={
            "total_distance": BikeCareerStatisticData.total_distance + distance,
            "total_time": BikeCareerStatisticData.total_time + time,
        }
    )
    await db.execute(stmt)

async def get_career_statistic_data(
    db: AsyncSession, 
    season_id: uuid.UUID,
    user_id: uuid.UUID
) -> BikeCareerStatisticData | None:
    result = await db.execute(
        select(BikeCareerStatisticData)
        .where(
            BikeCareerStatisticData.season_id == season_id,
            BikeCareerStatisticData.user_id == user_id
        )
    )
    return result.scalar_one_or_none()

def decide_task_type_by_date(date: date) -> DailyTaskType:
    return DailyTaskType.distance if date.day % 2 == 1 else DailyTaskType.time

async def get_daily_task(db: AsyncSession, user: User) -> BikeDailyTask | None:
    # 用户的local日期
    today = get_user_local_date(user, None)
    # 根据日期的奇偶决定 每日任务 的类型
    # 奇数日：distance，偶数日：time
    task_type = decide_task_type_by_date(today)
    result = await db.execute(
        select(BikeDailyTask)
        .where(
            BikeDailyTask.type == task_type
        )
    )
    return result.scalar_one_or_none()

async def get_today_task_record_by_user(
    db: AsyncSession, 
    user: User
) -> BikeDailyTaskRecord | None:
    today = get_user_local_date(user, None)
    task_type = decide_task_type_by_date(today)
    result = await db.execute(
        select(BikeDailyTaskRecord)
        .where(
            BikeDailyTaskRecord.user_id == user.id,
            BikeDailyTaskRecord.date == today,
            BikeDailyTaskRecord.type == task_type
        )
    )
    return result.scalar_one_or_none()

async def add_or_update_daily_task_record(
    db: AsyncSession,
    user: User,
    distance_progress: float,
    time_progress: float
):
    today = get_user_local_date(user, None)
    task_type = decide_task_type_by_date(today)
    progress = distance_progress if task_type == DailyTaskType.distance else time_progress
    result = await db.execute(
        select(BikeDailyTaskRecord)
        .where(
            BikeDailyTaskRecord.user_id == user.id,
            BikeDailyTaskRecord.date == today,
            BikeDailyTaskRecord.type == task_type
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        new_record = BikeDailyTaskRecord(
            user_id=user.id,
            type=task_type,
            progress=progress,
            date=today
        )
        db.add(new_record)
    else:
        record.progress += progress

async def get_bonus_record_with_team_magic_card_by_team_id(db: AsyncSession, team_id: uuid.UUID) -> List[BikeBonusByTeamMember]:
    result = await db.execute(
        select(BikeBonusByTeamMember)
        .where(
            BikeBonusByTeamMember.team_id == team_id
        )
    )
    return result.scalars().all()

async def get_bonus_record_with_team_magic_card_for_update(db: AsyncSession, team_id: uuid.UUID) -> List[BikeBonusByTeamMember]:
    result = await db.execute(
        select(BikeBonusByTeamMember)
        .where(
            BikeBonusByTeamMember.team_id == team_id
        )
        .order_by(BikeBonusByTeamMember.id)
        .with_for_update()
    )
    return result.scalars().all()

async def get_bonus_record_with_team_magic_card_by_team_user(db: AsyncSession, team_id: uuid.UUID, user_id: uuid.UUID) -> BikeBonusByTeamMember | None:
    result = await db.execute(
        select(BikeBonusByTeamMember)
        .where(
            BikeBonusByTeamMember.team_id == team_id,
            BikeBonusByTeamMember.user_id == user_id
        )
    )
    return result.scalar_one_or_none()
