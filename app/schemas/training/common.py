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
    tiles: List[GridTileKey]

class GridCellInfo(BaseModel):
    grid_x: int
    grid_y: int
    count: int

class GridTileInfo(BaseModel):
    key: GridTileKey
    cells: List[GridCellInfo]

class GridTileResponse(BaseModel):
    tiles: List[GridTileInfo]

class GridFamiliarityMeResponse(BaseModel):
    count: int
    rank: int

class GridFamiliarityRankInfo(BaseModel):
    user: PersonInfoResponse
    count: int
    rank: int

class GridFamiliarityRankListResponse(BaseModel):
    data: List[GridFamiliarityRankInfo]