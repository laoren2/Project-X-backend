from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_, exists
from app.db.models.competition import (
    Region, RunningEvent, RunningSeason, 
    RunningTrack, RunningRaceRecord, RunningTeam, RunningTeamMember, RunningTeamAppliedMember,
    CardBonusInRunningRecord, RunningLeaderboard, RunningCareerScore
)
from app.db.models.asset import UserEquipmentCard
from app.schemas.competition.common import RecordStatus, TeamStatus
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import timedelta
from sqlalchemy.dialects.postgresql import insert
from app.schemas.user import Gender
import uuid


async def create_season_crud(db: AsyncSession, season: RunningSeason) -> RunningSeason:
    db.add(season)
    await db.flush()
    await db.refresh(season)
    return season


async def update_season_crud(db: AsyncSession, season: RunningSeason, update_data: dict):
    for field, value in update_data.items():
        setattr(season, field, value)
    db.add(season)
    await db.flush()
    await db.refresh(season)


async def get_season_now(db: AsyncSession) -> List[RunningSeason]:
    current_time = func.now()
    stmt = select(RunningSeason).where(
        and_(
            RunningSeason.start_date <= current_time,
            RunningSeason.end_date >= current_time
        )
    )
    result = await db.execute(stmt)
    seasons = result.scalars().all()
    return seasons

async def get_history_seasons(db: AsyncSession) -> List[RunningSeason]:
    result = await db.execute(
        select(RunningSeason).where(
            RunningSeason.start_date < func.now()
        )
        .order_by(RunningSeason.start_date.desc())
    )
    return result.scalars().all()

async def get_season_by_name(db: AsyncSession, name: str) -> RunningSeason | None:
    result = await db.execute(
        select(RunningSeason).where(
            RunningSeason.name == name
        )
    )
    return result.scalar_one_or_none()

async def get_season_by_season_id(db: AsyncSession, season_id: str) -> RunningSeason | None:
    result = await db.execute(
        select(RunningSeason)
        .where(RunningSeason.season_id == season_id)
        .options(
            selectinload(RunningSeason.running_events)
                .selectinload(RunningEvent.region),
            selectinload(RunningSeason.running_events)
                .selectinload(RunningEvent.tracks)
        )
    )
    return result.scalar_one_or_none()


async def get_active_events_by_season_id(db: AsyncSession, season_id: uuid.UUID) -> List[RunningEvent]:
    result = await db.execute(
        select(RunningEvent)
        .options(
            selectinload(RunningEvent.tracks),
            selectinload(RunningEvent.region)
        )
        .where(
            RunningEvent.season_id == season_id,
            RunningEvent.start_date < func.now(),
            RunningEvent.end_date > func.now()
        )
    )
    return result.scalars().all()


async def get_event_by_event_id(db: AsyncSession, event_id: str) -> RunningEvent | None:
    result = await db.execute(
        select(RunningEvent)
        .options(
            selectinload(RunningEvent.season)
        )
        .where(RunningEvent.event_id == event_id)
    )
    return result.scalar_one_or_none()


async def get_event_by_name(db: AsyncSession, name: str) -> RunningEvent | None:
    result = await db.execute(select(RunningEvent).where(RunningEvent.name == name))
    return result.scalar_one_or_none()


async def get_event_by_season_id_and_region_id(db: AsyncSession, season_id: uuid.UUID, region_id: uuid.UUID) -> List[RunningEvent]:
    result = await db.execute(
        select(RunningEvent).where(
            and_(
                RunningEvent.season_id == season_id,
                RunningEvent.region_id == region_id,
                RunningEvent.start_date <= func.now() + timedelta(days=3),
                RunningEvent.end_date >= func.now()
            )
        )
    )
    return result.scalars().all()

async def create_event_crud(db: AsyncSession, event: RunningEvent) -> RunningEvent:
    db.add(event)
    await db.flush()
    await db.refresh(event)
    # 显式加载 region 和 season
    result = await db.execute(
        select(RunningEvent)
        .options(selectinload(RunningEvent.region), selectinload(RunningEvent.season))
        .where(RunningEvent.id == event.id)
    )
    return result.scalar_one()


