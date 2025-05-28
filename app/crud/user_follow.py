from typing import Optional
from datetime import datetime
from sqlalchemy import select, delete, and_, or_, desc, asc, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import UserFollow, User
from app.schemas.base import RelationshipStatus
from sqlalchemy.orm import selectinload
import uuid


async def count_following(db: AsyncSession, user_db_id):
    friend_ids = await get_friend_id_set(db, user_db_id)
    query = select(func.count()).select_from(UserFollow).where(UserFollow.follower_id == user_db_id)
    if friend_ids:
        query = query.where(UserFollow.followed_id.notin_(friend_ids))
    result = await db.execute(query)
    return result.scalar()

async def count_followers(db: AsyncSession, user_db_id):
    friend_ids = await get_friend_id_set(db, user_db_id)
    query = select(func.count()).select_from(UserFollow).where(UserFollow.followed_id == user_db_id)
    if friend_ids:
        query = query.where(UserFollow.follower_id.notin_(friend_ids))
    result = await db.execute(query)
    return result.scalar()

async def count_friends(db: AsyncSession, user_db_id):
    # 互相关注
    subq1 = select(UserFollow.followed_id).where(UserFollow.follower_id == user_db_id).subquery()
    subq2 = select(UserFollow.follower_id).where(UserFollow.followed_id == user_db_id).subquery()
    result = await db.execute(
        select(func.count())
        .select_from(subq1.join(subq2, subq1.c.followed_id == subq2.c.follower_id))
    )
    return result.scalar()


async def create_follow(db: AsyncSession, follower_id: uuid.UUID, followed_id: uuid.UUID):
    follow = UserFollow(follower_id=follower_id, followed_id=followed_id)
    db.add(follow)
    await db.commit()
    return follow

async def remove_follow(db: AsyncSession, follower_id: uuid.UUID, followed_id: uuid.UUID):
    await db.execute(
        delete(UserFollow).where(
            and_(
                UserFollow.follower_id == follower_id,
                UserFollow.followed_id == followed_id
            )
        )
    )
    await db.commit()

async def get_relationship_crud(db: AsyncSession, follower_id: uuid.UUID, followed_id: uuid.UUID) -> RelationshipStatus:
    # 是否 follower_id 关注了 followed_id
    result1 = await db.execute(
        select(UserFollow).where(
            UserFollow.follower_id == follower_id,
            UserFollow.followed_id == followed_id
        )
    )
    follow1 = result1.scalar()

    # 是否 followed_id 关注了 follower_id
    result2 = await db.execute(
        select(UserFollow).where(
            UserFollow.follower_id == followed_id,
            UserFollow.followed_id == follower_id
        )
    )
    follow2 = result2.scalar()

    if follow1 and follow2:
        return RelationshipStatus.friend
    elif follow1:
        return RelationshipStatus.following
    elif follow2:
        return RelationshipStatus.follower
    else:
        return RelationshipStatus.none

async def is_following(db: AsyncSession, follower_id: uuid.UUID, followed_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(UserFollow.id).where(
            and_(
                UserFollow.follower_id == follower_id,
                UserFollow.followed_id == followed_id
            )
        )
    )
    return result.scalar_one_or_none() is not None

async def get_friend_id_set(db: AsyncSession, user_id: uuid.UUID) -> set[uuid.UUID]:
    sub_a = select(UserFollow.followed_id).where(UserFollow.follower_id == user_id).subquery()
    sub_b = select(UserFollow.follower_id).where(UserFollow.followed_id == user_id).subquery()
    result = await db.execute(
        select(sub_a.c.followed_id)
        .join(sub_b, sub_a.c.followed_id == sub_b.c.follower_id)
    )
    return set(result.scalars().all())


async def get_following_ids(
        db: AsyncSession, 
        id: uuid.UUID,
        limit: int = 20,
        cursor_created_at: Optional[datetime] = None, 
        cursor_id: Optional[uuid.UUID] = None,
        search: Optional[str] = None
    ) -> tuple[list[User], Optional[datetime], Optional[str], bool]:
    friend_ids = await get_friend_id_set(db, id)

    query = select(UserFollow).options(selectinload(UserFollow.followed)).where(UserFollow.follower_id == id)
    if friend_ids:
        query = query.where(UserFollow.followed_id.notin_(friend_ids))
    if cursor_created_at and cursor_id:
        query = query.where(
            or_(
                UserFollow.created_at > cursor_created_at,
                and_(
                    UserFollow.created_at == cursor_created_at,
                    UserFollow.followed_id > cursor_id
                )
            )
        )
    elif cursor_created_at and not cursor_id:
        query = query.where(
            UserFollow.created_at > cursor_created_at
        )
    query = query.order_by(asc(UserFollow.created_at), UserFollow.followed_id)
    result = await db.execute(query)
    follows = result.scalars().all()
    users = [f.followed for f in follows]

    if search:
        users = [u for u in users if search.lower() in (u.nickname or "").lower()]

    users = users[:limit]

    next_cursor_created_at = None
    last_user_id = users[-1].id if users else None
    if last_user_id:
        for f in reversed(follows):
            if f.followed_id == last_user_id:
                next_cursor_created_at = f.created_at
                break

    next_cursor_id = users[-1].user_id if users else None
    return users, next_cursor_created_at, next_cursor_id, len(users) == limit


