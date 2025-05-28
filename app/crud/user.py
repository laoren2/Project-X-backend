from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import User
import uuid
import time
import random
from typing import Optional

async def get_user_by_phone(db: AsyncSession, phone_number: str):
    result = await db.execute(select(User).where(User.phone_number == phone_number))
    return result.scalar_one_or_none()

async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.user_id == user_id))
    return result.scalar_one_or_none()

async def delete_user_by_id(db: AsyncSession, user: User):
    await db.delete(user)
    await db.commit()

async def generate_unique_user_id(db: AsyncSession) -> str:
    while True:
        user_id = f"{int(time.time())}{random.randint(10000, 99999)}"
        existing_user = await get_user_by_id(db, user_id)
        if not existing_user:
            return user_id

async def create_user(db: AsyncSession, phone_number: str):
    user_id = await generate_unique_user_id(db)
    user = User(
        user_id=user_id,
        nickname=f"新用户_{user_id[-5:]}",
        phone_number=phone_number,
        avatar_image_url="/resources/placeholder/avatar.png",
        background_image_url="/resources/placeholder/background.png"
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def update_user(db: AsyncSession, user: User, data: dict):
    for key, value in data.items():
        setattr(user, key, value)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