async def update_event_crud(db: AsyncSession, event: RunningEvent, update_data: dict):
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
) -> List[RunningEvent]:
    stmt = select(RunningEvent).options(
        selectinload(RunningEvent.region),
        selectinload(RunningEvent.season)
    ).join(RunningEvent.region).join(RunningEvent.season)

    if season_name:
        stmt = stmt.filter(func.lower(RunningSeason.name).contains(season_name.lower()))
    if region_name:
        stmt = stmt.filter(func.lower(Region.name).contains(region_name.lower()))
    if event_name:
        stmt = stmt.filter(func.lower(RunningEvent.name).contains(event_name.lower()))

    stmt = stmt.order_by(RunningEvent.created_at.asc()).offset((page - 1) * size).limit(size)

    result = await db.execute(stmt)
    return result.scalars().all()


async def get_track_by_track_id(db: AsyncSession, track_id: str) -> RunningTrack | None:
    result = await db.execute(
        select(RunningTrack)
        .where(RunningTrack.track_id == track_id)
        .options(
            selectinload(RunningTrack.event).selectinload(RunningEvent.season)
        )
    )
    return result.scalar_one_or_none()

async def get_track_by_track_id_for_update(db: AsyncSession, track_id: str) -> RunningTrack | None:
    result = await db.execute(
        select(RunningTrack)
        .where(RunningTrack.track_id == track_id)
        .options(
            selectinload(RunningTrack.event).selectinload(RunningEvent.season)
        )
        .with_for_update()
    )
    return result.scalar_one_or_none()


async def get_track_by_name(db: AsyncSession, name: str) -> RunningTrack | None:
    result = await db.execute(select(RunningTrack).where(RunningTrack.name == name))
    return result.scalar_one_or_none()


async def get_track_by_event_id(db: AsyncSession, event_id: uuid.UUID) -> List[RunningTrack]:
    result = await db.execute(
        select(RunningTrack)
        .where(
            RunningTrack.event_id == event_id,
            RunningTrack.start_date <= func.now() + timedelta(days=3),
            RunningTrack.end_date >= func.now()
        )
        .order_by(RunningTrack.start_date.desc())
    )
    return result.scalars().all()


async def create_track_crud(db: AsyncSession, track: RunningTrack) -> RunningTrack:
    db.add(track)
    await db.flush()
    await db.refresh(track)
    # 显式加载 region 和 season
    result = await db.execute(
        select(RunningTrack)
        .options(
            selectinload(RunningTrack.event).selectinload(RunningEvent.season),
            selectinload(RunningTrack.event).selectinload(RunningEvent.region)
        )
        .where(RunningTrack.id == track.id)
    )
    return result.scalar_one()


async def update_track_crud(db: AsyncSession, track: RunningTrack, update_data: dict):
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
) -> List[RunningTrack]:
    # EXISTS 子查询：判断某 track_id 是否在 RunningLeaderboard 里存在
    is_settled_subq = (
        exists().where(RunningLeaderboard.track_id == RunningTrack.id)
        .correlate(RunningTrack)
        .select()
        .label("is_settled")
    )

    stmt = (
        select(RunningTrack, is_settled_subq)
        .options(
            selectinload(RunningTrack.event).selectinload(RunningEvent.season),
            selectinload(RunningTrack.event).selectinload(RunningEvent.region)
        )
        .join(RunningTrack.event)
        .join(RunningEvent.season)
        .join(RunningEvent.region)
    )

    if event_name:
        stmt = stmt.filter(func.lower(RunningEvent.name).contains(event_name.lower()))
    if season_name:
        stmt = stmt.filter(func.lower(RunningSeason.name).contains(season_name.lower()))
    if region_name:
        stmt = stmt.filter(func.lower(Region.name).contains(region_name.lower()))
    if track_name:
        stmt = stmt.filter(func.lower(RunningTrack.name).contains(track_name.lower()))

    stmt = stmt.order_by(RunningTrack.created_at.asc()).offset((page - 1) * size).limit(size)

    result = await db.execute(stmt)
    rows = result.all()
    return [(track, is_settled) for track, is_settled in rows]

