from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_
from app.db.models.competition import Region
from sqlalchemy.orm import selectinload
from typing import Optional, List
import uuid



async def create_region_crud(db: AsyncSession, region: Region):
    db.add(region)
    await db.flush()

async def get_region_by_name(db: AsyncSession, name: str) -> Region | None:
    result = await db.execute(select(Region).where(Region.name == name))
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
