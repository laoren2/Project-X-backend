from fastapi import APIRouter, Depends, File, UploadFile, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.base import BaseResponse
from app.schemas.competition.common import TeamRelationship, RecordStatus
from app.schemas.competition.bike import (
    BikeEventListResponse, BikeTrackListResponse,
    BikeRecordResponse, BikeBeginInfo, BikeFinishInfo,
    BikeSeasonBaseInfo, BikeSingleRegisterResponse, BikeRankInfo,
    BikeLeaderboardResponse, BikeTeamCreateInfo, BikeTeamResponse,
    BikeAppliedTeamResponse, BikeTeamDetailResponse, BikeTeamManageResponse,
    BikeTeamCreateResponse, BikeTeamUpdateInfo, BikeTeamUpdateResponse,
    BikeTeamStatusUpdateInfo, BikeTeamMembersResponse, BikeTeamAppliedRequest,
    BikeTeamExpiredResponse, BikeRecordDetailInfo, BikeSummaryRecordResponse,
    BikeHistorySeasonResponse, BikeCareerRecordResponse, BikeScoreLeaderboardResponse,
    BikeCareerDataInfo
)
from app.schemas.asset import CPAssetResponse
from app.schemas.user import AuthContext, Gender
from app.services.competition.bike import (
    query_events_by_region, query_tracks_by_event, single_register_service, 
    start_single_competition_service, finish_single_competition_service,
    query_current_season_service, get_incompleted_records_all, cancel_register_service,
    query_user_rank_info, query_leaderboard_in_page, create_team_service,
    get_user_teams, get_user_applied_teams, get_team_detail_service,
    get_team_manage_service, join_team_service, update_team_info_service,
    update_team_public_status_service, update_team_lock_status_service,
    update_team_ready_status_service, team_register_service, disband_team_service,
    quit_team_service, remove_team_member_service, get_public_teams_service,
    applied_join_team_service, reject_applied_request_service, approve_applied_request_service,
    cancel_applied_join_team_service, start_team_competition_service, finish_team_competition_service,
    get_team_expired_date_service, enter_team_competition_link_service, get_record_detail_service,
    get_current_best_records_service, get_history_seasons_service, get_career_records_service,
    query_leaderboard_history_in_page, get_score_leaderboard_service, get_career_data_service,
    get_completed_records_all
)
from app.api.deps import get_current_user
from typing import Optional


router = APIRouter()


# 查询赛季
@router.get("/query_season", response_model=BaseResponse[BikeSeasonBaseInfo], summary="查询bike赛季")
async def query_season(
    db: AsyncSession = Depends(get_db)
):
    season = await query_current_season_service(db)
    return BaseResponse.success(data=season)