async def track_has_settled(db: AsyncSession, track_id: uuid.UUID) -> bool:
    stmt = select(
        exists().where(RunningLeaderboard.track_id == track_id)
    )
    result = await db.execute(stmt)
    return result.scalar()

async def create_record_crud(db: AsyncSession, record: RunningRaceRecord):
    db.add(record)
    await db.flush()
    await db.refresh(record)
    result = await db.execute(
        select(RunningRaceRecord)
        .options(
            selectinload(RunningRaceRecord.track).selectinload(RunningTrack.event).selectinload(RunningEvent.region),
            selectinload(RunningRaceRecord.team)
        )
        .where(RunningRaceRecord.id == record.id)
    )
    return result.scalar_one()

async def get_records_by_user_id(
    db: AsyncSession, 
    user_id: uuid.UUID,
    status: RecordStatus,
    page: int,
    size: int
) -> List[RunningRaceRecord]:
    stmt = (
        select(RunningRaceRecord)
        .where(RunningRaceRecord.user_id == user_id, RunningRaceRecord.status == status)
        .options(
            selectinload(RunningRaceRecord.track).selectinload(RunningTrack.event).selectinload(RunningEvent.region),
            selectinload(RunningRaceRecord.team)
        )
        .order_by(RunningRaceRecord.created_at.desc()).offset((page - 1) * size).limit(size)
    )
    result = await db.execute(stmt)
    return result.scalars().all()

async def get_record_by_record_id(db: AsyncSession, record_id: str) -> RunningRaceRecord | None:
    record = await db.execute(
        select(RunningRaceRecord)
        .where(RunningRaceRecord.record_id == record_id)
        .options(
            selectinload(RunningRaceRecord.track),
            selectinload(RunningRaceRecord.team)
                .selectinload(RunningTeam.members),
            selectinload(RunningRaceRecord.path),
            selectinload(RunningRaceRecord.card_bonus)
                .selectinload(CardBonusInRunningRecord.card)
                .selectinload(UserEquipmentCard.equipment_def)
        )
    )
    return record.scalar_one_or_none()

async def get_records_by_team_id(db: AsyncSession, team_id: uuid.UUID) -> List[RunningRaceRecord]:
    result = await db.execute(
        select(RunningRaceRecord)
        .where(RunningRaceRecord.team_id == team_id)
        .options(
            selectinload(RunningRaceRecord.user)
        )
    )
    return result.scalars().all()

async def get_records_by_team_id_for_update(db: AsyncSession, team_id: uuid.UUID) -> List[RunningRaceRecord]:
    result = await db.execute(
        select(RunningRaceRecord)
        .where(RunningRaceRecord.team_id == team_id)
        .with_for_update()
    )
    return result.scalars().all()

async def get_record_by_team_id_and_user_id(db: AsyncSession, team_id: uuid.UUID, user_id: uuid.UUID) -> RunningRaceRecord | None:
    record = await db.execute(
        select(RunningRaceRecord)
        .where(RunningRaceRecord.team_id == team_id, RunningRaceRecord.user_id == user_id)
    )
    return record.scalar_one_or_none()

async def delete_record_crud(db: AsyncSession, record: RunningRaceRecord):
    await db.delete(record)
    await db.flush()

async def delete_records_by_team_id(db: AsyncSession, team_id: uuid.UUID):
    stmt = select(RunningRaceRecord).where(RunningRaceRecord.team_id == team_id)
    result = await db.execute(stmt)
    records = result.scalars().all()
    for record in records:
        await db.delete(record)
    await db.flush()

async def update_record_crud(db: AsyncSession, record: RunningRaceRecord, update_data: dict):
    for field, value in update_data.items():
        setattr(record, field, value)
    db.add(record)
    await db.flush()


