from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.user import User, UserBanHistory
import uuid
import time
import random
from typing import Optional, List

async def get_user_by_phone(db: AsyncSession, phone_number: str):
    result = await db.execute(select(User).where(User.phone_number == phone_number))
    return result.scalar_one_or_none()

async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.user_id == user_id))
    return result.scalar_one_or_none()

async def get_users_by_user_ids(db: AsyncSession, user_ids: List[str]) -> List[User]:
    if not user_ids:
        return []
    result = await db.execute(select(User).where(User.user_id.in_(user_ids)))
    return result.scalars().all()

async def get_users_by_ids(db: AsyncSession, ids: List[uuid.UUID]) -> List[User]:
    if not ids:
        return []
    result = await db.execute(select(User).where(User.id.in_(ids)))
    return result.scalars().all()

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
    await db.flush()
    await db.refresh(user)
    return user

async def update_user(db: AsyncSession, user: User, data: dict):
    for key, value in data.items():
        setattr(user, key, value)
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user

async def get_banned_history_by_user_id(db: AsyncSession, user_id: uuid.UUID):
    result = await db.execute(
        select(UserBanHistory).where(UserBanHistory.user_id == user_id)
    )
    return result.scalar_one_or_none()