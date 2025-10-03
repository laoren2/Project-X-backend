from app.crud.user import (
    create_user, get_user_by_id, get_banned_history_by_user_id,
    get_user_by_apple_id, create_user_with_apple, get_realname_info_by_user_id,
    get_realname_info_by_card_id, get_settings_by_user_id, get_exist_user_by_phone,
    get_exist_user_by_apple_id, get_exist_user_by_id
)
from app.core.security import create_access_token
from app.schemas.common import SportType
from app.schemas.user import UserUpdateForm, UserBaseInfo, UserStatus, Gender
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.base import BizException
from app.db.models.user import UserRealNameHK, UserSetting
from app.core.errors import ErrorCode
from app.core.config import settings
from alibabacloud_ocr_api20210707.client import Client as OcrClient
from alibabacloud_ocr_api20210707.models import RecognizeHKIdcardRequest
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util.client import Client as UtilClient
import datetime, io, asyncio, jwt, json
from jwt import PyJWKClient

async def login_or_register(phone_number: str, db: AsyncSession):
    async with db.begin():
        isRegister = False
        user = await get_exist_user_by_phone(db, phone_number)
        if not user:
            user = await create_user(db, phone_number)
            user_info = UserBaseInfo.model_validate(user)
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
            user_info = UserBaseInfo.model_validate(user)
            if user.real_name_info:
                user_info.gender = user.real_name_info.gender
                user_info.birthday = user.real_name_info.birth_date
            if user.settings:
                user_info.is_display_gender = user.settings.is_display_gender
                user_info.is_display_age = user.settings.is_display_age
                user_info.is_display_location = user.settings.is_display_location
                user_info.enable_auto_location = user.settings.enable_auto_location
                user_info.is_display_identity = user.settings.is_display_identity
                user_info.default_sport = user.settings.default_sport
        token = create_access_token({"user_id": user.user_id})
        return token, user_info, isRegister, user.role

async def login_or_register_apple(apple_id: str, email: str, db: AsyncSession):
    async with db.begin():
        user = await get_exist_user_by_apple_id(db, apple_id)
        is_register = False
        if not user:
            user = await create_user_with_apple(db, apple_id, email)
            user_info = UserBaseInfo.model_validate(user)
            is_register = True
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
            user_info = UserBaseInfo.model_validate(user)
            if user.real_name_info:
                user_info.gender = user.real_name_info.gender
                user_info.birthday = user.real_name_info.birth_date
            if user.settings:
                user_info.is_display_gender = user.settings.is_display_gender
                user_info.is_display_age = user.settings.is_display_age
                user_info.is_display_location = user.settings.is_display_location
                user_info.enable_auto_location = user.settings.enable_auto_location
                user_info.is_display_identity = user.settings.is_display_identity
                user_info.default_sport = user.settings.default_sport
        token = create_access_token({"user_id": user.user_id})
        return token, user_info, is_register, user.role

async def get_user_role(user_id: str, db: AsyncSession):
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
    return user.role

async def get_user_info(user_id: str, db: AsyncSession):
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
    user_info = UserBaseInfo.model_validate(user)
    if user.real_name_info:
        user_info.gender = user.real_name_info.gender
        user_info.birthday = user.real_name_info.birth_date
    if user.settings:
        user_info.is_display_gender = user.settings.is_display_gender
        user_info.is_display_age = user.settings.is_display_age
        user_info.is_display_location = user.settings.is_display_location
        user_info.enable_auto_location = user.settings.enable_auto_location
        user_info.is_display_identity = user.settings.is_display_identity
        user_info.default_sport = user.settings.default_sport
    else:
        db.add(UserSetting(user_id=user.id))  # 手动添加
        await db.commit()
    return user_info

async def update_user_info(user_id: str, form: UserUpdateForm, avatar_url: str, background_url: str, db: AsyncSession):
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
        if not user.settings:
            user_setting = UserSetting(user_id=user.id)
            user.settings = user_setting
            db.add(user_setting)
        user.nickname = form.nickname
        user.introduction = form.introduction
        user.location = form.location
        user.avatar_image_url = avatar_url
        user.background_image_url = background_url
        user.settings.is_display_gender = form.is_display_gender
        user.settings.is_display_age = form.is_display_age
        user.settings.is_display_location = form.is_display_location
        user.settings.enable_auto_location = form.enable_auto_location
        user.settings.is_display_identity = form.is_display_identity

        user_info = UserBaseInfo.model_validate(user)
        if user.real_name_info:
            user_info.gender = user.real_name_info.gender
            user_info.birthday = user.real_name_info.birth_date
        user_info.is_display_gender = user.settings.is_display_gender
        user_info.is_display_age = user.settings.is_display_age
        user_info.is_display_location = user.settings.is_display_location
        user_info.enable_auto_location = user.settings.enable_auto_location
        user_info.is_display_identity = user.settings.is_display_identity
        user_info.default_sport = user.settings.default_sport
        return user_info

async def delete_user_info(user_id: str, db: AsyncSession):
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
        # 删除实名信息
        if user.real_name_info:
            await db.delete(user.real_name_info)
        # 删除设置
        if user.settings:
            await db.delete(user.settings)
        user.status = UserStatus.deleted

async def update_user_default_sport_service(sport: SportType, user_id: str, db: AsyncSession) -> SportType:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
    if not user.settings:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户设置错误")
    user.settings.default_sport = sport
    await db.commit()
    return user.settings.default_sport

async def update_user_location_service(region: str, user_id: str, db: AsyncSession):
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
    user.location = region
    await db.commit()

def create_ocr_client() -> OcrClient:
    config = open_api_models.Config(
        access_key_id=settings.ALIYUN_ACCESS_KEY_ID,
        access_key_secret=settings.ALIYUN_ACCESS_KEY_SECRET
    )
    config.endpoint = settings.ALIYUN_ENDPOINT
    return OcrClient(config)

