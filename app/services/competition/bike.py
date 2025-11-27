from curses import raw
from app.crud.competition.common import get_region_by_name
from app.crud.competition.bike import (
    get_event_by_event_id, get_event_by_name, get_event_by_season_id_and_region_id,
    get_track_by_name, get_track_by_track_id, get_track_by_event_id,
    create_event_crud, create_track_crud, update_event_crud, update_track_crud,
    query_events_crud, query_tracks_crud, get_track_by_track_id_for_update,
    create_record_crud, get_record_by_record_id, update_record_crud,
    create_season_crud, get_season_by_season_id, update_season_crud, 
    get_season_now, get_season_by_name, get_active_events_by_season_id,
    delete_record_crud, create_team_crud, get_team_by_code_for_update,
    get_created_teams_by_user_id, get_applied_teams_by_user_id, get_joined_teams_by_user_id,
    get_team_by_team_id, create_team_member_crud, update_team_crud, delete_records_by_team_id,
    get_team_by_id_for_update, get_team_by_team_id_for_update, get_record_by_team_id_and_user_id,
    get_public_teams_by_track_id, get_records_by_team_id_for_update, get_records_by_team_id,
    track_has_settled, get_history_seasons, get_leaderboad_record, get_leaderboad_records_in_page,
    get_scores_in_page, add_or_update_career_score, get_score_and_rank_by_season_id_and_user,
    get_incompleted_records_by_user_id, get_completed_records_by_user_id, get_career_statistic_data,
    add_or_update_career_statistic_data, get_daily_task, get_today_task_record_by_user,
    add_or_update_daily_task_record, get_unverified_records, get_bonus_record_with_team_magic_card_for_update,
    get_record_by_record_id_for_update, get_team_id_by_record_id
)
from app.crud.asset_manage import (
    get_cpasset_def_by_id, get_register_card_price, get_registration_card_def, consume_cpasset, reward_ccasset,
    reward_cpasset, get_team_card_def, get_equip_card_by_card_id
)
from app.crud.user import get_user_by_id, get_users_by_ids, get_users_by_user_ids, get_exist_user_by_id
from app.core.errors import ErrorCode
from app.schemas.user import Gender
from app.schemas.base import BizException
from app.schemas.common import PersonInfoResponse, EquipCardBaseInfo, SportType
from app.services.mappers import equip_card_to_base_info
from app.services.competition.common import _distribute_voucher_and_scores, compute_distance
from app.schemas.asset import AssetOperation, CPAssetResponse, DailyTaskRewardResponse
from app.schemas.mailbox import MailType
from app.schemas.competition.common import (
    TeamRelationship, RecordStatus, TeamStatus, CardBonusInfo, 
    MemberScoreInfo, DailyTaskResponse, TeamMagicCardBonusInfo
)
from app.schemas.competition.bike import (
    BikeEventCreateForm, BikeEventBaseInfo, BikeEventUpdateForm, BikeEventBaseInfoInternal,
    BikeTrackBaseInfo, BikeTrackCreateForm,
    BikeTrackUpdateForm, BikeTrackBaseInfoInternal, 
    BikeBeginInfo, BikeFinishInfo, BikeLeaderboardInfo, BikeLeaderboardResponse,
    BikeSeasonBaseInfo, BikeSeasonCreateForm, BikeRecordInfo, BikeSingleRegisterResponse, BikeRankInfo,
    BikeTeamCreateInfo, BikeTeamCreateResponse, BikeAppliedTeamInfo, BikeAppliedTeamResponse,
    BikeTeamInfo, BikeTeamResponse, BikeTeamDetailResponse, BikeTeamManageResponse, BikeTeamMemberInfo,
    BikeTeamAppliedMemberInfo, BikeTeamUpdateResponse, BikeTeamUpdateInfo, BikeRecordDetailInfo,
    BikeTeamStatusUpdateInfo, BikeTeamMembersResponse, BikeTeamAppliedRequest, BikeTeamExpiredResponse,
    BikeSummaryRecordResponse, BikeSummaryRecordInfo, BikeHistorySeasonResponse, BikeHistorySeasonInfo,
    BikeCareerRecordResponse, BikeCareerRecordInfo, BikeScoreLeaderboardInfo, BikeScoreLeaderboardResponse,
    BikeCareerDataInfo, BikePathPoint, BikeUnverifiedRecordInfo, BikeUnverifiedRecordResponse
)
from app.db.models.competition import (
    BikeEvent, BikeTrack, BikeRaceRecord, BikeSeason, BikeTeam, BikeTeamMember, BikeTeamAppliedMember,
    CardBonusInBikeRecord, BikeRacePath, BikeLeaderboard, BikeBonusByTeamMember
)
from app.db.session import redis_client
from sqlalchemy import select
from app.db.models.mailbox import Mailbox
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import uuid, json, logging

competition_logger = logging.getLogger("competition")
leaderboard_logger = logging.getLogger("leaderboard")

async def create_season_service(db: AsyncSession, season_create: BikeSeasonCreateForm, image_url: str) -> BikeSeasonBaseInfo:
    season = await get_season_by_name(db, season_create.name)
    if season is not None:
        raise BizException(code=ErrorCode.SEASON_ALREADY_EXIST, message="Bike赛季已存在,不可重复创建")
    season_id = f"season_{str(uuid.uuid4())[:8]}"
    new_season = BikeSeason(
        season_id=season_id,
        name=season_create.name,
        start_date=season_create.start_date,
        end_date=season_create.end_date,
        image_url=image_url
    )
    res = await create_season_crud(db, new_season)
    await db.commit()
    return BikeSeasonBaseInfo(
        season_id=res.season_id,
        name=res.name,
        start_date=res.start_date.isoformat(),
        end_date=res.end_date.isoformat(),
        image_url=res.image_url
    )


async def update_season_image_url(db: AsyncSession, season_id: str, image_url: str):
    existing_season = await get_season_by_season_id(db, season_id)
    if existing_season is None:
        raise BizException(code=ErrorCode.SEASON_NOT_FOUND, message="Bike赛季不存在")
    update_data = {
        "image_url": image_url
    }
    await update_season_crud(db, existing_season, update_data)
    await db.commit()


async def query_current_season_service(db: AsyncSession) -> BikeSeasonBaseInfo:
    seasons = await get_season_now(db)
    if not seasons:
        raise BizException(code=ErrorCode.SEASON_NOT_FOUND, message="当前没有进行中的Bike赛季")
    if len(seasons) > 1:
        raise BizException(code=ErrorCode.SEASON_NOT_UNIQUE, message="当前时间存在多个进行中的Bike赛季")
    season: BikeSeason = seasons[0]
    return BikeSeasonBaseInfo(
        season_id=season.season_id,
        name=season.name,
        start_date=season.start_date.isoformat(),
        end_date=season.end_date.isoformat(),
        image_url=season.image_url
    )

async def get_history_seasons_service(db: AsyncSession) -> BikeHistorySeasonResponse:
    seasons = await get_history_seasons(db)
    response = []
    for season in seasons:
        response.append(BikeHistorySeasonInfo(
            season_id=season.season_id,
            season_name=season.name
        ))
    return BikeHistorySeasonResponse(seasons=response)

async def create_event_service(db: AsyncSession, event_form: BikeEventCreateForm, image_url: str) -> BikeEventBaseInfoInternal:
    region = await get_region_by_name(db, event_form.region_name)
    if region is None:
        raise BizException(code=ErrorCode.REGION_NOT_FOUND, message="地理区域不存在")

    season = await get_season_by_name(db, event_form.season_name)
    if season is None:
        raise BizException(code=ErrorCode.SEASON_NOT_FOUND, message="赛季不存在")
    if event_form.start_date < season.start_date or event_form.end_date > season.end_date or event_form.start_date > event_form.end_date:
        raise BizException(code=ErrorCode.EVENT_EEROR, message="赛事时间非法")

    event_id = f"event_{str(uuid.uuid4())[-12:]}"
    new_event = BikeEvent(
        event_id=event_id,
        name=event_form.name,
        description=event_form.description,
        start_date=event_form.start_date,
        end_date=event_form.end_date,
        region_id=region.id,
        season_id=season.id,
        image_url=image_url
    )
    res = await create_event_crud(db, new_event)
    await db.commit()
    return BikeEventBaseInfoInternal(
        event_id=res.event_id,
        name=res.name,
        description=res.description,
        start_date=res.start_date.isoformat(),
        end_date=res.end_date.isoformat(),
        season_name=res.season.name if res.season else "未知",
        region_name=res.region.name if res.region else "未知",
        image_url=res.image_url
    )


async def update_event_service(db: AsyncSession, event: BikeEventUpdateForm, image_url: str):
    existing_event = await get_event_by_event_id(db, event.event_id)
    if existing_event is None:
        raise BizException(code=ErrorCode.EVENT_NOT_FOUND, message="赛事不存在")
    if event.start_date < existing_event.season.start_date or event.end_date > existing_event.season.end_date or event.start_date > event.end_date:
        raise BizException(code=ErrorCode.EVENT_ERROR, message="赛事时间非法")
    update_data = {
        "name": event.name,
        "description": event.description,
        "start_date": event.start_date,
        "end_date": event.end_date,
        "image_url": image_url
    }
    await update_event_crud(db, existing_event, update_data)
    await db.commit()


async def update_event_image_url(db: AsyncSession, event_id: str, image_url: str):
    existing_event = await get_event_by_event_id(db, event_id)
    if existing_event is None:
        raise BizException(code=ErrorCode.EVENT_NOT_FOUND, message="赛事不存在")
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
) -> List[BikeEventBaseInfoInternal]:
    events = await query_events_crud(
        db=db,
        season_name=season_name,
        region_name=region_name,
        event_name=event_name,
        page=page,
        size=size
    )
    return [BikeEventBaseInfoInternal(
        event_id=e.event_id,
        name=e.name,
        description=e.description,
        start_date=e.start_date.isoformat(),
        end_date=e.end_date.isoformat(),
        season_name=e.season.name if e.season is not None else "未知",
        region_name=e.region.name if e.region is not None else "未知",
        image_url=e.image_url
    ) for e in events]


