from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_
from app.db.models import Region, RunningEvent, Season, RunningTrack
from sqlalchemy.orm import selectinload
from typing import Optional, List
import uuid



async def get_event_by_event_id(db: AsyncSession, event_id: str) -> RunningEvent | None:
    result = await db.execute(select(RunningEvent).where(RunningEvent.event_id == event_id))
    return result.scalar_one_or_none()


async def get_event_by_name(db: AsyncSession, name: str) -> RunningEvent | None:
    result = await db.execute(select(RunningEvent).where(RunningEvent.name == name))
    return result.scalar_one_or_none()


async def get_event_by_season_id_and_region_id(db: AsyncSession, season_id: uuid.UUID, region_id: uuid.UUID) -> List[RunningEvent]:
    result = await db.execute(
        select(RunningEvent).where(
            and_(
                RunningEvent.season_id == season_id,
                RunningEvent.region_id == region_id
            )
        )
    )
    return result.scalars().all()

async def create_event_crud(db: AsyncSession, event: RunningEvent) -> RunningEvent:
    db.add(event)
    await db.commit()
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
    await db.commit()
    await db.refresh(event)


async def query_events_crud(
    db: AsyncSession,
    season_name: Optional[str],
    region_name: Optional[str],
    sport_type: Optional[str],
    event_name: Optional[str],
    page: int,
    size: int
) -> List[RunningEvent]:
    stmt = select(RunningEvent).options(
        selectinload(RunningEvent.region),
        selectinload(RunningEvent.season)
    ).join(RunningEvent.region).join(RunningEvent.season)

    if season_name:
        stmt = stmt.filter(func.lower(Season.name).contains(season_name.lower()))
    if region_name:
        stmt = stmt.filter(func.lower(Region.name).contains(region_name.lower()))
    if sport_type:
        stmt = stmt.filter(func.lower(Season.sport_type).contains(sport_type.lower()))
    if event_name:
        stmt = stmt.filter(func.lower(RunningEvent.name).contains(event_name.lower()))

    stmt = stmt.order_by(RunningEvent.created_at.asc()).offset((page - 1) * size).limit(size)

    result = await db.execute(stmt)
    return result.scalars().all()


async def get_track_by_track_id(db: AsyncSession, track_id: str) -> RunningTrack | None:
    result = await db.execute(select(RunningTrack).where(RunningTrack.track_id == track_id))
    return result.scalar_one_or_none()


async def get_track_by_name(db: AsyncSession, name: str) -> RunningTrack | None:
    result = await db.execute(select(RunningTrack).where(RunningTrack.name == name))
    return result.scalar_one_or_none()


async def get_track_by_event_id(db: AsyncSession, event_id: uuid.UUID) -> List[RunningTrack]:
    result = await db.execute(select(RunningTrack).where(RunningTrack.event_id == event_id))
    return result.scalars().all()


async def create_track_crud(db: AsyncSession, track: RunningTrack) -> RunningTrack:
    db.add(track)
    await db.commit()
    await db.refresh(track)
    # 显式加载 region 和 season
    result = await db.execute(
        select(RunningTrack)
        .options(selectinload(RunningTrack.event))
        .where(RunningTrack.id == track.id)
    )
    return result.scalar_one()


async def update_track_crud(db: AsyncSession, track: RunningTrack, update_data: dict):
    for field, value in update_data.items():
        setattr(track, field, value)
    db.add(track)
    await db.commit()
    await db.refresh(track)


async def query_tracks_crud(
    db: AsyncSession,
    track_name: Optional[str],
    event_name: Optional[str],
    season_name: Optional[str],
    region_name: Optional[str],
    sport_type: Optional[str],
    page: int,
    size: int
) -> List[RunningTrack]:
    stmt = select(RunningTrack).options(
        selectinload(RunningTrack.event).selectinload(RunningEvent.season),
        selectinload(RunningTrack.event).selectinload(RunningEvent.region)
    ).join(RunningTrack.event).join(RunningEvent.season).join(RunningEvent.region)

    if event_name:
        stmt = stmt.filter(func.lower(RunningEvent.name).contains(event_name.lower()))
    if season_name:
        stmt = stmt.filter(func.lower(Season.name).contains(season_name.lower()))
    if region_name:
        stmt = stmt.filter(func.lower(Region.name).contains(region_name.lower()))
    if sport_type:
        stmt = stmt.filter(func.lower(Season.sport_type).contains(sport_type.lower()))
    if track_name:
        stmt = stmt.filter(func.lower(RunningTrack.name).contains(track_name.lower()))

    stmt = stmt.order_by(RunningTrack.created_at.asc()).offset((page - 1) * size).limit(size)

    result = await db.execute(stmt)
    return result.scalars().all()