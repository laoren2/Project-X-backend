from fastapi import Form
from app.schemas.base import ORMBase
from datetime import datetime
from enum import Enum
from typing import List, Literal, Tuple
from pydantic import BaseModel
from app.schemas.common import PersonInfoResponse


class TrainingType(str, Enum):
    freeTraining = "freeTraining"
    routeTraining = "routeTraining"

class RouteType(str, Enum):
    pointToPoint = "pointToPoint"
    multiPoints = "multiPoints"
    #curve = "curve"

class RouteSortType(str, Enum):
    participation = "participation"
    distance = "distance"

class RouteApplyStatus(str, Enum):
    none = "none"               # 未申请（默认，可申请）
    pending = "pending"         # 审核中
    approved = "approved"       # 审核通过（已转成赛道）
    rejected = "rejected"       # 审核驳回（允许重新申请，回到可申请态由 service 控制）

class TrackLifecycle(str, Enum):
    oneMonth = "oneMonth"       # 自审核通过起 1 个月
    twoMonth = "twoMonth"       # 自审核通过起 2 个月
    seasonEnd = "seasonEnd"     # 到赛季结束（= 承载 Event 的 end_date）

class GridEffectType(str, Enum):
    buff = "buff"
    debuff = "debuff"

class WeatherSnapshotResponse(BaseModel):
    condition: str
    temperature_c: float

class Checkpoint(BaseModel):
    kind: Literal["checkpoint"]
    lat: float
    lng: float
    radius: float

class Segment(BaseModel):
    kind: Literal["segment"]
    points: List[Tuple[float, float]]
    width: float

class RegionExploreResponse(BaseModel):
    explored_grids: int
    total_grids: int


class GridTileKey(BaseModel):
    level: int
    x: int
    y: int

class GridTileRequest(BaseModel):
    region_id: str
    tiles: List[GridTileKey]

class GridCellInfo(BaseModel):
    grid_x: int
    grid_y: int
    count: int

# 历史卡片缩略轨迹的单个坐标点（服务端已降采样，仅含经纬度 + 活动段序号）
class TrackPoint(BaseModel):
    lat: float
    lon: float
    segment: int = 0    # 活动段序号：free training 暂停恢复时 +1，客户端据此分段绘制（缺口不连线）；race/route 恒为 0

class GridFamiliarityMeResponse(BaseModel):
    count: int
    rank: int

class GridFamiliarityRankInfo(BaseModel):
    user: PersonInfoResponse
    count: int
    rank: int

class GridFamiliarityRankListResponse(BaseModel):
    data: List[GridFamiliarityRankInfo]

# 用户已占领网格数（基础格中 familiarity_count 排名第一的网格数）
class GridOccupancyResponse(BaseModel):
    occupied_count: int

# 训练模块：最近 7 天每日训练汇总
class WeeklyTrainingDayInfo(BaseModel):
    date: str               # "YYYY-MM-DD"
    total_time: float       # 当日训练总时长（秒）
    delta_state: int        # 当日 momentum 变化量
    total_distance: float   # 当日训练总距离（km）

class WeeklyTrainingSummaryResponse(BaseModel):
    current_state: int                      # 当前 momentum 值
    days: List[WeeklyTrainingDayInfo]       # 7 天，旧→新
