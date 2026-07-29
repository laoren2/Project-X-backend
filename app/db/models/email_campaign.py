from sqlalchemy import Column, DateTime, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base
import uuid


class EmailCampaign(Base):
    __tablename__ = "email_campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(String, unique=True, index=True, nullable=False)
    template_key = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    status = Column(String, nullable=False, default="draft", index=True)
    created_by = Column(String, nullable=False)
    total_count = Column(Integer, nullable=False, default=0)
    sent_count = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)
    skipped_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class EmailCampaignRecipient(Base):
    __tablename__ = "email_campaign_recipients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    email = Column(String, nullable=False)
    unsubscribe_token = Column(String, unique=True, index=True, nullable=False)
    status = Column(String, nullable=False, default="pending")
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("campaign_id", "email", name="uq_email_campaign_recipients_campaign_email"),
        Index("ix_email_campaign_recipients_campaign_status", "campaign_id", "status"),
    )
