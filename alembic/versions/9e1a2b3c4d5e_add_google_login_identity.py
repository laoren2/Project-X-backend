"""add Google login identity

Revision ID: 9e1a2b3c4d5e
Revises: c9d4e1f70a52
Create Date: 2026-07-20 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9e1a2b3c4d5e"
down_revision: Union[str, None] = "c9d4e1f70a52"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 先新增可空列，再扩展恢复方式约束；旧客户端和旧用户数据保持兼容。
    op.add_column("users", sa.Column("google_sub", sa.String(), nullable=True))
    op.add_column("users", sa.Column("google_email", sa.String(), nullable=True))
    op.create_index(
        "uq_users_google_sub_status",
        "users",
        ["google_sub"],
        unique=True,
        postgresql_where=sa.text("status IN ('normal', 'banned')"),
    )
    op.execute(
        """
        ALTER TABLE users
        DROP CONSTRAINT IF EXISTS ck_user_phone_or_apple_id_not_null
        """
    )
    op.execute(
        """
        ALTER TABLE users
        DROP CONSTRAINT IF EXISTS ck_user_phone_or_apple_id_or_email_not_null
        """
    )
    op.create_check_constraint(
        "ck_user_phone_or_apple_id_or_email_not_null",
        "users",
        "phone_number IS NOT NULL OR apple_id IS NOT NULL OR google_sub IS NOT NULL OR email IS NOT NULL",
    )


def downgrade() -> None:
    # Google-only 用户无法表达在旧约束中；拒绝降级以避免静默丢失其恢复方式。
    pass
