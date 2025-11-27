from fastapi import Form
from app.schemas.base import ORMBase
from datetime import datetime
from enum import Enum
from typing import List, Optional, Protocol
from pydantic import BaseModel
from app.schemas.common import EquipCardBaseInfo, PersonInfoResponse, CCAssetType


class RecordStatus(str, Enum):
    notStarted = "notStarted"
    recording = "recording"
    completed = "completed"
    expired = "expired"             # 被系统定时清理的过期记录
    toBeVerified = "toBeVerified"   # 待人工审核的记录
    invalid = "invalid"             # 成绩无效的记录

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

class DailyTaskType(str, Enum):
    distance = "distance"
    time = "time"

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
    user_id: str

# Protocol 接口：定义计算距离所需的最小属性
class LocationPoint(Protocol):
    """用于计算距离的坐标点接口，只需要 lat 和 lon"""
    lat: float
    lon: float

class PathPoint(BaseModel):
    lat: float
    lon: float
    speed: float
    altitude: float
    heart_rate: float | None = None
    timestamp: float

class MemberScoreInfo(BaseModel):
    user_info: PersonInfoResponse
    status: RecordStatus
    final_time: Optional[float]

class DailyTaskResponse(BaseModel):
    type: DailyTaskType
    total_progress: float
    reward_stage1_type: CCAssetType
    reward_stage1: int
    is_reward1_received: bool
    reward_stage2_type: CCAssetType
    reward_stage2: int
    is_reward2_received: bool
    reward_stage3_url: str
    is_reward3_received: bool
    progress: float

class TeamMagicCardBonusInfo(BaseModel):
    card_id: str
    bonus_ratio: float | None = None
    bonus_seconds: float | None = None