from app.schemas.asset import AssetRewardsResponse
from app.schemas.base import BaseResponse
from app.services.mailbox import (
    get_mail_unread_status_service, get_mails_service, get_mail_detail_service,
    receive_mail_rewards_service
)
from app.schemas.mailbox import (
    MailUnreadStatusResponse, MailDetailResponse, MailInfoResponse, MailCreateForm
)
from app.schemas.user import AuthContext
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.deps import get_current_user

router = APIRouter()


@router.get("/query_unread_status", response_model=BaseResponse[MailUnreadStatusResponse], summary="查询邮箱未读状态")
async def get_mail_unread_status(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await get_mail_unread_status_service(db, auth.payload["user_id"])
    return BaseResponse.success(token=auth.new_token, data=result)

@router.get("/query_mails", response_model=BaseResponse[MailInfoResponse], summary="分页查询邮件")
async def query_mails(
    page: int = Query(...),
    size: int = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await get_mails_service(page, size, auth.payload["user_id"], db)
    return BaseResponse.success(token=auth.new_token, data=result)

@router.get("/query_mail_detail", response_model=BaseResponse[MailDetailResponse], summary="查询邮件详情")
async def query_mail_detail(
    mail_id: str = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await get_mail_detail_service(mail_id, auth.payload["user_id"], db)
    return BaseResponse.success(token=auth.new_token, data=result)

@router.post("/receive_mail_rewards", response_model=BaseResponse[AssetRewardsResponse], summary="领取邮件中的奖励")
async def receive_mail_rewards(
    mail_id: str = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await receive_mail_rewards_service(mail_id, auth.payload["user_id"], db)
    return BaseResponse.success(token=auth.new_token, data=result)