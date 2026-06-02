from sqlalchemy import Boolean, Enum, Integer, Float, String
from sqlalchemy.orm.attributes import InstrumentedAttribute
from app.core.errors import ErrorCode
from app.core.config import settings
from app.db.models.user import User
from app.schemas.base import BizException
from datetime import date, datetime, UTC, timedelta
from zoneinfo import ZoneInfo
from functools import lru_cache
import logging, hashlib, math, json, base64, random

EARTH_RADIUS = 6378137
HK_TZ = ZoneInfo("Asia/Hong_Kong")

logger = logging.getLogger(__name__)


def hash_card_id(card_id: str) -> str:
    salt = settings.REALNAME_SECRET_SALT
    return hashlib.sha256((salt + card_id).encode()).hexdigest()

def get_today_hk_date():
    return datetime.now(HK_TZ).date()

def str_to_bool(val):
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        if val.lower() == "true":
            return True
        if val.lower() == "false":
            return False
    return val

def str_to_enum(val, enum_cls):
    if isinstance(val, enum_cls):
        return val
    if isinstance(val, str):
        try:
            return enum_cls(val)
        except ValueError:
            raise BizException(code=ErrorCode.PROPERTY_ERROR, message=f"{val} 不是合法的 {enum_cls.__name__} 枚举值")
    return val

def auto_cast_fields(subclass, data: dict):
    """
    根据 SQLAlchemy 子类模型的字段类型自动转换 data 字段的类型
    """
    for field, value in data.items():
        # 只处理模型里有的字段
        if not hasattr(subclass, field):
            continue
        column = getattr(subclass, field)
        if not isinstance(column, InstrumentedAttribute):
            continue
        column_type = column.property.columns[0].type

        # Boolean
        if isinstance(column_type, Boolean):
            data[field] = str_to_bool(value)
        # Enum
        elif isinstance(column_type, Enum):
            enum_cls = column_type.enum_class
            data[field] = str_to_enum(value, enum_cls)
        # Integer
        elif isinstance(column_type, Integer):
            if value is not None and not isinstance(value, int):
                try:
                    data[field] = int(value)
                except Exception:
                    logger.exception("Integer转换异常")
                    raise BizException(code=ErrorCode.PROPERTY_ERROR, message=f"{field} 字段无法转换为 int: {value}")
        # Float
        elif isinstance(column_type, Float):
            if value is not None and not isinstance(value, float):
                try:
                    data[field] = float(value)
                except Exception:
                    logger.exception("Float转换异常")
                    raise BizException(code=ErrorCode.PROPERTY_ERROR, message=f"{field} 字段无法转换为 float: {value}")
        # String
        elif isinstance(column_type, String):
            if value is not None and not isinstance(value, str):
                data[field] = str(value)
        # 其他类型可按需扩展
    return data

def format_time_duration(seconds: float | int | None) -> str:
    """
    将秒数转换为更友好的时间字符串：
    < 1小时  -> MM:SS.xx
    >=1小时 -> H:MM:SS.xx
    其中 xx 为百分之一秒（2位小数）
    """
    if seconds is None:
        return "00:00.00"

    total_seconds = float(seconds)

    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    secs = total_seconds % 60  # 带小数

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:05.2f}"
    else:
        return f"{minutes:02d}:{secs:05.2f}"

@lru_cache
def get_tz(tz_name: str):
    return ZoneInfo(tz_name)

def get_user_local_time(user: User, utc_time=None):
    if utc_time is None:
        utc_time = datetime.now(UTC)
    tz = get_tz(user.timezone)
    return utc_time.astimezone(tz)

def get_user_local_date(user: User, utc_time=None):
    return get_user_local_time(user, utc_time).date()

def get_tile_size(level: int) -> int:
    if level == 0:
        return 32
    elif level == 1:
        return 32
    elif level == 2:
        return 16
    else:
        return 8

def latlon_to_mercator(lon: float, lat: float):
    x = EARTH_RADIUS * math.radians(lon)
    y = EARTH_RADIUS * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    return x, y

def latlon_to_grid(lat: int, lng: int) -> tuple[int, int]:
    x, y = latlon_to_mercator(lng, lat)
    grid_x = int(math.floor(x / 500))
    grid_y = int(math.floor(y / 500))
    return grid_x, grid_y

def compute_effect_grid_count(grid_count: int) -> int:
    """根据 region 的网格总数动态决定当日生成的 buff 奖励网格数量。
    分档（按 grid_count）：
      - >= 50000        : 50
      - 10000 ~ 50000   : 随机 10 ~ 50
      - 1000  ~ 10000   : 随机 5 ~ 10
      - 100   ~ 1000    : 随机 1 ~ 5
      - < 100           : 1
    """
    if grid_count >= 50000:
        return 50
    elif grid_count >= 10000:
        return random.randint(10, 50)
    elif grid_count >= 1000:
        return random.randint(5, 10)
    elif grid_count >= 100:
        return random.randint(1, 5)
    else:
        return 1

def haversine(lat1, lon1, lat2, lon2):
    """计算两点距离（米）"""
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# --- Cursor encoding/decoding helpers ---
def encode_cursor(data: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(data).encode()).decode()

def decode_cursor(cursor: str) -> dict:
    return json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())