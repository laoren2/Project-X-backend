from fastapi import Form
from app.schemas.base import ORMBase
from app.schemas.common import CCAssetRewardResponse, PersonInfoResponse
from app.schemas.competition.bike import BikeTrackTerrainType
from app.schemas.competition.common import PathPoint, CardBonusItem, CardBonusInfo
from app.schemas.training.common import RouteType, TrainingType, GridCellInfo, GridTileKey, GridEffectType
from datetime import datetime
from enum import Enum
from typing import List, Optional, Any
from pydantic import BaseModel, Field


class BikeGridConditionType(str, Enum):
    distance = "distance"
    speed = "speed"
    none = "none"

class BikeFreeTrainingPathPoint(BaseModel):
    base: PathPoint
    
    power: float | None = None
    pedal_cadence: float | None = None

class BikeRouteTrainingPathPoint(BaseModel):
    base: PathPoint
    
    power: float | None = None
    pedal_cadence: float | None = None
    card_bonus: List[CardBonusItem] = Field(default_factory=list)

class FreeTrainingFinishInfo(BaseModel):
    start_time: datetime
    end_time: datetime
    path: List[BikeFreeTrainingPathPoint]

class FreeTrainingFinishResponse(BaseModel):
    record_id: str
    xp_before: int
    xp_delta: int
    training_state_before: int
    training_state_delta: int
    new_grids: int
    triggered_buff_count: int
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
    training_type: TrainingType

class TrainingRecordsResponse(BaseModel):
    records: List[TrainingRecordInfo]

class FreeTrainingRecordDetailResponse(BaseModel):
    duration: float
    path: List[BikeFreeTrainingPathPoint]
    settlements: dict[str, Any]      # 训练的结算信息
    triggered_buffs: list[dict[str, Any]] = []      # 训练的 buff 快照


class CreateRouteRequest(BaseModel):
    title: str
    region_id: str
    terrain_type: BikeTrackTerrainType
    is_public: bool
    enable_ranklist: bool
    enable_magiccard: bool
    route_type: RouteType
    route_data: dict

class UpdateRouteRequest(BaseModel):
    route_id: str
    title: str
    terrain_type: BikeTrackTerrainType
    is_public: bool
    enable_ranklist: bool
    enable_magiccard: bool
    route_type: RouteType
    route_data: dict

class BikeRouteInfo(BaseModel):
    route_id: str
    title: str
    route_type: RouteType
    terrain_type: BikeTrackTerrainType
    is_premium: bool
    enable_magiccard: bool
    distance: float
    total_distance: float
    elevation_diff: int
    participate_count: int
    route_data: dict

class BikeRouteInfoResponse(BaseModel):
    routes: List[BikeRouteInfo]
    next_cursor: str | None

class BikeRouteMangeInfo(BaseModel):
    route_id: str
    title: str
    is_public: bool
    route_type: RouteType
    terrain_type: BikeTrackTerrainType
    is_premium: bool
    enable_magiccard: bool
    route_data: dict

class BikeRouteManageInfoResponse(BaseModel):
    routes: List[BikeRouteMangeInfo]

class RouteTrainingFinishInfo(BaseModel):
    route_id: str
    start_time: datetime
    end_time: datetime
    path: List[BikeRouteTrainingPathPoint]
    bonus_in_cards: List[CardBonusItem]

class RouteTrainingFinishResponse(BaseModel):
    record_id: str
    xp_before: int
    xp_delta: int
    training_state_before: int
    training_state_delta: int
    new_grids: int
    cc_rewards: List[CCAssetRewardResponse]

class RouteTrainingRecordDetailResponse(BaseModel):
    original_time: float
    final_time: float
    penalty_time: float
    path: List[BikeRouteTrainingPathPoint]
    card_bonus: List[CardBonusInfo]
    settlements: dict[str, Any]

class BikeRouteRankInfo(BaseModel):
    rank: int
    duration_seconds: float
    user: PersonInfoResponse

class BikeRouteRanklistResponse(BaseModel):
    ranklist: List[BikeRouteRankInfo]
    next_cursor: str | None

class BikeGridBuffPreview(BaseModel):
    grid_x: int
    grid_y: int
    effect_type: str
    condition_type: BikeGridConditionType
    reward_type: str

class BikeGridTileInfo(BaseModel):
    key: GridTileKey
    cells: List[GridCellInfo]
    buff_info: List[BikeGridBuffPreview]

class BikeGridDetailInfo(BaseModel):
    description: str
    effect_type: GridEffectType
    condition_type: BikeGridConditionType
    condition_params: dict
    reward_type: str
    reward_count: int

class BikeGridInfoResponse(BaseModel):
    grids: List[BikeGridDetailInfo]

class BikeGridTileResponse(BaseModel):
    tiles: List[BikeGridTileInfo]