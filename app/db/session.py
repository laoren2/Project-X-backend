from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import redis.asyncio as aioredis
import logging

redis_client = aioredis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    max_connections=settings.REDIS_MAX_CONNECTIONS,  # 连接池大小
    socket_connect_timeout=5,    # 连接超时
    socket_timeout=5,            # 读写超时
    health_check_interval=30     # 连接健康检查
)

engine = create_async_engine(
    settings.DATABASE_URL,
    future=True,
    echo=False,
    pool_size=settings.DB_POOL_SIZE,          # 常驻连接数
    max_overflow=settings.DB_MAX_OVERFLOW,    # 临时超额连接
    pool_timeout=30,                         # 等待连接超时（秒）
    pool_recycle=1800,                       # 30分钟回收一次连接（防断连）
    pool_pre_ping=True                       # 连接失效自动检测
)
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
