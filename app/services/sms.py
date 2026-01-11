from app.core.config import settings
from app.core.errors import ErrorCode
from app.schemas.base import BizException
from app.db.session import redis_client
from alibabacloud_dysmsapi20180501.client import Client as DysmsapiClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_dysmsapi20180501 import models as dysmsapi_models
from alibabacloud_tea_util.client import Client as UtilClient
import asyncio, random


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
    except Exception as e:
        #print(f"send_message_to_globe failed with error: {e}")
        raise BizException(code=ErrorCode.SMS_SERVICE_ERROR, message="sms.service_error")

async def send_sms_code_service(phone_number: str):
    key = f"sms:{phone_number}"
    code = await redis_client.get(key)
    #    raise BizException(code=ErrorCode.SMS_SERVICE_ERROR, message="请勿频繁请求验证码")
    if not code:
        code = str(random.randint(100000, 999999))
        await redis_client.set(key, code, ex=300)  # 5分钟有效
    # 这里应调用短信服务商API发送验证码
    result = await send_message_to_globe(
        to=f"852{phone_number}",
        message=f"【Sporreer】您的驗證碼是：{code}，請在 5 分鐘內輸入此碼完成操作。如非本人操作，請忽略本短信。",
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
