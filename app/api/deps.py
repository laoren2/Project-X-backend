from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from app.core.security import verify_token
from app.schemas.base import BizException
from app.schemas.user import AuthContext
from app.core.errors import ErrorCode

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/user/login")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    result = verify_token(token)
    if result is None:
        # Token 无效或解码失败，处理异常情况
        raise BizException(code=ErrorCode.TOKEN_INVALID, message="登录校验失败")
    
    return AuthContext(payload=result["payload"], new_token=result.get("new_token"))
