from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_, text, desc, asc, literal, tuple_
from app.db.models.competition import Region, RunningTrack
from app.db.models.training import (
    RunningFreeTrainingRecord, RunningRouteRanklist, UserTrainingStateRunning,
    UserGridFamiliarityRunning, UserTrainingStateDailyRunning,
    UserGridFamiliarityRunningAgg, RunningRouteTrainingRecord,
    RunningTrainingRoute, CardBonusInRunningRouteTrainingRecord,
    RunningEffectGridTileAgg, RunningEffectGrid, RunningEffectGridHistory, RunningRouteTrackApplication
)
from app.db.models.asset import UserEquipmentCard
from app.db.models.user import User
from app.db.session import redis_client
from app.schemas.training.common import GridTileKey, GridCellInfo, RouteSortType, GridEffectType, RouteApplyStatus
from app.schemas.training.running import RunningGridBuffPreview, RunningGridTileResponse, RunningGridTileInfo, RunningGridConditionType
from sqlalchemy.orm import selectinload
from typing import List
from datetime import date, timedelta, datetime
from sqlalchemy.dialects.postgresql import insert
from app.core.tools import get_tile_size, get_user_local_date, compute_effect_grid_count
from collections import defaultdict
from geoalchemy2.functions import (
    ST_Distance, ST_SetSRID, ST_MakePoint, ST_Contains,
    ST_Transform, ST_XMin, ST_XMax, ST_YMin, ST_YMax
)
from geoalchemy2 import Geography
import uuid, math, calendar, json, random, hashlib


# 计算用户对某条赛道的熟悉度（起终点直线 + Buffer 带状区域 + 指数距离衰减）
async def get_familiarity_by_track_and_user(db: AsyncSession, track: RunningTrack, user_id: uuid.UUID) -> float:
    # 赛道总长（米）：直接用已按整条 route_data 计算好的 distance(km)
    race_length_m = (track.distance or 0.0) * 1000.0

    # buffer 设为赛道长度的 20%，并限制在 800m ~ 4000m 之间
    buffer_meters = max(800.0, min(race_length_m * 0.2, 4000.0))

    # 指数衰减参数（控制衰减速度）
    decay_distance = buffer_meters / 2.0  # 衰减半径

    sql = text(
        """
        WITH params AS (
            SELECT CAST(:buffer_meters AS float) AS buffer_meters
        ),

        -- 取整条赛道路线几何并转为 WebMercator (米)
        line AS (
            SELECT ST_Transform(route_geometry, 3857) AS geom
            FROM running_tracks WHERE id = :track_id
        ),

        buffered AS (
            SELECT ST_Buffer(geom, buffer_meters) AS geom
            FROM line, params
        ),

        bounds AS (
            SELECT
                ST_XMin(geom) AS min_x,
                ST_XMax(geom) AS max_x,
                ST_YMin(geom) AS min_y,
                ST_YMax(geom) AS max_y
            FROM buffered
        ),

        -- 网格尺寸（单位：米）
        grid_size AS (
            SELECT 500.0::double precision AS size
        ),

        grid_index_bounds AS (
            SELECT
                floor(min_x / size)::int AS min_gx,
                floor(max_x / size)::int AS max_gx,
                floor(min_y / size)::int AS min_gy,
                floor(max_y / size)::int AS max_gy,
                size
            FROM bounds, grid_size
        ),

        grid_candidates AS (
            SELECT
                gx AS grid_x,
                gy AS grid_y,
                (gx * size)::double precision AS x,
                (gy * size)::double precision AS y,
                size
            FROM grid_index_bounds,
            generate_series(min_gx, max_gx, 1) AS gx,
            generate_series(min_gy, max_gy, 1) AS gy
        ),

        filtered AS (
            SELECT
                gc.grid_x,
                gc.grid_y,
                ST_Centroid(
                    ST_MakeEnvelope(
                        gc.x,
                        gc.y,
                        gc.x + gc.size,
                        gc.y + gc.size,
                        3857
                    )
                ) AS centroid,
                l.geom AS line_geom
            FROM grid_candidates gc
            JOIN line l ON true
            JOIN buffered b ON true
            WHERE ST_Intersects(
                ST_MakeEnvelope(
                    gc.x,
                    gc.y,
                    gc.x + gc.size,
                    gc.y + gc.size,
                    3857
                ),
                b.geom
            )
        ),

        user_fam AS (
            SELECT
                grid_x,
                grid_y,
                familiarity_count
            FROM user_grid_familiarity_running
            WHERE season_id = :season_id
              AND user_id = :user_id
        ),

        scored AS (
            SELECT
                f.grid_x,
                f.grid_y,
                COALESCE(uf.familiarity_count, 0) AS fam,
                ST_Distance(f.centroid, f.line_geom) AS dist
            FROM filtered f
            LEFT JOIN user_fam uf
              ON uf.grid_x = f.grid_x
             AND uf.grid_y = f.grid_y
        )

        SELECT
            SUM(fam * EXP(-dist / :decay_distance)) AS weighted_score,
            COUNT(*) AS grid_count
        FROM scored;
        """
    )

    result = await db.execute(
        sql,
        {
            "season_id": str(track.event.season_id),
            "user_id": str(user_id),
            "track_id": str(track.id),
            "buffer_meters": buffer_meters,
            "decay_distance": decay_distance,
        },
    )

    row = result.first()
    if not row or row.weighted_score is None or row.grid_count == 0:
        return 0.0

    weighted_score = float(row.weighted_score)
    grid_count = int(row.grid_count)

    # 设定熟悉度理论上限 = 赛道覆盖网格数 * 单格最大熟悉度(10) * 0.5
    max_fam_per_grid = 10
    theoretical_max = grid_count * max_fam_per_grid * 0.5

    if theoretical_max <= 0:
        return 0.0

    familiarity_ratio = min(weighted_score / theoretical_max, 1.0)
    return familiarity_ratio


