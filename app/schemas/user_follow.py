from typing import Optional, List
from app.schemas.base import ORMBase
from app.schemas.common import PersonInfoResponse
from enum import Enum



class RelationListResponse(ORMBase):
    users: List[PersonInfoResponse]
    next_cursor_created_at: Optional[str]
    next_cursor_id: Optional[str]
    has_more: bool
