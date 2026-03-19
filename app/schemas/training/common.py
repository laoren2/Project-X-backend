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