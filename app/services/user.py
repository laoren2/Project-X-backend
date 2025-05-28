from app.crud.user import get_user_by_phone, create_user, get_user_by_id, update_user, delete_user_by_id
from app.core.security import create_access_token
from app.schemas.user import UserUpdateForm, UserBaseInfo
from app.db.session import get_db
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.base import BizException
from app.core.errors import ErrorCode

async def login_or_register(phone_number: str, db: AsyncSession):
    isRegister = False
    user = await get_user_by_phone(db, phone_number)
    if not user:
        user = await create_user(db, phone_number)
        isRegister = True
    userInfo = UserBaseInfo.model_validate(user)
    token = create_access_token({"user_id": user.user_id})
    return token, userInfo, isRegister

async def get_user_info(user_id: str, db: AsyncSession):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
    return UserBaseInfo.model_validate(user)

async def update_user_info(user_id: str, form: UserUpdateForm, avatar_url: str, background_url: str, db: AsyncSession):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, detail="用户不存在")
    update_data = form.__dict__.copy()
    update_data["avatar_image_url"] = avatar_url
    update_data["background_image_url"] = background_url
    user = await update_user(db, user, update_data)
    return UserBaseInfo.model_validate(user)

async def delete_user_info(user_id: str, db: AsyncSession):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, detail="用户不存在")
    await delete_user_by_id(db, user)
    return True