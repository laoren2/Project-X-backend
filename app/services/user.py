from app.crud.user import (
    create_user, get_user_by_id, get_banned_history_by_user_id,
    create_user_with_apple, get_realname_info_by_user_id, get_test_account,
    get_realname_info_by_card_id, get_settings_by_user_id, get_exist_user_by_phone,
    get_exist_user_by_apple_id, get_exist_user_by_id, get_sign_in_rewards, 
    get_user_normal_sign_in_today, get_user_sign_in_history, get_exist_user_by_email,
    get_user_vip_sign_in_today, get_sign_in_reward_by_day, create_user_with_email
)
from app.crud.asset_manage import reward_ccasset
from app.core.tools import get_today_hk_date
import app.crud.competition.bike as bike_crud
import app.crud.competition.running as running_crud
from app.core.security import create_access_token
from app.schemas.common import SportType, CCAssetBaseInfo
from app.schemas.user import UserUpdateForm, UserBaseInfo, UserStatus, Gender
from app.schemas.base import BizException
from app.schemas.asset import SignInStatusResponse, AssetOperation, SignInItemInfo, SignInRewardResponse
from app.schemas.mailbox import MailType
from app.db.models.user import UserRealNameHK, UserSetting, UserSignIn, UserSubscription
from app.db.models.mailbox import Mailbox
from app.core.errors import ErrorCode
from app.core.config import settings
from app.api.deps import Language
from alibabacloud_ocr_api20210707.client import Client as OcrClient
from alibabacloud_ocr_api20210707.models import RecognizeHKIdcardRequest
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util.client import Client as UtilClient
from app.services.app_store_api_tool import query_user_subscroption_status
from jwt import PyJWKClient
from datetime import datetime, timedelta, timezone
from app.db.session import redis_client
from sqlalchemy.ext.asyncio import AsyncSession
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr
import io, asyncio, jwt, json, uuid, random, smtplib, email, logging


logger = logging.getLogger(__name__)

async def distribute_newcomer_gift(db: AsyncSession, user_id: uuid.UUID):
    attachment = {
        "coin": 500,
        "stone1": 10,
        "stone2": 10,
        "stone3": 10,
        "description": "新人礼包"
    }
    mail = Mailbox(
        mail_id=f"mail_{uuid.uuid4()}",
        user_id=user_id,
        mail_type=MailType.REWARD,
        title_i18n={"en": "Newcomer Gift Pack", "zh-Hans": "新人礼包", "zh-Hant": "新人禮包"},
        content_i18n={
            "en": "Welcome to Sporreer! Ready to start your sporting career? We've prepared a welcome gift for you, have fun!", 
            "zh-Hans": "欢迎来到Sporreer，准备好开启你的运动生涯了吗？我们为您准备了一份见面礼，玩的开心！",
            "zh-Hant": "歡迎來到Sporreer，準備好開啟你的運動生涯了嗎？我們為您準備了一份見面禮，玩的開心！"
        },
        attachment = attachment,
        is_received = False,
        expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    )
    db.add(mail)

async def login_or_register(phone_number: str, db: AsyncSession):
    async with db.begin():
        isRegister = False
        user = await get_exist_user_by_phone(db, phone_number)
        if not user:
            user = await create_user(db, phone_number)
            user_info = UserBaseInfo.model_validate(user)
            isRegister = True
            await distribute_newcomer_gift(db, user.id)
        else:
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
                        remaining_str = "unknown"
                    raise BizException(code=ErrorCode.USER_BANNED, message="user.banned", params={"remaining": remaining_str})
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
            user_info.is_vip = user.subscription_info.is_active if user.subscription_info else False
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
            await distribute_newcomer_gift(db, user.id)
        else:
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
                        remaining_str = "unknown"
                    raise BizException(code=ErrorCode.USER_BANNED, message="user.banned", params={"remaining": remaining_str})
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
            user_info.is_vip = user.subscription_info.is_active if user.subscription_info else False
        token = create_access_token({"user_id": user.user_id})
        return token, user_info, is_register, user.role

async def login_or_register_email(email_address: str, db: AsyncSession):
    async with db.begin():
        isRegister = False
        user = await get_exist_user_by_email(db, email_address)
        if not user:
            user = await create_user_with_email(db, email_address)
            user_info = UserBaseInfo.model_validate(user)
            isRegister = True
            await distribute_newcomer_gift(db, user.id)
        else:
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
                        remaining_str = "unknown"
                    raise BizException(code=ErrorCode.USER_BANNED, message="user.banned", params={"remaining": remaining_str})
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
            user_info.is_vip = user.subscription_info.is_active if user.subscription_info else False
        token = create_access_token({"user_id": user.user_id})
        return token, user_info, isRegister, user.role

