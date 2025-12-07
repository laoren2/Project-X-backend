from fastapi import APIRouter, Depends, File, UploadFile, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.user import get_user_by_id, get_user_by_phone
from app.db.session import get_db
from app.schemas.common import SportType
from app.services.sms import send_sms_code, verify_sms_code
from app.services.user import (
    login_or_register, get_me_info, get_user_info, update_user_info, delete_user_info, 
    get_user_role, update_user_default_sport_service, unbind_phone_service,
    update_user_location_service, verify_apple_identity_token,
    login_or_register_apple, realname_hk_service, bind_phone_service,
    bind_apple_id_service, unbind_apple_id_service, sign_in_status_service,
    sign_in_today_service, sign_in_today_vip_service
)
from app.crud.user import get_exist_user_by_phone
from app.services.user_follow import get_relation_count, get_relationship_service
from app.api.deps import get_current_user
from app.core.errors import ErrorCode
from app.schemas import user as schemas_user
from app.schemas.common import PersonInfoResponse
from app.schemas.base import BaseResponse
from app.schemas.asset import SignInStatusResponse, CCAssetBaseInfo
from typing import Optional
from pathlib import Path
from datetime import datetime
import json

router = APIRouter()


@router.get("/user_card/phone", response_model=BaseResponse[PersonInfoResponse], summary="根据手机号查询用户")
async def get_anyone_card(
    phone_number: str,
    auth: schemas_user.AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    user = await get_exist_user_by_phone(db, phone_number)
    if user is None:
        return BaseResponse.error(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
    return BaseResponse.success(
        token=auth.new_token,
        message="成功获取用户信息卡片", 
        data=PersonInfoResponse(user_id=user.user_id, avatar_image_url=user.avatar_image_url, nickname=user.nickname)
    )

@router.post("/send_code", response_model=BaseResponse[schemas_user.SendCodeResponse], summary="发送验证码")
async def send_code(data: schemas_user.SMSCodeRequest):
    code = await send_sms_code(data.phone_number)
    return BaseResponse.success(message="验证码已发送", data=schemas_user.SendCodeResponse(code=code))

@router.post("/login", response_model=BaseResponse[schemas_user.LoginResponse], summary="手机号+验证码登录/注册")
async def login(data: schemas_user.SMSCodeVerify, db: AsyncSession = Depends(get_db)):
    if not await verify_sms_code(data.phone_number, data.code):
        return BaseResponse.error(code=ErrorCode.SMS_CODE_WRONG, message="验证码错误")
    token, user, isRegister, role = await login_or_register(data.phone_number, db)
    relation = await get_relation_count(db, user.user_id)
    return BaseResponse.success(token=token, message="登录成功", data=schemas_user.LoginResponse(user=user, relation=relation, role=role, isRegister=isRegister))

@router.get("/me", response_model=BaseResponse[schemas_user.UserMeResponse], summary="获取当前用户信息")
async def get_me(
    auth: schemas_user.AuthContext=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    user, o_id = await get_me_info(auth.payload["user_id"], db)
    relation = await get_relation_count(db, auth.payload["user_id"])
    return BaseResponse.success(token=auth.new_token, message="成功获取我的信息", data=schemas_user.UserMeResponse(user=user, relation=relation, origin_transaction_id=o_id))

@router.get("/me/role", response_model=BaseResponse[schemas_user.UserRole], summary="获取当前用户权限")
async def get_me_role(
    auth: schemas_user.AuthContext=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    role = await get_user_role(auth.payload["user_id"], db)
    return BaseResponse.success(token=auth.new_token, message="成功获取我的权限", data=role)

@router.get("/anyone", response_model=BaseResponse[schemas_user.UserAnyResponse], summary="获取任意用户信息")
async def get_anyone(
    user_id: str = Query(...),
    my_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    user = await get_user_info(user_id, db)
    relation = await get_relation_count(db, user_id)
    if my_id:
        relationship = await get_relationship_service(db, my_id, user_id)
        return BaseResponse.success(message="成功获取用户信息", data=schemas_user.UserAnyResponse(user=user, relation=relation, relationship=relationship))
    else:
        return BaseResponse.success(message="成功获取用户信息", data=schemas_user.UserAnyResponse(user=user, relation=relation, relationship=schemas_user.RelationshipStatus.none))

@router.post("/update", response_model=BaseResponse[schemas_user.UserBaseInfoResponse], summary="更新当前用户信息")
async def update_me(
    form: schemas_user.UserUpdateForm = Depends(),
    avatar_image: Optional[UploadFile] = File(None),
    background_image: Optional[UploadFile] = File(None),
    auth: schemas_user.AuthContext=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    user_id = auth.payload["user_id"]
    avatar_url = "/resources/placeholder/avatar.png"
    background_url = "/resources/placeholder/background.png"

    # 更新图片资源
    user_folder = Path("resources/user") / user_id
    user_folder.mkdir(parents=True, exist_ok=True)
    if avatar_image:
        # 删除旧头像
        for file in user_folder.glob("avatar_*.jpg"):
            file.unlink(missing_ok=True)
        avatar_path = user_folder / f"avatar_{int(datetime.now().timestamp())}.jpg"
        contents = await avatar_image.read()
        if len(contents) > 1 * 1024 * 1024:  # 超过 1MB
            return BaseResponse.error(code=ErrorCode.IMAGE_UPLOAD_OVERSIZE, message="上传图片体积超过限制")
        with avatar_path.open("wb") as f:
            f.write(contents)
        avatar_url = f"/resources/user/{user_id}/{avatar_path.name}"
    if background_image:
        # 删除旧背景图
        for file in user_folder.glob("background_*.jpg"):
            file.unlink(missing_ok=True)
        bg_path = user_folder / f"background_{int(datetime.now().timestamp())}.jpg"
        contents = await background_image.read()
        if len(contents) > 1 * 1024 * 1024:  # 超过 1MB
            return BaseResponse.error(code=ErrorCode.IMAGE_UPLOAD_OVERSIZE, message="上传图片体积超过限制")
        with bg_path.open("wb") as f:
            f.write(contents)
        background_url = f"/resources/user/{user_id}/{bg_path.name}"
    
    user = await update_user_info(user_id, form, avatar_url, background_url, db)
    return BaseResponse.success(token=auth.new_token, message="成功修改我的信息", data=schemas_user.UserBaseInfoResponse(user=user))

@router.post("/delete", response_model=BaseResponse[None], summary="注销账号")
async def delete_account(
    auth: schemas_user.AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await delete_user_info(auth.payload["user_id"], db)
    return BaseResponse.success(message="账号已成功注销")

@router.post("/update_user_default_sport", response_model=BaseResponse[SportType], summary="更新用户主页的默认展示运动")
async def update_user_default_sport(
    sport: SportType = Query(...),
    auth: schemas_user.AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await update_user_default_sport_service(sport, auth.payload["user_id"], db)
    return BaseResponse.success(token=auth.new_token, message="更新成功", data=result)

@router.post("/update_location", response_model=BaseResponse[None], summary="更新用户位置")
async def update_location(
    region: str = Query(...),
    auth: schemas_user.AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await update_user_location_service(region, auth.payload["user_id"], db)
    return BaseResponse.success(token=auth.new_token, message="更新成功")

@router.post("/realname_hk", response_model=BaseResponse[None], summary="香港身份证实名认证")
async def realname_hk(
    front_image: UploadFile = File(...),
    auth: schemas_user.AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    front_bytes = await front_image.read()
    await realname_hk_service(auth.payload["user_id"], front_bytes, db)
    return BaseResponse.success(token=auth.new_token, message="实名认证成功")

@router.post("/login/apple", response_model=BaseResponse[schemas_user.LoginResponse], summary="Apple ID 登录/注册")
async def login_with_apple(
    token: str = Query(...),   # identityToken
    db: AsyncSession = Depends(get_db)
):
    # 验证并解码 ID Token
    payload = await verify_apple_identity_token(token)
    if not payload:
        return BaseResponse.error(code=ErrorCode.OAUTH_FAILED, message="Apple 登录验证失败")

    apple_sub = payload.get("sub")  # Apple 提供的唯一用户 ID
    email = payload.get("email", "")
    if not apple_sub:
        return BaseResponse.error(code=ErrorCode.OAUTH_FAILED, message="Apple 登录验证失败")
    new_token, user, is_register, role = await login_or_register_apple(apple_sub, email, db)
    relation = await get_relation_count(db, user.user_id)
    
    return BaseResponse.success(
        token=new_token,
        message="登录成功",
        data=schemas_user.LoginResponse(user=user, relation=relation, role=role, isRegister=is_register)
    )

@router.post("/account/bind_phone", response_model=BaseResponse[None], summary="绑定手机号")
async def bind_phone(
    phone: str = Query(...),
    code: str = Query(...),
    auth: schemas_user.AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not await verify_sms_code(phone, code):
        return BaseResponse.error(code=ErrorCode.SMS_CODE_WRONG, message="验证码错误")
    await bind_phone_service(phone, auth.payload["user_id"], db)
    return BaseResponse.success(token=auth.new_token, message="绑定成功")

@router.post("/account/unbind_phone", response_model=BaseResponse[None], summary="解除绑定手机号")
async def unbind_phone(
    auth: schemas_user.AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await unbind_phone_service(auth.payload["user_id"], db)
    return BaseResponse.success(token=auth.new_token, message="解除绑定成功")

@router.post("/account/bind_apple_id", response_model=BaseResponse[str], summary="绑定appleid")
async def bind_apple_id(
    token: str = Query(...),
    auth: schemas_user.AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    email = await bind_apple_id_service(token, auth.payload["user_id"], db)
    return BaseResponse.success(token=auth.new_token, message="绑定成功", data=email)

@router.post("/account/unbind_apple_id", response_model=BaseResponse[None], summary="解除绑定appleid")
async def unbind_apple_id(
    auth: schemas_user.AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await unbind_apple_id_service(auth.payload["user_id"], db)
    return BaseResponse.success(token=auth.new_token, message="解除绑定成功")

# 查询签到状态
@router.get("/sign_in/status",response_model=BaseResponse[SignInStatusResponse], summary="查询签到状态")
async def sign_in_status(
    auth: schemas_user.AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await sign_in_status_service(db, auth.payload["user_id"])
    return BaseResponse.success(token=auth.new_token, data=result)

# 非会员签到
@router.post("/sign_in/today",response_model=BaseResponse[CCAssetBaseInfo], summary="非会员签到")
async def sign_in_today(
    auth: schemas_user.AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await sign_in_today_service(db, auth.payload["user_id"])
    return BaseResponse.success(token=auth.new_token, message="领取成功", data=result)

# 订阅会员签到
@router.post("/sign_in_vip/today",response_model=BaseResponse[CCAssetBaseInfo], summary="订阅会员签到")
async def sign_in_today_vip(
    auth: schemas_user.AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await sign_in_today_vip_service(db, auth.payload["user_id"])
    return BaseResponse.success(token=auth.new_token, message="领取成功", data=result)