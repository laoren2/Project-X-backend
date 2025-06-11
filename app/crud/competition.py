from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from app.db.models import Region, Event, Season, Track
from sqlalchemy.orm import selectinload
from typing import Optional, List
import uuid


async def create_season_crud(db: AsyncSession, season: Season) -> Season:
    db.add(season)
    await db.commit()
    await db.refresh(season)
    return season


async def update_season_crud(db: AsyncSession, season: Season, update_data: dict):
    for field, value in update_data.items():
        setattr(season, field, value)
    db.add(season)
    await db.commit()
    await db.refresh(season)


async def create_region_crud(db: AsyncSession, region: Region):
    db.add(region)
    await db.commit()
    await db.refresh(region)


async def get_region_by_name(db: AsyncSession, name: str) -> Region | None:
    result = await db.execute(select(Region).where(Region.name == name))
    return result.scalar_one_or_none()


async def get_season_by_name_and_sport_type(db: AsyncSession, name: str, sport_type: str) -> Season | None:
    result = await db.execute(
        select(Season).where(
            Season.name == name,
            Season.sport_type == sport_type
        )
    )
    return result.scalar_one_or_none()


async def get_season_by_season_id(db: AsyncSession, season_id: str) -> Season | None:
    result = await db.execute(select(Season).where(Season.season_id == season_id))
    return result.scalar_one_or_none()


async def get_event_by_event_id(db: AsyncSession, event_id: str) -> Event | None:
    result = await db.execute(select(Event).where(Event.event_id == event_id))
    return result.scalar_one_or_none()


async def get_event_by_name(db: AsyncSession, name: str) -> Event | None:
    result = await db.execute(select(Event).where(Event.name == name))
    return result.scalar_one_or_none()


async def create_event_crud(db: AsyncSession, event: Event) -> Event:
    db.add(event)
    await db.commit()
    await db.refresh(event)
    # 显式加载 region 和 season
    result = await db.execute(
        select(Event)
        .options(selectinload(Event.region), selectinload(Event.season))
        .where(Event.id == event.id)
    )
    return result.scalar_one()


async def update_event_crud(db: AsyncSession, event: Event, update_data: dict):
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
) -> List[Event]:
    stmt = select(Event).options(
        selectinload(Event.region),
        selectinload(Event.season)
    ).join(Event.region).join(Event.season)

    if season_name:
        stmt = stmt.filter(func.lower(Season.name).contains(season_name.lower()))
    if region_name:
        stmt = stmt.filter(func.lower(Region.name).contains(region_name.lower()))
    if sport_type:
        stmt = stmt.filter(func.lower(Season.sport_type).contains(sport_type.lower()))
    if event_name:
        stmt = stmt.filter(func.lower(Event.name).contains(event_name.lower()))

    stmt = stmt.order_by(Event.created_at.asc()).offset((page - 1) * size).limit(size)

    result = await db.execute(stmt)
    return result.scalars().all()


async def get_track_by_track_id(db: AsyncSession, track_id: str) -> Track | None:
    result = await db.execute(select(Track).where(Track.track_id == track_id))
    return result.scalar_one_or_none()


async def get_track_by_name(db: AsyncSession, name: str) -> Event | None:
    result = await db.execute(select(Track).where(Track.name == name))
    return result.scalar_one_or_none()


async def create_track_crud(db: AsyncSession, track: Track) -> Track:
    db.add(track)
    await db.commit()
    await db.refresh(track)
    # 显式加载 region 和 season
    result = await db.execute(
        select(Track)
        .options(selectinload(Track.event))
        .where(Track.id == track.id)
    )
    return result.scalar_one()


async def update_track_crud(db: AsyncSession, track: Track, update_data: dict):
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
) -> List[Track]:
    stmt = select(Track).options(
        selectinload(Track.event).selectinload(Event.season),
        selectinload(Track.event).selectinload(Event.region)
    ).join(Track.event).join(Event.season).join(Event.region)

    if event_name:
        stmt = stmt.filter(func.lower(Event.name).contains(event_name.lower()))
    if season_name:
        stmt = stmt.filter(func.lower(Season.name).contains(season_name.lower()))
    if region_name:
        stmt = stmt.filter(func.lower(Region.name).contains(region_name.lower()))
    if sport_type:
        stmt = stmt.filter(func.lower(Season.sport_type).contains(sport_type.lower()))
    if track_name:
        stmt = stmt.filter(func.lower(Track.name).contains(track_name.lower()))

    stmt = stmt.order_by(Track.created_at.asc()).offset((page - 1) * size).limit(size)

    result = await db.execute(stmt)
    return result.scalars().all()