async def get_user_role(user_id: str, db: AsyncSession):
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
    return user.role

async def get_user_info(user_id: str, db: AsyncSession):
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
    if not user.settings:
        raise BizException(code=ErrorCode.USER_INFO_ERROR, message="user.info_error")
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
    user_info.is_vip = user.subscription_info.is_active if user.subscription_info else False
    return user_info

async def get_me_info(user_id: str, db: AsyncSession) -> tuple[UserBaseInfo, str | None]:
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
        if not user.settings:
            raise BizException(code=ErrorCode.USER_INFO_ERROR, message="user.info_error")
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

        subscription_status = user.subscription_info.is_active if user.subscription_info else False
        if not user.subscription_info or not user.subscription_info.is_active or not user.subscription_info.apple_original_transaction_id:
            user_info.is_vip = subscription_status
            return user_info, user.subscription_info.apple_original_transaction_id if user.subscription_info else None
        if (datetime.now(timezone.utc) > user.subscription_info.updated_at + timedelta(days=1)) or (user.subscription_info.end_at and datetime.now(timezone.utc) > user.subscription_info.end_at):
            transaction, transaction_payload, renew_payload = await query_user_subscroption_status(user.subscription_info.apple_original_transaction_id)
            #print(transaction.status, renew_payload)
            if transaction and transaction_payload and renew_payload and transaction_payload.appAccountToken == str(user.apple_iap_token):
                subscription_status = (transaction.status == 1 or transaction.status == 4)
                auto_renew = renew_payload.autoRenewStatus == 1
                started_at = (
                    datetime.fromtimestamp(renew_payload.recentSubscriptionStartDate / 1000, tz=timezone.utc)
                    if renew_payload.recentSubscriptionStartDate
                    else None
                )
                expired_at = (
                    datetime.fromtimestamp(renew_payload.renewalDate / 1000, tz=timezone.utc)
                    if renew_payload.renewalDate
                    else None
                )
                user.subscription_info.product_id = renew_payload.productId
                user.subscription_info.is_active = subscription_status
                user.subscription_info.auto_renew = auto_renew
                user.subscription_info.start_at = started_at
                user.subscription_info.end_at = expired_at
                user.subscription_info.apple_original_transaction_id = renew_payload.originalTransactionId
                user.subscription_info.apple_latest_transaction_id = transaction_payload.transactionId
                # 强制更新 updated_at
                user.subscription_info.updated_at = datetime.now(timezone.utc)
            else:
                # 订单查询异常
                logger.error(f"订单查询异常 {user.subscription_info.apple_original_transaction_id}")
                subscription_status = False
                user.subscription_info.is_active = subscription_status
                user.subscription_info.auto_renew = False
        user_info.is_vip = subscription_status
        return user_info, user.subscription_info.apple_original_transaction_id if user.subscription_info else None


async def update_user_info(user_id: str, form: UserUpdateForm, avatar_url: str, background_url: str, db: AsyncSession):
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
        if not user.settings:
            raise BizException(code=ErrorCode.USER_INFO_ERROR, message="user.info_error")
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
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
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
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
    if not user.settings:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户设置错误")
    user.settings.default_sport = sport
    await db.commit()
    return user.settings.default_sport

async def update_user_location_service(region: str, user_id: str, db: AsyncSession):
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
    user.location = region
    await db.commit()

def create_ocr_client() -> OcrClient:
    config = open_api_models.Config(
        access_key_id=settings.ALIYUN_ACCESS_KEY_ID,
        access_key_secret=settings.ALIYUN_ACCESS_KEY_SECRET
    )
    config.endpoint = settings.ALIYUN_OCR_ENDPOINT
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
    except Exception:
        logger.exception("HK ID card recognize failed with request error")
        raise BizException(code=ErrorCode.REALNAME_FAILED, message="identity.recognition_failed.realname")

