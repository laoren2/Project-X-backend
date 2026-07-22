from app.schemas.common import CCAssetRewardResponse, PersonInfoResponse
from app.schemas.competition.common import PathPoint, CardBonusItem, CardBonusInfo
from app.schemas.training.common import RouteType, TrainingType, GridCellInfo, GridTileKey, GridEffectType, RouteApplyStatus, TrackLifecycle, TrackPoint, WeatherSnapshotResponse
from app.schemas.competition.running import RunningTrackTerrainType
from datetime import datetime
from enum import Enum
from typing import List, Optional, Any
from pydantic import BaseModel, Field


class RunningGridConditionType(str, Enum):
    distance = "distance"
    speed = "speed"
    weather = "weather"
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
    client_upload_id: str | None = None                   # 客户端幂等键，重传去重用（旧客户端可不传）

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
    record_count: int      # 当天训练记录数（旧客户端忽略该字段，保持兼容）

class TrainingStatesHistoryResponse(BaseModel):
    history: List[TrainingStatesHistoryInfo]

class TrainingRecordInfo(BaseModel):
    record_id: str
    delta_state: int
    end_time: str
    training_type: TrainingType
    track: List[TrackPoint]      # 已降采样的缩略轨迹（旧客户端忽略该字段，保持兼容）

class TrainingRecordsResponse(BaseModel):
    records: List[TrainingRecordInfo]

class FreeTrainingRecordDetailResponse(BaseModel):
    owner_user_id: str          # 记录归属者业务 ID（客户端据此判断是否本人/可否分享）
    duration: float
    end_time: datetime
    path: List[RunningFreeTrainingPathPoint]
    settlements: dict[str, Any]      # 训练的结算信息
    triggered_buffs: list[dict[str, Any]] = []      # 训练的 buff 快照
    weather: WeatherSnapshotResponse | None = None


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
    participate_count: int                  # 热度（路线训练参与次数），>100 才可申请转赛道
    apply_status: RouteApplyStatus          # 申请转赛道的状态
    route_data: dict

class RunningRouteManageInfoResponse(BaseModel):
    routes: List[RunningRouteMangeInfo]

# 申请热门路线转为赛道（语言取自 Accept-Language，title/sub_region_name 仅保存该语言一档）
class RouteTrackApplyRequest(BaseModel):
    route_id: str
    title: str
    sub_region_name: str
    terrain_type: RunningTrackTerrainType
    lifecycle: TrackLifecycle
    is_premium: bool        # 是否申请为高级赛道；仅高级路线可置 true，普通路线由服务端强制为 false

class RouteTrainingFinishInfo(BaseModel):
    route_id: str
    start_time: datetime
    end_time: datetime
    path: List[RunningRouteTrainingPathPoint]
    bonus_in_cards: List[CardBonusItem]
    client_upload_id: str | None = None                   # 客户端幂等键，重传去重用（旧客户端可不传）

class RouteTrainingFinishResponse(BaseModel):
    record_id: str
    xp_before: int
    xp_delta: int
    training_state_before: int
    training_state_delta: int
    new_grids: int
    cc_rewards: List[CCAssetRewardResponse]

class RouteTrainingRecordDetailResponse(BaseModel):
    owner_user_id: str          # 记录归属者业务 ID（客户端据此判断是否本人/可否分享）
    original_time: float
    final_time: float
    penalty_time: float
    end_time: datetime
    path: List[RunningRouteTrainingPathPoint]
    card_bonus: List[CardBonusInfo]
    settlements: dict[str, Any]
    weather: WeatherSnapshotResponse | None = None

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

# 运动中雷达指引：附近的奖励网格（含中心经纬度，供手表本地算方位/距离）
class RunningNearbyGridInfo(BaseModel):
    grid_x: int
    grid_y: int
    center_lat: float
    center_lon: float
    description: str
    effect_type: GridEffectType
    condition_type: RunningGridConditionType
    condition_params: dict
    reward_type: str
    reward_count: int

class RunningNearbyGridsResponse(BaseModel):
    grids: List[RunningNearbyGridInfo]
