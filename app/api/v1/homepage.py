from app.schemas.base import BaseResponse
from app.services.homepage import (
    query_annoucements_service, query_banner_ads_service
)
from app.schemas.homepage import (
    AnnouncementInfoResponse, BannerAdsInfoResponse
)
from app.db.session import get_db
from app.api.deps import get_language, Language
from fastapi import APIRouter, Depends, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

router = APIRouter(dependencies=[Depends(get_language)])


@router.get("/query_announcements", response_model=BaseResponse[AnnouncementInfoResponse], summary="查询公告")
async def query_announcements(
    lang: Language = Depends(get_language),
    db: AsyncSession = Depends(get_db)
):
    results = await query_annoucements_service(db, lang)
    return BaseResponse.success(data=results)

@router.get("/query_banner_ads", response_model=BaseResponse[BannerAdsInfoResponse], summary="查询首页轮播信息")
async def query_banner_ads(
    db: AsyncSession = Depends(get_db)
):
    results = await query_banner_ads_service(db)
    return BaseResponse.success(data=results)