from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy import select, func
from geoalchemy2.functions import ST_Contains
from geoalchemy2 import WKTElement
from app.db.models.competition import Region
from app.db.models.training import UserGridFamiliarityBike
from sqlalchemy.orm import selectinload
from typing import Optional, List
import uuid



async def create_region_crud(db: AsyncSession, region: Region):
    db.add(region)
    await db.flush()

async def get_region_by_name(db: AsyncSession, name: str) -> Region | None:
    result = await db.execute(select(Region).where(Region.name == name))
    return result.scalar_one_or_none()

async def get_region_by_coordinate(db: AsyncSession, lat: float, lon: float) -> Region | None:
    point = WKTElement(f'POINT({lon} {lat})', srid=4326)
    stmt = (
        select(Region)
        .where(ST_Contains(Region.boundary, point))
        .limit(1)
    )
    result = await db.execute(stmt)
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
) -> tuple[Region | None, dict | None]:
    result = await db.execute(
        select(
            Region,
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
    row = result.first()
    if row is None:
        return None, None
    region, boundary_geojson = row
    return region, boundary_geojson
