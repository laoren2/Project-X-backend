from fastapi import APIRouter, Depends, File, UploadFile, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.base import BaseResponse
from app.schemas.user import AuthContext
from app.schemas.competition import (
    SeasonCreateForm, EventCreateForm, 
    TrackCreateForm, EventUpdateForm, 
    TrackUpdateForm, EventListResponse, 
    TrackListResponse, RegionCreate
)
from app.services.competition import (
    create_season_service, 
    create_event_service, create_track_service,
    update_event_service, update_track_service,
    update_event_image_url, update_track_image_url,
    query_events_service, query_tracks_service,
    create_region_service, 
    update_season_image_url
)
from app.api.deps import get_current_admin
from typing import Optional, List
from pathlib import Path
from datetime import datetime


router = APIRouter()

# 创建新赛季
@router.post("/create_season", response_model=BaseResponse[None], summary="创建新赛季")
async def create_season(
    season: SeasonCreateForm = Depends(),
    season_image: Optional[UploadFile] = File(None),
    auth: AuthContext = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    image_url = "/resources/placeholder/season.png"
    new_season = await create_season_service(db, season, image_url)

    if season_image:
        season_folder = Path("resources/season") / new_season.season_id
        season_folder.mkdir(parents=True, exist_ok=True)
        background_path = season_folder / f"background_{int(datetime.now().timestamp())}.png"
        with background_path.open("wb") as f:
            f.write(await season_image.read())
        new_url = f"/resources/season/{new_season.season_id}/{background_path.name}"
        await update_season_image_url(db, new_season.season_id, new_url)
    return BaseResponse.success(token=auth.new_token, message=f"成功创建{season.sport_type}:{season.name}", data=None)


# 创建新地理区域
@router.post("/create_region", response_model=BaseResponse[None], summary="创建新地理区域")
async def create_region(
    region: RegionCreate,
    auth: AuthContext = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    await create_region_service(db, region)
    return BaseResponse.success(token=auth.new_token, message=f"成功创建区域:{region.name}", data=None)


# 创建新赛事
@router.post("/create_event", response_model=BaseResponse[None], summary="创建新赛事")
async def create_event(
    event: EventCreateForm = Depends(),
    event_image: Optional[UploadFile] = File(None),
    auth: AuthContext = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    image_url = "/resources/placeholder/event.png"
    new_event = await create_event_service(db, event, image_url)

    if event_image:
        event_folder = Path("resources/event") / new_event.event_id
        event_folder.mkdir(parents=True, exist_ok=True)
        background_path = event_folder / f"background_{int(datetime.now().timestamp())}.png"
        with background_path.open("wb") as f:
            f.write(await event_image.read())
        new_url = f"/resources/event/{new_event.event_id}/{background_path.name}"
        await update_event_image_url(db, new_event.event_id, new_url)

    return BaseResponse.success(token=auth.new_token, message=f"成功创建赛事:{event.name}", data=None)


# 更新赛事
@router.post("/update_event", response_model=BaseResponse[None], summary="更新赛事")
async def update_event(
    event: EventUpdateForm = Depends(),
    event_image: Optional[UploadFile] = File(None),
    auth: AuthContext = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    image_url = "/resources/placeholder/event.png"
    if event_image:
        event_folder = Path("resources/event") / event.event_id
        event_folder.mkdir(parents=True, exist_ok=True)
        for file in event_folder.glob("background_*.png"):
            file.unlink(missing_ok=True)
        bg_path = event_folder / f"background_{int(datetime.now().timestamp())}.png"
        with bg_path.open("wb") as f:
            f.write(await event_image.read())
        image_url = f"/resources/event/{event.event_id}/{bg_path.name}"
    await update_event_service(db, event, image_url)

    return BaseResponse.success(token=auth.new_token, message=f"成功更新赛事:{event.name}", data=None)


# 查询赛事
@router.get("/query_events", response_model=BaseResponse[EventListResponse], summary="查询赛事")
async def query_events(
    season_name: Optional[str] = Query(None),
    region_name: Optional[str] = Query(None),
    sport_type: Optional[str] = Query(None),
    event_name: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1),
    auth: AuthContext = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    events = await query_events_service(
        db=db,
        season_name=season_name,
        region_name=region_name,
        sport_type=sport_type,
        event_name=event_name,
        page=page,
        size=size
    )
    return BaseResponse.success(token=auth.new_token, data=EventListResponse(events=events))


# 创建新赛事
@router.post("/create_track", response_model=BaseResponse[None], summary="创建新赛道")
async def create_track(
    track: TrackCreateForm = Depends(),
    track_image: Optional[UploadFile] = File(None),
    auth: AuthContext = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    image_url = "/resources/placeholder/track.png"
    new_track = await create_track_service(db, track, image_url)

    if track_image:
        track_folder = Path("resources/track") / new_track.track_id
        track_folder.mkdir(parents=True, exist_ok=True)
        background_path = track_folder / f"background_{int(datetime.now().timestamp())}.png"
        with background_path.open("wb") as f:
            f.write(await track_image.read())
        new_url = f"/resources/track/{new_track.track_id}/{background_path.name}"
        await update_track_image_url(db, new_track.track_id, new_url)

    return BaseResponse.success(token=auth.new_token, message=f"成功创建赛道:{track.name}", data=None)


# 更新赛事
@router.post("/update_track", response_model=BaseResponse[None], summary="更新赛道")
async def update_track(
    track: TrackUpdateForm = Depends(),
    track_image: Optional[UploadFile] = File(None),
    auth: AuthContext = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    image_url = "/resources/placeholder/track.png"
    if track_image:
        track_folder = Path("resources/track") / track.track_id
        track_folder.mkdir(parents=True, exist_ok=True)
        for file in track_folder.glob("background_*.png"):
            file.unlink(missing_ok=True)
        bg_path = track_folder / f"background_{int(datetime.now().timestamp())}.png"
        with bg_path.open("wb") as f:
            f.write(await track_image.read())
        image_url = f"/resources/track/{track.track_id}/{bg_path.name}"
    await update_track_service(db, track, image_url)

    return BaseResponse.success(token=auth.new_token, message=f"成功更新赛道:{track.name}", data=None)


# 查询赛事
@router.get("/query_tracks", response_model=BaseResponse[TrackListResponse], summary="查询赛道")
async def query_tracks(
    track_name: Optional[str] = Query(None),
    event_name: Optional[str] = Query(None),
    season_name: Optional[str] = Query(None),
    region_name: Optional[str] = Query(None),
    sport_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1),
    auth: AuthContext = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    tracks = await query_tracks_service(
        db=db,
        track_name=track_name,
        event_name=event_name,
        season_name=season_name,
        region_name=region_name,
        sport_type=sport_type,
        page=page,
        size=size
    )
    return BaseResponse.success(token=auth.new_token, data=TrackListResponse(tracks=tracks))