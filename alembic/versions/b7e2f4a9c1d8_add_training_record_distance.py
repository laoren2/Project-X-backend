"""add distance column to training records + backfill from path

为「训练模块周训练汇总」的总距离指标，给 4 张训练记录表新增 distance 列（单位 km，
与 compute_distance 返回一致），并从已存的轨迹 path JSON 回填历史记录。
新记录在 finish 流程中写入；聚合查询按 local_date 对 distance 求和。

Revision ID: b7e2f4a9c1d8
Revises: d3f1a9c4b2e7
Create Date: 2026-06-25 00:00:00.000000

"""
from typing import Sequence, Union
import json
import math

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7e2f4a9c1d8'
down_revision: Union[str, None] = 'd3f1a9c4b2e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_RECORD_TABLES: list[str] = [
    "bike_free_training_records",
    "running_free_training_records",
    "bike_route_training_records",
    "running_route_training_records",
]

# (记录表, 轨迹表)：记录表 path_id 关联轨迹表主键 id
_RECORD_PATH_PAIRS: list[tuple[str, str]] = [
    ("bike_free_training_records", "bike_free_training_paths"),
    ("running_free_training_records", "running_free_training_paths"),
    ("bike_route_training_records", "bike_route_training_paths"),
    ("running_route_training_records", "running_route_training_paths"),
]

_EARTH_RADIUS = 6371000.0  # 米


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
    )
    return _EARTH_RADIUS * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _path_distance_km(path) -> float:
    if isinstance(path, str):
        try:
            path = json.loads(path)
        except (ValueError, TypeError):
            return 0.0
    if not path or len(path) < 2:
        return 0.0
    total = 0.0
    prev = None
    for p in path:
        if not isinstance(p, dict):
            continue
        base = p.get("base")
        if not isinstance(base, dict):
            continue
        lat = base.get("lat")
        lon = base.get("lon")
        if lat is None or lon is None:
            continue
        try:
            lat = float(lat)
            lon = float(lon)
        except (TypeError, ValueError):
            continue
        if prev is not None:
            total += _haversine_m(prev[0], prev[1], lat, lon)
        prev = (lat, lon)
    return total / 1000.0


def upgrade() -> None:
    for table in _RECORD_TABLES:
        op.add_column(table, sa.Column("distance", sa.Float(), nullable=False, server_default="0"))

    # 回填历史记录：从轨迹 path JSON 逐条计算距离
    conn = op.get_bind()
    for rec_table, path_table in _RECORD_PATH_PAIRS:
        rows = conn.execute(
            sa.text(
                f"SELECT r.id AS rid, p.path AS path "
                f"FROM {rec_table} r JOIN {path_table} p ON r.path_id = p.id"
            )
        ).fetchall()
        for row in rows:
            dist = _path_distance_km(row.path)
            if dist > 0:
                conn.execute(
                    sa.text(f"UPDATE {rec_table} SET distance = :d WHERE id = :id"),
                    {"d": dist, "id": row.rid},
                )


def downgrade() -> None:
    pass
