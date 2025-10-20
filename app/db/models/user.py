import uuid
from sqlalchemy import Column, String, Boolean, DateTime, Date, func, UniqueConstraint, Integer, Enum, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from app.schemas.asset import CCAssetType
from app.schemas.common import SportType
from app.schemas.user import UserRole, Gender, UserStatus
from app.db.base import Base
from sqlalchemy.orm import relationship


# 用户表
# todo: 将个人配置拆分出去只保留基本信息
class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(String, unique=True, index=True, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.user.value, nullable=False)
    status = Column(Enum(UserStatus), default=UserStatus.normal, nullable=False)

    nickname = Column(String, nullable=False)
    phone_number = Column(String, nullable=True)
    apple_id = Column(String, nullable=True)
    apple_email = Column(String, nullable=True)
    avatar_image_url = Column(String, nullable=False)
    background_image_url = Column(String, nullable=False)
    introduction = Column(String, nullable=True)
    location = Column(String, nullable=True)
    identity_auth_name = Column(String, nullable=True)

    settings = relationship("UserSetting", primaryjoin="foreign(User.id)==UserSetting.user_id", uselist=False)
    real_name_info = relationship("UserRealNameHK", primaryjoin="foreign(User.id)==UserRealNameHK.user_id", uselist=False, overlaps="settings")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        # 否则账号无法找回
        CheckConstraint(
            "phone_number IS NOT NULL OR apple_id IS NOT NULL",
            name="ck_user_phone_or_apple_id_not_null"
        ),
        # 部分唯一索引：仅对 status='normal' 或 'banned' 的数据生效
        Index(
            "uq_users_nickname_status",
            "nickname",
            unique=True,
            postgresql_where=(status.in_([UserStatus.normal, UserStatus.banned]))
        ),
        Index(
            "uq_users_phone_status",
            "phone_number",
            unique=True,
            postgresql_where=(status.in_([UserStatus.normal, UserStatus.banned]))
        )
    )

class UserSetting(Base):
    __tablename__ = "user_settings"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, unique=True)
    is_display_gender = Column(Boolean, default=False, nullable=False)
    is_display_age = Column(Boolean, default=False, nullable=False)
    is_display_location = Column(Boolean, default=False, nullable=False)
    enable_auto_location = Column(Boolean, default=False, nullable=False)
    is_display_identity = Column(Boolean, default=False, nullable=False)
    default_sport = Column(Enum(SportType), default=SportType.bike, nullable=False)     # 用户主页默认展示运动

class UserRealNameHK(Base):
    __tablename__ = "user_real_name_hk"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, unique=True)
    gender = Column(Enum(Gender), nullable=False)
    birth_date = Column(String, nullable=False)
    name_Cn = Column(String, nullable=True)
    name_En = Column(String, nullable=False)
    card_id = Column(String, nullable=False)
    name_code = Column(String, nullable=True)
    issued_code = Column(String, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), server_onupdate=func.now(), nullable=False)


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

# 用户签到记录表
class UserSignIn(Base):
    __tablename__ = "user_sign_in"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    is_vip = Column(Boolean, nullable=False)    # 是否是领取vip签到奖励
    sign_in_date = Column(Date, nullable=False)     # 使用 Date 记录已签到的日期(注意暂时只支持香港地区，需要考虑存储为 UTC+8 时区)

    # 添加user_id、is_vip和sign_in_date的唯一约束
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "is_vip", "sign_in_date", name="uq_user_vip_sign_in_date"),
    )

# 连续签到奖励表
class SignInReward(Base):
    __tablename__ = "sign_in_rewards"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    days = Column(Integer, nullable=False)      # 连续签到天数（0-7）
    reward_type = Column(Enum(CCAssetType), nullable=False)
    reward_count = Column(Integer, nullable=False)
    reward_type_vip = Column(Enum(CCAssetType), nullable=False)
    reward_count_vip = Column(Integer, nullable=False)