async def recognize_hk_idcard(image_bytes: bytes) -> dict:
    """
    调用阿里云香港身份证 OCR，直接传图片 body，不存储文件
    """
    client = create_ocr_client()
    request = RecognizeHKIdcardRequest(
        body=io.BytesIO(image_bytes)
    )
    try:
        # 调用阿里云接口
        response = await asyncio.to_thread(client.recognize_hkidcard, request)
        return UtilClient.to_map(response)
    except Exception as e:
        raise BizException(code=ErrorCode.REALNAME_FAILED, message="身份证识别失败")

async def realname_hk_service(user_id: str, front_bytes: bytes, db: AsyncSession):
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
        exist_info = await get_realname_info_by_user_id(db, user.id)
        if exist_info:
            raise BizException(code=ErrorCode.REALNAME_FAILED, message="请勿重复认证")
    
        result = await recognize_hk_idcard(front_bytes)
        raw_data = result.get("body", {}).get("Data", {})
        if not raw_data:
            return BizException(code=ErrorCode.REALNAME_FAILED, message="身份证识别失败")
        try:
            parsed = json.loads(raw_data)
            data = parsed.get("data", {}) if isinstance(parsed, dict) else {}
        except Exception:
            data = {}
        # 3. 提取需要的字段
        name_Cn = data.get("nameCn", "")
        name_En = data.get("nameEn", "")
        gender_str = data.get("sex", "")
        if "男" in gender_str or "M" in gender_str:
            gender = Gender.male
        elif "女" in gender_str or "F" in gender_str:
            gender = Gender.female
        else:
            gender = None
        nation_id = data.get("idNumber", "")
        birth_date = data.get("birthDate", "")
        name_code = data.get("nameCode", "")
        issued_code = data.get("issuedCode", "")

        if not (name_En and gender_str and nation_id and birth_date and issued_code):
            raise BizException(code=ErrorCode.REALNAME_FAILED, message="身份证识别失败")
        exist_card_info = await get_realname_info_by_card_id(db, nation_id)
        if exist_card_info:
            raise BizException(code=ErrorCode.REALNAME_FAILED, message="身份已被认证")

        # 这里写回数据库，只存识别字段，不存身份证图片
        realname_info = UserRealNameHK(
            user_id=user.id,
            gender=gender,
            birth_date=birth_date,
            name_Cn=name_Cn,
            name_En=name_En,
            card_id=nation_id,
            name_code=name_code,
            issued_code=issued_code
        )
        db.add(realname_info)

async def verify_apple_identity_token(identity_token: str):
    try:
        jwks_client = PyJWKClient(settings.APPLE_KEYS_URL)
        signing_key = jwks_client.get_signing_key_from_jwt(identity_token)
        payload = jwt.decode(
            identity_token,
            signing_key.key,
            algorithms=["RS256"],
            audience="com.renjie.sportsx",
            issuer="https://appleid.apple.com"
        )
        return payload
    except Exception as e:
        print("Apple Token 验证失败:", e)
        return None

async def bind_phone_service(phone_number: str, user_id: str, db: AsyncSession):
    user = await get_exist_user_by_id(db, user_id)
    if not user:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
    if user.phone_number:
        raise BizException(code=ErrorCode.PHONE_NUMBER_ERROR, message="请先解除当前绑定号码")
    exist_phone = await get_exist_user_by_phone(db, phone_number)
    if exist_phone:
        raise BizException(code=ErrorCode.PHONE_NUMBER_ERROR, message="该号码已被绑定")
    user.phone_number = phone_number
    await db.commit()

async def unbind_phone_service(user_id: str, db: AsyncSession):
    user = await get_exist_user_by_id(db, user_id)
    if not user:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
    if not user.phone_number:
        raise BizException(code=ErrorCode.PHONE_NUMBER_ERROR, message="请先绑定手机号码")
    if not user.apple_id:
        raise BizException(code=ErrorCode.PHONE_NUMBER_ERROR, message="请先绑定一个Apple账号否则账号无法找回")
    user.phone_number = None
    await db.commit()

async def bind_apple_id_service(token: str, user_id: str, db: AsyncSession) -> str:
    user = await get_exist_user_by_id(db, user_id)
    if not user:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
    if user.apple_id:
        raise BizException(code=ErrorCode.APPLE_ID_ERROR, message="请先解除当前绑定的apple账号")
    
    payload = await verify_apple_identity_token(token)
    if not payload:
        return BizException(code=ErrorCode.OAUTH_FAILED, message="apple账号绑定失败")
    apple_sub = payload.get("sub")  # Apple 提供的唯一用户 ID
    email = payload.get("email")
    if not apple_sub or not email:
        return BizException(code=ErrorCode.OAUTH_FAILED, message="apple账号绑定失败，请在“系统设置-Apple账户-通过Apple登录”里删除账号后重试")
    exist_apple_id = await get_exist_user_by_apple_id(db, apple_sub)
    if exist_apple_id:
        raise BizException(code=ErrorCode.PHONE_NUMBER_ERROR, message="该账号已被绑定")
    user.apple_id = apple_sub
    user.apple_email = email
    await db.commit()
    return email

async def unbind_apple_id_service(user_id: str, db: AsyncSession):
    user = await get_exist_user_by_id(db, user_id)
    if not user:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
    if not user.apple_id:
        raise BizException(code=ErrorCode.APPLE_ID_ERROR, message="请先绑定apple账号")
    if not user.phone_number:
        raise BizException(code=ErrorCode.APPLE_ID_ERROR, message="请先绑定手机号否则账号无法找回")
    user.apple_id = None
    user.apple_email = None
    await db.commit()