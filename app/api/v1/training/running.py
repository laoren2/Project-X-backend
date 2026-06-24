from fastapi import APIRouter, Depends, Query
from app.api.deps import get_current_user, get_language, Language
from app.schemas.base import BaseResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.common import CPAssetCoverInfo, PaceBaselineResponse
from app.schemas.asset import CPAssetResponse
from app.schemas.user import AuthContext, Gender
from app.schemas.training.running import (
    FreeTrainingFinishInfo, FreeTrainingFinishResponse, RunningGridInfoResponse, TrainingStatesHistoryResponse,
    TrainingRecordsResponse, FreeTrainingRecordDetailResponse, CreateRouteRequest, UpdateRouteRequest,
    RunningRouteInfoResponse, RunningRouteManageInfoResponse, RouteTrainingFinishInfo, RouteTrainingFinishResponse,
    RouteTrainingRecordDetailResponse, RunningRouteRanklistResponse, RunningGridTileResponse, RunningRouteRankInfo,
    RouteTrackApplyRequest, RunningNearbyGridsResponse
)
from app.schemas.training.common import (
    RegionExploreResponse, GridTileRequest,
    GridFamiliarityMeResponse, GridFamiliarityRankListResponse, RouteSortType, GridOccupancyResponse, WeeklyTrainingSummaryResponse
)
from app.services.training.running import (
    finish_free_training_service, query_training_states_history_service, query_training_records_service,
    query_training_states_service, query_region_exploration_service, query_free_training_record_detail_service,
    query_grids_info_by_tiles_service, query_me_familiarity_by_grid, query_familiarity_ranking_by_grid,
    create_training_route_service, update_training_route_service, query_routes_service, query_my_routes_service, delete_route_service,
    finish_route_training_service, query_route_training_record_detail_service, get_route_card_info_service,
    query_route_ranklist_service, query_grid_info_service, query_route_ranklist_me_service,
    apply_route_to_track_service, get_route_pace_baseline_service, query_nearby_grids_service,
    query_grids_within_distance_service, query_occupied_grids_count, query_weekly_training_summary_service
)

router = APIRouter(dependencies=[Depends(get_language)])