async def get_training_state_by_user(db: AsyncSession, user_id: uuid.UUID) -> UserTrainingStateRunning | None:
    result = await db.execute(
        select(UserTrainingStateRunning)
        .where(
            UserTrainingStateRunning.user_id == user_id
        )
    )
    return result.scalar_one_or_none()

async def get_training_state_daily_by_user_date(db: AsyncSession, user_id: uuid.UUID, date: date) -> UserTrainingStateDailyRunning | None:
    result = await db.execute(
        select(UserTrainingStateDailyRunning)
        .where(
            UserTrainingStateDailyRunning.user_id == user_id,
            UserTrainingStateDailyRunning.local_date == date
        )
    )
    return result.scalar_one_or_none()

# 查询用户某月的所有训练状态变化
async def get_training_states_by_user_and_month(db: AsyncSession, user_id: uuid.UUID, month: str) -> List[UserTrainingStateDailyRunning]:
    # 解析 month
    year, mon = map(int, month.split("-"))

    start_date = date(year, mon, 1)
    last_day = calendar.monthrange(year, mon)[1]
    end_date = date(year, mon, last_day)

    result = await db.execute(
        select(UserTrainingStateDailyRunning)
        .where(
            UserTrainingStateDailyRunning.user_id == user_id,
            UserTrainingStateDailyRunning.local_date >= start_date,
            UserTrainingStateDailyRunning.local_date <= end_date
        )
        .order_by(UserTrainingStateDailyRunning.local_date)
    )
    return result.scalars().all()


# 统计用户某月每天的训练记录数（free + route），用于日历日期角标
async def get_training_record_counts_by_user_and_month(db: AsyncSession, user_id: uuid.UUID, month: str) -> dict[date, int]:
    year, mon = map(int, month.split("-"))
    start_date = date(year, mon, 1)
    end_date = date(year, mon, calendar.monthrange(year, mon)[1])

    counts: dict[date, int] = defaultdict(int)
    for model in (RunningFreeTrainingRecord, RunningRouteTrainingRecord):
        rows = await db.execute(
            select(model.local_date, func.count())
            .where(
                model.user_id == user_id,
                model.local_date >= start_date,
                model.local_date <= end_date,
            )
            .group_by(model.local_date)
        )
        for d, c in rows.all():
            counts[d] += c
    return dict(counts)


# 训练模块周汇总：按 local_date 聚合 free+route 的总时长(秒)与总距离(km)
async def get_weekly_training_aggregates(db: AsyncSession, user_id: uuid.UUID, start_date: date, end_date: date) -> dict[date, tuple[float, float]]:
    agg: dict[date, list[float]] = defaultdict(lambda: [0.0, 0.0])
    for model in (RunningFreeTrainingRecord, RunningRouteTrainingRecord):
        rows = await db.execute(
            select(
                model.local_date,
                func.coalesce(func.sum(model.duration_seconds), 0.0),
                func.coalesce(func.sum(model.distance), 0.0),
            )
            .where(
                model.user_id == user_id,
                model.local_date >= start_date,
                model.local_date <= end_date,
            )
            .group_by(model.local_date)
        )
        for d, total_time, total_distance in rows.all():
            agg[d][0] += float(total_time or 0.0)
            agg[d][1] += float(total_distance or 0.0)
    return {d: (v[0], v[1]) for d, v in agg.items()}


# 训练模块周汇总：按 local_date 取每日 momentum delta
async def get_daily_states_by_user_and_range(db: AsyncSession, user_id: uuid.UUID, start_date: date, end_date: date) -> dict[date, int]:
    rows = await db.execute(
        select(UserTrainingStateDailyRunning.local_date, UserTrainingStateDailyRunning.delta)
        .where(
            UserTrainingStateDailyRunning.user_id == user_id,
            UserTrainingStateDailyRunning.local_date >= start_date,
            UserTrainingStateDailyRunning.local_date <= end_date,
        )
    )
    return {d: delta for d, delta in rows.all()}


# 查询用户某天的自由训练记录
async def get_free_training_records_by_user_and_day(db: AsyncSession, user_id: uuid.UUID, day: str) -> List[RunningFreeTrainingRecord]:
    target_date = date.fromisoformat(day)
    result = await db.execute(
        select(RunningFreeTrainingRecord)
        .options(selectinload(RunningFreeTrainingRecord.path))
        .where(
            RunningFreeTrainingRecord.user_id == user_id,
            RunningFreeTrainingRecord.local_date == target_date
        )
        .order_by(RunningFreeTrainingRecord.start_time.asc())
    )
    return result.scalars().all()

# 查询用户某天的路线训练记录
async def get_route_training_records_by_user_and_day(db: AsyncSession, user_id: uuid.UUID, day: str) -> List[RunningRouteTrainingRecord]:
    target_date = date.fromisoformat(day)
    result = await db.execute(
        select(RunningRouteTrainingRecord)
        .options(selectinload(RunningRouteTrainingRecord.path))
        .where(
            RunningRouteTrainingRecord.user_id == user_id,
            RunningRouteTrainingRecord.local_date == target_date
        )
        .order_by(RunningRouteTrainingRecord.start_time.asc())
    )
    return result.scalars().all()

async def get_training_state_by_user(db: AsyncSession, user_id: uuid.UUID) -> UserTrainingStateRunning | None:
    result = await db.execute(
        select(UserTrainingStateRunning)
        .where(UserTrainingStateRunning.user_id == user_id)
    )
    return result.scalar_one_or_none()

async def add_or_update_daily_training_states(
    db: AsyncSession,
    user_id: uuid.UUID,
    local_date: date,
    delta: int,
    new_value: int
):
    stmt = insert(UserTrainingStateDailyRunning).values(
        user_id=user_id,
        local_date=local_date,
        delta=delta,
        value=new_value
    ).on_conflict_do_update(
        index_elements=["user_id", "local_date"],
        set_={
            "delta": UserTrainingStateDailyRunning.delta + delta,
            "value": UserTrainingStateDailyRunning.value + delta
        }
    )
    await db.execute(stmt)


