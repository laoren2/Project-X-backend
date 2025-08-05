import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime, func, UniqueConstraint, Integer, Float, Enum, Numeric
from sqlalchemy.dialects.postgresql import UUID
from app.schemas.user import UserRole, Gender, UserStatus
from app.schemas.asset import CCAssetType, AssetOperation
from app.db.base import Base
from sqlalchemy.orm import relationship


# 用户表
class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(String, unique=True, index=True, nullable=False)
    role = Column(String, default=UserRole.user.value, nullable=False)
    status = Column(Enum(UserStatus), default=UserStatus.normal, nullable=False)

    nickname = Column(String, unique=True, nullable=False)
    phone_number = Column(String, unique=True, index=True, nullable=True)
    avatar_image_url = Column(String, nullable=False)
    background_image_url = Column(String, nullable=False)
    introduction = Column(String, nullable=True)
    gender = Column(Enum(Gender), nullable=True)
    birthday = Column(String, nullable=True)
    location = Column(String, nullable=True)
    identity_auth_name = Column(String, nullable=True)
    is_realname_auth = Column(Boolean, default=False, nullable=False)
    is_identity_auth = Column(Boolean, default=False, nullable=False)
    is_display_gender = Column(Boolean, default=False, nullable=False)
    is_display_age = Column(Boolean, default=False, nullable=False)
    is_display_location = Column(Boolean, default=False, nullable=False)
    enable_auto_location = Column(Boolean, default=False, nullable=False)
    is_display_identity = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UserBanHistory(Base):
    __tablename__ = "user_bans_history"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    banned_times = Column(Integer, default=1, nullable=False)
    unban_time = Column(DateTime(timezone=True), nullable=False)


# 用户关注关系表
class UserFollow(Base):
    __tablename__ = "user_follows"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    follower_id = Column(UUID(as_uuid=True), nullable=False)
    followed_id = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("follower_id", "followed_id", name="uq_follower_followed"),
    )

    # 与users表建立关联关系，可以方便的获取关注者和被关注者的User对象
    follower = relationship("User", primaryjoin="foreign(UserFollow.follower_id)==User.id")
    followed = relationship("User", primaryjoin="foreign(UserFollow.followed_id)==User.id")
