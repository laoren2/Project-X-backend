from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_, exists
from app.db.models.competition import (
    Region, BikeEvent, BikeSeason, 
    BikeTrack, BikeRaceRecord, BikeTeam, BikeTeamMember, BikeTeamAppliedMember,
    CardBonusInBikeRecord, BikeLeaderboard, BikeCareerScore
)
from app.db.models.asset import EquipmentCardDef, UserEquipmentCard
from app.schemas.competition.common import RecordStatus, TeamStatus
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import timedelta
import uuid
from sqlalchemy.dialects.postgresql import insert
from app.schemas.user import Gender



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


async def get_season_now(db: AsyncSession) -> List[BikeSeason]:
    current_time = func.now()
    stmt = select(BikeSeason).where(
        and_(
            BikeSeason.start_date <= current_time,
            BikeSeason.end_date >= current_time
        )
    )
    result = await db.execute(stmt)
    seasons = result.scalars().all()
    return seasons

async def get_history_seasons(db: AsyncSession) -> List[BikeSeason]:
    result = await db.execute(
        select(BikeSeason).where(
            BikeSeason.start_date < func.now()
        )
        .order_by(BikeSeason.start_date.desc())
    )
    return result.scalars().all()

async def get_season_by_name(db: AsyncSession, name: str) -> BikeSeason | None:
    result = await db.execute(
        select(BikeSeason).where(
            BikeSeason.name == name
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


async def get_event_by_name(db: AsyncSession, name: str) -> BikeEvent | None:
    result = await db.execute(select(BikeEvent).where(BikeEvent.name == name))
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
        stmt = stmt.filter(func.lower(BikeSeason.name).contains(season_name.lower()))
    if region_name:
        stmt = stmt.filter(func.lower(Region.name).contains(region_name.lower()))
    if event_name:
        stmt = stmt.filter(func.lower(BikeEvent.name).contains(event_name.lower()))

    stmt = stmt.order_by(BikeEvent.created_at.asc()).offset((page - 1) * size).limit(size)

    result = await db.execute(stmt)
    return result.scalars().all()


async def get_track_by_track_id(db: AsyncSession, track_id: str) -> BikeTrack | None:
    result = await db.execute(
        select(BikeTrack)
        .where(BikeTrack.track_id == track_id)
        .options(
            selectinload(BikeTrack.event).selectinload(BikeEvent.season)
        )
    )
    return result.scalar_one_or_none()

async def get_track_by_track_id_for_update(db: AsyncSession, track_id: str) -> BikeTrack | None:
    result = await db.execute(
        select(BikeTrack)
        .where(BikeTrack.track_id == track_id)
        .options(
            selectinload(BikeTrack.event).selectinload(BikeEvent.season)
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
        .order_by(BikeTrack.start_date.desc())
    )
    return result.scalars().all()


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
        stmt = stmt.filter(func.lower(BikeEvent.name).contains(event_name.lower()))
    if season_name:
        stmt = stmt.filter(func.lower(BikeSeason.name).contains(season_name.lower()))
    if region_name:
        stmt = stmt.filter(func.lower(Region.name).contains(region_name.lower()))
    if track_name:
        stmt = stmt.filter(func.lower(BikeTrack.name).contains(track_name.lower()))

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

async def get_records_by_user_id(
    db: AsyncSession, 
    user_id: uuid.UUID,
    status: RecordStatus,
    page: int,
    size: int
) -> List[BikeRaceRecord]:
    stmt = (
        select(BikeRaceRecord)
        .where(BikeRaceRecord.user_id == user_id, BikeRaceRecord.status == status)
        .options(
            selectinload(BikeRaceRecord.track).selectinload(BikeTrack.event).selectinload(BikeEvent.region),
            selectinload(BikeRaceRecord.team)
        )
        .order_by(BikeRaceRecord.created_at.desc()).offset((page - 1) * size).limit(size)
    )
    result = await db.execute(stmt)
    return result.scalars().all()

async def get_record_by_record_id(db: AsyncSession, record_id: str) -> BikeRaceRecord | None:
    record = await db.execute(
        select(BikeRaceRecord)
        .where(BikeRaceRecord.record_id == record_id)
        .options(
            selectinload(BikeRaceRecord.track),
            selectinload(BikeRaceRecord.team)
                .selectinload(BikeTeam.members),
            selectinload(BikeRaceRecord.path),
            selectinload(BikeRaceRecord.card_bonus)
                .selectinload(CardBonusInBikeRecord.card)
                .selectinload(UserEquipmentCard.equipment_def)
        )
    )
    return record.scalar_one_or_none()

async def get_records_by_team_id(db: AsyncSession, team_id: uuid.UUID) -> List[BikeRaceRecord]:
    result = await db.execute(
        select(BikeRaceRecord)
        .where(BikeRaceRecord.team_id == team_id)
        .options(
            selectinload(BikeRaceRecord.user)
        )
    )
    return result.scalars().all()

async def get_records_by_team_id_for_update(db: AsyncSession, team_id: uuid.UUID) -> List[BikeRaceRecord]:
    result = await db.execute(
        select(BikeRaceRecord)
        .where(BikeRaceRecord.team_id == team_id)
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
async def get_team_by_code_for_update(db: AsyncSession, team_code: str) -> BikeTeam | None:
    team = await db.execute(
        select(BikeTeam)
        .where(BikeTeam.team_code == team_code)
        .with_for_update()
        .options(
            selectinload(BikeTeam.track),
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

async def get_score_and_rank_by_season_id_and_user_id(
    db: AsyncSession, 
    season_id: uuid.UUID,
    user_id: uuid.UUID
) -> tuple[int | None, int | None]:
    rank_col = func.rank().over(
        order_by=(BikeCareerScore.score.desc(), BikeCareerScore.updated_at.asc())
    )
    # 子查询：对整个赛季计算 rank
    subq = (
        select(
            BikeCareerScore.user_id,
            BikeCareerScore.score,
            rank_col.label("rank")
        )
        .where(BikeCareerScore.season_id == season_id)
        .subquery()
    )
    # 再查出目标用户
    stmt = select(subq.c.score, subq.c.rank).where(subq.c.user_id == user_id)
    result = await db.execute(stmt)
    row = result.first()

    if row is None:
        return None, None
    score, rank = row
    return score, rank

async def add_or_update_career_score(
    db: AsyncSession, 
    season_id: uuid.UUID,
    gender: Gender, 
    user_id: uuid.UUID, 
    score: int
):
    stmt = insert(BikeCareerScore).values(
        season_id=season_id,
        gender=gender,
        user_id=user_id,
        score=score
    ).on_conflict_do_update(
        index_elements=[BikeCareerScore.season_id, BikeCareerScore.user_id],
        set_={
            "score": BikeCareerScore.score + score,
            "gender": gender  # 冲突时强制更新为新 gender
        }
    )
    await db.execute(stmt)