"""add record visibility and App Store notification idempotency

为用户设置新增比赛结果可见范围，默认 public 以保持历史结果对外可见；
同时为订阅事件新增 App Store Server Notification V2 的幂等键。

Revision ID: c2f8a1d4e7b9
Revises: a1b2c3d4e5f6
Create Date: 2026-07-23 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c2f8a1d4e7b9"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    visibility = postgresql.ENUM(
        "public", "followers", "friends",
        name="recordvisibility",
        create_type=False,
    )
    visibility.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "user_settings",
        sa.Column(
            "record_visibility",
            visibility,
            nullable=False,
            server_default="public",
        ),
    )
    op.add_column("subscription_events", sa.Column("notification_uuid", sa.String(), nullable=True))
    op.create_unique_constraint(
        "uq_subscription_events_notification_uuid",
        "subscription_events",
        ["notification_uuid"],
    )


def downgrade() -> None:
    pass
