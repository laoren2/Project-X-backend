from app.crud.user import (
    create_user, get_user_by_id, get_banned_history_by_user_id,
    create_user_with_apple, get_realname_info_by_user_id, get_test_account,
    get_realname_info_by_country_method_card, get_settings_by_user_id, get_exist_user_by_phone,
    get_exist_user_by_apple_id, get_exist_user_by_id, get_sign_in_rewards, 
    get_user_normal_sign_in_today, get_user_sign_in_history, get_exist_user_by_email,
    get_user_vip_sign_in_today, get_sign_in_reward_by_day, create_user_with_email
)
from app.crud.asset_manage import reward_ccasset
from app.core.tools import get_today_hk_date, get_user_local_date, hash_card_id
import app.crud.competition.bike as bike_crud
import app.crud.competition.running as running_crud
from app.core.security import create_access_token
from app.schemas.common import SportType, CCAssetBaseInfo
from app.schemas.user import UserUpdateForm, UserBaseInfo, UserStatus, Gender, RealNameMethod
from app.schemas.base import BizException
from app.schemas.asset import SignInStatusResponse, AssetOperation, SignInItemInfo, SignInRewardResponse
from app.schemas.mailbox import MailType
from app.db.models.user import User, UserRealNameIdentity, UserSetting, UserSignIn, UserSubscription
from app.db.models.mailbox import Mailbox
from app.core.errors import ErrorCode
from app.core.config import settings
from app.api.deps import Language
from alibabacloud_ocr_api20210707.client import Client as OcrClient
from alibabacloud_ocr_api20210707.models import (
    RecognizeHKIdcardRequest, RecognizePassportRequest, RecognizeChinesePassportRequest,
    RecognizeInternationalIdcardRequest, RecognizeGeneralRequest
)
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util.client import Client as UtilClient
from app.services.app_store_api_tool import query_user_subscroption_status
from jwt import PyJWKClient
from datetime import datetime, timedelta, timezone, date
from app.db.session import redis_client
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr
from functools import lru_cache
import io, asyncio, jwt, json, uuid, random, smtplib, email, logging, re


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
        title_i18n={"en": "Newcomer Gift Pack", "zh-Hans": "新人礼包", "zh-Hant": "新人禮包", "ko": "신규 사용자 선물 세트"},
        content_i18n={
            "en": "Welcome to Sporreer! Ready to start your sporting career? We've prepared a welcome gift for you, have fun!", 
            "zh-Hans": "欢迎来到Sporreer，准备好开启你的运动生涯了吗？我们为您准备了一份见面礼，玩的开心！",
            "zh-Hant": "歡迎來到Sporreer，準備好開啟你的運動生涯了嗎？我們為您準備了一份見面禮，玩的開心！",
            "ko": "Sporreer 오신 것을 환영합니다! 스포츠 선수 생활을 시작할 준비가 되셨나요? 여러분을 위한 환영 선물을 준비했습니다. 즐거운 시간 보내세요!"
        },
        attachment = attachment,
        is_received = False,
        expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    )
    db.add(mail)

# 更新赛季时可调用
async def generate_season_score(db: AsyncSession, user_id: uuid.UUID):
    bike_season = await bike_crud.get_season_now(db)
    if not bike_season:
        return
    await bike_crud.add_or_update_career_score(db, bike_season.id, Gender.male, user_id, 0, 0)
    running_season = await running_crud.get_season_now(db)
    if not running_season:
        return
    await running_crud.add_or_update_career_score(db, running_season.id, Gender.male, user_id, 0, 0)

async def login_or_register(db: AsyncSession, phone_number: str, timezone: str):
    async with db.begin():
        isRegister = False
        user = await get_exist_user_by_phone(db, phone_number)
        if not user:
            user = await create_user(db, phone_number, timezone)
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
                user_info.birthday = user.real_name_info.birth_date.strftime("%Y-%m-%d")
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

