from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_
from app.db.models import Region, BikeEvent, Season, BikeTrack
from sqlalchemy.orm import selectinload
from typing import Optional, List
import uuid



async def get_event_by_event_id(db: AsyncSession, event_id: str) -> BikeEvent | None:
    result = await db.execute(select(BikeEvent).where(BikeEvent.event_id == event_id))
    return result.scalar_one_or_none()


async def get_event_by_name(db: AsyncSession, name: str) -> BikeEvent | None:
    result = await db.execute(select(BikeEvent).where(BikeEvent.name == name))
    return result.scalar_one_or_none()


async def get_event_by_season_id_and_region_id(db: AsyncSession, season_id: uuid.UUID, region_id: uuid.UUID) -> List[BikeEvent]:
    result = await db.execute(
        select(BikeEvent).where(
            and_(
                BikeEvent.season_id == season_id,
                BikeEvent.region_id == region_id
            )
        )
    )
    return result.scalars().all()

async def create_event_crud(db: AsyncSession, event: BikeEvent) -> BikeEvent:
    db.add(event)
    await db.commit()
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
) -> List[BikeEvent]:
    stmt = select(BikeEvent).options(
        selectinload(BikeEvent.region),
        selectinload(BikeEvent.season)
    ).join(BikeEvent.region).join(BikeEvent.season)

    if season_name:
        stmt = stmt.filter(func.lower(Season.name).contains(season_name.lower()))
    if region_name:
        stmt = stmt.filter(func.lower(Region.name).contains(region_name.lower()))
    if sport_type:
        stmt = stmt.filter(func.lower(Season.sport_type).contains(sport_type.lower()))
    if event_name:
        stmt = stmt.filter(func.lower(BikeEvent.name).contains(event_name.lower()))

    stmt = stmt.order_by(BikeEvent.created_at.asc()).offset((page - 1) * size).limit(size)

    result = await db.execute(stmt)
    return result.scalars().all()


async def get_track_by_track_id(db: AsyncSession, track_id: str) -> BikeTrack | None:
    result = await db.execute(select(BikeTrack).where(BikeTrack.track_id == track_id))
    return result.scalar_one_or_none()


async def get_track_by_name(db: AsyncSession, name: str) -> BikeTrack | None:
    result = await db.execute(select(BikeTrack).where(BikeTrack.name == name))
    return result.scalar_one_or_none()


async def get_track_by_event_id(db: AsyncSession, event_id: uuid.UUID) -> List[BikeTrack]:
    result = await db.execute(select(BikeTrack).where(BikeTrack.event_id == event_id))
    return result.scalars().all()


async def create_track_crud(db: AsyncSession, track: BikeTrack) -> BikeTrack:
    db.add(track)
    await db.commit()
    await db.refresh(track)
    # 显式加载 region 和 season
    result = await db.execute(
        select(BikeTrack)
        .options(selectinload(BikeTrack.event))
        .where(BikeTrack.id == track.id)
    )
    return result.scalar_one()


async def update_track_crud(db: AsyncSession, track: BikeTrack, update_data: dict):
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
) -> List[BikeTrack]:
    stmt = select(BikeTrack).options(
        selectinload(BikeTrack.event).selectinload(BikeEvent.season),
        selectinload(BikeTrack.event).selectinload(BikeEvent.region)
    ).join(BikeTrack.event).join(BikeEvent.season).join(BikeEvent.region)

    if event_name:
        stmt = stmt.filter(func.lower(BikeEvent.name).contains(event_name.lower()))
    if season_name:
        stmt = stmt.filter(func.lower(Season.name).contains(season_name.lower()))
    if region_name:
        stmt = stmt.filter(func.lower(Region.name).contains(region_name.lower()))
    if sport_type:
        stmt = stmt.filter(func.lower(Season.sport_type).contains(sport_type.lower()))
    if track_name:
        stmt = stmt.filter(func.lower(BikeTrack.name).contains(track_name.lower()))

    stmt = stmt.order_by(BikeTrack.created_at.asc()).offset((page - 1) * size).limit(size)

    result = await db.execute(stmt)
    return result.scalars().all()