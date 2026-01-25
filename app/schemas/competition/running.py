from fastapi import Form
from app.schemas.base import ORMBase
from app.schemas.common import PersonInfoResponse, CPAssetBaseInfo
from app.schemas.competition.common import(
    TeamStatus, RecordStatus, CardBonusItem, CardBonusInfo, 
    MemberScoreInfo, PathPoint, TeamMagicCardBonusInfo
)
from datetime import datetime
from enum import Enum
from typing import List, Optional, Any
from pydantic import BaseModel


class RunningTrackTerrainType(str, Enum):
    road = "road"
    mountain = "mountain"

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
    season_id: str
    region_id: str
    image_url: str

    def __init__(
        self,
        name: str = Form(...),
        description: str = Form(...),
        start_date: datetime = Form(...),
        end_date: datetime = Form(...),
        season_id: str = Form(...),
        region_id: str = Form(...),
        image_url: str = Form(None)
    ):
        self.name = name
        self.description = description
        self.start_date = start_date
        self.end_date = end_date
        self.season_id = season_id
        self.region_id = region_id
        self.image_url = image_url

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
    name: dict[str, Any]
    description: dict[str, Any]
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
    event_id: str
    from_latitude: float
    from_longitude: float
    from_radius: int
    to_latitude: float
    to_longitude: float
    to_radius: int
    single_registercard_id: str
    team_registercard_id: str
    elevationDifference: int
    subRegioName: str
    prizePool: int
    distance: float
    score: int
    terrain_type: RunningTrackTerrainType

    def __init__(
        self,
        name: str = Form(...),
        start_date: datetime = Form(...),
        end_date: datetime = Form(...),
        event_id: str = Form(...),
        from_latitude: float = Form(...),
        from_longitude: float = Form(...),
        from_radius: int = Form(...),
        to_latitude: float = Form(...),
        to_longitude: float = Form(...),
        to_radius: int = Form(...),
        single_registercard_id: str = Form(...),
        team_registercard_id: str = Form(...),
        elevationDifference: int = Form(...),
        subRegioName: str = Form(...),
        prizePool: int = Form(...),
        distance: float = Form(...),
        score: int = Form(...),
        terrain_type: RunningTrackTerrainType = Form(...)
    ):
        self.name = name
        self.start_date = start_date
        self.end_date = end_date
        self.event_id = event_id
        self.from_latitude = from_latitude
        self.from_longitude = from_longitude
        self.from_radius = from_radius
        self.to_latitude = to_latitude
        self.to_longitude = to_longitude
        self.to_radius = to_radius
        self.single_registercard_id = single_registercard_id
        self.team_registercard_id = team_registercard_id
        self.elevationDifference = elevationDifference
        self.subRegioName = subRegioName
        self.prizePool = prizePool
        self.distance = distance
        self.score = score
        self.terrain_type = terrain_type


class RunningTrackUpdateForm:
    track_id: str
    name: str
    start_date: datetime
    end_date: datetime
    from_latitude: float
    from_longitude: float
    from_radius: int
    to_latitude: float
    to_longitude: float
    to_radius: int
    elevationDifference: int
    subRegioName: str
    prizePool: int
    distance: float
    score: int
    terrain_type: RunningTrackTerrainType

    def __init__(
        self,
        track_id: str = Form(...),
        name: str = Form(...),
        start_date: datetime = Form(...),
        end_date: datetime = Form(...),
        from_latitude: float = Form(...),
        from_longitude: float = Form(...),
        from_radius: int = Form(...),
        to_latitude: float = Form(...),
        to_longitude: float = Form(...),
        to_radius: int = Form(...),
        elevationDifference: int = Form(...),
        subRegioName: str = Form(...),
        prizePool: int = Form(...),
        distance: float = Form(...),
        score: int = Form(...),
        terrain_type: RunningTrackTerrainType = Form(...)
    ):
        self.track_id = track_id
        self.name = name
        self.start_date = start_date
        self.end_date = end_date
        self.from_latitude = from_latitude
        self.from_longitude = from_longitude
        self.from_radius = from_radius
        self.to_latitude = to_latitude
        self.to_longitude = to_longitude
        self.to_radius = to_radius
        self.elevationDifference = elevationDifference
        self.subRegioName = subRegioName
        self.prizePool = prizePool
        self.distance = distance
        self.score = score
        self.terrain_type = terrain_type


