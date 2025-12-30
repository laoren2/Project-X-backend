from app.schemas.asset import AssetRewardsResponse
from app.schemas.base import BaseResponse, BizException
from app.services.mailbox import (
    get_mail_unread_status_service, get_mails_service, get_mail_detail_service,
    receive_mail_rewards_service, commit_feedback_service
)
from app.schemas.mailbox import (
    MailUnreadStatusResponse, MailDetailResponse, MailInfoResponse, MailCreateForm,
    FeedbackMailCreateForm
)
from app.core.errors import ErrorCode
from app.schemas.user import AuthContext
from app.db.session import get_db
from app.api.deps import get_current_user, get_language
from fastapi import APIRouter, Depends, Query, UploadFile, File
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

router = APIRouter(dependencies=[Depends(get_language)])


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

@router.post("/commit_feedback", response_model=BaseResponse[None], summary="提交反馈")
async def commit_feedback(
    form: FeedbackMailCreateForm = Depends(FeedbackMailCreateForm.as_form),
    image1: UploadFile | None = File(None),
    image2: UploadFile | None = File(None),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    feedback_id = f"feedback_{str(uuid.uuid4())[:12]}"
    feedback_folder = Path("resources/feedbacks") / feedback_id
    image_url1 = None
    image_url2 = None
    if image1:
        feedback_folder.mkdir(parents=True, exist_ok=True)
        path1 = feedback_folder / "feedback_1.jpg"
        content1 = await image1.read()
        if len(content1) > 0.2 * 1024 * 1024:  # 超过 200KB
            raise BizException(code=ErrorCode.IMAGE_UPLOAD_OVERSIZE, message="image.over_size")
        with path1.open("wb") as f:
            f.write(content1)
        image_url1 = f"/resources/feedbacks/{feedback_id}/{path1.name}"
    if image2:
        feedback_folder.mkdir(parents=True, exist_ok=True)
        path2 = feedback_folder / "feedback_2.jpg"
        content2 = await image2.read()
        if len(content2) > 0.2 * 1024 * 1024:  # 超过 200KB
            raise BizException(code=ErrorCode.IMAGE_UPLOAD_OVERSIZE, message="image.over_size")
        with path2.open("wb") as f:
            f.write(content2)
        image_url2 = f"/resources/feedbacks/{feedback_id}/{path2.name}"
    
    await commit_feedback_service(form, image_url1, image_url2, auth.payload["user_id"], db)
    return BaseResponse.success(token=auth.new_token, message="提交成功，感谢您的支持")
