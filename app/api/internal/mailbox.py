from app.schemas.base import BaseResponse
from app.services.mailbox import send_mail_service
from app.schemas.mailbox import (
    MailCreateForm
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