async def query_events_by_region(db: AsyncSession, region_name: str) -> List[BikeEventBaseInfo]:
    seasons = await get_season_now(db)
    if not seasons:
        raise BizException(code=ErrorCode.SEASON_NOT_FOUND, message="当前没有进行中的赛季")
    if len(seasons) > 1:
        raise BizException(code=ErrorCode.SEASON_NOT_UNIQUE, message="当前时间存在多个进行中的赛季")
    
    season = seasons[0]
    region = await get_region_by_name(db, region_name)
    if region is None:
        raise BizException(code=ErrorCode.REGION_NOT_FOUND, message="当前区域无赛事")
    
    events = await get_event_by_season_id_and_region_id(db, season_id=season.id, region_id=region.id)
    if not events:
        raise BizException(code=ErrorCode.REGION_NOT_FOUND, message="当前区域无赛事")
    return [BikeEventBaseInfo(
        event_id=e.event_id,
        name=e.name,
        description=e.description,
        start_date=e.start_date.isoformat(),
        end_date=e.end_date.isoformat(),
        image_url=e.image_url
    ) for e in events]


async def create_track_service(db: AsyncSession, track_form: BikeTrackCreateForm, image_url: str) -> BikeTrackBaseInfoInternal:
    event = await get_event_by_name(db, track_form.event_name)
    if event is None:
        raise BizException(code=ErrorCode.EVENT_NOT_FOUND, message="Bike赛事不存在")
    if track_form.start_date < event.start_date or track_form.end_date > event.end_date or track_form.start_date > track_form.end_date:
        raise BizException(code=ErrorCode.TRACK_ERROR, message="赛道时间非法")

    region = await get_region_by_name(db, track_form.region_name)
    if region is None:
        raise BizException(code=ErrorCode.REGION_NOT_FOUND, message="地理区域不存在")

    season = await get_season_by_name(db, track_form.season_name)
    if season is None:
        raise BizException(code=ErrorCode.SEASON_NOT_FOUND, message="Bike赛季不存在")

    track_id = f"track_{str(uuid.uuid4())[-12:]}"
    new_track = BikeTrack(
        track_id = track_id,
        name = track_form.name,
        start_date = track_form.start_date,
        end_date = track_form.end_date,
        event_id = event.id,
        from_lat = track_form.from_latitude,
        from_lng = track_form.from_longitude,
        from_radius = track_form.from_radius,
        to_lat = track_form.to_latitude,
        to_lng = track_form.to_longitude,
        to_radius = track_form.to_radius,
        elevation_difference = track_form.elevationDifference,
        sub_region_name = track_form.subRegioName,
        prize_pool = track_form.prizePool,
        score = track_form.score,
        terrain_type = track_form.terrain_type,
        image_url = image_url
    )
    res = await create_track_crud(db, new_track)
    await db.commit()
    
    return BikeTrackBaseInfoInternal(
        track_id=res.track_id,
        name=res.name,
        start_date=res.start_date.isoformat(),
        end_date=res.end_date.isoformat(),
        event_name=res.event.name if res.event else "未知",
        season_name=res.event.season.name if res.event and res.event.season else "未知",
        region_name=res.event.region.name if res.event and res.event.region else "未知",
        image_url=res.image_url,
        from_latitude=str(res.from_lat),
        from_longitude=str(res.from_lng),
        to_latitude=str(res.to_lat),
        to_longitude=str(res.to_lng),
        elevation_difference=str(res.elevation_difference),
        sub_region_name=res.sub_region_name,
        prize_pool=str(res.prize_pool),
        score=str(res.score),
        is_settled=False
    )


async def update_track_service(db: AsyncSession, track: BikeTrackUpdateForm, image_url: str):
    existing_track = await get_track_by_track_id(db, track.track_id)
    if existing_track is None:
        raise BizException(code=ErrorCode.TRACK_NOT_FOUND, message="赛道不存在")
    if track.start_date < existing_track.event.start_date or track.end_date > existing_track.event.end_date or track.start_date > track.end_date:
        raise BizException(code=ErrorCode.TRACK_ERROR, message="赛道时间非法")
    update_data = {
        "name": track.name,
        "start_date": track.start_date,
        "end_date": track.end_date,
        "from_lat": track.from_latitude,
        "from_lng": track.from_longitude,
        "from_radius": track.from_radius,
        "to_lat": track.to_latitude,
        "to_lng": track.to_longitude,
        "to_radius": track.to_radius,
        "elevation_difference": track.elevationDifference,
        "sub_region_name": track.subRegioName,
        "prize_pool": track.prizePool,
        "score": track.score,
        "terrain_type": track.terrain_type,
        "image_url": image_url
    }
    await update_track_crud(db, existing_track, update_data)
    await db.commit()


async def update_track_image_url(db: AsyncSession, track_id: str, image_url: str):
    existing_track = await get_track_by_track_id(db, track_id)
    if existing_track is None:
        raise BizException(code=ErrorCode.TRACK_NOT_FOUND, message="赛道不存在")
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
) -> List[BikeTrackBaseInfoInternal]:
    tracks = await query_tracks_crud(
        db=db,
        track_name=track_name,
        event_name=event_name,
        season_name=season_name,
        region_name=region_name,
        page=page,
        size=size
    )
    return [BikeTrackBaseInfoInternal(
        track_id=t.track_id,
        name=t.name,
        start_date=t.start_date.isoformat(),
        end_date=t.end_date.isoformat(),
        event_name=t.event.name if t.event else "未知",
        season_name=t.event.season.name if t.event and t.event.season else "未知",
        region_name=t.event.region.name if t.event and t.event.region else "未知",
        image_url=t.image_url,
        from_latitude=str(t.from_lat),
        from_longitude=str(t.from_lng),
        from_radius=t.from_radius,
        to_latitude=str(t.to_lat),
        to_longitude=str(t.to_lng),
        to_radius=t.to_radius,
        elevation_difference=str(t.elevation_difference),
        sub_region_name=t.sub_region_name,
        prize_pool=str(t.prize_pool),
        score=str(t.score),
        terrain_type=t.terrain_type,
        is_settled=is_settled
    ) for t, is_settled in tracks]


async def query_tracks_by_event(db: AsyncSession, event_id: str) -> List[BikeTrackBaseInfo]:
    event = await get_event_by_event_id(db, event_id)
    if event is None:
        raise BizException(code=ErrorCode.EVENT_NOT_FOUND, message="赛事不存在")
    tracks = await get_track_by_event_id(db, event.id)
    results = []
    for t in tracks:
        male_key = f"leaderboard:bike:{t.track_id}:male"
        female_key = f"leaderboard:bike:{t.track_id}:female"

        male_count = await redis_client.zcard(male_key)
        female_count = await redis_client.zcard(female_key)
        total_count = male_count + female_count

        results.append(BikeTrackBaseInfo(
            track_id=t.track_id,
            name=t.name,
            start_date=t.start_date.isoformat(),
            end_date=t.end_date.isoformat(),
            image_url=t.image_url,
            from_latitude=t.from_lat,
            from_longitude=t.from_lng,
            from_radius=t.from_radius,
            to_latitude=t.to_lat,
            to_longitude=t.to_lng,
            to_radius=t.to_radius,
            elevation_difference=t.elevation_difference,
            sub_region_name=t.sub_region_name,
            prize_pool=t.prize_pool,
            score=t.score,
            totalParticipants=total_count,
            terrain_type=t.terrain_type,
        ))
    return results


async def single_register_service(db: AsyncSession, track_id: str, user_id: str) -> BikeSingleRegisterResponse:
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
        track = await get_track_by_track_id(db, track_id)
        if track is None:
            raise BizException(code=ErrorCode.TRACK_NOT_FOUND, message="赛道不存在")
        if track.start_date > datetime.now(timezone.utc):
            raise BizException(code=ErrorCode.RECORD_ERROR, message="比赛未开始")
        if track.end_date < datetime.now(timezone.utc):
            raise BizException(code=ErrorCode.RECORD_ERROR, message="比赛已结束")
        # 消费报名卡
        registrarion_card_def = await get_registration_card_def(db, SportType.bike, False)
        new_balance = await consume_cpasset(db, user.id, registrarion_card_def.id, 1, "自行车赛事报名")
        # 创建record
        record_id = f"record_{uuid.uuid4()}"
        new_record = BikeRaceRecord (
            record_id = record_id,
            user_id = user.id,
            track_id = track.id
        )
        record = await create_record_crud(db, new_record)
        record_info = BikeRecordInfo(
            record_id=record.record_id,
            region_name=record.track.event.region.name if record.track and record.track.event and record.track.event.region else "未知",
            event_name=record.track.event.name if record.track and record.track.event else "未知",
            track_name=record.track.name if record.track else "未知",
            track_start_lat=record.track.from_lat if record.track else -1,
            track_start_lng=record.track.from_lng if record.track else -1,
            track_start_radius=record.track.from_radius if record.track else 10,
            track_end_lat=record.track.to_lat if record.track else -1,
            track_end_lng=record.track.to_lng if record.track else -1,
            track_end_radius=record.track.to_radius if record.track else 10,
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
        return BikeSingleRegisterResponse(
            record=record_info,
            asset_id=registrarion_card_def.asset_id,
            new_balance=new_balance
        )


async def team_register_service(db: AsyncSession, team_code: str, user_id: str) -> CPAssetResponse:
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
        team = await get_team_by_code_for_update(db, team_code)
        if team is None:
            raise BizException(code=ErrorCode.TEAM_NOT_FOUND, message="队伍不存在")
        if team.track is None:
            raise BizException(code=ErrorCode.TRACK_NOT_FOUND, message="赛道不存在")
        if team.track.start_date > datetime.now(timezone.utc):
            raise BizException(code=ErrorCode.RECORD_ERROR, message="比赛未开始")
        if team.track.end_date < datetime.now(timezone.utc):
            raise BizException(code=ErrorCode.RECORD_ERROR, message="比赛已结束")
        
        user_member = next((member for member in team.members if member.user_id == user.id), None)
        if user_member is None:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="您不在队伍中")
        if user_member.is_registered:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="请勿重复报名")

        # 消费报名卡
        registrarion_card_def = await get_registration_card_def(db, SportType.bike, True)
        new_balance = await consume_cpasset(db, user.id, registrarion_card_def.id, 1, "自行车赛事报名")

        record_id = f"record_{uuid.uuid4()}"
        new_record = BikeRaceRecord (
            record_id = record_id,
            user_id = user.id,
            track_id = team.track.id,
            team_id = team.id
        )
        await create_record_crud(db, new_record)
        user_member.is_registered = True
        return CPAssetResponse(
            asset_id=registrarion_card_def.asset_id,
            new_balance=new_balance
        )


