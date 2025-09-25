from ast import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.mailbox import get_mail_unread_status, get_mails_curd, get_mail_by_mail_id
from app.crud.user import get_user_by_id
from app.crud.asset_manage import reward_ccasset
from app.core.errors import ErrorCode
from app.db.models.mailbox import Mailbox
from app.schemas.base import BizException
from app.schemas.mailbox import (
    MailUnreadStatusResponse, MailInfo, MailDetailResponse, MailInfoResponse, MailCreateForm
)
from app.schemas.asset import AssetRewardsResponse, CCAssetType, CCAssetBaseInfo, AssetOperation
from datetime import datetime, timezone, timedelta
import uuid, json


async def get_mail_unread_status_service(
    db: AsyncSession,
    user_id: str
) -> MailUnreadStatusResponse:
    """获取用户未读邮件状态"""
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
    
    has_unread, unread_count = await get_mail_unread_status(db, user.id)
    
    return MailUnreadStatusResponse(
        has_unread=has_unread,
        unread_count=unread_count
    )

async def get_mails_service(
    page: int,
    size: int,
    user_id: str,
    db: AsyncSession,
) -> MailInfoResponse:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
    
    mails = await get_mails_curd(db, user.id, page, size)
    mail_infos = [MailInfo(
        mail_id=mail.mail_id,
        title=mail.title,
        mail_type=mail.mail_type,
        is_read=mail.is_read,
        created_at=mail.created_at.isoformat()
    ) for mail in mails]
    return MailInfoResponse(mails=mail_infos)

async def get_mail_detail_service(
    mail_id: str,
    user_id: str,
    db: AsyncSession
) -> MailDetailResponse:
    mail = await get_mail_by_mail_id(db, mail_id)
    if mail is None:
        raise BizException(code=ErrorCode.MAIL_NOT_FOUND, message="邮件不存在")
    mail.is_read = True
    db.add(mail)
    await db.commit()
    return MailDetailResponse(
        mail_id=mail.mail_id,
        title=mail.title,
        content=mail.content,
        mail_type=mail.mail_type,
        attachments=mail.attachment,
        is_received=mail.is_received,
        created_at=mail.created_at.isoformat(),
        expired_at=mail.expires_at.isoformat() if mail.expires_at else None
    )

async def send_mail_service(
    create_info: MailCreateForm,
    user_id: str,
    db: AsyncSession
):
    user = await get_user_by_id(db, create_info.user_id)
    if not user:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
    try:
        attach_json = json.loads(create_info.attachments) if create_info.attachments else None
    except:
        raise BizException(code=ErrorCode.JSON_DECODE_ERROR, message=f"JSON格式错误")
    mail = Mailbox(
        mail_id=f"mail_{uuid.uuid4()}",
        user_id=user.id,
        mail_type=create_info.type,
        title = create_info.title,
        content = create_info.content,
        attachment = attach_json,
        is_received = False if create_info.attachments else None,
        expires_at = datetime.now(timezone.utc) + timedelta(days=30) if create_info.attachments else None
    )
    db.add(mail)
    await db.commit()

async def receive_mail_rewards_service(
    mail_id: str,
    user_id: str,
    db: AsyncSession
) -> AssetRewardsResponse:
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if not user:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
        mail = await get_mail_by_mail_id(db, mail_id)
        if mail is None:
            raise BizException(code=ErrorCode.MAIL_NOT_FOUND, message="邮件不存在")
        if mail.is_received:
            raise BizException(code=ErrorCode.MAIL_ERROR, message="请勿重复领取奖励哦")
        if mail.expires_at < datetime.now(timezone.utc):
            raise BizException(code=ErrorCode.MAIL_ERROR, message="奖励过期啦，下次记得早点领哦")
        if not mail.attachment:
            raise BizException(code=ErrorCode.MAIL_ERROR, message="无奖励可领取")
        # 暂仅支持 CCAsset
        ccassets = []
        for asset_type in CCAssetType:
            asset_key = asset_type.value
            if asset_key in mail.attachment and mail.attachment[asset_key] > 0:
                ccassets.append(
                    CCAssetBaseInfo(
                        ccasset_type=asset_type,
                        new_ccamount=mail.attachment[asset_key]
                    )
                )
        description = str(mail.attachment.get("description", "系统奖励"))
        for ccasset in ccassets:
            new_balance = await reward_ccasset(db, ccasset.ccasset_type, ccasset.new_ccamount, user.id, description, AssetOperation.REWARD)
            ccasset.new_ccamount = new_balance
        mail.is_received = True
        db.add(mail)
        return AssetRewardsResponse(
            ccassets=ccassets,
            cpassets=[],
            equip_cards=[]
        )
    