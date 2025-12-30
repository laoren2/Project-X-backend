from app.schemas.base import BaseResponse
from app.services.mailbox import (
    send_mail_service, query_feedback_mails_service, handle_feedback_mail_service
)
from app.schemas.mailbox import (
    MailCreateForm, FeedbackMailInfoResponse
)
from app.schemas.user import AuthContext
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.deps import get_current_admin

router = APIRouter()


@router.post("/send_mail", response_model=BaseResponse[None], summary="发送邮件")
async def send_mail(
    create_info: MailCreateForm,
    auth: AuthContext = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    await send_mail_service(create_info, auth.payload["user_id"], db)
    return BaseResponse.success(token=auth.new_token)

@router.get("/query_feedback_mails", response_model=BaseResponse[FeedbackMailInfoResponse], summary="查询反馈邮件")
async def query_feedback_mails(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1),
    auth: AuthContext = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    results = await query_feedback_mails_service(db, page, size)
    return BaseResponse.success(token=auth.new_token, message="success", data=results)

@router.post("/handle_feedback_mail", response_model=BaseResponse[None], summary="处理反馈邮件")
async def handle_feedback_mail(
    mail_id: str = Query(...),
    auth: AuthContext = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    await handle_feedback_mail_service(db, mail_id)
    return BaseResponse.success(token=auth.new_token, message="success")