async def get_incompleted_records_all(
    db: AsyncSession, 
    user_id: str,
    page: int,
    size: int
) -> List[BikeRecordInfo]:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
    records = await get_incompleted_records_by_user_id(db, user.id, page, size)
    return [BikeRecordInfo(
        record_id=r.record_id,
        region_name=r.track.event.region.name if r.track and r.track.event and r.track.event.region else "未知",
        event_name=r.track.event.name if r.track and r.track.event else "未知",
        track_name=r.track.name if r.track else "未知",
        track_start_lat=r.track.from_lat if r.track else -1,
        track_start_lng=r.track.from_lng if r.track else -1,
        track_start_radius=r.track.from_radius if r.track else 10,
        track_end_lat=r.track.to_lat if r.track else -1,
        track_end_lng=r.track.to_lng if r.track else -1,
        track_end_radius=r.track.to_radius if r.track else 10,
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
    user_id: str,
    page: int,
    size: int
) -> List[BikeRecordInfo]:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
    records = await get_completed_records_by_user_id(db, user.id, page, size)
    return [BikeRecordInfo(
        record_id=r.record_id,
        region_name=r.track.event.region.name if r.track and r.track.event and r.track.event.region else "未知",
        event_name=r.track.event.name if r.track and r.track.event else "未知",
        track_name=r.track.name if r.track else "未知",
        track_start_lat=r.track.from_lat if r.track else -1,
        track_start_lng=r.track.from_lng if r.track else -1,
        track_start_radius=r.track.from_radius if r.track else 10,
        track_end_lat=r.track.to_lat if r.track else -1,
        track_end_lng=r.track.to_lng if r.track else -1,
        track_end_radius=r.track.to_radius if r.track else 10,
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
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
        record = await get_record_by_record_id(db, record_id)
        if record is None:
            raise BizException(code=ErrorCode.RECORD_NOT_FOUND, message="记录不存在")
        if record.user_id != user.id:
            raise BizException(code=ErrorCode.RECORD_ERROR, message="无权限,取消失败")
        if record.status == RecordStatus.recording:
            raise BizException(code=ErrorCode.RECORD_ERROR, message="比赛在进行中,无法取消")
        if record.status == RecordStatus.completed:
            raise BizException(code=ErrorCode.RECORD_ERROR, message="比赛已结束,无法取消")
        if record.track is None:
            raise BizException(code=ErrorCode.TRACK_NOT_FOUND, message="赛道不存在")
        if record.track.end_date < datetime.now(timezone.utc):
            raise BizException(code=ErrorCode.RECORD_ERROR, message="比赛已结束,无法取消")
        
        is_team = record.team_id is not None
        team = None
        if is_team:
            team = await get_team_by_id_for_update(db, record.team_id)
            if team.status in [TeamStatus.ready, TeamStatus.recording, TeamStatus.completed]:
                raise BizException(code=ErrorCode.TEAM_ERROR, message="队伍处于比赛状态,无法取消")

        cpasset_def = await get_registration_card_def(db, SportType.bike, is_team)
        new_balance = await reward_cpasset(db, user.id, cpasset_def.id, 1, "取消报名", AssetOperation.REFUND)
        if is_team:
            user_member = next((member for member in team.members if member.user_id == user.id), None)
            if user_member is None:
                raise BizException(code=ErrorCode.TEAM_ERROR, message="您不在队伍中")
            if not user_member.is_registered:
                raise BizException(code=ErrorCode.RECORD_ERROR, message="请勿重复取消")
            user_member.is_registered = False
        await delete_record_crud(db, record)
        return CPAssetResponse(
            asset_id=cpasset_def.asset_id,
            new_balance=new_balance
        )


async def enter_team_competition_link_service(db: AsyncSession, record_id: str):
    record = await get_record_by_record_id(db, record_id)
    if record is None:
        raise BizException(code=ErrorCode.RECORD_NOT_FOUND, message="记录不存在")
    if record.track is None:
        raise BizException(code=ErrorCode.TRACK_NOT_FOUND, message="赛道不存在")
    if record.track.end_date < datetime.now(timezone.utc):
        raise BizException(code=ErrorCode.RECORD_ERROR, message="比赛已结束")
    if record.team is None:
        raise BizException(code=ErrorCode.TEAM_NOT_FOUND, message="队伍不存在")
    if record.team.status != TeamStatus.ready and record.team.status != TeamStatus.recording:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="队伍不在比赛状态")
    if record.team.start_date > datetime.now(timezone.utc) or datetime.now(timezone.utc) > record.team.start_date + timedelta(hours=2):
        raise BizException(code=ErrorCode.RECORD_ERROR, message="不在比赛有效时间内")


async def start_single_competition_service(db: AsyncSession, user_id: str, info: BikeBeginInfo):
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
    record = await get_record_by_record_id(db, info.record_id)
    if record is None:
        raise BizException(code=ErrorCode.RECORD_NOT_FOUND, message="记录不存在")
    if record.user_id != user.id:
        raise BizException(code=ErrorCode.RECORD_ERROR, message="无权限,无法开始比赛")
    if record.status != RecordStatus.notStarted:
        raise BizException(code=ErrorCode.RECORD_ERROR, message="状态错误,无法开始比赛")
    if record.track is None:
        raise BizException(code=ErrorCode.TRACK_NOT_FOUND, message="赛道不存在")
    if record.track.end_date < info.start_time:
        raise BizException(code=ErrorCode.RECORD_ERROR, message="比赛已结束")
    update_data = {
        "status": RecordStatus.recording,
        "start_time": info.start_time
    }
    await update_record_crud(db, record, update_data)
    await db.commit()


async def start_team_competition_service(db: AsyncSession, user_id: str, info: BikeBeginInfo):
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
        record = await get_record_by_record_id(db, info.record_id)
        if record is None:
            raise BizException(code=ErrorCode.RECORD_NOT_FOUND, message="记录不存在")
        if record.user_id != user.id:
            raise BizException(code=ErrorCode.RECORD_ERROR, message="无权限,无法开始比赛")
        if record.status != RecordStatus.notStarted:
            raise BizException(code=ErrorCode.RECORD_ERROR, message="状态错误,无法开始比赛")
        if record.track is None:
            raise BizException(code=ErrorCode.TRACK_NOT_FOUND, message="赛道不存在")
        if record.track.end_date < info.start_time:
            raise BizException(code=ErrorCode.RECORD_ERROR, message="比赛已结束")
        if record.team_id is None:
            raise BizException(code=ErrorCode.RECORD_ERROR, message="您不在队伍中")
        
        team = await get_team_by_id_for_update(db, record.team_id)
        if team is None:
            raise BizException(code=ErrorCode.TEAM_NOT_FOUND, message="队伍不存在")
        if team.status == TeamStatus.ready and team.start_date_real is None:
            if info.start_time < team.start_date:
                raise BizException(code=ErrorCode.RECORD_ERROR, message="未到队伍比赛时间")
            if info.start_time > team.start_date + timedelta(hours=2):
                raise BizException(code=ErrorCode.RECORD_ERROR, message="已错过队伍比赛时间")
            team.start_date_real = info.start_time
            team.status = TeamStatus.recording
        elif team.status == TeamStatus.recording and team.start_date_real is not None:
            if info.start_time > team.start_date_real + timedelta(seconds=180) or info.start_time < team.start_date_real:
                raise BizException(code=ErrorCode.RECORD_ERROR, message="不在队伍比赛窗口期,无法加入")
        else:
            raise BizException(code=ErrorCode.RECORD_ERROR, message="队伍状态错误")

        update_data = {
            "status": RecordStatus.recording,
            "start_time": info.start_time
        }
        await update_record_crud(db, record, update_data)

# 插入新记录更新排行榜
async def update_leaderboard_for_record(
    record: BikeRaceRecord,
    user_id: str,
    gender: Gender
):
    try:
        key = f"leaderboard:bike:{record.track.track_id}:{gender.value}"
        if record.status != RecordStatus.completed or record.duration_seconds is None:
            raise BizException(code=ErrorCode.RECORD_ERROR, message="记录数据错误")
        if record.track is None:
            raise BizException(code=ErrorCode.TRACK_NOT_FOUND, message="赛道不存在")
        # 1. 查找旧成绩
        best_score = None
        best_member = None
        members = await redis_client.zrange(key, 0, -1, withscores=True)
        for m, score in members:
            if m.startswith(f"{user_id}:"):
                best_score = score
                best_member = m
                break  # 只会有一条
        # 2. 比较成绩
        if best_score is None or record.duration_seconds < best_score:
            if best_member:
                await redis_client.zrem(key, best_member)
            member = f"{user_id}:{record.record_id}"
            await redis_client.zadd(key, {member: record.duration_seconds})
    except Exception as e:
        # todo: 记录错误日志，后续由定时任务补偿
        leaderboard_logger.error(f"Failed to update leaderboard {key} for record {record.record_id}: {e}")

async def finish_single_competition_service(db: AsyncSession, info: BikeFinishInfo, user_id: str):
    try:
        async with db.begin():
            user = await get_user_by_id(db, user_id)
            if user is None:
                raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
            gender = user.real_name_info.gender if user.real_name_info else Gender.male
            record = await get_record_by_record_id(db, info.record_id)
            if record is None:
                raise BizException(code=ErrorCode.RECORD_NOT_FOUND, message="记录不存在")
            if record.track is None:
                raise BizException(code=ErrorCode.TRACK_NOT_FOUND, message="赛道不存在")
            if record.start_time is None or record.start_time > info.end_time:
                raise BizException(code=ErrorCode.RECORD_ERROR, message="比赛时间错误")
            if record.status != RecordStatus.recording and record.status != RecordStatus.expired:
                raise BizException(code=ErrorCode.RECORD_ERROR, message="比赛状态错误")
            final_time = (info.end_time - record.start_time).total_seconds()
            bonus_time = 0

            for item in info.bonus_in_cards:
                bonus_time += item.bonus_time
                card = await get_equip_card_by_card_id(db, item.card_id)
                if card is not None:
                    db.add(CardBonusInBikeRecord(
                        record_id=record.id,
                        card_id=card.id,
                        bonus_time=item.bonus_time
                    ))
            # 奖励时间上限为20%
            if bonus_time / final_time > 0.2:
                final_time = final_time * 0.8
            else:
                final_time -= bonus_time
            path_data = [p.model_dump() for p in info.path]
            path = BikeRacePath(
                path_id=f"path_{uuid.uuid4()}",
                record_id=record.id,
                path=path_data
            )
            db.add(path)
            await db.flush()  # 先flush，让对象持久化
            await db.refresh(path)  # 再refresh，获取数据库生成的值
            update_data = {
                "path_id": path.id,
                "end_time": info.end_time,
                "duration_seconds": final_time,
                "validation_score": info.validation_score,
                "is_finish_bonus_computing": True
            }
            if record.status == RecordStatus.recording:
                if info.validation_score >= 80:
                    update_data["status"] = RecordStatus.completed
                elif info.validation_score >= 50:
                    update_data["status"] = RecordStatus.toBeVerified
                else:
                    update_data["status"] = RecordStatus.invalid
            await update_record_crud(db, record, update_data)
            # 更新奖金池
            track = await get_track_by_track_id_for_update(db, record.track.track_id)
            if track is None or track.event is None or track.event.season is None:
                raise BizException(code=ErrorCode.TRACK_NOT_FOUND, message="赛道不存在")
            card_price = await get_register_card_price(db, SportType.bike, False)
            if card_price:
                track.prize_pool += card_price.price
            db.add(track)
            # 更新个人统计数据 & 每日任务进度
            if record.status == RecordStatus.completed:
                distance = compute_distance([p.base for p in info.path])
                await add_or_update_career_statistic_data(db, track.event.season.id, user.id, distance, final_time)
                await add_or_update_daily_task_record(db, user.id, distance, final_time)
    except Exception as e:
        competition_logger.error(f"finish single bike competition failed: {e}")
        return
    # 更新排行榜
    if record.duration_seconds is not None and record.status == RecordStatus.completed:
        await update_leaderboard_for_record(record, user_id, gender)


async def finish_team_competition_service(db: AsyncSession, info: BikeFinishInfo, user_id: str):
    try:
        async with db.begin():
            user = await get_user_by_id(db, user_id)
            if user is None:
                raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
            gender = user.real_name_info.gender if user.real_name_info else Gender.male

            # 先对 team 上锁
            team_id = await get_team_id_by_record_id(db, info.record_id)
            if not team_id:
                raise BizException(code=ErrorCode.RECORD_ERROR, message="您不在队伍中")
            team = await get_team_by_id_for_update(db, team_id)
            if team is None:
                raise BizException(code=ErrorCode.TEAM_NOT_FOUND, message="队伍不存在")
            
            record = None
            records_in_team = await get_records_by_team_id_for_update(db, team_id)
            for r in records_in_team:
                if r.user_id == user.id:
                    record = r

            if record is None:
                raise BizException(code=ErrorCode.RECORD_NOT_FOUND, message="记录不存在")
            if record.track is None:
                raise BizException(code=ErrorCode.TRACK_NOT_FOUND, message="赛道不存在")
            if record.start_time is None or record.start_time > info.end_time:
                raise BizException(code=ErrorCode.RECORD_ERROR, message="比赛时间错误")
            if record.status != RecordStatus.recording and record.status != RecordStatus.expired:
                raise BizException(code=ErrorCode.RECORD_ERROR, message="比赛状态错误")

            final_time = (info.end_time - record.start_time).total_seconds()
            bonus_time = 0

            # 待应用的 team bonus
            for bonus_info in record.card_bonus:
                #print(f"applied bonus: {bonus_info.bonus_time}")
                bonus_time += bonus_info.bonus_time
                if bonus_info.bonus_ratio:
                    bonus_time += final_time * bonus_info.bonus_ratio
            
            for item in info.bonus_in_cards:
                bonus_time += item.bonus_time
                card = await get_equip_card_by_card_id(db, item.card_id)
                if card is not None:
                    db.add(CardBonusInBikeRecord(
                        record_id=record.id,
                        card_id=card.id,
                        bonus_time=item.bonus_time
                    ))
            # 奖励时间上限为20%
            if bonus_time / final_time > 0.2:
                final_time = final_time * 0.8
            else:
                final_time -= bonus_time
            path_data = [p.model_dump() for p in info.path]
            path = BikeRacePath(
                path_id=f"path_{uuid.uuid4()}",
                record_id=record.id,
                path=path_data
            )
            db.add(path)
            await db.flush()
            await db.refresh(path)
            update_data = {
                "path_id": path.id,
                "end_time": info.end_time,
                "duration_seconds": final_time,
                "validation_score": info.validation_score
            }
            if record.status == RecordStatus.recording:
                if info.validation_score >= 80:
                    update_data["status"] = RecordStatus.completed
                elif info.validation_score >= 50:
                    update_data["status"] = RecordStatus.toBeVerified
                else:
                    update_data["status"] = RecordStatus.invalid
            await update_record_crud(db, record, update_data)

            # 如果其他队员都完成比赛则修改team状态
            all_completed = True if record.status != RecordStatus.notStarted and record.status != RecordStatus.recording else False
            for r in records_in_team:
                if r.user_id != user.id and (r.status == RecordStatus.notStarted or r.status == RecordStatus.recording):
                    all_completed = False
                    break
            if all_completed:
                team.status = TeamStatus.completed

            # 更新奖金池
            track = await get_track_by_track_id_for_update(db, record.track.track_id)
            if track is None or track.event is None or track.event.season is None:
                raise BizException(code=ErrorCode.TRACK_NOT_FOUND, message="赛道不存在")
            #print(f"prize pool before update: {track.prize_pool}")
            card_price = await get_register_card_price(db, SportType.bike, True)
            if card_price:
                track.prize_pool += card_price.price
            db.add(track)
            # 应用团队收益 & 更新个人统计数据 & 更新每日任务进度
            if record.status == RecordStatus.completed:
                if info.team_bonus:
                    await finish_competition_with_team_bonus_card_service(db, user.id, team_id, info.team_bonus)
                distance = compute_distance([p.base for p in info.path])
                await add_or_update_career_statistic_data(db, track.event.season.id, user.id, distance, final_time)
                await add_or_update_daily_task_record(db, user.id, distance, final_time)
    except Exception as e:
        competition_logger.error(f"finish team bike competition failed: {e}")
        return
    # 更新排行榜
    if record.duration_seconds is not None and record.status == RecordStatus.completed:
        await update_leaderboard_for_record(record, user_id, gender)


async def query_unverified_records_service(
    db: AsyncSession,
    page: int = 1,
    size: int = 10
) -> List[BikeUnverifiedRecordResponse]:
    records = await get_unverified_records(db, page, size)
    if not records:
        return BikeUnverifiedRecordResponse(records=[])
    infos = [BikeUnverifiedRecordInfo(
        is_vip=r.user.subscription_info.is_active if r.user.subscription_info else False,
        record_id=r.record_id,
        validation_score=r.validation_score,
        path=[BikePathPoint.model_validate(p) for p in r.path.path],
        finished_at=r.end_time.isoformat() if r.end_time else None
    ) for r in records if r.user and r.path]
    return BikeUnverifiedRecordResponse(records=infos)


async def handle_record_verified_service(db: AsyncSession, record_id: str, result: bool):
    async with db.begin():
        record = await get_record_by_record_id(db, record_id)
        if record is None:
            raise BizException(code=ErrorCode.RECORD_NOT_FOUND, message="记录不存在")
        if record.status != RecordStatus.toBeVerified:
            raise BizException(code=ErrorCode.RECORD_ERROR, message="比赛状态错误")
        if record.user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
        if result:
            record.status = RecordStatus.completed
            points = []
            if record.path and record.path.path:
                points = [BikePathPoint.model_validate(p) for p in record.path.path]
            distance = compute_distance([p.base for p in points])
            if record.duration_seconds is None:
                raise BizException(code=ErrorCode.RECORD_ERROR, message="找不到比赛成绩")
            track = await get_track_by_track_id(db, record.track.track_id)
            if track is None or track.event is None or track.event.season is None:
                raise BizException(code=ErrorCode.TRACK_NOT_FOUND, message="赛道不存在")
            await add_or_update_career_statistic_data(db, track.event.season.id, record.user.id, distance, record.duration_seconds)
            await add_or_update_daily_task_record(db, record.user.id, distance, record.duration_seconds)
            # 更新排行榜
            gender = record.user.real_name_info.gender if record.user.real_name_info else Gender.male
            await update_leaderboard_for_record(record, record.user.user_id, gender)
            # team 的状态交给定时清理
        else:
            record.status = RecordStatus.invalid


async def get_team_expired_date_service(db: AsyncSession, record_id: str) -> BikeTeamExpiredResponse:
    record = await get_record_by_record_id(db, record_id)
    if record is None:
        raise BizException(code=ErrorCode.RECORD_NOT_FOUND, message="记录不存在")
    if record.track is None:
        raise BizException(code=ErrorCode.TRACK_NOT_FOUND, message="赛道不存在")
    if record.team is None:
        raise BizException(code=ErrorCode.TEAM_NOT_FOUND, message="队伍不存在")
    expired_date = (record.team.start_date_real + timedelta(seconds=180)).isoformat() if record.team.start_date_real else None
    return BikeTeamExpiredResponse(expired_date=expired_date)


async def get_latest_snapshot_key(track_id: str, gender: Gender) -> str | None:
    base_prefix = f"leaderboard:bike:{track_id}:{gender.value}:snapshot:"
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
) -> BikeLeaderboardResponse:
    if timestamp:
        snapshot_key = f"leaderboard:bike:{track_id}:{gender.value}:snapshot:{timestamp}"
    else:
        snapshot_key = await get_latest_snapshot_key(track_id, gender)
        if snapshot_key is None:
            return BikeLeaderboardResponse(entries=[], time_stamp=None)
        timestamp = snapshot_key.split(":")[-1]
    rewards_hash_key = f"{snapshot_key}:rewards"

    start = (page - 1) * page_size
    end = start + page_size - 1

    # 从Redis获取排行榜数据
    leaderboard_page = await redis_client.zrange(snapshot_key, start, end, withscores=True)
    if not leaderboard_page:
        raise BizException(code=ErrorCode.LEADERBOARD_EXPIRED, message="排行榜数据已过期,请刷新")
    
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
        leaderboard_infos.append(BikeLeaderboardInfo(
            rank=reward["rank"],
            record_id=record_id,
            user_info=PersonInfoResponse(
                user_id=user_id,
                avatar_image_url=user.avatar_image_url if user else "/resources/placeholder/avatar.png",
                nickname=user.nickname if user else "未知"
            ),
            duration_seconds=duration_seconds,
            voucher=reward["voucher"],
            score=reward["score"]
        ))
    return BikeLeaderboardResponse(
        entries=leaderboard_infos, 
        time_stamp=timestamp
    )

async def query_leaderboard_history_in_page(
    db: AsyncSession,
    track_id: str,
    gender: Gender,
    page: int = 1,
    page_size: int = 20
) -> BikeLeaderboardResponse:
    track = await get_track_by_track_id(db, track_id)
    if track is None:
        raise BizException(code=ErrorCode.TRACK_NOT_FOUND, message="赛道不存在")
    records = await get_leaderboad_records_in_page(db, track.id, gender, page, page_size)
    entries = []
    for record in records:
        if record.record is None or record.user is None:
            continue
        entries.append(BikeLeaderboardInfo(
            rank=record.rank_position,
            record_id=record.record.record_id,
            user_info=PersonInfoResponse(
                user_id=record.user.user_id,
                avatar_image_url=record.user.avatar_image_url,
                nickname=record.user.nickname
            ),
            duration_seconds=record.duration_seconds,
            voucher=record.reward["voucher"],
            score=record.score
        ))
    return BikeLeaderboardResponse(entries=entries, time_stamp=None)

async def get_score_leaderboard_service(
    db: AsyncSession,
    season_id: str,
    gender: Gender,
    page: int = 1,
    page_size: int = 20
) -> BikeScoreLeaderboardResponse:
    season = await get_season_by_season_id(db, season_id)
    if not season:
        raise BizException(code=ErrorCode.SEASON_NOT_FOUND, message="赛季数据错误")
    scores = await get_scores_in_page(db, season.id, gender, page, page_size)
    entries = []
    for rank, score in enumerate(scores, start=1):
        if score.user is None:
            continue
        entries.append(BikeScoreLeaderboardInfo(
            rank=rank,
            user_info=PersonInfoResponse(
                user_id=score.user.user_id,
                avatar_image_url=score.user.avatar_image_url,
                nickname=score.user.nickname
            ),
            score=score.score
        ))
    return BikeScoreLeaderboardResponse(entries=entries)

async def query_user_rank_info(db: AsyncSession, user_id: str, track_id: str) -> BikeRankInfo:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
    gender = user.real_name_info.gender if user.real_name_info else Gender.male

    snapshot_key = await get_latest_snapshot_key(track_id, gender)
    if not snapshot_key:
        return BikeRankInfo()
    rewards_hash_key = f"{snapshot_key}:rewards"

    members = await redis_client.zrange(snapshot_key, 0, -1, withscores=True)

    for member, duration in members:
        if member.startswith(f"{user_id}:"):
            _, record_id = member.split(":", 1)
            member_key = f"{user_id}:{record_id}"
            reward_json = await redis_client.hget(rewards_hash_key, member_key)
            if not reward_json:
                return BikeRankInfo()
            try:
                reward = json.loads(reward_json)
            except:
                return BikeRankInfo()
            return BikeRankInfo(
                record_id=record_id,
                rank=reward["rank"],
                duration_seconds=duration,
                reward_voucher_amount=reward["voucher"],
                score=reward["score"]
            )
    return BikeRankInfo()

async def create_team_service(db: AsyncSession, create_info: BikeTeamCreateInfo, user_id: str) -> BikeTeamCreateResponse:
    async with db.begin():
        track = await get_track_by_track_id(db, create_info.track_id)
        if track is None:
            raise BizException(code=ErrorCode.TRACK_NOT_FOUND, message="赛道不存在")
        if track.start_date > datetime.now(timezone.utc):
            raise BizException(code=ErrorCode.RECORD_ERROR, message="比赛未开始")
        if track.end_date < datetime.now(timezone.utc):
            raise BizException(code=ErrorCode.RECORD_ERROR, message="比赛已结束")
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
        # 消费组队卡
        team_card_def = await get_team_card_def(db, SportType.bike)
        new_balance = await consume_cpasset(db, user.id, team_card_def.id, 1, "自行车赛事报名")
        team_id = f"team_{uuid.uuid4()}"
        team_code = team_id[-8:]
        new_team = BikeTeam(
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
        new_member = BikeTeamMember(
            member_id=member_id,
            team_id=new_team_id,
            user_id=user.id,
            is_leader=True
        )
        await create_team_member_crud(db, new_member)
        return BikeTeamCreateResponse(
            team_code=team_code,
            asset_id=team_card_def.asset_id,
            new_balance=new_balance
        )
    

async def get_public_teams_service(
    db: AsyncSession, 
    track_id: str,
    page: int, 
    size: int
) -> BikeAppliedTeamResponse:
    track = await get_track_by_track_id(db, track_id)
    if track is None:
        raise BizException(code=ErrorCode.TRACK_NOT_FOUND, message="赛道不存在")
    if track.start_date > datetime.now(timezone.utc):
        raise BizException(code=ErrorCode.TRACK_ERROR, message="比赛未开始")
    if track.end_date < datetime.now(timezone.utc):
        raise BizException(code=ErrorCode.TRACK_ERROR, message="比赛已结束")
    teams = await get_public_teams_by_track_id(db, track.id, page, size)
    infos = []
    for t in teams:
        leader_member = next((m for m in t.members if m.is_leader), None)
        if leader_member is not None:
            infos.append(BikeAppliedTeamInfo(
                team_id=t.team_id,
                leader_id=leader_member.user.user_id,
                leader_name=leader_member.user.nickname,
                leader_avatar_url=leader_member.user.avatar_image_url,
                title=t.title,
                description=t.description,
                member_count=len(t.members),
                max_member_size=t.members_count_max,
                region_name="未知",
                event_name="未知",
                track_name="未知",
                competition_date=t.start_date.isoformat(),
            ))
    return BikeAppliedTeamResponse(teams=infos)


async def get_user_applied_teams(
    db: AsyncSession, 
    user_id: str,
    page: int, 
    size: int
) -> BikeAppliedTeamResponse:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
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
            infos.append(BikeAppliedTeamInfo(
                team_id=t.team_id,
                leader_id=leader.user_id,
                leader_name=leader.nickname,
                leader_avatar_url=leader.avatar_image_url,
                title=t.title,
                description=t.description,
                member_count=len(t.members),
                max_member_size=t.members_count_max,
                region_name=t.track.event.region.name if t.track and t.track.event and t.track.event.region else "未知",
                event_name=t.track.event.name if t.track and t.track.event else "未知",
                track_name=t.track.name if t.track else "未知",
                competition_date=t.start_date.isoformat(),
            ))
    return BikeAppliedTeamResponse(teams=infos)


async def get_user_teams(
    db: AsyncSession, 
    user_id: str,
    relationship: TeamRelationship,
    page: int, 
    size: int
) -> BikeTeamResponse:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
    
    infos = []
    if relationship == TeamRelationship.created:
        teams = await get_created_teams_by_user_id(db, user.id, page, size)
        for t in teams:
            infos.append(BikeTeamInfo(
                team_id=t.team_id,
                leader_id=user_id,
                leader_name=user.nickname,
                leader_avatar_url=user.avatar_image_url,
                title=t.title,
                member_count=len(t.members),
                max_member_size=t.members_count_max,
                team_code=t.team_code,
                region_name=t.track.event.region.name if t.track and t.track.event and t.track.event.region else "未知",
                event_name=t.track.event.name if t.track and t.track.event else "未知",
                track_name=t.track.name if t.track else "未知",
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
                infos.append(BikeTeamInfo(
                    team_id=t.team_id,
                    leader_id=leader.user_id,
                    leader_name=leader.nickname,
                    leader_avatar_url=leader.avatar_image_url,
                    title=t.title,
                    member_count=len(t.members),
                    max_member_size=t.members_count_max,
                    team_code=t.team_code,
                    region_name=t.track.event.region.name if t.track and t.track.event and t.track.event.region else "未知",
                    event_name=t.track.event.name if t.track and t.track.event else "未知",
                    track_name=t.track.name if t.track else "未知",
                    is_public=t.is_public,
                    status=t.status,
                    competition_date=t.start_date.isoformat(),
                ))
    return BikeTeamResponse(teams=infos)


async def get_team_detail_service(db: AsyncSession, team_id: str) -> BikeTeamDetailResponse:
    team = await get_team_by_team_id(db, team_id)
    if team is None:
        raise BizException(code=ErrorCode.TEAM_NOT_FOUND, message="队伍不存在")
    if team.status == TeamStatus.completed:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="队伍已过期")
    members = [
        BikeTeamMemberInfo(
            member_id=m.member_id,
            user_id=m.user.user_id,
            nick_name=m.user.nickname if m.user else "未知",
            avatar_url=m.user.avatar_image_url if m.user else "未知",
            join_date=m.created_at.isoformat(),
            is_registered=m.is_registered,
            is_leader=m.is_leader
        )
        for m in team.members
    ]
    region_name = team.track.event.region.name if team.track and team.track.event and team.track.event.region else "未知"
    event_name = team.track.event.name if team.track and team.track.event else "未知"
    track_name = team.track.name if team.track else "未知"
    return BikeTeamDetailResponse(
        team_id=team.team_id,
        title=team.title,
        description=team.description,
        max_member_size=team.members_count_max,
        team_code=team.team_code,
        region_name=region_name,
        event_name=event_name,
        track_name=track_name,
        is_public=team.is_public,
        status=team.status,
        created_at=team.created_at.isoformat(),
        competition_date=team.start_date.isoformat(),
        members=members
    )
    

async def get_team_manage_service(db: AsyncSession, team_id: str) -> BikeTeamManageResponse:
    team = await get_team_by_team_id(db, team_id)
    if team is None:
        raise BizException(code=ErrorCode.TEAM_NOT_FOUND, message="队伍不存在")
    if team.status == TeamStatus.completed:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="队伍已过期")
    if team.track is None:
        raise BizException(code=ErrorCode.TRACK_NOT_FOUND, message="赛道不存在")
    if team.track.end_date < datetime.now(timezone.utc):
        raise BizException(code=ErrorCode.TEAM_ERROR, message="队伍已过期")
    members = [
        BikeTeamMemberInfo(
            member_id=m.member_id,
            user_id=m.user.user_id,
            nick_name=m.user.nickname if m.user else "未知",
            avatar_url=m.user.avatar_image_url if m.user else "未知",
            join_date=m.created_at.isoformat(),
            is_registered=m.is_registered,
            is_leader=m.is_leader
        )
        for m in team.members
    ]
    applied_members = [
        BikeTeamAppliedMemberInfo(
            member_id=m.member_id,
            user_id=m.user.user_id,
            nick_name=m.user.nickname if m.user else "未知",
            avatar_url=m.user.avatar_image_url if m.user else "未知",
            introduction=m.introduction,
            join_date=m.created_at.isoformat()
        )
        for m in team.applied_members
    ]
    region_name = team.track.event.region.name if team.track.event and team.track.event.region else "未知"
    event_name = team.track.event.name if team.track.event else "未知"
    track_name = team.track.name
    track_end_date = team.track.end_date.isoformat()
    return BikeTeamManageResponse(
        team_id=team.team_id,
        title=team.title,
        description=team.description,
        max_member_size=team.members_count_max,
        team_code=team.team_code,
        region_name=region_name,
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
        if user is None or record is None or user.real_name_info is None or user.real_name_info.gender != gender:
            continue
        filtered_result.append((user_id, record_id, duration))
    return filtered_result
    

async def settle_bike_leaderboard_service(db: AsyncSession, track_id: str) -> tuple[int, int, int, int, int]:
    async with db.begin():
        track = await get_track_by_track_id(db, track_id)
        if track is None:
            raise BizException(code=ErrorCode.TRACK_NOT_FOUND, message="赛道不存在")
        if track.end_date > datetime.now(timezone.utc):
            raise BizException(code=ErrorCode.TRACK_ERROR, message="赛道未结束，无法结算")
        if track.event is None or track.event.season is None:
            raise BizException(code=ErrorCode.TRACK_ERROR, message="赛事数据缺失")
        if await track_has_settled(db, track.id):
            raise BizException(code=ErrorCode.TRACK_ERROR, message="赛道已被结算")

        male_key = f"leaderboard:bike:{track.track_id}:male"
        female_key = f"leaderboard:bike:{track.track_id}:female"
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

        # 写入BikeLeaderboard、生成Mailbox、累加BikeCareerScore
        async def _write_leaderboard(db: AsyncSession, gender: Gender, settled: List[tuple[str, str, float, int, int, int]]):
            for user_id, record_id, duration, voucher, score, rank in settled:
                user = await get_exist_user_by_id(db, user_id)
                record = await get_record_by_record_id(db, record_id)
                if user is None or record is None or user.real_name_info is None or user.real_name_info.gender != gender:
                    raise BizException(code=ErrorCode.TRACK_ERROR, message="结算失败")
                # leaderboard
                db.add(BikeLeaderboard(
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
                        title=f"自行车赛事结算奖励",
                        content=f"恭喜您在 {track.event.name} - {track.name} 比赛中获得第 {rank} 名，请尽快领取奖励:",
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


async def update_team_info_service(db: AsyncSession, user_id: str, info: BikeTeamUpdateInfo) -> BikeTeamUpdateResponse:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
    team = await get_team_by_team_id_for_update(db, info.team_id)
    if team is None:
        raise BizException(code=ErrorCode.TEAM_NOT_FOUND, message="队伍不存在")
    if team.status != TeamStatus.prepared:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="队伍已锁定,保存失败")
    # 验证用户是否是队伍成员
    user_member = next((member for member in team.members if member.user_id == user.id), None)
    if user_member is None:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="无修改权限")
    # 验证用户是否是队长
    if not user_member.is_leader:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="无修改权限")
    
    update_data = {
        "title": info.title,
        "description": info.description,
        "start_date": info.competition_date
    }
    await update_team_crud(db, team, update_data)
    await db.commit()
    return BikeTeamUpdateResponse(
        title=team.title,
        description=team.description,
        competition_date=team.start_date.isoformat()
    )


async def update_team_public_status_service(db: AsyncSession, user_id: str, info: BikeTeamStatusUpdateInfo) -> bool:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
    team = await get_team_by_team_id_for_update(db, info.team_id)
    if team is None:
        raise BizException(code=ErrorCode.TEAM_NOT_FOUND, message="队伍不存在")
    if team.status != TeamStatus.prepared:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="队伍已锁定,无法修改")
    # 验证用户是否是队伍成员
    user_member = next((member for member in team.members if member.user_id == user.id), None)
    if user_member is None:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="无修改权限")
    # 验证用户是否是队长
    if not user_member.is_leader:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="无修改权限")
    
    update_data = {
        "is_public": info.new_status
    }
    await update_team_crud(db, team, update_data)
    await db.commit()
    return team.is_public


