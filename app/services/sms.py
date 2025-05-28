import random
import redis.asyncio as aioredis
from app.core.config import settings
from app.core.errors import ErrorCode
from app.schemas.base import BizException

redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

async def send_sms_code(phone_number: str):
    key = f"sms:{phone_number}"
    if await redis_client.get(key):
        raise BizException(code=ErrorCode.SMS_SERVICE_ERROR, message="请勿频繁请求验证码")
    code = str(random.randint(100000, 999999))
    await redis_client.set(key, code, ex=300)  # 5分钟有效
    # 这里应调用短信服务商API发送验证码
    print(f"【调试用】发送验证码 {code} 到 {phone_number}")
    return code

async def verify_sms_code(phone_number: str, code: str):
    key = f"sms:{phone_number}"
    real_code = await redis_client.get(key)
    return real_code == code
