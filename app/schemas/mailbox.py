from typing import Optional, List, Any
from app.schemas.base import ORMBase
from enum import Enum
from pydantic import BaseModel, Field
from fastapi import Form

class MailType(str, Enum):
    REWARD = "reward"               # 奖励邮件
    NOTIFICATION = "notification"   # 通知邮件

class FeedbackMailType(str, Enum):
    IAP = "iap"             # iap问题反馈
    BUG = "bug"             # bug问题反馈
    FEATURE = "feature"     # 功能建议反馈
    REPORT = "report"       # 举报
    OTHER = "other"         # 其他

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
    title: dict
    content: dict | None = None
    attachments: str | None = None

class FeedbackMailCreateForm(BaseModel):
    type: FeedbackMailType
    user_contact_info: str | None
    content: str

    @classmethod
    def as_form(
        cls,
        type: str = Form(...),
        user_contact_info: str | None = Form(None),
        content: str = Form(...)
    ):
        return cls(
            type=type,
            user_contact_info=user_contact_info,
            content=content
        )

class FeedbackMailInfo(BaseModel):
    mail_id: str
    mail_type: FeedbackMailType
    user_contact_info: str | None
    content: str
    images: List[str]
    is_handled: bool
    created_at: str

class FeedbackMailInfoResponse(BaseModel):
    mails: List[FeedbackMailInfo]
