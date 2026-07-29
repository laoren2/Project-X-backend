from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.common import get_device_by_id
from app.db.models.common import Device
from app.core.config import settings
from app.core.errors import ErrorCode
from app.schemas.base import BizException
import alibabacloud_oss_v2 as oss
import alibabacloud_oss_v2.aio as oss_aio
import numpy as np
import uuid, random, time, logging, os, math

logger = logging.getLogger(__name__)
_client = None
DATA_DIR = "/app/resources/srtm_data"

def get_oss_client():
    global _client
    if _client is None:
        credentials_provider = oss.credentials.StaticCredentialsProvider(
            settings.ALIYUN_ACCESS_KEY_ID,
            settings.ALIYUN_ACCESS_KEY_SECRET
        )
        cfg = oss.config.load_default()
        cfg.credentials_provider = credentials_provider
        cfg.region = 'cn-hongkong'
        cfg.use_internal_endpoint = True if settings.ENV.lower() == "prod" else False
        cfg.connect_timeout = 10
        cfg.readwrite_timeout = 10
        _client = oss_aio.AsyncClient(cfg)
    return _client

async def generate_unique_device_id(db: AsyncSession) -> str:
    while True:
        device_id = f"{random.randint(100000000000000, 999999999999999)}"
        existing_device = await get_device_by_id(db, device_id)
        if not existing_device:
            return device_id

async def generate_did_service(db: AsyncSession) -> str:
    device_id = await generate_unique_device_id(db)
    new_device = Device(device_id=device_id)
    db.add(new_device)
    await db.commit()
    return device_id

async def upload_to_oss(path: str, data: bytes):
    #print("start uploading")
    client = get_oss_client()
    bucket = "sporreer-prod-resources" if settings.ENV.lower() == "prod" else "sporreer-dev-resources"
    try:
        # 执行异步上传对象的请求，指定存储空间名称、对象名称和数据内容
        result = await client.put_object(
            oss.PutObjectRequest(
                bucket=bucket,
                key=path,
                body=data
            )
        )
        #print("finish upload")
    except Exception as e:
        logger.exception(f"用户资料上传失败：{e}")
        raise BizException(code=ErrorCode.USER_INFO_ERROR, message="oss.error.upload")
    finally:
        # 关闭异步客户端连接（重要：避免资源泄漏）
        await client.close()
        # client 已关闭，下一次上传必须重新创建，避免复用已关闭连接。
        global _client
        if _client is client:
            _client = None

def get_tile_name(lat, lon):
    lat_floor = math.floor(lat)
    lon_floor = math.floor(lon)

    lat_prefix = "N" if lat_floor >= 0 else "S"
    lon_prefix = "E" if lon_floor >= 0 else "W"

    return f"{lat_prefix}{abs(lat_floor):02d}{lon_prefix}{abs(lon_floor):03d}.hgt"


def get_elevation(lat, lon):
    tile_name = get_tile_name(lat, lon)
    path = os.path.join(DATA_DIR, tile_name)
    if not os.path.exists(path):
        return None
    
    # SRTM3 = 1201 x 1201
    data = np.fromfile(path, dtype=">i2").reshape((1201, 1201))
    
    # 计算像素位置
    lat_floor = math.floor(lat)
    lon_floor = math.floor(lon)
    
    row = int((lat - lat_floor) * 1200)
    col = int((lon - lon_floor) * 1200)
    
    return int(data[1200 - row][col])