async def update_user_familiarity_by_grids(
    db: AsyncSession,
    season_id: uuid.UUID,
    user_id: uuid.UUID,
    grid_region_pairs: list[tuple[int, int, uuid.UUID]]
) -> int:
    sql = text(
        """
        WITH input_grids AS (
            SELECT
                CAST(:user_id AS uuid) AS user_id,
                CAST(:season_id AS uuid) AS season_id,
                g.grid_x,
                g.grid_y,
                g.region_id
            FROM jsonb_to_recordset(:grids_json)
            AS g(grid_x int, grid_y int, region_id uuid)
        ),

        insert_base AS (
            INSERT INTO user_grid_familiarity_running (
                id,
                season_id,
                user_id,
                grid_x,
                grid_y,
                region_id,
                familiarity_count,
                created_at,
                updated_at
            )
            SELECT
                gen_random_uuid(),
                season_id,
                user_id,
                grid_x,
                grid_y,
                region_id,
                1,
                NOW(),
                NOW()
            FROM input_grids
            ON CONFLICT (season_id, user_id, grid_x, grid_y)
            DO UPDATE
            SET familiarity_count = user_grid_familiarity_running.familiarity_count + 1,
                updated_at = NOW()
            RETURNING (xmax = 0) AS inserted, grid_x, grid_y
        ),

        levels AS (
            SELECT generate_series(0, 3) AS level
        ),

        expanded AS (
            SELECT
                CAST(:user_id AS uuid) AS user_id,
                CAST(:season_id AS uuid) AS season_id,
                l.level,
                floor(grid_x / power(2, l.level))::int AS grid_x,
                floor(grid_y / power(2, l.level))::int AS grid_y,
                1 AS inc
            FROM insert_base
            CROSS JOIN levels l
        ),

        agg_delta AS (
            SELECT
                user_id,
                season_id,
                level,
                grid_x,
                grid_y,
                COUNT(*) AS inc
            FROM expanded
            GROUP BY user_id, season_id, level, grid_x, grid_y
        ),

        agg_upsert AS (
            INSERT INTO user_grid_familiarity_running_agg (
                id,
                user_id,
                season_id,
                level,
                grid_x,
                grid_y,
                familiarity_count
            )
            SELECT
                gen_random_uuid(),
                user_id,
                season_id,
                level,
                grid_x,
                grid_y,
                inc
            FROM agg_delta
            ON CONFLICT (season_id, user_id, level, grid_x, grid_y)
            DO UPDATE
            SET familiarity_count = user_grid_familiarity_running_agg.familiarity_count + EXCLUDED.familiarity_count
            RETURNING 1
        ),

        final AS (
            SELECT COUNT(*) AS new_grid_count
            FROM insert_base
            WHERE inserted = true
        )

        SELECT new_grid_count FROM final;
        """
    )

    grids_json = [
        {"grid_x": gx, "grid_y": gy, "region_id": str(rid)}
        for gx, gy, rid in grid_region_pairs
    ]

    result = await db.execute(
        sql,
        {
            "season_id": str(season_id),
            "user_id": str(user_id),
            "grids_json": json.dumps(grids_json),
        },
    )
    row = result.first()
    return int(row.new_grid_count) if row and row.new_grid_count is not None else 0


async def get_region_explored_grid_count(
    db: AsyncSession,
    region_id: uuid.UUID,
    season_id: uuid.UUID,
    user_id: uuid.UUID
) -> int:
    explored_grids = await db.scalar(
        select(func.count())
        .select_from(UserGridFamiliarityRunning)
        .where(
            UserGridFamiliarityRunning.region_id == region_id,
            UserGridFamiliarityRunning.user_id == user_id,
            UserGridFamiliarityRunning.season_id == season_id
        )
    )
    return explored_grids or 0

async def get_free_training_record_by_record_id(db: AsyncSession, record_id: str) -> RunningFreeTrainingRecord | None:
    record = await db.execute(
        select(RunningFreeTrainingRecord)
        .where(RunningFreeTrainingRecord.record_id == record_id)
        .options(
            selectinload(RunningFreeTrainingRecord.path),
            selectinload(RunningFreeTrainingRecord.user)
        )
    )
    return record.scalar_one_or_none()

async def get_route_training_record_by_record_id(db: AsyncSession, record_id: str) -> RunningRouteTrainingRecord | None:
    result = await db.execute(
        select(RunningRouteTrainingRecord)
        .where(RunningRouteTrainingRecord.record_id == record_id)
        .options(
            selectinload(RunningRouteTrainingRecord.user),
            selectinload(RunningRouteTrainingRecord.path),
            selectinload(RunningRouteTrainingRecord.card_bonus)
                .selectinload(CardBonusInRunningRouteTrainingRecord.card)
                .selectinload(UserEquipmentCard.equipment_def),
            selectinload(RunningRouteTrainingRecord.card_bonus)
                .selectinload(CardBonusInRunningRouteTrainingRecord.card)
                .selectinload(UserEquipmentCard.user)
        )
    )
    return result.scalar_one_or_none()

