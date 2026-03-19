from pydantic_settings import BaseSettings
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
from starlette.requests import Request
import os

class CustomStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope) -> FileResponse:
        response: FileResponse = await super().get_response(path, scope)
        
        if path.endswith(".png") or path.endswith(".jpg"):
            response.headers["Cache-Control"] = "public, max-age=86400"  # 1 day
        else:
            response.headers["Cache-Control"] = "public, max-age=3600"  # 1 hour
        
        return response


class Settings(BaseSettings):
    PROJECT_NAME: str = "SportsX 用户中心"
    ENV: str
    DATABASE_URL: str
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 5
    REDIS_URL: str
    REDIS_MAX_CONNECTIONS: int = 50
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200    # 默认 30 天
    MIN_APP_VERSION: str = "1.0.0"              # 默认最低版本
    GEOIP_DB_PATH: str = "app/resources/CN_ip.mmdb"
    ALIYUN_ACCESS_KEY_ID: str
    ALIYUN_ACCESS_KEY_SECRET: str
    ALIYUN_OCR_ENDPOINT: str
    ALIYUN_SMS_ENDPOINT: str
    ALIYUN_EMAIL_ENDPOINT: str
    APPLE_KEYS_URL: str
    APPLE_IAP_ISSUER_ID: str
    NOREPLY_EMAIL_ADDRESS: str
    NOREPLY_EMAIL_PASSWORD: str
    LOG_LEVEL: str
    LOG_FILE: str
    REALNAME_SECRET_SALT: str

    class Config:
        env_file = ".env"  # 默认从项目根目录的 .env 文件中读取
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()