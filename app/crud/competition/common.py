from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_
from app.db.models import Region, Season
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


async def get_season_now_by_sport(db: AsyncSession, sport_type: str) -> List[Season]:
    # 根据当前的服务器时间和sport_type查询返回满足要求的所有Season
    current_time = func.now()
    stmt = select(Season).where(
        and_(
            Season.sport_type == sport_type,
            Season.start_date <= current_time,
            Season.end_date >= current_time
        )
    )
    result = await db.execute(stmt)
    seasons = result.scalars().all()
    return seasons


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
