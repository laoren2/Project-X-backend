from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.base import BaseResponse
from app.schemas.user import UserBaseInfo
from app.schemas.user_follow import PersonInfoResponse
from app.services.user import get_user_by_phone
from app.core.errors import ErrorCode
from app.schemas.user import AuthContext
from app.api.deps import get_current_admin

router = APIRouter()

# 内部API
@router.get("/anyone_card", response_model=BaseResponse[PersonInfoResponse], summary="获取任意用户信息卡片")
async def get_anyone_card(
    phone_number: str,
    auth: AuthContext = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    user = await get_user_by_phone(db, phone_number)
    if not user:
        return BaseResponse.error(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
    userInfo = UserBaseInfo.model_validate(user)
    return BaseResponse.success(token=auth.new_token, message="成功获取用户信息卡片", data=PersonInfoResponse(user_id=userInfo.user_id, avatar_image_url=userInfo.avatar_image_url, nickname=userInfo.nickname))