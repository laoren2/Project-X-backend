from app.core.security import verify_token
from app.schemas.base import BizException, Language, DEFAULT_LANGUAGE
from app.schemas.user import AuthContext, UserRole, UserStatus
from app.core.errors import ErrorCode
from app.db.session import get_db
from app.db.models.user import User, UserBanHistory
from app.crud.user import get_banned_history_by_user_id
from fastapi import Depends, Header, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from enum import Enum
import datetime


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/user/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    result = verify_token(token)
    if result is None:
        # Token 无效或解码失败，处理异常情况
        raise BizException(code=ErrorCode.TOKEN_INVALID, message="identity.verify_failed.token")
    
    user_id = result["payload"]["user_id"]
    result_db = await db.execute(
        select(User)
        .where(
            User.user_id == user_id,
            User.status != UserStatus.deleted
        )
    )
    user = result_db.scalar_one_or_none()
    if user is None:
        raise BizException(code=ErrorCode.USER_DELETED, message="user.deleted")
    if user.status == UserStatus.banned:
        ban_history = await get_banned_history_by_user_id(db, user.id)
        now = datetime.datetime.now(datetime.timezone.utc)
        if ban_history and ban_history.unban_time <= now:
            # 自动解封
            user.status = UserStatus.normal
        else:
            # 计算剩余时间
            if ban_history:
                remaining = ban_history.unban_time - now
                remaining_str = str(remaining).split(".")[0]  # 去掉微秒
            else:
                remaining_str = "未知"
            raise BizException(code=ErrorCode.USER_BANNED, message="user.banned", params={"remaining": remaining_str})
    
    if db.in_transaction():
        await db.commit()

    return AuthContext(payload=result["payload"], new_token=result.get("new_token"))


async def get_current_admin(
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(User).where(User.user_id == ctx.payload["user_id"])
    result = await db.execute(stmt)
    if db.in_transaction():
        await db.commit()
    user = result.scalar_one_or_none()

    if not user or user.role != UserRole.admin.value:
        raise BizException(code=ErrorCode.NO_PERMISSION, message="identity.no_permission.internal_backend")

    return ctx


def get_language(
    request: Request,
    accept_language: str | None = Header(default=None)
) -> Language:
    lang = DEFAULT_LANGUAGE

    if accept_language:
        raw = accept_language.split(",")[0].split(";")[0].lower()

        if raw.startswith("zh"):
            if "tw" in raw or "hk" in raw or "hant" in raw:
                lang = Language.zh_hant
            else:
                lang = Language.zh_hans
        elif raw.startswith("en"):
            lang = Language.en

    request.state.lang = lang
    return lang