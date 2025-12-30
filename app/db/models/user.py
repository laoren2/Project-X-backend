import uuid
from sqlalchemy import Column, String, Boolean, DateTime, Date, func, UniqueConstraint, Integer, Enum, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.schemas.common import SportType, CCAssetType
from app.schemas.user import UserRole, Gender, UserStatus, SubscriptionEventType, SubscriptionPeriod
from app.db.base import Base
from sqlalchemy.orm import relationship


# 用户表
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
    email = Column(String, nullable=True)
    apple_iap_token = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, nullable=False)    # 用来和 app store 交易关联
    avatar_image_url = Column(String, nullable=False)
    background_image_url = Column(String, nullable=False)
    introduction = Column(String, nullable=True)
    location = Column(String, nullable=True)
    identity_auth_name = Column(String, nullable=True)

    settings = relationship("UserSetting", primaryjoin="User.id==foreign(UserSetting.user_id)", uselist=False, back_populates="user")
    real_name_info = relationship("UserRealNameHK", primaryjoin="User.id==foreign(UserRealNameHK.user_id)", uselist=False, back_populates="user")
    subscription_info = relationship("UserSubscription", primaryjoin="User.id==foreign(UserSubscription.user_id)", uselist=False, back_populates="user")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        # 否则账号无法找回
        CheckConstraint(
            "phone_number IS NOT NULL OR apple_id IS NOT NULL OR email IS NOT NULL",
            name="ck_user_phone_or_apple_id_or_email_not_null"
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
        ),
        Index(
            "uq_users_apple_id_status",
            "apple_id",
            unique=True,
            postgresql_where=(status.in_([UserStatus.normal, UserStatus.banned]))
        ),
        Index(
            "uq_users_email_status",
            "email",
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

    user = relationship("User", primaryjoin="foreign(UserSetting.user_id) == User.id", uselist=False, back_populates="settings")


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
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", primaryjoin="foreign(UserRealNameHK.user_id) == User.id", uselist=False, back_populates="real_name_info")


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


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    plan_code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    period = Column(Enum(SubscriptionPeriod), nullable=False)
    price_cents = Column(Integer, nullable=False)
    currency = Column(String, nullable=False, default="HKD")
    # Apple 商品ID（仅支持 Apple）
    apple_product_id = Column(String, unique=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    #user_subscription_infos = relationship("UserSubscription", uselist=True, primaryjoin="foreign(UserSubscription.plan_id)==SubscriptionPlan.id", back_populates="plan")


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    product_id = Column(String, nullable=True)                         # 订阅项目

    is_active = Column(Boolean, default=False, nullable=False)
    auto_renew = Column(Boolean, default=False, nullable=False)         # 是否开启了自动续费
    start_at = Column(DateTime(timezone=True), nullable=True)       # 当前订阅的开始日期（todo: 可能有 60 days 以内的误差）
    end_at = Column(DateTime(timezone=True), nullable=True)         # 当前订阅的结束日期
    grace_until = Column(DateTime(timezone=True), nullable=True)    # 当前的宽限期状态

    # Apple 平台交易信息
    apple_original_transaction_id = Column(String, nullable=True)
    apple_latest_transaction_id = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", primaryjoin="foreign(UserSubscription.user_id) == User.id", uselist=False, back_populates="subscription_info")
    #plan = relationship("SubscriptionPlan", uselist=False, primaryjoin="foreign(UserSubscription.plan_id)==SubscriptionPlan.id", back_populates="user_subscription_infos")
    events = relationship("SubscriptionEvent", uselist=True, primaryjoin="foreign(SubscriptionEvent.subscription_id)==UserSubscription.id", back_populates="subscription")


class SubscriptionEvent(Base):
    __tablename__ = "subscription_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    subscription_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    event_type = Column(Enum(SubscriptionEventType), nullable=False)
    payload = Column(JSONB, nullable=True)      # Apple回执
    note = Column(String, nullable=True)        # 备注
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    subscription = relationship("UserSubscription", uselist=False, primaryjoin="foreign(SubscriptionEvent.subscription_id)==UserSubscription.id", back_populates="events")