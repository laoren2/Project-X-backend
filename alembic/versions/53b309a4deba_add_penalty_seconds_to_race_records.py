"""add_penalty_seconds_to_race_records

Revision ID: 53b309a4deba
Revises: c7f3a9e21d80
Create Date: 2026-06-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '53b309a4deba'
down_revision: Union[str, None] = 'c7f3a9e21d80'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 表中已有存量记录，先用 server_default=0 回填存量行，再去掉 server_default，
    # 后续新行由 ORM 层 default=0 保证。
    for table in ("bike_race_records", "running_race_records"):
        op.add_column(
            table,
            sa.Column("penalty_seconds", sa.Float(), nullable=True)
        )


def downgrade() -> None:
    """Downgrade schema."""
    pass
