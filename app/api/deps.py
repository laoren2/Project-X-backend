from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from app.core.security import verify_token
from app.schemas.base import BizException
from app.schemas.user import AuthContext, UserRole
from app.core.errors import ErrorCode
from app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import User
from sqlalchemy import select


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/user/login")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    result = verify_token(token)
    if result is None:
        # Token 无效或解码失败，处理异常情况
        raise BizException(code=ErrorCode.TOKEN_INVALID, message="登录校验失败")
    
    return AuthContext(payload=result["payload"], new_token=result.get("new_token"))


async def get_current_admin(
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(User).where(User.user_id == ctx.payload["user_id"])
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or user.role != UserRole.admin.value:
        raise BizException(code=ErrorCode.NO_PERMISSION, message="无权限访问")

    return ctx
