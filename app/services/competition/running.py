from app.crud.competition.common import get_region_by_region_id, get_region_by_id
from app.crud.competition.running import (
    get_event_by_event_id, get_event_by_name, get_event_by_season_id_and_region_id,
    get_track_by_name, get_track_by_track_id, get_track_by_event_id, get_tracks_by_event_page_crud,
    get_tracks_by_track_ids,
    create_event_crud, create_track_crud, update_event_crud, update_track_crud,
    query_events_crud, query_tracks_crud, get_track_by_track_id_for_update,
    create_record_crud, get_record_by_record_id, update_record_crud,
    create_season_crud, get_season_by_season_id, update_season_crud,
    get_season_now, get_season_by_name, get_active_events_by_season_id, get_community_event,
    delete_record_crud, create_team_crud, get_active_team_by_code_for_update,
    get_created_teams_by_user_id, get_applied_teams_by_user_id, get_joined_teams_by_user_id,
    get_team_by_team_id, create_team_member_crud, update_team_crud, delete_records_by_team_id,
    get_team_by_id_for_update, get_team_by_team_id_for_update, get_record_by_team_id_and_user_id,
    get_public_teams_by_track_id, get_records_by_team_id_for_update, get_records_by_team_id,
    track_has_settled, get_history_seasons, get_leaderboad_record, get_leaderboad_records_in_page,
    get_scores_in_page, add_or_update_career_score, get_score_and_rank_by_season_id_and_user,
    get_incompleted_records_by_user_id, get_completed_records_by_user_id, get_career_statistic_data,
    add_or_update_career_statistic_data, get_daily_task, get_today_task_record_by_user,
    add_or_update_daily_task_record, get_unverified_records, get_bonus_record_with_team_magic_card_for_update,
    get_team_id_by_record_id, get_season_by_date, get_bonus_record_with_team_magic_card_by_team_user,
    get_user_best_race_profile
)
from app.crud.training.running import (
    get_familiarity_by_track_and_user, get_training_state_by_user,
    get_application_by_application_id, query_applications_by_status_crud, count_route_training_records
)
from app.crud.asset_manage import (
    consume_cpasset, get_register_card_price, get_cpasset_def_by_asset_id,
    reward_cpasset, get_team_card_def, get_equip_card_by_card_id, get_cpasset_def_by_id,
    reward_ccasset, get_registration_card_def
)
from app.crud.user import get_user_by_id, get_users_by_ids, get_users_by_user_ids, get_exist_user_by_id
from app.core.errors import ErrorCode
from app.core.tools import get_user_local_date, encode_cursor, decode_cursor
from app.core.storage import build_resource_url
from app.schemas.base import BizException, Language, pick_i18n_text
from app.schemas.common import PersonInfoResponse, EquipCardBaseInfo, SportType, CCAssetType, CCAssetRewardResponse, PaceBaselineResponse, PaceSnapshotResponse, SplitProfileInfo
from app.schemas.mailbox import MailType
from app.schemas.user import Gender
from app.schemas.asset import CPAssetResponse, DailyTaskRewardResponse, AssetOperation
from app.schemas.competition.common import (
    TeamRelationship, TeamStatus, RecordStatus, MatchFinishInfo,
    CardBonusInfo, MemberScoreInfo, DailyTaskResponse, TeamMagicCardBonusInfo, MatchFinishResponse, EventType
)
from app.schemas.competition.running import (
    RunningEventCreateForm, RunningEventBaseInfo, RunningEventUpdateForm, RunningEventBaseInfoInternal,
    RunningTrackBaseInfo, RunningTrackCreateForm, RunningTrackListResponse, RunningTrackUserInfo,
    RunningTrackUpdateForm, RunningTrackBaseInfoInternal,
    RunningBeginInfo, RunningFinishInfo, RunningLeaderboardInfo, RunningLeaderboardResponse,
    RunningSeasonBaseInfo, RunningSeasonCreateForm, RunningRecordInfo, RunningSingleRegisterResponse, RunningRankInfo,
    RunningTeamCreateInfo, RunningTeamCreateResponse, RunningAppliedTeamInfo, RunningAppliedTeamResponse,
    RunningTeamInfo, RunningTeamResponse, RunningTeamDetailResponse, RunningTeamManageResponse, RunningTeamMemberInfo,
    RunningTeamAppliedMemberInfo, RunningTeamUpdateResponse, RunningTeamUpdateInfo,
    RunningTeamStatusUpdateInfo, RunningTeamMembersResponse, RunningTeamAppliedRequest, RunningTeamExpiredResponse,
    RunningRecordDetailInfo, RunningSummaryRecordResponse, RunningSummaryRecordInfo, RunningHistorySeasonResponse, RunningHistorySeasonInfo,
    RunningCareerRecordResponse, RunningCareerRecordInfo, RunningScoreLeaderboardInfo, RunningScoreLeaderboardResponse,
    RunningCareerDataInfo, RunningPathPoint, RunningUnverifiedRecordInfo, RunningUnverifiedRecordResponse,
    RunningRouteApplicationInfoInternal, RunningRouteApplicationListInternalResponse
)
from app.schemas.training.common import RouteApplyStatus, TrackLifecycle
from app.db.models.competition import (
    RunningEvent, RunningTrack, RunningSeason, RunningRaceRecord, RunningTeam, 
    RunningTeamMember, RunningTeamAppliedMember, RunningRacePath, CardBonusInRunningRecord,
    RunningLeaderboard, RunningBonusByTeamMember, VideoWatermarkPaceSnapshot
)
from app.db.models.mailbox import Mailbox
from app.db.models.user import User
from app.services.mappers import equip_card_to_base_info
from app.services.weather import fetch_weather_snapshot, weather_snapshot_from_record
from app.services.training.common import validate_route_data, build_geometry, extract_path_points, extract_checkpoints_from_route_data, build_route_checkpoint_events, build_split_profile
from app.services.common import get_elevation
from app.schemas.training.common import RouteSortType
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from app.services.competition.common import (
    _distribute_voucher_and_scores, compute_distance, update_running_leaderboard_for_record,
    send_running_match_rewards, compute_running_match_rewards, settle_running_match_xp, get_track_leaderboard_times
)
from app.services.competition.record_privacy import ensure_record_detail_visible
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import redis_client
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import uuid, json, logging, random


logger = logging.getLogger(__name__)


async def create_season_service(db: AsyncSession, season_create: RunningSeasonCreateForm, image_url: str) -> str:
    season = await get_season_by_date(db, season_create.start_date, season_create.end_date)
    if season is not None:
        raise BizException(code=ErrorCode.SEASON_ERROR, message="season.data_error")
    season_id = f"season_{str(uuid.uuid4())[:8]}"
    try:
        name_i18n = json.loads(season_create.name)
    except:
        raise BizException(code=ErrorCode.JSON_DECODE_ERROR, message=f"JSON格式错误")
    new_season = RunningSeason(
        season_id=season_id,
        name_i18n=name_i18n,
        start_date=season_create.start_date,
        end_date=season_create.end_date,
        image_url=image_url
    )
    res = await create_season_crud(db, new_season)
    await db.commit()
    return res.season_id


async def update_season_image_url(db: AsyncSession, season_id: str, image_url: str):
    existing_season = await get_season_by_season_id(db, season_id)
    if existing_season is None:
        raise BizException(code=ErrorCode.SEASON_ERROR, message="season.not_found")
    update_data = {
        "image_url": image_url
    }
    await update_season_crud(db, existing_season, update_data)
    await db.commit()


async def query_current_season_service(db: AsyncSession, lang: Language) -> RunningSeasonBaseInfo:
    season = await get_season_now(db)
    if not season:
        raise BizException(code=ErrorCode.SEASON_ERROR, message="season.out_of_season")
    return RunningSeasonBaseInfo(
        season_id=season.season_id,
        name=pick_i18n_text(season.name_i18n, lang),
        start_date=season.start_date.isoformat(),
        end_date=season.end_date.isoformat(),
        image_url=build_resource_url(season.image_url)
    )

async def get_history_seasons_service(db: AsyncSession, lang: Language) -> RunningHistorySeasonResponse:
    seasons = await get_history_seasons(db)
    response = []
    for season in seasons:
        response.append(RunningHistorySeasonInfo(
            season_id=season.season_id,
            season_name=pick_i18n_text(season.name_i18n, lang)
        ))
    return RunningHistorySeasonResponse(seasons=response)

async def create_event_service(db: AsyncSession, event_form: RunningEventCreateForm, image_url: str) -> str:
    region = await get_region_by_region_id(db, event_form.region_id)
    if region is None:
        raise BizException(code=ErrorCode.REGION_ERROR, message="region.not_found")

    season = await get_season_by_season_id(db, event_form.season_id)
    if season is None:
        raise BizException(code=ErrorCode.SEASON_ERROR, message="season.not_found")
    if event_form.start_date < season.start_date or event_form.end_date > season.end_date or event_form.start_date > event_form.end_date:
        raise BizException(code=ErrorCode.EVENT_EEROR, message="赛事时间非法")

    try:
        name_i18n = json.loads(event_form.name)
        description_i18n = json.loads(event_form.description)
    except:
        raise BizException(code=ErrorCode.JSON_DECODE_ERROR, message=f"JSON格式错误")

    event_id = f"event_{str(uuid.uuid4())[-12:]}"
    new_event = RunningEvent(
        event_id=event_id,
        name_i18n=name_i18n,
        description_i18n=description_i18n,
        start_date=event_form.start_date,
        end_date=event_form.end_date,
        region_id=region.id,
        season_id=season.id,
        image_url=image_url
    )
    res = await create_event_crud(db, new_event)
    await db.commit()
    return res.event_id


async def update_event_service(db: AsyncSession, event: RunningEventUpdateForm, image_url: str):
    existing_event = await get_event_by_event_id(db, event.event_id)
    if existing_event is None:
        raise BizException(code=ErrorCode.EVENT_ERROR, message="event.not_found")
    if event.start_date < existing_event.season.start_date or event.end_date > existing_event.season.end_date or event.start_date > event.end_date:
        raise BizException(code=ErrorCode.EVENT_ERROR, message="event.invalid_time")
    try:
        name_i18n = json.loads(event.name)
        description_i18n = json.loads(event.description)
    except:
        raise BizException(code=ErrorCode.JSON_DECODE_ERROR, message=f"JSON格式错误")
    update_data = {
        "name_i18n": name_i18n,
        "description_i18n": description_i18n,
        "start_date": event.start_date,
        "end_date": event.end_date,
        "image_url": image_url
    }
    await update_event_crud(db, existing_event, update_data)
    await db.commit()


async def update_event_image_url(db: AsyncSession, event_id: str, image_url: str):
    existing_event = await get_event_by_event_id(db, event_id)
    if existing_event is None:
        raise BizException(code=ErrorCode.EVENT_ERROR, message="event.not_found")
    update_data = {
        "image_url": image_url
    }
    await update_event_crud(db, existing_event, update_data)
    await db.commit()


async def query_events_service(
    db: AsyncSession,
    season_name: Optional[str],
    region_name: Optional[str],
    event_name: Optional[str],
    page: int,
    size: int
) -> List[RunningEventBaseInfoInternal]:
    events = await query_events_crud(
        db=db,
        season_name=season_name,
        region_name=region_name,
        event_name=event_name,
        page=page,
        size=size
    )
    return [RunningEventBaseInfoInternal(
        event_id=e.event_id,
        name=e.name_i18n,
        description=e.description_i18n,
        start_date=e.start_date.isoformat(),
        end_date=e.end_date.isoformat(),
        season_name=e.season.name_i18n["zh-Hans"] if e.season is not None else "未知",
        region_id=e.region.region_id if e.region is not None else "未知",
        image_url=build_resource_url(e.image_url)
    ) for e in events]


async def query_events_by_region(db: AsyncSession, lang: Language, region_id: str) -> List[RunningEventBaseInfo]:
    season = await get_season_now(db)
    if not season:
        raise BizException(code=ErrorCode.SEASON_ERROR, message="season.out_of_season")
    
    region = await get_region_by_region_id(db, region_id)
    if region is None:
        raise BizException(code=ErrorCode.REGION_ERROR, message="region.not_found")
    
    events = await get_event_by_season_id_and_region_id(db, season_id=season.id, region_id=region.id)
    if not events:
        raise BizException(code=ErrorCode.REGION_ERROR, message="region.no_events")
    return [RunningEventBaseInfo(
        event_id=e.event_id,
        name=pick_i18n_text(e.name_i18n, lang),
        description=pick_i18n_text(e.description_i18n, lang),
        start_date=e.start_date.isoformat(),
        end_date=e.end_date.isoformat(),
        image_url=build_resource_url(e.image_url)
    ) for e in events]


async def query_event_detail_service(db: AsyncSession, lang: Language, event_id: str) -> RunningEventBaseInfo:
    event = await get_event_by_event_id(db, event_id)
    if not event:
        raise BizException(code=ErrorCode.EVENT_ERROR, message="event.not_found")
    return RunningEventBaseInfo(
        event_id=event.event_id,
        name=pick_i18n_text(event.name_i18n, lang),
        description=pick_i18n_text(event.description_i18n, lang),
        start_date=event.start_date.isoformat(),
        end_date=event.end_date.isoformat(),
        image_url=build_resource_url(event.image_url)
    )


