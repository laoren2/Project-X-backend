from fastapi import Form
from app.schemas.base import ORMBase
from app.schemas.common import PersonInfoResponse, CPAssetBaseInfo
from app.schemas.competition.common import (
    TeamStatus, RecordStatus, CardBonusItem, CardBonusInfo,
    MemberScoreInfo, PathPoint, TeamMagicCardBonusInfo
)
from app.schemas.training.common import RouteType, RouteApplyStatus, TrackLifecycle
from datetime import datetime
from enum import Enum
from typing import List, Optional, Any
from pydantic import BaseModel, Field


class BikeTrackTerrainType(str, Enum):
    road = "road"
    crossCountry = "crossCountry"
    enduro = "enduro"
    downHill = "downHill"
    other = "other"

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
    season_id: str
    region_id: str
    image_url: str | None

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
    name: dict[str, Any]
    description: dict[str, Any]
    start_date: str
    end_date: str
    season_name: str
    region_id: str
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
    event_id: str
    route_type: RouteType
    route_data: str             # JSON 字符串（multipart 表单），service 内 json.loads
    single_registercard_id: str
    team_registercard_id: str
    subRegioName: str
    prizePool: int
    score: int
    terrain_type: BikeTrackTerrainType

    def __init__(
        self,
        name: str = Form(...),
        start_date: datetime = Form(...),
        end_date: datetime = Form(...),
        event_id: str = Form(...),
        route_type: RouteType = Form(...),
        route_data: str = Form(...),
        single_registercard_id: str = Form(...),
        team_registercard_id: str = Form(...),
        subRegioName: str = Form(...),
        prizePool: int = Form(...),
        score: int = Form(...),
        terrain_type: BikeTrackTerrainType = Form(...)
    ):
        self.name = name
        self.start_date = start_date
        self.end_date = end_date
        self.event_id = event_id
        self.route_type = route_type
        self.route_data = route_data
        self.single_registercard_id = single_registercard_id
        self.team_registercard_id = team_registercard_id
        self.subRegioName = subRegioName
        self.prizePool = prizePool
        self.score = score
        self.terrain_type = terrain_type


class BikeTrackUpdateForm:
    track_id: str
    name: str
    start_date: datetime
    end_date: datetime
    route_type: RouteType
    route_data: str             # JSON 字符串（multipart 表单），service 内 json.loads
    subRegioName: str
    prizePool: int
    score: int
    terrain_type: BikeTrackTerrainType

    def __init__(
        self,
        track_id: str = Form(...),
        name: str = Form(...),
        start_date: datetime = Form(...),
        end_date: datetime = Form(...),
        route_type: RouteType = Form(...),
        route_data: str = Form(...),
        subRegioName: str = Form(...),
        prizePool: int = Form(...),
        score: int = Form(...),
        terrain_type: BikeTrackTerrainType = Form(...)
    ):
        self.track_id = track_id
        self.name = name
        self.start_date = start_date
        self.end_date = end_date
        self.route_type = route_type
        self.route_data = route_data
        self.subRegioName = subRegioName
        self.prizePool = prizePool
        self.score = score
        self.terrain_type = terrain_type


class BikeTrackBaseInfoInternal(ORMBase):
    track_id: str
    name: dict[str, Any]
    start_date: str
    end_date: str
    event_name: str
    season_name: str
    region_id: str
    image_url: str | None

    route_type: RouteType
    route_data: dict
    elevation_difference: str
    sub_region_name: dict[str, Any]
    prize_pool: str
    score: str
    distance: str
    terrain_type: BikeTrackTerrainType
    is_settled: bool


class BikeTrackListInternalResponse(ORMBase):
    tracks: List[BikeTrackBaseInfoInternal]