async def ensure_running_effect_grids_generated(
    db: AsyncSession,
    region: Region,
    active_date: date
):
    exists_stmt = (
        select(RunningEffectGrid.id)
        .where(
            RunningEffectGrid.region_id == region.id,
            RunningEffectGrid.active_date == active_date
        )
        .limit(1)
    )

    exists_result = await db.execute(exists_stmt)
    if exists_result.first() is not None:
        return

    lock_raw = f"running_effect_grid:{region.id}:{active_date.isoformat()}"

    lock_key = int(
        hashlib.md5(lock_raw.encode()).hexdigest()[:8],
        16
    )

    await db.execute(
        text("SELECT pg_advisory_xact_lock(:lock_key)"),
        {"lock_key": lock_key}
    )

    recheck_result = await db.execute(exists_stmt)
    if recheck_result.first() is not None:
        return


    boundary_stmt = select(
        ST_XMin(ST_Transform(region.boundary, 3857)),
        ST_XMax(ST_Transform(region.boundary, 3857)),
        ST_YMin(ST_Transform(region.boundary, 3857)),
        ST_YMax(ST_Transform(region.boundary, 3857)),
    )

    boundary_result = await db.execute(boundary_stmt)
    bounds = boundary_result.first()

    if bounds is None:
        return

    min_x, max_x, min_y, max_y = bounds

    # 依据 region 网格总数动态决定 buff 奖励网格数量
    target_count = compute_effect_grid_count(region.grid_count)

    condition_pool = {
        RunningGridConditionType.distance: [
            {"sum": 1},
            {"sum": 3},
            {"sum": 5},
        ],
        RunningGridConditionType.speed: [
            {"avg": 8},
            {"avg": 10},
            {"avg": 12},
        ],
        RunningGridConditionType.weather: [
            {"match": "clear"},
            {"match": "cloudy"},
            {"match": "rain"},
            {"match": "snow"},
            {"match": "fog"},
        ],
        RunningGridConditionType.none: [
            {}
        ]
    }

    reward_types = [
        "coin",
        "coupon",
        "stone1",
        "stone2",
        "stone3"
    ]

    generated_positions = set()
    generated_grids = []

    attempts = 0

    while len(generated_grids) < target_count and attempts < 500:
        attempts += 1

        rand_x = random.uniform(min_x, max_x)
        rand_y = random.uniform(min_y, max_y)

        base_grid_x = math.floor(rand_x / 500)
        base_grid_y = math.floor(rand_y / 500)

        position_key = (base_grid_x, base_grid_y)

        if position_key in generated_positions:
            continue

        point_x = base_grid_x * 500 + 250
        point_y = base_grid_y * 500 + 250

        contains_stmt = select(
            ST_Contains(
                ST_Transform(region.boundary, 3857),
                ST_SetSRID(
                    ST_MakePoint(point_x, point_y),
                    3857
                )
            )
        )

        contains_result = await db.execute(contains_stmt)

        if not contains_result.scalar():
            continue

        generated_positions.add(position_key)

        condition_type = random.choice([
            RunningGridConditionType.distance,
            RunningGridConditionType.speed,
            RunningGridConditionType.weather,
            RunningGridConditionType.none
        ])

        condition_params = random.choice(
            condition_pool[condition_type]
        )

        reward_type = random.choice(reward_types)

        if reward_type == "coin":
            reward_count = random.randint(10, 100)
        else:
            reward_count = random.randint(1, 5)

        # ---- Add i18n description generation ----
        if condition_type == RunningGridConditionType.distance:
            sum_km = condition_params["sum"]
            description_i18n = {
                "en": f"Receive {{{{reward}}}} reward when passing through and total distance exceeds {sum_km}km",
                "zh-Hans": f"经过时，累计运动距离大于{sum_km}km时可获得{{{{reward}}}}奖励",
                "zh-Hant": f"經過時，累計運動距離大於{sum_km}km時可獲得{{{{reward}}}}獎勵",
                "ko": f"통과 시 누적 이동 거리가 {sum_km}km를 넘으면 {{{{reward}}}} 보상을 획득할 수 있습니다",
                "ja": f"通過時に累計走行距離が{sum_km}kmを超えると{{{{reward}}}}報酬を獲得できます"
            }
        elif condition_type == RunningGridConditionType.speed:
            avg_speed = condition_params["avg"]

            # km/h -> min/km pace
            pace_minutes = 60 / avg_speed
            pace_min = int(pace_minutes)
            pace_sec = int(round((pace_minutes - pace_min) * 60))

            if pace_sec == 60:
                pace_min += 1
                pace_sec = 0

            pace_text = f"{pace_min}'{pace_sec:02d}''/km"

            description_i18n = {
                "en": f"Receive {{{{reward}}}} reward when passing through and pace is faster than {pace_text}",
                "zh-Hans": f"经过时，平均配速快于{pace_text}时可获得{{{{reward}}}}奖励",
                "zh-Hant": f"經過時，平均配速快於{pace_text}時可獲得{{{{reward}}}}獎勵",
                "ko": f"통과 시 평균 페이스가 {pace_text}보다 빠르면 {{{{reward}}}} 보상을 획득할 수 있습니다",
                "ja": f"通過時に平均ペースが{pace_text}より速いと{{{{reward}}}}報酬を獲得できます"
            }
        elif condition_type == RunningGridConditionType.weather:
            condition_labels = {
                "clear": {"en": "clear", "zh-Hans": "晴天", "zh-Hant": "晴天", "fr": "ciel dégagé", "ja": "晴れ", "ko": "맑음"},
                "cloudy": {"en": "cloudy", "zh-Hans": "多云", "zh-Hant": "多雲", "fr": "nuageux", "ja": "曇り", "ko": "흐림"},
                "rain": {"en": "rainy", "zh-Hans": "下雨", "zh-Hant": "下雨", "fr": "pluvieux", "ja": "雨", "ko": "비"},
                "snow": {"en": "snowy", "zh-Hans": "下雪", "zh-Hant": "下雪", "fr": "neigeux", "ja": "雪", "ko": "눈"},
                "fog": {"en": "foggy", "zh-Hans": "有雾", "zh-Hant": "有霧", "fr": "brumeux", "ja": "霧", "ko": "안개"},
            }
            labels = condition_labels[condition_params["match"]]
            description_i18n = {
                "en": f"Receive {{{{reward}}}} reward when passing through in {labels['en']} weather",
                "zh-Hans": f"经过时天气为{labels['zh-Hans']}可获得{{{{reward}}}}奖励",
                "zh-Hant": f"經過時天氣為{labels['zh-Hant']}可獲得{{{{reward}}}}獎勵",
                "fr": f"Recevez {{{{reward}}}} en passant par temps {labels['fr']}",
                "ja": f"通過時に天気が{labels['ja']}なら{{{{reward}}}}報酬を獲得できます",
                "ko": f"통과 시 날씨가 {labels['ko']}이면 {{{{reward}}}} 보상을 획득할 수 있습니다",
            }
        elif condition_type == RunningGridConditionType.none:
            description_i18n = {
                "en": "Receive {{reward}} reward upon passing through",
                "zh-Hans": "经过时可获得{{reward}}奖励",
                "zh-Hant": "經過時可獲得{{reward}}獎勵",
                "ko": "통과 시 {{reward}} 보상을 획득할 수 있습니다",
                "ja": "通過時に{{reward}}報酬を獲得できます"
            }
        else:
            continue

        generated_grids.append({
            "grid_x": base_grid_x,
            "grid_y": base_grid_y,
            "description_i18n": description_i18n,
            "effect_type": GridEffectType.buff.value,
            "condition_type": condition_type.value,
            "condition_params": condition_params,
            "reward_type": reward_type,
            "reward_count": reward_count
        })

    if not generated_grids:
        return

    effect_rows = []

    for grid in generated_grids:
        effect_rows.append({
            "id": uuid.uuid4(),
            "region_id": region.id,
            "grid_x": grid["grid_x"],
            "grid_y": grid["grid_y"],
            "description_i18n": grid["description_i18n"],
            "effect_type": grid["effect_type"],
            "condition_type": grid["condition_type"],
            "condition_params": grid["condition_params"],
            "reward_type": grid["reward_type"],
            "reward_count": grid["reward_count"],
            "active_date": active_date
        })

    effect_stmt = (
        insert(RunningEffectGrid)
        .values(effect_rows)
        .on_conflict_do_nothing(
            index_elements=[
                "grid_x",
                "grid_y",
                "active_date"
            ]
        )
        .returning(
            RunningEffectGrid.grid_x,
            RunningEffectGrid.grid_y,
            RunningEffectGrid.effect_type,
            RunningEffectGrid.condition_type,
            RunningEffectGrid.reward_type,
            RunningEffectGrid.reward_count
        )
    )

    effect_result = await db.execute(effect_stmt)

    inserted_grids = effect_result.mappings().all()

    if not inserted_grids:
        return

    tile_preview_map = defaultdict(list)

    for grid in inserted_grids:
        for level in range(0, 4):
            grid_scale = 2 ** level

            agg_grid_x = grid["grid_x"] // grid_scale
            agg_grid_y = grid["grid_y"] // grid_scale

            tile_preview_map[
                (level, agg_grid_x, agg_grid_y)
            ].append({
                "grid_x": grid["grid_x"],
                "grid_y": grid["grid_y"],
                "effect_type": (
                    grid["effect_type"].value
                    if hasattr(grid["effect_type"], "value")
                    else grid["effect_type"]
                ),
                "condition_type": grid["condition_type"],
                "reward_type": grid["reward_type"]
            })

    agg_rows = []

    for (level, grid_x, grid_y), previews in tile_preview_map.items():
        agg_rows.append({
            "id": uuid.uuid4(),
            "active_date": active_date,
            "level": level,
            "grid_x": grid_x,
            "grid_y": grid_y,
            "grid_previews": previews
        })

    agg_stmt = insert(RunningEffectGridTileAgg).values(agg_rows)

    agg_stmt = agg_stmt.on_conflict_do_update(
        index_elements=[
            "active_date",
            "level",
            "grid_x",
            "grid_y"
        ],
        set_={
            "grid_previews": (
                RunningEffectGridTileAgg.grid_previews.op("||")(
                    agg_stmt.excluded.grid_previews
                )
            )
        }
    )
    await db.execute(agg_stmt)
    #print(f"create buff grids for region{region.region_id}")


