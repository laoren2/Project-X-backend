from fastapi import APIRouter, Depends, Query
from app.api.deps import get_current_user, get_language, Language
from app.schemas.base import BaseResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.user import AuthContext
from app.schemas.training.bike import (
    FreeTrainingFinishInfo, FreeTrainingFinishResponse, TrainingStatesHistoryResponse,
    TrainingRecordsResponse, FreeTrainingRecordDetailResponse
)
from app.schemas.training.common import RegionExploreResponse, GridTileResponse, GridTileRequest
from app.services.training.bike import (
    finish_free_training_service, query_training_states_history_service, query_training_records_service,
    query_training_states_service, query_region_exploration_service, query_free_training_record_detail_service,
    query_familiarity_grids_by_tiles_service
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

# 查询训练记录
@router.get("/training_records/day",response_model=BaseResponse[TrainingRecordsResponse],summary="查询训练记录")
async def query_training_records(
    day: str = Query(...),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    records = await query_training_records_service(db, day, auth.payload["user_id"])
    return BaseResponse.success(token=auth.new_token, data=records)

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
@router.post("/query_grid_tiles",response_model=BaseResponse[GridTileResponse],summary="查询熟悉度网格 tiles")
async def query_grid_tiles(
    request: GridTileRequest,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await query_familiarity_grids_by_tiles_service(db, auth.payload["user_id"], request.tiles)
    return BaseResponse.success(token=auth.new_token, data=result)