async def create_track_service(db: AsyncSession, track_form: RunningTrackCreateForm, image_url: str) -> str:
    event = await get_event_by_event_id(db, track_form.event_id)
    if event is None:
        raise BizException(code=ErrorCode.EVENT_ERROR, message="event.not_found")
    if track_form.start_date < event.start_date or track_form.end_date > event.end_date or track_form.start_date > track_form.end_date:
        raise BizException(code=ErrorCode.TRACK_ERROR, message="track.invalid_time")

    single_card = await get_cpasset_def_by_asset_id(db, track_form.single_registercard_id)
    team_card = await get_cpasset_def_by_asset_id(db, track_form.team_registercard_id)
    if single_card is None or team_card is None:
        raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.not_found")

    try:
        name_i18n = json.loads(track_form.name)
        sub_region_i18n = json.loads(track_form.subRegioName)
        route_data = json.loads(track_form.route_data)
    except:
        raise BizException(code=ErrorCode.JSON_DECODE_ERROR, message=f"JSON格式错误")

    # 校验并构建路线几何 / 海拔差 / 距离（与 training route 同构）
    steps = validate_route_data(track_form.route_type, route_data)
    geometry = build_geometry(steps)
    start = steps[0]
    end = steps[-1]
    elevation_start = get_elevation(start.lat, start.lng)
    elevation_end = get_elevation(end.lat, end.lng)
    if elevation_start is None or elevation_end is None:
        raise BizException(code=ErrorCode.TRACK_ERROR, message="track.data_error")
    total_distance = compute_distance(extract_path_points(steps))

    track_id = f"track_{str(uuid.uuid4())[-12:]}"
    new_track = RunningTrack(
        track_id = track_id,
        name_i18n = name_i18n,
        start_date = track_form.start_date,
        end_date = track_form.end_date,
        event_id = event.id,
        route_type = track_form.route_type,
        route_data = route_data,
        route_geometry = from_shape(geometry, srid=4326),
        start_point = from_shape(Point(start.lng, start.lat), srid=4326),
        end_point = from_shape(Point(end.lng, end.lat), srid=4326),
        single_register_card_id = single_card.id,
        team_register_card_id = team_card.id,
        elevation_difference = elevation_end - elevation_start,
        sub_region_name_i18n = sub_region_i18n,
        prize_pool = track_form.prizePool,
        score = track_form.score,
        distance = total_distance,
        terrain_type = track_form.terrain_type,
        image_url = image_url
    )
    res = await create_track_crud(db, new_track)
    await db.commit()
    return res.track_id


# ---- 热门路线申请转赛道：后台审核 ----

def _compute_track_rewards(distance_m: float, elevation_diff: int, is_premium: bool) -> tuple[int, int]:
    """根据路线长度(米)与海拔差(米)估算赛道奖池与积分。prize_pool∈[1000,3000], score∈[100,500]。"""
    d_km = (distance_m or 0) / 1000.0
    elev = abs(elevation_diff or 0)
    difficulty = min(1.0, (d_km / 30.0) * 0.6 + (elev / 1000.0) * 0.4)
    score = int(100 + difficulty * 400)
    prize_pool = int(1000 + difficulty * 2000)
    if is_premium:
        score = int(score * 1.2)
        prize_pool = int(prize_pool * 1.2)
    score = max(100, min(500, score))
    prize_pool = max(1000, min(3000, prize_pool))
    return prize_pool, score


def _build_application_info(application, current_count: int) -> RunningRouteApplicationInfoInternal:
    route = application.route
    return RunningRouteApplicationInfoInternal(
        application_id=application.application_id,
        route_id=route.route_id if route else "",
        applicant_user_id=application.user.user_id if application.user else "",
        applicant_nickname=application.user.nickname if application.user else "",
        title=application.title,
        sub_region_name=application.sub_region_name,
        language=application.language,
        terrain_type=application.terrain_type,
        lifecycle=application.lifecycle,
        is_premium=application.is_premium,
        participate_count=application.participate_count,
        current_participate_count=current_count,
        region_id=route.region.region_id if route and route.region else str(application.region_id),
        route_type=route.route_type if route else None,
        route_data=route.route_data if route else {},
        distance=route.total_distance if route else 0,
        elevation_difference=route.elevation_difference if route else 0,
        status=application.status,
        review_note=application.review_note,
        track_id=application.track_id,
        created_at=application.created_at.isoformat(),
        reviewed_at=application.reviewed_at.isoformat() if application.reviewed_at else None
    )


async def query_route_applications_service(
    db: AsyncSession,
    status: RouteApplyStatus | None,
    page: int,
    size: int
) -> RunningRouteApplicationListInternalResponse:
    applications = await query_applications_by_status_crud(db, status, page, size)
    infos = []
    for application in applications:
        current_count = await count_route_training_records(db, application.route_id)
        infos.append(_build_application_info(application, current_count))
    return RunningRouteApplicationListInternalResponse(applications=infos)


def _resolve_track_end_date(lifecycle: TrackLifecycle, start: datetime, event_end: datetime) -> datetime:
    if lifecycle == TrackLifecycle.oneMonth:
        end = start + timedelta(days=30)
    elif lifecycle == TrackLifecycle.twoMonth:
        end = start + timedelta(days=60)
    else:
        end = event_end
    return min(end, event_end)


async def review_route_application_service(
    db: AsyncSession,
    application_id: str,
    approve: bool,
    review_note: str | None
):
    async with db.begin():
        application = await get_application_by_application_id(db, application_id)
        if application is None:
            raise BizException(code=ErrorCode.ROUTE_APPLY_ERROR, message="route.apply_not_found")
        if application.status != RouteApplyStatus.pending:
            raise BizException(code=ErrorCode.ROUTE_APPLY_ERROR, message="route.apply_handled")
        route = application.route
        if route is None:
            raise BizException(code=ErrorCode.ROUTE_NOT_FOUND, message="route.not_found")

        now = datetime.now(timezone.utc)

        if not approve:
            application.status = RouteApplyStatus.rejected
            application.review_note = review_note
            application.reviewed_at = now
            route.apply_status = RouteApplyStatus.rejected
            db.add(application)
            db.add(route)
            _send_application_mail(db, application, approved=False, track_title=application.title, review_note=review_note)
            return

        season = await get_season_now(db)
        if season is None:
            raise BizException(code=ErrorCode.SEASON_ERROR, message="season.out_of_season")

        event = await get_community_event(db, season.id, application.region_id)
        if event is None:
            region = await get_region_by_id(db, application.region_id)
            if region is None:
                raise BizException(code=ErrorCode.REGION_ERROR, message="region.not_found")
            event = RunningEvent(
                event_id=f"event_{uuid.uuid4()}",
                name_i18n={"en": "Community Arena", "zh-Hans": "社区竞技场", "zh-Hant": "社區競技場", "ko": "커뮤니티 아레나", "ja": "コミュニティアリーナ", "fr": "Arène communautaire"},
                description_i18n={
                    "en": "Welcome to the Community Arena! Every track here grew from the community's most-loved training routes, shaped by your passion and sweat. Challenge yourself, chase new records, and meet fellow runners along the way. Above all, have fun out there!",
                    "zh-Hans": "欢迎来到社区竞技场！这里的每一条赛道都源自社区中最受欢迎的训练路线，凝聚着大家的汗水与热爱。在这里挑战自我、刷新纪录、结识同好，愿你尽情奔跑，玩得开心！",
                    "zh-Hant": "歡迎來到社區競技場！這裡的每一條賽道都源自社區中最受歡迎的訓練路線，凝聚著大家的汗水與熱愛。在這裡挑戰自我、刷新紀錄、結識同好，願你盡情奔跑，玩得開心！",
                    "ko": "커뮤니티 아레나에 오신 것을 환영합니다! 이곳의 모든 트랙은 커뮤니티에서 가장 사랑받은 훈련 경로에서 탄생했으며, 여러분의 땀과 열정이 담겨 있습니다. 자신에게 도전하고 기록을 경신하며 동료들을 만나 보세요. 무엇보다 마음껏 즐기시길 바랍니다!",
                    "ja": "コミュニティアリーナへようこそ！ここにあるすべてのトラックは、コミュニティで最も愛されたトレーニングルートから生まれ、皆さんの汗と情熱が詰まっています。自分に挑戦し、記録を更新し、仲間と出会いましょう。何よりも、思いきり楽しんでください！",
                    "fr": "Bienvenue dans l'Arène communautaire ! Chaque parcours ici est né des itinéraires d'entraînement préférés de la communauté, façonné par votre passion et votre sueur. Défiez-vous, battez des records et rencontrez d'autres coureurs en chemin. Et surtout, amusez-vous bien !"
                },
                start_date=season.start_date,
                end_date=season.end_date,
                region_id=application.region_id,
                season_id=season.id,
                event_type=EventType.community,
                image_url=f"/resources/competition/official_event/city_tour/cover_{region.country_code.lower()}.png"
            )
            event = await create_event_crud(db, event)

        single_card = await get_registration_card_def(db, SportType.running, is_team=False, premium=application.is_premium)
        team_card = await get_registration_card_def(db, SportType.running, is_team=True, premium=application.is_premium)

        start_date = now
        end_date = _resolve_track_end_date(application.lifecycle, start_date, event.end_date)
        prize_pool, score = _compute_track_rewards(route.total_distance, route.elevation_difference, application.is_premium)

        track_id = f"track_{str(uuid.uuid4())[-12:]}"
        new_track = RunningTrack(
            track_id=track_id,
            name_i18n={application.language: application.title},
            start_date=start_date,
            end_date=end_date,
            event_id=event.id,
            route_type=route.route_type,
            route_data=route.route_data,
            route_geometry=route.route_geometry,
            start_point=route.start_point,
            end_point=route.end_point,
            single_register_card_id=single_card.id,
            team_register_card_id=team_card.id,
            elevation_difference=route.elevation_difference,
            sub_region_name_i18n={application.language: application.sub_region_name},
            prize_pool=prize_pool,
            score=score,
            distance=route.total_distance,
            terrain_type=application.terrain_type,
            image_url=None
        )
        await create_track_crud(db, new_track)

        application.status = RouteApplyStatus.approved
        application.review_note = review_note
        application.track_id = track_id
        application.reviewed_at = now
        route.apply_status = RouteApplyStatus.approved
        db.add(application)
        db.add(route)
        _send_application_mail(db, application, approved=True, track_title=application.title, review_note=None)


def _send_application_mail(db: AsyncSession, application, approved: bool, track_title: str, review_note: str | None):
    if approved:
        title_i18n = {
            "en": "Your route has been approved",
            "zh-Hans": "你的路线已通过审核",
            "zh-Hant": "你的路線已通過審核",
            "ko": "경로가 승인되었습니다",
            "ja": "ルートが承認されました",
            "fr": "Votre itinéraire a été approuvé"
        }
        content_i18n = {
            "en": f"Congratulations! Your route \"{track_title}\" has been approved and is now a race track. Go check it out!",
            "zh-Hans": f"恭喜！你的路线「{track_title}」已通过审核并成为正式赛道，快去看看吧！",
            "zh-Hant": f"恭喜！你的路線「{track_title}」已通過審核並成為正式賽道，快去看看吧！",
            "ko": f"축하합니다! 경로 \"{track_title}\"이(가) 승인되어 정식 트랙이 되었습니다. 확인해 보세요!",
            "ja": f"おめでとうございます！ルート「{track_title}」が承認され、正式なトラックになりました。ぜひご確認ください！",
            "fr": f"Félicitations ! Votre itinéraire « {track_title} » a été approuvé et est désormais un parcours de course. Allez y jeter un œil !"
        }
    else:
        reason_suffix = {
            "en": f" Reason: {review_note}" if review_note else "",
            "zh-Hans": f" 原因：{review_note}" if review_note else "",
            "zh-Hant": f" 原因：{review_note}" if review_note else "",
            "ko": f" 사유: {review_note}" if review_note else "",
            "ja": f" 理由：{review_note}" if review_note else "",
            "fr": f" Raison : {review_note}" if review_note else ""
        }
        title_i18n = {
            "en": "Your route application was not approved",
            "zh-Hans": "你的路线申请未通过",
            "zh-Hant": "你的路線申請未通過",
            "ko": "경로 신청이 승인되지 않았습니다",
            "ja": "ルート申請が承認されませんでした",
            "fr": "Votre demande d'itinéraire n'a pas été approuvée"
        }
        content_i18n = {
            "en": f"Sorry, your route \"{track_title}\" application was not approved.{reason_suffix['en']} You can improve it and apply again.",
            "zh-Hans": f"很抱歉，你的路线「{track_title}」申请未通过。{reason_suffix['zh-Hans']} 你可以改进后重新申请。",
            "zh-Hant": f"很抱歉，你的路線「{track_title}」申請未通過。{reason_suffix['zh-Hant']} 你可以改進後重新申請。",
            "ko": f"죄송합니다. 경로 \"{track_title}\" 신청이 승인되지 않았습니다.{reason_suffix['ko']} 개선 후 다시 신청할 수 있습니다.",
            "ja": f"申し訳ありません。ルート「{track_title}」の申請は承認されませんでした。{reason_suffix['ja']} 改善して再度申請できます。",
            "fr": f"Désolé, votre demande pour l'itinéraire « {track_title} » n'a pas été approuvée.{reason_suffix['fr']} Vous pouvez l'améliorer et postuler à nouveau."
        }
    db.add(Mailbox(
        mail_id=f"mail_{uuid.uuid4()}",
        user_id=application.user_id,
        mail_type=MailType.NOTIFICATION,
        title_i18n=title_i18n,
        content_i18n=content_i18n,
        attachment=None,
        is_received=True,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30)
    ))


async def update_track_service(db: AsyncSession, track: RunningTrackUpdateForm, image_url: str):
    existing_track = await get_track_by_track_id(db, track.track_id)
    if existing_track is None:
        raise BizException(code=ErrorCode.TRACK_ERROR, message="track.not_found")
    if track.start_date < existing_track.event.start_date or track.end_date > existing_track.event.end_date or track.start_date > track.end_date:
        raise BizException(code=ErrorCode.TRACK_ERROR, message="track.invalid_time")
    try:
        name_i18n = json.loads(track.name)
        sub_region_i18n = json.loads(track.subRegioName)
        route_data = json.loads(track.route_data)
    except:
        raise BizException(code=ErrorCode.JSON_DECODE_ERROR, message=f"JSON格式错误")

    steps = validate_route_data(track.route_type, route_data)
    geometry = build_geometry(steps)
    start = steps[0]
    end = steps[-1]
    elevation_start = get_elevation(start.lat, start.lng)
    elevation_end = get_elevation(end.lat, end.lng)
    if elevation_start is None or elevation_end is None:
        raise BizException(code=ErrorCode.TRACK_ERROR, message="track.data_error")
    total_distance = compute_distance(extract_path_points(steps))

    update_data = {
        "name_i18n": name_i18n,
        "start_date": track.start_date,
        "end_date": track.end_date,
        "route_type": track.route_type,
        "route_data": route_data,
        "route_geometry": from_shape(geometry, srid=4326),
        "start_point": from_shape(Point(start.lng, start.lat), srid=4326),
        "end_point": from_shape(Point(end.lng, end.lat), srid=4326),
        "elevation_difference": elevation_end - elevation_start,
        "sub_region_name_i18n": sub_region_i18n,
        "prize_pool": track.prizePool,
        "score": track.score,
        "distance": total_distance,
        "terrain_type": track.terrain_type,
        "image_url": image_url
    }
    await update_track_crud(db, existing_track, update_data)
    await db.commit()


