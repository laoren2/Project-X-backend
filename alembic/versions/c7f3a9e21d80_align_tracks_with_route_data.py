"""align competition tracks/records with route_data (multipoint routes)

Revision ID: c7f3a9e21d80
Revises: 04f23c05a42a
Create Date: 2026-06-03 00:00:00.000000

把 bike_tracks / running_tracks 由「起点+终点」结构升级为对齐 training route 的
route_type / route_data / route_geometry / start_point / end_point 多检查点结构；
bike_race_records / running_race_records 增加 route_data 快照列。

无线上用户：已有 track 的 from/to 会被转换为 2 点 pointToPoint 的 route_data 并回填几何，
record.route_data 从其 track 回填。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import geoalchemy2

# revision identifiers, used by Alembic.
revision: str = 'c7f3a9e21d80'
down_revision: Union[str, None] = '04f23c05a42a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TRACK_TABLES = ["bike_tracks", "running_tracks"]
RECORD_TABLES = ["bike_race_records", "running_race_records"]

# routetype enum 已由 training route 迁移创建，这里复用，勿重复 CREATE TYPE
_route_type_enum = postgresql.ENUM(
    'pointToPoint', 'multiPoints', name='routetype', create_type=False
)


def _line_geom(table: str) -> str:
    # gist 索引名按表区分
    return table.replace("_tracks", "")


def upgrade() -> None:
    for table in TRACK_TABLES:
        # 1) 先以可空方式新增列，便于回填已有数据
        op.add_column(table, sa.Column('route_type', _route_type_enum, nullable=True))
        op.add_column(table, sa.Column('route_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
        op.add_column(table, sa.Column('route_geometry', geoalchemy2.types.Geometry(
            geometry_type='LINESTRING', srid=4326, dimension=2, spatial_index=False,
            from_text='ST_GeomFromEWKT', name='geometry'), nullable=True))
        op.add_column(table, sa.Column('start_point', geoalchemy2.types.Geometry(
            geometry_type='POINT', srid=4326, dimension=2, spatial_index=False,
            from_text='ST_GeomFromEWKT', name='geometry'), nullable=True))
        op.add_column(table, sa.Column('end_point', geoalchemy2.types.Geometry(
            geometry_type='POINT', srid=4326, dimension=2, spatial_index=False,
            from_text='ST_GeomFromEWKT', name='geometry'), nullable=True))

        # 2) 用已有 from/to 回填为 2 点 pointToPoint 路线
        op.execute(f"""
            UPDATE {table} SET
                route_type = 'pointToPoint'::routetype,
                route_data = jsonb_build_object(
                    'type', 'pointToPoint',
                    'steps', jsonb_build_array(
                        jsonb_build_object('kind','checkpoint','lat',from_lat,'lng',from_lng,'radius',from_radius),
                        jsonb_build_object('kind','checkpoint','lat',to_lat,'lng',to_lng,'radius',to_radius)
                    )
                ),
                route_geometry = ST_SetSRID(ST_MakeLine(ST_MakePoint(from_lng, from_lat), ST_MakePoint(to_lng, to_lat)), 4326),
                start_point = ST_SetSRID(ST_MakePoint(from_lng, from_lat), 4326),
                end_point = ST_SetSRID(ST_MakePoint(to_lng, to_lat), 4326)
        """)

        # 3) 置为 NOT NULL
        op.alter_column(table, 'route_type', nullable=False)
        op.alter_column(table, 'route_data', nullable=False)
        op.alter_column(table, 'route_geometry', nullable=False)
        op.alter_column(table, 'start_point', nullable=False)
        op.alter_column(table, 'end_point', nullable=False)

        # 4) gist 空间索引
        prefix = _line_geom(table)
        op.create_index(f'idx_{prefix}_tracks_start_point', table, ['start_point'], unique=False, postgresql_using='gist')
        op.create_index(f'idx_{prefix}_tracks_end_point', table, ['end_point'], unique=False, postgresql_using='gist')
        op.create_index(f'idx_{prefix}_tracks_geometry', table, ['route_geometry'], unique=False, postgresql_using='gist')

        # 5) 删除旧的起终点列
        for col in ['from_lat', 'from_lng', 'from_radius', 'to_lat', 'to_lng', 'to_radius']:
            op.drop_column(table, col)

    # record 表：新增 route_data 快照列，从 track 回填后置为 NOT NULL
    for rtable, ttable in zip(RECORD_TABLES, TRACK_TABLES):
        op.add_column(rtable, sa.Column('route_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
        op.execute(f"""
            UPDATE {rtable} r SET route_data = t.route_data
            FROM {ttable} t WHERE r.track_id = t.id
        """)
        # 清理 track 已不存在、无法回填的孤儿记录（无线上用户），再置为 NOT NULL
        op.execute(f"DELETE FROM {rtable} WHERE route_data IS NULL")
        op.alter_column(rtable, 'route_data', nullable=False)


def downgrade() -> None:
    # 一律不回退
    pass