async def login_or_register_apple(db: AsyncSession, apple_id: str, email: str, timezone: str):
    async with db.begin():
        user = await get_exist_user_by_apple_id(db, apple_id)
        is_register = False
        if not user:
            user = await create_user_with_apple(db, apple_id, email, timezone)
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
                user_info.birthday = user.real_name_info.birth_date.strftime("%Y-%m-%d")
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

async def login_or_register_email(db: AsyncSession, email_address: str, timezone: str):
    async with db.begin():
        isRegister = False
        user = await get_exist_user_by_email(db, email_address)
        if not user:
            user = await create_user_with_email(db, email_address, timezone)
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
                user_info.birthday = user.real_name_info.birth_date.strftime("%Y-%m-%d")
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
        user_info.birthday = user.real_name_info.birth_date.strftime("%Y-%m-%d")
    user_info.is_display_gender = user.settings.is_display_gender
    user_info.is_display_age = user.settings.is_display_age
    user_info.is_display_location = user.settings.is_display_location
    user_info.enable_auto_location = user.settings.enable_auto_location
    user_info.is_display_identity = user.settings.is_display_identity
    user_info.default_sport = user.settings.default_sport
    user_info.is_vip = user.subscription_info.is_active if user.subscription_info else False
    return user_info

async def get_me_info(db: AsyncSession, user_id: str, timezone: str | None) -> tuple[UserBaseInfo, str | None]:
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
        if not user.settings:
            raise BizException(code=ErrorCode.USER_INFO_ERROR, message="user.info_error")
        user.timezone = timezone if timezone else "UTC"
        user_info = UserBaseInfo.model_validate(user)
        if user.real_name_info:
            user_info.gender = user.real_name_info.gender
            user_info.birthday = user.real_name_info.birth_date.strftime("%Y-%m-%d")
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
                    datetime.fromtimestamp(transaction_payload.expiresDate / 1000, tz=timezone.utc)
                    if transaction_payload.expiresDate
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
            user_info.birthday = user.real_name_info.birth_date.strftime("%Y-%m-%d")
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

@lru_cache(maxsize=1)
def create_ocr_client() -> OcrClient:
    config = open_api_models.Config(
        access_key_id=settings.ALIYUN_ACCESS_KEY_ID,
        access_key_secret=settings.ALIYUN_ACCESS_KEY_SECRET
    )
    config.endpoint = settings.ALIYUN_OCR_ENDPOINT
    return OcrClient(config)


async def _get_realname_info_from_ocr(country_code: str, method: RealNameMethod, image_bytes: bytes) -> tuple[Gender, str, date]:
    country_code = (country_code or "").upper()
    if not image_bytes:
        raise BizException(code=ErrorCode.REALNAME_FAILED, message="identity.recognition_failed.realname")

    if country_code == "HK":
        if method == RealNameMethod.idcard:
            return await get_realname_info_hk_idcard(image_bytes)
        if method == RealNameMethod.passport:
            return await get_realname_info_hk_passport(image_bytes)

    if country_code == "TW":
        if method == RealNameMethod.idcard:
            return await get_realname_info_tw_idcard(image_bytes)
        if method == RealNameMethod.passport:
            return await get_realname_info_tw_passport(image_bytes)

    if country_code == "KR":
        if method == RealNameMethod.idcard:
            return await get_realname_info_kr_idcard(image_bytes)
        if method == RealNameMethod.passport:
            return await get_realname_info_kr_passport(image_bytes)

    raise BizException(code=ErrorCode.REALNAME_FAILED, message="identity.recognition_failed.realname")


def _parse_aliyun_ocr_data(result: dict) -> dict:
    """
    统一解析阿里云 OCR 返回结构，尽量抽取出 data 字典。
    兼容 data 在 root 或 face 中的情况。
    """
    raw = result.get("body", {}).get("Data")
    if raw is None or raw == "":
        return {}

    # 先解析 Data
    if isinstance(raw, dict):
        parsed = raw
    else:
        try:
            parsed = json.loads(raw)
        except Exception:
            logger.exception("OCR parse failed with json.loads")
            return {}

    if not isinstance(parsed, dict):
        return {}

    # 从 data 字段取
    if isinstance(parsed.get("data"), dict):
        return parsed["data"]

    # 再 fallback：直接返回 parsed
    return parsed