async def update_track_image_url(db: AsyncSession, track_id: str, image_url: str):
    existing_track = await get_track_by_track_id(db, track_id)
    if existing_track is None:
        raise BizException(code=ErrorCode.TRACK_ERROR, message="track.not_found")
    update_data = {
        "image_url": image_url
    }
    await update_track_crud(db, existing_track, update_data)
    await db.commit()


async def query_tracks_service(
    db: AsyncSession,
    track_name: Optional[str],
    event_name: Optional[str],
    season_name: Optional[str],
    region_name: Optional[str],
    page: int,
    size: int
) -> List[RunningTrackBaseInfoInternal]:
    tracks = await query_tracks_crud(
        db=db,
        track_name=track_name,
        event_name=event_name,
        season_name=season_name,
        region_name=region_name,
        page=page,
        size=size
    )
    return [RunningTrackBaseInfoInternal(
        track_id=t.track_id,
        name=t.name_i18n,
        start_date=t.start_date.isoformat(),
        end_date=t.end_date.isoformat(),
        event_name=t.event.name_i18n["zh-Hans"] if t.event else "未知",
        season_name=t.event.season.name_i18n["zh-Hans"] if t.event and t.event.season else "未知",
        region_id=t.event.region.region_id if t.event and t.event.region else "未知",
        image_url=build_resource_url(t.image_url) if t.image_url else None,
        route_type=t.route_type,
        route_data=t.route_data,
        elevation_difference=str(t.elevation_difference),
        sub_region_name=t.sub_region_name_i18n,
        prize_pool=str(t.prize_pool),
        distance=str(t.distance),
        score=str(t.score),
        terrain_type=t.terrain_type,
        is_settled=is_settled
    ) for t, is_settled in tracks]


async def query_tracks_by_event(
    db: AsyncSession,
    lang: Language,
    event_id: str,
    sort_type: RouteSortType,
    lat: float | None,
    lng: float | None,
    cursor: str | None,
    limit: int
) -> RunningTrackListResponse:
    event = await get_event_by_event_id(db, event_id)
    if event is None:
        raise BizException(code=ErrorCode.EVENT_ERROR, message="event.not_found")

    cursor_data = None
    if cursor:
        try:
            cursor_data = decode_cursor(cursor)
            if "created_at" in cursor_data:
                cursor_data["created_at"] = datetime.fromisoformat(cursor_data["created_at"])
            if "track_id" in cursor_data:
                cursor_data["track_id"] = uuid.UUID(cursor_data["track_id"])
        except:
            raise BizException(code=ErrorCode.JSON_DECODE_ERROR, message="cursor解析错误")

    rows = await get_tracks_by_event_page_crud(db, event.id, sort_type, lat, lng, limit, cursor_data)
    results = []
    next_cursor = None
    for row in rows:
        t = row["RunningTrack"]
        count = row.get("count") or 0
        distance_to_user = row.get("user_distance")

        # 游标按行更新（即便该 track 因缺报名卡被跳过，也要推进游标，保证分页连续）
        if sort_type == RouteSortType.participation:
            next_cursor = {"count": count, "created_at": t.created_at.isoformat(), "track_id": str(t.id)}
        else:
            next_cursor = {"distance": float(distance_to_user), "track_id": str(t.id), "lat": lat, "lng": lng}

        if not t.single_register_card_def or not t.team_register_card_def:
            continue

        male_count = await redis_client.zcard(f"leaderboard:running:{t.track_id}:male")
        female_count = await redis_client.zcard(f"leaderboard:running:{t.track_id}:female")

        results.append(RunningTrackBaseInfo(
            track_id=t.track_id,
            name=pick_i18n_text(t.name_i18n, lang),
            start_date=t.start_date.isoformat(),
            end_date=t.end_date.isoformat(),
            image_url=build_resource_url(t.image_url) if t.image_url else None,
            single_register_card_url=build_resource_url(t.single_register_card_def.image_url),
            team_register_card_url=build_resource_url(t.team_register_card_def.image_url),
            route_type=t.route_type,
            route_data=t.route_data,
            elevation_difference=t.elevation_difference,
            sub_region_name=pick_i18n_text(t.sub_region_name_i18n, lang),
            prize_pool=t.prize_pool,
            distance=t.distance,
            score=t.score,
            totalParticipants=male_count + female_count,
            participate_count=count,
            distance_to_user=float(distance_to_user) if distance_to_user is not None else None,
            terrain_type=t.terrain_type
        ))

    encoded_cursor = encode_cursor(next_cursor) if (len(rows) == limit and next_cursor) else None
    return RunningTrackListResponse(tracks=results, next_cursor=encoded_cursor)


async def single_register_service(db: AsyncSession, lang: Language, track_id: str, user_id: str) -> RunningSingleRegisterResponse:
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
        track = await get_track_by_track_id(db, track_id)
        if track is None:
            raise BizException(code=ErrorCode.TRACK_ERROR, message="track.not_found")
        if track.start_date > datetime.now(timezone.utc):
            raise BizException(code=ErrorCode.TRACK_ERROR, message="track.not_started")
        if track.end_date < datetime.now(timezone.utc):
            raise BizException(code=ErrorCode.TRACK_ERROR, message="track.is_finished")
        if track.single_register_card_def is None:
            raise BizException(code=ErrorCode.TRACK_ERROR, message="track.data_error")
        # 消费报名卡
        new_balance = await consume_cpasset(db, user.id, track.single_register_card_id, 1, "自行车赛事报名")
        # 创建record
        record_id = f"record_{uuid.uuid4()}"
        new_record = RunningRaceRecord (
            record_id = record_id,
            user_id = user.id,
            track_id = track.id,
            route_data = track.route_data        # 报名时快照赛道路线
        )
        record = await create_record_crud(db, new_record)
        record_info = RunningRecordInfo(
            record_id=record.record_id,
            region_id=record.track.event.region.region_id if record.track and record.track.event and record.track.event.region else "未知",
            event_name=pick_i18n_text(record.track.event.name_i18n, lang) if record.track and record.track.event else "未知",
            track_name=pick_i18n_text(record.track.name_i18n, lang) if record.track else "未知",
            route_type=record.route_data.get("type", "pointToPoint"),
            route_data=record.route_data,
            track_end_date=record.track.end_date.isoformat(),
            status=record.status,
            start_date=record.start_time.isoformat() if record.start_time else None,
            end_date=record.end_time.isoformat() if record.end_time else None,
            duration_seconds=record.duration_seconds,
            is_team=True if record.team_id is not None else False,
            team_title=record.team.title if record.team else None,
            team_competition_date=record.team.start_date if record.team else None,
            created_at=record.created_at.isoformat()
        )
        return RunningSingleRegisterResponse(
            record=record_info,
            asset_id=track.single_register_card_def.asset_id,
            new_balance=new_balance
        )


async def team_register_service(db: AsyncSession, team_code: str, user_id: str) -> CPAssetResponse:
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
        team = await get_active_team_by_code_for_update(db, team_code)
        if team is None:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.not_found")
        if team.track is None:
            raise BizException(code=ErrorCode.TRACK_ERROR, message="track.not_found")
        if team.track.start_date > datetime.now(timezone.utc):
            raise BizException(code=ErrorCode.TRACK_ERROR, message="track.not_started")
        if team.track.end_date < datetime.now(timezone.utc):
            raise BizException(code=ErrorCode.TRACK_ERROR, message="track.is_finished")
        if team.track.team_register_card_def is None:
            raise BizException(code=ErrorCode.TRACK_ERROR, message="track.data_error")
        
        user_member = next((member for member in team.members if member.user_id == user.id), None)
        if user_member is None:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.not_in_members")
        if user_member.is_registered:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.repeat_register")

        # 消费报名卡
        new_balance = await consume_cpasset(db, user.id, team.track.team_register_card_id, 1, "自行车赛事报名")

        record_id = f"record_{uuid.uuid4()}"
        new_record = RunningRaceRecord (
            record_id = record_id,
            user_id = user.id,
            track_id = team.track.id,
            team_id = team.id,
            route_data = team.track.route_data        # 报名时快照赛道路线
        )
        await create_record_crud(db, new_record)
        user_member.is_registered = True
        return CPAssetResponse(
            asset_id=team.track.team_register_card_def.asset_id,
            new_balance=new_balance
        )


async def get_incompleted_records_all(
    db: AsyncSession, 
    lang: Language,
    user_id: str,
    page: int,
    size: int
) -> List[RunningRecordInfo]:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
    records = await get_incompleted_records_by_user_id(db, user.id, page, size)
    return [RunningRecordInfo(
        record_id=r.record_id,
        region_id=r.track.event.region.region_id if r.track and r.track.event and r.track.event.region else "未知",
        event_name=pick_i18n_text(r.track.event.name_i18n, lang) if r.track and r.track.event else "未知",
        track_name=pick_i18n_text(r.track.name_i18n, lang) if r.track else "未知",
        route_type=r.route_data.get("type", "pointToPoint"),
        route_data=r.route_data,
        track_end_date=r.track.end_date.isoformat(),
        status=r.status,
        start_date=r.start_time.isoformat() if r.start_time else None,
        end_date=r.end_time.isoformat() if r.end_time else None,
        duration_seconds=r.duration_seconds,
        is_team=True if r.team_id is not None else False,
        team_title=r.team.title if r.team else None,
        team_competition_date=r.team.start_date.isoformat() if r.team else None,
        created_at=r.created_at.isoformat()
    ) for r in records]


async def get_completed_records_all(
    db: AsyncSession, 
    lang: Language,
    user_id: str,
    page: int,
    size: int
) -> List[RunningRecordInfo]:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
    records = await get_completed_records_by_user_id(db, user.id, page, size)
    return [RunningRecordInfo(
        record_id=r.record_id,
        region_id=r.track.event.region.region_id if r.track and r.track.event and r.track.event.region else "未知",
        event_name=pick_i18n_text(r.track.event.name_i18n, lang) if r.track and r.track.event else "未知",
        track_name=pick_i18n_text(r.track.name_i18n, lang) if r.track else "未知",
        route_type=r.route_data.get("type", "pointToPoint"),
        route_data=r.route_data,
        track_end_date=r.track.end_date.isoformat(),
        status=r.status,
        start_date=r.start_time.isoformat() if r.start_time else None,
        end_date=r.end_time.isoformat() if r.end_time else None,
        duration_seconds=r.duration_seconds,
        is_team=True if r.team_id is not None else False,
        team_title=r.team.title if r.team else None,
        team_competition_date=r.team.start_date.isoformat() if r.team else None,
        created_at=r.created_at.isoformat()
    ) for r in records]


async def cancel_register_service(db: AsyncSession, record_id: str, user_id: str) -> CPAssetResponse:
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
        record = await get_record_by_record_id(db, record_id)
        if record is None:
            raise BizException(code=ErrorCode.RECORD_ERROR, message="record.not_found")
        if record.user_id != user.id:
            raise BizException(code=ErrorCode.RECORD_ERROR, message="record.op_failed")
        if record.status != RecordStatus.notStarted:
            raise BizException(code=ErrorCode.RECORD_ERROR, message="record.status_error.cancel_register")
        if record.track is None:
            raise BizException(code=ErrorCode.TRACK_ERROR, message="track.not_found")
        if record.track.end_date < datetime.now(timezone.utc):
            raise BizException(code=ErrorCode.TRACK_ERROR, message="track.is_finished.cancel_register")
        if not record.track.single_register_card_def or not record.track.team_register_card_def:
            raise BizException(code=ErrorCode.TRACK_ERROR, message="track.data_error")

        is_team = record.team_id is not None
        team = None
        if is_team:
            team = await get_team_by_id_for_update(db, record.team_id)
            if team.status in [TeamStatus.ready, TeamStatus.recording, TeamStatus.completed]:
                raise BizException(code=ErrorCode.TEAM_ERROR, message="team.match_recording.cancel_register")

        register_card_def = record.track.team_register_card_def if is_team else record.track.single_register_card_def
        new_balance = await reward_cpasset(db, user.id, register_card_def.id, 1, "取消报名", AssetOperation.REFUND)
        if is_team:
            user_member = next((member for member in team.members if member.user_id == user.id), None)
            if user_member is None:
                raise BizException(code=ErrorCode.TEAM_ERROR, message="team.not_in_members")
            if not user_member.is_registered:
                raise BizException(code=ErrorCode.TEAM_ERROR, message="team.repeat_cancel_register")
            user_member.is_registered = False
        await delete_record_crud(db, record)
        return CPAssetResponse(
            asset_id=register_card_def.asset_id,
            new_balance=new_balance
        )


async def enter_team_competition_link_service(db: AsyncSession, record_id: str):
    record = await get_record_by_record_id(db, record_id)
    if record is None:
        raise BizException(code=ErrorCode.RECORD_ERROR, message="record.not_found")
    if record.track is None:
        raise BizException(code=ErrorCode.TRACK_ERROR, message="track.not_found")
    if record.track.end_date < datetime.now(timezone.utc):
        raise BizException(code=ErrorCode.TEAM_ERROR, message="team.status_expired")
    if record.team is None:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="team.not_found")
    if record.team.status != TeamStatus.ready and record.team.status != TeamStatus.recording:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="team.status_error.enter_match")
    if record.team.start_date > datetime.now(timezone.utc) or datetime.now(timezone.utc) > record.team.start_date + timedelta(hours=2):
        raise BizException(code=ErrorCode.RECORD_ERROR, message="team.out_of_match_time")


async def start_single_competition_service(db: AsyncSession, user_id: str, info: RunningBeginInfo):
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
    record = await get_record_by_record_id(db, info.record_id)
    if record is None:
        raise BizException(code=ErrorCode.RECORD_ERROR, message="record.not_found")
    if record.user_id != user.id:
        raise BizException(code=ErrorCode.RECORD_ERROR, message="record.op_failed")
    if record.status != RecordStatus.notStarted:
        raise BizException(code=ErrorCode.RECORD_ERROR, message="record.status_error.start_match")
    if record.track is None:
        raise BizException(code=ErrorCode.TRACK_ERROR, message="track.not_found")
    if record.track.end_date < info.start_time:
        raise BizException(code=ErrorCode.TRACK_ERROR, message="track.is_finished")
    update_data = {
        "status": RecordStatus.recording,
        "start_time": info.start_time
    }
    await update_record_crud(db, record, update_data)
    await db.commit()