async def update_team_lock_status_service(db: AsyncSession, user_id: str, info: BikeTeamStatusUpdateInfo) -> bool:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
    team = await get_team_by_team_id_for_update(db, info.team_id)
    if team is None:
        raise BizException(code=ErrorCode.TEAM_NOT_FOUND, message="队伍不存在")
    if team.status != TeamStatus.prepared and team.status != TeamStatus.locked:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="队伍处于比赛状态,无法修改")
    # 验证用户是否是队伍成员
    user_member = next((member for member in team.members if member.user_id == user.id), None)
    if user_member is None:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="无修改权限")
    # 验证用户是否是队长
    if not user_member.is_leader:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="无修改权限")
    
    update_data = {
        "status": TeamStatus.locked if info.new_status else TeamStatus.prepared
    }
    await update_team_crud(db, team, update_data)
    await db.commit()
    return team.status != TeamStatus.prepared


async def update_team_ready_status_service(db: AsyncSession, user_id: str, team_id: str) -> bool:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
    team = await get_team_by_team_id_for_update(db, team_id)
    if team is None:
        raise BizException(code=ErrorCode.TEAM_NOT_FOUND, message="队伍不存在")
    if team.status != TeamStatus.prepared and team.status != TeamStatus.locked:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="队伍处于比赛状态,无法修改")
    # 验证用户是否是队伍成员
    user_member = next((member for member in team.members if member.user_id == user.id), None)
    if user_member is None:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="无修改权限")
    # 验证用户是否是队长
    if not user_member.is_leader:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="无修改权限")
    # 确认队伍中所有members都已报名
    if any(not member.is_registered for member in team.members):
        raise BizException(code=ErrorCode.TEAM_ERROR, message="队伍中存在未报名成员")
    # 确认队伍不存在applied_members
    if len(team.applied_members) > 0:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="队伍存在待审核成员")
    if team.track is None:
        raise BizException(code=ErrorCode.TEAM_JOIN_ERROR, message="队伍赛道无效")
    # 确认比赛时间的合法性:
    if team.start_date < datetime.now(timezone.utc) or team.start_date > team.track.end_date:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="比赛时间不合法")
    # 确认队伍已锁定
    if team.status == TeamStatus.prepared:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="请先锁定队伍")
    # 禁止1人进行组队比赛
    if len(team.members) == 1:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="队伍至少需要有2名成员哦")
    
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
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
        team = await get_team_by_team_id_for_update(db, team_id)
        if team is None:
            raise BizException(code=ErrorCode.TEAM_NOT_FOUND, message="队伍不存在")
        if team.status != TeamStatus.prepared:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="队伍已锁定,无法解散")
        if team.track is None:
            raise BizException(code=ErrorCode.TRACK_NOT_FOUND, message="队伍无效")
        if team.track.end_date < datetime.now(timezone.utc):
            raise BizException(code=ErrorCode.TEAM_ERROR, message="队伍已过期")
        user_member = next((member for member in team.members if member.user_id == user.id), None)
        if user_member is None:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="无修改权限")
        if not user_member.is_leader:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="无修改权限")
        if user_member.is_registered:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="请先取消报名")
        
        # 返回组队卡
        team_card_def = await get_team_card_def(db, SportType.bike)
        new_balance = await reward_cpasset(db, user.id, team_card_def.id, 1, "解散队伍", AssetOperation.REFUND)
        # 所有已报名成员取消报名
        register_card_def = await get_registration_card_def(db, SportType.bike, True)
        for member in team.members:
            if member.is_registered:
                await reward_cpasset(db, member.user_id, register_card_def.id, 1, "取消报名", AssetOperation.REFUND)
        await delete_records_by_team_id(db, team.id)
        await db.delete(team)
        return CPAssetResponse(
            asset_id=team_card_def.asset_id,
            new_balance=new_balance
        )
    

