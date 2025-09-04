from fastapi import Form
from app.schemas.base import ORMBase
from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel
from app.schemas.common import EquipCardBaseInfo, PersonInfoResponse



class RecordStatus(str, Enum):
    notStarted = "notStarted"
    recording = "recording"
    completed = "completed"

class TeamStatus(str, Enum):
    prepared = "prepared"
    locked = "locked"
    ready = "ready"
    recording = "recording"
    completed = "completed"

class TeamRelationship(str, Enum):
    created = "created"     # 我创建的
    joined = "joined"       # 我加入的
    applied = "applied"     # 我申请的

class RegionCreate(ORMBase):
    name: str

class RegionsResponse(ORMBase):
    regions_with_events: List[str]

class CardBonusItem(BaseModel):
    card_id: str
    bonus_time: float

class CardBonusInfo(BaseModel):
    card: EquipCardBaseInfo
    bonus_time: float

class PathPoint(BaseModel):
    lat: float
    lon: float
    speed: float
    timestamp: float

class MemberScoreInfo(BaseModel):
    user_info: PersonInfoResponse
    status: RecordStatus
    final_time: Optional[float]