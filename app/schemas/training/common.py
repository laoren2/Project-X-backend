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

class GridFamiliarityMeResponse(BaseModel):
    count: int
    rank: int

class GridFamiliarityRankInfo(BaseModel):
    user: PersonInfoResponse
    count: int
    rank: int

class GridFamiliarityRankListResponse(BaseModel):
    data: List[GridFamiliarityRankInfo]