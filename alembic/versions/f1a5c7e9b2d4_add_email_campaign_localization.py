"""add email campaign localization

Revision ID: f1a5c7e9b2d4
Revises: e4f8a2b6c0d3
Create Date: 2026-07-30 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f1a5c7e9b2d4"
down_revision: Union[str, None] = "e4f8a2b6c0d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    language_enum = postgresql.ENUM(
        "zh_hans", "zh_hant", "en", "ko", "ja", "fr",
        name="language",
        create_type=False,
    )
    language_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "user_settings",
        sa.Column("preferred_language", language_enum, nullable=False, server_default="en"),
    )
    op.add_column(
        "email_campaign_recipients",
        sa.Column("language", language_enum, nullable=False, server_default="en"),
    )

    # 语言集合仅覆盖产品已本地化的六种语言；未覆盖的时区安全回退为英文。
    op.execute("""
        UPDATE user_settings AS settings
        SET preferred_language = CASE
            WHEN users.timezone = 'Asia/Tokyo' THEN 'ja'::language
            WHEN users.timezone = 'Europe/Paris' THEN 'fr'::language
            WHEN users.timezone = 'Asia/Shanghai' THEN 'zh_hans'::language
            WHEN users.timezone = 'Asia/Taipei' THEN 'zh_hant'::language
            WHEN users.timezone = 'Asia/Hong_Kong' THEN 'zh_hant'::language
            WHEN users.timezone = 'Asia/Seoul' THEN 'ko'::language
            WHEN users.timezone IN (
                'UTC', 'America/Los_Angeles', 'US/Pacific',
                'Europe/Istanbul', 'Europe/Dublin', 'Europe/Amsterdam'
            ) THEN 'en'::language
            ELSE 'en'::language
        END
        FROM users
        WHERE settings.user_id = users.id
    """)
    # 已创建但尚未发送的 campaign 也使用所属用户的同一回填结果。
    op.execute("""
        UPDATE email_campaign_recipients AS recipient
        SET language = settings.preferred_language
        FROM user_settings AS settings
        WHERE recipient.user_id = settings.user_id
    """)
    op.alter_column("user_settings", "preferred_language", server_default=None)
    op.alter_column("email_campaign_recipients", "language", server_default=None)


def downgrade() -> None:
    pass
