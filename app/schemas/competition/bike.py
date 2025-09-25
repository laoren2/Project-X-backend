from fastapi import Form
from app.schemas.base import ORMBase
from app.schemas.common import PersonInfoResponse, CPAssetBaseInfo
from app.schemas.competition.common import TeamStatus, RecordStatus, CardBonusItem, CardBonusInfo, PathPoint, MemberScoreInfo
from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel


class BikeSeasonCreateForm:
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

class BikeSeasonBaseInfo(ORMBase):
    season_id: str
    name: str
    start_date: str
    end_date: str
    image_url: str

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
    prizePool: int
    score: int

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
        score: int = Form(...)
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
        self.score = score


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
    prizePool: int
    score: int

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
        score: int = Form(...)
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
        self.score = score


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
    prize_pool: str
    score: str
    is_settled: bool


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
    prize_pool: int
    score: int
    totalParticipants: int

class BikeTrackListResponse(ORMBase):
    tracks: List[BikeTrackBaseInfo]

class BikeRankInfo(ORMBase):
    record_id: Optional[str] = None
    rank: Optional[int] = None
    duration_seconds: Optional[float] = None
    reward_voucher_amount: Optional[int] = None
    score: Optional[int] = None

class BikeBeginInfo(ORMBase):
    record_id: str
    start_time: datetime

class BikeFinishInfo(BaseModel):
    record_id: str
    end_time: datetime
    bonus_in_cards: List[CardBonusItem]
    path: List[PathPoint]

class BikeRecordInfo(ORMBase):
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

class BikeRecordResponse(ORMBase):
    records: List[BikeRecordInfo]

class BikeSingleRegisterResponse(ORMBase):
    record: BikeRecordInfo
    asset_id: str
    new_balance: int

class BikeLeaderboardInfo(ORMBase):
    rank: int
    record_id: str
    user_info: PersonInfoResponse
    duration_seconds: float
    voucher: int
    score: int

class BikeLeaderboardResponse(ORMBase):
    entries: List[BikeLeaderboardInfo]
    time_stamp: Optional[str]


# 队伍
class BikeTeamCreateInfo(ORMBase):
    track_id: str
    title: str
    description: str
    team_size: int
    competition_date: datetime
    is_public: bool

class BikeTeamCreateResponse(ORMBase):
    team_code: str
    asset_id: str
    new_balance: int

class BikeAppliedTeamInfo(ORMBase):
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

class BikeAppliedTeamResponse(ORMBase):
    teams: List[BikeAppliedTeamInfo]

class BikeTeamInfo(ORMBase):
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

class BikeTeamResponse(ORMBase):
    teams: List[BikeTeamInfo]

class BikeTeamMemberInfo(ORMBase):
    member_id: str
    user_id: str
    nick_name: str
    avatar_url: str
    join_date: str
    is_registered: bool
    is_leader: bool

class BikeTeamAppliedMemberInfo(ORMBase):
    member_id: str
    user_id: str
    nick_name: str
    avatar_url: str
    introduction: Optional[str]
    join_date: str

class BikeTeamDetailResponse(ORMBase):
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
    members: List[BikeTeamMemberInfo]

class BikeTeamManageResponse(ORMBase):
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
    members: List[BikeTeamMemberInfo]
    request_members: List[BikeTeamAppliedMemberInfo]

class BikeTeamUpdateInfo(ORMBase):
    team_id: str
    title: str
    description: str
    competition_date: datetime

class BikeTeamUpdateResponse(ORMBase):
    title: str
    description: str
    competition_date: str

class BikeTeamStatusUpdateInfo(ORMBase):
    team_id: str
    new_status: bool

class BikeTeamMembersResponse(ORMBase):
    members: List[BikeTeamMemberInfo]

class BikeTeamExpiredResponse(ORMBase):
    expired_date: Optional[str]

class BikeTeamAppliedRequest(ORMBase):
    team_id: str
    introduction: Optional[str] = None

class BikeRecordDetailInfo(BaseModel):
    original_time: float
    final_time: float
    path: List[PathPoint]
    card_bonus: List[CardBonusInfo]
    team_member_scores: List[MemberScoreInfo]

class BikeSummaryRecordInfo(BaseModel):
    record_id: str
    event_name: str
    track_name: str
    city_name: str
    best_time: float
    rank: int
    voucher: int
    score: int

class BikeSummaryRecordResponse(BaseModel):
    records: List[BikeSummaryRecordInfo]

class BikeHistorySeasonInfo(BaseModel):
    season_id: str
    season_name: str

class BikeHistorySeasonResponse(BaseModel):
    seasons: List[BikeHistorySeasonInfo]

class BikeCareerRecordInfo(BaseModel):
    record_id: str
    track_id: str
    track_name: str
    event_name: str
    region: str
    track_score: int
    score: int
    record_date: str

class BikeCareerRecordResponse(BaseModel):
    records: List[BikeCareerRecordInfo]

class BikeScoreLeaderboardInfo(ORMBase):
    rank: int
    user_info: PersonInfoResponse
    score: int

class BikeScoreLeaderboardResponse(ORMBase):
    entries: List[BikeScoreLeaderboardInfo]

class BikeCareerDataInfo(ORMBase):
    total_score: int | None
    total_rank: int | None
    