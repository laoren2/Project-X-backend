from sqlalchemy.ext.asyncio import AsyncSession
from app.core.tools import get_user_local_date
from app.schemas.common import CCAssetRewardResponse, CCAssetType
from app.schemas.asset import AssetOperation
from app.services.competition.common import compute_distance
from app.crud.competition.bike import get_season_now, get_score_by_season_and_user, add_or_update_career_xp
from app.db.models.user import User
from app.schemas.base import BizException, Language, pick_i18n_text
from app.schemas.user import Gender
from app.schemas.training.bike import (
    FreeTrainingFinishInfo, FreeTrainingFinishResponse, TrainingStatesHistoryResponse,
    TrainingStatesHistoryInfo, TrainingRecordsResponse, TrainingRecordInfo,
    BikeTrainingPathPoint, FreeTrainingRecordDetailResponse
)
from app.schemas.training.common import RegionExploreResponse, GridTileKey, GridTileResponse
from app.crud.training.bike import (
    get_training_states_by_user_and_month, get_training_records_by_user_and_day,
    add_or_update_daily_training_states, get_training_state_by_user, update_grid_familiarity_by_path,
    get_region_explored_grid_count, get_record_by_record_id, get_training_state_daily_by_user_date,
    get_familiarity_grids_by_tiles
)
from app.db.models.training import UserTrainingStateDailyBike, BikeFreeTrainingPath, BikeFreeTrainingRecord, UserTrainingStateBike
from sqlalchemy.dialects.postgresql import insert
from app.crud.user import get_user_by_id
from app.crud.asset_manage import reward_ccasset
from app.crud.competition.common import get_region_boundary_geojson_by_region_id, get_region_by_coordinate
from app.core.errors import ErrorCode
from sqlalchemy import text, func
from datetime import date, datetime, timedelta
from typing import List
import math, uuid, logging, random

logger = logging.getLogger(__name__)


async def finish_free_training_service(db: AsyncSession, info: FreeTrainingFinishInfo, user_id: str) -> FreeTrainingFinishResponse:
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
        season = await get_season_now(db)
        if not season:
            raise BizException(code=ErrorCode.SEASON_ERROR, message="season.out_of_season")
        state, _ = await compute_training_decay(db, user, True)

        # 检查记录合理性(时间过短 < 30s or 距离过短 < 100m 则不进行记录)
        duration = (info.end_time - info.start_time).total_seconds()
        distance = compute_distance([p.base for p in info.path])
        if duration < 30 or distance < 0.1:
            raise BizException(code=ErrorCode.RECORD_ERROR, message="record.invalid.too_short")
        
        # 更新地图熟悉度
        new_grids = await update_grid_familiarity(db, season.id, user.id, info.path)

        # 计算并更新 xp 和 训练状态 奖励，可以根据整体的训练距离、海拔累计落差、是否有心率数据等信息进行计算，xp控制在 0-50，training_state控制在 0-10
        xp_before, xp_delta, training_state_before, training_state_delta, cc_rewards = await apply_training_rewards(db, season.id, user, info, state, new_grids)

        # 写入记录
        path_data = [p.model_dump() for p in info.path]
        path = BikeFreeTrainingPath(
            path_id=f"path_{uuid.uuid4()}",
            path=path_data
        )
        db.add(path)
        await db.flush()

        settlements = {
            "xp": xp_delta,
            "training_state": training_state_delta
        }
        for ccasset in cc_rewards:
            settlements[f"{ccasset.ccasset_type.value}"] = ccasset.reward_amount
        record = BikeFreeTrainingRecord(
            record_id=f"record_{uuid.uuid4()}",
            user_id=user.id,
            path_id=path.id,
            start_time = info.start_time,
            end_time = info.end_time,
            duration_seconds = duration,
            local_date = get_user_local_date(user, info.end_time),
            settlement_rewards = settlements
        )
        db.add(record)

        return FreeTrainingFinishResponse(
            record_id=record.record_id,
            xp_before=xp_before,
            xp_delta=xp_delta,
            training_state_before=training_state_before,
            training_state_delta=training_state_delta,
            new_grids=new_grids,
            cc_rewards=cc_rewards
        )


