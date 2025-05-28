# BaseResponse 和 BizException 的定义
from typing import Optional, Generic, TypeVar
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict
from enum import Enum

T = TypeVar("T")

class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class BaseResponse(BaseModel, Generic[T]):
    access_token: Optional[str] = None
    code: int
    message: str
    data: Optional[T] = None

    @classmethod
    def success(cls, token: Optional[str] = None, message: str = "success", data: Optional[T] = None):
        return cls(access_token=token, code=0, message=message, data=data)

    @classmethod
    def error(cls, code: int, message: str):
        return cls(access_token=None, code=code, message=message, data=None)


class BizException(HTTPException):
    def __init__(self, code: int, message: str, status_code: int = 200):
        detail = {
            "access_token": None,
            "code": code,
            "message": message,
            "data": None
        }
        super().__init__(status_code=status_code, detail=detail)

class RelationshipStatus(str, Enum):
    friend = "friend"
    following = "following"
    follower = "follower"
    none = "none"  # 当无关系时标记