from fastapi import APIRouter, Depends, File, UploadFile, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.base import BaseResponse
from app.schemas.user import AuthContext
from app.schemas.competition import (
    SeasonCreateForm, RegionCreate
)
from app.services.competition.common import (
    create_season_service, 
    create_region_service, 
    update_season_image_url
)
from app.core.errors import ErrorCode
from app.api.deps import get_current_admin
from typing import Optional
from pathlib import Path
from datetime import datetime


router = APIRouter()

# 创建新赛季
@router.post("/create_season", response_model=BaseResponse[None], summary="创建新赛季")
async def create_season(
    season: SeasonCreateForm = Depends(),
    season_image: Optional[UploadFile] = File(None),
    auth: AuthContext = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    image_url = "/resources/placeholder/season.png"
    new_season = await create_season_service(db, season, image_url)

    if season_image:
        season_folder = Path(f"resources/competition/{season.sport_type.value}/season") / new_season.season_id
        season_folder.mkdir(parents=True, exist_ok=True)
        for file in season_folder.glob("background_*.jpg"):
            file.unlink(missing_ok=True)
        background_path = season_folder / f"background_{int(datetime.now().timestamp())}.jpg"
        contents = await season_image.read()
        if len(contents) > 2 * 1024 * 1024:  # 超过 2MB
            return BaseResponse.error(status_code=ErrorCode.IMAGE_UPLOAD_OVERSIZE, detail="上传图片体积超过限制")
        with background_path.open("wb") as f:
            f.write(contents)
        new_url = f"/resources/competition/{season.sport_type.value}/season/{new_season.season_id}/{background_path.name}"
        await update_season_image_url(db, new_season.season_id, new_url)
    return BaseResponse.success(token=auth.new_token, message=f"成功创建{season.sport_type.value}:{season.name}", data=None)


# 创建新地理区域
@router.post("/create_region", response_model=BaseResponse[None], summary="创建新地理区域")
async def create_region(
    region: RegionCreate,
    auth: AuthContext = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    await create_region_service(db, region)
    return BaseResponse.success(token=auth.new_token, message=f"成功创建区域:{region.name}", data=None)