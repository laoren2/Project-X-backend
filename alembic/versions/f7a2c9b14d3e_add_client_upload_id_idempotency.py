"""add client_upload_id for idempotent finish upload

为 race / free training / route training 的记录表增加 client_upload_id（客户端生成的幂等键），
并建立 (user_id, client_upload_id) 唯一索引，防止上传失败后手动重传造成重复结算 / 重复发奖。
client_upload_id 可空（旧数据 / 旧客户端为 NULL，PostgreSQL 中 NULL 互不冲突，不影响唯一约束）。

Revision ID: f7a2c9b14d3e
Revises: b2bfda035ee2
Create Date: 2026-06-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7a2c9b14d3e'
down_revision: Union[str, None] = 'b2bfda035ee2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (表名, 唯一索引名)
_TABLES: list[tuple[str, str]] = [
    ("bike_free_training_records", "uq_bike_free_training_records_user_upload"),
    ("running_free_training_records", "uq_running_free_training_records_user_upload"),
    ("bike_route_training_records", "uq_bike_route_training_records_user_upload"),
    ("running_route_training_records", "uq_running_route_training_records_user_upload"),
    ("bike_race_records", "uq_bike_race_records_user_upload"),
    ("running_race_records", "uq_running_race_records_user_upload"),
]


def upgrade() -> None:
    for table, idx in _TABLES:
        op.add_column(table, sa.Column("client_upload_id", sa.String(), nullable=True))
        op.create_index(idx, table, ["user_id", "client_upload_id"], unique=True)


def downgrade() -> None:
    pass
