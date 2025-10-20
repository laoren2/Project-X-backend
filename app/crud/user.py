from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.user import User, UserBanHistory, UserRealNameHK, UserSetting, UserSignIn, SignInReward
from typing import Optional, List
from sqlalchemy.orm import selectinload
from app.schemas.user import UserStatus
from app.schemas.asset import CCAssetType
from datetime import date, datetime, timezone, timedelta
from app.core.tools import get_today_hk_date
import uuid, random, time


async def get_user_by_phone(db: AsyncSession, phone_number: str) -> List[User]:
    result = await db.execute(
        select(User)
        .where(User.phone_number == phone_number)
    )
    return result.scalars().all()

# todo: 模糊匹配
async def get_user_by_name(db: AsyncSession, name: str) -> List[User]:
    result = await db.execute(
        select(User)
        .where(User.nickname == name)
    )
    return result.scalars().all()

async def get_exist_user_by_phone(db: AsyncSession, phone_number: str) -> User | None:
    result = await db.execute(
        select(User)
        .where(
            User.phone_number == phone_number,
            User.status != UserStatus.deleted
        )
        .options(
            selectinload(User.settings),
            selectinload(User.real_name_info)
        )
    )
    return result.scalar_one_or_none()

async def get_user_by_apple_id(db: AsyncSession, apple_id: str) -> List[User]:
    result = await db.execute(
        select(User)
        .where(User.apple_id == apple_id)
        .options(
            selectinload(User.settings),
            selectinload(User.real_name_info)
        )
    )
    return result.scalars().all()

async def get_exist_user_by_apple_id(db: AsyncSession,  apple_id: str) -> User | None:
    result = await db.execute(
        select(User)
        .where(
            User.apple_id == apple_id,
            User.status != UserStatus.deleted
        )
        .options(
            selectinload(User.settings),
            selectinload(User.real_name_info)
        )
    )
    return result.scalar_one_or_none()

async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
    result = await db.execute(
        select(User)
        .where(User.user_id == user_id)
        .options(
            selectinload(User.settings),
            selectinload(User.real_name_info)
        )
    )
    return result.scalar_one_or_none()

async def get_exist_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
    result = await db.execute(
        select(User)
        .where(
            User.user_id == user_id,
            User.status != UserStatus.deleted
        )
        .options(
            selectinload(User.settings),
            selectinload(User.real_name_info)
        )
    )
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
    user_setting = UserSetting(user_id=user.id)
    db.add(user_setting)
    return user

async def create_user_with_apple(db: AsyncSession, apple_id: str, email: str) -> User:
    user_id = await generate_unique_user_id(db)
    user = User(
        user_id=user_id,
        nickname=f"新用户_{user_id[-5:]}",
        apple_id=apple_id,
        apple_email=email,
        avatar_image_url="/resources/placeholder/avatar.png",
        background_image_url="/resources/placeholder/background.png"
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    user_setting = UserSetting(user_id=user.id)
    db.add(user_setting)
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

async def get_realname_info_by_user_id(db: AsyncSession, user_id: uuid.UUID) -> UserRealNameHK | None:
    result = await db.execute(select(UserRealNameHK).where(UserRealNameHK.user_id == user_id))
    return result.scalar_one_or_none()

async def get_realname_info_by_card_id(db: AsyncSession, card_id: str) -> UserRealNameHK | None:
    result = await db.execute(select(UserRealNameHK).where(UserRealNameHK.card_id == card_id))
    return result.scalar_one_or_none()

async def get_settings_by_user_id(db: AsyncSession, user_id: uuid.UUID) -> UserSetting | None:
    result = await db.execute(select(UserSetting).where(UserSetting.user_id == user_id))
    return result.scalar_one_or_none()


async def get_sign_in_reward_by_day(db: AsyncSession, days: int) -> SignInReward | None:
    """获取指定签到奖励信息"""
    result = await db.execute(
        select(SignInReward)
        .where(SignInReward.days == days)
    )
    return result.scalar_one_or_none()

async def get_sign_in_rewards(db: AsyncSession) -> List[SignInReward]:
    """获取所有签到奖励信息"""
    result = await db.execute(select(SignInReward).order_by(SignInReward.days))
    return result.scalars().all()

async def get_user_normal_sign_in_today(db: AsyncSession, user_id: uuid.UUID, sign_date: date) -> Optional[UserSignIn]:
    """查询用户今日是否已普通签到"""
    result = await db.execute(
        select(UserSignIn)
        .where(
            UserSignIn.user_id == user_id,
            UserSignIn.is_vip == False,
            UserSignIn.sign_in_date == sign_date
        )
    )
    return result.scalar_one_or_none()

async def get_user_vip_sign_in_today(db: AsyncSession, user_id: uuid.UUID, sign_date: date) -> Optional[UserSignIn]:
    """查询用户今日是否已vip签到"""
    result = await db.execute(
        select(UserSignIn)
        .where(
            UserSignIn.user_id == user_id,
            UserSignIn.is_vip == True,
            UserSignIn.sign_in_date == sign_date
        )
    )
    return result.scalar_one_or_none()

async def get_user_sign_in_history(db: AsyncSession, user_id: uuid.UUID, days: int = 6) -> List[UserSignIn]:
    """获取用户最近N天的签到记录"""
    end_date = get_today_hk_date() - timedelta(days=1)
    start_date = end_date - timedelta(days=days)
    result = await db.execute(
        select(UserSignIn)
        .where(
            UserSignIn.user_id == user_id,
            UserSignIn.sign_in_date >= start_date,
            UserSignIn.sign_in_date <= end_date
        )
        .order_by(UserSignIn.sign_in_date.desc())
    )
    return result.scalars().all()