async def realname_hk_service(user_id: str, front_bytes: bytes, db: AsyncSession):
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
        exist_info = await get_realname_info_by_user_id(db, user.id)
        if exist_info and (datetime.now(timezone.utc) < (exist_info.updated_at + timedelta(days=180))):
            raise BizException(code=ErrorCode.REALNAME_FAILED, message="identity.frequently_certified.realname")
    
        result = await recognize_hk_idcard(front_bytes)
        raw_data = result.get("body", {}).get("Data", {})
        if not raw_data:
            raise BizException(code=ErrorCode.REALNAME_FAILED, message="identity.recognition_failed.realname")
        try:
            parsed = json.loads(raw_data)
            data = parsed.get("data", {}) if isinstance(parsed, dict) else {}
        except Exception:
            logger.exception("HK ID card recognize failed with json.loads")
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
            raise BizException(code=ErrorCode.REALNAME_FAILED, message="identity.recognition_failed.realname")
        exist_card_info = await get_realname_info_by_card_id(db, nation_id)
        if exist_card_info:
            raise BizException(code=ErrorCode.REALNAME_FAILED, message="identity.has_certified.realname")

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
        if exist_info:
            bike_score = await bike_crud.get_score_by_user_id(db, user.id)
            if bike_score:
                bike_score.gender = gender
                bike_score.score = 0
            running_score = await running_crud.get_score_by_user_id(db, user.id)
            if running_score:
                running_score.gender = gender
                running_score.score = 0

async def verify_apple_identity_token(identity_token: str):
    try:
        jwks_client = PyJWKClient(settings.APPLE_KEYS_URL)
        signing_key = jwks_client.get_signing_key_from_jwt(identity_token)
        payload = jwt.decode(
            identity_token,
            signing_key.key,
            algorithms=["RS256"],
            audience="com.valbara.sporreer",
            issuer="https://appleid.apple.com"
        )
        return payload
    except Exception:
        logger.exception("Apple Token verified failed when verified apple account")
        return None

async def bind_phone_service(phone_number: str, user_id: str, db: AsyncSession):
    user = await get_exist_user_by_id(db, user_id)
    if not user:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
    if user.phone_number:
        raise BizException(code=ErrorCode.PHONE_NUMBER_ERROR, message="identity.with_phone.phone_bind")
    exist_phone = await get_exist_user_by_phone(db, phone_number)
    if exist_phone:
        raise BizException(code=ErrorCode.PHONE_NUMBER_ERROR, message="identity.already_certified.phone_bind")
    user.phone_number = phone_number
    await db.commit()

async def unbind_phone_service(user_id: str, db: AsyncSession):
    user = await get_exist_user_by_id(db, user_id)
    if not user:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
    if not user.phone_number:
        raise BizException(code=ErrorCode.PHONE_NUMBER_ERROR, message="identity.no_phone.phone_unbind")
    if not user.apple_id and not user.email:
        raise BizException(code=ErrorCode.PHONE_NUMBER_ERROR, message="identity.cannot_recover.phone_unbind")
    user.phone_number = None
    await db.commit()

async def bind_apple_id_service(token: str, user_id: str, db: AsyncSession) -> str:
    user = await get_exist_user_by_id(db, user_id)
    if not user:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
    if user.apple_id:
        raise BizException(code=ErrorCode.APPLE_ID_ERROR, message="identity.with_appleID.apple_bind")
    
    payload = await verify_apple_identity_token(token)
    if not payload:
        raise BizException(code=ErrorCode.APPLE_ID_ERROR, message="identity.verify_failed.apple_bind")
    apple_sub = payload.get("sub")  # Apple 提供的唯一用户 ID
    email = payload.get("email")
    if not apple_sub or not email:
        raise BizException(code=ErrorCode.APPLE_ID_ERROR, message="identity.verify_failed.apple_bind")
    exist_apple_id = await get_exist_user_by_apple_id(db, apple_sub)
    if exist_apple_id:
        raise BizException(code=ErrorCode.APPLE_ID_ERROR, message="identity.already_certified.apple_bind")
    user.apple_id = apple_sub
    user.apple_email = email
    await db.commit()
    return email

async def unbind_apple_id_service(user_id: str, db: AsyncSession):
    user = await get_exist_user_by_id(db, user_id)
    if not user:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
    if not user.apple_id:
        raise BizException(code=ErrorCode.APPLE_ID_ERROR, message="identity.no_appleID.apple_unbind")
    if not user.phone_number and not user.email:
        raise BizException(code=ErrorCode.APPLE_ID_ERROR, message="identity.cannot_recover.apple_unbind")
    user.apple_id = None
    user.apple_email = None
    await db.commit()


async def bind_email_service(email: str, user_id: str, db: AsyncSession) -> str:
    user = await get_exist_user_by_id(db, user_id)
    if not user:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
    if user.email:
        raise BizException(code=ErrorCode.EMAIL_ERROR, message="identity.with_email.email_bind")
    exist_email = await get_exist_user_by_email(db, email)
    if exist_email:
        raise BizException(code=ErrorCode.EMAIL_ERROR, message="identity.already_certified.email_bind")
    user.email = email
    await db.commit()

