from fastapi import Form
from app.schemas.base import ORMBase
from app.schemas.common import CCAssetRewardResponse
from app.schemas.competition.common import PathPoint
from datetime import datetime
from enum import Enum
from typing import List, Optional, Any
from pydantic import BaseModel, Field


class BikeTrainingPathPoint(BaseModel):
    base: PathPoint
    
    power: float | None = None
    pedal_cadence: float | None = None

class FreeTrainingFinishInfo(BaseModel):
    start_time: datetime
    end_time: datetime
    path: List[BikeTrainingPathPoint]

class FreeTrainingFinishResponse(BaseModel):
    record_id: str
    xp_before: int
    xp_delta: int
    training_state_before: int
    training_state_delta: int
    new_grids: int
    cc_rewards: List[CCAssetRewardResponse]

class TrainingStatesHistoryInfo(BaseModel):
    date: str
    delta_state: int

class TrainingStatesHistoryResponse(BaseModel):
    history: List[TrainingStatesHistoryInfo]

class TrainingRecordInfo(BaseModel):
    record_id: str
    delta_state: int
    end_time: str

class TrainingRecordsResponse(BaseModel):
    records: List[TrainingRecordInfo]

class FreeTrainingRecordDetailResponse(BaseModel):
    duration: float
    path: List[BikeTrainingPathPoint]
    settlements: dict[str, Any]      # 训练的结算信息