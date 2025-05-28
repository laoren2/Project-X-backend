#import os
#from dotenv import load_dotenv

#load_dotenv()

#class Settings:
#    PROJECT_NAME: str = "SportsX 用户中心"
#    DATABASE_URL: str = os.getenv("DATABASE_URL")
#    REDIS_URL: str = os.getenv("REDIS_URL")
#    SECRET_KEY: str = os.getenv("SECRET_KEY")
#    ACCESS_TOKEN_EXPIRE_MINUTES: int = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")  # 7天

#settings = Settings()

from pydantic_settings import BaseSettings
from typing import Optional


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