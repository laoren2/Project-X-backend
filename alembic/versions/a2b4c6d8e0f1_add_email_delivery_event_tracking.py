"""add email delivery event tracking

Revision ID: a2b4c6d8e0f1
Revises: f1a5c7e9b2d4
Create Date: 2026-08-01 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "a2b4c6d8e0f1"
down_revision: Union[str, None] = "f1a5c7e9b2d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("email_campaign_recipients", sa.Column("message_id", sa.String(), nullable=True))
    op.create_index(
        "ix_email_campaign_recipients_message_id",
        "email_campaign_recipients",
        ["message_id"],
        unique=True,
    )
    op.create_table(
        "email_campaign_suppressions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_event_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("email", name="uq_email_campaign_suppressions_email"),
    )
    op.alter_column("email_campaign_suppressions", "is_active", server_default=None)


def downgrade() -> None:
    pass