# 查询赛事
@router.get("/query_events", response_model=BaseResponse[BikeEventListResponse], summary="查询bike赛事")
async def query_events(
    region_name: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    events = await query_events_by_region(
        db=db,
        region_name=region_name
    )
    return BaseResponse.success(data=BikeEventListResponse(events=events))


# 查询赛道
@router.get("/query_tracks", response_model=BaseResponse[BikeTrackListResponse], summary="查询bike赛道")
async def query_tracks(
    event_id: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    tracks = await query_tracks_by_event(
        db=db,
        event_id=event_id
    )
    return BaseResponse.success(data=BikeTrackListResponse(tracks=tracks))


# 单人比赛报名
@router.post("/single_register",response_model=BaseResponse[BikeSingleRegisterResponse], summary="bike单人赛事报名")
async def single_register(
    track_id: str = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    response = await single_register_service(db, track_id, auth.payload["user_id"])
    return BaseResponse.success(token=auth.new_token, message=f"报名成功", data=response)


# 组队比赛报名
@router.post("/team_register",response_model=BaseResponse[CPAssetResponse], summary="bike组队赛事报名")
async def team_register(
    team_code: str = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    response = await team_register_service(db, team_code, auth.payload["user_id"])
    return BaseResponse.success(token=auth.new_token, message=f"报名成功", data=response)


@router.post("/cancel_register", response_model=BaseResponse[CPAssetResponse], summary="取消报名bike赛事")
async def cancel_register(
    record_id: str = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await cancel_register_service(db, record_id, auth.payload["user_id"])
    return BaseResponse.success(token=auth.new_token, message=f"已成功取消", data=result)


# 开始单人比赛
@router.post("/start_single_competition",response_model=BaseResponse[None],summary="开始单人比赛")
async def start_single_competition(
    bengin_info: BikeBeginInfo,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await start_single_competition_service(db, auth.payload["user_id"], bengin_info)
    return BaseResponse.success(token=auth.new_token, message=f"比赛已开始", data=None)


# 结束单人比赛
@router.post("/finish_single_competition",response_model=BaseResponse[None],summary="结束单人比赛")
async def finish_single_competition(
    finish_info: BikeFinishInfo,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await finish_single_competition_service(db, finish_info, auth.payload["user_id"])
    return BaseResponse.success(token=auth.new_token, message=f"比赛已结束", data=None)


# 检查是否可以进入组队比赛链路
@router.post("/enter_team_competition_link",response_model=BaseResponse[None],summary="进入组队比赛链路")
async def enter_team_competition_link(
    record_id: str = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await enter_team_competition_link_service(db, record_id)
    return BaseResponse.success(token=auth.new_token)


# 开始组队比赛
@router.post("/start_team_competition",response_model=BaseResponse[None],summary="开始组队比赛")
async def start_team_competition(
    bengin_info: BikeBeginInfo,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await start_team_competition_service(db, auth.payload["user_id"], bengin_info)
    return BaseResponse.success(token=auth.new_token, message=f"比赛已开始", data=None)


# 结束组队比赛
@router.post("/finish_team_competition",response_model=BaseResponse[None],summary="结束组队比赛")
async def finish_team_competition(
    finish_info: BikeFinishInfo,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await finish_team_competition_service(db, finish_info, auth.payload["user_id"])
    return BaseResponse.success(token=auth.new_token, message=f"比赛已结束", data=None)


@router.get("/query_team_expired_date",response_model=BaseResponse[BikeTeamExpiredResponse],summary="查询队伍比赛窗口过期时间")
async def query_team_expired_date(
    record_id: str = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    date = await get_team_expired_date_service(db, record_id)
    return BaseResponse.success(token=auth.new_token, data=date)


@router.get("/query_incompleted_records",response_model=BaseResponse[BikeRecordResponse],summary="查询当前赛季未开始记录")
async def query_incompleted_records(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    records = await get_incompleted_records_all(db, auth.payload["user_id"], page, size)
    return BaseResponse.success(token=auth.new_token, data=BikeRecordResponse(records=records))


@router.get("/query_completed_records",response_model=BaseResponse[BikeRecordResponse],summary="查询当前赛季已结束记录")
async def query_completed_records(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    records = await get_completed_records_all(db, auth.payload["user_id"], page, size)
    return BaseResponse.success(token=auth.new_token, data=BikeRecordResponse(records=records))


# 查询我的排名信息
@router.get("/query_me_rank",response_model=BaseResponse[BikeRankInfo],summary="查询当前我的排名")
async def query_me_rank(
    track_id: str = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    rank_info = await query_user_rank_info(db, auth.payload["user_id"], track_id)
    return BaseResponse.success(token=auth.new_token, data=rank_info)


# 查询实时排名榜
@router.get("/query_leaderboads",response_model=BaseResponse[BikeLeaderboardResponse],summary="查询当前实时排行榜")
async def query_leaderboads(
    track_id: str = Query(...),
    gender: Gender = Query(...),
    time_stamp: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1),
    db: AsyncSession = Depends(get_db)
):
    rank_info = await query_leaderboard_in_page(db, track_id, gender, page, size, time_stamp)
    return BaseResponse.success(data=rank_info)


# 查询历史排名榜
@router.get("/query_leaderboads_history",response_model=BaseResponse[BikeLeaderboardResponse],summary="查询历史排行榜")
async def query_leaderboads(
    track_id: str = Query(...),
    gender: Gender = Query(...),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1),
    db: AsyncSession = Depends(get_db)
):
    rank_info = await query_leaderboard_history_in_page(db, track_id, gender, page, size)
    return BaseResponse.success(data=rank_info)

# 查询赛季积分排名榜
@router.get("/query_score_leaderboard",response_model=BaseResponse[BikeScoreLeaderboardResponse],summary="查询赛季积分排行榜")
async def query_score_leaderboard(
    season_id: str = Query(...),
    gender: Gender = Query(...),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1),
    db: AsyncSession = Depends(get_db)
):
    rank_info = await get_score_leaderboard_service(db, season_id, gender, page, size)
    return BaseResponse.success(data=rank_info)

@router.post("/create_team",response_model=BaseResponse[BikeTeamCreateResponse],summary="创建队伍")
async def create_team(
    create_info: BikeTeamCreateInfo,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    response = await create_team_service(db, create_info, auth.payload["user_id"])
    return BaseResponse.success(token=auth.new_token, message="创建成功,队伍码已复制", data=response)


@router.get("/query_public_teams",response_model=BaseResponse[BikeAppliedTeamResponse],summary="查询公开的队伍信息")
async def query_public_teams(
    track_id: str = Query(...),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1),
    db: AsyncSession = Depends(get_db)
):
    teams = await get_public_teams_service(db, track_id, page, size)
    return BaseResponse.success(data=teams)


@router.get("/query_created_teams",response_model=BaseResponse[BikeTeamResponse],summary="查询已创建队伍信息")
async def query_created_teams(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    teams = await get_user_teams(db, auth.payload["user_id"], TeamRelationship.created, page, size)
    return BaseResponse.success(token=auth.new_token, data=teams)


@router.get("/query_applied_teams",response_model=BaseResponse[BikeAppliedTeamResponse],summary="查询已申请队伍信息")
async def query_applied_teams(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    teams = await get_user_applied_teams(db, auth.payload["user_id"], page, size)
    return BaseResponse.success(token=auth.new_token, data=teams)


@router.get("/query_joined_teams",response_model=BaseResponse[BikeTeamResponse],summary="查询已加入队伍信息")
async def query_joined_teams(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    teams = await get_user_teams(db, auth.payload["user_id"], TeamRelationship.joined, page, size)
    return BaseResponse.success(token=auth.new_token, data=teams)


@router.get("/query_team_detail",response_model=BaseResponse[BikeTeamDetailResponse],summary="查询队伍详细信息")
async def query_team_detail(
    team_id: str = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    info = await get_team_detail_service(db, team_id)
    return BaseResponse.success(token=auth.new_token, data=info)


@router.get("/query_team_manage",response_model=BaseResponse[BikeTeamManageResponse],summary="查询队伍管理信息")
async def query_team_manage(
    team_id: str = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    info = await get_team_manage_service(db, team_id)
    return BaseResponse.success(token=auth.new_token, data=info)


@router.post("/update_team_info",response_model=BaseResponse[BikeTeamUpdateResponse],summary="更新队伍信息")
async def update_team_info(
    create_info: BikeTeamUpdateInfo,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    response = await update_team_info_service(db, auth.payload["user_id"], create_info)
    return BaseResponse.success(token=auth.new_token, message="保存成功", data=response)


@router.post("/update_team_public_status",response_model=BaseResponse[bool],summary="更新队伍公开状态")
async def update_team_public_status(
    update_info: BikeTeamStatusUpdateInfo,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    new_status = await update_team_public_status_service(db, auth.payload["user_id"], update_info)
    return BaseResponse.success(token=auth.new_token, message="队伍已公开" if new_status else "队伍已关闭公开状态", data=new_status)


@router.post("/update_team_lock_status",response_model=BaseResponse[bool],summary="更新队伍锁定状态")
async def update_team_lock_status(
    update_info: BikeTeamStatusUpdateInfo,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    new_status = await update_team_lock_status_service(db, auth.payload["user_id"], update_info)
    return BaseResponse.success(token=auth.new_token, message="队伍已锁定" if new_status else "队伍已解锁", data=new_status)


@router.post("/update_team_ready_status",response_model=BaseResponse[bool],summary="更新队伍比赛状态")
async def update_team_ready_status(
    team_id: str = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    new_status = await update_team_ready_status_service(db, auth.payload["user_id"], team_id)
    return BaseResponse.success(token=auth.new_token, message="队伍已进入比赛状态" if new_status else "状态修改失败", data=new_status)


@router.post("/disband_team",response_model=BaseResponse[CPAssetResponse],summary="解散队伍")
async def disband_team(
    team_id: str = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    response = await disband_team_service(db, auth.payload["user_id"], team_id)
    return BaseResponse.success(token=auth.new_token, message="队伍已解散", data=response)


@router.post("/remove_team_member",response_model=BaseResponse[BikeTeamMembersResponse],summary="移除队员")
async def remove_team_member(
    team_id: str = Query(...),
    member_id: str = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    response = await remove_team_member_service(db, auth.payload["user_id"], team_id, member_id)
    return BaseResponse.success(token=auth.new_token, message="移除成功", data=response)


@router.post("/approve_applied_request",response_model=BaseResponse[BikeTeamMembersResponse],summary="同意加入队伍申请")
async def approve_applied_request(
    team_id: str = Query(...),
    member_id: str = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    response = await approve_applied_request_service(db, auth.payload["user_id"], team_id, member_id)
    return BaseResponse.success(token=auth.new_token, message="已同意", data=response)


@router.post("/reject_applied_request",response_model=BaseResponse[None],summary="拒绝加入队伍申请")
async def reject_applied_request(
    team_id: str = Query(...),
    member_id: str = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await reject_applied_request_service(db, auth.payload["user_id"], team_id, member_id)
    return BaseResponse.success(token=auth.new_token, message="已拒绝")


@router.post("/quit_team",response_model=BaseResponse[None],summary="退出队伍")
async def quit_team(
    team_id: str = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await quit_team_service(db, auth.payload["user_id"], team_id)
    return BaseResponse.success(token=auth.new_token, message="退出成功")


@router.post("/join_team",response_model=BaseResponse[None],summary="加入队伍")
async def join_team(
    team_code: str = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await join_team_service(db, auth.payload["user_id"], team_code)
    return BaseResponse.success(token=auth.new_token, message="加入队伍成功")


@router.post("/applied_join_team",response_model=BaseResponse[None],summary="申请加入队伍")
async def applied_join_team(
    request: BikeTeamAppliedRequest,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await applied_join_team_service(db, auth.payload["user_id"], request)
    return BaseResponse.success(token=auth.new_token, message="申请成功")


@router.post("/cancel_applied_join_team",response_model=BaseResponse[None],summary="取消加入队伍申请")
async def cancel_applied_join_team(
    team_id: str = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await cancel_applied_join_team_service(db, auth.payload["user_id"], team_id)
    return BaseResponse.success(token=auth.new_token, message="取消成功")


@router.get("/query_record_detail",response_model=BaseResponse[BikeRecordDetailInfo],summary="查询比赛记录详情")
async def query_record_detail(
    record_id: str = Query(...),
    user_id: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    detail = await get_record_detail_service(db, record_id, user_id)
    return BaseResponse.success(data=detail)

@router.get("/query_user_current_best_records",response_model=BaseResponse[BikeSummaryRecordResponse],summary="查询任意用户当前赛季最佳记录")
async def query_user_current_best_records(
    user_id: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    records = await get_current_best_records_service(db, user_id)
    return BaseResponse.success(data=records)

@router.get("/query_me_current_best_records",response_model=BaseResponse[BikeSummaryRecordResponse],summary="查询自己当前赛季最佳记录")
async def query_me_current_best_records(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    records = await get_current_best_records_service(db, auth.payload["user_id"])
    return BaseResponse.success(token=auth.new_token, data=records)

@router.get("/query_history_seasons",response_model=BaseResponse[BikeHistorySeasonResponse],summary="查询历史赛季信息")
async def query_history_seasons(
    db: AsyncSession = Depends(get_db)
):
    seasons = await get_history_seasons_service(db)
    return BaseResponse.success(data=seasons)

@router.get("/query_user_career_records",response_model=BaseResponse[BikeCareerRecordResponse],summary="查询任意用户历史赛季记录")
async def query_user_career_records(
    season_id: str = Query(...),
    user_id: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    records = await get_career_records_service(db, season_id, user_id)
    return BaseResponse.success(data=records)

@router.get("/query_me_career_records",response_model=BaseResponse[BikeCareerRecordResponse],summary="查询自己历史赛季最佳记录")
async def query_me_career_records(
    season_id: str = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    records = await get_career_records_service(db, season_id, auth.payload["user_id"])
    return BaseResponse.success(token=auth.new_token, data=records)

@router.get("/query_user_career_data",response_model=BaseResponse[BikeCareerDataInfo],summary="查询用户历史赛季总结数据")
async def query_user_career_data(
    season_id: str = Query(...),
    user_id: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    records = await get_career_data_service(db, season_id, user_id)
    return BaseResponse.success(data=records)

@router.get("/query_me_career_data",response_model=BaseResponse[BikeCareerDataInfo],summary="查询我的历史赛季总结数据")
async def query_me_career_data(
    season_id: str = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    records = await get_career_data_service(db, season_id, auth.payload["user_id"])
    return BaseResponse.success(data=records)