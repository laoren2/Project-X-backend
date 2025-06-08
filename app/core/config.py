from pydantic_settings import BaseSettings
from typing import Optional
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
from starlette.requests import Request
import os

class CustomStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope) -> FileResponse:
        response: FileResponse = await super().get_response(path, scope)
        
        if path.endswith(".png"):
            response.headers["Cache-Control"] = "public, max-age=86400"  # 1 day
        else:
            response.headers["Cache-Control"] = "public, max-age=3600"  # 1 hour
        
        return response


class Settings(BaseSettings):
    PROJECT_NAME: str = "SportsX 用户中心"
    DATABASE_URL: str
    REDIS_URL: str
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 默认 7 天

    class Config:
        env_file = ".env"  # 默认从项目根目录的 .env 文件中读取
        env_file_encoding = "utf-8"


settings = Settings()