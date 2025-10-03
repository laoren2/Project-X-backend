from fastapi import Form
from pydantic import BaseModel
from typing import Optional
from app.schemas.base import ORMBase
from enum import Enum

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

class AuthContext(BaseModel):
    payload: dict
    new_token: Optional[str] = None

class UserBaseInfo(ORMBase):
    user_id: str
    nickname: str
    phone_number: Optional[str] = None
    apple_email: Optional[str] = None
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
        is_display_gender: bool = Form(...),
        is_display_age: bool = Form(...),
        is_display_location: bool = Form(...),
        enable_auto_location: bool = Form(...),
        is_display_identity: bool = Form(...)
    ):
        self.nickname = nickname
        self.introduction = introduction
        self.location = location
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

class UserAnyResponse(UserMeResponse):
    relationship: RelationshipStatus

class SMSCodeRequest(ORMBase):
    phone_number: str

class SendCodeResponse(ORMBase):
    code: str

class SMSCodeVerify(ORMBase):
    phone_number: str
    code: str

class GetAnyUserRequest(ORMBase):
    user_id: str