from fastapi import Form
from app.schemas.base import ORMBase
from datetime import datetime
from enum import Enum
from typing import List, Optional


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

class SeasonBaseInfo(ORMBase):
    season_id: str
    name: str
    start_date: str
    end_date: str
    image_url: str

class RegionCreate(ORMBase):
    name: str

class RegionsResponse(ORMBase):
    regions_with_events: List[str]

class BikeEventCreateForm:
    name: str
    description: str
    start_date: datetime
    end_date: datetime
    season_name: str
    region_name: str

    def __init__(
        self,
        name: str = Form(...),
        description: str = Form(...),
        start_date: datetime = Form(...),
        end_date: datetime = Form(...),
        season_name: str = Form(...),
        region_name: str = Form(...)
    ):
        self.name = name
        self.description = description
        self.start_date = start_date
        self.end_date = end_date
        self.season_name = season_name
        self.region_name = region_name

class BikeEventUpdateForm:
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

class BikeEventBaseInfoInternal(ORMBase):
    event_id: str
    name: str
    description: str
    start_date: str
    end_date: str
    season_name: str
    region_name: str
    image_url: str

class BikeEventListInternalResponse(ORMBase):
    events: List[BikeEventBaseInfoInternal]

class BikeEventBaseInfo(ORMBase):
    event_id: str
    name: str
    description: str
    start_date: str
    end_date: str
    image_url: str

class BikeEventListResponse(ORMBase):
    events: List[BikeEventBaseInfo]

class BikeTrackCreateForm:
    name: str
    start_date: datetime
    end_date: datetime
    event_name: str
    season_name: str
    region_name: str
    from_latitude: float
    from_longitude: float
    to_latitude: float
    to_longitude: float
    elevationDifference: int
    subRegioName: str
    fee: int
    prizePool: int

    def __init__(
        self,
        name: str = Form(...),
        start_date: datetime = Form(...),
        end_date: datetime = Form(...),
        event_name: str = Form(...),
        season_name: str = Form(...),
        region_name: str = Form(...),
        from_latitude: float = Form(...),
        from_longitude: float = Form(...),
        to_latitude: float = Form(...),
        to_longitude: float = Form(...),
        elevationDifference: int = Form(...),
        subRegioName: str = Form(...),
        fee: int = Form(...),
        prizePool: int = Form(...)
    ):
        self.name = name
        self.start_date = start_date
        self.end_date = end_date
        self.event_name = event_name
        self.season_name = season_name
        self.region_name = region_name
        self.from_latitude = from_latitude
        self.from_longitude = from_longitude
        self.to_latitude = to_latitude
        self.to_longitude = to_longitude
        self.elevationDifference = elevationDifference
        self.subRegioName = subRegioName
        self.fee = fee
        self.prizePool = prizePool


class BikeTrackUpdateForm:
    track_id: str
    name: str
    start_date: datetime
    end_date: datetime
    from_latitude: float
    from_longitude: float
    to_latitude: float
    to_longitude: float
    elevationDifference: int
    subRegioName: str
    fee: int
    prizePool: int

    def __init__(
        self,
        track_id: str = Form(...),
        name: str = Form(...),
        start_date: datetime = Form(...),
        end_date: datetime = Form(...),
        from_latitude: float = Form(...),
        from_longitude: float = Form(...),
        to_latitude: float = Form(...),
        to_longitude: float = Form(...),
        elevationDifference: int = Form(...),
        subRegioName: str = Form(...),
        fee: int = Form(...),
        prizePool: int = Form(...)
    ):
        self.track_id = track_id
        self.name = name
        self.start_date = start_date
        self.end_date = end_date
        self.from_latitude = from_latitude
        self.from_longitude = from_longitude
        self.to_latitude = to_latitude
        self.to_longitude = to_longitude
        self.elevationDifference = elevationDifference
        self.subRegioName = subRegioName
        self.fee = fee
        self.prizePool = prizePool


class BikeTrackBaseInfoInternal(ORMBase):
    track_id: str
    name: str
    start_date: str
    end_date: str
    event_name: str
    season_name: str
    region_name: str
    image_url: str

    from_latitude: str
    from_longitude: str
    to_latitude: str
    to_longitude: str
    elevation_difference: str
    sub_region_name: str
    fee: str
    prize_pool: str


class BikeTrackListInternalResponse(ORMBase):
    tracks: List[BikeTrackBaseInfoInternal]


class BikeTrackBaseInfo(ORMBase):
    track_id: str
    name: str
    start_date: str
    end_date: str
    image_url: str

    from_latitude: float
    from_longitude: float
    to_latitude: float
    to_longitude: float
    elevation_difference: int
    sub_region_name: str
    fee: int
    prize_pool: int

