"""route_to_track_application

支持热门训练路线申请转为赛道：
- Event 加 event_type（normal/community）
- Track.image_url 改为 nullable
- CPRegistrationCardDef 加 premium
- TrainingRoute 加 apply_status
- 新增 bike/running_route_track_applications 申请表

Revision ID: b2bfda035ee2
Revises: 53b309a4deba
Create Date: 2026-06-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b2bfda035ee2'
down_revision: Union[str, None] = '53b309a4deba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # 1. 新建枚举类型
    eventtype = postgresql.ENUM('normal', 'community', name='eventtype')
    routeapplystatus = postgresql.ENUM('none', 'pending', 'approved', 'rejected', name='routeapplystatus')
    tracklifecycle = postgresql.ENUM('oneMonth', 'twoMonth', 'seasonEnd', name='tracklifecycle')
    eventtype.create(bind, checkfirst=True)
    routeapplystatus.create(bind, checkfirst=True)
    tracklifecycle.create(bind, checkfirst=True)

    # 已存在的枚举类型（复用，勿重复创建）
    eventtype_existing = postgresql.ENUM(name='eventtype', create_type=False)
    routeapplystatus_existing = postgresql.ENUM(name='routeapplystatus', create_type=False)
    tracklifecycle_existing = postgresql.ENUM(name='tracklifecycle', create_type=False)
    bike_terrain = postgresql.ENUM(name='biketrackterraintype', create_type=False)
    running_terrain = postgresql.ENUM(name='runningtrackterraintype', create_type=False)

    # 2. Event.event_type（存量行回填 normal 后去掉 server_default）
    for table in ('bike_events', 'running_events'):
        op.add_column(table, sa.Column('event_type', eventtype_existing, nullable=False, server_default='community'))
        op.alter_column(table, 'event_type', server_default=None)

    # 3. Track.image_url 改 nullable
    op.alter_column('bike_tracks', 'image_url', existing_type=sa.String(), nullable=True)
    op.alter_column('running_tracks', 'image_url', existing_type=sa.String(), nullable=True)

    # 4. CPRegistrationCardDef.premium
    op.add_column('cp_registration_card_defs', sa.Column('premium', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.alter_column('cp_registration_card_defs', 'premium', server_default=None)

    # 5. TrainingRoute.apply_status
    for table in ('bike_training_routes', 'running_training_routes'):
        op.add_column(table, sa.Column('apply_status', routeapplystatus_existing, nullable=False, server_default='none'))
        op.alter_column(table, 'apply_status', server_default=None)

    # 6. 申请表
    def _application_table(name: str, terrain_enum):
        op.create_table(
            name,
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('application_id', sa.String(), nullable=False),
            sa.Column('route_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('region_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('language', sa.String(), nullable=False),
            sa.Column('title', sa.String(), nullable=False),
            sa.Column('sub_region_name', sa.String(), nullable=False),
            sa.Column('terrain_type', terrain_enum, nullable=False),
            sa.Column('lifecycle', tracklifecycle_existing, nullable=False),
            sa.Column('is_premium', sa.Boolean(), nullable=False),
            sa.Column('participate_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('status', routeapplystatus_existing, nullable=False, server_default='pending'),
            sa.Column('review_note', sa.String(), nullable=True),
            sa.Column('track_id', sa.String(), nullable=True),
            sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(f'ix_{name}_application_id', name, ['application_id'], unique=True)
        op.create_index(f'ix_{name}_route_id', name, ['route_id'], unique=False)
        op.create_index(f'ix_{name}_user_id', name, ['user_id'], unique=False)
        op.create_index(f'idx_{name}_status', name, ['status', 'created_at'], unique=False)

    _application_table('bike_route_track_applications', bike_terrain)
    _application_table('running_route_track_applications', running_terrain)


def downgrade() -> None:
    for name in ('running_route_track_applications', 'bike_route_track_applications'):
        op.drop_index(f'idx_{name}_status', table_name=name)
        op.drop_index(f'ix_{name}_user_id', table_name=name)
        op.drop_index(f'ix_{name}_route_id', table_name=name)
        op.drop_index(f'ix_{name}_application_id', table_name=name)
        op.drop_table(name)

    for table in ('bike_training_routes', 'running_training_routes'):
        op.drop_column(table, 'apply_status')

    op.drop_column('cp_registration_card_defs', 'premium')

    op.alter_column('running_tracks', 'image_url', existing_type=sa.String(), nullable=False)
    op.alter_column('bike_tracks', 'image_url', existing_type=sa.String(), nullable=False)

    for table in ('bike_events', 'running_events'):
        op.drop_column(table, 'event_type')

    bind = op.get_bind()
    postgresql.ENUM(name='tracklifecycle').drop(bind, checkfirst=True)
    postgresql.ENUM(name='routeapplystatus').drop(bind, checkfirst=True)
    postgresql.ENUM(name='eventtype').drop(bind, checkfirst=True)
