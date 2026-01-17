from sqlalchemy import (
    Column, String, Boolean, ForeignKey, DateTime, 
    func, UniqueConstraint, Integer, Float, Enum, Text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base
import uuid


class Announcement(Base):
    __tablename__ = "announcements"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_i18n = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class BannerAds(Base):
    __tablename__ = "banner_ads"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ad_id = Column(String, unique=True, index=True, nullable=False)
    image_url_i18n = Column(JSONB, nullable=False)
    web_url = Column(String, nullable=True)
    is_displayed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)