async def remove_team_member_service(db: AsyncSession, user_id: str, team_id: str, member_id: str) -> BikeTeamMembersResponse:
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
        team = await get_team_by_team_id_for_update(db, team_id)
        if team is None:
            raise BizException(code=ErrorCode.TEAM_NOT_FOUND, message="队伍不存在")
        if team.status != TeamStatus.prepared:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="队伍已锁定")
        if team.track is None:
            raise BizException(code=ErrorCode.TRACK_NOT_FOUND, message="队伍无效")
        if team.track.end_date < datetime.now(timezone.utc):
            raise BizException(code=ErrorCode.TEAM_ERROR, message="队伍已过期")
        user_member = next((member for member in team.members if member.user_id == user.id), None)
        member_need_delete = next((member for member in team.members if member.member_id == member_id), None)
        if member_need_delete is None:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="用户已不在队伍中")
        if member_need_delete.user_id == user.id:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="不能移除自己")
        if user_member is None:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="无移除权限")
        if not user_member.is_leader:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="无移除权限")
        # 若已报名则自动取消报名
        if member_need_delete.is_registered:
            record = await get_record_by_team_id_and_user_id(db, team.id, member_need_delete.user_id)
            if record is not None and record.status == RecordStatus.notStarted:
                await delete_record_crud(db, record)
                register_card_def = await get_registration_card_def(db, SportType.bike, True)
                await reward_cpasset(db, member_need_delete.user_id, register_card_def.id, 1, "取消报名", AssetOperation.REFUND)
        await db.delete(member_need_delete)
        await db.flush()
        await db.refresh(team, attribute_names=["members"])
        members = [BikeTeamMemberInfo(
            member_id=member.member_id,
            user_id=member.user.user_id,
            nick_name=member.user.nickname if member.user else "未知",
            avatar_url=member.user.avatar_image_url if member.user else "未知",
            join_date=member.created_at.isoformat(),
            is_registered=member.is_registered,
            is_leader=member.is_leader
        ) for member in team.members]
        return BikeTeamMembersResponse(members=members)


