from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.base import Base
from sqlalchemy.orm import relationship

# 用户表
class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(String, unique=True, index=True, nullable=False)
    nickname = Column(String, nullable=False)
    phone_number = Column(String, unique=True, index=True, nullable=False)
    avatar_image_url = Column(String, nullable=False)
    background_image_url = Column(String, nullable=False)
    introduction = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    birthday = Column(String, nullable=True)
    location = Column(String, nullable=True)
    identity_auth_name = Column(String, nullable=True)
    is_realname_auth = Column(Boolean, default=False)
    is_identity_auth = Column(Boolean, default=False)
    is_display_gender = Column(Boolean, default=False)
    is_display_age = Column(Boolean, default=False)
    is_display_location = Column(Boolean, default=False)
    enable_auto_location = Column(Boolean, default=False)
    is_display_identity = Column(Boolean, default=False)

# 用户关注关系表
class UserFollow(Base):
    __tablename__ = "user_follows"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    follower_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    followed_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("follower_id", "followed_id", name="uq_follower_followed"),
    )

    # 与users表建立关联关系，可以方便的获取关注者和被关注者的User对象
    follower = relationship("User", foreign_keys=[follower_id])
    followed = relationship("User", foreign_keys=[followed_id])
