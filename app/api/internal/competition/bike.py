from fastapi import APIRouter, Depends, File, UploadFile, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.base import BaseResponse, BizException
from app.schemas.user import AuthContext
from app.schemas.competition.bike import (
    BikeEventCreateForm, BikeTrackCreateForm, BikeEventUpdateForm, 
    BikeTrackUpdateForm, BikeEventListInternalResponse, BikeTrackListInternalResponse,
    BikeSeasonCreateForm, BikeUnverifiedRecordResponse
)
from app.services.competition.bike import (
    create_event_service, create_track_service, query_unverified_records_service,
    update_event_service, update_track_service, handle_record_verified_service,
    update_event_image_url, update_track_image_url,
    query_events_service, query_tracks_service,
    create_season_service, update_season_image_url, settle_bike_leaderboard_service
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
    image_url = "/resources/placeholder/season.jpg"
    new_season_id = await create_season_service(db, season, image_url)

    if season_image:
        season_folder = Path(f"resources/competition/bike/season") / new_season_id
        season_folder.mkdir(parents=True, exist_ok=True)
        for file in season_folder.glob("background_*.jpg"):
            file.unlink(missing_ok=True)
        background_path = season_folder / f"background_{int(datetime.now().timestamp())}.jpg"
        contents = await season_image.read()
        if len(contents) > 2 * 1024 * 1024:  # 超过 2MB
            raise BizException(code=ErrorCode.IMAGE_UPLOAD_OVERSIZE, message="image.over_size")
        with background_path.open("wb") as f:
            f.write(contents)
        new_url = f"/resources/competition/bike/season/{new_season_id}/{background_path.name}"
        await update_season_image_url(db, new_season_id, new_url)
    return BaseResponse.success(token=auth.new_token, message="success", data=None)


# bike创建新赛事
@router.post("/create_event", response_model=BaseResponse[None], summary="创建新bike赛事")
async def create_event(
    event: BikeEventCreateForm = Depends(),
    event_image: Optional[UploadFile] = File(None),
    auth: AuthContext = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    image_url = "/resources/placeholder/event.jpg"
    new_event_id = await create_event_service(db, event, image_url)

    if event_image:
        event_folder = Path("resources/competition/bike/event") / new_event_id
        event_folder.mkdir(parents=True, exist_ok=True)
        for file in event_folder.glob("background_*.png"):
            file.unlink(missing_ok=True)
        background_path = event_folder / f"background_{int(datetime.now().timestamp())}.png"
        contents = await event_image.read()
        if len(contents) > 2 * 1024 * 1024:  # 超过 2MB
            raise BizException(code=ErrorCode.IMAGE_UPLOAD_OVERSIZE, message="image.over_size")
        with background_path.open("wb") as f:
            f.write(contents)
        new_url = f"/resources/competition/bike/event/{new_event_id}/{background_path.name}"
        await update_event_image_url(db, new_event_id, new_url)
    elif event.image_url:
        # 校验 image_url 指向的文件是否真实存在
        image_path = Path(event.image_url.lstrip("/"))
        if not image_path.exists() or not image_path.is_file():
            raise BizException(code=ErrorCode.FILE_NOT_FOUND, message="找不到文件")
        await update_event_image_url(db, new_event_id, event.image_url)
    return BaseResponse.success(token=auth.new_token, message="success", data=None)


# bike更新赛事
@router.post("/update_event", response_model=BaseResponse[None], summary="更新bike赛事")
async def update_event(
    event: BikeEventUpdateForm = Depends(),
    event_image: Optional[UploadFile] = File(None),
    auth: AuthContext = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    image_url = "/resources/placeholder/event.jpg"
    if event_image:
        event_folder = Path("resources/competition/bike/event") / event.event_id
        event_folder.mkdir(parents=True, exist_ok=True)
        for file in event_folder.glob("background_*.png"):
            file.unlink(missing_ok=True)
        bg_path = event_folder / f"background_{int(datetime.now().timestamp())}.png"
        contents = await event_image.read()
        if len(contents) > 2 * 1024 * 1024:  # 超过 2MB
            raise BizException(code=ErrorCode.IMAGE_UPLOAD_OVERSIZE, message="image.over_size")
        with bg_path.open("wb") as f:
            f.write(contents)
        image_url = f"/resources/competition/bike/event/{event.event_id}/{bg_path.name}"
    await update_event_service(db, event, image_url)
    return BaseResponse.success(token=auth.new_token, message="success", data=None)


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
    image_url = "/resources/placeholder/track.jpg"
    new_track_id = await create_track_service(db, track, image_url)

    if track_image:
        track_folder = Path("resources/competition/bike/track") / new_track_id
        track_folder.mkdir(parents=True, exist_ok=True)
        for file in track_folder.glob("background_*.png"):
            file.unlink(missing_ok=True)
        background_path = track_folder / f"background_{int(datetime.now().timestamp())}.png"
        contents = await track_image.read()
        if len(contents) > 2 * 1024 * 1024:  # 超过 2MB
            raise BizException(code=ErrorCode.IMAGE_UPLOAD_OVERSIZE, message="image.over_size")
        with background_path.open("wb") as f:
            f.write(contents)
        new_url = f"/resources/competition/bike/track/{new_track_id}/{background_path.name}"
        await update_track_image_url(db, new_track_id, new_url)

    return BaseResponse.success(token=auth.new_token, message="success", data=None)


# bike更新赛道
@router.post("/update_track", response_model=BaseResponse[None], summary="更新bike赛道")
async def update_track(
    track: BikeTrackUpdateForm = Depends(),
    track_image: Optional[UploadFile] = File(None),
    auth: AuthContext = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    image_url = "/resources/placeholder/track.jpg"
    if track_image:
        track_folder = Path("resources/competition/bike/track") / track.track_id
        track_folder.mkdir(parents=True, exist_ok=True)
        for file in track_folder.glob("background_*.png"):
            file.unlink(missing_ok=True)
        bg_path = track_folder / f"background_{int(datetime.now().timestamp())}.png"
        contents = await track_image.read()
        if len(contents) > 2 * 1024 * 1024:  # 超过 2MB
            raise BizException(code=ErrorCode.IMAGE_UPLOAD_OVERSIZE, message="image.over_size")
        with bg_path.open("wb") as f:
            f.write(contents)
        image_url = f"/resources/competition/bike/track/{track.track_id}/{bg_path.name}"
    await update_track_service(db, track, image_url)

    return BaseResponse.success(token=auth.new_token, message="success", data=None)


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

# bike赛道排行榜数据的结算和存档，包括voucher奖池结算（通过邮箱发放）、积分的结算（直接写表）以及leaderboard数据存表
@router.post("/settle_leaderboard", response_model=BaseResponse[None], summary="结算bike赛道排行榜")
async def settle_leaderboard(
    track_id: str = Query(...),
    auth: AuthContext = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    male_settled, male_sum, female_settled, female_sum, voucher = await settle_bike_leaderboard_service(db, track_id)
    return BaseResponse.success(token=auth.new_token, message=f"结算完成，共结算男{male_settled}/{male_sum}人，女{female_settled}/{female_sum}人，金券{voucher}张")

# 查询待校验记录
@router.get("/query_unverified_records", response_model=BaseResponse[BikeUnverifiedRecordResponse], summary="查询待校验记录")
async def query_unverified_records(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1),
    auth: AuthContext = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await query_unverified_records_service(db, page, size)
    return BaseResponse.success(token=auth.new_token, data=result)

# 手动校验record数据
@router.post("/handle_unverified_record", response_model=BaseResponse[None], summary="手动校验record数据")
async def handle_unverified_record(
    record_id: str = Query(...),
    result: bool = Query(...),
    auth: AuthContext = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    await handle_record_verified_service(db, record_id, result)
    return BaseResponse.success(token=auth.new_token, message="success")