async def create_team_crud(db: AsyncSession, team: RunningTeam) -> tuple[str, uuid.UUID]:
    db.add(team)
    await db.flush()
    await db.refresh(team)
    return team.team_code, team.id

async def create_team_member_crud(db: AsyncSession, member: RunningTeamMember):
    db.add(member)
    await db.flush()


async def get_team_by_code(db: AsyncSession, team_code: str) -> RunningTeam | None:
    team = await db.execute(
        select(RunningTeam)
        .where(RunningTeam.team_code == team_code)
        .options(
            selectinload(RunningTeam.track),
            selectinload(RunningTeam.members)
        )
    )
    return team.scalar_one_or_none()
# 加行级锁
async def get_team_by_code_for_update(db: AsyncSession, team_code: str) -> RunningTeam | None:
    team = await db.execute(
        select(RunningTeam)
        .where(RunningTeam.team_code == team_code)
        .with_for_update()
        .options(
            selectinload(RunningTeam.track),
            selectinload(RunningTeam.members)
        )
    )
    return team.scalar_one_or_none()

async def get_team_by_team_id(db: AsyncSession, team_id: str) -> RunningTeam | None:
    team = await db.execute(
        select(RunningTeam)
        .where(RunningTeam.team_id == team_id)
        .options(
            selectinload(RunningTeam.track)
                .selectinload(RunningTrack.event)
                .selectinload(RunningEvent.region),
            selectinload(RunningTeam.members)
                .selectinload(RunningTeamMember.user),
            selectinload(RunningTeam.applied_members)
                .selectinload(RunningTeamAppliedMember.user)
        )
    )
    return team.scalar_one_or_none()
# 加行级锁
async def get_team_by_team_id_for_update(db: AsyncSession, team_id: str) -> RunningTeam | None:
    team = await db.execute(
        select(RunningTeam)
        .where(RunningTeam.team_id == team_id)
        .with_for_update()
        .options(
            selectinload(RunningTeam.track)
                .selectinload(RunningTrack.event)
                .selectinload(RunningEvent.region),
            selectinload(RunningTeam.members)
                .selectinload(RunningTeamMember.user),
            selectinload(RunningTeam.applied_members)
                .selectinload(RunningTeamAppliedMember.user)
        )
    )
    return team.scalar_one_or_none()
# 加行级锁
async def get_team_by_id_for_update(db: AsyncSession, team_id: uuid.UUID) -> RunningTeam | None:
    team = await db.execute(
        select(RunningTeam)
        .where(RunningTeam.id == team_id)
        .with_for_update()
        .options(
            selectinload(RunningTeam.track)
                .selectinload(RunningTrack.event)
                .selectinload(RunningEvent.region),
            selectinload(RunningTeam.members)
                .selectinload(RunningTeamMember.user),
            selectinload(RunningTeam.applied_members)
                .selectinload(RunningTeamAppliedMember.user)
        )
    )
    return team.scalar_one_or_none()

async def get_public_teams_by_track_id(db: AsyncSession, track_id: uuid.UUID, page: int, size: int) -> List[RunningTeam]:
    result = await db.execute(
        select(RunningTeam)
        .where(
            RunningTeam.track_id == track_id,
            RunningTeam.is_public == True,
            RunningTeam.status == TeamStatus.prepared
        )
        .options(
            selectinload(RunningTeam.members)
                .selectinload(RunningTeamMember.user)
        )
        .order_by(RunningTeam.created_at.desc(), RunningTeam.id)
        .offset((page - 1) * size)
        .limit(size)
    )
    teams = result.scalars().all()
    filtered_teams = [
        team for team in teams if len(team.members) < team.members_count_max
    ]
    return filtered_teams

async def get_created_teams_by_user_id(db: AsyncSession, user_id: uuid.UUID, page: int, size: int) -> List[RunningTeam]:
    result = await db.execute(
        select(RunningTeam)
        .join(RunningTeam.members)
        .where(
            RunningTeamMember.user_id == user_id,
            RunningTeamMember.is_leader == True,
            RunningTeam.status != TeamStatus.completed
        )
        .options(
            selectinload(RunningTeam.members),
            selectinload(RunningTeam.track)
                .selectinload(RunningTrack.event)
                .selectinload(RunningEvent.region)
        )
        .order_by(RunningTeam.created_at.desc(), RunningTeam.id)
        .offset((page - 1) * size)
        .limit(size)
    )
    return result.scalars().all()