async def start_team_competition_service(db: AsyncSession, user_id: str, info: RunningBeginInfo):
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
        record = await get_record_by_record_id(db, info.record_id)
        if record is None:
            raise BizException(code=ErrorCode.RECORD_ERROR, message="record.not_found")
        if record.user_id != user.id:
            raise BizException(code=ErrorCode.RECORD_ERROR, message="record.op_failed")
        if record.status != RecordStatus.notStarted:
            raise BizException(code=ErrorCode.RECORD_ERROR, message="record.status_error.start_match")
        if record.track is None:
            raise BizException(code=ErrorCode.TRACK_ERROR, message="track.not_found")
        if record.track.end_date < info.start_time:
            raise BizException(code=ErrorCode.TRACK_ERROR, message="track.is_finished")
        if record.team_id is None:
            raise BizException(code=ErrorCode.RECORD_ERROR, message="team.not_in_members")
        
        team = await get_team_by_id_for_update(db, record.team_id)
        if team is None:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.not_found")
        if team.status == TeamStatus.ready and team.start_date_real is None:
            if info.start_time < team.start_date:
                raise BizException(code=ErrorCode.RECORD_ERROR, message="team.out_of_match_time")
            if info.start_time > team.start_date + timedelta(hours=2):
                raise BizException(code=ErrorCode.RECORD_ERROR, message="team.out_of_match_time")
            team.start_date_real = info.start_time
            team.status = TeamStatus.recording
        elif team.status == TeamStatus.recording and team.start_date_real is not None:
            if info.start_time > team.start_date_real + timedelta(seconds=180) or info.start_time < team.start_date_real:
                raise BizException(code=ErrorCode.RECORD_ERROR, message="team.out_of_match_window")
        else:
            raise BizException(code=ErrorCode.RECORD_ERROR, message="team.status_error")

        update_data = {
            "status": RecordStatus.recording,
            "start_time": info.start_time
        }
        await update_record_crud(db, record, update_data)


async def _fetch_finish_weather(path):
    if not path:
        return None
    point = path[-1].base
    return await fetch_weather_snapshot(point.lat, point.lon)


async def _capture_record_pace_snapshot(db: AsyncSession, record: RunningRaceRecord, user: User) -> dict:
    """冻结本次成绩写入排行榜之前的实时配速基线。"""
    gender = (user.gender or Gender.male).value
    return {
        "version": 1,
        "finish_times": await get_track_leaderboard_times("running", record.track.track_id, gender),
        "pb_profile": await get_user_best_race_profile(db, record.track_id, user.id),
        "route_data": record.route_data,
    }


async def _save_record_pace_snapshot(db: AsyncSession, record: RunningRaceRecord, user: User) -> None:
    snapshot = VideoWatermarkPaceSnapshot(snapshot=await _capture_record_pace_snapshot(db, record, user))
    db.add(snapshot)
    await db.flush()
    record.pace_snapshot_id = snapshot.id


async def finish_single_competition_service(db: AsyncSession, info: RunningFinishInfo, user_id: str) -> MatchFinishResponse:
    finish_weather = await _fetch_finish_weather(info.path)
    try:
        async with db.begin():
            user = await get_user_by_id(db, user_id)
            if user is None:
                raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
            record = await get_record_by_record_id(db, info.record_id)
            if record is None:
                raise BizException(code=ErrorCode.RECORD_ERROR, message="record.not_found")
            # 幂等：同一 client_upload_id 已结算过，直接返回（防止重传重复发奖/覆盖成绩）
            if info.client_upload_id and record.client_upload_id == info.client_upload_id:
                return MatchFinishResponse(match_result=None)
            if record.track is None:
                raise BizException(code=ErrorCode.TRACK_ERROR, message="track.not_found")
            if record.start_time is None or record.start_time > info.end_time:
                raise BizException(code=ErrorCode.RECORD_ERROR, message="record.invalid_time")
            if record.status != RecordStatus.recording and record.status != RecordStatus.expired:
                raise BizException(code=ErrorCode.RECORD_ERROR, message="record.status_error.finish_match")
            if record.pace_snapshot_id is None:
                await _save_record_pace_snapshot(db, record, user)
            original_time = (info.end_time - record.start_time).total_seconds()
            final_time = original_time
            bonus_time = 0

            for item in info.bonus_in_cards:
                bonus_time += item.bonus_time
                card = await get_equip_card_by_card_id(db, item.card_id)
                if card is not None:
                    db.add(CardBonusInRunningRecord(
                        record_id=record.id,
                        card_id=card.id,
                        bonus_time=item.bonus_time
                    ))
            # 卡牌奖励时间上限为20%
            if bonus_time / original_time > 0.2:
                final_time = final_time * 0.8
            else:
                final_time -= bonus_time

            # 赛道熟悉度收益 & 训练状态收益
            familiarity = await get_familiarity_by_track_and_user(db, record.track, user.id)
            training_state = await get_training_state_by_user(db, user.id)
            training_state_value = training_state.current_value if training_state else 0
            familiarity_ratio = familiarity * 0.02
            training_state_ratio = training_state_value * 0.02 / 100
            familiarity_time = original_time * familiarity_ratio
            training_state_time = original_time * training_state_ratio
            final_time -= (familiarity_time + training_state_time)

            # 多检查点路径校验（对齐 route training：首尾必经，中间点可 miss 计罚时）
            checkpoints = extract_checkpoints_from_route_data(record.route_data)
            checkpoint_events, checkpoint_penalty, path_passes = build_route_checkpoint_events([p.base for p in info.path], checkpoints)
            final_time += checkpoint_penalty

            path_data = [p.model_dump() for p in info.path]
            path = RunningRacePath(
                path_id=f"race_path_{uuid.uuid4()}",
                record_id=record.id,
                path=path_data
            )
            db.add(path)
            await db.flush()  # 先flush，让对象持久化
            await db.refresh(path)  # 再refresh，获取数据库生成的值

            # 审核账号直接通过
            validation_score = info.validation_score if user_id != "176987647574535" else 100

            update_data = {
                "path_id": path.id,
                "end_time": info.end_time,
                "duration_seconds": final_time,
                "penalty_seconds": checkpoint_penalty,
                "validation_score": validation_score,
                "is_finish_bonus_computing": True,       # 当前只有 team mode 的 magiccard 需要延迟收益计算
                "local_date": get_user_local_date(user, info.end_time),
                "familiarity_time": familiarity_time,
                "training_state_time": training_state_time,
                "weather_condition": finish_weather.condition if finish_weather else None,
                "weather_temperature_c": finish_weather.temperature_c if finish_weather else None,
                "client_upload_id": info.client_upload_id
            }
            if record.status == RecordStatus.recording:
                if not path_passes:
                    update_data["status"] = RecordStatus.invalid       # 未经过赛道首尾检查点
                elif validation_score >= 70:
                    update_data["status"] = RecordStatus.completed
                elif validation_score >= 30:
                    update_data["status"] = RecordStatus.toBeVerified
                else:
                    update_data["status"] = RecordStatus.invalid
            await update_record_crud(db, record, update_data)

            # 审核账号直接返回
            if user_id == "176987647574535":
                return MatchFinishResponse(match_result=None)

            # 更新奖金池
            track = await get_track_by_track_id_for_update(db, record.track.track_id)
            if track is None or track.event is None or track.event.season is None:
                raise BizException(code=ErrorCode.TRACK_ERROR, message="track.not_found")
            if track.single_register_card_def is None:
                raise BizException(code=ErrorCode.TRACK_ERROR, message="track.data_error")
            card_price = await get_register_card_price(db, track.single_register_card_id)
            if card_price:
                price_need_to_add = int(card_price.price / 5) if card_price.ccasset_type == CCAssetType.COIN else int(card_price.price / 2.5)
                track.prize_pool += price_need_to_add
            
            match_result = None
            # 更新个人统计数据 & 每日任务进度 & 发放比赛结算奖励 & 更新排行榜
            if record.status == RecordStatus.completed:
                distance = compute_distance([p.base for p in info.path])
                await add_or_update_career_statistic_data(db, track.event.season.id, user.id, distance, final_time)
                await add_or_update_daily_task_record(db, user, distance, final_time)
                xp_before, xp_delta = await settle_running_match_xp(db, record)
                reward_result = await compute_running_match_rewards(record)
                if reward_result:
                    rewards = reward_result[2]
                    total_rewards = []
                    for reward in rewards:
                        balance = await reward_ccasset(db, reward.ccasset_type, reward.new_ccamount, user.id, "单次running比赛结算", AssetOperation.REWARD)
                        reward_response = CCAssetRewardResponse(
                            ccasset_type=reward.ccasset_type,
                            new_ccamount=balance,
                            reward_amount=reward.new_ccamount
                        )
                        total_rewards.append(reward_response)
                    match_result = MatchFinishInfo(
                        is_user_best=reward_result[0],
                        is_track_best=reward_result[1],
                        rewards=total_rewards,
                        xp_before=xp_before,
                        xp_delta=xp_delta
                    )
                    # 刷新个人最佳时存档 split profile（供实时预测名次 / 自我对比）
                    if reward_result[0]:
                        record.split_profile = build_split_profile(
                            [p.base for p in info.path], record.route_data, final_time, "running",
                            checkpoint_events=checkpoint_events,
                            card_bonus_samples=[
                                (p.base.timestamp, sum(item.bonus_time for item in p.card_bonus))
                                for p in info.path
                            ],
                            original_duration_seconds=original_time,
                        )
                # 更新排行榜
                if record.duration_seconds is not None:
                    await update_running_leaderboard_for_record(record)
            return MatchFinishResponse(match_result=match_result)
    except Exception:
        logger.exception("finish single running competition failed")
        raise BizException(code=ErrorCode.UNKNOWN_ERROR, message="sys.unknown_error")


async def finish_team_competition_service(db: AsyncSession, info: RunningFinishInfo, user_id: str) -> MatchFinishResponse:
    finish_weather = await _fetch_finish_weather(info.path)
    try:
        async with db.begin():
            user = await get_user_by_id(db, user_id)
            if user is None:
                raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
            
            # 先对 team 上锁
            team_id = await get_team_id_by_record_id(db, info.record_id)
            if not team_id:
                raise BizException(code=ErrorCode.RECORD_ERROR, message="team.not_in_members")
            team = await get_team_by_id_for_update(db, team_id)
            if team is None:
                raise BizException(code=ErrorCode.TEAM_ERROR, message="team.not_found")
            
            record = None
            records_in_team = await get_records_by_team_id_for_update(db, team_id)
            for r in records_in_team:
                if r.user_id == user.id:
                    record = r

            if record is None:
                raise BizException(code=ErrorCode.RECORD_ERROR, message="record.not_found")
            # 幂等：同一 client_upload_id 已结算过，直接返回（防止重传重复发奖/覆盖成绩）
            if info.client_upload_id and record.client_upload_id == info.client_upload_id:
                return MatchFinishResponse(match_result=None)
            if record.track is None:
                raise BizException(code=ErrorCode.TRACK_ERROR, message="track.not_found")
            if record.start_time is None or record.start_time > info.end_time:
                raise BizException(code=ErrorCode.RECORD_ERROR, message="record.invalid_time")
            if record.status != RecordStatus.recording and record.status != RecordStatus.expired:
                raise BizException(code=ErrorCode.RECORD_ERROR, message="record.status_error.finish_match")

            if record.pace_snapshot_id is None:
                await _save_record_pace_snapshot(db, record, user)
            
            original_time = (info.end_time - record.start_time).total_seconds()
            final_time = original_time
            bonus_time = 0

            # 待应用的 team bonus
            for bonus_info in record.card_bonus:
                bonus_time += bonus_info.bonus_time
                if bonus_info.bonus_ratio:
                    bonus_time += final_time * bonus_info.bonus_ratio

            for item in info.bonus_in_cards:
                bonus_time += item.bonus_time
                card = await get_equip_card_by_card_id(db, item.card_id)
                if card is not None:
                    db.add(CardBonusInRunningRecord(
                        record_id=record.id,
                        card_id=card.id,
                        bonus_time=item.bonus_time
                    ))
            # 卡牌奖励时间上限为20%
            if bonus_time / original_time > 0.2:
                final_time = final_time * 0.8
            else:
                final_time -= bonus_time

            # 赛道熟悉度收益 & 训练状态收益
            familiarity = await get_familiarity_by_track_and_user(db, record.track, user.id)
            training_state = await get_training_state_by_user(db, user.id)
            training_state_value = training_state.current_value if training_state else 0
            familiarity_ratio = familiarity * 0.02
            training_state_ratio = training_state_value * 0.02 / 100
            familiarity_time = original_time * familiarity_ratio
            training_state_time = original_time * training_state_ratio
            final_time -= (familiarity_time + training_state_time)

            # 多检查点路径校验（对齐 route training：首尾必经，中间点可 miss 计罚时）
            checkpoints = extract_checkpoints_from_route_data(record.route_data)
            checkpoint_events, checkpoint_penalty, path_passes = build_route_checkpoint_events([p.base for p in info.path], checkpoints)
            final_time += checkpoint_penalty

            path_data = [p.model_dump() for p in info.path]
            path = RunningRacePath(
                path_id=f"race_path_{uuid.uuid4()}",
                record_id=record.id,
                path=path_data
            )
            db.add(path)
            await db.flush()
            await db.refresh(path)

            team_bonus_records = await get_bonus_record_with_team_magic_card_for_update(db, team_id)
            team_bonus_record = None
            is_finish_computed = True
            for br in team_bonus_records:
                if br.user_id == user.id and info.team_bonus:
                    br.bonus_in_ratio = info.team_bonus.bonus_ratio
                    br.bonus_in_seconds = info.team_bonus.bonus_seconds
                    team_bonus_record = br
                if br.user_id != user.id and not br.is_applied:
                    is_finish_computed = False

            if not path_passes:
                status = RecordStatus.invalid       # 未经过赛道首尾检查点
            elif info.validation_score >= 70:
                status = RecordStatus.completed
            elif info.validation_score >= 30:
                status = RecordStatus.toBeVerified
            else:
                status = RecordStatus.invalid

            update_data = {
                "path_id": path.id,
                "end_time": info.end_time,
                "duration_seconds": final_time,
                "penalty_seconds": checkpoint_penalty,
                "status": status,
                "validation_score": info.validation_score,
                "is_finish_bonus_computing": is_finish_computed,
                "local_date": get_user_local_date(user, info.end_time),
                "familiarity_time": familiarity_time,
                "training_state_time": training_state_time,
                "weather_condition": finish_weather.condition if finish_weather else None,
                "weather_temperature_c": finish_weather.temperature_c if finish_weather else None,
                "client_upload_id": info.client_upload_id
            }
            await update_record_crud(db, record, update_data)

            # 如果其他队员都完成比赛则修改team状态
            all_completed = True if record.status != RecordStatus.notStarted and record.status != RecordStatus.recording else False
            for r in records_in_team:
                if r.user_id != user.id and (r.status == RecordStatus.notStarted or r.status == RecordStatus.recording):
                    all_completed = False
                    break
            if all_completed:
                team.status = TeamStatus.completed

            # 更新赛道奖金池
            track = await get_track_by_track_id_for_update(db, record.track.track_id)
            if track is None or track.event is None or track.event.season is None:
                raise BizException(code=ErrorCode.TRACK_ERROR, message="track.not_found")
            if track.team_register_card_def is None:
                raise BizException(code=ErrorCode.TRACK_ERROR, message="track.data_error")
            card_price = await get_register_card_price(db, track.team_register_card_id)
            if card_price:
                price_need_to_add = int(card_price.price / 5) if card_price.ccasset_type == CCAssetType.COIN else int(card_price.price / 2.5)
                track.prize_pool += price_need_to_add

            match_result = None
            if record.status == RecordStatus.completed:
                # pass validation task: 发放比赛结算奖励 & 更新排行榜 & 更新个人统计数据 & 更新每日任务进度
                # 如果有效成绩准备好立即处理当前 record
                if is_finish_computed:
                    xp_before, xp_delta = await settle_running_match_xp(db, record)
                    reward_result = await compute_running_match_rewards(record)
                    if reward_result:
                        rewards = reward_result[2]
                        total_rewards = []
                        for reward in rewards:
                            balance = await reward_ccasset(db, reward.ccasset_type, reward.new_ccamount, user.id, "单次running比赛结算", AssetOperation.REWARD)
                            reward_response = CCAssetRewardResponse(
                                ccasset_type=reward.ccasset_type,
                                new_ccamount=balance,
                                reward_amount=reward.new_ccamount
                            )
                            total_rewards.append(reward_response)
                        match_result = MatchFinishInfo(
                            is_user_best=reward_result[0],
                            is_track_best=reward_result[1],
                            rewards=total_rewards,
                            xp_before=xp_before,
                            xp_delta=xp_delta
                        )
                        # 刷新个人最佳时存档 split profile（供实时预测名次 / 自我对比）
                        if reward_result[0]:
                            record.split_profile = build_split_profile(
                                [p.base for p in info.path], record.route_data, final_time, "running",
                                checkpoint_events=checkpoint_events,
                                card_bonus_samples=[
                                    (p.base.timestamp, sum(item.bonus_time for item in p.card_bonus))
                                    for p in info.path
                                ],
                                original_duration_seconds=original_time,
                            )
                    await update_running_leaderboard_for_record(record)
                    distance = compute_distance([p.base for p in info.path])
                    await add_or_update_career_statistic_data(db, track.event.season.id, user.id, distance, final_time)
                    await add_or_update_daily_task_record(db, user, distance, final_time)
                # 应用 team bonus
                if info.team_bonus and team_bonus_record:
                    await finish_competition_with_team_bonus_card_service(db, user, team_id, info.team_bonus)
            elif record.status == RecordStatus.invalid:
                # failed validation task: 有 team bonus 时标记为已应用
                if info.team_bonus and team_bonus_record:
                    team_bonus_record.is_applied = True
            # tobevalid 状态交给手动处理
            return MatchFinishResponse(match_result=match_result)
    except Exception:
        logger.exception("finish team running competition failed")
        raise BizException(code=ErrorCode.UNKNOWN_ERROR, message="sys.unknown_error")


