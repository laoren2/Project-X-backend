from typing import Optional, List, Any
from app.schemas.base import ORMBase
from enum import Enum
from pydantic import BaseModel
from fastapi import Form

class MailType(str, Enum):
    REWARD = "reward"           # 奖励邮件
    NOTIFICATION = "notification"  # 通知邮件

class MailUnreadStatusResponse(BaseModel):
    has_unread: bool
    unread_count: int

class MailInfo(BaseModel):
    mail_id: str
    title: str
    mail_type: MailType
    is_read: bool
    created_at: str

class MailInfoResponse(BaseModel):
    mails: List[MailInfo]

class MailDetailResponse(BaseModel):
    mail_id: str
    title: str
    content: str | None
    mail_type: MailType
    attachments: dict[str, Any] | None
    is_received: bool | None
    created_at: str
    expired_at: str | None

class MailCreateForm(BaseModel):
    user_id: str
    type: MailType
    title: str
    content: str | None = None
    attachments: str | None = None