def _normalize_birth_date(value) -> date | None:
    """
    将各种出生日期输入规整为 `datetime.date`。
    - 支持: "DD-MM-YYYY", "YYYY-MM-DD", "YYYY/MM/DD", "YYYY.MM.DD", "YYYY年MM月DD日", "YYYYMMDD"
    - 支持: datetime/date 直接传入
    """
    if not value:
        return None

    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    s = str(value).strip()
    s = s.replace("年", "-").replace("月", "-").replace("日", "")
    s = s.replace(".", "-").replace("/", "-")

    # 允许 YYYY-MM-DD 或 YYYYMMDD
    # 优先匹配 YYYY-MM-DD / YYYYMMDD
    m = re.search(r"(\d{4})-?(\d{2})-?(\d{2})", s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except Exception:
            pass

    # 再尝试匹配 DD-MM-YYYY
    m = re.search(r"(\d{2})-(\d{2})-(\d{4})", s)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except Exception:
            pass

    # 再尝试匹配 YY-MM-DD（如 88-08-08）
    m = re.search(r"(\d{2})-(\d{2})-(\d{2})", s)
    if m:
        try:
            year = int(m.group(1))
            current_year = date.today().year % 100
            year += 2000 if year <= current_year else 1900
            return date(year, int(m.group(2)), int(m.group(3)))
        except Exception:
            pass

    return None


def _gender_from_str(value: str) -> Gender | None:
    if not value:
        return None

    s = str(value).strip().lower()

    # 精确匹配优先（避免 female 被识别成 male）
    if s in ("m", "male", "男"):
        return Gender.male
    if s in ("f", "female", "女"):
        return Gender.female

    # 再做模糊匹配
    if "男" in s:
        return Gender.male
    if "女" in s:
        return Gender.female

    return None


def _birth_date_gender_from_kr_card_number(card_number: str) -> tuple[Gender | None, date | None]:
    """
    韩国身份证号：YYMMDD-SXXXXXX（共 13 位数字，可含分隔符，例如 900101-1234567）

    规则：
    - 出生日期：前 6 位 YYMMDD（根据性别位 S 推断世纪）
    - 性别/世纪：
        - S in {1,2}: 1900 年代（1 男 2 女）
        - S in {3,4}: 2000 年代（3 男 4 女）
        - S in {5,6}: 1900 年代（5 男 6 女）
        - S in {7,8}: 2000 年代（7 男 8 女）
    """
    if not card_number:
        return None, None

    digits = re.sub(r"\D", "", str(card_number))
    if len(digits) != 13:
        return None, None

    yy = digits[0:2]
    mm = digits[2:4]
    dd = digits[4:6]
    s = digits[6]

    if s not in ("1", "2", "3", "4", "5", "6", "7", "8"):
        return None, None

    if s in ("1", "2", "5", "6"):
        century = "19"
    else:
        century = "20"

    full_year = f"{century}{yy}"
    birth_date = _normalize_birth_date(f"{full_year}-{mm}-{dd}")

    if s in ("1", "3", "5", "7"):
        gender = Gender.male
    else:
        gender = Gender.female

    return gender, birth_date

def validate_tw_id(card_id: str) -> bool:
    if not re.match(r"^[A-Z][12]\d{8}$", card_id):
        return False

    code_map = {
        'A':10,'B':11,'C':12,'D':13,'E':14,'F':15,'G':16,'H':17,
        'I':34,'J':18,'K':19,'L':20,'M':21,'N':22,'O':35,'P':23,
        'Q':24,'R':25,'S':26,'T':27,'U':28,'V':29,'W':32,'X':30,
        'Y':31,'Z':33
    }

    code = code_map[card_id[0]]
    digits = [int(x) for x in card_id[1:]]

    total = (code // 10) + (code % 10) * 9

    weights = [8,7,6,5,4,3,2,1,1]

    for i in range(9):
        total += digits[i] * weights[i]
    return total % 10 == 0


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

async def recognize_chinese_passport(image_bytes: bytes) -> dict:
    """
    调用阿里云中国护照识别（用于 HK/TW passport）
    """
    client = create_ocr_client()
    request = RecognizeChinesePassportRequest(body=io.BytesIO(image_bytes))
    try:
        response = await asyncio.to_thread(client.recognize_chinese_passport, request)
        return UtilClient.to_map(response)
    except Exception:
        logger.exception("Chinese passport recognize failed with request error")
        raise BizException(code=ErrorCode.REALNAME_FAILED, message="identity.recognition_failed.realname")


async def recognize_passport(image_bytes: bytes) -> dict:
    """
    调用阿里云护照识别（用于 KR passport）
    """
    client = create_ocr_client()
    request = RecognizePassportRequest(body=io.BytesIO(image_bytes))
    try:
        response = await asyncio.to_thread(client.recognize_passport, request)
        return UtilClient.to_map(response)
    except Exception:
        logger.exception("Passport recognize failed with request error")
        raise BizException(code=ErrorCode.REALNAME_FAILED, message="identity.recognition_failed.realname")


async def recognize_international_idcard(image_bytes: bytes, country: str) -> dict:
    """
    调用阿里云国际身份证识别（用于 KR idcard）
    """
    client = create_ocr_client()
    request = RecognizeInternationalIdcardRequest(country=country, body=io.BytesIO(image_bytes))
    try:
        response = await asyncio.to_thread(client.recognize_international_idcard, request)
        return UtilClient.to_map(response)
    except Exception:
        logger.exception("International ID card recognize failed with request error")
        raise BizException(code=ErrorCode.REALNAME_FAILED, message="identity.recognition_failed.realname")


async def recognize_general(image_bytes: bytes) -> dict:
    """
    调用阿里云通用文字识别（用于 TW idcard）
    """
    client = create_ocr_client()
    request = RecognizeGeneralRequest(body=io.BytesIO(image_bytes))
    try:
        response = await asyncio.to_thread(client.recognize_general, request)
        return UtilClient.to_map(response)
    except Exception:
        logger.exception("General recognize failed with request error")
        raise BizException(code=ErrorCode.REALNAME_FAILED, message="identity.recognition_failed.realname")


async def get_realname_info_hk_idcard(image_bytes: bytes) -> tuple[Gender, str, date]:
    result = await recognize_hk_idcard(image_bytes)
    #print(result)
    data = _parse_aliyun_ocr_data(result)
    #print(data)
    if not data:
        raise BizException(code=ErrorCode.REALNAME_FAILED, message="identity.recognition_failed.realname")
    # 3. 提取需要的字段
    #name_Cn = data.get("nameCn", "")
    #name_En = data.get("nameEn", "")
    gender = _gender_from_str(data.get("sex", ""))
    nation_id = (data.get("idNumber") or data.get("cardNumber") or "").strip()
    birth_date = _normalize_birth_date(data.get("birthDate", ""))
    #name_code = data.get("nameCode", "")
    #issued_code = data.get("issuedCode", "")
    if not (gender and nation_id and birth_date):
        raise BizException(code=ErrorCode.REALNAME_FAILED, message="identity.recognition_failed.realname")
    return gender, nation_id, birth_date


async def get_realname_info_hk_passport(image_bytes: bytes) -> tuple[Gender, str, date]:
    result = await recognize_chinese_passport(image_bytes)
    #print(result)
    data = _parse_aliyun_ocr_data(result)
    #print(data)
    if not data:
        raise BizException(code=ErrorCode.REALNAME_FAILED, message="identity.recognition_failed.realname")
    gender = _gender_from_str(data.get("sex", ""))
    passport_no = (data.get("passportNumber") or data.get("passportNo") or data.get("idNumber") or "").strip()
    birth_date = _normalize_birth_date(data.get("birthDate") or data.get("birthday") or "")
    #print(gender, passport_no, birth_date)
    if not (gender and passport_no and birth_date):
        raise BizException(code=ErrorCode.REALNAME_FAILED, message="identity.recognition_failed.realname")
    return gender, passport_no, birth_date


async def get_realname_info_tw_passport(image_bytes: bytes) -> tuple[Gender, str, date]:
    # 你指定 TW passport 复用 RecognizeChinesePassportRequest
    return await get_realname_info_hk_passport(image_bytes)


async def get_realname_info_kr_passport(image_bytes: bytes) -> tuple[Gender, str, date]:
    result = await recognize_passport(image_bytes)
    #print(result)
    data = _parse_aliyun_ocr_data(result)
    #print(data)
    if not data:
        raise BizException(code=ErrorCode.REALNAME_FAILED, message="identity.recognition_failed.realname")
    passport_no = (data.get("passportNumber") or data.get("passportNo") or data.get("idNumber") or "").strip()
    birth_date = _normalize_birth_date(data.get("birthDateYmd") or data.get("birthDate") or "")
    gender = _gender_from_str(data.get("sex", ""))
    #print(gender, passport_no, birth_date)
    if not (gender and passport_no and birth_date):
        raise BizException(code=ErrorCode.REALNAME_FAILED, message="identity.recognition_failed.realname")
    return gender, passport_no, birth_date


async def get_realname_info_kr_idcard(image_bytes: bytes) -> tuple[Gender, str, date]:
    result = await recognize_international_idcard(image_bytes, "Korea")
    #print("result:", result)
    data = _parse_aliyun_ocr_data(result)
    #print("data:", data)
    if not data:
        raise BizException(code=ErrorCode.REALNAME_FAILED, message="identity.recognition_failed.realname")
    face = data.get("face", {})
    inner = face.get("data", {})
    card_number = (inner.get("cardNumber") or inner.get("idNumber") or "").strip()
    gender, birth_date = _birth_date_gender_from_kr_card_number(card_number)
    #print(gender, card_number, birth_date)
    if not (gender and card_number and birth_date):
        raise BizException(code=ErrorCode.REALNAME_FAILED, message="identity.recognition_failed.realname")
    return gender, card_number, birth_date


async def get_realname_info_tw_idcard(image_bytes: bytes) -> tuple[Gender, str, date]:
    """
    TW 身份证：走通用文字识别。这里做容错提取：
    - 证件号：优先匹配 1 个字母 + 9 位数字（台湾身份证常见）
    - 性别：若证件号符合规则，用第 2 位 1/2 推断
    - 出生日期：从全文中抓取 YYYY-MM-DD / YYYY/MM/DD / YYYYMMDD
    """
    result = await recognize_general(image_bytes)
    #print(result)
    data = _parse_aliyun_ocr_data(result)
    #print(data)
    if not data:
        raise BizException(code=ErrorCode.REALNAME_FAILED, message="identity.recognition_failed.realname")

    words = [item.get("word", "") for item in data.get("prism_wordsInfo", [])]

    # 拼接所有文本（用于正则全局匹配）
    full_text = " ".join(words)

    # 身份证号（統一編號）
    id_match = re.search(r"[A-Z][12]\d{8}", full_text)
    card_id = id_match.group(0) if id_match else None

    # 性别
    gender = None
    for w in words:
        if "性别" in w or "性別" in w:
            if "男" in w:
                gender = "male"
            elif "女" in w:
                gender = "female"
    # fallback（OCR拆词情况）
    if not gender:
        if "男" in words:
            gender = "male"
        elif "女" in words:
            gender = "female"

    # 出生日期（民國 → 西元）
    birth_date = None
    birth_match = re.search(
        r"出\s*生\s*年?\s*月?\s*日?\s*[:：]?\s*"
        r"(?:民國\s*)?"
        r"(\d{2,3})\s*年"
        r"(?:\s*\d{1,2})?\s*"   # 允许多余数字
        r"(\d{1,2})\s*月"
        r"(?:\s*\d{1,2})?\s*"   # 再允许一次噪声
        r"(\d{1,2})\s*日",
        full_text
    )

    if birth_match:
        year = int(birth_match.group(1)) + 1911
        month = int(birth_match.group(2))
        day = int(birth_match.group(3))
        try:
            birth_date = date(year, month, day)
        except:
            birth_date = None
    #print(gender, card_id, birth_date)
    if not (gender and card_id and birth_date):
        raise BizException(code=ErrorCode.REALNAME_FAILED, message="identity.recognition_failed.realname")
    if not validate_tw_id(card_id):
        raise BizException(code=ErrorCode.REALNAME_FAILED, message="identity.recognition_failed.realname")
    #print(gender, card_id, birth_date)
    return gender, card_id, birth_date


# 实名认证
async def realname_service(
    db: AsyncSession,
    user_id: str,
    front_bytes: bytes,
    country_code: str,
    method: RealNameMethod
):
    normalized_country_code = (country_code or "").upper()
    # OCR/解析放在事务外，避免长事务占锁
    gender, nation_id, birth_date = await _get_realname_info_from_ocr(normalized_country_code, method, front_bytes)
    #print(gender, nation_id, birth_date)
    if not (gender and nation_id and birth_date):
        raise BizException(code=ErrorCode.REALNAME_FAILED, message="identity.recognition_failed.realname")
    card_id_hash = hash_card_id(nation_id)

    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")

        exist_info = await get_realname_info_by_user_id(db, user.id)
        if exist_info and (datetime.now(timezone.utc) < (exist_info.updated_at + timedelta(days=180))):
            raise BizException(code=ErrorCode.REALNAME_FAILED, message="identity.frequently_certified.realname")

        exist_card_info = await get_realname_info_by_country_method_card(db, normalized_country_code, method, card_id_hash)
        #print(exist_card_info)
        if exist_card_info:
            raise BizException(code=ErrorCode.REALNAME_FAILED, message="identity.has_certified.realname")

        try:
            # 这里写回数据库，只存识别字段，不存证件图片
            if exist_info:
                exist_info.country_code = normalized_country_code
                exist_info.method = method
                exist_info.gender = gender
                exist_info.birth_date = birth_date
                exist_info.card_id_hash = card_id_hash
            else:
                realname_info = UserRealNameIdentity(
                    user_id=user.id,
                    country_code=normalized_country_code,
                    method=method,
                    gender=gender,
                    birth_date=birth_date,
                    card_id_hash=card_id_hash
                )
                db.add(realname_info)

            # flush 以便尽早触发唯一约束冲突并转换为业务错误
            await db.flush()
        except IntegrityError:
            logger.exception("Realname upsert failed with integrity error")
            raise BizException(code=ErrorCode.REALNAME_FAILED, message="identity.has_certified.realname")

        # 若是重认证（存在旧记录），同步重置当季分数
        if exist_info:
            bike_score = await bike_crud.get_score_by_season_and_user(db, user.id)
            if bike_score:
                bike_score.gender = gender
                bike_score.score = 0
            running_score = await running_crud.get_score_by_season_and_user(db, user.id)
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
async def compute_continuous_days(db: AsyncSession, user: User) -> int:
    today = get_user_local_date(user)
    # 查询最近6天签到记录
    sign_in_history = await get_user_sign_in_history(db, user, 6)
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
    
    today = get_user_local_date(user)
    
    # 查询今日签到状态
    today_sign_in = await get_user_normal_sign_in_today(db, user.id, today)
    today_vip_sign_in = await get_user_vip_sign_in_today(db, user.id, today)
    today_signed = today_sign_in is not None
    today_signed_vip = today_vip_sign_in is not None
    
    continuous_days = await compute_continuous_days(db, user)
    
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
        today = get_user_local_date(user)
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
        continuous_days = await compute_continuous_days(db, user)
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
        today = get_user_local_date(user)
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
        continuous_days = await compute_continuous_days(db, user)
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