"""add shared pace snapshot table for video watermarks

Revision ID: f8b3c6d1e4a2
Revises: e6f7a8b9c0d1
Create Date: 2026-07-27 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f8b3c6d1e4a2"
down_revision: Union[str, None] = "e6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_RECORD_TABLES = [
    "bike_race_records",
    "running_race_records",
    "bike_route_training_records",
    "running_route_training_records",
]


def upgrade() -> None:
    op.create_table(
        "video_watermark_pace_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    for record_table in _RECORD_TABLES:
        op.add_column(record_table, sa.Column("pace_snapshot_id", postgresql.UUID(as_uuid=True), nullable=True))


def downgrade() -> None:
    pass