async def query_unverified_records_service(
    db: AsyncSession,
    page: int = 1,
    size: int = 10
) -> List[RunningUnverifiedRecordResponse]:
    records = await get_unverified_records(db, page, size)
    if not records:
        return RunningUnverifiedRecordResponse(records=[])
    infos = [RunningUnverifiedRecordInfo(
        is_vip=r.user.subscription_info.is_active if r.user.subscription_info else False,
        record_id=r.record_id,
        validation_score=r.validation_score,
        path=[RunningPathPoint.model_validate(p) for p in r.path.path],
        finished_at=r.end_time.isoformat() if r.end_time else None
    ) for r in records if r.user and r.path]
    return RunningUnverifiedRecordResponse(records=infos)


async def handle_record_verified_service(db: AsyncSession, record_id: str, result: bool):
    async with db.begin():
        record = await get_record_by_record_id(db, record_id)
        if record is None:
            raise BizException(code=ErrorCode.RECORD_ERROR, message="record.not_found")
        if record.status != RecordStatus.toBeVerified:
            raise BizException(code=ErrorCode.RECORD_ERROR, message="比赛状态错误")
        team_bonus_record = await get_bonus_record_with_team_magic_card_by_team_user(db, record.team_id, record.user_id)
        if result:
            record.status = RecordStatus.completed
            if record.is_finish_bonus_computing:
                points = []
                if record.path and record.path.path:
                    points = [RunningPathPoint.model_validate(p) for p in record.path.path]
                distance = compute_distance([p.base for p in points])
                if record.duration_seconds is None:
                    raise BizException(code=ErrorCode.RECORD_ERROR, message="比赛成绩为空")
                track = await get_track_by_track_id(db, record.track.track_id)
                if track is None or track.event is None or track.event.season is None:
                    raise BizException(code=ErrorCode.TRACK_ERROR, message="track.not_found")
                await add_or_update_career_statistic_data(db, track.event.season.id, record.user.id, distance, record.duration_seconds)
                await add_or_update_daily_task_record(db, record.user, distance, record.duration_seconds)
                # 发放奖励
                await send_running_match_rewards(db, record)
                # 更新排行榜
                await update_running_leaderboard_for_record(record)
            # 应用 team bonus
            if team_bonus_record and not team_bonus_record.is_applied:
                team_bonus_record.is_applied = True
                records = await get_records_by_team_id_for_update(db, record.team_id)
                for r in records:
                    if r.user_id != record.user.id:
                        db.add(CardBonusInRunningRecord(
                            record_id=r.id,
                            card_id=team_bonus_record.card_id,
                            bonus_ratio=team_bonus_record.bonus_in_ratio,
                            bonus_time=team_bonus_record.bonus_in_seconds if team_bonus_record.bonus_in_seconds else 0
                        ))
                        # 已结束需要手动应用 bonus
                        if r.duration_seconds and r.start_time and r.end_time:
                            raw_duration = (r.end_time - r.start_time).total_seconds()
                            if team_bonus_record.bonus_in_ratio:
                                r.duration_seconds -= team_bonus_record.bonus_in_ratio * raw_duration
                            r.duration_seconds -= team_bonus_record.bonus_in_seconds if team_bonus_record.bonus_in_seconds else 0
                            r.duration_seconds = max(raw_duration * 0.8, r.duration_seconds)
        else:
            record.status = RecordStatus.invalid
            if team_bonus_record:
                team_bonus_record.is_applied = True


async def get_team_expired_date_service(db: AsyncSession, record_id: str) -> RunningTeamExpiredResponse:
    record = await get_record_by_record_id(db, record_id)
    if record is None:
        raise BizException(code=ErrorCode.RECORD_ERROR, message="record.not_found")
    if record.track is None:
        raise BizException(code=ErrorCode.TRACK_ERROR, message="track.not_found")
    if record.team is None:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="team.not_found")
    expired_date = (record.team.start_date_real + timedelta(seconds=180)).isoformat() if record.team.start_date_real else None
    return RunningTeamExpiredResponse(expired_date=expired_date)


async def get_latest_snapshot_key(track_id: str, gender: Gender) -> str | None:
    base_prefix = f"leaderboard:running:{track_id}:{gender.value}:snapshot:"
    # 获取所有匹配的 key
    keys = await redis_client.keys(f"{base_prefix}*")
    if not keys:
        return None
    # 过滤掉 rewards hash
    keys = [k for k in keys if not k.endswith(":rewards")]
    if not keys:
        return None
    # 从 key 中提取出时间戳，并选择最新的
    latest_key = max(keys, key=lambda k: k.split(":")[-1])
    return latest_key


async def query_leaderboard_in_page(
    db: AsyncSession,
    track_id: str,
    gender: Gender,
    page: int = 1,
    page_size: int = 20,
    timestamp: Optional[str] = None
) -> RunningLeaderboardResponse:
    if timestamp:
        snapshot_key = f"leaderboard:running:{track_id}:{gender.value}:snapshot:{timestamp}"
    else:
        snapshot_key = await get_latest_snapshot_key(track_id, gender)
        if snapshot_key is None:
            return RunningLeaderboardResponse(entries=[], time_stamp=None)
        timestamp = snapshot_key.split(":")[-1]
    rewards_hash_key = f"{snapshot_key}:rewards"

    start = (page - 1) * page_size
    end = start + page_size - 1

    # 从Redis获取排行榜数据
    leaderboard_page = await redis_client.zrange(snapshot_key, start, end, withscores=True)
    if not leaderboard_page:
        raise BizException(code=ErrorCode.LEADERBOARD_ERROR, message="leaderboard.expired")
    
    member_keys = [member for member, _ in leaderboard_page]
    rewards_data = await redis_client.hmget(rewards_hash_key, *member_keys)

    user_ids, record_ids, durations = [], [], []
    for member, duration_seconds in leaderboard_page:
        if ":" in member:
            user_id, record_id = member.split(":", 1)
        else:
            user_id, record_id = member, "None"
        user_ids.append(user_id)
        record_ids.append(record_id)
        durations.append(duration_seconds)

    # 批量获取用户信息
    users = await get_users_by_user_ids(db, user_ids)
    user_dict = {user.user_id: user for user in users}
    # 构建排行榜响应
    leaderboard_infos = []
    for user_id, record_id, duration_seconds, reward_json in zip(user_ids, record_ids, durations, rewards_data):
        user = user_dict.get(str(user_id))
        try:
            reward = json.loads(reward_json) if reward_json else {"voucher": 0, "score": 0, "rank": 0}
        except:
            reward = {"voucher": 0, "score": 0, "rank": 0}
        leaderboard_infos.append(RunningLeaderboardInfo(
            rank=reward["rank"],
            record_id=record_id,
            user_info=PersonInfoResponse(
                user_id=user_id,
                avatar_image_url=build_resource_url(user.avatar_image_url if user else "/resources/placeholder/avatar.jpg"),
                nickname=user.nickname if user else "未知"
            ),
            duration_seconds=duration_seconds,
            voucher=reward["voucher"],
            score=reward["score"]
        ))
    return RunningLeaderboardResponse(
        entries=leaderboard_infos, 
        time_stamp=timestamp
    )

async def query_leaderboard_history_in_page(
    db: AsyncSession,
    track_id: str,
    gender: Gender,
    page: int = 1,
    page_size: int = 20
) -> RunningLeaderboardResponse:
    track = await get_track_by_track_id(db, track_id)
    if track is None:
        raise BizException(code=ErrorCode.TRACK_ERROR, message="track.not_found")
    records = await get_leaderboad_records_in_page(db, track.id, gender, page, page_size)
    entries = []
    for record in records:
        if record.record is None or record.user is None:
            continue
        entries.append(RunningLeaderboardInfo(
            rank=record.rank_position,
            record_id=record.record.record_id,
            user_info=PersonInfoResponse(
                user_id=record.user.user_id,
                avatar_image_url=build_resource_url(record.user.avatar_image_url),
                nickname=record.user.nickname
            ),
            duration_seconds=record.duration_seconds,
            voucher=record.reward["voucher"],
            score=record.score
        ))
    return RunningLeaderboardResponse(entries=entries, time_stamp=None)

async def get_score_leaderboard_service(
    db: AsyncSession,
    season_id: str,
    gender: Gender,
    page: int = 1,
    page_size: int = 20
) -> RunningScoreLeaderboardResponse:
    season = await get_season_by_season_id(db, season_id)
    if not season:
        raise BizException(code=ErrorCode.SEASON_ERROR, message="season.not_found")
    scores = await get_scores_in_page(db, season.id, gender, page, page_size)
    entries = []
    for rank, score in enumerate(scores, start=1):
        if score.user is None:
            continue
        entries.append(RunningScoreLeaderboardInfo(
            rank=rank,
            user_info=PersonInfoResponse(
                user_id=score.user.user_id,
                avatar_image_url=build_resource_url(score.user.avatar_image_url),
                nickname=score.user.nickname
            ),
            score=score.score
        ))
    return RunningScoreLeaderboardResponse(entries=entries)

async def query_user_rank_info(db: AsyncSession, user_id: str, track_id: str, user: User | None = None) -> RunningRankInfo:
    # 批量场景下由调用方传入已查到的 user，避免逐条重复查询
    if user is None:
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
    gender = user.gender if user.gender else Gender.male

    snapshot_key = await get_latest_snapshot_key(track_id, gender)
    if not snapshot_key:
        return RunningRankInfo()
    rewards_hash_key = f"{snapshot_key}:rewards"

    members = await redis_client.zrange(snapshot_key, 0, -1, withscores=True)

    for member, duration in members:
        if member.startswith(f"{user_id}:"):
            _, record_id = member.split(":", 1)
            member_key = f"{user_id}:{record_id}"
            reward_json = await redis_client.hget(rewards_hash_key, member_key)
            if not reward_json:
                return RunningRankInfo()
            try:
                reward = json.loads(reward_json)
            except:
                return RunningRankInfo()
            return RunningRankInfo(
                record_id=record_id,
                rank=reward["rank"],
                duration_seconds=duration,
                reward_voucher_amount=reward["voucher"],
                score=reward["score"]
            )
    return RunningRankInfo()


async def get_user_rank_and_score(track_id: str, user_id: str, gender: Gender) -> tuple[int | None, float | None, str | None]:
    key = f"leaderboard:running:{track_id}:{gender.value}"
    members = await redis_client.zrange(key, 0, -1, withscores=True)
    for member, score in members:
        if member.startswith(f"{user_id}:"):
            _, record_id = member.split(":", 1)
            rank = await redis_client.zrank(key, member)
            return (rank + 1 if rank is not None else None, score, record_id)
    return None, None, None


