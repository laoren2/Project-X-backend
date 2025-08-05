from fastapi import Form
from app.schemas.base import ORMBase
from app.schemas.common import PersonInfoResponse, CPAssetBaseInfo
from app.schemas.competition.common import TeamStatus, RecordStatus
from datetime import datetime
from enum import Enum
from typing import List, Optional


class RunningSeasonCreateForm:
    name: str
    start_date: datetime
    end_date: datetime

    def __init__(
        self,
        name: str = Form(...),
        start_date: datetime = Form(...),
        end_date: datetime = Form(...)
    ):
        self.name = name
        self.start_date = start_date
        self.end_date = end_date

class RunningSeasonBaseInfo(ORMBase):
    season_id: str
    name: str
    start_date: str
    end_date: str
    image_url: str

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
    prize_pool: int
    distance: float


class RunningTrackListResponse(ORMBase):
    tracks: List[RunningTrackBaseInfo]


class RunningRankInfo(ORMBase):
    record_id: Optional[str]
    rank: Optional[int]
    duration_seconds: Optional[float]
    reward_coin_amount: int
    reward_coupon_amount: int
    reward_voucher_amount: int
    cpassets: List[CPAssetBaseInfo]

class RunningBeginInfo(ORMBase):
    record_id: str
    start_time: datetime

class RunningFinishInfo(ORMBase):
    record_id: str
    end_time: datetime
    duration_seconds: float

class RunningRecordInfo(ORMBase):
    record_id: str
    region_name: str
    event_name: str
    track_name: str
    track_start_lat: float
    track_start_lng: float
    track_end_lat: float
    track_end_lng: float
    track_end_date: str
    status: RecordStatus
    start_date: Optional[str]
    end_date: Optional[str]
    duration_seconds: Optional[float]

    is_team: bool
    team_title: Optional[str]
    team_competition_date: Optional[str]

    created_at: str

class RunningRecordResponse(ORMBase):
    records: List[RunningRecordInfo]

class RunningSingleRegisterResponse(ORMBase):
    record: RunningRecordInfo
    asset_id: str
    new_balance: int

class RunningLeaderboardInfo(ORMBase):
    record_id: str
    user_info: PersonInfoResponse
    duration_seconds: float

class RunningLeaderboardResponse(ORMBase):
    entries: List[RunningLeaderboardInfo]
    time_stamp: Optional[str]


# 队伍
class RunningTeamCreateInfo(ORMBase):
    track_id: str
    title: str
    description: str
    team_size: int
    competition_date: datetime
    is_public: bool

class RunningTeamCreateResponse(ORMBase):
    team_code: str
    asset_id: str
    new_balance: int

class RunningAppliedTeamInfo(ORMBase):
    team_id: str
    leader_id: str
    leader_name: str
    leader_avatar_url: str
    title: str
    description: str
    member_count: int
    max_member_size: int
    region_name: str
    event_name: str
    track_name: str
    competition_date: str

class RunningAppliedTeamResponse(ORMBase):
    teams: List[RunningAppliedTeamInfo]

class RunningTeamInfo(ORMBase):
    team_id: str
    leader_id: str
    leader_name: str
    leader_avatar_url: str
    title: str
    member_count: int
    max_member_size: int
    team_code: str
    region_name: str
    event_name: str
    track_name: str
    is_public: bool
    status: TeamStatus
    competition_date: str

class RunningTeamResponse(ORMBase):
    teams: List[RunningTeamInfo]

class RunningTeamMemberInfo(ORMBase):
    member_id: str
    user_id: str
    nick_name: str
    avatar_url: str
    join_date: str
    is_registered: bool
    is_leader: bool

class RunningTeamAppliedMemberInfo(ORMBase):
    member_id: str
    user_id: str
    nick_name: str
    avatar_url: str
    introduction: Optional[str]
    join_date: str

class RunningTeamDetailResponse(ORMBase):
    team_id: str
    title: str
    description: str
    max_member_size: int
    team_code: str
    region_name: str
    event_name: str
    track_name: str
    is_public: bool
    status: TeamStatus
    created_at: str
    competition_date: str
    members: List[RunningTeamMemberInfo]

class RunningTeamManageResponse(ORMBase):
    team_id: str
    title: str
    description: str
    max_member_size: int
    team_code: str
    region_name: str
    event_name: str
    track_name: str
    track_end_date: str
    is_public: bool
    status: TeamStatus
    created_at: str
    competition_date: str
    members: List[RunningTeamMemberInfo]
    request_members: List[RunningTeamAppliedMemberInfo]

class RunningTeamUpdateInfo(ORMBase):
    team_id: str
    title: str
    description: str
    competition_date: datetime

class RunningTeamUpdateResponse(ORMBase):
    title: str
    description: str
    competition_date: str

class RunningTeamStatusUpdateInfo(ORMBase):
    team_id: str
    new_status: bool

class RunningTeamMembersResponse(ORMBase):
    members: List[RunningTeamMemberInfo]

class RunningTeamExpiredResponse(ORMBase):
    expired_date: Optional[str]

class RunningTeamAppliedRequest(ORMBase):
    team_id: str
    introduction: Optional[str] = None