# 运动中雷达：取 region 内当天「最近 N 个未触发的 buff 网格」（按网格空间平方距离排序）
async def get_nearby_effect_grids(
    db: AsyncSession,
    user: User,
    region: Region,
    active_date: date,
    grid_x: int,
    grid_y: int,
    count: int
) -> List[RunningEffectGrid]:
    dist = (
        (RunningEffectGrid.grid_x - grid_x) * (RunningEffectGrid.grid_x - grid_x)
        + (RunningEffectGrid.grid_y - grid_y) * (RunningEffectGrid.grid_y - grid_y)
    )
    stmt = (
        select(RunningEffectGrid)
        .outerjoin(
            RunningEffectGridHistory,
            (
                (RunningEffectGridHistory.user_id == user.id)
                & (RunningEffectGridHistory.grid_x == RunningEffectGrid.grid_x)
                & (RunningEffectGridHistory.grid_y == RunningEffectGrid.grid_y)
                & (RunningEffectGridHistory.active_date == RunningEffectGrid.active_date)
            )
        )
        .where(
            RunningEffectGrid.region_id == region.id,
            RunningEffectGrid.active_date == active_date,
            RunningEffectGrid.effect_type == GridEffectType.buff,
            RunningEffectGridHistory.id.is_(None),
        )
        .order_by(dist.asc())
        .limit(count)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


# 查询用户附近指定地表距离（米）内、当天还能领取的 buff 网格（自由训练页附近网格列表）
async def get_effect_grids_within_distance(
    db: AsyncSession,
    user: User,
    region: Region,
    active_date: date,
    lat: float,
    lon: float,
    distance: float,
    max_count: int
) -> List[RunningEffectGrid]:
    # 奖励格以 EPSG:3857 网格索引存储，但 3857 的单位会随纬度失真；
    # 这里将格中心转为 geography 后计算真实地表距离，和客户端 Haversine 展示口径一致。
    grid_center = ST_SetSRID(
        ST_MakePoint(
            RunningEffectGrid.grid_x * 500 + 250,
            RunningEffectGrid.grid_y * 500 + 250,
        ),
        3857,
    )
    grid_center_geography = ST_Transform(grid_center, 4326).cast(Geography)
    user_point_geography = ST_SetSRID(ST_MakePoint(lon, lat), 4326).cast(Geography)
    distance_meters = ST_Distance(grid_center_geography, user_point_geography)
    stmt = (
        select(RunningEffectGrid)
        .outerjoin(
            RunningEffectGridHistory,
            (
                (RunningEffectGridHistory.user_id == user.id)
                & (RunningEffectGridHistory.grid_x == RunningEffectGrid.grid_x)
                & (RunningEffectGridHistory.grid_y == RunningEffectGrid.grid_y)
                & (RunningEffectGridHistory.active_date == RunningEffectGrid.active_date)
            )
        )
        .where(
            RunningEffectGrid.region_id == region.id,
            RunningEffectGrid.active_date == active_date,
            RunningEffectGrid.effect_type == GridEffectType.buff,
            RunningEffectGridHistory.id.is_(None),
            distance_meters <= distance,
        )
        .order_by(distance_meters.asc())
        .limit(max_count)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def ensure_running_effect_grids_for_viewport(
    db: AsyncSession,
    min_grid_x: int,
    max_grid_x: int,
    min_grid_y: int,
    max_grid_y: int,
    level: int,
    active_date: date
):
    """保证视口（网格范围）覆盖到的所有 region 当天都已生成 buff grids。
    - 视口网格范围 -> 3857 包络盒 -> 4326，按 ST_Intersects 查相交 region（命中 boundary 的 GiST 索引）
    - 用 Redis 当天「已生成」集合做短路：稳态下不碰 DB，仅当天首次才走 ensure_*
    避免只 ensure 传入的单个 region 导致拖动到邻近 region 时出现空白。
    注意：agg 网格按 2**level 降采样，故 level-L 单格边长 = 500 * 2**level 米，不能直接乘 500。
    """
    cell = 500 * (2 ** level)
    envelope = func.ST_Transform(
        func.ST_MakeEnvelope(
            min_grid_x * cell, min_grid_y * cell,
            (max_grid_x + 1) * cell, (max_grid_y + 1) * cell,
            3857
        ),
        4326
    )
    regions = (await db.execute(
        select(Region).where(func.ST_Intersects(Region.boundary, envelope))
    )).scalars().all()
    
    if not regions:
        return

    redis_key = f"effect_grids:ensured:running:{active_date.isoformat()}"
    region_ids = [str(r.id) for r in regions]

    # Redis 批量判断哪些 region 今天还没生成（Redis 异常则全部回退到 DB ensure，仍幂等安全）
    try:
        flags = await redis_client.smismember(redis_key, *region_ids)
    except Exception:
        flags = [0] * len(region_ids)

    pending = [r for r, f in zip(regions, flags) if not f]
    if not pending:
        return

    # 按 id 排序后逐个 ensure：保证并发事务以相同顺序获取 advisory lock，避免死锁
    pending.sort(key=lambda r: r.id)
    for r in pending:
        await ensure_running_effect_grids_generated(db, r, active_date)

    try:
        await redis_client.sadd(redis_key, *[str(r.id) for r in pending])
        await redis_client.expire(redis_key, 93600)  # ~26h，跨天自然滚动
    except Exception:
        pass


async def get_grids_info_by_tiles(
    db: AsyncSession,
    user: User,
    region: Region,
    season_id: uuid.UUID,
    tiles: List[GridTileKey]
) -> RunningGridTileResponse:
    if not tiles:
        return RunningGridTileResponse(tiles=[])

    local_date = get_user_local_date(user)

    level = tiles[0].level  # 同一批一定同 level
    tile_size = get_tile_size(level)

    min_tile_x = min(t.x for t in tiles)
    max_tile_x = max(t.x for t in tiles)
    min_tile_y = min(t.y for t in tiles)
    max_tile_y = max(t.y for t in tiles)

    min_x = min_tile_x * tile_size
    max_x = (max_tile_x + 1) * tile_size - 1
    min_y = min_tile_y * tile_size
    max_y = (max_tile_y + 1) * tile_size - 1

    # lazy ensure：保证视口覆盖到的所有 region 当天都已生成 buff grids
    await ensure_running_effect_grids_for_viewport(db, min_x, max_x, min_y, max_y, level, local_date)

    familiarity_stmt = (
        select(
            UserGridFamiliarityRunningAgg.grid_x,
            UserGridFamiliarityRunningAgg.grid_y,
            UserGridFamiliarityRunningAgg.familiarity_count
        )
        .where(
            and_(
                UserGridFamiliarityRunningAgg.user_id == user.id,
                UserGridFamiliarityRunningAgg.season_id == season_id,
                UserGridFamiliarityRunningAgg.level == level,
                UserGridFamiliarityRunningAgg.grid_x >= min_x,
                UserGridFamiliarityRunningAgg.grid_x <= max_x,
                UserGridFamiliarityRunningAgg.grid_y >= min_y,
                UserGridFamiliarityRunningAgg.grid_y <= max_y,
            )
        )
    )

    familiarity_result = await db.execute(familiarity_stmt)
    familiarity_rows = familiarity_result.all()

    buff_stmt = (
        select(
            RunningEffectGridTileAgg.grid_x,
            RunningEffectGridTileAgg.grid_y,
            RunningEffectGridTileAgg.grid_previews
        )
        .where(
            and_(
                RunningEffectGridTileAgg.active_date == local_date,
                RunningEffectGridTileAgg.level == level,
                RunningEffectGridTileAgg.grid_x >= min_x,
                RunningEffectGridTileAgg.grid_x <= max_x,
                RunningEffectGridTileAgg.grid_y >= min_y,
                RunningEffectGridTileAgg.grid_y <= max_y,
            )
        )
    )

    buff_result = await db.execute(buff_stmt)
    buff_rows = buff_result.all()

    preview_positions = set()

    for row in buff_rows:
        previews = row.grid_previews

        if not isinstance(previews, list):
            continue

        for preview in previews:
            if not isinstance(preview, dict):
                continue
            preview_positions.add((
                preview["grid_x"],
                preview["grid_y"]
            ))

    history_set = set()

    if preview_positions:
        history_stmt = (
            select(
                RunningEffectGridHistory.grid_x,
                RunningEffectGridHistory.grid_y
            )
            .where(
                and_(
                    RunningEffectGridHistory.user_id == user.id,
                    RunningEffectGridHistory.active_date == local_date,
                    tuple_(
                        RunningEffectGridHistory.grid_x,
                        RunningEffectGridHistory.grid_y
                    ).in_(preview_positions)
                )
            )
        )

        history_result = await db.execute(history_stmt)
        history_rows = history_result.all()

        history_set = {
            (r.grid_x, r.grid_y)
            for r in history_rows
        }

    # 分桶到 tile
    tile_map = defaultdict(list)

    for r in familiarity_rows:
        tile_x = r.grid_x // tile_size
        tile_y = r.grid_y // tile_size
        key = (tile_x, tile_y)

        tile_map[key].append(GridCellInfo(
            grid_x=r.grid_x,
            grid_y=r.grid_y,
            count=r.familiarity_count
        ))

    buff_map = defaultdict(list)

    for row in buff_rows:
        tile_x = row.grid_x // tile_size
        tile_y = row.grid_y // tile_size
        key = (tile_x, tile_y)
        previews = row.grid_previews

        if not isinstance(previews, list):
            continue

        selected_preview = None
        previews = sorted(
            previews,
            key=lambda p: (
                p.get("grid_x", 0),
                p.get("grid_y", 0)
            ) if isinstance(p, dict) else (0, 0)
        )

        for preview in previews:
            if not isinstance(preview, dict):
                continue
            grid_key = (
                preview["grid_x"],
                preview["grid_y"]
            )
            if grid_key in history_set:
                continue
            selected_preview = RunningGridBuffPreview(
                grid_x=row.grid_x,
                grid_y=row.grid_y,
                effect_type=preview["effect_type"],
                condition_type=preview["condition_type"],
                reward_type=preview["reward_type"]
            )
            break
        if selected_preview is not None:
            buff_map[key].append(selected_preview)

    result_tiles = []
    for tile in tiles:
        key = (tile.x, tile.y)
        result_tiles.append(RunningGridTileInfo(
            key=GridTileKey(level=tile.level, x=tile.x, y=tile.y),
            cells=tile_map.get(key, []),
            buff_info=buff_map.get(key, [])
        ))

    return RunningGridTileResponse(tiles=result_tiles)


async def get_routes_by_page_crud(
    db: AsyncSession,
    region_id: str,
    sort_type: RouteSortType,
    lat: float,
    lng: float,
    limit: int,
    cursor: dict | None
):
    # participation 排序
    if sort_type == "participation":
        subq = (
            select(
                RunningRouteTrainingRecord.route_id,
                func.count().label("count")
            )
            .group_by(RunningRouteTrainingRecord.route_id)
            .subquery()
        )
        
        distance_expr = None
        if lat is not None and lng is not None:
            point = ST_SetSRID(ST_MakePoint(lng, lat), 4326)
            distance_expr = ST_Distance(
                RunningTrainingRoute.start_point.cast(Geography),
                point.cast(Geography)
            )
        
        query = (
            select(
                RunningTrainingRoute,
                func.coalesce(subq.c.count, 0).label("count"),
                (distance_expr if distance_expr is not None else literal(None)).label("distance")
            )
            .outerjoin(subq, RunningTrainingRoute.id == subq.c.route_id)
            .where(
                RunningTrainingRoute.region_id == region_id,
                RunningTrainingRoute.is_public == True
            )
        )
        if cursor:
            count_expr = func.coalesce(subq.c.count, 0)
            query = query.where(
                (count_expr < cursor["count"]) |
                (
                    (count_expr == cursor["count"]) &
                    (RunningTrainingRoute.created_at > cursor["created_at"])
                ) |
                (
                    (count_expr == cursor["count"]) &
                    (RunningTrainingRoute.created_at == cursor["created_at"]) &
                    (RunningTrainingRoute.id > cursor["route_id"])
                )
            )
        query = query.order_by(
            desc("count"),
            asc(RunningTrainingRoute.created_at),
            asc(RunningTrainingRoute.id)
        ).limit(limit)

    # distance 排序
    else:
        # 如果有 cursor，则冻结使用 cursor 中的 lat/lng（保证分页稳定）
        if cursor and "lat" in cursor and "lng" in cursor:
            lat = cursor["lat"]
            lng = cursor["lng"]
        point = ST_SetSRID(ST_MakePoint(lng, lat), 4326)
        distance_expr = ST_Distance(
            RunningTrainingRoute.start_point.cast(Geography),
            point.cast(Geography)
        )
        subq = (
            select(
                RunningRouteTrainingRecord.route_id,
                func.count().label("count")
            )
            .group_by(RunningRouteTrainingRecord.route_id)
            .subquery()
        )

        query = (
            select(
                RunningTrainingRoute,
                func.coalesce(subq.c.count, 0).label("count"),
                distance_expr.label("distance")
            )
            .outerjoin(subq, RunningTrainingRoute.id == subq.c.route_id)
            .where(
                RunningTrainingRoute.region_id == region_id,
                RunningTrainingRoute.is_public == True
            )
        )
        if cursor:
            query = query.where(
                (distance_expr > cursor["distance"]) |
                (
                    (distance_expr == cursor["distance"]) &
                    (RunningTrainingRoute.id > cursor["route_id"])
                )
            )
        query = query.order_by(
            asc("distance"),
            asc(RunningTrainingRoute.id)
        ).limit(limit)
    
    result = await db.execute(query)
    return result.mappings().all()


async def get_routes_by_uesr_id(
    db: AsyncSession,
    user_id: uuid.UUID,
    page: int,
    size: int
) -> List[RunningTrainingRoute]:
    stmt = (
        select(RunningTrainingRoute)
        .where(RunningTrainingRoute.user_id == user_id)
        .order_by(RunningTrainingRoute.created_at.desc()).offset((page - 1) * size).limit(size)
    )
    result = await db.execute(stmt)
    return result.scalars().all()

async def get_route_by_route_id(db: AsyncSession, route_id: str) -> RunningTrainingRoute | None:
    result = await db.execute(
        select(RunningTrainingRoute)
        .where(RunningTrainingRoute.route_id == route_id)
    )
    return result.scalar_one_or_none()


# ---- 热门路线申请转赛道 ----

async def count_route_training_records(db: AsyncSession, route_internal_id: uuid.UUID) -> int:
    """统计某条路线的训练参与次数（热度），用于申请资格校验与展示。"""
    result = await db.execute(
        select(func.count())
        .select_from(RunningRouteTrainingRecord)
        .where(RunningRouteTrainingRecord.route_id == route_internal_id)
    )
    return int(result.scalar() or 0)


async def count_route_training_records_by_routes(db: AsyncSession, route_internal_ids: List[uuid.UUID]) -> dict:
    """批量统计多条路线的热度，返回 {route_internal_id: count}。"""
    if not route_internal_ids:
        return {}
    result = await db.execute(
        select(RunningRouteTrainingRecord.route_id, func.count().label("count"))
        .where(RunningRouteTrainingRecord.route_id.in_(route_internal_ids))
        .group_by(RunningRouteTrainingRecord.route_id)
    )
    return {row.route_id: int(row.count) for row in result.all()}


async def create_route_track_application_crud(db: AsyncSession, application: RunningRouteTrackApplication) -> RunningRouteTrackApplication:
    db.add(application)
    await db.flush()
    await db.refresh(application)
    return application


async def get_active_application_by_route(db: AsyncSession, route_internal_id: uuid.UUID) -> RunningRouteTrackApplication | None:
    """取该路线进行中（pending）的申请，用于防止重复提交。"""
    result = await db.execute(
        select(RunningRouteTrackApplication).where(
            RunningRouteTrackApplication.route_id == route_internal_id,
            RunningRouteTrackApplication.status == RouteApplyStatus.pending
        )
    )
    return result.scalar_one_or_none()


async def get_application_by_application_id(db: AsyncSession, application_id: str) -> RunningRouteTrackApplication | None:
    result = await db.execute(
        select(RunningRouteTrackApplication)
        .where(RunningRouteTrackApplication.application_id == application_id)
        .options(
            selectinload(RunningRouteTrackApplication.route).selectinload(RunningTrainingRoute.region),
            selectinload(RunningRouteTrackApplication.user)
        )
    )
    return result.scalar_one_or_none()


async def query_applications_by_status_crud(
    db: AsyncSession,
    status: RouteApplyStatus | None,
    page: int,
    size: int
) -> List[RunningRouteTrackApplication]:
    stmt = (
        select(RunningRouteTrackApplication)
        .options(
            selectinload(RunningRouteTrackApplication.route).selectinload(RunningTrainingRoute.region),
            selectinload(RunningRouteTrackApplication.user)
        )
    )
    if status is not None:
        stmt = stmt.where(RunningRouteTrackApplication.status == status)
    stmt = stmt.order_by(RunningRouteTrackApplication.created_at.desc()).offset((page - 1) * size).limit(size)
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_rank_info_by_route_and_user(
    db: AsyncSession,
    user_id: uuid.UUID,
    route_id: uuid.UUID
) -> tuple[RunningRouteRanklist | None, int | None]:
    rank_info_result = await db.execute(
        select(RunningRouteRanklist)
        .where(
            RunningRouteRanklist.route_id == route_id,
            RunningRouteRanklist.user_id == user_id
        )
    )

    rank_info = rank_info_result.scalar_one_or_none()
    if rank_info is None:
        return None, None

    rank_result = await db.execute(
        select(func.count())
        .select_from(RunningRouteRanklist)
        .where(
            RunningRouteRanklist.route_id == route_id,
            (
                (RunningRouteRanklist.duration_seconds < rank_info.duration_seconds)
                |
                (
                    (RunningRouteRanklist.duration_seconds == rank_info.duration_seconds)
                    &
                    (RunningRouteRanklist.user_id < rank_info.user_id)
                )
            )
        )
    )
    rank = (rank_result.scalar() or 0) + 1
    return rank_info, rank

async def get_running_free_training_record_by_upload_id(db: AsyncSession, user_id: uuid.UUID, client_upload_id: str) -> RunningFreeTrainingRecord | None:
    """按 (user_id, client_upload_id) 查找已存在的自由训练记录，用于重传幂等去重"""
    result = await db.execute(
        select(RunningFreeTrainingRecord).where(
            RunningFreeTrainingRecord.user_id == user_id,
            RunningFreeTrainingRecord.client_upload_id == client_upload_id
        ).limit(1)
    )
    return result.scalar_one_or_none()


async def get_running_route_training_record_by_upload_id(db: AsyncSession, user_id: uuid.UUID, client_upload_id: str) -> RunningRouteTrainingRecord | None:
    """按 (user_id, client_upload_id) 查找已存在的路线训练记录，用于重传幂等去重"""
    result = await db.execute(
        select(RunningRouteTrainingRecord).where(
            RunningRouteTrainingRecord.user_id == user_id,
            RunningRouteTrainingRecord.client_upload_id == client_upload_id
        ).limit(1)
    )
    return result.scalar_one_or_none()


async def get_route_finish_times(db: AsyncSession, route_internal_id: uuid.UUID) -> list[float]:
    """该路线排行榜按用时升序的完赛成绩数组（预测名次用）。"""
    result = await db.execute(
        select(RunningRouteRanklist.duration_seconds)
        .where(RunningRouteRanklist.route_id == route_internal_id)
        .order_by(RunningRouteRanklist.duration_seconds.asc())
    )
    return [float(r) for r in result.scalars().all()]


async def get_route_pb_profile(db: AsyncSession, route_internal_id: uuid.UUID, user_id: uuid.UUID) -> dict | None:
    """调用者在该路线个人最佳的 split profile（无则 None）。"""
    result = await db.execute(
        select(RunningRouteRanklist.split_profile)
        .where(
            RunningRouteRanklist.route_id == route_internal_id,
            RunningRouteRanklist.user_id == user_id
        )
        .limit(1)
    )
    return result.scalar_one_or_none()
