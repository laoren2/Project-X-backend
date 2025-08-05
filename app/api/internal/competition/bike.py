from fastapi import APIRouter, Depends, File, UploadFile, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.base import BaseResponse
from app.schemas.user import AuthContext
from app.schemas.competition.bike import (
    BikeEventCreateForm, BikeTrackCreateForm, BikeEventUpdateForm, 
    BikeTrackUpdateForm, BikeEventListInternalResponse, BikeTrackListInternalResponse,
    BikeSeasonCreateForm
)
from app.services.competition.bike import (
    create_event_service, create_track_service,
    update_event_service, update_track_service,
    update_event_image_url, update_track_image_url,
    query_events_service, query_tracks_service,
    create_season_service, update_season_image_url
)
from app.core.errors import ErrorCode
from app.api.deps import get_current_admin
from typing import Optional
from pathlib import Path
from datetime import datetime


router = APIRouter()


# 创建Bike新赛季
@router.post("/create_season", response_model=BaseResponse[None], summary="创建Bike新赛季")
async def create_season(
    season: BikeSeasonCreateForm = Depends(),
    season_image: Optional[UploadFile] = File(None),
    auth: AuthContext = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    image_url = "/resources/placeholder/season.png"
    new_season = await create_season_service(db, season, image_url)

    if season_image:
        season_folder = Path(f"resources/competition/bike/season") / new_season.season_id
        season_folder.mkdir(parents=True, exist_ok=True)
        for file in season_folder.glob("background_*.jpg"):
            file.unlink(missing_ok=True)
        background_path = season_folder / f"background_{int(datetime.now().timestamp())}.jpg"
        contents = await season_image.read()
        if len(contents) > 2 * 1024 * 1024:  # 超过 2MB
            return BaseResponse.error(code=ErrorCode.IMAGE_UPLOAD_OVERSIZE, message="上传图片体积超过限制")
        with background_path.open("wb") as f:
            f.write(contents)
        new_url = f"/resources/competition/bike/season/{new_season.season_id}/{background_path.name}"
        await update_season_image_url(db, new_season.season_id, new_url)
    return BaseResponse.success(token=auth.new_token, message=f"成功创建bike:{season.name}", data=None)


# bike创建新赛事
@router.post("/create_event", response_model=BaseResponse[None], summary="创建新bike赛事")
async def create_event(
    event: BikeEventCreateForm = Depends(),
    event_image: Optional[UploadFile] = File(None),
    auth: AuthContext = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    image_url = "/resources/placeholder/event.png"
    new_event = await create_event_service(db, event, image_url)

    if event_image:
        event_folder = Path("resources/competition/bike/event") / new_event.event_id
        event_folder.mkdir(parents=True, exist_ok=True)
        for file in event_folder.glob("background_*.jpg"):
            file.unlink(missing_ok=True)
        background_path = event_folder / f"background_{int(datetime.now().timestamp())}.jpg"
        contents = await event_image.read()
        if len(contents) > 2 * 1024 * 1024:  # 超过 2MB
            return BaseResponse.error(code=ErrorCode.IMAGE_UPLOAD_OVERSIZE, message="上传图片体积超过限制")
        with background_path.open("wb") as f:
            f.write(contents)
        new_url = f"/resources/competition/bike/event/{new_event.event_id}/{background_path.name}"
        await update_event_image_url(db, new_event.event_id, new_url)

    return BaseResponse.success(token=auth.new_token, message=f"成功创建bike赛事:{event.name}", data=None)


# bike更新赛事
@router.post("/update_event", response_model=BaseResponse[None], summary="更新bike赛事")
async def update_event(
    event: BikeEventUpdateForm = Depends(),
    event_image: Optional[UploadFile] = File(None),
    auth: AuthContext = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    image_url = "/resources/placeholder/event.png"
    if event_image:
        event_folder = Path("resources/competition/bike/event") / event.event_id
        event_folder.mkdir(parents=True, exist_ok=True)
        for file in event_folder.glob("background_*.jpg"):
            file.unlink(missing_ok=True)
        bg_path = event_folder / f"background_{int(datetime.now().timestamp())}.jpg"
        contents = await event_image.read()
        if len(contents) > 2 * 1024 * 1024:  # 超过 2MB
            return BaseResponse.error(code=ErrorCode.IMAGE_UPLOAD_OVERSIZE, message="上传图片体积超过限制")
        with bg_path.open("wb") as f:
            f.write(contents)
        image_url = f"/resources/competition/bike/event/{event.event_id}/{bg_path.name}"
    await update_event_service(db, event, image_url)

    return BaseResponse.success(token=auth.new_token, message=f"成功更新bike赛事:{event.name}", data=None)


# bike查询赛事
@router.get("/query_events", response_model=BaseResponse[BikeEventListInternalResponse], summary="查询bike赛事")
async def query_events(
    season_name: Optional[str] = Query(None),
    region_name: Optional[str] = Query(None),
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
        event_name=event_name,
        page=page,
        size=size
    )
    return BaseResponse.success(token=auth.new_token, data=BikeEventListInternalResponse(events=events))


# bike创建新赛道
@router.post("/create_track", response_model=BaseResponse[None], summary="创建新bike赛道")
async def create_track(
    track: BikeTrackCreateForm = Depends(),
    track_image: Optional[UploadFile] = File(None),
    auth: AuthContext = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    image_url = "/resources/placeholder/track.png"
    new_track = await create_track_service(db, track, image_url)

    if track_image:
        track_folder = Path("resources/competition/bike/track") / new_track.track_id
        track_folder.mkdir(parents=True, exist_ok=True)
        for file in track_folder.glob("background_*.jpg"):
            file.unlink(missing_ok=True)
        background_path = track_folder / f"background_{int(datetime.now().timestamp())}.jpg"
        contents = await track_image.read()
        if len(contents) > 2 * 1024 * 1024:  # 超过 2MB
            return BaseResponse.error(code=ErrorCode.IMAGE_UPLOAD_OVERSIZE, message="上传图片体积超过限制")
        with background_path.open("wb") as f:
            f.write(contents)
        new_url = f"/resources/competition/bike/track/{new_track.track_id}/{background_path.name}"
        await update_track_image_url(db, new_track.track_id, new_url)

    return BaseResponse.success(token=auth.new_token, message=f"成功创建bike赛道:{track.name}", data=None)


# bike更新赛道
@router.post("/update_track", response_model=BaseResponse[None], summary="更新bike赛道")
async def update_track(
    track: BikeTrackUpdateForm = Depends(),
    track_image: Optional[UploadFile] = File(None),
    auth: AuthContext = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    image_url = "/resources/placeholder/track.png"
    if track_image:
        track_folder = Path("resources/competition/bike/track") / track.track_id
        track_folder.mkdir(parents=True, exist_ok=True)
        for file in track_folder.glob("background_*.jpg"):
            file.unlink(missing_ok=True)
        bg_path = track_folder / f"background_{int(datetime.now().timestamp())}.jpg"
        contents = await track_image.read()
        if len(contents) > 2 * 1024 * 1024:  # 超过 2MB
            return BaseResponse.error(code=ErrorCode.IMAGE_UPLOAD_OVERSIZE, message="上传图片体积超过限制")
        with bg_path.open("wb") as f:
            f.write(contents)
        image_url = f"/resources/competition/bike/track/{track.track_id}/{bg_path.name}"
    await update_track_service(db, track, image_url)

    return BaseResponse.success(token=auth.new_token, message=f"成功更新bike赛道:{track.name}", data=None)


# bike查询赛道
@router.get("/query_tracks", response_model=BaseResponse[BikeTrackListInternalResponse], summary="查询bike赛道")
async def query_tracks(
    track_name: Optional[str] = Query(None),
    event_name: Optional[str] = Query(None),
    season_name: Optional[str] = Query(None),
    region_name: Optional[str] = Query(None),
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
        page=page,
        size=size
    )
    return BaseResponse.success(token=auth.new_token, data=BikeTrackListInternalResponse(tracks=tracks))