async def reject_applied_request_service(db: AsyncSession, user_id: str, team_id: str, member_id: str):
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
        team = await get_team_by_team_id_for_update(db, team_id)
        if team is None:
            raise BizException(code=ErrorCode.TEAM_NOT_FOUND, message="队伍不存在")
        if team.status != TeamStatus.prepared:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="队伍已锁定")
        if team.track is None:
            raise BizException(code=ErrorCode.TRACK_NOT_FOUND, message="队伍无效")
        if team.track.end_date < datetime.now(timezone.utc):
            raise BizException(code=ErrorCode.TEAM_ERROR, message="队伍已过期")
        user_member = next((member for member in team.members if member.user_id == user.id), None)
        member_need_delete = next((member for member in team.applied_members if member.member_id == member_id), None)
        if member_need_delete is None:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="用户已不在申请列表中")
        if member_need_delete.user_id == user.id:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="不能拒绝自己")
        if user_member is None:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="无操作权限")
        if not user_member.is_leader:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="无操作权限")
        await db.delete(member_need_delete)


async def approve_applied_request_service(db: AsyncSession, user_id: str, team_id: str, member_id: str) -> BikeTeamMembersResponse:
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
        team = await get_team_by_team_id_for_update(db, team_id)
        if team is None:
            raise BizException(code=ErrorCode.TEAM_NOT_FOUND, message="队伍不存在")
        if team.status != TeamStatus.prepared:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="队伍已锁定")
        if team.track is None:
            raise BizException(code=ErrorCode.TRACK_NOT_FOUND, message="队伍无效")
        if team.track.end_date < datetime.now(timezone.utc):
            raise BizException(code=ErrorCode.TEAM_ERROR, message="队伍已过期")
        user_member = next((member for member in team.members if member.user_id == user.id), None)
        member_need_delete = next((member for member in team.applied_members if member.member_id == member_id), None)
        if member_need_delete is None:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="用户已不在申请列表中")
        if member_need_delete.user_id == user.id:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="不能处理自己的申请")
        if user_member is None:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="无操作权限")
        if not user_member.is_leader:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="无操作权限")
        if len(team.members) >= team.members_count_max:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="队伍已满")
        new_member = BikeTeamMember(
            member_id=f"member_{uuid.uuid4()}",
            team_id=team.id,
            user_id=member_need_delete.user.id
        )
        await db.delete(member_need_delete)
        db.add(new_member)
        await db.flush()
        await db.refresh(team, attribute_names=["members"])
        members = [BikeTeamMemberInfo(
            member_id=member.member_id,
            user_id=member.user.user_id,
            nick_name=member.user.nickname if member.user else "未知",
            avatar_url=member.user.avatar_image_url if member.user else "未知",
            join_date=member.created_at.isoformat(),
            is_registered=member.is_registered,
            is_leader=member.is_leader
        ) for member in team.members]
        return BikeTeamMembersResponse(members=members)

        '''if member_need_delete in team.applied_members:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="操作失败")
        if new_member not in team.members:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="操作失败")'''


