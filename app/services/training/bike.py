from app.core.tools import get_user_local_date, latlon_to_grid, encode_cursor, decode_cursor
from app.core.storage import build_resource_url
from app.core.errors import ErrorCode
from app.schemas.common import CCAssetRewardResponse, CCAssetType, PersonInfoResponse, SportType, CPAssetCoverInfo
from app.schemas.asset import AssetOperation, CPAssetResponse
from app.schemas.training.common import (
    RegionExploreResponse, GridTileKey, GridFamiliarityRankListResponse,
    GridFamiliarityMeResponse, GridFamiliarityRankInfo, RouteSortType, TrainingType
)
from app.schemas.competition.common import CardBonusInfo, PathPoint
from app.schemas.base import BizException, Language, pick_i18n_text
from app.schemas.user import Gender
from app.schemas.training.bike import (
    FreeTrainingFinishInfo, FreeTrainingFinishResponse, TrainingStatesHistoryResponse,
    TrainingStatesHistoryInfo, TrainingRecordsResponse, TrainingRecordInfo,
    BikeFreeTrainingPathPoint, FreeTrainingRecordDetailResponse, CreateRouteRequest, UpdateRouteRequest,
    BikeRouteInfoResponse, BikeRouteInfo, BikeRouteManageInfoResponse, BikeRouteMangeInfo,
    RouteTrainingFinishInfo, RouteTrainingFinishResponse, RouteTrainingRecordDetailResponse,
    BikeRouteTrainingPathPoint, BikeRouteRanklistResponse, BikeRouteRankInfo, BikeGridTileResponse,
    BikeGridInfoResponse, BikeGridDetailInfo, RouteTrackApplyRequest
)
from app.schemas.training.common import RouteApplyStatus
from app.services.common import get_elevation
from app.services.competition.common import compute_distance
from app.services.training.common import (
    validate_route_data, build_geometry, extract_checkpoints_from_route_data, 
    evaluate_route_training_checkpoint_path, extract_path_points
)
from app.services.mappers import equip_card_to_base_info
from app.db.models.user import User
from app.db.models.training import (
    CardBonusInBikeRouteTrainingRecord, UserTrainingStateDailyBike, BikeFreeTrainingPath, BikeFreeTrainingRecord, UserTrainingStateBike,
    BikeTrainingRoute, BikeRouteTrainingPath, BikeRouteTrainingRecord, BikeRouteRanklist, BikeEffectGrid, BikeEffectGridHistory,
    BikeRouteTrackApplication
)
from app.crud.training.bike import (
    get_training_states_by_user_and_month, get_free_training_records_by_user_and_day, get_route_training_records_by_user_and_day,
    add_or_update_daily_training_states, get_training_state_by_user, update_user_familiarity_by_grids,
    get_region_explored_grid_count, get_free_training_record_by_record_id, get_training_state_daily_by_user_date,
    get_grids_info_by_tiles, get_routes_by_page_crud, get_routes_by_uesr_id, get_route_by_route_id,
    get_route_training_record_by_record_id, get_rank_info_by_route_and_user,
    count_route_training_records, count_route_training_records_by_routes,
    create_route_track_application_crud, get_active_application_by_route
)
from app.crud.competition.bike import get_season_now, get_score_by_season_and_user, add_or_update_career_xp
from app.crud.user import get_user_by_id
from app.crud.asset_manage import reward_ccasset, get_equip_card_by_card_id, get_route_card_def, consume_cpasset
from app.crud.competition.common import get_region_by_coordinate, get_region_by_region_id
from sqlalchemy import text, func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, datetime, timedelta
from typing import List
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
import json, uuid, logging, random

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
        new_grids = await update_user_familiarity(db, season.id, user.id, [p.base for p in info.path])

        # 计算并更新 xp 和 训练状态 奖励，可以根据整体的训练距离、海拔累计落差、是否有心率数据等信息进行计算，xp控制在 0-50，training_state控制在 0-10
        xp_before, xp_delta, training_state_before, training_state_delta, base_rewards = await apply_training_rewards(
            db, 
            season.id, 
            user, 
            info.start_time,
            info.end_time,
            info.path,
            state, 
            new_grids
        )

        # buff grids 结算
        triggered_count, buff_rewards, triggered_buffs_data = await apply_buff_grids(db, user, info)

        # 合并相同资产类型奖励，统一结算
        reward_map: dict[CCAssetType, int] = {}

        for reward_type, amount in base_rewards + buff_rewards:
            reward_map[reward_type] = reward_map.get(reward_type, 0) + amount

        cc_rewards: list[CCAssetRewardResponse] = []

        for reward_type, amount in reward_map.items():
            new_amount = await reward_ccasset(
                db,
                reward_type,
                amount,
                user.id,
                "自行车自由训练结算",
                AssetOperation.REWARD
            )
            cc_rewards.append(
                CCAssetRewardResponse(
                    ccasset_type=reward_type,
                    new_ccamount=new_amount,
                    reward_amount=amount
                )
            )

        # 写入记录
        path_data = [p.model_dump() for p in info.path]
        path = BikeFreeTrainingPath(
            path_id=f"free_training_path_{uuid.uuid4()}",
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
            record_id=f"free_training_record_{uuid.uuid4()}",
            user_id=user.id,
            path_id=path.id,
            start_time = info.start_time,
            end_time = info.end_time,
            duration_seconds = duration,
            local_date = get_user_local_date(user, info.end_time),
            settlement_rewards = settlements,
            triggered_buffs = triggered_buffs_data
        )
        db.add(record)

        return FreeTrainingFinishResponse(
            record_id=record.record_id,
            xp_before=xp_before,
            xp_delta=xp_delta,
            training_state_before=training_state_before,
            training_state_delta=training_state_delta,
            new_grids=new_grids,
            triggered_buff_count=triggered_count,
            cc_rewards=cc_rewards
        )


