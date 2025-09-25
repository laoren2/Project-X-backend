from app.core.config import settings
from app.schemas.base import BaseResponse
from app.schemas.user import AuthContext
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.deps import get_current_user
import geoip2.database

router = APIRouter()


@router.get("/query_min_version", response_model=BaseResponse[str], summary="查询支持的最低客户端版本")
async def query_min_version():
    return BaseResponse.success(data=settings.MIN_APP_VERSION)


@router.get("/query_ip_country", response_model=BaseResponse[str], summary="查询客户端IP所属国家")
async def query_ip_country(request: Request):
    ip = None
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        x_real_ip = request.headers.get("X-Real-IP")
        if x_real_ip:
            ip = x_real_ip.strip()
    if not ip:
        ip = request.client.host
    #print(ip)
    try:
        with geoip2.database.Reader(settings.GEOIP_DB_PATH) as reader:
            response = reader.country(ip)
            country_iso = response.country.iso_code or "UNKNOWN"
    except Exception:
        country_iso = "UNKNOWN"

    return BaseResponse.success(data=country_iso)