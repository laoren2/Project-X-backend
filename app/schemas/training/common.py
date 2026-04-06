from fastapi import Form
from app.schemas.base import ORMBase
from datetime import datetime
from enum import Enum
from typing import List, Optional, Protocol
from pydantic import BaseModel


class RegionExploreResponse(BaseModel):
    explored_grids: int
    total_grids: int
    boundary: dict


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