class BikeTrackListResponse(ORMBase):
    tracks: List[BikeTrackBaseInfo]


class RunningEventCreateForm:
    name: str
    description: str
    start_date: datetime
    end_date: datetime
    season_name: str
    region_name: str

    def __init__(
        self,
        name: str = Form(...),
        description: str = Form(...),
        start_date: datetime = Form(...),
        end_date: datetime = Form(...),
        season_name: str = Form(...),
        region_name: str = Form(...)
    ):
        self.name = name
        self.description = description
        self.start_date = start_date
        self.end_date = end_date
        self.season_name = season_name
        self.region_name = region_name

class RunningEventUpdateForm:
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

class RunningEventBaseInfoInternal(ORMBase):
    event_id: str
    name: str
    description: str
    start_date: str
    end_date: str
    season_name: str
    region_name: str
    image_url: str

class RunningEventListInternalResponse(ORMBase):
    events: List[RunningEventBaseInfoInternal]

class RunningEventBaseInfo(ORMBase):
    event_id: str
    name: str
    description: str
    start_date: str
    end_date: str
    image_url: str

class RunningEventListResponse(ORMBase):
    events: List[RunningEventBaseInfo]

class RunningTrackCreateForm:
    name: str
    start_date: datetime
    end_date: datetime
    event_name: str
    season_name: str
    region_name: str
    from_latitude: float
    from_longitude: float
    to_latitude: float
    to_longitude: float
    elevationDifference: int
    subRegioName: str
    fee: int
    prizePool: int
    distance: float

    def __init__(
        self,
        name: str = Form(...),
        start_date: datetime = Form(...),
        end_date: datetime = Form(...),
        event_name: str = Form(...),
        season_name: str = Form(...),
        region_name: str = Form(...),
        from_latitude: float = Form(...),
        from_longitude: float = Form(...),
        to_latitude: float = Form(...),
        to_longitude: float = Form(...),
        elevationDifference: int = Form(...),
        subRegioName: str = Form(...),
        fee: int = Form(...),
        prizePool: int = Form(...),
        distance: float = Form(...)
    ):
        self.name = name
        self.start_date = start_date
        self.end_date = end_date
        self.event_name = event_name
        self.season_name = season_name
        self.region_name = region_name
        self.from_latitude = from_latitude
        self.from_longitude = from_longitude
        self.to_latitude = to_latitude
        self.to_longitude = to_longitude
        self.elevationDifference = elevationDifference
        self.subRegioName = subRegioName
        self.fee = fee
        self.prizePool = prizePool
        self.distance = distance


class RunningTrackUpdateForm:
    track_id: str
    name: str
    start_date: datetime
    end_date: datetime
    from_latitude: float
    from_longitude: float
    to_latitude: float
    to_longitude: float
    elevationDifference: int
    subRegioName: str
    fee: int
    prizePool: int
    distance: float

    def __init__(
        self,
        track_id: str = Form(...),
        name: str = Form(...),
        start_date: datetime = Form(...),
        end_date: datetime = Form(...),
        from_latitude: float = Form(...),
        from_longitude: float = Form(...),
        to_latitude: float = Form(...),
        to_longitude: float = Form(...),
        elevationDifference: int = Form(...),
        subRegioName: str = Form(...),
        fee: int = Form(...),
        prizePool: int = Form(...),
        distance: float = Form(...)
    ):
        self.track_id = track_id
        self.name = name
        self.start_date = start_date
        self.end_date = end_date
        self.from_latitude = from_latitude
        self.from_longitude = from_longitude
        self.to_latitude = to_latitude
        self.to_longitude = to_longitude
        self.elevationDifference = elevationDifference
        self.subRegioName = subRegioName
        self.fee = fee
        self.prizePool = prizePool
        self.distance = distance


class RunningTrackBaseInfoInternal(ORMBase):
    track_id: str
    name: str
    start_date: str
    end_date: str
    event_name: str
    season_name: str
    region_name: str
    image_url: str

    from_latitude: str
    from_longitude: str
    to_latitude: str
    to_longitude: str
    elevation_difference: str
    sub_region_name: str
    fee: str
    prize_pool: str
    distance: str


class RunningTrackListInternalResponse(ORMBase):
    tracks: List[RunningTrackBaseInfoInternal]


class RunningTrackBaseInfo(ORMBase):
    track_id: str
    name: str
    start_date: str
    end_date: str
    image_url: str

    from_latitude: float
    from_longitude: float
    to_latitude: float
    to_longitude: float
    elevation_difference: int
    sub_region_name: str
    fee: int
    prize_pool: int
    distance: float

class RunningTrackListResponse(ORMBase):
    tracks: List[RunningTrackBaseInfo]