async def apply_training_rewards(
    db: AsyncSession,
    season_id: uuid.UUID,
    user: User,
    info: FreeTrainingFinishInfo,
    state: UserTrainingStateBike | None,
    new_grids: int
) -> tuple[int, int, int, int, List[CCAssetRewardResponse]]:
    gender = user.real_name_info.gender if user.real_name_info else Gender.male
    season_data = await get_score_by_season_and_user(db, user.id, season_id)
    current_xp = season_data.xp if season_data else 0

    has_bpm = False
    has_power = False
    has_pedal = False
    duration = (info.end_time - info.start_time).total_seconds()
    altitude_sum = 0.0
    last_altitude = info.path[0].base.altitude
    for point in info.path:
        altitude_sum += abs(point.base.altitude - last_altitude)
        last_altitude = point.base.altitude
        if point.base.heart_rate:
            has_bpm = True
        if point.power:
            has_power = True
        if point.pedal_cadence:
            has_pedal = True
    
    # 计算XP
    # 1 基础XP
    BASE_XP = 10

    # 2 段位衰减
    tier = current_xp // 100
    rank_factor = max(0.3, 1 - tier * 0.03)

    # 3 距离奖励
    distance_factor = 1.0
    distance = compute_distance([p.base for p in info.path])
    if distance > 5:
        distance_factor += min(1.0, (distance - 5) / 45)

    # 4 累计海拔奖励
    altitude_factor = 1.0
    altitude_factor += min(0.2, 0.2 * altitude_sum / 1000)

    # 5 心率、功率数据额外奖励
    extra_data_factor = 1.0
    if has_bpm or has_power or has_pedal:
        extra_data_factor += 0.1

    # 6 最终XP
    xp = BASE_XP * rank_factor * distance_factor * altitude_factor * extra_data_factor
    xp = int(round(xp)) + new_grids
    xp = max(0, min(50, xp))
    await add_or_update_career_xp(db, season_id, gender, user.id, xp)

    # 计算金币奖励
    cc_rewards = []
    coin = 0
    for _ in range(new_grids):
        r = random.random()
        if r < 0.75:
            coin += 1
        elif r < 0.95:
            coin += 2
        else:
            coin += 4
    if coin > 0:
        new_coin = await reward_ccasset(db, CCAssetType.COIN, coin, user.id, "bike训练结算", AssetOperation.REWARD)
        cc_rewards.append(CCAssetRewardResponse(
            ccasset_type=CCAssetType.COIN,
            new_ccamount=new_coin,
            reward_amount=coin
        ))

    # 计算运动状态
    state_value = 1
    state_distance = min(3, int(distance // 10))
    state_duration = min(3, int(duration // 1200))
    state_value += state_distance + state_duration + (1 if has_bpm else 0) + (1 if has_power else 0) + (1 if has_pedal else 0)

    current_state = 0
    new_value = min(20, state_value)
    finish_date = get_user_local_date(user, info.end_time)
    if not state:
        new_state = UserTrainingStateBike(
            user_id = user.id,
            current_value = new_value,
            last_training_at = info.end_time,
            last_decay_date = None
        )
        db.add(new_state)
    else:
        current_state = state.current_value
        today_state = await get_training_state_daily_by_user_date(db, user.id, finish_date)
        already = today_state.delta if today_state else 0
        remaining = max(0, 20 - already)        # 每日上限为 20
        state_value = min(remaining, state_value)

        new_value = min(100, current_state + state_value)
        state_value = new_value - current_state
        state.current_value = new_value
        state.last_training_at = info.end_time
    await add_or_update_daily_training_states(db, user.id, finish_date, state_value, new_value)

    return current_xp, xp, current_state, state_value, cc_rewards


async def query_training_states_history_service(db: AsyncSession, month: str, user_id: str) -> TrainingStatesHistoryResponse:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
    history = await get_training_states_by_user_and_month(db, user.id, month)
    result = []
    for item in history:
        result.append(TrainingStatesHistoryInfo(
            date=item.local_date.strftime("%Y-%m-%d"),
            delta_state=item.delta
        ))
    return TrainingStatesHistoryResponse(history=result)

async def query_training_records_service(db: AsyncSession, day: str, user_id: str) -> TrainingRecordsResponse:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
    records = await get_training_records_by_user_and_day(db, user.id, day)
    result = []
    for record in records:
        if "training_state" in record.settlement_rewards:
            result.append(TrainingRecordInfo(
                record_id=record.record_id,
                delta_state=record.settlement_rewards["training_state"],
                end_time=record.end_time.isoformat()
            ))
    return TrainingRecordsResponse(records=result)

# 计算/应用训练状态衰减
async def compute_training_decay(
    db: AsyncSession,
    user: User,
    is_apply: bool
) -> tuple[UserTrainingStateBike | None, int]:
    today = get_user_local_date(user)
    state = await get_training_state_by_user(db, user.id)
    if not state or not state.last_training_at:
        return state, 0

    last_training_date = get_user_local_date(user, state.last_training_at)
    inactive_days = (today - last_training_date).days

    # 未达到衰减条件
    if inactive_days <= 7:
        return state, state.current_value

    # 第一次衰减起点
    decay_start = last_training_date + timedelta(days=6)

    # 上次衰减日期
    last_decay_date = state.last_decay_date or decay_start
    last_decay_date = max(last_decay_date, decay_start)

    decay_days = (today - last_decay_date).days - 1

    if decay_days <= 0:
        return state, state.current_value

    # 当前状态
    value = state.current_value
    for i in range(1, decay_days + 1):
        decay_date = last_decay_date + timedelta(days=i)
        new_value = max(0, value - 5)
        delta = new_value - value
        if delta == 0:
            break
        value = new_value
        if is_apply:
            await add_or_update_daily_training_states(db, user.id, decay_date, delta, new_value)
    # 更新总状态
    if is_apply:
        state.current_value = value
        state.last_decay_date = last_decay_date + timedelta(days=decay_days)
    return state, value

# 查询运动状态
async def query_training_states_service(db: AsyncSession, user_id_from: str | None, user_id_to: str) -> int:
    async with db.begin():
        user = await get_user_by_id(db, user_id_to)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
        is_self = user_id_from == user_id_to
        _, state_value = await compute_training_decay(db, user, is_self)
        return state_value
    
# 查询 region 探索度
async def query_region_exploration_service(
    db: AsyncSession,
    user_id: str,
    region_id: str
) -> RegionExploreResponse:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
    season = await get_season_now(db)
    if season is None:
        raise BizException(code=ErrorCode.SEASON_ERROR, message="season.not_found")
    # 1 获取region & boundary (GeoJSON)
    region, boundary_geojson = await get_region_boundary_geojson_by_region_id(db, region_id)
    if region is None or boundary_geojson is None:
        raise BizException(code=ErrorCode.REGION_ERROR, message="region.not_found")

    # 2 统计探索grid数量
    explored_grids = await get_region_explored_grid_count(db, region.id, season.id, user.id)

    # 3 获取总grid数量
    total_grids = region.grid_count

    # 4 计算进度
    #progress = 0.0
    #if total_grids > 0:
    #    progress = min(explored_grids / total_grids, 1.0)

    return RegionExploreResponse(
        explored_grids=explored_grids,
        total_grids=total_grids,
        boundary=boundary_geojson
    )

# 根据训练路线，计算覆盖的网格，更新 user_grid_familiarity_bike 表
async def update_grid_familiarity(
    db: AsyncSession,
    season_id: uuid.UUID,
    user_id: uuid.UUID,
    path: List[BikeTrainingPathPoint],
) -> int:
    # 将自定义路径点转换为 LINESTRING WKT
    if len(path) < 2:
        return

    coordinates = []
    for p in path:
        lat = p.base.lat
        lon = p.base.lon
        coordinates.append(f"{lon} {lat}")  # 注意: WKT 是 lon lat

    if len(coordinates) < 2:
        return

    linestring_wkt = f"LINESTRING({', '.join(coordinates)})"
    return await update_grid_familiarity_by_path(db, season_id, user_id, linestring_wkt)

async def query_free_training_record_detail_service(
    db: AsyncSession,
    user_id: str,
    record_id: str
) -> FreeTrainingRecordDetailResponse:
    record = await get_record_by_record_id(db, record_id)
    if record is None:
        raise BizException(code=ErrorCode.RECORD_ERROR, message="record.not_found")
    path_points = []
    if record.path and record.path.path:
        try:
            path_points = []
            for point_data in record.path.path:
                # 注意兼容新旧数据格式
                path_points.append(BikeTrainingPathPoint.model_validate(point_data))
        except Exception:
            logger.exception("Handle path data failed in querying record detail info")
            path_points = []
    duration = (record.end_time - record.start_time).total_seconds()
    return FreeTrainingRecordDetailResponse(
        duration=duration,
        path=path_points,
        settlements=record.settlement_rewards
    )

async def query_familiarity_grids_by_tiles_service(
    db: AsyncSession,
    user_id: str,
    tiles: List[GridTileKey]
) -> GridTileResponse:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
    season = await get_season_now(db)
    if season is None:
        raise BizException(code=ErrorCode.SEASON_ERROR, message="season.not_found")
    return await get_familiarity_grids_by_tiles(db, user.id, season.id, tiles)