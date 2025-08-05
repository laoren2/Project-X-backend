from fastapi import APIRouter, Depends, File, UploadFile, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.base import BaseResponse
from app.schemas.user import AuthContext
from app.schemas.competition.common import RegionCreate
from app.services.competition.common import create_region_service
from app.core.errors import ErrorCode
from app.api.deps import get_current_admin
from typing import Optional
from pathlib import Path
from datetime import datetime


router = APIRouter()


# 创建新地理区域
@router.post("/create_region", response_model=BaseResponse[None], summary="创建新地理区域")
async def create_region(
    region: RegionCreate,
    auth: AuthContext = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    await create_region_service(db, region)
    return BaseResponse.success(token=auth.new_token, message=f"成功创建区域:{region.name}", data=None)