async def unbind_email_service(user_id: str, db: AsyncSession):
    user = await get_exist_user_by_id(db, user_id)
    if not user:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
    if not user.email:
        raise BizException(code=ErrorCode.EMAIL_ERROR, message="identity.no_email.email_unbind")
    if not user.apple_id and not user.phone_number:
        raise BizException(code=ErrorCode.EMAIL_ERROR, message="identity.cannot_recover.email_unbind")
    user.email = None
    await db.commit()


# 计算连续签到天数
async def compute_continuous_days(db: AsyncSession, user_id: uuid.UUID) -> int:
    today = get_today_hk_date()
    # 查询最近6天签到记录
    sign_in_history = await get_user_sign_in_history(db, user_id, 6)
    # 计算连续签到天数
    continuous_days = 0
    current_date = today - timedelta(days=1)
    for sign_in in sign_in_history:
        if sign_in.sign_in_date == current_date:
            continuous_days += 1
            current_date = current_date - timedelta(days=1)
        else:
            continue
    return continuous_days

# 签到状态查询服务
async def sign_in_status_service(db: AsyncSession, user_id: str) -> SignInStatusResponse:
    """查询用户签到状态"""
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
    
    today = get_today_hk_date()
    
    # 查询今日签到状态
    today_sign_in = await get_user_normal_sign_in_today(db, user.id, today)
    today_vip_sign_in = await get_user_vip_sign_in_today(db, user.id, today)
    today_signed = today_sign_in is not None
    today_signed_vip = today_vip_sign_in is not None
    
    continuous_days = await compute_continuous_days(db, user.id)
    
    # 构建签到奖励信息
    items = []
    for i in range(7):
        day_index = continuous_days + i
        reward = await get_sign_in_reward_by_day(db, today + timedelta(days=i), day_index)
        if not reward:
            raise BizException(code=ErrorCode.REWARD_CLAIM_FAILED, message="reward.data_error")
        items.append(SignInItemInfo(
            date=(today + timedelta(days=i)).strftime("%Y-%m-%d"),
            is_today=(i == 0),
            ccasset_type=reward.reward_type,
            ccasset_reward=reward.reward_count,
            ccasset_type_vip=reward.reward_type_vip,
            ccasset_reward_vip=reward.reward_count_vip
        ))
    
    return SignInStatusResponse(
        today_signed=today_signed,
        today_signed_vip=today_signed_vip,
        items=items
    )

async def sign_in_today_service(db: AsyncSession, user_id: str) -> SignInRewardResponse:
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
        today = get_today_hk_date()
        today_sign_in = await get_user_normal_sign_in_today(db, user.id, today)
        today_signed = today_sign_in is not None
        if today_signed:
            raise BizException(code=ErrorCode.REWARD_CLAIM_FAILED, message="reward.repeat_claimed")
        sign_in = UserSignIn(
            user_id=user.id,
            sign_in_date=today,
            is_vip=False
        )
        db.add(sign_in)
        continuous_days = await compute_continuous_days(db, user.id)
        reward = await get_sign_in_reward_by_day(db, today, continuous_days)
        new_amount = await reward_ccasset(db, reward.reward_type, reward.reward_count, user.id, "签到奖励", AssetOperation.REWARD)
        return SignInRewardResponse(ccasset_type=reward.reward_type, new_ccamount=new_amount, date=today.strftime("%Y-%m-%d"))

async def sign_in_today_vip_service(db: AsyncSession, user_id: str) -> SignInRewardResponse:
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
        if not user.subscription_info or not user.subscription_info.is_active:
            raise BizException(code=ErrorCode.REWARD_CLAIM_FAILED, message="reward.no_auth.sign_in")
        today = get_today_hk_date()
        today_sign_in = await get_user_vip_sign_in_today(db, user.id, today)
        today_signed = today_sign_in is not None
        if today_signed:
            raise BizException(code=ErrorCode.REWARD_CLAIM_FAILED, message="reward.repeat_claimed")
        sign_in = UserSignIn(
            user_id=user.id,
            sign_in_date=today,
            is_vip=True
        )
        db.add(sign_in)
        continuous_days = await compute_continuous_days(db, user.id)
        reward = await get_sign_in_reward_by_day(db, today, continuous_days)
        new_amount = await reward_ccasset(db, reward.reward_type_vip, reward.reward_count_vip, user.id, "签到奖励", AssetOperation.REWARD)
        return SignInRewardResponse(ccasset_type=reward.reward_type_vip, new_ccamount=new_amount, date=today.strftime("%Y-%m-%d"))


