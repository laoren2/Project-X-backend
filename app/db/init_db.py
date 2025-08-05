import asyncio
from app.db.base import Base
from app.db.session import engine


async def keep_event_loop_alive():
    while True:
        await asyncio.sleep(3600)  # 每小时睡一次，几乎不占资源

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

if __name__ == "__main__":
    asyncio.run(init_db())
