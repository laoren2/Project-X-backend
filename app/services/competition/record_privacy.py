from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ErrorCode
from app.crud.user import get_user_by_id
from app.crud.user_follow import get_friend_id_set, is_following
from app.schemas.base import BizException
from app.schemas.user import RecordVisibility


async def ensure_record_detail_visible(db: AsyncSession, owner, viewer_id: str | None) -> None:
    """仅允许记录所有者设置的受众查看其比赛结果详情。"""
    if viewer_id == owner.user_id:
        return

    visibility = owner.settings.record_visibility if owner.settings else RecordVisibility.public
    if visibility == RecordVisibility.public:
        return

    if viewer_id:
        viewer = await get_user_by_id(db, viewer_id)
        if viewer:
            if visibility == RecordVisibility.followers:
                # “粉丝”指查看者关注记录主人。
                if await is_following(db, viewer.id, owner.id):
                    return
            elif visibility == RecordVisibility.friends:
                if owner.id in await get_friend_id_set(db, viewer.id):
                    return

    raise BizException(code=ErrorCode.NO_PERMISSION, message="record.access_denied")
