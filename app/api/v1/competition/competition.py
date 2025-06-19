from fastapi import APIRouter, Depends, File, UploadFile, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.base import BaseResponse
from app.schemas.competition import SeasonBaseInfo, RegionsResponse
from app.schemas.user import AuthContext
from app.services.competition.common import query_current_season_service, query_regions_with_events
from app.api.deps import get_current_user
from typing import Optional


router = APIRouter()

# 查询赛季
@router.get("/query_season", response_model=BaseResponse[SeasonBaseInfo], summary="查询赛季")
async def query_season(
    sport_type: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    season = await query_current_season_service(
        db=db,
        sport_type=sport_type
    )
    return BaseResponse.success(data=season)


# 查询有赛事的地区
@router.get("/query_regions", response_model=BaseResponse[RegionsResponse], summary="查询有赛事的区域")
async def query_regions(
    sport_type: str = Query(...),
    country_code: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    regions = await query_regions_with_events(db, sport_type, country_code)
    return BaseResponse.success(data=RegionsResponse(regions_with_events=regions))