from app.crud.user import get_user_by_phone, create_user, get_user_by_id, update_user, get_banned_history_by_user_id
from app.core.security import create_access_token
from app.schemas.user import UserUpdateForm, UserBaseInfo, UserRole, UserStatus
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.base import BizException
from app.core.errors import ErrorCode
import datetime

async def login_or_register(phone_number: str, db: AsyncSession):
    isRegister = False
    user = await get_user_by_phone(db, phone_number)
    if not user:
        user = await create_user(db, phone_number)
        isRegister = True
    else:
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
                raise BizException(code=ErrorCode.USER_BANNED, message=f"账号已封禁\n剩余时间:{remaining_str}")
        if user.status == UserStatus.deleted:
            raise BizException(code=ErrorCode.USER_DELETED, message="账号已注销")
    await db.commit()
    userInfo = UserBaseInfo.model_validate(user)
    token = create_access_token({"user_id": user.user_id})
    return token, userInfo, isRegister, UserRole(user.role)

async def get_user_role(user_id: str, db: AsyncSession):
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
    return UserRole(user.role)

async def get_user_info(user_id: str, db: AsyncSession):
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
    return UserBaseInfo.model_validate(user)

async def update_user_info(user_id: str, form: UserUpdateForm, avatar_url: str, background_url: str, db: AsyncSession):
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
    update_data = form.__dict__.copy()
    update_data["avatar_image_url"] = avatar_url
    update_data["background_image_url"] = background_url
    user = await update_user(db, user, update_data)
    await db.commit()
    return UserBaseInfo.model_validate(user)

async def delete_user_info(user_id: str, db: AsyncSession):
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
    user.status = UserStatus.deleted
    user.nickname = f"已注销_{user_id[-5:]}"
    user.phone_number = None
    user.avatar_image_url = "/resources/placeholder/avatar.png"
    user.background_image_url = "/resources/placeholder/background.png"
    user.introduction = None
    user.gender = None
    user.birthday = None
    user.location = None
    user.identity_auth_name = None
    user.is_realname_auth = False
    user.is_identity_auth = False
    user.is_display_gender = False
    user.is_display_age = False
    user.is_display_location = False
    user.enable_auto_location = False
    user.is_display_identity = False
    await db.commit()
    return True