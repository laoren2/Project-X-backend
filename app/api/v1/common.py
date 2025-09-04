from app.core.config import settings
from fastapi import APIRouter
from app.schemas.base import BaseResponse


router = APIRouter()


@router.get("/query_min_version", response_model=BaseResponse[str], summary="查询支持的最低客户端版本")
async def query_min_version():
    return BaseResponse.success(data=settings.MIN_APP_VERSION)