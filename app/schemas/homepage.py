from app.schemas.base import I18nSchema
from typing import Optional, List, Any
from enum import Enum
from pydantic import BaseModel, Field
from fastapi import Form


class AnnouncementInfo(I18nSchema):
    content: str
    date: str

    i18n_fields = {
        "content": "content_i18n"
    }

class AnnouncementInfoResponse(BaseModel):
    announcements: List[AnnouncementInfo]

class AnnouncementUpdateForm(BaseModel):
    content: dict

class AdsInfoInternal(BaseModel):
    image_url: str
    web_url: str | None
    is_displayed: bool

class AdsInfo(BaseModel):
    image_url: str
    web_url: str | None

class BannerAdsInfoResponse(BaseModel):
    ads: List[AdsInfo]

class AdCreateForm(BaseModel):
    web_url: str | None
    is_displayed: bool

    @classmethod
    def as_form(
        cls,
        web_url: str | None = Form(None),
        is_displayed: bool = Form(...)
    ):
        return cls(
            web_url=web_url,
            is_displayed=is_displayed
        )