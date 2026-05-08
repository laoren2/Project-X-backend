from app.core.config import settings
from app.core.errors import ErrorCode
from app.schemas.base import BaseResponse, BizException
from app.schemas.user import AuthContext
from app.schemas.common import CountryBBoxResponse, CountryBBoxConfig, CountryBBoxInfo
from app.services.common import generate_did_service, get_elevation
from app.crud.competition.common import get_region_boundary_geojson_by_region_id
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.deps import get_current_user, get_language
from app.db.models.training import COUNTRY_GRIDS_BBOX
import geoip2.database, logging

router = APIRouter(dependencies=[Depends(get_language)])

logger = logging.getLogger(__name__)

@router.get("/ping", response_model=BaseResponse[None], summary="用于检查客户端本地网络权限")
async def ping():
    return BaseResponse.success(data=None)

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
        logger.exception("ip查询异常")
        raise
    return BaseResponse.success(data=country_iso)

@router.post("/generate_did", response_model=BaseResponse[str], summary="生成设备ID")
async def generate_did(
    db: AsyncSession = Depends(get_db)
):
    device_id = await generate_did_service(db)
    return BaseResponse.success(data=device_id)

@router.get("/country_bboxes", response_model=BaseResponse[CountryBBoxResponse], summary="查询国家bbox范围")
async def query_country_bboxes():
    country_bboxes = [CountryBBoxConfig(
        country_code=country_code,
        bbox=CountryBBoxInfo(originLat=bbox[0], originLng=bbox[1], endLat=bbox[2], endLng=bbox[3])
    ) for country_code, bbox in COUNTRY_GRIDS_BBOX.items()]
    return BaseResponse.success(data=CountryBBoxResponse(configs=country_bboxes))


@router.get("/elevation_diff", response_model=BaseResponse[int | None], summary="查询两坐标点之间的海拔差")
async def elevation_diff(
    lat1: float = Query(...),
    lng1: float = Query(...),
    lat2: float = Query(...),
    lng2: float = Query(...)
):
    e1 = get_elevation(lat1, lng1)
    e2 = get_elevation(lat2, lng2)
    #print(e1, e2)
    
    if e1 is None or e2 is None:
        return BaseResponse.success(data = None)
    return BaseResponse.success(data=e2 - e1)

# 查询 region boudary
@router.get("/region_boundary",response_model=BaseResponse[dict],summary="查询 region boudary")
async def region_boundary(
    region_id: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    result = await get_region_boundary_geojson_by_region_id(db, region_id)
    if not result:
        raise BizException(code=ErrorCode.REGION_ERROR, message="region.not_found")
    return BaseResponse.success(data=result)