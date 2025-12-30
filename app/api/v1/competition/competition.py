from fastapi import APIRouter, Depends, File, UploadFile, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.base import BaseResponse
from app.schemas.competition.common import RegionsResponse, RegionResponse
from app.schemas.user import AuthContext
from app.services.competition.common import query_regions_with_events_service, query_region_with_coordinate_service
from app.api.deps import get_current_user, get_language
from typing import Optional


router = APIRouter(dependencies=[Depends(get_language)])


# 查询有赛事的地区
@router.get("/query_regions_with_events", response_model=BaseResponse[RegionsResponse], summary="查询有赛事的区域")
async def query_regions_with_events(
    sport_type: str = Query(...),
    country_code: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    regions = await query_regions_with_events_service(db, sport_type, country_code)
    return BaseResponse.success(data=RegionsResponse(regions_with_events=regions))
    
# 查询坐标对应的地区
@router.get("/query_region_id", response_model=BaseResponse[RegionResponse], summary="查询坐标对应的地区")
async def query_region_id(
    lat: float = Query(...),
    lon: float = Query(...),
    db: AsyncSession = Depends(get_db)
):
    result = await query_region_with_coordinate_service(db, lat, lon)
    return BaseResponse.success(data=result)