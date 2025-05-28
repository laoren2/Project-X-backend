from app.crud import user_follow
from app.crud.user import get_user_by_id
from app.schemas.user import UserRelationInfo
from app.schemas.base import BizException
from app.schemas.user_follow import PersonInfoResponse
from app.core.errors import ErrorCode
from sqlalchemy.ext.asyncio import AsyncSession

async def get_relation_count(db: AsyncSession, user_id):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
    # 使用user.id查询数据库
    following_count = await user_follow.count_following(db, user.id)
    follower_count = await user_follow.count_followers(db, user.id)
    friend_count = await user_follow.count_friends(db, user.id)
    return UserRelationInfo (
        follower=follower_count,
        followed=following_count,
        friends=friend_count
    )


async def get_relationship_service(db: AsyncSession, follower_id, followed_id):
    user_follower = await get_user_by_id(db, follower_id)
    user_followed = await get_user_by_id(db, followed_id)
    if not user_followed:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
    relationship = await user_follow.get_relationship_crud(db, user_follower.id, user_followed.id)
    return relationship


async def follow_user(db: AsyncSession, follower_id, followed_id):
    if follower_id == followed_id:
        raise BizException(code=ErrorCode.USER_FOLLOW_SELF, message="不能关注自己")
    user_follower = await get_user_by_id(db, follower_id)
    user_followed = await get_user_by_id(db, followed_id)
    if not user_followed:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
    already_following = await user_follow.is_following(db, user_follower.id, user_followed.id)
    if already_following:
        raise BizException(code=ErrorCode.USER_FOLLOW_REPEAT, message="请勿重复关注")
    await user_follow.create_follow(db, user_follower.id, user_followed.id)


async def cancel_follow_user(db: AsyncSession, follower_id, followed_id):
    if follower_id == followed_id:
        raise BizException(code=ErrorCode.USER_FOLLOW_SELF, message="不能取消关注自己")
    user_follower = await get_user_by_id(db, follower_id)
    user_followed = await get_user_by_id(db, followed_id)
    if not user_followed:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
    await user_follow.remove_follow(db, user_follower.id, user_followed.id)


async def get_following_list(db: AsyncSession, user_id, limit=20, cursor_created_at=None, cursor_id=None, search=None):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
    cursor_user_id = cursor_id
    if cursor_user_id:
        cursor_user = await get_user_by_id(db, cursor_id)
        if not cursor_user:
            print("get_follower_list携带的cursor_id无效")
        cursor_user_id = cursor_user.id if cursor_user else None
    users, next_cursor_created_at, next_cursor_id, has_more = await user_follow.get_following_ids(db, user.id, limit, cursor_created_at, cursor_user_id, search)
    items = [
        PersonInfoResponse(
            user_id=user.user_id,
            avatar_image_url=user.avatar_image_url,
            nickname=user.nickname
        ) for user in users
    ]
    return items, next_cursor_created_at.isoformat() if next_cursor_created_at else None, next_cursor_id, has_more


async def get_follower_list(db: AsyncSession, user_id, limit=20, cursor_created_at=None, cursor_id=None, search=None):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
    cursor_user_id = cursor_id
    if cursor_user_id:
        cursor_user = await get_user_by_id(db, cursor_id)
        if not cursor_user:
            print("get_follower_list携带的cursor_id无效")
        cursor_user_id = cursor_user.id if cursor_user else None
    users, next_cursor_created_at, next_cursor_id, has_more = await user_follow.get_follower_ids(db, user.id, limit, cursor_created_at, cursor_user_id, search)
    items = [
        PersonInfoResponse(
            user_id=user.user_id,
            avatar_image_url=user.avatar_image_url,
            nickname=user.nickname
        ) for user in users
    ]
    return items, next_cursor_created_at.isoformat() if next_cursor_created_at else None, next_cursor_id, has_more


async def get_friend_list(db: AsyncSession, user_id, limit=20, cursor_created_at=None, cursor_id=None, search=None):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
    cursor_user_id = cursor_id
    if cursor_user_id:
        cursor_user = await get_user_by_id(db, cursor_id)
        if not cursor_user:
            print("get_follower_list携带的cursor_id无效")
        cursor_user_id = cursor_user.id if cursor_user else None
    users, next_cursor_created_at, next_cursor_id, has_more = await user_follow.get_friend_ids(db, user.id, limit, cursor_created_at, cursor_user_id, search)
    items = [
        PersonInfoResponse(
            user_id=user.user_id,
            avatar_image_url=user.avatar_image_url,
            nickname=user.nickname
        ) for user in users
    ]
    return items, next_cursor_created_at.isoformat() if next_cursor_created_at else None, next_cursor_id, has_more