async def create_team_service(db: AsyncSession, create_info: RunningTeamCreateInfo, user_id: str) -> RunningTeamCreateResponse:
    async with db.begin():
        track = await get_track_by_track_id(db, create_info.track_id)
        if track is None:
            raise BizException(code=ErrorCode.TRACK_ERROR, message="track.not_found")
        if track.start_date > datetime.now(timezone.utc):
            raise BizException(code=ErrorCode.TRACK_ERROR, message="track.not_started")
        if track.end_date < datetime.now(timezone.utc):
            raise BizException(code=ErrorCode.TRACK_ERROR, message="track.is_finished")
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
        # 消费组队卡
        team_card_def = await get_team_card_def(db, SportType.running)
        new_balance = await consume_cpasset(db, user.id, team_card_def.id, 1, "自行车赛事报名")
        team_id = f"team_{uuid.uuid4()}"
        team_code = team_id[-8:]
        new_team = RunningTeam(
            team_id=team_id,
            team_code=team_code,
            track_id=track.id,
            title=create_info.title,
            description=create_info.description,
            members_count_max=create_info.team_size,
            is_public=create_info.is_public,
            start_date=create_info.competition_date
        )
        team_code, new_team_id = await create_team_crud(db, new_team)
        member_id = f"member_{uuid.uuid4()}"
        new_member = RunningTeamMember(
            member_id=member_id,
            team_id=new_team_id,
            user_id=user.id,
            is_leader=True
        )
        await create_team_member_crud(db, new_member)
        return RunningTeamCreateResponse(
            team_code=team_code,
            asset_id=team_card_def.asset_id,
            new_balance=new_balance
        )
    

async def get_public_teams_service(
    db: AsyncSession, 
    track_id: str,
    page: int, 
    size: int
) -> RunningAppliedTeamResponse:
    track = await get_track_by_track_id(db, track_id)
    if track is None:
        raise BizException(code=ErrorCode.TRACK_ERROR, message="track.not_found")
    if track.start_date > datetime.now(timezone.utc):
        raise BizException(code=ErrorCode.TRACK_ERROR, message="track.not_started")
    if track.end_date < datetime.now(timezone.utc):
        raise BizException(code=ErrorCode.TRACK_ERROR, message="track.is_finished")
    teams = await get_public_teams_by_track_id(db, track.id, page, size)
    infos = []
    for t in teams:
        leader_member = next((m for m in t.members if m.is_leader), None)
        if leader_member is not None:
            infos.append(RunningAppliedTeamInfo(
                team_id=t.team_id,
                leader_id=leader_member.user.user_id,
                leader_name=leader_member.user.nickname,
                leader_avatar_url=build_resource_url(leader_member.user.avatar_image_url),
                title=t.title,
                description=t.description,
                member_count=len(t.members),
                max_member_size=t.members_count_max,
                region_id="未知",
                event_name="未知",
                track_name="未知",
                competition_date=t.start_date.isoformat(),
            ))
    return RunningAppliedTeamResponse(teams=infos)


async def get_user_applied_teams(
    db: AsyncSession,
    lang: Language,
    user_id: str,
    page: int, 
    size: int
) -> RunningAppliedTeamResponse:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
    teams = await get_applied_teams_by_user_id(db, user.id, page, size)
    # 批量查找所有队长 user_id
    leader_ids = [m.user_id for t in teams for m in t.members if m.is_leader]
    users = await get_users_by_ids(db, leader_ids)
    user_map = {user.id: user for user in users}

    infos = []
    for t in teams:
        leader_member = next((m for m in t.members if m.is_leader), None)
        leader = user_map.get(leader_member.user_id) if leader_member else None
        if leader is not None:
            infos.append(RunningAppliedTeamInfo(
                team_id=t.team_id,
                leader_id=leader.user_id,
                leader_name=leader.nickname,
                leader_avatar_url=build_resource_url(leader.avatar_image_url),
                title=t.title,
                description=t.description,
                member_count=len(t.members),
                max_member_size=t.members_count_max,
                region_id=t.track.event.region.region_id if t.track and t.track.event and t.track.event.region else "未知",
                event_name=pick_i18n_text(t.track.event.name_i18n, lang) if t.track and t.track.event else "未知",
                track_name=pick_i18n_text(t.track.name_i18n, lang) if t.track else "未知",
                competition_date=t.start_date.isoformat(),
            ))
    return RunningAppliedTeamResponse(teams=infos)


async def get_user_teams(
    db: AsyncSession, 
    lang: Language,
    user_id: str,
    relationship: TeamRelationship,
    page: int, 
    size: int
) -> RunningTeamResponse:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
    
    infos = []
    if relationship == TeamRelationship.created:
        teams = await get_created_teams_by_user_id(db, user.id, page, size)
        for t in teams:
            infos.append(RunningTeamInfo(
                team_id=t.team_id,
                leader_id=user_id,
                leader_name=user.nickname,
                leader_avatar_url=build_resource_url(user.avatar_image_url),
                title=t.title,
                member_count=len(t.members),
                max_member_size=t.members_count_max,
                team_code=t.team_code,
                region_id=t.track.event.region.region_id if t.track and t.track.event and t.track.event.region else "未知",
                event_name=pick_i18n_text(t.track.event.name_i18n, lang) if t.track and t.track.event else "未知",
                track_name=pick_i18n_text(t.track.name_i18n, lang) if t.track else "未知",
                is_public=t.is_public,
                status=t.status,
                competition_date=t.start_date.isoformat(),
            ))
    else:
        teams = await get_joined_teams_by_user_id(db, user.id, page, size)
        leader_ids = [m.user_id for t in teams for m in t.members if m.is_leader]
        users = await get_users_by_ids(db, leader_ids)
        user_map = {user.id: user for user in users}
        for t in teams:
            leader_member = next((m for m in t.members if m.is_leader), None)
            leader = user_map.get(leader_member.user_id) if leader_member else None
            if leader is not None:
                infos.append(RunningTeamInfo(
                    team_id=t.team_id,
                    leader_id=leader.user_id,
                    leader_name=leader.nickname,
                    leader_avatar_url=build_resource_url(leader.avatar_image_url),
                    title=t.title,
                    member_count=len(t.members),
                    max_member_size=t.members_count_max,
                    team_code=t.team_code,
                    region_id=t.track.event.region.region_id if t.track and t.track.event and t.track.event.region else "未知",
                    event_name=pick_i18n_text(t.track.event.name_i18n, lang) if t.track and t.track.event else "未知",
                    track_name=pick_i18n_text(t.track.name_i18n, lang) if t.track else "未知",
                    is_public=t.is_public,
                    status=t.status,
                    competition_date=t.start_date.isoformat(),
                ))
    return RunningTeamResponse(teams=infos)


async def get_team_detail_service(db: AsyncSession, lang: Language, team_id: str) -> RunningTeamDetailResponse:
    team = await get_team_by_team_id(db, team_id)
    if team is None:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="team.not_found")
    if team.status == TeamStatus.completed:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="team.status_expired")
    members = [
        RunningTeamMemberInfo(
            member_id=m.member_id,
            user_id=m.user.user_id,
            nick_name=m.user.nickname if m.user else "未知",
            avatar_url=build_resource_url(m.user.avatar_image_url if m.user else "未知"),
            join_date=m.created_at.isoformat(),
            is_registered=m.is_registered,
            is_leader=m.is_leader
        )
        for m in team.members
    ]
    region_id = team.track.event.region.region_id if team.track and team.track.event and team.track.event.region else "未知"
    event_name = pick_i18n_text(team.track.event.name_i18n, lang) if team.track and team.track.event else "未知"
    track_name = pick_i18n_text(team.track.name_i18n, lang) if team.track else "未知"
    return RunningTeamDetailResponse(
        team_id=team.team_id,
        title=team.title,
        description=team.description,
        max_member_size=team.members_count_max,
        team_code=team.team_code,
        region_id=region_id,
        event_name=event_name,
        track_name=track_name,
        is_public=team.is_public,
        status=team.status,
        created_at=team.created_at.isoformat(),
        competition_date=team.start_date.isoformat(),
        members=members
    )
    

async def get_team_manage_service(db: AsyncSession, lang: Language, team_id: str) -> RunningTeamManageResponse:
    team = await get_team_by_team_id(db, team_id)
    if team is None:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="team.not_found")
    if team.status == TeamStatus.completed:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="team.status_expired")
    if team.track is None:
        raise BizException(code=ErrorCode.TRACK_ERROR, message="track.not_found")
    if team.track.end_date < datetime.now(timezone.utc):
        raise BizException(code=ErrorCode.TEAM_ERROR, message="team.status_expired")
    members = [
        RunningTeamMemberInfo(
            member_id=m.member_id,
            user_id=m.user.user_id,
            nick_name=m.user.nickname if m.user else "未知",
            avatar_url=build_resource_url(m.user.avatar_image_url if m.user else "未知"),
            join_date=m.created_at.isoformat(),
            is_registered=m.is_registered,
            is_leader=m.is_leader
        )
        for m in team.members
    ]
    applied_members = [
        RunningTeamAppliedMemberInfo(
            member_id=m.member_id,
            user_id=m.user.user_id,
            nick_name=m.user.nickname if m.user else "未知",
            avatar_url=build_resource_url(m.user.avatar_image_url if m.user else "未知"),
            introduction=m.introduction,
            join_date=m.created_at.isoformat()
        )
        for m in team.applied_members
    ]
    region_id = team.track.event.region.region_id if team.track.event and team.track.event.region else "未知"
    event_name = pick_i18n_text(team.track.event.name_i18n, lang) if team.track.event else "未知"
    track_name = pick_i18n_text(team.track.name_i18n, lang)
    track_end_date = team.track.end_date.isoformat()
    return RunningTeamManageResponse(
        team_id=team.team_id,
        title=team.title,
        description=team.description,
        max_member_size=team.members_count_max,
        team_code=team.team_code,
        region_id=region_id,
        event_name=event_name,
        track_name=track_name,
        track_end_date=track_end_date,
        is_public=team.is_public,
        status=team.status,
        created_at=team.created_at.isoformat(),
        competition_date=team.start_date.isoformat(),
        members=members,
        request_members=applied_members
    )


async def _get_redis_leaderboard(key: str, start: int = 0, end: int = -1) -> List[tuple[str, str, float]]:
    members = await redis_client.zrange(key, start, end, withscores=True)
    results: List[tuple[str, str, float]] = []
    for member, duration_seconds in members:
        if ":" in member:
            user_id, record_id = member.split(":", 1)
        else:
            user_id, record_id = member, "None"
        results.append((user_id, record_id, float(duration_seconds)))
    return results

async def filtered_entries(db: AsyncSession, entries: List[tuple[str, str, float]], gender: Gender) -> List[tuple[str, str, float]]:
    filtered_result = []
    for user_id, record_id, duration in entries:
        user = await get_exist_user_by_id(db, user_id)
        record = await get_record_by_record_id(db, record_id)
        # 未实名注册以及与排行榜性别不符的用户无法结算
        if user is None or record is None or user.gender is None or user.gender != gender:
            continue
        filtered_result.append((user_id, record_id, duration))
    return filtered_result

async def settle_running_leaderboard_service(db: AsyncSession, track_id: str) -> tuple[int, int, int, int, int]:
    async with db.begin():
        track = await get_track_by_track_id(db, track_id)
        if track is None:
            raise BizException(code=ErrorCode.TRACK_ERROR, message="track.not_found")
        if track.end_date > datetime.now(timezone.utc):
            raise BizException(code=ErrorCode.TRACK_ERROR, message="赛道未结束，无法结算")
        if track.event is None or track.event.season is None:
            raise BizException(code=ErrorCode.TRACK_ERROR, message="track.data_error")
        if await track_has_settled(db, track.id):
            raise BizException(code=ErrorCode.TRACK_ERROR, message="赛道已被结算")

        male_key = f"leaderboard:running:{track.track_id}:male"
        female_key = f"leaderboard:running:{track.track_id}:female"
        # 读取Redis榜单
        male_entries = await _get_redis_leaderboard(male_key)
        female_entries = await _get_redis_leaderboard(female_key)

        # 过滤掉非法的记录
        male_filtered_entries = await filtered_entries(db, male_entries, Gender.male)
        female_filtered_entries = await filtered_entries(db, female_entries, Gender.female)

        total_participants = len(male_filtered_entries) + len(female_filtered_entries)
        if total_participants == 0:
            return 0, 0, 0

        # 奖金按人数比例在男女之间分配
        prize_pool = track.prize_pool
        base_score = track.score
        male_pool = int(prize_pool * (len(male_filtered_entries) / total_participants))
        female_pool = prize_pool - male_pool

        male_settled = _distribute_voucher_and_scores(male_pool, base_score, male_filtered_entries)
        female_settled = _distribute_voucher_and_scores(female_pool, base_score, female_filtered_entries)

        # 写入RunningLeaderboard、生成Mailbox、累加RunningCareerScore
        async def _write_leaderboard(db: AsyncSession, gender: Gender, settled: List[tuple[str, str, float, int, int, int]]):
            for user_id, record_id, duration, voucher, score, rank in settled:
                user = await get_exist_user_by_id(db, user_id)
                record = await get_record_by_record_id(db, record_id)
                if user is None or record is None or user.gender is None or user.gender != gender:
                    raise BizException(code=ErrorCode.TRACK_ERROR, message="结算失败")
                # leaderboard
                db.add(RunningLeaderboard(
                    track_id=track.id,
                    gender=gender,
                    rank_position=rank,
                    user_id=user.id,
                    record_id=record.id,
                    duration_seconds=duration,
                    reward={"voucher": voucher},
                    score=score,
                ))
                # career score & voucher
                await add_or_update_career_score(db, track.event.season.id, gender, user.id, score, voucher)
                # mailbox 奖金发放（领取时再入账）
                if voucher > 0:
                    db.add(Mailbox(
                        mail_id=f"mail_{uuid.uuid4()}",
                        user_id=user.id,
                        mail_type=MailType.REWARD,
                        title_i18n={"en": "Running race settlement", "zh-Hans": "跑步赛事结算", "zh-Hant": "跑步賽事結算", "ko": "달리기 경주 상금 정산", "ja": "ランニングレースリザルト", "fr": "Résultats de la course à pied"},
                        content_i18n={
                            "en": f"Congratulations on achieving rank {rank} in the {pick_i18n_text(track.event.name_i18n, Language.en)} - {pick_i18n_text(track.name_i18n, Language.en)} competition! Please claim your reward as soon as possible:", 
                            "zh-Hans": f"恭喜您在 {pick_i18n_text(track.event.name_i18n, Language.zh_hans)} - {pick_i18n_text(track.name_i18n, Language.zh_hans)} 比赛中获得第 {rank} 名，请尽快领取奖励:", 
                            "zh-Hant": f"恭喜您在 {pick_i18n_text(track.event.name_i18n, Language.zh_hant)} - {pick_i18n_text(track.name_i18n, Language.zh_hant)} 比賽中獲得第 {rank} 名，請盡快領取獎勵:",
                            "ko": f"{pick_i18n_text(track.event.name_i18n, Language.ko)} - {pick_i18n_text(track.name_i18n, Language.ko)} 대회에서 {rank}위를 달성하신 것을 진심으로 축하드립니다! 가능한 한 빨리 상품을 수령해 가세요:",
                            "ja": f"{pick_i18n_text(track.event.name_i18n, Language.ja)} - {pick_i18n_text(track.name_i18n, Language.ja)} の大会で第 {rank} 位を獲得しました。おめでとうございます！報酬をお早めにお受け取りください:",
                            "fr": f"Félicitations pour votre {rank}e place dans la compétition {pick_i18n_text(track.event.name_i18n, Language.fr)} - {pick_i18n_text(track.name_i18n, Language.fr)} ! Récupérez votre récompense dès que possible :"
                        },
                        attachment={"voucher": voucher, "description": "比赛结算奖励"},
                        is_read=False,
                        is_received=False,
                        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
                    ))

        await _write_leaderboard(db, Gender.male, male_settled)
        await _write_leaderboard(db, Gender.female, female_settled)

        # 清理 redis 排行榜
        await redis_client.delete(male_key)
        await redis_client.delete(female_key)
        # 实发奖励
        total_voucher = sum(item[-3] for item in male_settled) + sum(item[-3] for item in female_settled)
        return len(male_settled), len(male_entries), len(female_settled), len(female_entries), total_voucher


