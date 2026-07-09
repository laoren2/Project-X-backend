"""user_settings 增加 auto_pause / global_default_sport；cp_asset_defs 上提 sport_type 到基类

- user_settings: 新增 auto_pause(Bool, 默认 True)、global_default_sport(sporttype, 默认 bike)
- cp_asset_defs: 新增 sport_type(sporttype, NOT NULL)，从 3 张子类表(registration/team/route
  card def)回填后，删除子类表的 sport_type 列（sport_type 统一收敛到基类）

Revision ID: c9d4e1f70a52
Revises: b7e2f4a9c1d8
Create Date: 2026-07-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c9d4e1f70a52'
down_revision: Union[str, None] = 'b7e2f4a9c1d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# 复用已存在的 sporttype 枚举，勿重复 CREATE TYPE
_sporttype = postgresql.ENUM('running', 'bike', name='sporttype', create_type=False)

_CP_SUBCLASS_TABLES = ['cp_registration_card_defs', 'cp_team_card_defs', 'cp_route_card_defs']


def upgrade() -> None:
    # 1. user_settings 两个新字段（先带 server_default 回填存量行，再去掉 server_default 与 ORM 保持一致）
    op.add_column('user_settings', sa.Column('global_default_sport', _sporttype, nullable=False, server_default='bike'))
    op.add_column('user_settings', sa.Column('auto_pause', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.alter_column('user_settings', 'global_default_sport', server_default=None)
    op.alter_column('user_settings', 'auto_pause', server_default=None)

    # 2. cp_asset_defs.sport_type：先可空新增，从子类表回填，再置 NOT NULL
    op.add_column('cp_asset_defs', sa.Column('sport_type', _sporttype, nullable=True))
    conn = op.get_bind()
    for sub in _CP_SUBCLASS_TABLES:
        conn.execute(sa.text(
            f"UPDATE cp_asset_defs d SET sport_type = s.sport_type "
            f"FROM {sub} s WHERE d.id = s.id"
        ))
    op.alter_column('cp_asset_defs', 'sport_type', nullable=False)

    # 3. 删除子类表冗余的 sport_type 列
    for sub in _CP_SUBCLASS_TABLES:
        op.drop_column(sub, 'sport_type')


def downgrade() -> None:
    # 逆向：把 sport_type 还给子类表并回填，再从基类删除
    pass