# 结束自由训练
@router.post("/finish_free_training",response_model=BaseResponse[FreeTrainingFinishResponse],summary="结束自由训练")
async def finish_free_training(
    finish_info: FreeTrainingFinishInfo,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await finish_free_training_service(db, finish_info, auth.payload["user_id"])
    return BaseResponse.success(token=auth.new_token, data=result)

# 查询训练状态历史
@router.get("/training_states/month",response_model=BaseResponse[TrainingStatesHistoryResponse],summary="查询训练状态历史")
async def query_training_states_history(
    month: str = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    history = await query_training_states_history_service(db, month, auth.payload["user_id"])
    return BaseResponse.success(token=auth.new_token, data=history)

# 查询训练记录（user_id 缺省为本人；传入可查他人）
@router.get("/training_records/day",response_model=BaseResponse[TrainingRecordsResponse],summary="查询训练记录")
async def query_training_records(
    day: str = Query(...),
    user_id: str | None = Query(None),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    records = await query_training_records_service(db, day, user_id or auth.payload["user_id"])
    return BaseResponse.success(token=auth.new_token, data=records)

# 查询最近 7 天训练汇总（user_id 缺省为本人；传入可查他人）
@router.get("/weekly_training_summary",response_model=BaseResponse[WeeklyTrainingSummaryResponse],summary="查询最近7天训练汇总")
async def weekly_training_summary(
    user_id: str | None = Query(None),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await query_weekly_training_summary_service(db, auth.payload["user_id"], user_id)
    return BaseResponse.success(token=auth.new_token, data=result)

# 查询我的当前训练状态
@router.get("/training_states/me",response_model=BaseResponse[int],summary="查询我的当前训练状态")
async def query_me_training_states(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    user_id = auth.payload["user_id"]
    value = await query_training_states_service(db, user_id, user_id)
    return BaseResponse.success(token=auth.new_token, data=value)

# 查询用户当前训练状态
@router.get("/training_states/user",response_model=BaseResponse[int],summary="查询用户当前训练状态")
async def query_user_training_states(
    user_id_from: str = Query(None),
    user_id_to: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    value = await query_training_states_service(db, user_id_from, user_id_to)
    return BaseResponse.success(data=value)

# 查询 region 探索度
@router.get("/query_region_exploration",response_model=BaseResponse[RegionExploreResponse],summary="查询 region 探索度")
async def query_region_exploration(
    region_id: str = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await query_region_exploration_service(db, auth.payload["user_id"], region_id)
    return BaseResponse.success(token=auth.new_token, data=result)

# 查询 free training 记录详情
@router.get("/query_free_training_record_detail",response_model=BaseResponse[FreeTrainingRecordDetailResponse],summary="查询 free training 记录详情")
async def query_free_training_record_detail(
    record_id: str = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await query_free_training_record_detail_service(db, auth.payload["user_id"], record_id)
    return BaseResponse.success(token=auth.new_token, data=result)

# 查询熟悉度网格 tiles
@router.post("/query_grid_tiles",response_model=BaseResponse[RunningGridTileResponse],summary="查询熟悉度网格 tiles")
async def query_grid_tiles(
    request: GridTileRequest,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await query_grids_info_by_tiles_service(db, auth.payload["user_id"], request.region_id, request.tiles)
    return BaseResponse.success(token=auth.new_token, data=result)

# 查询我的网格熟悉度状态
@router.get("/query_grid_familiarity_me",response_model=BaseResponse[GridFamiliarityMeResponse],summary="查询我的网格熟悉度状态")
async def query_grid_familiarity_me(
    grid_x: int = Query(...),
    grid_y: int = Query(...),
    level: int = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await query_me_familiarity_by_grid(db, auth.payload["user_id"], grid_x, grid_y, level)
    return BaseResponse.success(token=auth.new_token, data=result)

# 查询网格熟悉度排行榜
@router.get("/query_grid_familiarity_ranklist",response_model=BaseResponse[GridFamiliarityRankListResponse],summary="查询网格熟悉度排行榜")
async def query_grid_familiarity_ranklist(
    grid_x: int = Query(...),
    grid_y: int = Query(...),
    level: int = Query(...),
    page: int = Query(...),
    size: int = Query(...),
    db: AsyncSession = Depends(get_db)
):
    result = await query_familiarity_ranking_by_grid(db, grid_x, grid_y, level, page, size)
    return BaseResponse.success(data=result)

# 查询网格 buff 信息
@router.get("/query_grid_info",response_model=BaseResponse[RunningGridInfoResponse],summary="查询网格 buff 信息")
async def query_grid_info(
    grid_x: int = Query(...),
    grid_y: int = Query(...),
    level: int = Query(...),
    lang: Language = Depends(get_language),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await query_grid_info_service(db, lang, auth.payload["user_id"], grid_x, grid_y, level)
    return BaseResponse.success(token=auth.new_token, data=result)

# 查询附近的奖励网格（运动中雷达指引）
@router.get("/query_nearby_grids",response_model=BaseResponse[RunningNearbyGridsResponse],summary="查询附近的奖励网格")
async def query_nearby_grids(
    lat: float = Query(...),
    lon: float = Query(...),
    count: int = Query(3),
    lang: Language = Depends(get_language),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await query_nearby_grids_service(db, lang, auth.payload["user_id"], lat, lon, count)
    return BaseResponse.success(token=auth.new_token, data=result)

# 查询附近指定距离内可领取的奖励网格（自由训练页附近网格列表）
@router.get("/query_grids_within_distance",response_model=BaseResponse[RunningNearbyGridsResponse],summary="查询附近指定距离内的奖励网格")
async def query_grids_within_distance(
    lat: float = Query(...),
    lon: float = Query(...),
    distance: float = Query(...),
    lang: Language = Depends(get_language),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await query_grids_within_distance_service(db, lang, auth.payload["user_id"], lat, lon, distance)
    return BaseResponse.success(token=auth.new_token, data=result)

# 查询我已占领的网格数量
@router.get("/query_occupied_grids_count",response_model=BaseResponse[GridOccupancyResponse],summary="查询我已占领的网格数量")
async def query_occupied_grids_count_api(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await query_occupied_grids_count(db, auth.payload["user_id"])
    return BaseResponse.success(token=auth.new_token, data=result)

# 创建训练路线
@router.post("/create_route",response_model=BaseResponse[CPAssetResponse],summary="创建训练路线")
async def create_training_route(
    request: CreateRouteRequest,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await create_training_route_service(db, auth.payload["user_id"], request)
    return BaseResponse.success(token=auth.new_token, data=result)

# 编辑训练路线（仅私有路线）
@router.post("/routes/update",response_model=BaseResponse[None],summary="编辑训练路线")
async def update_training_route(
    request: UpdateRouteRequest,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await update_training_route_service(db, auth.payload["user_id"], request)
    return BaseResponse.success(token=auth.new_token, data=None)

# 查询路线创建卡信息
@router.get("/route_card_info",response_model=BaseResponse[CPAssetCoverInfo],summary="查询路线创建卡信息")
async def query_route_card_info(
    db: AsyncSession = Depends(get_db)
):
    result = await get_route_card_info_service(db)
    return BaseResponse.success(data=result)

# 查询路线排行榜
@router.get("/route_ranklist",response_model=BaseResponse[RunningRouteRanklistResponse],summary="查询路线排行榜")
async def query_route_ranklist(
    route_id: str = Query(...),
    gender: Gender = Query(None),
    limit: int = Query(...),
    cursor: str = Query(None),
    db: AsyncSession = Depends(get_db)
):
    result = await query_route_ranklist_service(db, route_id, gender, limit, cursor)
    return BaseResponse.success(data=result)

# 查询我的路线排行信息
@router.get("/route_ranklist/me",response_model=BaseResponse[RunningRouteRankInfo | None],summary="查询我的路线排行信息")
async def query_route_ranklist(
    route_id: str = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await query_route_ranklist_me_service(db, auth.payload["user_id"], route_id)
    return BaseResponse.success(token=auth.new_token, data=result)

# 分页查询路线
@router.get("/routes",response_model=BaseResponse[RunningRouteInfoResponse],summary="分页查询路线")
async def query_routes(
    region_id: str = Query(...),
    sort_type: RouteSortType = Query(...),
    lat: float = Query(...),
    lng: float = Query(...),
    limit: int = Query(...),
    cursor: str = Query(None),
    db: AsyncSession = Depends(get_db)
):
    result = await query_routes_service(db, region_id, sort_type, lat, lng, limit, cursor)
    return BaseResponse.success(data=result)
    

# 查询我创建的路线
@router.get("/routes/my",response_model=BaseResponse[RunningRouteManageInfoResponse],summary="查询我创建的路线")
async def query_routes(
    page: int = Query(...),
    size: int = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await query_my_routes_service(db, auth.payload["user_id"], page, size)
    return BaseResponse.success(data=result)

# 申请热门路线转为赛道
@router.post("/routes/apply_track",response_model=BaseResponse[None],summary="申请热门路线转为赛道")
async def apply_route_to_track(
    request: RouteTrackApplyRequest,
    auth: AuthContext = Depends(get_current_user),
    lang: Language = Depends(get_language),
    db: AsyncSession = Depends(get_db)
):
    await apply_route_to_track_service(db, auth.payload["user_id"], lang, request)
    return BaseResponse.success(token=auth.new_token, data=None)

# 删除路线
@router.post("/routes/delete",response_model=BaseResponse[None],summary="删除路线")
async def delete_route(
    route_id: str = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await delete_route_service(db, auth.payload["user_id"], route_id)
    return BaseResponse.success(token=auth.new_token, data=None)

# 结束路线训练
@router.post("/finish_route_training",response_model=BaseResponse[RouteTrainingFinishResponse],summary="结束路线训练")
async def finish_route_training(
    finish_info: RouteTrainingFinishInfo,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await finish_route_training_service(db, finish_info, auth.payload["user_id"])
    return BaseResponse.success(token=auth.new_token, data=result)

# 查询路线训练记录详情
@router.get("/query_route_training_record_detail",response_model=BaseResponse[RouteTrainingRecordDetailResponse],summary="查询路线训练记录详情")
async def query_route_training_record_detail(
    record_id: str = Query(...),
    lang: Language = Depends(get_language),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await query_route_training_record_detail_service(db, lang, record_id)
    return BaseResponse.success(token=auth.new_token, data=result)

@router.get("/route_pace_baseline", response_model=BaseResponse[PaceBaselineResponse], summary="查询路线配速基线（实时预测名次 + 自我对比）")
async def route_pace_baseline(
    route_id: str = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await get_route_pace_baseline_service(db, route_id, auth.payload["user_id"])
    return BaseResponse.success(token=auth.new_token, data=result)
