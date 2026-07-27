"""add region grid occupancy ranking projections

Revision ID: e6f7a8b9c0d1
Revises: c2f8a1d4e7b9
Create Date: 2026-07-23 16:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, None] = "c2f8a1d4e7b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_projection_tables(sport: str) -> None:
    owner_table = f"{sport}_grid_occupancy_owners"
    occupancy_table = f"{sport}_region_grid_occupancies"

    op.create_table(
        owner_table,
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("season_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("region_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("grid_x", sa.Integer(), nullable=False),
        sa.Column("grid_y", sa.Integer(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("season_id", "grid_x", "grid_y", name=f"uq_{sport}_grid_occupancy_owner_season_grid"),
    )
    op.create_index(f"ix_{sport}_grid_occupancy_owner_season_region", owner_table, ["season_id", "region_id"], unique=False)

    op.create_table(
        occupancy_table,
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("season_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("region_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("occupied_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("season_id", "region_id", "user_id", name=f"uq_{sport}_region_grid_occupancy_season_region_user"),
    )
    op.create_index(
        f"ix_{sport}_region_grid_occupancy_rank",
        occupancy_table,
        ["season_id", "region_id", sa.text("occupied_count DESC"), "updated_at", "user_id"],
        unique=False,
    )


def _backfill_projection(sport: str) -> None:
    familiarity_table = f"user_grid_familiarity_{sport}"
    owner_table = f"{sport}_grid_occupancy_owners"
    occupancy_table = f"{sport}_region_grid_occupancies"

    # Tie-breaker matches the existing occupancy API: visits DESC, earlier update first.
    op.execute(
        f"""
        WITH ranked AS (
            SELECT season_id, region_id, grid_x, grid_y, user_id,
                   ROW_NUMBER() OVER (
                       PARTITION BY season_id, grid_x, grid_y
                       ORDER BY familiarity_count DESC, updated_at ASC, user_id ASC
                   ) AS row_no
            FROM {familiarity_table}
        ), owners AS (
            SELECT season_id, region_id, grid_x, grid_y, user_id
            FROM ranked WHERE row_no = 1
        )
        INSERT INTO {owner_table} (id, season_id, region_id, grid_x, grid_y, user_id, created_at, updated_at)
        SELECT gen_random_uuid(), season_id, region_id, grid_x, grid_y, user_id, NOW(), NOW()
        FROM owners
        """
    )
    op.execute(
        f"""
        INSERT INTO {occupancy_table} (id, season_id, region_id, user_id, occupied_count, created_at, updated_at)
        SELECT gen_random_uuid(), season_id, region_id, user_id, COUNT(*), NOW(), NOW()
        FROM {owner_table}
        GROUP BY season_id, region_id, user_id
        """
    )


def upgrade() -> None:
    for sport in ("bike", "running"):
        _create_projection_tables(sport)
        _backfill_projection(sport)


def downgrade() -> None:
    pass