async def get_follower_ids(
        db: AsyncSession,
        id: uuid.UUID,
        limit: int = 20,
        cursor_created_at: Optional[datetime] = None,
        cursor_id: Optional[uuid.UUID] = None,
        search: Optional[str] = None
    ) -> tuple[list[User], Optional[datetime], Optional[str], bool]:
    friend_ids = await get_friend_id_set(db, id)

    query = select(UserFollow).options(selectinload(UserFollow.follower)).where(UserFollow.followed_id == id)
    if friend_ids:
        query = query.where(UserFollow.follower_id.notin_(friend_ids))
    if cursor_created_at and cursor_id:
        query = query.where(
            or_(
                UserFollow.created_at > cursor_created_at,
                and_(
                    UserFollow.created_at == cursor_created_at,
                    UserFollow.follower_id > cursor_id
                )
            )
        )
    elif cursor_created_at and not cursor_id:
        query = query.where(
            UserFollow.created_at > cursor_created_at
        )
    query = query.order_by(asc(UserFollow.created_at), UserFollow.follower_id)
    result = await db.execute(query)
    follows = result.scalars().all()
    users = [f.follower for f in follows]

    if search:
        users = [u for u in users if search.lower() in (u.nickname or "").lower()]

    users = users[:limit]

    next_cursor_created_at = None
    last_user_id = users[-1].id if users else None
    if last_user_id:
        for f in reversed(follows):
            if f.follower_id == last_user_id:
                next_cursor_created_at = f.created_at
                break

    next_cursor_user_id = users[-1].user_id if users else None
    return users, next_cursor_created_at, next_cursor_user_id, len(users) == limit

async def get_friend_ids(
        db: AsyncSession, 
        id: uuid.UUID, 
        limit: int = 20, 
        cursor_created_at: Optional[datetime] = None, 
        cursor_id: Optional[uuid.UUID] = None,
        search: Optional[str] = None
    ) -> tuple[list[User], Optional[datetime], Optional[str], bool]:
    sub_a = select(
        UserFollow.followed_id.label("friend_id"),
        UserFollow.created_at.label("created_at_a")
    ).where(UserFollow.follower_id == id).subquery()

    sub_b = select(
        UserFollow.follower_id.label("friend_id"),
        UserFollow.created_at.label("created_at_b")
    ).where(UserFollow.followed_id == id).subquery()

    # 取交集并计算“成为朋友”的时间（max(a, b))
    friend_since_col = func.greatest(sub_a.c.created_at_a, sub_b.c.created_at_b).label("friend_since")

    join_stmt = select(
        sub_a.c.friend_id,
        friend_since_col
    ).join(sub_b, sub_a.c.friend_id == sub_b.c.friend_id)

    if cursor_created_at and cursor_id:
        join_stmt = join_stmt.where(
            or_(
                friend_since_col > cursor_created_at,
                and_(
                    friend_since_col == cursor_created_at,
                    sub_a.c.friend_id > cursor_id  # 用 friend_id 作为 tie-breaker
                )
            )
        )
    elif cursor_created_at and not cursor_id:
        join_stmt = join_stmt.where(
            friend_since_col > cursor_created_at
        )

    join_stmt = join_stmt.order_by(friend_since_col, sub_a.c.friend_id)
    result = await db.execute(join_stmt)
    rows = result.all()

    friend_ids = [r.friend_id for r in rows]
    friend_since_map = {r.friend_id: r.friend_since for r in rows}

    if not friend_ids:
        return [], None, None, False

    # 加载用户信息
    user_stmt = select(User).where(User.id.in_(friend_ids))
    users_result = await db.execute(user_stmt)
    users = users_result.scalars().all()

    if search:
        users = [u for u in users if search.lower() in (u.nickname or "").lower()]

    if not users:
        return [], None, None, False

    # 保持顺序一致
    users.sort(key=lambda u: friend_since_map.get(u.id))
    users = users[:limit]

    last_user = users[-1]
    next_cursor_created_at = friend_since_map.get(last_user.id)
    return users, next_cursor_created_at, last_user.user_id, len(users) == limit