async def quit_team_service(db: AsyncSession, user_id: str, team_id: str):
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
    team = await get_team_by_team_id_for_update(db, team_id)
    if team is None:
        raise BizException(code=ErrorCode.TEAM_NOT_FOUND, message="队伍不存在")
    if team.status != TeamStatus.prepared and team.status != TeamStatus.locked:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="队伍处于比赛状态,无法退出")
    user_member = next((member for member in team.members if member.user_id == user.id), None)
    if user_member is None:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="您不在队伍中")
    if user_member.is_leader:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="您是队长,无法退出队伍")
    if user_member.is_registered:
        raise BizException(code=ErrorCode.TEAM_ERROR, message="请先取消报名")
    await db.delete(user_member)
    await db.commit()


async def join_team_service(db: AsyncSession, user_id: str, team_code: str):
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
        team = await get_team_by_code_for_update(db, team_code)
        if team is None:
            raise BizException(code=ErrorCode.TEAM_NOT_FOUND, message="队伍不存在")
        if any(member.user_id == user.id for member in team.members):
            raise BizException(code=ErrorCode.TEAM_JOIN_ERROR, message="您已在队伍中")
        if team.status != TeamStatus.prepared:
            raise BizException(code=ErrorCode.TEAM_JOIN_ERROR, message="队伍当前不可加入")
        if team.track is None:
            raise BizException(code=ErrorCode.TEAM_JOIN_ERROR, message="队伍赛道无效")
        if team.track.end_date < datetime.now(timezone.utc):
            raise BizException(code=ErrorCode.TEAM_JOIN_ERROR, message="队伍已过期")
        if len(team.members) >= team.members_count_max:
            raise BizException(code=ErrorCode.TEAM_JOIN_ERROR, message="队伍已满")
        new_member = BikeTeamMember(
            member_id=f"member_{uuid.uuid4()}",
            team_id=team.id,
            user_id=user.id
        )
        await create_team_member_crud(db, new_member)


async def applied_join_team_service(db: AsyncSession, user_id: str, request: BikeTeamAppliedRequest):
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
        team = await get_team_by_team_id_for_update(db, request.team_id)
        if team is None:
            raise BizException(code=ErrorCode.TEAM_NOT_FOUND, message="队伍不存在")
        if any(member.user_id == user.id for member in team.members):
            raise BizException(code=ErrorCode.TEAM_JOIN_ERROR, message="您已在队伍中")
        if any(member.user_id == user.id for member in team.applied_members):
            raise BizException(code=ErrorCode.TEAM_JOIN_ERROR, message="请勿重复申请")
        if team.status != TeamStatus.prepared:
            raise BizException(code=ErrorCode.TEAM_JOIN_ERROR, message="队伍当前不可加入")
        if team.track is None:
            raise BizException(code=ErrorCode.TEAM_JOIN_ERROR, message="队伍无效")
        if team.track.end_date < datetime.now(timezone.utc):
            raise BizException(code=ErrorCode.TEAM_JOIN_ERROR, message="队伍已过期")
        if len(team.members) >= team.members_count_max:
            raise BizException(code=ErrorCode.TEAM_JOIN_ERROR, message="队伍已满")
        new_member = BikeTeamAppliedMember(
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
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
        team = await get_team_by_team_id_for_update(db, team_id)
        if team is None:
            raise BizException(code=ErrorCode.TEAM_NOT_FOUND, message="队伍不存在")
        if team.track is None:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="队伍无效")
        if team.track.end_date < datetime.now(timezone.utc):
            raise BizException(code=ErrorCode.TEAM_ERROR, message="队伍已过期")
        member = next((member for member in team.applied_members if member.user_id == user.id), None)
        if member is None:
            raise BizException(code=ErrorCode.TEAM_ERROR, message="您不在申请列表中")
        await db.delete(member)


