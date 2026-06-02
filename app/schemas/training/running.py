from app.schemas.common import CCAssetRewardResponse, PersonInfoResponse
from app.schemas.competition.common import PathPoint, CardBonusItem, CardBonusInfo
from app.schemas.training.common import RouteType, TrainingType, GridCellInfo, GridTileKey, GridEffectType
from app.schemas.competition.running import RunningTrackTerrainType
from datetime import datetime
from enum import Enum
from typing import List, Optional, Any
from pydantic import BaseModel, Field


class RunningGridConditionType(str, Enum):
    distance = "distance"
    speed = "speed"
    none = "none"

class RunningFreeTrainingPathPoint(BaseModel):
    base: PathPoint
    
    power: float | None = None
    step_cadence: float | None = None
    vertical_amplitude: float | None = None
    touchdown_time: float | None = None
    step_size: float | None = None

class RunningRouteTrainingPathPoint(BaseModel):
    base: PathPoint
    
    power: float | None = None
    step_cadence: float | None = None
    vertical_amplitude: float | None = None
    touchdown_time: float | None = None
    step_size: float | None = None
    card_bonus: List[CardBonusItem] = Field(default_factory=list)

class FreeTrainingFinishInfo(BaseModel):
    start_time: datetime
    end_time: datetime
    path: List[RunningFreeTrainingPathPoint]

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
    path: List[RunningFreeTrainingPathPoint]
    settlements: dict[str, Any]      # 训练的结算信息
    triggered_buffs: list[dict[str, Any]] = []      # 训练的 buff 快照


class CreateRouteRequest(BaseModel):
    title: str
    region_id: str
    terrain_type: RunningTrackTerrainType
    is_public: bool
    enable_ranklist: bool
    enable_magiccard: bool
    route_type: RouteType
    route_data: dict

class UpdateRouteRequest(BaseModel):
    route_id: str
    title: str
    terrain_type: RunningTrackTerrainType
    is_public: bool
    enable_ranklist: bool
    enable_magiccard: bool
    route_type: RouteType
    route_data: dict

class RunningRouteInfo(BaseModel):
    route_id: str
    title: str
    route_type: RouteType
    terrain_type: RunningTrackTerrainType
    is_premium: bool
    enable_magiccard: bool
    distance: float
    total_distance: float
    elevation_diff: int
    participate_count: int
    route_data: dict

class RunningRouteInfoResponse(BaseModel):
    routes: List[RunningRouteInfo]
    next_cursor: str | None

class RunningRouteMangeInfo(BaseModel):
    route_id: str
    title: str
    is_public: bool
    route_type: RouteType
    terrain_type: RunningTrackTerrainType
    is_premium: bool
    enable_magiccard: bool
    route_data: dict

class RunningRouteManageInfoResponse(BaseModel):
    routes: List[RunningRouteMangeInfo]

class RouteTrainingFinishInfo(BaseModel):
    route_id: str
    start_time: datetime
    end_time: datetime
    path: List[RunningRouteTrainingPathPoint]
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
    path: List[RunningRouteTrainingPathPoint]
    card_bonus: List[CardBonusInfo]
    settlements: dict[str, Any]

class RunningRouteRankInfo(BaseModel):
    rank: int
    duration_seconds: float
    user: PersonInfoResponse

class RunningRouteRanklistResponse(BaseModel):
    ranklist: List[RunningRouteRankInfo]
    next_cursor: str | None

class RunningGridBuffPreview(BaseModel):
    grid_x: int
    grid_y: int
    effect_type: str
    condition_type: RunningGridConditionType
    reward_type: str

class RunningGridTileInfo(BaseModel):
    key: GridTileKey
    cells: List[GridCellInfo]
    buff_info: List[RunningGridBuffPreview]

class RunningGridDetailInfo(BaseModel):
    description: str
    effect_type: GridEffectType
    condition_type: RunningGridConditionType
    condition_params: dict
    reward_type: str
    reward_count: int

class RunningGridInfoResponse(BaseModel):
    grids: List[RunningGridDetailInfo]

class RunningGridTileResponse(BaseModel):
    tiles: List[RunningGridTileInfo]