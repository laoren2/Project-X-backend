from fastapi import Form
from pydantic import BaseModel, field_validator
from typing import Optional, Any
from app.schemas.base import ORMBase
from enum import Enum
from app.core.storage import build_resource_url
from datetime import date
import uuid

from app.schemas.common import SportType


class UserRole(str, Enum):
    user = "user"
    admin = "admin"

class Gender(str, Enum):
    male = "male"
    female = "female"

class UserStatus(str, Enum):
    normal = "normal"
    deleted = "deleted"
    banned = "banned"

# 订阅相关（仅 Apple：按月/季/年）
class SubscriptionPeriod(str, Enum):
    monthly = "monthly"
    quarterly = "quarterly"
    yearly = "yearly"


class SubscriptionEventType(str, Enum):
    rewarded = "rewarded"               # 奖励
    created = "created"                 # 新创建订阅
    renewed = "renewed"                 # 续费
    refunded = "refunded"               # 退订
    auto_renew_off = "auto_renew_off"   # 开启自动续费
    auto_renew_on = "auto_renew_on"     # 关闭自动续费
    grace_started = "grace_started"     # Apple 扣款失败/待重试，进入宽限期
    grace_ended = "grace_ended"         # 重试成功或超时，宽限期结束

class RealNameMethod(str, Enum):
    idcard = "idcard"
    passport = "passport"
    drivingLicense = "drivingLicense"

class AuthContext(BaseModel):
    payload: dict
    new_token: Optional[str] = None

class UserBaseInfo(ORMBase):
    user_id: str
    apple_iap_token: str
    nickname: str
    phone_number: Optional[str] = None
    apple_email: Optional[str] = None
    email: Optional[str] = None
    avatar_image_url: str
    background_image_url: str
    introduction: Optional[str] = None
    gender: Optional[str] = None
    birthday: Optional[str] = None
    location: Optional[str] = None
    identity_auth_name: Optional[str] = None
    is_display_gender: bool = False
    is_display_age: bool = False
    is_display_location: bool = False
    enable_auto_location: bool = False
    is_display_identity: bool = False
    default_sport: SportType = SportType.bike
    status: UserStatus
    is_vip: bool = False

    @field_validator('apple_iap_token', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v: Any) -> str:
        """将 UUID 对象转换为字符串"""
        if isinstance(v, uuid.UUID):
            return str(v)
        # 如果已经是字符串，直接返回
        return v
    
    @field_validator("avatar_image_url", "background_image_url", mode="after")
    def build_avatar_url(cls, v):
        if not v:
            return v
        return build_resource_url(v)

class UserRelationInfo(ORMBase):
    follower: int = 0
    followed: int = 0
    friends: int = 0

class UserCreateInfo(ORMBase):
    user_id: str
    phone_number: str
    nickname: Optional[str] = None

class UserUpdateForm:
    nickname: str
    introduction: Optional[str]
    location: Optional[str]
    gender: Optional[Gender]
    birthday: Optional[date]
    is_display_gender: bool
    is_display_age: bool
    is_display_location: bool
    enable_auto_location: bool
    is_display_identity: bool
    
    def __init__(
        self,
        nickname: str = Form(...),
        introduction: Optional[str] = Form(None),
        location: Optional[str] = Form(None),
        gender: Optional[Gender] = Form(None),
        birthday: Optional[date] = Form(None),
        is_display_gender: bool = Form(...),
        is_display_age: bool = Form(...),
        is_display_location: bool = Form(...),
        enable_auto_location: bool = Form(...),
        is_display_identity: bool = Form(...)
    ):
        self.nickname = nickname
        self.introduction = introduction
        self.location = location
        self.gender = gender
        self.birthday = birthday
        self.is_display_gender = is_display_gender
        self.is_display_age = is_display_age
        self.is_display_location = is_display_location
        self.enable_auto_location = enable_auto_location
        self.is_display_identity = is_display_identity

class RelationshipStatus(str, Enum):
    friend = "friend"
    following = "following"
    follower = "follower"
    none = "none"  # 当无关系时标记

class LoginResponse(ORMBase):
    user: UserBaseInfo
    relation: UserRelationInfo
    role: UserRole
    isRegister: bool = False

class UserBaseInfoResponse(ORMBase):
    user: UserBaseInfo

class UserMeResponse(ORMBase):
    user: UserBaseInfo
    relation: UserRelationInfo
    origin_transaction_id: str | None

class UserAnyResponse(ORMBase):
    user: UserBaseInfo
    relation: UserRelationInfo
    relationship: RelationshipStatus

class SMSCodeRequest(ORMBase):
    phone_number: str

class SendCodeResponse(ORMBase):
    code: str

class SMSCodeVerify(ORMBase):
    phone_number: str
    code: str
    timezone: str = "UTC"

class EmailCodeRequest(BaseModel):
    email_address: str

class EmailCodeVerify(ORMBase):
    email_address: str
    code: str
    timezone: str = "UTC"

class GetAnyUserRequest(ORMBase):
    user_id: str

class SubscriptionStatusResponse(BaseModel):
    is_active: bool
    auto_renew: Optional[bool] = None
    started_at: Optional[str] = None
    expired_at: Optional[str] = None
    #grace_until: Optional[str] = None

class IAPJWSRequest(BaseModel):
    jws: str
    timezone: str = "UTC"

class IAPTransactionRequest(BaseModel):
    transaction_id: str

class SubscriptionQueryInfo(BaseModel):
    enforce: bool
    transaction_id: str | None = None

class RealNameForm(BaseModel):
    country_code: str
    method: RealNameMethod

    @classmethod
    def as_form(
        cls,
        country_code: str = Form(...),
        method: RealNameMethod = Form(...)
    ):
        return cls(
            country_code=country_code,
            method=method,
        )