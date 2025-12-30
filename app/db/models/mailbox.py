from sqlalchemy import (
    Column, String, Boolean, ForeignKey, DateTime, 
    func, UniqueConstraint, Integer, Float, Enum, Text
)
from sqlalchemy.dialects.postgresql import UUID
from app.schemas.mailbox import MailType, FeedbackMailType
from app.db.base import Base
from sqlalchemy.dialects.postgresql import JSONB
import uuid


class Mailbox(Base):
    __tablename__ = "mailbox"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mail_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    mail_type = Column(Enum(MailType), nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=True)
    attachment = Column(JSONB, nullable=True)
    is_read = Column(Boolean, default=False, nullable=False)
    is_received = Column(Boolean, default=False, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    claimed_at = Column(DateTime(timezone=True), nullable=True)

class FeedbackMailbox(Base):
    __tablename__ = "feedback_mailbox"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mail_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_contact_info = Column(String, nullable=True)
    mail_type = Column(Enum(FeedbackMailType), nullable=False)
    description = Column(Text, nullable=False)
    images = Column(JSONB, nullable=False, default=list)   # string数组
    is_handled = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
