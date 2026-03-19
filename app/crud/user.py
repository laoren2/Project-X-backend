from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.user import User, UserBanHistory, UserRealNameIdentity, UserSetting, UserSignIn, SignInReward, TestAccount
from typing import Optional, List
from sqlalchemy.orm import selectinload
from app.schemas.user import RealNameMethod, UserStatus
from datetime import date, datetime, timezone, timedelta
from app.core.tools import get_today_hk_date, get_user_local_date
import uuid, random, time


async def get_user_by_phone(db: AsyncSession, phone_number: str) -> List[User]:
    result = await db.execute(
        select(User)
        .where(User.phone_number == phone_number)
    )
    return result.scalars().all()

async def get_users_by_name(db: AsyncSession, name: str, page: int, size: int) -> List[User]:
    """
    根据用户昵称进行模糊查询（大小写不敏感）
    例如传入 'tom'，可以匹配到 'Tom', 'tommy', 'atome' 等
    """
    # 防止空字符串导致全表扫描
    keyword = name.strip()
    if not keyword:
        return []

    result = await db.execute(
        select(User)
        .where(User.nickname.ilike(f"%{keyword}%"))
        .order_by(User.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    return result.scalars().all()

async def get_exist_user_by_name(db: AsyncSession, nickname: str) -> User | None:
    result = await db.execute(
        select(User)
        .where(
            User.nickname == nickname,
            User.status != UserStatus.deleted
        )
        .options(
            selectinload(User.settings),
            selectinload(User.real_name_info),
            selectinload(User.subscription_info)
        )
    )
    return result.scalar_one_or_none()

async def get_exist_user_by_phone(db: AsyncSession, phone_number: str) -> User | None:
    result = await db.execute(
        select(User)
        .where(
            User.phone_number == phone_number,
            User.status != UserStatus.deleted
        )
        .options(
            selectinload(User.settings),
            selectinload(User.real_name_info),
            selectinload(User.subscription_info)
        )
    )
    return result.scalar_one_or_none()

async def get_user_by_apple_id(db: AsyncSession, apple_id: str) -> List[User]:
    result = await db.execute(
        select(User)
        .where(User.apple_id == apple_id)
        .options(
            selectinload(User.settings),
            selectinload(User.real_name_info),
            selectinload(User.subscription_info)
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
            selectinload(User.real_name_info),
            selectinload(User.subscription_info)
        )
    )
    return result.scalar_one_or_none()

async def get_user_by_email(db: AsyncSession, email_address: str) -> List[User]:
    result = await db.execute(
        select(User)
        .where(User.email == email_address)
        .options(
            selectinload(User.settings),
            selectinload(User.real_name_info),
            selectinload(User.subscription_info)
        )
    )
    return result.scalars().all()

async def get_exist_user_by_email(db: AsyncSession, email_address: str) -> User | None:
    result = await db.execute(
        select(User)
        .where(
            User.email == email_address,
            User.status != UserStatus.deleted
        )
        .options(
            selectinload(User.settings),
            selectinload(User.real_name_info),
            selectinload(User.subscription_info)
        )
    )
    return result.scalar_one_or_none()

async def get_user_by_iap_token(db: AsyncSession,  iap_token: str) -> User | None:
    result = await db.execute(
        select(User)
        .where(User.apple_iap_token == iap_token)
    )
    return result.scalar_one_or_none()

async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
    result = await db.execute(
        select(User)
        .where(User.user_id == user_id)
        .options(
            selectinload(User.settings),
            selectinload(User.real_name_info),
            selectinload(User.subscription_info)
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
            selectinload(User.real_name_info),
            selectinload(User.subscription_info)
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

async def generate_unique_user_nickname(db: AsyncSession) -> str:
    while True:
        nickname = f"新用户_{random.randint(10000, 99999)}"
        existing_user = await get_exist_user_by_name(db, nickname)
        if not existing_user:
            return nickname

async def create_user(db: AsyncSession, phone_number: str, timezone: str):
    user_id = await generate_unique_user_id(db)
    nickname = await generate_unique_user_nickname(db)
    user = User(
        user_id=user_id,
        timezone=timezone,
        nickname=nickname,
        phone_number=phone_number,
        avatar_image_url="/resources/placeholder/avatar.jpg",
        background_image_url="/resources/placeholder/background.jpg"
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    user_setting = UserSetting(user_id=user.id)
    db.add(user_setting)
    return user

async def create_user_with_apple(db: AsyncSession, apple_id: str, email: str, timezone: str) -> User:
    user_id = await generate_unique_user_id(db)
    nickname = await generate_unique_user_nickname(db)
    user = User(
        user_id=user_id,
        timezone=timezone,
        nickname=nickname,
        apple_id=apple_id,
        apple_email=email,
        avatar_image_url="/resources/placeholder/avatar.jpg",
        background_image_url="/resources/placeholder/background.jpg"
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    user_setting = UserSetting(user_id=user.id)
    db.add(user_setting)
    return user

async def create_user_with_email(db: AsyncSession, email_address: str, timezone: str) -> User:
    user_id = await generate_unique_user_id(db)
    nickname = await generate_unique_user_nickname(db)
    user = User(
        user_id=user_id,
        timezone=timezone,
        nickname=nickname,
        email=email_address,
        avatar_image_url="/resources/placeholder/avatar.jpg",
        background_image_url="/resources/placeholder/background.jpg"
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

async def get_realname_info_by_user_id(db: AsyncSession, user_id: uuid.UUID) -> UserRealNameIdentity | None:
    result = await db.execute(select(UserRealNameIdentity).where(UserRealNameIdentity.user_id == user_id))
    return result.scalar_one_or_none()

async def get_realname_info_by_country_method_card(
    db: AsyncSession,
    country_code: str,
    method: RealNameMethod,
    card_id_hash: str
) -> UserRealNameIdentity | None:
    result = await db.execute(
        select(UserRealNameIdentity)
        .where(
            UserRealNameIdentity.country_code == country_code,
            UserRealNameIdentity.method == method,
            UserRealNameIdentity.card_id_hash == card_id_hash
        )
    )
    return result.scalar_one_or_none()

async def get_settings_by_user_id(db: AsyncSession, user_id: uuid.UUID) -> UserSetting | None:
    result = await db.execute(select(UserSetting).where(UserSetting.user_id == user_id))
    return result.scalar_one_or_none()


async def get_sign_in_reward_by_day(db: AsyncSession, day: date, days: int) -> SignInReward | None:
    """获取指定签到奖励信息"""
    if 0 <= days <= 5:
        query_days = days
    elif days > 5:
        index = day.day % 5
        query_days = 6 + index
    else:
        return None
    result = await db.execute(
        select(SignInReward)
        .where(SignInReward.days == query_days)
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

async def get_user_sign_in_history(db: AsyncSession, user: User, days: int = 6) -> List[UserSignIn]:
    """获取用户最近N天的签到记录"""
    end_date = get_user_local_date(user) - timedelta(days=1)
    start_date = end_date - timedelta(days=days-1)
    result = await db.execute(
        select(UserSignIn)
        .where(
            UserSignIn.user_id == user.id,
            UserSignIn.sign_in_date >= start_date,
            UserSignIn.sign_in_date <= end_date
        )
        .order_by(UserSignIn.sign_in_date.desc())
    )
    return result.scalars().all()

async def get_test_account(db: AsyncSession, email_address: str) -> TestAccount | None:
    result = await db.execute(
        select(TestAccount)
        .where(
            TestAccount.email == email_address
        )
    )
    return result.scalar_one_or_none()