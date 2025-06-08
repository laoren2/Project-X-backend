from app.crud.competition import (
    create_season_crud,
    get_event_by_event_id,
    get_season_by_name_and_sport_type,
    get_season_by_season_id,
    update_season_crud,
    get_region_by_name,
    create_event_crud,
    update_event_crud,
    query_events_crud,
    create_region_crud
)
from app.core.errors import ErrorCode
from app.schemas.base import BizException
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.competition import SeasonCreateForm, EventCreateForm, EventBaseInfo, EventUpdateForm, RegionCreate, SeasonBaseInfo
from app.db.models import Season, Event, Region
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
        sport_type=res.sport_type,
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


async def create_region_service(db: AsyncSession, region_create: RegionCreate):
    region = await get_region_by_name(db, region_create.name)
    if region is not None:
        raise BizException(code=ErrorCode.REGION_ALREADY_EXIST, message="地理区域已存在，不可重复创建")
    new_region = Region(
        name=region_create.name
    )
    await create_region_crud(db, new_region)


async def create_event_service(db: AsyncSession, event: EventCreateForm, image_url: str) -> EventBaseInfo:
    region = await get_region_by_name(db, event.region_name)
    if region is None:
        raise BizException(code=ErrorCode.REGION_NOT_FOUND, message="地理区域不存在")

    season = await get_season_by_name_and_sport_type(db, event.season_name, event.sport_type.value)
    if season is None:
        raise BizException(code=ErrorCode.SEASON_NOT_FOUND, message="赛季不存在")

    event_id = f"event_{str(uuid.uuid4())[:8]}"
    new_event = Event(
        event_id=event_id,
        name=event.name,
        description=event.description,
        start_date=event.start_date,
        end_date=event.end_date,
        region_id=region.id,
        season_id=season.id,
        image_url=image_url
    )
    res = await create_event_crud(db, new_event)
    return EventBaseInfo(
        event_id=res.event_id,
        name=res.name,
        description=res.description,
        start_date=res.start_date.isoformat(),
        end_date=res.end_date.isoformat(),
        region_name=res.region.name,
        season_name=res.season.name,
        sport_type=res.season.sport_type,
        image_url=res.image_url
    )


async def update_event_service(db: AsyncSession, event: EventUpdateForm, image_url: str):
    existing_event = await get_event_by_event_id(db, event.event_id)
    if existing_event is None:
        raise BizException(code=ErrorCode.EVENT_NOT_FOUND, message="赛事不存在")
    update_data = {
        "name": event.name,
        "description": event.description,
        "start_date": event.start_date,
        "end_date": event.end_date,
        "image_url": image_url
    }
    await update_event_crud(db, existing_event, update_data)


async def update_event_image_url(db: AsyncSession, event_id: str, image_url: str):
    existing_event = await get_event_by_event_id(db, event_id)
    if existing_event is None:
        raise BizException(code=ErrorCode.EVENT_NOT_FOUND, message="赛事不存在")
    update_data = {
        "image_url": image_url
    }
    await update_event_crud(db, existing_event, update_data)


async def query_events_service(
    db: AsyncSession,
    season_name: Optional[str],
    region_name: Optional[str],
    sport_type: Optional[str],
    event_name: Optional[str],
    page: int,
    size: int
) -> List[EventBaseInfo]:
    events = await query_events_crud(
        db=db,
        season_name=season_name,
        region_name=region_name,
        sport_type=sport_type,
        event_name=event_name,
        page=page,
        size=size
    )
    return [EventBaseInfo(
        event_id=e.event_id,
        name=e.name,
        description=e.description,
        start_date=e.start_date.isoformat(),
        end_date=e.end_date.isoformat(),
        season_name=e.season.name,
        region_name=e.region.name,
        sport_type=e.season.sport_type,
        image_url=e.image_url
    ) for e in events]