from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import redis.asyncio as aioredis
import logging

redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

engine = create_async_engine(settings.DATABASE_URL, future=True, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

logger = logging.getLogger("main")

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def test_redis_connection():
    """测试Redis连接"""
    try:
        await redis_client.ping()
        return True
    except Exception:
        logger.exception("Redis connection test failed")
        return False

async def close_redis_connection():
    """关闭Redis连接"""
    try:
        await redis_client.close()
        logger.info("Redis connection closed")
    except Exception:
        logger.exception("Error while closing Redis connection")

async def close_database_connection():
    """关闭数据库连接池"""
    try:
        await engine.dispose()
        logger.info("Database engine closed")
    except Exception:
        logger.exception("Error while disposing database engine")
