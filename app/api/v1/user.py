from fastapi import APIRouter, Depends, File, UploadFile, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.services.sms import send_sms_code, verify_sms_code
from app.services.user import login_or_register, get_user_info, update_user_info, delete_user_info, get_user_by_phone, get_user_role
from app.services.user_follow import get_relation_count, get_relationship_service
from app.api.deps import get_current_user
from app.core.errors import ErrorCode
from app.schemas import user as schemas_user
from app.schemas.base import BaseResponse
from typing import Optional
from pathlib import Path
from datetime import datetime


router = APIRouter()


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
    user = await get_user_info(auth.payload["user_id"], db)
    relation = await get_relation_count(db, auth.payload["user_id"])
    return BaseResponse.success(token=auth.new_token, message="成功获取我的信息", data=schemas_user.UserMeResponse(user=user, relation=relation))

@router.get("/me/role", response_model=BaseResponse[schemas_user.UserRole], summary="获取当前用户权限")
async def get_me_role(
    auth: schemas_user.AuthContext=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    role = await get_user_role(auth.payload["user_id"], db)
    return BaseResponse.success(token=auth.new_token, message="成功获取我的权限", data=role)

@router.get("/anyone", response_model=BaseResponse[schemas_user.UserAnyResponse], summary="获取任意用户信息")
async def get_anyone(
    user_id: str,
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
            return BaseResponse.error(status_code=ErrorCode.IMAGE_UPLOAD_OVERSIZE, detail="上传图片体积超过限制")
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
            return BaseResponse.error(status_code=ErrorCode.IMAGE_UPLOAD_OVERSIZE, detail="上传图片体积超过限制")
        with bg_path.open("wb") as f:
            f.write(contents)
        background_url = f"/resources/user/{user_id}/{bg_path.name}"
    
    user = await update_user_info(user_id, form, avatar_url, background_url, db)
    return BaseResponse.success(token=auth.new_token, message="成功修改我的信息", data=schemas_user.UserBaseInfoResponse(user=user))

@router.post("/delete", response_model=BaseResponse[None], summary="注销账号（删除用户数据）")
async def delete_account(
    auth: schemas_user.AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    user_id = auth.payload["user_id"]
    await delete_user_info(user_id, db)
    return BaseResponse.success(message="账号已注销")