async def get_joined_teams_by_user_id(db: AsyncSession, user_id: uuid.UUID, page: int, size: int) -> List[RunningTeam]:
    result = await db.execute(
        select(RunningTeam)
        .join(RunningTeam.members)
        .where(
            RunningTeamMember.user_id == user_id,
            RunningTeamMember.is_leader == False,
            RunningTeam.status != TeamStatus.completed
        )
        .options(
            selectinload(RunningTeam.members),
            selectinload(RunningTeam.track)
                .selectinload(RunningTrack.event)
                .selectinload(RunningEvent.region)
        )
        .order_by(RunningTeamMember.created_at.desc(), RunningTeam.id)
        .offset((page - 1) * size)
        .limit(size)
    )
    return result.scalars().all()

async def get_applied_teams_by_user_id(db: AsyncSession, user_id: uuid.UUID, page: int, size: int) -> List[RunningTeam]:
    result = await db.execute(
        select(RunningTeam)
        .join(RunningTeam.applied_members)
        .where(
            RunningTeamAppliedMember.user_id == user_id,
            RunningTeam.status != TeamStatus.completed
        )
        .options(
            selectinload(RunningTeam.members),
            selectinload(RunningTeam.track)
                .selectinload(RunningTrack.event)
                .selectinload(RunningEvent.region)
        )
        .order_by(RunningTeamAppliedMember.created_at.desc(), RunningTeam.id)
        .offset((page - 1) * size)
        .limit(size)
    )
    return result.scalars().all()

async def update_team_crud(db: AsyncSession, team: RunningTeam, update_data: dict):
    for field, value in update_data.items():
        setattr(team, field, value)
    db.add(team)
    await db.flush()
    await db.refresh(team)

async def get_leaderboad_record(
    db: AsyncSession, 
    track_id: uuid.UUID,
    user_id: uuid.UUID
) -> RunningLeaderboard | None:
    result = await db.execute(
        select(RunningLeaderboard)
        .where(
            RunningLeaderboard.track_id == track_id,
            RunningLeaderboard.user_id == user_id
        )
        .options(
            selectinload(RunningLeaderboard.record)
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
) -> List[RunningLeaderboard]:
    result = await db.execute(
        select(RunningLeaderboard)
        .where(
            RunningLeaderboard.track_id == track_id,
            RunningLeaderboard.gender == gender
        )
        .options(
            selectinload(RunningLeaderboard.record),
            selectinload(RunningLeaderboard.user)
        )
        .order_by(RunningLeaderboard.rank_position.asc())
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
) -> List[RunningCareerScore]:
    result = await db.execute(
        select(RunningCareerScore)
        .where(
            RunningCareerScore.season_id == season_id,
            RunningCareerScore.gender == gender
        )
        .options(
            selectinload(RunningCareerScore.user)
        )
        .order_by(RunningCareerScore.score.desc(), RunningCareerScore.updated_at.asc())
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
        order_by=(RunningCareerScore.score.desc(), RunningCareerScore.updated_at.asc())
    )
    # 子查询：对整个赛季计算 rank
    subq = (
        select(
            RunningCareerScore.user_id,
            RunningCareerScore.score,
            rank_col.label("rank")
        )
        .where(RunningCareerScore.season_id == season_id)
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
    stmt = insert(RunningCareerScore).values(
        season_id=season_id,
        gender=gender,
        user_id=user_id,
        score=score
    ).on_conflict_do_update(
        index_elements=[RunningCareerScore.season_id, RunningCareerScore.user_id],
        set_={
            "score": RunningCareerScore.score + score,
            "gender": gender  # 冲突时强制更新为新 gender
        }
    )
    await db.execute(stmt)