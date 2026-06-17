"""add split_profile for realtime rank & self pace compare

为「运动中实时预测名次 + 自我对比」存档每人最佳成绩的 split profile（时间-里程曲线）：
- bike/running_route_ranklists：路线训练的「每人每路线最佳」行加 split_profile
- bike/running_race_records：比赛记录加 split_profile（仅在刷新 PB 时写）
profile 为 JSONB（{L, N, splits[]}），可空（历史数据 / 非最佳记录为 NULL）。

Revision ID: c4e8b1fa2d76
Revises: f7a2c9b14d3e
Create Date: 2026-06-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c4e8b1fa2d76'
down_revision: Union[str, None] = 'f7a2c9b14d3e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TABLES: list[str] = [
    "bike_route_ranklists",
    "running_route_ranklists",
    "bike_race_records",
    "running_race_records",
]


def upgrade() -> None:
    for table in _TABLES:
        op.add_column(table, sa.Column("split_profile", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    pass