def _send_smtp(username, password, receivers, msg_str):
    #client = smtplib.SMTP('smtpdm-ap-southeast-1.aliyuncs.com', 80, timeout=5)
    client = smtplib.SMTP_SSL(settings.ALIYUN_EMAIL_ENDPOINT, 465, timeout=5)
    client.set_debuglevel(0)
    client.login(username, password)
    client.sendmail(username, receivers, msg_str)
    client.quit()

# 发送验证码邮件
async def send_email_code_service(to_email: str, lang: Language):
    """
    发送验证码邮件，不接收回信
    :param to_email: 收件人邮箱
    """

    key = f"email:{to_email}"
    code = await redis_client.get(key)
    if not code:
        code = str(random.randint(100000, 999999))
    await redis_client.set(key, code, ex=300)  # 5分钟有效
    
    username = settings.NOREPLY_EMAIL_ADDRESS
    password = settings.NOREPLY_EMAIL_PASSWORD
    receivers = [to_email]

    if lang == Language.en:
        title0 = "Your login verification code"
        title1 = "Your verification Code:"
        title2 = "Please enter this code within 5 minutes. Do not share it with anyone."
        title3 = "If you did not request this, you can safely ignore this email, please do not reply to this email."
        title4 = "Sporreer Team"
    elif lang == Language.zh_hant:
        title0 = "你的登入驗證碼"
        title1 = "你的驗證碼:"
        title2 = "請在5分鐘內輸入此驗證碼。請勿將此驗證碼透露給任何人。"
        title3 = "如果您沒有提出這樣的請求，您可以忽略這封郵件，請勿回覆此郵件。"
        title4 = "Sporreer 團隊"
    else:
        title0 = "你的登录验证码"
        title1 = "你的验证码:"
        title2 = "请在5分钟内输入此验证码。请勿将此验证码透露给任何人。"
        title3 = "如果您没有提出这样的请求，您可以忽略这封邮件，请勿回复此邮件。"
        title4 = "Sporreer 团队"

    if settings.ENV.lower() == "dev":
        title0 += "（测试）"

    # 构建邮件
    msg = MIMEMultipart('alternative')
    msg['Subject'] = Header(f"【Sporreer】{title0}", "UTF-8")
    msg['From'] = formataddr(("Sporreer", username))
    msg['To'] = to_email
    msg['Date'] = email.utils.formatdate()
    msg['Message-id'] = email.utils.make_msgid()

    # 组装 HTML
    html = f"""
    <html>
        <body>
            <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; padding: 24px; max-width: 420px; margin: auto;">

            <p style="font-size:16px; color:#333; margin-bottom: 6px;">
                {title1}
            </p>

            <p style="font-size:36px; font-weight:700; background:#f6f6f6; padding:12px 18px; border-radius:8px; display:inline-block; letter-spacing:3px; margin-bottom: 16px;">
                {code}
            </p>

            <p style="font-size:15px; color:#555;">
                {title2}
            </p>

            <hr style="border:none; border-top:1px solid #eee; margin: 24px 0;" />

            <p style="font-size:13px; color:#999;">
                {title3}
            </p>

            <p style="font-size:14px; color:#666; margin-top: 18px;">-· {title4} ·-</p>
            </div>
        </body>
    </html>
    """

    msg.attach(MIMEText(html, _subtype='html', _charset='UTF-8'))

    # 发送邮件
    try:
        # 线程池方式执行 SMTP 发送，避免阻塞 event loop
        await asyncio.wait_for(asyncio.to_thread(_send_smtp, username, password, receivers, msg.as_string()), timeout=5)
        #print("邮件发送成功:", to_email, code)
        return
    except Exception:
        logger.exception("Email send task failed")
        raise BizException(code=ErrorCode.EMAIL_SERVICE_ERROR, message="sms.service_error")

async def verify_email_code(email_address: str, code: str) -> bool:
    if email_address == "sporreer_test0@valbara.top":
        return code == "000000"
    key = f"email:{email_address}"
    real_code = await redis_client.get(key)
    return real_code == code

async def verify_test_account(db: AsyncSession, email_address: str, password: str) -> bool:
    account = await get_test_account(db, email_address)
    await db.commit()
    return account.password == password if account else False