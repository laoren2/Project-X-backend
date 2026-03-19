from typing import Optional, Generic, TypeVar, ClassVar, Dict
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict
from enum import Enum

T = TypeVar("T")

class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Language(str, Enum):
    zh_hans = "zh-Hans"
    zh_hant = "zh-Hant"
    en = "en"
    ko = "ko"

DEFAULT_LANGUAGE = Language.en

def pick_i18n_text(
    data: dict | None,
    lang: Language,
) -> str:
    if not data:
        return ""

    # 1️⃣ 精确匹配
    if lang.value in data:
        return data[lang.value]

    # 2️⃣ 语言前缀匹配（zh）
    short = lang.value.split("-")[0]
    for key, value in data.items():
        if key.startswith(short):
            return value

    # 3️⃣ fallback to default
    if DEFAULT_LANGUAGE.value in data:
        return data[DEFAULT_LANGUAGE.value]

    # 4️⃣ 最后兜底
    return next(iter(data.values()))

class I18nSchema(BaseModel):
    """
    i18n_fields:
      key   -> response field name
      value -> orm i18n json field name
    """
    i18n_fields: ClassVar[Dict[str, str]] = {}

    @classmethod
    def from_orm_with_lang(cls, orm_obj, lang: Language):
        if not cls.i18n_fields:
            raise RuntimeError(f"{cls.__name__} 未定义 i18n_fields")
        data = {}
        # 1️⃣ 普通字段（同名字段）
        for field in cls.model_fields:
            if field in cls.i18n_fields:
                continue
            if hasattr(orm_obj, field):
                data[field] = getattr(orm_obj, field)

        # 2️⃣ i18n 字段自动转换
        for resp_field, orm_i18n_field in cls.i18n_fields.items():
            raw_i18n = getattr(orm_obj, orm_i18n_field, None)
            data[resp_field] = pick_i18n_text(raw_i18n, lang)

        return cls(**data)

    class Config:
        from_attributes = True

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
    def __init__(
        self, 
        code: int, 
        message: str, 
        status_code: int = 200,
        params: dict | None = None
    ):
        detail = {
            "access_token": None,
            "code": code,
            "message": message,
            "params": params or {},
            "data": None
        }
        super().__init__(status_code=status_code, detail=detail)
