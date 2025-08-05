from fastapi import Form
from app.schemas.base import ORMBase
from datetime import datetime
from enum import Enum
from typing import List, Optional


class SportType(str, Enum):
    running = "running"
    bike = "bike"

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