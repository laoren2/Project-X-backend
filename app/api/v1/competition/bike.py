from fastapi import APIRouter, Depends, File, UploadFile, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.base import BaseResponse
from app.schemas.competition import BikeEventListResponse, BikeTrackListResponse
from app.schemas.user import AuthContext
from app.services.competition.bike import query_events_by_sport_and_region, query_tracks_by_event
from app.api.deps import get_current_user
from typing import Optional


router = APIRouter()

# 查询赛事
@router.get("/query_events", response_model=BaseResponse[BikeEventListResponse], summary="查询bike赛事")
async def query_events(
    region_name: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    events = await query_events_by_sport_and_region(
        db=db,
        region_name=region_name
    )
    return BaseResponse.success(data=BikeEventListResponse(events=events))


# 查询赛道
@router.get("/query_tracks", response_model=BaseResponse[BikeTrackListResponse], summary="查询bike赛道")
async def query_tracks(
    event_id: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    tracks = await query_tracks_by_event(
        db=db,
        event_id=event_id
    )
    return BaseResponse.success(data=BikeTrackListResponse(tracks=tracks))