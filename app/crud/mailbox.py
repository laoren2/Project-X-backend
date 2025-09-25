from sqlalchemy import select, func
from app.db.models.mailbox import Mailbox
from app.schemas.mailbox import MailDetailResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid


async def get_mail_unread_status(db: AsyncSession, user_id: uuid.UUID) -> tuple[bool, int]:
    """获取用户未读邮件状态"""
    result = await db.execute(
        select(
            func.count(Mailbox.id).label('unread_count')
        )
        .where(Mailbox.user_id == user_id)
        .where(Mailbox.is_read == False)
        .where(
            (Mailbox.expires_at.is_(None)) | 
            (Mailbox.expires_at > func.now())
        )
    )
    
    unread_count = result.scalar() or 0
    has_unread = unread_count > 0
    
    return has_unread, unread_count

async def get_mails_curd(db: AsyncSession, user_id: uuid.UUID, page: int, size: int) -> List[Mailbox]:
    stmt = (
        select(Mailbox)
        .where(Mailbox.user_id == user_id)
        .order_by(Mailbox.created_at.desc()).offset((page - 1) * size).limit(size)
    )
    result = await db.execute(stmt)
    return result.scalars().all()

async def get_mail_by_mail_id(db: AsyncSession, mail_id: str) -> Mailbox | None:
    mail = await db.execute(
        select(Mailbox)
        .where(Mailbox.mail_id == mail_id)
    )
    return mail.scalar_one_or_none()