async def update_team_info_service(db: AsyncSession, user_id: str, info: RunningTeamUpdateInfo) -> RunningTeamUpdateResponse:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
    team = await get_team_by_team_id_for_update(db, info.team_id)
    if team is None:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="team.not_found")
    if team.status != TeamStatus.prepared:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="team.status_not_prepared.manage_team")
    # 验证用户是否是队伍成员
    user_member = next((member for member in team.members if member.user_id == user.id), None)
    if user_member is None:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="team.op_failed.manage_team")
    # 验证用户是否是队长
    if not user_member.is_leader:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="team.op_failed.manage_team")
    
    update_data = {
        "title": info.title,
        "description": info.description,
        "start_date": info.competition_date
    }
    await update_team_crud(db, team, update_data)
    await db.commit()
    return RunningTeamUpdateResponse(
        title=team.title,
        description=team.description,
        competition_date=team.start_date.isoformat()
    )


async def update_team_public_status_service(db: AsyncSession, user_id: str, info: RunningTeamStatusUpdateInfo) -> bool:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
    team = await get_team_by_team_id_for_update(db, info.team_id)
    if team is None:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="team.not_found")
    if team.status != TeamStatus.prepared:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="team.status_not_prepared.manage_team")
    # 验证用户是否是队伍成员
    user_member = next((member for member in team.members if member.user_id == user.id), None)
    if user_member is None:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="team.op_failed.manage_team")
    # 验证用户是否是队长
    if not user_member.is_leader:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="team.op_failed.manage_team")
    
    update_data = {
        "is_public": info.new_status
    }
    await update_team_crud(db, team, update_data)
    await db.commit()
    return team.is_public


async def update_team_lock_status_service(db: AsyncSession, user_id: str, info: RunningTeamStatusUpdateInfo) -> bool:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
    team = await get_team_by_team_id_for_update(db, info.team_id)
    if team is None:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="team.not_found")
    if team.status != TeamStatus.prepared and team.status != TeamStatus.locked:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="team.match_recording.manage_team")
    # 验证用户是否是队伍成员
    user_member = next((member for member in team.members if member.user_id == user.id), None)
    if user_member is None:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="team.op_failed.manage_team")
    # 验证用户是否是队长
    if not user_member.is_leader:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="team.op_failed.manage_team")
    
    update_data = {
        "status": TeamStatus.locked if info.new_status else TeamStatus.prepared
    }
    await update_team_crud(db, team, update_data)
    await db.commit()
    return team.status != TeamStatus.prepared


async def update_team_ready_status_service(db: AsyncSession, user_id: str, team_id: str) -> bool:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
    team = await get_team_by_team_id_for_update(db, team_id)
    if team is None:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="team.not_found")
    if team.status != TeamStatus.prepared and team.status != TeamStatus.locked:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="team.match_recording.manage_team")
    # 验证用户是否是队伍成员
    user_member = next((member for member in team.members if member.user_id == user.id), None)
    if user_member is None:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="team.op_failed.manage_team")
    # 验证用户是否是队长
    if not user_member.is_leader:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="team.op_failed.manage_team")
    # 确认队伍中所有members都已报名
    if any(not member.is_registered for member in team.members):
        raise BizException(code=ErrorCode.TEAM_ERROR, message="team.not_all_registered.manage_team")
    # 确认队伍中不存在applied_members
    if len(team.applied_members) > 0:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="team.not_all_settled.manage_team")
    if team.track is None:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="team.data_error")
    # 确认比赛时间的合法性:
    if team.start_date < datetime.now(timezone.utc) or team.start_date > team.track.end_date:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="team.invalid_match_time")
    # 确认队伍已锁定
    if team.status == TeamStatus.prepared:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="team.status_not_locked")
    # 禁止1人进行组队比赛
    if len(team.members) == 1:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="team.member_not_enough")
    
    update_data = {
        "status": TeamStatus.ready
    }
    await update_team_crud(db, team, update_data)
    await db.commit()
    return team.status != TeamStatus.prepared and team.status != TeamStatus.locked


async def disband_team_service(db: AsyncSession, user_id: str, team_id: str) -> CPAssetResponse:
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
        team = await get_team_by_team_id_for_update(db, team_id)
        if team is None:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.not_found")
        if team.status != TeamStatus.prepared:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.status_not_prepared.manage_team")
        if team.track is None or team.track.team_register_card_def is None:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.data_error")
        if team.track.end_date < datetime.now(timezone.utc):
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.status_expired")
        user_member = next((member for member in team.members if member.user_id == user.id), None)
        if user_member is None:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.op_failed.manage_team")
        if not user_member.is_leader:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.op_failed.manage_team")
        if user_member.is_registered:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.is_registered.quit_team")
        
        # 返回组队卡
        team_card_def = await get_team_card_def(db, SportType.running)
        new_balance = await reward_cpasset(db, user.id, team_card_def.id, 1, "解散队伍", AssetOperation.REFUND)
        # 所有已报名成员取消报名
        for member in team.members:
            if member.is_registered:
                await reward_cpasset(db, member.user_id, team.track.team_register_card_id, 1, "取消报名", AssetOperation.REFUND)
        await delete_records_by_team_id(db, team.id)
        await db.delete(team)
        return CPAssetResponse(
            asset_id=team_card_def.asset_id,
            new_balance=new_balance
        )
    

async def remove_team_member_service(db: AsyncSession, user_id: str, team_id: str, member_id: str) -> RunningTeamMembersResponse:
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
        team = await get_team_by_team_id_for_update(db, team_id)
        if team is None:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.not_found")
        if team.status != TeamStatus.prepared:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.status_not_prepared.manage_team")
        if team.track is None or team.track.team_register_card_def is None:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.data_error")
        if team.track.end_date < datetime.now(timezone.utc):
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.status_expired")
        user_member = next((member for member in team.members if member.user_id == user.id), None)
        member_need_delete = next((member for member in team.members if member.member_id == member_id), None)
        if member_need_delete is None:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.not_in_members.manage_team")
        if member_need_delete.user_id == user.id:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.op_failed.manage_team")
        if user_member is None:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.op_failed.manage_team")
        if not user_member.is_leader:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.op_failed.manage_team")
        # 若已报名则自动取消报名
        if member_need_delete.is_registered:
            record = await get_record_by_team_id_and_user_id(db, team.id, member_need_delete.user_id)
            if record is not None and record.status == RecordStatus.notStarted:
                await delete_record_crud(db, record)
                await reward_cpasset(db, member_need_delete.user_id, team.track.team_register_card_id, 1, "取消报名", AssetOperation.REFUND)
        await db.delete(member_need_delete)
        await db.flush()
        await db.refresh(team, attribute_names=["members"])
        members = [RunningTeamMemberInfo(
            member_id=member.member_id,
            user_id=member.user.user_id,
            nick_name=member.user.nickname if member.user else "未知",
            avatar_url=build_resource_url(member.user.avatar_image_url if member.user else "未知"),
            join_date=member.created_at.isoformat(),
            is_registered=member.is_registered,
            is_leader=member.is_leader
        ) for member in team.members]
        return RunningTeamMembersResponse(members=members)


async def reject_applied_request_service(db: AsyncSession, user_id: str, team_id: str, member_id: str):
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
        team = await get_team_by_team_id_for_update(db, team_id)
        if team is None:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.not_found")
        if team.status != TeamStatus.prepared:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.status_not_prepared.manage_team")
        if team.track is None:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.data_error")
        if team.track.end_date < datetime.now(timezone.utc):
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.status_expired")
        user_member = next((member for member in team.members if member.user_id == user.id), None)
        member_need_delete = next((member for member in team.applied_members if member.member_id == member_id), None)
        if member_need_delete is None:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.not_in_applied_members.manage_team")
        if member_need_delete.user_id == user.id:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.op_failed.manage_team")
        if user_member is None or not user_member.is_leader:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.op_failed.manage_team")
        await db.delete(member_need_delete)


async def approve_applied_request_service(db: AsyncSession, user_id: str, team_id: str, member_id: str) -> RunningTeamMembersResponse:
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
        team = await get_team_by_team_id_for_update(db, team_id)
        if team is None:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.not_found")
        if team.status != TeamStatus.prepared:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.status_not_prepared.manage_team")
        if team.track is None:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.data_error")
        if team.track.end_date < datetime.now(timezone.utc):
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.status_expired")
        user_member = next((member for member in team.members if member.user_id == user.id), None)
        member_need_delete = next((member for member in team.applied_members if member.member_id == member_id), None)
        if member_need_delete is None:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.not_in_applied_members.manage_team")
        if member_need_delete.user_id == user.id:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.op_failed.manage_team")
        if user_member is None or not user_member.is_leader:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.op_failed.manage_team")
        if len(team.members) >= team.members_count_max:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.member_fulled")
        new_member = RunningTeamMember(
            member_id=f"member_{uuid.uuid4()}",
            team_id=team.id,
            user_id=member_need_delete.user.id
        )
        await db.delete(member_need_delete)
        db.add(new_member)
        await db.flush()
        await db.refresh(team, attribute_names=["members"])
        members = [RunningTeamMemberInfo(
            member_id=member.member_id,
            user_id=member.user.user_id,
            nick_name=member.user.nickname if member.user else "未知",
            avatar_url=build_resource_url(member.user.avatar_image_url if member.user else "未知"),
            join_date=member.created_at.isoformat(),
            is_registered=member.is_registered,
            is_leader=member.is_leader
        ) for member in team.members]
        return RunningTeamMembersResponse(members=members)


async def quit_team_service(db: AsyncSession, user_id: str, team_id: str):
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
    team = await get_team_by_team_id_for_update(db, team_id)
    if team is None:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="team.not_found")
    if team.status != TeamStatus.prepared and team.status != TeamStatus.locked:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="team.match_recording.quit_team")
    user_member = next((member for member in team.members if member.user_id == user.id), None)
    if user_member is None:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="team.not_in_members")
    if user_member.is_leader:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="team.is_leader.quit_team")
    if user_member.is_registered:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="team.is_registered.quit_team")
    await db.delete(user_member)
    await db.commit()


async def join_team_service(db: AsyncSession, user_id: str, team_code: str):
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
        team = await get_active_team_by_code_for_update(db, team_code)
        if team is None:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.not_found")
        if any(member.user_id == user.id for member in team.members):
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.already_in_members")
        if team.status != TeamStatus.prepared:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.status_not_prepared.join_team")
        if team.track is None:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.data_error")
        if team.track.end_date < datetime.now(timezone.utc):
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.status_expired")
        if len(team.members) >= team.members_count_max:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.member_fulled")
        new_member = RunningTeamMember(
            member_id=f"member_{uuid.uuid4()}",
            team_id=team.id,
            user_id=user.id
        )
        await create_team_member_crud(db, new_member)


async def applied_join_team_service(db: AsyncSession, user_id: str, request: RunningTeamAppliedRequest):
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
        team = await get_team_by_team_id_for_update(db, request.team_id)
        if team is None:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.not_found")
        if any(member.user_id == user.id for member in team.members):
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.already_in_members")
        if any(member.user_id == user.id for member in team.applied_members):
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.already_in_applied_members")
        if team.status != TeamStatus.prepared:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.status_not_prepared.join_team")
        if team.track is None:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.data_error")
        if team.track.end_date < datetime.now(timezone.utc):
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.status_expired")
        if len(team.members) >= team.members_count_max:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.member_fulled")
        new_member = RunningTeamAppliedMember(
            member_id=f"member_{uuid.uuid4()}",
            team_id=team.id,
            user_id=user.id,
            introduction=request.introduction
        )
        db.add(new_member)


async def cancel_applied_join_team_service(db: AsyncSession, user_id: str, team_id: str):
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
        team = await get_team_by_team_id_for_update(db, team_id)
        if team is None:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.not_found")
        if team.track is None:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.data_error")
        if team.track.end_date < datetime.now(timezone.utc):
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.status_expired")
        member = next((member for member in team.applied_members if member.user_id == user.id), None)
        if member is None:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="team.not_in_applied_members")
        await db.delete(member)


