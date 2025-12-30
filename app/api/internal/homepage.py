from app.schemas.base import BaseResponse, BizException
from app.services.homepage import (
    update_announcements_service, create_banner_ad_service
)
from app.schemas.homepage import (
    AnnouncementUpdateForm, AdCreateForm
)
from app.schemas.user import AuthContext
from fastapi import APIRouter, Depends, Query, UploadFile, File
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.deps import get_current_admin
from datetime import datetime
from app.core.errors import ErrorCode
import uuid

router = APIRouter()


@router.post("/update_announcements", response_model=BaseResponse[None], summary="更新公告")
async def update_announcements(
    form: AnnouncementUpdateForm,
    auth: AuthContext = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    await update_announcements_service(db, form.content)
    return BaseResponse.success(token=auth.new_token, message="success")

@router.post("/create_banner_ad", response_model=BaseResponse[None], summary="创建首页轮播图")
async def create_banner_ad(
    form: AdCreateForm = Depends(AdCreateForm.as_form),
    image: UploadFile = File(...),
    auth: AuthContext = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    cpasset_folder = Path("resources/homepage/banner")
    cpasset_folder.mkdir(parents=True, exist_ok=True)
    ad_path = cpasset_folder / f"ad_{int(datetime.now().timestamp())}.jpg"
    contents = await image.read()
    if len(contents) > 0.5 * 1024 * 1024:  # 超过 512KB
        raise BizException(code=ErrorCode.IMAGE_UPLOAD_OVERSIZE, message="image.over_size")
    with ad_path.open("wb") as f:
        f.write(contents)
    new_url = f"/resources/homepage/banner/{ad_path.name}"

    await create_banner_ad_service(db, form, new_url)
    return BaseResponse.success(token=auth.new_token, message="success")