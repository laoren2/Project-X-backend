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
from datetime import datetime, timezone


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/user/login")
# 可选鉴权：无 token 时返回 None 而非抛 401（用于「未登录可看、登录则带身份」的接口）
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/v1/user/login", auto_error=False)


async def _resolve_auth_context(token: str, db: AsyncSession) -> AuthContext:
    """校验 token、处理封禁/自动解封与续期，返回 AuthContext。token 无效则抛异常。"""
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
        now = datetime.now(timezone.utc)
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


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    return await _resolve_auth_context(token, db)


async def get_current_user_optional(
    token: str | None = Depends(oauth2_scheme_optional),
    db: AsyncSession = Depends(get_db)
) -> AuthContext | None:
    """可选鉴权：未携带 token 时视为匿名（返回 None）；携带则按标准流程校验（无效仍抛错）。"""
    if not token:
        return None
    return await _resolve_auth_context(token, db)


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
        primary = raw.split("-")[0]
        if primary == "zh":
            if "tw" in raw or "hk" in raw or "hant" in raw:
                lang = Language.zh_hant
            else:
                lang = Language.zh_hans
        elif primary == "en":
            lang = Language.en
        elif primary == "ko":
            lang = Language.ko
        elif primary == "ja":
            lang = Language.ja
        elif primary == "fr":
            lang = Language.fr

    request.state.lang = lang
    return lang