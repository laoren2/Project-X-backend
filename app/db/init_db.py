import asyncio
from app.db.base import Base
from app.db.session import engine
from sqlalchemy import text


async def test_db_connection():
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))

if __name__ == "__main__":
    asyncio.run(test_db_connection())