async def get_record_detail_service(db: AsyncSession, lang: Language, record_id: str, viewer_id: str | None) -> RunningRecordDetailInfo:
    record = await get_record_by_record_id(db, record_id)
    if record is None:
        raise BizException(code=ErrorCode.RECORD_ERROR, message="record.not_found")
    await ensure_record_detail_visible(db, record.user, viewer_id)
    
    # 构建MemberScoreInfo列表
    team_member_scores_list = []
    if record.team_id:
        member_records = await get_records_by_team_id(db, record.team_id)
        for member_record in member_records:
            team_member_scores_list.append(MemberScoreInfo(
                user_info=PersonInfoResponse(
                    user_id=member_record.user.user_id,
                    avatar_image_url=build_resource_url(member_record.user.avatar_image_url),
                    nickname=member_record.user.nickname
                ),
                status=member_record.status, final_time=member_record.duration_seconds))
    
    # 构建CardBonusInfo列表
    card_bonus_list = []
    raw_duration = (record.end_time - record.start_time).total_seconds() if record.end_time and record.start_time else 0
    for card_bonus in record.card_bonus:
        if card_bonus.card and card_bonus.card.user:
            card_info = equip_card_to_base_info(card_bonus.card, lang)
            ratio_bonus = card_bonus.bonus_ratio * raw_duration if card_bonus.bonus_ratio else 0
            if card_info is not None:
                card_bonus_list.append(
                    CardBonusInfo(
                        card=card_info,
                        bonus_time=card_bonus.bonus_time + ratio_bonus,
                        user_id=card_bonus.card.user.user_id
                    )
                )
    
    # 构建路径点列表
    path_points = []
    if record.path and record.path.path:
        try:
            for point_data in record.path.path:
                # 注意兼容新旧数据格式
                path_points.append(RunningPathPoint.model_validate(point_data))
        except Exception:
            logger.exception("Handle path data failed in querying running match record detail info")
    
    # 计算时间
    original_time = 0.0
    final_time = 0.0
    if record.start_time and record.end_time:
        original_time = (record.end_time - record.start_time).total_seconds()
    if record.duration_seconds is not None:
        final_time = float(record.duration_seconds)
    
    return RunningRecordDetailInfo(
        owner_user_id=record.user.user_id,
        status=record.status,
        original_time=original_time,
        final_time=final_time,
        penalty_time=record.penalty_seconds if record.penalty_seconds else 0,
        end_time=record.end_time,
        is_finish_computed=record.is_finish_bonus_computing if record.is_finish_bonus_computing else False,
        path=path_points,
        card_bonus=card_bonus_list,
        team_member_scores=team_member_scores_list,
        settlements=record.settlement_rewards,
        familiarity_time=record.familiarity_time if record.familiarity_time else 0,
        training_state_time=record.training_state_time if record.training_state_time else 0,
        weather=weather_snapshot_from_record(record)
    )


async def get_record_pace_snapshot_service(db: AsyncSession, record_id: str, user_id: str) -> PaceSnapshotResponse | None:
    """仅记录所有者可读取冻结后的水印配速快照。"""
    record = await get_record_by_record_id(db, record_id)
    if record is None:
        raise BizException(code=ErrorCode.RECORD_ERROR, message="record.not_found")
    if record.user is None or record.user.user_id != user_id:
        raise BizException(code=ErrorCode.NO_PERMISSION, message="record.access_denied")
    if record.pace_snapshot_id is None:
        return None
    snapshot = await db.get(VideoWatermarkPaceSnapshot, record.pace_snapshot_id)
    return PaceSnapshotResponse.model_validate(snapshot.snapshot) if snapshot else None

async def get_current_best_records_service(db: AsyncSession, lang: Language, user_id: str) -> RunningSummaryRecordResponse:
    season = await get_season_now(db)
    if not season:
        return RunningSummaryRecordResponse(records=[])
    events = await get_active_events_by_season_id(db, season.id)
    records = []
    for event in events:
        for track in event.tracks:
            if track.start_date < datetime.now(timezone.utc) and track.end_date > datetime.now(timezone.utc):
                rank_info = await query_user_rank_info(db, user_id, track.track_id)
                if rank_info.record_id and event.region:
                    records.append(RunningSummaryRecordInfo(
                        record_id=rank_info.record_id,
                        event_name=pick_i18n_text(event.name_i18n, lang),
                        track_name=pick_i18n_text(track.name_i18n, lang),
                        region_id=event.region.region_id,
                        best_time=rank_info.duration_seconds if rank_info.duration_seconds else 0,
                        rank=rank_info.rank if rank_info.rank else 0,
                        voucher=rank_info.reward_voucher_amount if rank_info.reward_voucher_amount else 0,
                        score=rank_info.score if rank_info.score else 0
                    ))
    return RunningSummaryRecordResponse(records=records)

async def get_career_records_service(db: AsyncSession, lang: Language, season_id: str, user_id: str) -> RunningCareerRecordResponse:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
    season = await get_season_by_season_id(db, season_id)
    if season is None:
        raise BizException(code=ErrorCode.SEASON_ERROR, message="season.not_found")
    records = []
    for event in season.running_events:
        for track in event.tracks:
            record = await get_leaderboad_record(db, track.id, user.id)
            if record and record.record:
                records.append(RunningCareerRecordInfo(
                    record_id=record.record.record_id,
                    track_id=track.track_id,
                    track_name=pick_i18n_text(track.name_i18n, lang),
                    event_name=pick_i18n_text(event.name_i18n, lang),
                    region_id=event.region.region_id,
                    track_score=track.score,
                    score=record.score,
                    record_date=record.record.end_time.isoformat()
                ))
    return RunningCareerRecordResponse(records=records)

async def get_career_data_service(db: AsyncSession, season_id: str, user_id: str) -> RunningCareerDataInfo:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
    season = await get_season_by_season_id(db, season_id)
    if not season:
        raise BizException(code=ErrorCode.SEASON_ERROR, message="season.not_found")
    gender = user.gender if user.gender else Gender.male
    statistic_data = await get_career_statistic_data(db, season.id, user.id)
    score, rank, voucher_bonus, xp = await get_score_and_rank_by_season_id_and_user(db, season.id, user.id, gender)
    return RunningCareerDataInfo(
        total_score=score if score else 0, 
        total_rank=rank if rank else None, 
        total_voucher=voucher_bonus if voucher_bonus else 0,
        total_distance=statistic_data.total_distance if statistic_data else 0,
        total_time=statistic_data.total_time if statistic_data else 0,
        total_xp=xp if xp else 0
    )

async def query_daily_task_status_service(db: AsyncSession, user_id: str) -> DailyTaskResponse | None:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
    task = await get_daily_task(db, user)
    task_record = await get_today_task_record_by_user(db, user)
    if task:
        cpasset_def = await get_cpasset_def_by_id(db, task.reward_stage3_id)
        return DailyTaskResponse(
            type=task.type,
            total_progress=task.total_progress,
            reward_stage1_type=task.reward_stage1_type,
            reward_stage1=task.reward_stage1,
            is_reward1_received=task_record.is_reward1_received if task_record else False,
            reward_stage2_type=task.reward_stage2_type,
            reward_stage2=task.reward_stage2,
            is_reward2_received=task_record.is_reward2_received if task_record else False,
            reward_stage3_url=build_resource_url(cpasset_def.image_url),
            is_reward3_received=task_record.is_reward3_received if task_record else False,
            progress=task_record.progress if task_record else 0
        ) if cpasset_def else None
    else:
        return None

async def claimed_daily_task_reward_service(db: AsyncSession, user_id: str, stage: int) -> DailyTaskRewardResponse:
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
        if stage < 1 or stage > 3:
            raise BizException(code=ErrorCode.REWARD_CLAIM_FAILED, message="reward.data_error")
        task = await get_daily_task(db, user)
        task_record = await get_today_task_record_by_user(db, user)
        if task is None or task_record is None:
            raise BizException(code=ErrorCode.REWARD_CLAIM_FAILED, message="reward.data_error")
        if stage == 1 and (task_record.progress / task.total_progress > 1/3):
            new_balance = await reward_ccasset(db, task.reward_stage1_type, task.reward_stage1, user.id, "每日任务奖励", AssetOperation.REWARD)
            task_record.is_reward1_received = True
            return DailyTaskRewardResponse(
                ccasset_type=task.reward_stage1_type,
                ccasset_amount=new_balance,
                cpasset_id=None,
                cpasset_amount=None
            )
        if stage == 2 and (task_record.progress / task.total_progress > 2/3):
            new_balance = await reward_ccasset(db, task.reward_stage2_type, task.reward_stage2, user.id, "每日任务奖励", AssetOperation.REWARD)
            task_record.is_reward2_received = True
            return DailyTaskRewardResponse(
                ccasset_type=task.reward_stage2_type,
                ccasset_amount=new_balance,
                cpasset_id=None,
                cpasset_amount=None
            )
        if stage == 3 and task_record.progress > task.total_progress:
            new_balance = await reward_cpasset(db, user.id, task.reward_stage3_id, 1, "每日任务奖励", AssetOperation.REWARD)
            task_record.is_reward3_received = True
            cpasset_def = await get_cpasset_def_by_id(db, task.reward_stage3_id)
            return DailyTaskRewardResponse(
                ccasset_type=None,
                ccasset_amount=None,
                cpasset_id=cpasset_def.asset_id if cpasset_def else None,
                cpasset_amount=new_balance
            )
        raise BizException(code=ErrorCode.REWARD_CLAIM_FAILED, message="reward.data_error")

async def start_competition_with_team_bonus_card_service(db: AsyncSession, user_id: str, record_id: str, card_id: str):
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
    record = await get_record_by_record_id(db, record_id)
    if record is None:
        raise BizException(code=ErrorCode.RECORD_ERROR, message="record.not_found")
    if record.team_id is None:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="team.not_found")
    card = await get_equip_card_by_card_id(db, card_id)
    if card is None:
        raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.not_found")
    new_bonus_record = RunningBonusByTeamMember(
        team_id=record.team_id,
        user_id=user.id,
        card_id=card.id
    )
    db.add(new_bonus_record)
    await db.commit()

async def finish_competition_with_team_bonus_card_service(
    db: AsyncSession, 
    user: User,
    team_id: uuid.UUID, 
    info: TeamMagicCardBonusInfo
):
    bonus_records = await get_bonus_record_with_team_magic_card_for_update(db, team_id)
    is_all_completed = True
    for br in bonus_records:
        if br.user_id == user.id:
            br.is_applied = True
        if br.user_id != user.id and not br.is_applied:
            is_all_completed = False
            
    records = await get_records_by_team_id_for_update(db, team_id)
    for r in records:
        if r.user_id != user.id:
            card = await get_equip_card_by_card_id(db, info.card_id)
            if card is not None:
                db.add(CardBonusInRunningRecord(
                    record_id=r.id,
                    card_id=card.id,
                    bonus_ratio=info.bonus_ratio,
                    bonus_time=info.bonus_seconds if info.bonus_seconds else 0
                ))
            # 已结束需要手动应用 bonus
            if r.duration_seconds and r.start_time and r.end_time:
                raw_duration = (r.end_time - r.start_time).total_seconds()
                if info.bonus_ratio:
                    r.duration_seconds -= info.bonus_ratio * raw_duration
                r.duration_seconds -= info.bonus_seconds if info.bonus_seconds else 0
                r.duration_seconds = max(raw_duration * 0.8, r.duration_seconds)
            if is_all_completed:
                r.is_finish_bonus_computing = True
                if r.status == RecordStatus.completed:
                    await send_running_match_rewards(db, r)
                    await update_running_leaderboard_for_record(r)
                    if r.user and r.path and r.path.path and r.duration_seconds:
                        points = [RunningPathPoint.model_validate(p) for p in r.path.path]
                        distance = compute_distance([p.base for p in points])
                        await add_or_update_daily_task_record(db, r.user, distance, r.duration_seconds)
                        if r.track and r.track.event and r.track.event.season:
                            await add_or_update_career_statistic_data(db, r.track.event.season.id, r.user.id, distance, r.duration_seconds)

async def query_record_familiarity_service(db: AsyncSession, user_id: str, record_id: str) -> float:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
    record = await get_record_by_record_id(db, record_id)
    if record is None:
        raise BizException(code=ErrorCode.RECORD_ERROR, message="record.not_found")
    familiarity = await get_familiarity_by_track_and_user(db, record.track, user.id)
    return familiarity


async def query_track_familiarity_service(db: AsyncSession, user_id: str, track_id: str) -> float:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
    track = await get_track_by_track_id(db, track_id)
    if track is None:
        raise BizException(code=ErrorCode.TRACK_ERROR, message="track.not_found")
    familiarity = await get_familiarity_by_track_and_user(db, track, user.id)
    return familiarity

async def query_tracks_user_info_service(db: AsyncSession, user_id: str, track_ids: List[str]) -> List[RunningTrackUserInfo]:
    """批量查询一组赛道的用户态信息（熟悉度 + 我的排名），供列表分页后一次性填充。"""
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")

    # 批量取赛道，避免逐条查询；user 已查到，透传给 rank 查询省去重复
    tracks = await get_tracks_by_track_ids(db, track_ids)
    track_map = {track.track_id: track for track in tracks}

    infos: List[RunningTrackUserInfo] = []
    for track_id in track_ids:
        track = track_map.get(track_id)
        if track is None:
            continue
        familiarity = await get_familiarity_by_track_and_user(db, track, user.id)
        rank_info = await query_user_rank_info(db, user_id, track_id, user=user)
        infos.append(RunningTrackUserInfo(
            track_id=track_id,
            familiarity=familiarity,
            rank_info=rank_info
        ))
    return infos

async def get_track_pace_baseline_service(db: AsyncSession, record_id: str, user_id: str) -> PaceBaselineResponse:
    """开赛基线：该赛道（按 gender 桶）排行榜成绩 + 调用者 PB race 记录的 split profile。入参为当前比赛 record_id。"""
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
    record = await get_record_by_record_id(db, record_id)
    if record is None or record.track is None:
        raise BizException(code=ErrorCode.TRACK_ERROR, message="track.not_found")
    gender = (user.gender or Gender.male).value
    finish_times = await get_track_leaderboard_times("running", record.track.track_id, gender)
    pb = await get_user_best_race_profile(db, record.track_id, user.id)
    return PaceBaselineResponse(
        finish_times=finish_times,
        pb_profile=SplitProfileInfo(**pb) if pb else None
    )