async def apply_buff_grids(
    db: AsyncSession,
    user: User,
    info: FreeTrainingFinishInfo
) -> tuple[int, list[tuple[CCAssetType, int]], list[dict]]:
    # 统计 path 回放依次经过的 grids（仅忽略连续重复 grid）
    # 这里需要保留“重复进入同一 grid”的事件，因为同一个 buff grid 可以在一次运动中多次经过
    passed_grids: list[tuple[int, int, int]] = []
    last_grid = None
    for idx, point in enumerate(info.path):
        gx, gy = latlon_to_grid(point.base.lat, point.base.lon)
        current_grid = (gx, gy)
        # 只忽略连续重复 grid
        if current_grid != last_grid:
            passed_grids.append((gx, gy, idx))
            last_grid = current_grid

    triggered_count: int = 0
    triggered_buffs_data: list[dict] = []
    cc_rewards: list[tuple[CCAssetType, int]] = []

    if passed_grids:
        local_date = get_user_local_date(user, info.end_time)

        # 查询所有经过过的 buff grids（过滤已触发 history）
        unique_grids = list({(gx, gy) for gx, gy, _ in passed_grids})
        effect_stmt = (
            select(BikeEffectGrid)
            .outerjoin(
                BikeEffectGridHistory,
                (
                    (BikeEffectGridHistory.user_id == user.id)
                    & (BikeEffectGridHistory.grid_x == BikeEffectGrid.grid_x)
                    & (BikeEffectGridHistory.grid_y == BikeEffectGrid.grid_y)
                    & (BikeEffectGridHistory.active_date == BikeEffectGrid.active_date)
                )
            )
            .where(
                BikeEffectGrid.active_date == local_date,
                tuple_(BikeEffectGrid.grid_x, BikeEffectGrid.grid_y).in_(unique_grids),
                BikeEffectGridHistory.id.is_(None)
            )
        )

        effect_result = await db.execute(effect_stmt)
        effect_grids = effect_result.scalars().all()

        # 建立 grid -> effect 映射
        # 虽然数据库约束保证唯一，但这里做 map 可以避免 O(n²) 查找
        effect_map = {
            (effect.grid_x, effect.grid_y): effect
            for effect in effect_grids
        }

        triggered_histories = []

        # 按 path 顺序依次处理经过的 buff grid
        for gx, gy, path_index in passed_grids:
            effect = effect_map.get((gx, gy))
            if effect is None:
                continue

            # 只统计到当前 buff grid 为止的 path 数据
            current_path = info.path[: path_index + 1]

            # 当前累计距离（km）
            current_distance = compute_distance([p.base for p in current_path])

            # 当前累计平均速度（km/h）
            current_duration = current_path[-1].base.timestamp - current_path[0].base.timestamp

            current_avg_speed = 0.0
            if current_duration > 0:
                current_avg_speed = current_distance / (current_duration / 3600)

            should_trigger = False
            trigger_value = None
            # distance 条件
            if effect.condition_type.value == "distance":
                min_distance = effect.condition_params.get("sum", 0)
                trigger_value = round(current_distance, 2)
                should_trigger = current_distance >= min_distance
            # speed 条件
            elif effect.condition_type.value == "speed":
                min_speed = effect.condition_params.get("avg", 0)
                trigger_value = round(current_avg_speed, 2)
                should_trigger = current_avg_speed >= min_speed
            # 无条件触发
            elif effect.condition_type.value == "none":
                trigger_value = 1
                should_trigger = True

            if not should_trigger:
                continue

            triggered_buffs_data.append({
                "grid_x": effect.grid_x,
                "grid_y": effect.grid_y,
                "effect_type": effect.effect_type.value,
                "condition_type": effect.condition_type.value,
                "condition_params": effect.condition_params,
                "reward_type": effect.reward_type,
                "reward_count": effect.reward_count,
                "trigger_value": trigger_value
            })

            reward_type = effect.reward_type
            reward_count = effect.reward_count

            ccasset_type = None

            if reward_type == "coin":
                ccasset_type = CCAssetType.COIN
            elif reward_type == "coupon":
                ccasset_type = CCAssetType.COUPON
            elif reward_type == "stone1":
                ccasset_type = CCAssetType.STONE1
            elif reward_type == "stone2":
                ccasset_type = CCAssetType.STONE2
            elif reward_type == "stone3":
                ccasset_type = CCAssetType.STONE3

            if ccasset_type is not None:
                cc_rewards.append((ccasset_type, reward_count))

            # 一旦成功触发，后续同一 grid 不再触发
            triggered_histories.append(
                BikeEffectGridHistory(
                    user_id=user.id,
                    grid_x=effect.grid_x,
                    grid_y=effect.grid_y,
                    active_date=effect.active_date
                )
            )
            # 防止本次训练后续再次触发同一个 grid
            effect_map.pop((gx, gy), None)

        if triggered_histories:
            db.add_all(triggered_histories)
            triggered_count = len(triggered_histories)

    return triggered_count, cc_rewards, triggered_buffs_data


