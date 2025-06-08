from fastapi import Form
from app.schemas.base import ORMBase
from datetime import datetime
from enum import Enum
from typing import List


class SportType(str, Enum):
    running = "running"
    bike = "bike"

class SeasonCreateForm:
    name: str
    start_date: datetime
    end_date: datetime
    sport_type: SportType

    def __init__(
        self,
        name: str = Form(...),
        start_date: datetime = Form(...),
        end_date: datetime = Form(...),
        sport_type: SportType = Form(...)
    ):
        self.name = name
        self.start_date = start_date
        self.end_date = end_date
        self.sport_type = sport_type

class RegionCreate(ORMBase):
    name: str

class EventCreateForm:
    name: str
    description: str
    start_date: datetime
    end_date: datetime
    season_name: str
    region_name: str
    sport_type: SportType

    def __init__(
        self,
        name: str = Form(...),
        description: str = Form(...),
        start_date: datetime = Form(...),
        end_date: datetime = Form(...),
        season_name: str = Form(...),
        region_name: str = Form(...),
        sport_type: SportType = Form(...)
    ):
        self.name = name
        self.description = description
        self.start_date = start_date
        self.end_date = end_date
        self.season_name = season_name
        self.region_name = region_name
        self.sport_type = sport_type

class EventUpdateForm:
    event_id: str
    name: str
    description: str
    start_date: datetime
    end_date: datetime

    def __init__(
        self,
        event_id: str = Form(...),
        name: str = Form(...),
        description: str = Form(...),
        start_date: datetime = Form(...),
        end_date: datetime = Form(...)
    ):
        self.event_id = event_id
        self.name = name
        self.description = description
        self.start_date = start_date
        self.end_date = end_date

class EventBaseInfo(ORMBase):
    event_id: str
    name: str
    description: str
    start_date: str
    end_date: str
    season_name: str
    region_name: str
    sport_type: SportType
    image_url: str

class EventListResponse(ORMBase):
    events: List[EventBaseInfo]

class SeasonBaseInfo(ORMBase):
    season_id: str
    name: str
    start_date: str
    end_date: str
    sport_type: SportType
    image_url: str
