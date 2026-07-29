from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.schemas.base import BaseResponse
from app.schemas.email_campaign import EmailCampaignInfo
from app.schemas.user import AuthContext
from app.services.email_campaign import (
    create_video_watermark_email_campaign_service,
    get_email_campaign_service,
    start_email_campaign_service,
)


router = APIRouter()


@router.post("/create_video_watermark_feature", response_model=BaseResponse[EmailCampaignInfo], summary="创建视频水印功能宣传邮件活动")
async def create_video_watermark_feature_campaign(
    auth: AuthContext = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await create_video_watermark_email_campaign_service(db, auth.payload["user_id"])
    return BaseResponse.success(token=auth.new_token, data=result)


@router.post("/start", response_model=BaseResponse[EmailCampaignInfo], summary="开始发送邮件群发活动")
async def start_email_campaign(
    campaign_id: str = Query(...),
    auth: AuthContext = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await start_email_campaign_service(db, campaign_id)
    return BaseResponse.success(token=auth.new_token, data=result)


@router.get("/query", response_model=BaseResponse[EmailCampaignInfo], summary="查询邮件群发活动进度")
async def query_email_campaign(
    campaign_id: str = Query(...),
    auth: AuthContext = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await get_email_campaign_service(db, campaign_id)
    return BaseResponse.success(token=auth.new_token, data=result)
