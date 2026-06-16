from app.core.config import settings
from app.core.errors import ErrorCode
from app.schemas.base import BizException, Language
from app.db.session import redis_client
from alibabacloud_dysmsapi20180501.client import Client as DysmsapiClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_dysmsapi20180501 import models as dysmsapi_models
from alibabacloud_tea_util.client import Client as UtilClient
import asyncio, random, logging

logger = logging.getLogger(__name__)


def create_dysmsapi_client() -> DysmsapiClient:
    """
    使用AK&SK初始化账号Client
    """
    config = open_api_models.Config(
        access_key_id=settings.ALIYUN_ACCESS_KEY_ID,
        access_key_secret=settings.ALIYUN_ACCESS_KEY_SECRET
    )
    config.endpoint = settings.ALIYUN_SMS_ENDPOINT
    #config.connect_timeout = 5
    #config.read_timeout = 5
    return DysmsapiClient(config)

async def send_message_to_globe(
    to: str,
    message: str,
    from_: str
) -> bool:
    client = create_dysmsapi_client()
    request = dysmsapi_models.SendMessageToGlobeRequest(
        from_=from_,
        message=message,
        to=to
    )
    try:
        response = await asyncio.wait_for(asyncio.to_thread(client.send_message_to_globe, request), timeout=5)
        return response.body.response_code == "OK"
    except Exception:
        #print(f"send_message_to_globe failed with error: {e}")
        logger.exception("Gloabl sms send task failed")
        raise BizException(code=ErrorCode.SMS_SERVICE_ERROR, message="sms.service_error")

async def send_sms_code_service(phone_number: str, lang: Language):
    key = f"sms:{phone_number}"              # 验证码key（5分钟有效）
    rate_key = f"sms:rate:{phone_number}"   # 发送频率限制key（60秒）

    # 60秒内限制重复发送
    if await redis_client.get(rate_key):
        raise BizException(code=ErrorCode.SMS_SERVICE_ERROR, message="sms.too_frequent")

    code = await redis_client.get(key)
    if not code:
        code = str(random.randint(100000, 999999))
        # 先写入验证码（5分钟有效）
        await redis_client.set(key, code, ex=300)
    # 设置发送频率限制（60秒）
    await redis_client.set(rate_key, "1", ex=60)
    
    if lang == Language.zh_hans:
        msg = f"【Movmov】您的验证码是：{code}，请在5分钟内输入此码完成操作。如非本人操作，请忽略本短信。"
    elif lang == Language.zh_hant:
        msg = f"【Movmov】您的驗證碼是：{code}，請在5分鐘內輸入此碼完成操作。如非本人操作，請忽略本短信。"
    elif lang == Language.ko:
        msg = f"[Movmov] 인증번호는 {code}입니다. 5분 내에 입력해 주세요. 타인에게 공유하지 마세요."
    elif lang == Language.ja:
        msg = f"Movmov : 認証コードは {code} です。5分以内に入力してください。"
    elif lang == Language.fr:
        msg = f"Movmov : votre code de vérification est {code}. Il expirera dans 5 minutes. Ne partagez ce code avec personne."
    else:
        msg = f"Movmov: Your verification code is: {code}. It will expire in 5 minutes. Do not share this code with anyone."
    if settings.ENV.lower() == "dev":
        msg += "（测试）"
    result = await send_message_to_globe(
        to=phone_number,
        message=msg,
        from_="ValbaraTech"
    )
    if not result:
        raise BizException(code=ErrorCode.SMS_SERVICE_ERROR, message="sms.service_error")
    #print(f"【调试用】发送验证码 {code} 到 {phone_number}")
    return code

async def verify_sms_code(phone_number: str, code: str):
    key = f"sms:{phone_number}"
    real_code = await redis_client.get(key)
    return real_code == code