# 热门路线申请转赛道 —— 后台审核列表项
class BikeRouteApplicationInfoInternal(ORMBase):
    application_id: str
    route_id: str
    applicant_user_id: str
    applicant_nickname: str
    title: str
    sub_region_name: str
    language: str
    terrain_type: BikeTrackTerrainType
    lifecycle: TrackLifecycle
    is_premium: bool
    participate_count: int                  # 申请时热度快照
    current_participate_count: int          # 审核时实时热度
    region_id: str
    route_type: RouteType
    route_data: dict
    distance: float
    elevation_difference: int
    status: RouteApplyStatus
    review_note: str | None
    track_id: str | None
    created_at: str
    reviewed_at: str | None

class BikeRouteApplicationListInternalResponse(ORMBase):
    applications: List[BikeRouteApplicationInfoInternal]

class BikeTrackBaseInfo(ORMBase):
    track_id: str
    name: str
    start_date: str
    end_date: str
    image_url: str | None
    single_register_card_url: str
    team_register_card_url: str

    route_type: RouteType
    route_data: dict
    elevation_difference: int
    sub_region_name: str
    prize_pool: int
    score: int
    totalParticipants: int
    participate_count: int              # 报名/比赛记录数（用于热度排序与展示）
    distance_to_user: Optional[float] = None    # 起点到用户的距离（米，distance 排序时返回）
    distance: float
    terrain_type: BikeTrackTerrainType

class BikeTrackListResponse(ORMBase):
    tracks: List[BikeTrackBaseInfo]
    next_cursor: Optional[str] = None

class BikeRankInfo(ORMBase):
    record_id: Optional[str] = None
    rank: Optional[int] = None
    duration_seconds: Optional[float] = None
    reward_voucher_amount: Optional[int] = None
    score: Optional[int] = None

# 批量查询赛道的用户态信息（熟悉度 + 排名），需登录
class BikeTracksUserInfoRequest(BaseModel):
    track_ids: List[str]

class BikeTrackUserInfo(ORMBase):
    track_id: str
    familiarity: float
    rank_info: Optional[BikeRankInfo] = None

class BikeTracksUserInfoResponse(ORMBase):
    infos: List[BikeTrackUserInfo]

class BikeBeginInfo(ORMBase):
    record_id: str
    start_time: datetime

class BikePathPoint(BaseModel):
    """自行车运动路径点"""
    base: PathPoint
    
    power: float | None = None
    pedal_cadence: float | None = None
    estimate_pedal_count: float = 0

    card_bonus: List[CardBonusItem] = Field(default_factory=list)

class BikeFinishInfo(BaseModel):
    record_id: str
    validation_score: float
    end_time: datetime
    bonus_in_cards: List[CardBonusItem]
    team_bonus: TeamMagicCardBonusInfo | None = None      # 每人只允许使用一张组队卡牌
    path: List[BikePathPoint]

class BikeRecordInfo(ORMBase):
    record_id: str
    region_id: str
    event_name: str
    track_name: str
    route_type: RouteType
    route_data: dict
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
    region_id: str
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
    region_id: str
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
    region_id: str
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
    region_id: str
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
    status: RecordStatus
    original_time: float
    final_time: float
    penalty_time: float
    is_finish_computed: bool
    path: List[BikePathPoint]
    card_bonus: List[CardBonusInfo]
    team_member_scores: List[MemberScoreInfo]
    settlements: dict[str, Any] | None      # 记录的结算信息
    familiarity_time: float
    training_state_time: float

class BikeUnverifiedRecordInfo(ORMBase):
    is_vip: bool
    record_id: str
    validation_score: float | None
    path: List[BikePathPoint]
    finished_at: str | None

class BikeUnverifiedRecordResponse(ORMBase):
    records: List[BikeUnverifiedRecordInfo]

class BikeSummaryRecordInfo(BaseModel):
    record_id: str
    event_name: str
    track_name: str
    region_id: str
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
    region_id: str
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
    total_score: int
    total_rank: int | None
    total_voucher: int
    total_distance: float
    total_time: float
    total_xp: int
    