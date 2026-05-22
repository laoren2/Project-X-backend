from app.schemas.base import BaseResponse, BizException
from app.services.homepage import (
    update_announcements_service, create_banner_ad_service
)
from app.services.common import upload_to_oss
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
    image_hans: UploadFile = File(...),
    image_hant: UploadFile = File(...),
    image_en: UploadFile = File(...),
    image_ko: UploadFile = File(...),
    image_ja: UploadFile = File(...),
    auth: AuthContext = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    cpasset_folder = Path("resources/homepage/banner")
    cpasset_folder.mkdir(parents=True, exist_ok=True)
    now_str = f"{int(datetime.now().timestamp())}"
    hans_path = cpasset_folder / f"ad_{now_str}_hans.jpg"
    hant_path = cpasset_folder / f"ad_{now_str}_hant.jpg"
    en_path = cpasset_folder / f"ad_{now_str}_en.jpg"
    ko_path = cpasset_folder / f"ad_{now_str}_ko.jpg"
    ja_path = cpasset_folder / f"ad_{now_str}_ja.jpg"
    content_hans = await image_hans.read()
    content_hant = await image_hant.read()
    content_en = await image_en.read()
    content_ko = await image_ko.read()
    content_ja = await image_ja.read()
    max_size = 0.5 * 1024 * 1024
    if len(content_hans) > max_size or len(content_hant) > max_size or len(content_en) > max_size or len(content_ko) > max_size or len(content_ja) > max_size:  # 超过 512KB
        raise BizException(code=ErrorCode.IMAGE_UPLOAD_OVERSIZE, message="image.over_size")
    await upload_to_oss(str(hans_path), content_hans)
    await upload_to_oss(str(hant_path), content_hant)
    await upload_to_oss(str(en_path), content_en)
    await upload_to_oss(str(ko_path), content_ko)
    await upload_to_oss(str(ja_path), content_ja)
    url_hans = f"/resources/homepage/banner/{hans_path.name}"
    url_hant = f"/resources/homepage/banner/{hant_path.name}"
    url_en = f"/resources/homepage/banner/{en_path.name}"
    url_ko = f"/resources/homepage/banner/{ko_path.name}"
    url_ja = f"/resources/homepage/banner/{ja_path.name}"

    await create_banner_ad_service(db, form, url_hans, url_hant, url_en, url_ko, url_ja)
    return BaseResponse.success(token=auth.new_token, message="success")