"""add composite index on user grid familiarity for occupancy ranking

为「已占领网格数」查询（统计用户在某网格 familiarity_count 排名第一的网格数）加复合索引：
- user_grid_familiarity_bike / running 基础表
- 索引列 (season_id, grid_x, grid_y, familiarity_count, updated_at)
让 NOT EXISTS 子查询按 (season_id, grid_x, grid_y) 定位后用 familiarity_count/updated_at
直接判断是否被他人超越，避免全表扫描。

Revision ID: d3f1a9c4b2e7
Revises: c4e8b1fa2d76
Create Date: 2026-06-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'd3f1a9c4b2e7'
down_revision: Union[str, None] = 'c4e8b1fa2d76'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_INDEXES: list[tuple[str, str]] = [
    ("ix_user_grid_familiarity_bike_grid_rank", "user_grid_familiarity_bike"),
    ("ix_user_grid_familiarity_running_grid_rank", "user_grid_familiarity_running"),
]

_COLUMNS = ["season_id", "grid_x", "grid_y", "familiarity_count", "updated_at"]


def upgrade() -> None:
    for index_name, table in _INDEXES:
        op.create_index(index_name, table, _COLUMNS, unique=False)


def downgrade() -> None:
    pass
