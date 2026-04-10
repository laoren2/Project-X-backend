from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_, exists, case, text
from app.db.models.competition import BikeTrack
from app.db.models.training import (
    BikeFreeTrainingRecord, UserTrainingStateBike,
    UserGridFamiliarityBike, UserTrainingStateDailyBike, UserGridFamiliarityBikeAgg
)
from sqlalchemy.orm import selectinload
from app.schemas.training.common import GridTileKey, GridCellInfo, GridTileResponse, GridTileInfo
from typing import List
from datetime import date, timedelta, datetime
from sqlalchemy.dialects.postgresql import insert
from app.core.tools import get_tile_size
from collections import defaultdict
import uuid, math, calendar, json


# 计算用户对某条赛道的熟悉度（起终点直线 + Buffer 带状区域 + 指数距离衰减）
async def get_familiarity_by_track_and_user(db: AsyncSession, track: BikeTrack, user_id: uuid.UUID) -> float:
    start_lat = track.from_lat
    start_lon = track.from_lng
    end_lat = track.to_lat
    end_lon = track.to_lng

    # 根据起终点直线距离自动计算 buffer_meters
    R = 6371000  # 地球半径（米）
    lat1 = math.radians(start_lat)
    lon1 = math.radians(start_lon)
    lat2 = math.radians(end_lat)
    lon2 = math.radians(end_lon)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    race_length_m = R * c

    # buffer 设为赛道长度的 20%，并限制在 800m ~ 4000m 之间
    buffer_meters = max(800.0, min(race_length_m * 0.2, 4000.0))

    # 指数衰减参数（控制衰减速度）
    decay_distance = buffer_meters / 2.0  # 衰减半径

    sql = text(
        """
        WITH params AS (
            SELECT
                CAST(:start_lat AS float) AS start_lat,
                CAST(:start_lon AS float) AS start_lon,
                CAST(:end_lat AS float) AS end_lat,
                CAST(:end_lon AS float) AS end_lon,
                CAST(:buffer_meters AS float) AS buffer_meters
        ),

        -- 将经纬度转为 WebMercator (米)
        line AS (
            SELECT
                ST_Transform(
                    ST_SetSRID(ST_MakeLine(
                        ST_MakePoint(start_lon, start_lat),
                        ST_MakePoint(end_lon, end_lat)
                    ), 4326),
                    3857
                ) AS geom
            FROM params
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
            FROM user_grid_familiarity_bike
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
            "start_lat": start_lat,
            "start_lon": start_lon,
            "end_lat": end_lat,
            "end_lon": end_lon,
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


async def get_training_state_by_user(db: AsyncSession, user_id: uuid.UUID) -> UserTrainingStateBike | None:
    result = await db.execute(
        select(UserTrainingStateBike)
        .where(
            UserTrainingStateBike.user_id == user_id
        )
    )
    return result.scalar_one_or_none()

async def get_training_state_daily_by_user_date(db: AsyncSession, user_id: uuid.UUID, date: date) -> UserTrainingStateDailyBike | None:
    result = await db.execute(
        select(UserTrainingStateDailyBike)
        .where(
            UserTrainingStateDailyBike.user_id == user_id,
            UserTrainingStateDailyBike.local_date == date
        )
    )
    return result.scalar_one_or_none()

# 查询用户某月的所有训练状态变化
async def get_training_states_by_user_and_month(db: AsyncSession, user_id: uuid.UUID, month: str) -> List[UserTrainingStateDailyBike]:
    # 解析 month
    year, mon = map(int, month.split("-"))

    start_date = date(year, mon, 1)
    last_day = calendar.monthrange(year, mon)[1]
    end_date = date(year, mon, last_day)

    result = await db.execute(
        select(UserTrainingStateDailyBike)
        .where(
            UserTrainingStateDailyBike.user_id == user_id,
            UserTrainingStateDailyBike.local_date >= start_date,
            UserTrainingStateDailyBike.local_date <= end_date
        )
        .order_by(UserTrainingStateDailyBike.local_date)
    )
    return result.scalars().all()


# 查询用户某天的训练记录
async def get_training_records_by_user_and_day(db: AsyncSession, user_id: uuid.UUID, day: str) -> List[BikeFreeTrainingRecord]:
    target_date = date.fromisoformat(day)
    result = await db.execute(
        select(BikeFreeTrainingRecord)
        .options(selectinload(BikeFreeTrainingRecord.path))
        .where(
            BikeFreeTrainingRecord.user_id == user_id,
            BikeFreeTrainingRecord.local_date == target_date
        )
        .order_by(BikeFreeTrainingRecord.start_time.asc())
    )
    return result.scalars().all()

async def get_training_state_by_user(db: AsyncSession, user_id: uuid.UUID) -> UserTrainingStateBike | None:
    result = await db.execute(
        select(UserTrainingStateBike)
        .where(UserTrainingStateBike.user_id == user_id)
    )
    return result.scalar_one_or_none()

async def add_or_update_daily_training_states(
    db: AsyncSession,
    user_id: uuid.UUID,
    local_date: date,
    delta: int,
    new_value: int
):
    stmt = insert(UserTrainingStateDailyBike).values(
        user_id=user_id,
        local_date=local_date,
        delta=delta,
        value=new_value
    ).on_conflict_do_update(
        index_elements=["user_id", "local_date"],
        set_={
            "delta": UserTrainingStateDailyBike.delta + delta,
            "value": UserTrainingStateDailyBike.value + delta
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
            INSERT INTO user_grid_familiarity_bike (
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
            SET familiarity_count = user_grid_familiarity_bike.familiarity_count + 1,
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
            INSERT INTO user_grid_familiarity_bike_agg (
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
            SET familiarity_count = user_grid_familiarity_bike_agg.familiarity_count + EXCLUDED.familiarity_count
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
        .select_from(UserGridFamiliarityBike)
        .where(
            UserGridFamiliarityBike.region_id == region_id,
            UserGridFamiliarityBike.user_id == user_id,
            UserGridFamiliarityBike.season_id == season_id
        )
    )
    return explored_grids or 0

async def get_record_by_record_id(db: AsyncSession, record_id: str) -> BikeFreeTrainingRecord | None:
    record = await db.execute(
        select(BikeFreeTrainingRecord)
        .where(BikeFreeTrainingRecord.record_id == record_id)
        .options(
            selectinload(BikeFreeTrainingRecord.path)
        )
    )
    return record.scalar_one_or_none()

async def get_familiarity_grids_by_tiles(
    db: AsyncSession,
    user_id: uuid.UUID,
    season_id: uuid.UUID,
    tiles: List[GridTileKey]
) -> GridTileResponse:
    if not tiles:
        return GridTileResponse(tiles=[])

    level = tiles[0].level  # 同一批一定同 level
    tile_size = get_tile_size(level)

    # 计算整体 bounding box（超级关键优化）
    min_x = min(t.x for t in tiles) * tile_size
    max_x = (max(t.x for t in tiles) + 1) * tile_size - 1
    min_y = min(t.y for t in tiles) * tile_size
    max_y = (max(t.y for t in tiles) + 1) * tile_size - 1

    stmt = (
        select(
            UserGridFamiliarityBikeAgg.grid_x,
            UserGridFamiliarityBikeAgg.grid_y,
            UserGridFamiliarityBikeAgg.familiarity_count
        )
        .where(
            and_(
                UserGridFamiliarityBikeAgg.user_id == user_id,
                UserGridFamiliarityBikeAgg.season_id == season_id,
                UserGridFamiliarityBikeAgg.level == level,
                UserGridFamiliarityBikeAgg.grid_x >= min_x,
                UserGridFamiliarityBikeAgg.grid_x <= max_x,
                UserGridFamiliarityBikeAgg.grid_y >= min_y,
                UserGridFamiliarityBikeAgg.grid_y <= max_y,
            )
        )
    )

    result = await db.execute(stmt)
    rows = result.all()

    # 分桶到 tile
    tile_map = defaultdict(list)

    for r in rows:
        tile_x = r.grid_x // tile_size
        tile_y = r.grid_y // tile_size

        key = (tile_x, tile_y)

        tile_map[key].append(GridCellInfo(
            grid_x=r.grid_x,
            grid_y=r.grid_y,
            count=r.familiarity_count
        ))

    # 组装返回
    result_tiles = []
    for tile in tiles:
        key = (tile.x, tile.y)
        result_tiles.append(GridTileInfo(
            key=GridTileKey(level=tile.level, x=tile.x, y=tile.y),
            cells=tile_map.get(key, [])
        ))

    return GridTileResponse(tiles=result_tiles)