class RunningTrackBaseInfoInternal(ORMBase):
    track_id: str
    name: dict[str, Any]
    start_date: str
    end_date: str
    event_name: str
    season_name: str
    region_name: str
    image_url: str

    from_latitude: str
    from_longitude: str
    from_radius: int
    to_latitude: str
    to_longitude: str
    to_radius: int
    elevation_difference: str
    sub_region_name: dict[str, Any]
    prize_pool: str
    distance: str
    score: str
    terrain_type: RunningTrackTerrainType
    is_settled: bool


class RunningTrackListInternalResponse(ORMBase):
    tracks: List[RunningTrackBaseInfoInternal]


class RunningTrackBaseInfo(ORMBase):
    track_id: str
    name: str
    start_date: str
    end_date: str
    image_url: str
    single_register_card_url: str
    team_register_card_url: str

    from_latitude: float
    from_longitude: float
    from_radius: int
    to_latitude: float
    to_longitude: float
    to_radius: int
    elevation_difference: int
    sub_region_name: str
    prize_pool: int
    distance: float
    score: int
    totalParticipants: int
    terrain_type: RunningTrackTerrainType


class RunningTrackListResponse(ORMBase):
    tracks: List[RunningTrackBaseInfo]


class RunningRankInfo(ORMBase):
    record_id: Optional[str] = None
    rank: Optional[int] = None
    duration_seconds: Optional[float] = None
    reward_voucher_amount: Optional[int] = None
    score: Optional[int] = None

class RunningBeginInfo(ORMBase):
    record_id: str
    start_time: datetime

class RunningPathPoint(BaseModel):
    """跑步运动路径点"""
    base: PathPoint
    
    power: float | None = None
    step_cadence: float | None = None
    vertical_amplitude: float | None = None
    touchdown_time: float | None = None
    step_size: float | None = None
    estimate_step_count: float = 0

class RunningFinishInfo(BaseModel):
    record_id: str
    validation_score: float
    end_time: datetime
    bonus_in_cards: List[CardBonusItem]
    team_bonus: TeamMagicCardBonusInfo | None = None      # 每人只允许使用一张组队卡牌
    path: List[RunningPathPoint]

class RunningRecordInfo(ORMBase):
    record_id: str
    region_name: str
    event_name: str
    track_name: str
    track_start_lat: float
    track_start_lng: float
    track_start_radius: int
    track_end_lat: float
    track_end_lng: float
    track_end_radius: int
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
    rank: int
    record_id: str
    user_info: PersonInfoResponse
    duration_seconds: float
    voucher: int
    score: int

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

class RunningRecordDetailInfo(BaseModel):
    status: RecordStatus
    original_time: float
    final_time: float
    is_finish_computed: bool
    path: List[RunningPathPoint]
    card_bonus: List[CardBonusInfo]
    team_member_scores: List[MemberScoreInfo]

class RunningUnverifiedRecordInfo(ORMBase):
    is_vip: bool
    record_id: str
    validation_score: float | None
    path: List[RunningPathPoint]
    finished_at: str | None

class RunningUnverifiedRecordResponse(ORMBase):
    records: List[RunningUnverifiedRecordInfo]

class RunningSummaryRecordInfo(BaseModel):
    record_id: str
    event_name: str
    track_name: str
    city_name: str
    best_time: float
    rank: int
    voucher: int
    score: int

class RunningSummaryRecordResponse(BaseModel):
    records: List[RunningSummaryRecordInfo]

class RunningHistorySeasonInfo(BaseModel):
    season_id: str
    season_name: str

class RunningHistorySeasonResponse(BaseModel):
    seasons: List[RunningHistorySeasonInfo]

class RunningCareerRecordInfo(BaseModel):
    record_id: str
    track_id: str
    track_name: str
    event_name: str
    region: str
    track_score: int
    score: int
    record_date: str

class RunningCareerRecordResponse(BaseModel):
    records: List[RunningCareerRecordInfo]

class RunningScoreLeaderboardInfo(ORMBase):
    rank: int
    user_info: PersonInfoResponse
    score: int

class RunningScoreLeaderboardResponse(ORMBase):
    entries: List[RunningScoreLeaderboardInfo]

class RunningCareerDataInfo(ORMBase):
    total_score: int
    total_rank: int | None
    total_voucher: int
    total_distance: float
    total_time: float