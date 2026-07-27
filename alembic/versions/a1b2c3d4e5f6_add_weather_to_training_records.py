"""persist workout weather and enable weather buff grids

Revision ID: a1b2c3d4e5f6
Revises: 9e1a2b3c4d5e
Create Date: 2026-07-22 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "9e1a2b3c4d5e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_RECORD_TABLES = (
    "bike_free_training_records",
    "running_free_training_records",
    "bike_route_training_records",
    "running_route_training_records",
    "bike_race_records",
    "running_race_records",
)


def upgrade() -> None:
    # PostgreSQL enum values must be added before rows using the new condition can be written.
    op.execute("ALTER TYPE bikegridconditiontype ADD VALUE IF NOT EXISTS 'weather'")
    op.execute("ALTER TYPE runninggridconditiontype ADD VALUE IF NOT EXISTS 'weather'")
    for table in _RECORD_TABLES:
        op.add_column(table, sa.Column("weather_condition", sa.String(), nullable=True))
        op.add_column(table, sa.Column("weather_temperature_c", sa.Float(), nullable=True))


def downgrade() -> None:
    pass
    # PostgreSQL cannot safely remove enum values in place. Keep `weather` on downgrade.
