from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from app.core.config import settings
from app.schemas.base import BizException
from app.core.errors import ErrorCode

ALGORITHM = "HS256"
TOKEN_REFRESH_THRESHOLD_MINUTES = 24 * 60 * 3   # 不足3天过期则刷新token

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        exp_timestamp = payload.get("exp")
        if exp_timestamp is None:
            return None

        exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        now = datetime.now(timezone.utc)
        refresh_token = None

        if exp_datetime < now:
            raise BizException(code=ErrorCode.TOKEN_EXPIRED, message="登录已过期")

        if exp_datetime - now < timedelta(minutes=TOKEN_REFRESH_THRESHOLD_MINUTES):
            refresh_token = create_access_token({k: v for k, v in payload.items() if k != "exp"})

        return {"payload": payload, "new_token": refresh_token}
    except JWTError:
        return None
