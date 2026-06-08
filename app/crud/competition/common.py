from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy import select, func
from geoalchemy2.functions import ST_Contains
from geoalchemy2 import WKTElement
from app.db.models.competition import Region, BikeEvent, BikeTrack, RunningEvent, RunningTrack
from app.db.models.training import UserGridFamiliarityBike
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone
from typing import Optional, List
import uuid


async def get_region_ids_with_playable_tracks(db: AsyncSession, country_code: str, sport_type: str) -> List[str]:
    """返回该国家下、存在「可玩 track」的 region_id（去重）。
    可玩 track：track.start_date < now < track.end_date，且挂在进行中的 event 下。
    用 Region→Event→Track 的连接 + distinct 一次查出，避免懒加载 N+1。"""
    if sport_type == "bike":
        Event, Track = BikeEvent, BikeTrack
    elif sport_type == "running":
        Event, Track = RunningEvent, RunningTrack
    else:
        return []
    now = datetime.now(timezone.utc)
    stmt = (
        select(Region.region_id)
        .join(Event, Event.region_id == Region.id)
        .join(Track, Track.event_id == Event.id)
        .where(
            Region.country_code == country_code,
            Event.start_date <= now,
            Event.end_date >= now,
            Track.start_date < now,
            Track.end_date > now,
        )
        .distinct()
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())



async def create_region_crud(db: AsyncSession, region: Region):
    db.add(region)
    await db.flush()

async def get_region_by_coordinate(db: AsyncSession, lat: float, lon: float) -> Region | None:
    point = WKTElement(f'POINT({lon} {lat})', srid=4326)
    stmt = (
        select(Region)
        .where(ST_Contains(Region.boundary, point))
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def get_region_by_id(db: AsyncSession, region_id: uuid.UUID) -> Region | None:
    result = await db.execute(select(Region).where(Region.id == region_id))
    return result.scalar_one_or_none()

async def get_region_by_region_id(db: AsyncSession, region_id: str) -> Region | None:
    result = await db.execute(select(Region).where(Region.region_id == region_id))
    return result.scalar_one_or_none()

async def get_regions_by_country_code(db: AsyncSession, country_code: str) -> List[Region]:
    stmt = (
        select(Region)
        .where(Region.country_code == country_code)
        .options(
            selectinload(Region.bike_events),
            selectinload(Region.running_events)
        )
    )
    result = await db.execute(stmt)
    return result.scalars().all()

async def get_region_boundary_geojson_by_region_id(
    db: AsyncSession,
    region_id: str
) -> dict | None:
    result = await db.execute(
        select(
            func.json_build_object(
                'type', 'Feature',
                'geometry',
                func.ST_AsGeoJSON(
                    func.ST_Simplify(Region.boundary, 0.0001)
                ).cast(JSON),
                'properties',
                func.json_build_object()
            )
        ).where(Region.region_id == region_id)
    )
    return result.scalar_one_or_none()
