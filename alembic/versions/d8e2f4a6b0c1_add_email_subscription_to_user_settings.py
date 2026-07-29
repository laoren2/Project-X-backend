"""add email subscription to user settings

Revision ID: d8e2f4a6b0c1
Revises: f8b3c6d1e4a2
Create Date: 2026-07-29 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d8e2f4a6b0c1"
down_revision: Union[str, None] = "f8b3c6d1e4a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 以服务端默认值一次性回填现有用户；随后移除默认值，让 ORM 负责新建设置的默认值。
    op.add_column(
        "user_settings",
        sa.Column("is_email_subscribed", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.alter_column("user_settings", "is_email_subscribed", server_default=None)


def downgrade() -> None:
    pass
