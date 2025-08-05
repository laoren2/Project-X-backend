from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import redis.asyncio as aioredis

redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

engine = create_async_engine(settings.DATABASE_URL, future=True, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def test_redis_connection():
    """测试Redis连接"""
    try:
        await redis_client.ping()
        return True
    except Exception as e:
        print(f"Redis连接测试失败: {e}")
        return False

async def close_redis_connection():
    """关闭Redis连接"""
    try:
        await redis_client.close()
        print("Redis连接已关闭")
    except Exception as e:
        print(f"关闭Redis连接时出错: {e}")

async def close_database_connection():
    """关闭数据库连接池"""
    try:
        await engine.dispose()
        print("数据库连接池已关闭")
    except Exception as e:
        print(f"关闭数据库连接池时出错: {e}")
