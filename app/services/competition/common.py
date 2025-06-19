from app.crud.competition.common import (
    create_season_crud,
    get_season_by_name_and_sport_type,
    get_season_by_season_id,
    update_season_crud, 
    get_region_by_name,
    create_region_crud, get_season_now_by_sport,
    get_regions_by_country_code
)
from app.core.errors import ErrorCode
from app.schemas.base import BizException
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.competition import (
    SeasonCreateForm,
    RegionCreate, SeasonBaseInfo,
)
from app.db.models import Season, Region
from typing import Optional, List
import uuid


async def create_season_service(db: AsyncSession, season_create: SeasonCreateForm, image_url: str) -> SeasonBaseInfo:
    season = await get_season_by_name_and_sport_type(db, season_create.name, season_create.sport_type.value)
    if season is not None:
        raise BizException(code=ErrorCode.SEASON_ALREADY_EXIST, message="赛季已存在，不可重复创建")
    season_id = f"season_{str(uuid.uuid4())[:8]}"
    new_season = Season(
        season_id=season_id,
        name=season_create.name,
        start_date=season_create.start_date,
        end_date=season_create.end_date,
        sport_type=season_create.sport_type,
        image_url=image_url
    )
    res = await create_season_crud(db, new_season)
    return SeasonBaseInfo(
        season_id=res.season_id,
        name=res.name,
        start_date=res.start_date.isoformat(),
        end_date=res.end_date.isoformat(),
        image_url=res.image_url
    )


async def update_season_image_url(db: AsyncSession, season_id: str, image_url: str):
    existing_season = await get_season_by_season_id(db, season_id)
    if existing_season is None:
        raise BizException(code=ErrorCode.SEASON_NOT_FOUND, message="赛季不存在")
    update_data = {
        "image_url": image_url
    }
    await update_season_crud(db, existing_season, update_data)


async def query_current_season_service(db: AsyncSession, sport_type: str) -> SeasonBaseInfo:
    seasons = await get_season_now_by_sport(db, sport_type)
    if not seasons:
        raise BizException(code=ErrorCode.SEASON_NOT_FOUND, message="当前没有进行中的赛季")
    if len(seasons) > 1:
        raise BizException(code=ErrorCode.SEASON_NOT_UNIQUE, message="当前时间存在多个进行中的赛季")
    season: Season = seasons[0]
    return SeasonBaseInfo(
        season_id=season.season_id,
        name=season.name,
        start_date=season.start_date.isoformat(),
        end_date=season.end_date.isoformat(),
        image_url=season.image_url
    )


async def create_region_service(db: AsyncSession, region_create: RegionCreate):
    region = await get_region_by_name(db, region_create.name)
    if region is not None:
        raise BizException(code=ErrorCode.REGION_ALREADY_EXIST, message="地理区域已存在，不可重复创建")
    new_region = Region(
        name=region_create.name
    )
    await create_region_crud(db, new_region)


async def query_regions_with_events(db: AsyncSession, sport_type: str, country_code: str) -> List[str]:
    regions = await get_regions_by_country_code(db, country_code)
    if not regions:
        raise BizException(code=ErrorCode.REGION_NOT_FOUND, message="该国家地区暂无赛事")
    result = []
    for region in regions:
        if sport_type == "bike" and region.bike_events:
            if len(region.bike_events) > 0:
                result.append(region.name)
        elif sport_type == "running" and region.running_events:
            if len(region.running_events) > 0:
                result.append(region.name)
    return result