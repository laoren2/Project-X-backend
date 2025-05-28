from typing import Optional, List
from app.schemas.base import ORMBase
from enum import Enum


class PersonInfoResponse(ORMBase):
    user_id: str
    avatar_image_url: str
    nickname: str

class RelationListResponse(ORMBase):
    users: List[PersonInfoResponse]
    next_cursor_created_at: Optional[str]
    next_cursor_id: Optional[str]
    has_more: bool