async def get_record_detail_service(db: AsyncSession, record_id: str, user_id: str | None) -> BikeRecordDetailInfo:
    record = await get_record_by_record_id(db, record_id)
    if record is None:
        raise BizException(code=ErrorCode.RECORD_NOT_FOUND, message="记录不存在")
    
    # 构建MemberScoreInfo列表
    team_member_scores_list = []
    if record.team_id:
        member_records = await get_records_by_team_id(db, record.team_id)
        for member_record in member_records:
            team_member_scores_list.append(MemberScoreInfo(
                user_info=PersonInfoResponse(user_id=member_record.user.user_id, avatar_image_url=member_record.user.avatar_image_url, nickname=member_record.user.nickname),
                status=member_record.status, final_time=member_record.duration_seconds))
    
    # 构建CardBonusInfo列表
    card_bonus_list = []
    raw_duration = (record.end_time - record.start_time).total_seconds() if record.end_time and record.start_time else 0
    for card_bonus in record.card_bonus:
        if card_bonus.card and card_bonus.card.user:
            card_info = equip_card_to_base_info(card_bonus.card)
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
            path_points = []
            for point_data in record.path.path:
                # 兼容新旧数据格式
                # 新格式：{"base": {...}, "power": ..., "pedal_cadence": ...}
                # 旧格式：所有字段在同一层级
                if "base" in point_data:
                    # 新格式，直接验证
                    path_points.append(BikePathPoint.model_validate(point_data))
                else:
                    # 旧格式，转换为新格式
                    # 提取 PathPoint 的字段
                    base_data = {
                        "lat": point_data.get("lat"),
                        "lon": point_data.get("lon"),
                        "speed": point_data.get("speed"),
                        "altitude": point_data.get("altitude"),
                        "heart_rate": point_data.get("heart_rate"),
                        "timestamp": point_data.get("timestamp")
                    }
                    # 提取 BikePathPoint 特有的字段
                    bike_path_point_data = {
                        "base": base_data,
                        "power": point_data.get("power"),
                        "pedal_cadence": point_data.get("pedal_cadence"),
                        "estimate_pedal_count": point_data.get("estimate_pedal_count")
                    }
                    path_points.append(BikePathPoint.model_validate(bike_path_point_data))
        except Exception:
            path_points = []
    
    # 计算时间
    original_time = 0.0
    final_time = 0.0
    if record.start_time and record.end_time:
        original_time = (record.end_time - record.start_time).total_seconds()
    if record.duration_seconds is not None:
        final_time = float(record.duration_seconds)
    
    return BikeRecordDetailInfo(
        status=record.status,
        original_time=original_time,
        final_time=final_time,
        is_finish_computed=record.is_finish_bonus_computing if record.is_finish_bonus_computing else False,
        path=path_points,
        card_bonus=card_bonus_list,
        team_member_scores=team_member_scores_list
    )

async def get_current_best_records_service(db: AsyncSession, user_id: str) -> BikeSummaryRecordResponse:
    seasons = await get_season_now(db)
    if not seasons:
        #raise BizException(code=ErrorCode.SEASON_NOT_FOUND, message="当前没有进行中的Bike赛季")
        return BikeSummaryRecordResponse(records=[])
    if len(seasons) > 1:
        raise BizException(code=ErrorCode.SEASON_NOT_UNIQUE, message="当前时间存在多个进行中的Bike赛季")
    season: BikeSeason = seasons[0]
    events = await get_active_events_by_season_id(db, season.id)
    records = []
    for event in events:
        for track in event.tracks:
            if track.start_date < datetime.now(timezone.utc) and track.end_date > datetime.now(timezone.utc):
                rank_info = await query_user_rank_info(db, user_id, track.track_id)
                if rank_info.record_id and event.region:
                    records.append(BikeSummaryRecordInfo(
                        record_id=rank_info.record_id,
                        event_name=event.name,
                        track_name=track.name,
                        city_name=event.region.name,
                        best_time=rank_info.duration_seconds if rank_info.duration_seconds else 0,
                        rank=rank_info.rank if rank_info.rank else 0,
                        voucher=rank_info.reward_voucher_amount if rank_info.reward_voucher_amount else 0,
                        score=rank_info.score if rank_info.score else 0
                    ))
    return BikeSummaryRecordResponse(records=records)

async def get_career_records_service(db: AsyncSession, season_id: str, user_id: str) -> BikeCareerRecordResponse:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
    season = await get_season_by_season_id(db, season_id)
    if season is None:
        raise BizException(code=ErrorCode.SEASON_NOT_FOUND, message="赛季数据异常")
    records = []
    for event in season.bike_events:
        for track in event.tracks:
            record = await get_leaderboad_record(db, track.id, user.id)
            if record and record.record:
                records.append(BikeCareerRecordInfo(
                    record_id=record.record.record_id,
                    track_id=track.track_id,
                    track_name=track.name,
                    event_name=event.name,
                    region=event.region.name,
                    track_score=track.score,
                    score=record.score,
                    record_date=record.record.end_time.isoformat()
                ))
    return BikeCareerRecordResponse(records=records)

async def get_career_data_service(db: AsyncSession, season_id: str, user_id: str) -> BikeCareerDataInfo:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
    season = await get_season_by_season_id(db, season_id)
    if not season:
        raise BizException(code=ErrorCode.SEASON_NOT_FOUND, message="赛季数据错误")
    gender = user.real_name_info.gender if user.real_name_info else Gender.male
    statistic_data = await get_career_statistic_data(db, season.id, user.id)
    score, rank, voucher_bonus = await get_score_and_rank_by_season_id_and_user(db, season.id, user.id, gender)
    return BikeCareerDataInfo(
        total_score=score if score else 0, 
        total_rank=rank if rank else None, 
        total_voucher=voucher_bonus if voucher_bonus else 0,
        total_distance=statistic_data.total_distance if statistic_data else 0,
        total_time=statistic_data.total_time if statistic_data else 0
    )

async def query_daily_task_status_service(db: AsyncSession, user_id: str) -> DailyTaskResponse | None:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
    task = await get_daily_task(db)
    task_record = await get_today_task_record_by_user(db, user.id)
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
            reward_stage3_url=cpasset_def.image_url,
            is_reward3_received=task_record.is_reward3_received if task_record else False,
            progress=task_record.progress if task_record else 0
        ) if cpasset_def else None
    else:
        return None

async def claimed_daily_task_reward_service(db: AsyncSession, user_id: str, stage: int) -> DailyTaskRewardResponse:
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
        if stage < 1 or stage > 3:
            raise BizException(code=ErrorCode.PROPERTY_ERROR, message="领取失败")
        task = await get_daily_task(db)
        task_record = await get_today_task_record_by_user(db, user.id)
        if task is None or task_record is None:
            raise BizException(code=ErrorCode.DAILY_TASK_NOT_FOUND, message="领取失败")
        if stage == 1 and not task_record.is_reward1_received and (task_record.progress / task.total_progress > 1/3):
            new_balance = await reward_ccasset(db, task.reward_stage1_type, task.reward_stage1, user.id, "每日任务奖励", AssetOperation.REWARD)
            task_record.is_reward1_received = True
            return DailyTaskRewardResponse(
                ccasset_type=task.reward_stage1_type,
                ccasset_amount=new_balance,
                cpasset_id=None,
                cpasset_amount=None
            )
        if stage == 2 and not task_record.is_reward2_received and (task_record.progress / task.total_progress > 2/3):
            new_balance = await reward_ccasset(db, task.reward_stage2_type, task.reward_stage2, user.id, "每日任务奖励", AssetOperation.REWARD)
            task_record.is_reward2_received = True
            return DailyTaskRewardResponse(
                ccasset_type=task.reward_stage2_type,
                ccasset_amount=new_balance,
                cpasset_id=None,
                cpasset_amount=None
            )
        if stage == 3 and not task_record.is_reward3_received and task_record.progress > task.total_progress:
            new_balance = await reward_cpasset(db, user.id, task.reward_stage3_id, 1, "每日任务奖励", AssetOperation.REWARD)
            task_record.is_reward3_received = True
            cpasset_def = await get_cpasset_def_by_id(db, task.reward_stage3_id)
            return DailyTaskRewardResponse(
                ccasset_type=None,
                ccasset_amount=None,
                cpasset_id=cpasset_def.asset_id if cpasset_def else None,
                cpasset_amount=new_balance
            )
        raise BizException(code=ErrorCode.DAILY_TASK_ERROR, message="领取失败")

async def start_competition_with_team_bonus_card_service(db: AsyncSession, user_id: str, record_id: str):
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="用户不存在")
    record = await get_record_by_record_id(db, record_id)
    if record is None:
        raise BizException(code=ErrorCode.RECORD_NOT_FOUND, message="记录不存在")
    if record.team_id is None:
        raise BizException(code=ErrorCode.TEAM_NOT_FOUND, message="队伍不存在")
    new_bonus_record = BikeBonusByTeamMember(
        team_id=record.team_id,
        user_id=user.id
    )
    db.add(new_bonus_record)
    await db.commit()

async def finish_competition_with_team_bonus_card_service(db: AsyncSession, user_id: uuid.UUID, team_id: uuid.UUID, info: TeamMagicCardBonusInfo):
    bonus_records = await get_bonus_record_with_team_magic_card_for_update(db, team_id)
    is_all_completed = True
    for br in bonus_records:
        if br.user_id == user_id:
            br.bonus_in_ratio = info.bonus_ratio
            br.bonus_in_seconds = info.bonus_seconds
            br.is_applied = True
        if br.user_id != user_id and not br.is_applied:
            is_all_completed = False
            
    records = await get_records_by_team_id_for_update(db, team_id)
    for r in records:
        if r.user_id != user_id:
            # 已结束需要手动应用 bonus
            if r.duration_seconds and r.start_time and r.end_time:
                raw_duration = (r.end_time - r.start_time).total_seconds()
                if info.bonus_ratio:
                    r.duration_seconds -= info.bonus_ratio * raw_duration
                r.duration_seconds -= info.bonus_seconds if info.bonus_seconds else 0
                r.duration_seconds = max(raw_duration * 0.8, r.duration_seconds)
                #print(f"update duration_seconds to: {r.duration_seconds}")
            if is_all_completed:
                r.is_finish_bonus_computing = True
                #print(f"update record {r.record_id} is_completed to: {r.is_finish_bonus_computing}")
            card = await get_equip_card_by_card_id(db, info.card_id)
            if card is not None:
                #print("add card bonus!")
                db.add(CardBonusInBikeRecord(
                    record_id=r.id,
                    card_id=card.id,
                    bonus_ratio=info.bonus_ratio,
                    bonus_time=info.bonus_seconds if info.bonus_seconds else 0
                ))
        else:
            if is_all_completed:
                r.is_finish_bonus_computing = True
                #print(f"update record {r.record_id} is_completed to: {r.is_finish_bonus_computing}")