async def apply_training_rewards(
    db: AsyncSession,
    season_id: uuid.UUID,
    user: User,
    start_time: datetime,
    end_time: datetime,
    path: List[BikeFreeTrainingPathPoint],
    state: UserTrainingStateBike | None,
    new_grids: int
) -> tuple[int, int, int, int, list[tuple[CCAssetType, int]]]:
    gender = user.gender if user.gender else Gender.male
    season_data = await get_score_by_season_and_user(db, user.id, season_id)
    current_xp = season_data.xp if season_data else 0

    has_bpm = False
    has_power = False
    has_pedal = False
    duration = (end_time - start_time).total_seconds()
    altitude_sum = 0.0
    last_altitude = path[0].base.altitude
    for point in path:
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
    distance = compute_distance([p.base for p in path])
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
    cc_rewards: list[tuple[CCAssetType, int]] = []
    coin = int(round(10 * distance_factor * altitude_factor * extra_data_factor))
    for _ in range(new_grids):
        r = random.random()
        if r < 0.6:
            coin += 1
        elif r < 0.9:
            coin += 2
        else:
            coin += 4
    if coin > 0:
        cc_rewards.append((CCAssetType.COIN, coin))

    # 计算运动状态
    state_value = 1
    state_distance = min(3, int(distance // 10))
    state_duration = min(3, int(duration // 1200))
    state_value += state_distance + state_duration + (1 if has_bpm else 0) + (1 if has_power else 0) + (1 if has_pedal else 0)

    current_state = 0
    new_value = min(20, state_value)
    finish_date = get_user_local_date(user, end_time)
    if not state:
        new_state = UserTrainingStateBike(
            user_id = user.id,
            current_value = new_value,
            last_training_at = end_time,
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
        state.last_training_at = end_time
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

    free_training_records = await get_free_training_records_by_user_and_day(db, user.id, day)
    route_training_records = await get_route_training_records_by_user_and_day(db, user.id, day)

    # 合并并按结束时间升序排序
    records = []
    for record in free_training_records:
        records.append((record, TrainingType.freeTraining))
    for record in route_training_records:
        records.append((record, TrainingType.routeTraining))
    records.sort(key=lambda x: x[0].end_time)

    result = []
    for record, training_type in records:
        settlement_rewards = record.settlement_rewards or {}
        result.append(TrainingRecordInfo(
            record_id=record.record_id,
            delta_state=settlement_rewards.get("training_state", 0),
            end_time=record.end_time.isoformat(),
            training_type=training_type
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
    # 1 获取region
    region = await get_region_by_region_id(db, region_id)
    if region is None:
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
        total_grids=total_grids
    )

# 根据训练路线，计算覆盖的网格，更新 user_grid_familiarity_bike 表
async def update_user_familiarity(
    db: AsyncSession,
    season_id: uuid.UUID,
    user_id: uuid.UUID,
    path: List[PathPoint],
) -> int:
    if len(path) < 2:
        return 0

    # 构建 grid -> representative point（每个 grid 只保留一个点）
    grid_point_map = {}
    for p in path:
        lat = p.lat
        lon = p.lon
        gx, gy = latlon_to_grid(lat, lon)
        if (gx, gy) not in grid_point_map:
            grid_point_map[(gx, gy)] = (lat, lon)

    point_records = [
        {
            "lat": lat,
            "lng": lng,
            "grid_x": gx,
            "grid_y": gy
        }
        for (gx, gy), (lat, lng) in grid_point_map.items()
    ]

    # 查询每个 point 对应的 region，并直接绑定 grid
    sql = text(
        """
        WITH input_points AS (
            SELECT
                p.lat,
                p.lng,
                p.grid_x,
                p.grid_y,
                ST_SetSRID(ST_MakePoint(p.lng, p.lat), 4326) AS geom
            FROM jsonb_to_recordset(:points_json)
            AS p(lat double precision, lng double precision, grid_x int, grid_y int)
        )
        SELECT DISTINCT
            p.grid_x,
            p.grid_y,
            r.id AS region_id
        FROM input_points p
        JOIN regions r
          ON ST_Contains(r.boundary, p.geom)
        """
    )

    result = await db.execute(
        sql,
        {
            "points_json": json.dumps(point_records)
        }
    )

    grid_region_pairs = [
        (row.grid_x, row.grid_y, row.region_id)
        for row in result.fetchall()
    ]

    if not grid_region_pairs:
        return 0

    return await update_user_familiarity_by_grids(
        db,
        season_id,
        user_id,
        grid_region_pairs
    )

async def query_free_training_record_detail_service(
    db: AsyncSession,
    user_id: str,
    record_id: str
) -> FreeTrainingRecordDetailResponse:
    record = await get_free_training_record_by_record_id(db, record_id)
    if record is None:
        raise BizException(code=ErrorCode.RECORD_ERROR, message="record.not_found")

    path_points = []
    if record.path and record.path.path:
        try:
            for point_data in record.path.path:
                # 注意兼容新旧数据格式
                path_points.append(BikeFreeTrainingPathPoint.model_validate(point_data))
        except Exception:
            logger.exception("Handle path data failed in querying bike free training record detail info")

    duration = (record.end_time - record.start_time).total_seconds()
    return FreeTrainingRecordDetailResponse(
        duration=duration,
        path=path_points,
        settlements=record.settlement_rewards,
        triggered_buffs=record.triggered_buffs or []
    )

# tiles 分块查询
async def query_grids_info_by_tiles_service(
    db: AsyncSession,
    user_id: str,
    region_id: str,
    tiles: List[GridTileKey]
) -> BikeGridTileResponse:
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
        season = await get_season_now(db)
        if season is None:
            raise BizException(code=ErrorCode.SEASON_ERROR, message="season.not_found")
        region = await get_region_by_region_id(db, region_id)
        if region is None:
            raise BizException(code=ErrorCode.REGION_ERROR, message="region.not_found")
        return await get_grids_info_by_tiles(db, user, region, season.id, tiles)


# 查询当前 level grid 包含的所有 buff 信息
async def query_grid_info_service(
    db: AsyncSession,
    lang: Language,
    user_id: str,
    grid_x: int,
    grid_y: int,
    level: int
) -> BikeGridInfoResponse:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")

    local_date = get_user_local_date(user)

    # 当前 level 下一个 grid 覆盖的基础 grid 范围
    base_grid_size = 2 ** level

    min_x = grid_x * base_grid_size
    max_x = min_x + base_grid_size - 1
    min_y = grid_y * base_grid_size
    max_y = min_y + base_grid_size - 1

    stmt = (
        select(BikeEffectGrid)
        .outerjoin(
            BikeEffectGridHistory,
            (
                (BikeEffectGridHistory.user_id == user.id)
                & (BikeEffectGridHistory.grid_x == BikeEffectGrid.grid_x)
                & (BikeEffectGridHistory.grid_y == BikeEffectGrid.grid_y)
                & (BikeEffectGridHistory.active_date == BikeEffectGrid.active_date)
            )
        )
        .where(
            BikeEffectGrid.active_date == local_date,
            BikeEffectGrid.grid_x >= min_x,
            BikeEffectGrid.grid_x <= max_x,
            BikeEffectGrid.grid_y >= min_y,
            BikeEffectGrid.grid_y <= max_y,
            BikeEffectGridHistory.id.is_(None)
        )
        .order_by(
            BikeEffectGrid.grid_x.asc(),
            BikeEffectGrid.grid_y.asc()
        )
    )

    result = await db.execute(stmt)
    grids = result.scalars().all()

    grid_infos = []

    for grid in grids:
        grid_infos.append(
            BikeGridDetailInfo(
                description=pick_i18n_text(grid.description_i18n, lang),
                effect_type=grid.effect_type,
                condition_type=grid.condition_type,
                condition_params=grid.condition_params,
                reward_type=grid.reward_type,
                reward_count=grid.reward_count
            )
        )
    return BikeGridInfoResponse(grids=grid_infos)

# 查询某网格我的访问次数和名次
async def query_me_familiarity_by_grid(
    db: AsyncSession,
    user_id: str,
    grid_x: int,
    grid_y: int,
    level: int
) -> GridFamiliarityMeResponse:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
    season = await get_season_now(db)
    if season is None:
        raise BizException(code=ErrorCode.SEASON_ERROR, message="season.not_found")

    # 查询当前用户该 grid 的次数和更新时间
    sql_count = text(
        """
        SELECT familiarity_count, updated_at
        FROM user_grid_familiarity_bike_agg
        WHERE user_id = :user_id
          AND season_id = :season_id
          AND level = :level
          AND grid_x = :grid_x
          AND grid_y = :grid_y
        """
    )

    result = await db.execute(sql_count, {
        "user_id": user.id,
        "season_id": season.id,
        "level": level,
        "grid_x": grid_x,
        "grid_y": grid_y
    })
    row = result.fetchone()
    count = row.familiarity_count if row else 0
    updated_at = row.updated_at if row else None

    if count == 0:
        return GridFamiliarityMeResponse(count=0, rank=0)

    # 查询排名（比自己大的数量 + 1，若次数相同则按更新时间升序）
    sql_rank = text(
        """
        SELECT COUNT(*) + 1 AS rank
        FROM user_grid_familiarity_bike_agg
        WHERE season_id = :season_id
          AND level = :level
          AND grid_x = :grid_x
          AND grid_y = :grid_y
          AND (
                familiarity_count > :count
                OR (
                    familiarity_count = :count
                    AND updated_at < :updated_at
                )
              )
        """
    )

    result = await db.execute(sql_rank, {
        "season_id": season.id,
        "level": level,
        "grid_x": grid_x,
        "grid_y": grid_y,
        "count": count,
        "updated_at": updated_at
    })
    rank = result.scalar_one()

    return GridFamiliarityMeResponse(count=count, rank=rank)

async def query_familiarity_ranking_by_grid(
    db: AsyncSession,
    grid_x: int,
    grid_y: int,
    level: int,
    page: int,
    size: int
) -> GridFamiliarityRankListResponse:
    season = await get_season_now(db)
    if season is None:
        raise BizException(code=ErrorCode.SEASON_ERROR, message="season.not_found")

    offset = (page - 1) * size

    # 查询排行榜数据（带 rank，按次数降序、更新时间升序，rank为ROW_NUMBER）
    sql = text(
        """
        SELECT 
            u.user_id AS user_id,
            u.avatar_image_url,
            u.nickname,
            f.familiarity_count,
            ROW_NUMBER() OVER (ORDER BY f.familiarity_count DESC, f.updated_at ASC) AS rank
        FROM user_grid_familiarity_bike_agg f
        JOIN users u ON u.id = f.user_id
        WHERE f.season_id = :season_id
          AND f.level = :level
          AND f.grid_x = :grid_x
          AND f.grid_y = :grid_y
        ORDER BY f.familiarity_count DESC, f.updated_at ASC
        LIMIT :limit OFFSET :offset
        """
    )

    result = await db.execute(sql, {
        "season_id": season.id,
        "level": level,
        "grid_x": grid_x,
        "grid_y": grid_y,
        "limit": size,
        "offset": offset
    })

    rows = result.fetchall()

    data = []
    for row in rows:
        data.append(GridFamiliarityRankInfo(
            user=PersonInfoResponse(
                user_id=str(row.user_id),
                avatar_image_url=build_resource_url(row.avatar_image_url),
                nickname=row.nickname
            ),
            count=row.familiarity_count,
            rank=row.rank
        ))

    return GridFamiliarityRankListResponse(data=data)


async def create_training_route_service(db: AsyncSession, user_id: str, data: CreateRouteRequest) -> CPAssetResponse:
    steps = validate_route_data(data.route_type, data.route_data)
    geometry = build_geometry(steps)
    start = steps[0]
    end = steps[-1]

    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
    region = await get_region_by_region_id(db, data.region_id)
    if region is None:
        raise BizException(code=ErrorCode.REGION_ERROR, message="region.not_found")
    is_subscription_active = user.subscription_info.is_active if user.subscription_info else False

    elevation_start = get_elevation(start.lat, start.lng)
    elevation_end = get_elevation(end.lat, end.lng)
    if elevation_start is None or elevation_end is None:
        raise BizException(code=ErrorCode.ROUTE_CREATE_FAILED, message="route.data_error.create")

    path_points = extract_path_points(steps)
    total_distance = compute_distance(path_points)

    if total_distance > 50:
        raise BizException(code=ErrorCode.ROUTE_CREATE_FAILED, message="route.data_error.create")
    
    # 消费路线创建卡
    route_card_def = await get_route_card_def(db, SportType.bike)
    if route_card_def is None:
        raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.data_error")
    new_balance = await consume_cpasset(db, user.id, route_card_def.id, 1, "自行车路线创建")

    route = BikeTrainingRoute(
        route_id=f"route_{uuid.uuid4()}",
        user_id=user.id,
        region_id=region.id,
        route_type=data.route_type,
        route_data=data.route_data,
        route_geometry=from_shape(geometry, srid=4326),
        is_premium=is_subscription_active,
        start_point=from_shape(Point(start.lng, start.lat), srid=4326),
        end_point=from_shape(Point(end.lng, end.lat), srid=4326),
        title=data.title,
        elevation_difference=elevation_end - elevation_start,
        total_distance=total_distance,
        terrain_type=data.terrain_type,
        is_public=data.is_public,
        enable_ranklist=data.enable_ranklist,
        enable_magiccard=data.enable_magiccard
    )
    db.add(route)
    await db.commit()
    return CPAssetResponse(
        asset_id=route_card_def.asset_id,
        new_balance=new_balance
    )

async def update_training_route_service(db: AsyncSession, user_id: str, data: UpdateRouteRequest):
    steps = validate_route_data(data.route_type, data.route_data)
    geometry = build_geometry(steps)
    start = steps[0]
    end = steps[-1]

    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
    route = await get_route_by_route_id(db, data.route_id)
    if route is None or route.user_id != user.id:
        raise BizException(code=ErrorCode.ROUTE_NOT_FOUND, message="route.not_found")
    # 仅私有路线可编辑（公开路线已产生排行榜数据，不允许修改）
    if route.is_public:
        raise BizException(code=ErrorCode.ROUTE_UPDATE_FAILED, message="route.edit_forbidden")
    is_subscription_active = user.subscription_info.is_active if user.subscription_info else False

    elevation_start = get_elevation(start.lat, start.lng)
    elevation_end = get_elevation(end.lat, end.lng)
    if elevation_start is None or elevation_end is None:
        raise BizException(code=ErrorCode.ROUTE_UPDATE_FAILED, message="route.data_error.update")

    path_points = extract_path_points(steps)
    total_distance = compute_distance(path_points)

    if total_distance > 50:
        raise BizException(code=ErrorCode.ROUTE_UPDATE_FAILED, message="route.data_error.update")

    route.route_type = data.route_type
    route.route_data = data.route_data
    route.route_geometry = from_shape(geometry, srid=4326)
    route.is_premium = is_subscription_active
    route.start_point = from_shape(Point(start.lng, start.lat), srid=4326)
    route.end_point = from_shape(Point(end.lng, end.lat), srid=4326)
    route.title = data.title
    route.elevation_difference = elevation_end - elevation_start
    route.total_distance = total_distance
    route.terrain_type = data.terrain_type
    route.is_public = data.is_public
    route.enable_ranklist = data.enable_ranklist
    route.enable_magiccard = data.enable_magiccard
    await db.commit()

async def get_route_card_info_service(db: AsyncSession) -> CPAssetCoverInfo:
    route_card_def = await get_route_card_def(db, SportType.bike)
    if route_card_def is None:
        raise BizException(code=ErrorCode.ASSET_ERROR, message="asset.data_error")
    return CPAssetCoverInfo(
        asset_id=route_card_def.asset_id,
        image_url=build_resource_url(route_card_def.image_url)
    )

async def query_routes_service(
    db: AsyncSession,
    region_id: str,
    sort_type: RouteSortType,
    lat: float,
    lng: float,
    limit: int,
    cursor: str | None
) -> BikeRouteInfoResponse:
    region = await get_region_by_region_id(db, region_id)
    if region is None:
        raise BizException(code=ErrorCode.REGION_ERROR, message="region.not_found")

    try:
        cursor_data = decode_cursor(cursor) if cursor else None
        if cursor_data and "created_at" in cursor_data:
            cursor_data["created_at"] = datetime.fromisoformat(cursor_data["created_at"])
    except:
        raise BizException(code=ErrorCode.JSON_DECODE_ERROR, message=f"cursor解析错误")

    rows = await get_routes_by_page_crud(
        db=db,
        region_id=region.id,
        sort_type=sort_type,
        lat=lat,
        lng=lng,
        limit=limit,
        cursor=cursor_data
    )
    routes = []
    next_cursor = None
    for row in rows:
        route = row["BikeTrainingRoute"]
        if sort_type == RouteSortType.participation:
            count = row.get("count")
            next_cursor = {
                "count": count,
                "created_at": route.created_at.isoformat(),
                "route_id": str(route.id)
            }
        elif sort_type == RouteSortType.distance:
            distance = row.get("distance")
            next_cursor = {
                "distance": float(distance),
                "route_id": str(route.id),
                "lat": cursor_data.get("lat") if cursor_data else lat,
                "lng": cursor_data.get("lng") if cursor_data else lng
            }
        routes.append(BikeRouteInfo(
            route_id=route.route_id,
            title=route.title,
            route_type=route.route_type,
            terrain_type=route.terrain_type,
            is_premium=route.is_premium,
            enable_magiccard=route.enable_magiccard,
            distance=row.get("distance"),
            total_distance=route.total_distance,
            elevation_diff=route.elevation_difference,
            participate_count=row.get("count"),
            route_data=route.route_data
        ))
    # 如果返回数量小于 limit，说明已经到最后一页，不再返回 cursor
    if len(rows) < limit:
        encoded_cursor = None
    else:
        encoded_cursor = encode_cursor(next_cursor) if next_cursor else None
    return BikeRouteInfoResponse(
        routes=routes,
        next_cursor=encoded_cursor
    )


async def query_my_routes_service(
    db: AsyncSession,
    user_id: str,
    page: int,
    size: int
) -> BikeRouteManageInfoResponse:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
    routes = await get_routes_by_uesr_id(db, user.id, page, size)
    count_map = await count_route_training_records_by_routes(db, [route.id for route in routes])
    result = []
    for route in routes:
        result.append(BikeRouteMangeInfo(
            route_id=route.route_id,
            title=route.title,
            is_public=route.is_public,
            route_type=route.route_type,
            terrain_type=route.terrain_type,
            is_premium=route.is_premium,
            enable_magiccard=route.enable_magiccard,
            participate_count=count_map.get(route.id, 0),
            apply_status=route.apply_status,
            route_data=route.route_data
        ))
    return BikeRouteManageInfoResponse(routes=result)


# 申请热门路线转为赛道：仅公开、热度 > 阈值、且无进行中申请的路线可申请
ROUTE_APPLY_MIN_PARTICIPATION = 100

async def apply_route_to_track_service(db: AsyncSession, user_id: str, lang: Language, request: RouteTrackApplyRequest):
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
        route = await get_route_by_route_id(db, request.route_id)
        if route is None or route.user_id != user.id:
            raise BizException(code=ErrorCode.ROUTE_NOT_FOUND, message="route.not_found")
        if not route.is_public:
            raise BizException(code=ErrorCode.ROUTE_APPLY_ERROR, message="route.apply_forbidden")
        # 仅 none / rejected 可再次申请；pending/approved 不可
        if route.apply_status == RouteApplyStatus.pending or await get_active_application_by_route(db, route.id) is not None:
            raise BizException(code=ErrorCode.ROUTE_APPLY_ERROR, message="route.apply_pending")
        if route.apply_status == RouteApplyStatus.approved:
            raise BizException(code=ErrorCode.ROUTE_APPLY_ERROR, message="route.apply_forbidden")
        count = await count_route_training_records(db, route.id)
        if count < ROUTE_APPLY_MIN_PARTICIPATION:
            raise BizException(code=ErrorCode.ROUTE_APPLY_ERROR, message="route.apply_forbidden")

        application = BikeRouteTrackApplication(
            application_id=f"rta_{uuid.uuid4()}",
            route_id=route.id,
            user_id=user.id,
            region_id=route.region_id,
            language=lang.value,
            title=request.title,
            sub_region_name=request.sub_region_name,
            terrain_type=request.terrain_type,
            lifecycle=request.lifecycle,
            # 高级赛道由用户选择，但仅高级路线可申请；普通路线强制为普通赛道
            is_premium=route.is_premium and request.is_premium,
            participate_count=count,
            status=RouteApplyStatus.pending
        )
        await create_route_track_application_crud(db, application)
        route.apply_status = RouteApplyStatus.pending
        db.add(route)

async def delete_route_service(db: AsyncSession, user_id: str, route_id: str):
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
    route = await get_route_by_route_id(db, route_id)
    if route is None:
        raise BizException(code=ErrorCode.ROUTE_NOT_FOUND, message="route.not_found")
    if route.user_id != user.id:
        raise BizException(code=ErrorCode.ROUTE_NOT_FOUND, message="route.not_found")
    await db.delete(route)
    await db.commit()


# 结束路线训练
async def finish_route_training_service(db: AsyncSession, finish_info: RouteTrainingFinishInfo, user_id: str) -> RouteTrainingFinishResponse:
    async with db.begin():
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
        route = await get_route_by_route_id(db, finish_info.route_id)
        if route is None:
            raise BizException(code=ErrorCode.ROUTE_NOT_FOUND, message="route.not_found")
        season = await get_season_now(db)
        if not season:
            raise BizException(code=ErrorCode.SEASON_ERROR, message="season.out_of_season")

        checkpoints = extract_checkpoints_from_route_data(route.route_data)
        total_penalty, path_passes_checkpoints = evaluate_route_training_checkpoint_path([p.base for p in finish_info.path], checkpoints)
        #print(path_passes_checkpoints)
        if not path_passes_checkpoints:
            raise BizException(code=ErrorCode.RECORD_ERROR, message="record.invalid.route_path")

        state, _ = await compute_training_decay(db, user, True)
        new_grids = await update_user_familiarity(db, season.id, user.id, [p.base for p in finish_info.path])
        free_training_path = [BikeFreeTrainingPathPoint(
            base=p.base,
            power=p.power,
            pedal_cadence=p.pedal_cadence
        ) for p in finish_info.path]
        xp_before, xp_delta, training_state_before, training_state_delta, training_rewards = await apply_training_rewards(
            db, 
            season.id, 
            user, 
            finish_info.start_time, 
            finish_info.end_time, 
            free_training_path, 
            state, 
            new_grids
        )

        cc_rewards: list[CCAssetRewardResponse] = []
        for reward_type, amount in training_rewards:
            new_amount = await reward_ccasset(
                db,
                reward_type,
                amount,
                user.id,
                "自行车路线训练结算",
                AssetOperation.REWARD
            )
            cc_rewards.append(
                CCAssetRewardResponse(
                    ccasset_type=reward_type,
                    new_ccamount=new_amount,
                    reward_amount=amount
                )
            )

        path_data = [p.model_dump() for p in finish_info.path]
        path = BikeRouteTrainingPath(
            path_id=f"route_training_path_{uuid.uuid4()}",
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

        original_time = (finish_info.end_time - finish_info.start_time).total_seconds()
        final_time = original_time
        bonus_time = 0

        record = BikeRouteTrainingRecord(
            record_id=f"route_training_record_{uuid.uuid4()}",
            user_id=user.id,
            route_id=route.id,
            path_id=path.id,
            start_time=finish_info.start_time,
            end_time=finish_info.end_time,
            duration_seconds=final_time,
            penalty_seconds=total_penalty,
            local_date=get_user_local_date(user, finish_info.end_time),
            settlement_rewards=settlements
        )
        db.add(record)
        await db.flush()

        for item in finish_info.bonus_in_cards:
            bonus_time += item.bonus_time
            card = await get_equip_card_by_card_id(db, item.card_id)
            if card is not None:
                db.add(CardBonusInBikeRouteTrainingRecord(
                    record_id=record.id,
                    card_id=card.id,
                    bonus_time=item.bonus_time
                ))
        # 卡牌奖励时间上限为20%
        if original_time > 0 and bonus_time / original_time > 0.2:
            final_time = final_time * 0.8
        else:
            final_time -= bonus_time

        record.duration_seconds = final_time + total_penalty

        # 更新路线排行榜
        final_score = final_time + total_penalty

        ranklist_stmt = text(
            """
            SELECT *
            FROM bike_route_ranklists
            WHERE route_id = :route_id
              AND user_id = :user_id
            LIMIT 1
            """
        )

        ranklist_result = await db.execute(ranklist_stmt, {
            "route_id": route.id,
            "user_id": user.id
        })
        existing_rank = ranklist_result.fetchone()

        should_update_rank = False

        if existing_rank is None:
            should_update_rank = True
        elif final_score < existing_rank.duration_seconds:
            should_update_rank = True

        if should_update_rank:
            if existing_rank is None:
                db.add(BikeRouteRanklist(
                    route_id=route.id,
                    user_id=user.id,
                    gender=user.gender if user.gender else Gender.male,
                    record_id=record.id,
                    duration_seconds=final_score
                ))
            else:
                await db.execute(
                    text(
                        """
                        UPDATE bike_route_ranklists
                        SET
                            record_id = :record_id,
                            duration_seconds = :duration_seconds
                        WHERE id = :id
                        """
                    ),
                    {
                        "id": existing_rank.id,
                        "record_id": record.id,
                        "duration_seconds": final_score
                    }
                )

            # 非 premium 路线排行榜最多只保留100条
            if not route.is_premium:
                trim_stmt = text(
                    """
                    SELECT id
                    FROM bike_route_ranklists
                    WHERE route_id = :route_id
                    ORDER BY duration_seconds ASC, user_id ASC
                    OFFSET 100
                    """
                )
                trim_result = await db.execute(trim_stmt, {
                    "route_id": route.id
                })
                overflow_ids = [row.id for row in trim_result.fetchall()]

                if overflow_ids:
                    await db.execute(
                        text(
                            """
                            DELETE FROM bike_route_ranklists
                            WHERE id = ANY(:ids)
                            """
                        ),
                        {
                            "ids": overflow_ids
                        }
                    )

        return RouteTrainingFinishResponse(
            record_id=record.record_id, 
            xp_before=xp_before, 
            xp_delta=xp_delta, 
            training_state_before=training_state_before, 
            training_state_delta=training_state_delta, 
            new_grids=new_grids, 
            cc_rewards=cc_rewards
        )



async def query_route_training_record_detail_service(db: AsyncSession, lang: Language, record_id: str) -> RouteTrainingRecordDetailResponse:
    record = await get_route_training_record_by_record_id(db, record_id)
    if record is None:
        raise BizException(code=ErrorCode.RECORD_ERROR, message="record.not_found")
    
    path_points = []
    if record.path and record.path.path:
        try:
            for point_data in record.path.path:
                # 注意兼容新旧数据格式
                path_points.append(BikeRouteTrainingPathPoint.model_validate(point_data))
        except Exception:
            logger.exception("Handle path data failed in querying bike route training record detail info")
    
    duration = (record.end_time - record.start_time).total_seconds()
    final_time = record.duration_seconds

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
    
    return RouteTrainingRecordDetailResponse(
        original_time=duration,
        final_time=final_time,
        penalty_time=record.penalty_seconds,
        path=path_points,
        card_bonus=card_bonus_list,
        settlements=record.settlement_rewards
    )

async def query_route_ranklist_service(
    db: AsyncSession,
    route_id: str,
    gender: Gender | None,
    limit: int,
    cursor: str | None
) -> BikeRouteRanklistResponse:
    route = await get_route_by_route_id(db, route_id)
    if route is None:
        raise BizException(code=ErrorCode.ROUTE_NOT_FOUND, message="route.not_found")

    try:
        cursor_data = decode_cursor(cursor) if cursor else None
    except:
        raise BizException(code=ErrorCode.JSON_DECODE_ERROR, message=f"cursor解析错误")

    params = {
        "route_id": route.id,
        "limit": limit + 1
    }

    ranked_where_sql = "WHERE r.route_id = :route_id"
    if gender is not None:
        ranked_where_sql += " AND r.gender = :gender"
        params["gender"] = gender.value
    
    cursor_where_sql = ""
    if cursor_data:
        cursor_where_sql += """
        AND (
            duration_seconds > :cursor_duration
            OR (
                duration_seconds = :cursor_duration
                AND user_id > :cursor_user_id
            )
        )
        """

        params["cursor_duration"] = cursor_data["duration_seconds"]
        params["cursor_user_id"] = cursor_data["user_id"]

    sql = text(
        f"""
        WITH ranked AS (
            SELECT
                r.user_id,
                r.duration_seconds,

                u.user_id AS public_user_id,
                u.nickname,
                u.avatar_image_url,

                ROW_NUMBER() OVER (
                    ORDER BY r.duration_seconds ASC, r.user_id ASC
                ) AS rank

            FROM bike_route_ranklists r
            JOIN users u ON u.id = r.user_id

            {ranked_where_sql}
        )

        SELECT *
        FROM ranked
        {cursor_where_sql}
        ORDER BY duration_seconds ASC, user_id ASC
        LIMIT :limit
        """
    )

    result = await db.execute(sql, params)
    rows = result.fetchall()

    has_next = len(rows) > limit
    rows = rows[:limit]

    rank_infos = []

    for _, row in enumerate(rows):
        rank_infos.append(BikeRouteRankInfo(
            rank=row.rank,
            duration_seconds=row.duration_seconds,
            user=PersonInfoResponse(
                user_id=str(row.public_user_id),
                nickname=row.nickname,
                avatar_image_url=build_resource_url(row.avatar_image_url)
            )
        ))

    next_cursor = None

    if has_next and rows:
        last_row = rows[-1]

        next_cursor = encode_cursor({
            "duration_seconds": last_row.duration_seconds,
            "user_id": str(last_row.user_id)
        })

    return BikeRouteRanklistResponse(
        ranklist=rank_infos,
        next_cursor=next_cursor
    )

async def query_route_ranklist_me_service(db: AsyncSession, user_id: str, route_id: str) -> BikeRouteRankInfo | None:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise BizException(code=ErrorCode.USER_NOT_FOUND, message="user.not_found")
    route = await get_route_by_route_id(db, route_id)
    if route is None:
        raise BizException(code=ErrorCode.ROUTE_NOT_FOUND, message="route.not_found")
    rankInfo, rank = await get_rank_info_by_route_and_user(db, user.id, route.id)
    return BikeRouteRankInfo(
        rank=rank,
        duration_seconds=rankInfo.duration_seconds,
        user=PersonInfoResponse(user_id="", avatar_image_url="", nickname="")
    ) if rankInfo and rank else None