from sqlalchemy import Column, String, Boolean, DateTime, func, UniqueConstraint, Integer, Float, Enum, Date, Index
from sqlalchemy.dialects.postgresql import UUID
from app.schemas.competition.bike import BikeTrackTerrainType
from app.schemas.competition.running import RunningTrackTerrainType
from app.schemas.training.common import RouteType
from app.db.base import Base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict
from geoalchemy2 import Geometry
import uuid


# 暂时保存国家 grid 范围（弃用）
COUNTRY_GRIDS_BBOX = {
    "KR": (38.62226528, 125.34306912, 33.16020748, 130.92873665),
    "TW": (26.28872719, 118.26983294, 21.86414334, 122.02333580),
    "HK": (22.5630725, 113.82416054, 22.17282617, 114.41189433),
    "CN": (41.059233, 114.84595390, 29.41635100, 122.242919),
    "US": (71.42736545, -179.20383122, 18.90647722, -66.94494637)
}

# 网格 buff 系统
'''class EffectGrid(Base):
    __tablename__ = "effect_grids"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # 所属区域
    region_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    # 网格坐标
    grid_x = Column(Integer, nullable=False)
    grid_y = Column(Integer, nullable=False)
    # 类型
    # effect_type = Column(String, nullable=False)  
    # e.g. "buff", "debuff"
    # 奖励
    reward_type = Column(String, nullable=False)  
    # e.g. "xp", "coin", "energy"
    reward_value = Column(Float, nullable=False)
    # 条件（核心）
    condition_type = Column(String, nullable=False)  
    # e.g. "visit_count", "distance", "unique_grids"
    condition_params = Column(MutableDict.as_mutable(JSONB), nullable=False)
    # e.g. {"min": 3}
    # 生命周期（用于每日刷新）
    active_date = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "region_id", "grid_x", "grid_y", "active_date",
            name="uq_effect_grids_region_grid_date"
        ),
    )'''


# 用户网格熟悉度表
class UserGridFamiliarityBike(Base):
    __tablename__ = "user_grid_familiarity_bike"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    season_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    region_id = Column(UUID(as_uuid=True), index=True, nullable=False)

    grid_x = Column(Integer, nullable=False)
    grid_y = Column(Integer, nullable=False)
    familiarity_count = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("season_id", "user_id", "grid_x", "grid_y", name="uq_user_grid_familiarity_bike_season_user_grid"),
    )


# 聚合用户网格熟悉度表
class UserGridFamiliarityBikeAgg(Base):
    __tablename__ = "user_grid_familiarity_bike_agg"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    season_id = Column(UUID(as_uuid=True), index=True, nullable=False)

    level = Column(Integer, nullable=False)  # 0=500m,1=1km,2=2km,3=4km

    grid_x = Column(Integer, nullable=False)
    grid_y = Column(Integer, nullable=False)

    familiarity_count = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("season_id", "user_id", "level", "grid_x", "grid_y", name="uq_user_grid_familiarity_bike_agg_season_user_level_grid"),
    )


class UserGridFamiliarityRunning(Base):
    __tablename__ = "user_grid_familiarity_running"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    season_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    region_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    
    grid_x = Column(Integer, nullable=False)
    grid_y = Column(Integer, nullable=False)
    familiarity_count = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("season_id", "user_id", "grid_x", "grid_y", name="uq_user_grid_familiarity_running_season_user_grid"),
    )


class UserGridFamiliarityRunningAgg(Base):
    __tablename__ = "user_grid_familiarity_running_agg"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    season_id = Column(UUID(as_uuid=True), index=True, nullable=False)

    level = Column(Integer, nullable=False)  # 0=500m,1=1km,2=2km,3=4km

    grid_x = Column(Integer, nullable=False)
    grid_y = Column(Integer, nullable=False)

    familiarity_count = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("season_id", "user_id", "level", "grid_x", "grid_y", name="uq_user_grid_familiarity_running_agg_season_user_level_grid"),
    )

# =========================
# 用户训练记录
# =========================
class BikeFreeTrainingRecord(Base):
    __tablename__ = "bike_free_training_records"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_id = Column(String, unique=True, index=True, nullable=False)

    user_id = Column(UUID(as_uuid=True), nullable=False)
    path_id = Column(UUID(as_uuid=True), nullable=False)

    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    duration_seconds = Column(Float, nullable=False)
    local_date = Column(Date, nullable=False)
    settlement_rewards = Column(MutableDict.as_mutable(JSONB), nullable=False)      # 此次训练的结算，可能包含 xp/state_value/familiarity...

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index(
            "idx_bike_free_training_records_user_date",
            "user_id",
            "local_date"
        ),
    )

    # ORM 关系
    user = relationship("User", primaryjoin="foreign(BikeFreeTrainingRecord.user_id)==User.id")
    path = relationship("BikeFreeTrainingPath", primaryjoin="foreign(BikeFreeTrainingRecord.path_id)==BikeFreeTrainingPath.id")

class BikeFreeTrainingPath(Base):
    __tablename__ = "bike_free_training_paths"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    path_id = Column(String, unique=True, index=True, nullable=False)
    #record_id = Column(UUID(as_uuid=True), nullable=False)

    path = Column(JSONB, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class RunningFreeTrainingRecord(Base):
    __tablename__ = "running_free_training_records"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_id = Column(String, unique=True, index=True, nullable=False)

    user_id = Column(UUID(as_uuid=True), nullable=False)
    path_id = Column(UUID(as_uuid=True), nullable=False)

    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    duration_seconds = Column(Float, nullable=False)
    local_date = Column(Date, nullable=False)
    settlement_rewards = Column(MutableDict.as_mutable(JSONB), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index(
            "idx_running_free_training_records_user_date",
            "user_id",
            "local_date"
        ),
    )

    # ORM 关系
    user = relationship("User", primaryjoin="foreign(RunningFreeTrainingRecord.user_id)==User.id")
    path = relationship("RunningFreeTrainingPath", primaryjoin="foreign(RunningFreeTrainingRecord.path_id)==RunningFreeTrainingPath.id")

class RunningFreeTrainingPath(Base):
    __tablename__ = "running_free_training_paths"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    path_id = Column(String, unique=True, index=True, nullable=False)
    #record_id = Column(UUID(as_uuid=True), nullable=False)

    path = Column(JSONB, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# =========================
# 用户训练情况统计
# =========================
class UserTrainingStateBike(Base):
    __tablename__ = "user_training_states_bike"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    current_value = Column(Integer, default=0, nullable=False)
    last_training_at = Column(DateTime(timezone=True), nullable=True)
    last_decay_date = Column(Date, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class UserTrainingStateDailyBike(Base):
    __tablename__ = "user_training_states_daily_bike"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    value = Column(Integer, default=0, nullable=False)
    delta = Column(Integer, default=0, nullable=False)
    local_date = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "local_date", name="uq_user_training_state_daily_bike_user_date"),
    )

class UserTrainingStateRunning(Base):
    __tablename__ = "user_training_states_running"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    current_value = Column(Integer, default=0, nullable=False)
    last_training_at = Column(DateTime(timezone=True), nullable=True)
    last_decay_date = Column(Date, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class UserTrainingStateDailyRunning(Base):
    __tablename__ = "user_training_states_daily_running"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    value = Column(Integer, default=0, nullable=False)
    delta = Column(Integer, default=0, nullable=False)
    local_date = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "local_date", name="uq_user_training_state_daily_running_user_date"),
    )

# Bike 训练路线
class BikeTrainingRoute(Base):
    __tablename__ = "bike_training_routes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    route_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), index=True, nullable=False)    # 路线创造者
    region_id = Column(UUID(as_uuid=True), index=True, nullable=False)  # 路线所在区域

    # 路线类型
    route_type = Column(Enum(RouteType), nullable=False)
    # 路线地理数据
    route_data = Column(JSONB, nullable=False)
    # 路线的空间几何
    route_geometry = Column(Geometry("LINESTRING", srid=4326, spatial_index=False), nullable=False)

    # 路线基本信息
    is_premium = Column(Boolean, nullable=False)
    start_point = Column(Geometry("POINT", srid=4326, spatial_index=False), nullable=False)
    end_point = Column(Geometry("POINT", srid=4326, spatial_index=False), nullable=False)
    title = Column(String, nullable=False)
    elevation_difference = Column(Integer, default=0, nullable=False)
    total_distance = Column(Float, nullable=False)
    terrain_type = Column(Enum(BikeTrackTerrainType), nullable=False)
    is_public = Column(Boolean, nullable=False)
    enable_ranklist = Column(Boolean, nullable=False)
    enable_magiccard = Column(Boolean, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", primaryjoin="foreign(BikeTrainingRoute.user_id)==User.id", uselist=False)
    region = relationship("Region", primaryjoin="foreign(BikeTrainingRoute.region_id)==Region.id", uselist=False)

    # 空间索引
    __table_args__ = (
        Index("idx_bike_routes_start_point", "start_point", postgresql_using="gist"),
        Index("idx_bike_routes_end_point", "end_point", postgresql_using="gist"),
        Index("idx_bike_routes_geometry", "route_geometry", postgresql_using="gist"),
    )
    

# Running 训练路线
class RunningTrainingRoute(Base):
    __tablename__ = "running_training_routes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    route_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), index=True, nullable=False)    # 路线创造者
    region_id = Column(UUID(as_uuid=True), index=True, nullable=False)  # 路线所在区域

    # 路线类型
    route_type = Column(Enum(RouteType), nullable=False)
    # 路线地理数据
    route_data = Column(JSONB, nullable=False)
    # 路线的空间几何
    route_geometry = Column(Geometry("LINESTRING", srid=4326, spatial_index=False), nullable=False)

    # 路线基本信息
    is_premium = Column(Boolean, nullable=False)
    start_point = Column(Geometry("POINT", srid=4326, spatial_index=False), nullable=False)
    end_point = Column(Geometry("POINT", srid=4326, spatial_index=False), nullable=False)
    title = Column(String, nullable=False)
    elevation_difference = Column(Integer, default=0, nullable=False)
    total_distance = Column(Float, nullable=False)
    terrain_type = Column(Enum(RunningTrackTerrainType), nullable=False)
    is_public = Column(Boolean, nullable=False)
    enable_ranklist = Column(Boolean, nullable=False)
    enable_magiccard = Column(Boolean, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", primaryjoin="foreign(RunningTrainingRoute.user_id)==User.id", uselist=False)
    region = relationship("Region", primaryjoin="foreign(RunningTrainingRoute.region_id)==Region.id", uselist=False)

    # 空间索引
    __table_args__ = (
        Index("idx_running_routes_start_point", "start_point", postgresql_using="gist"),
        Index("idx_running_routes_end_point", "end_point", postgresql_using="gist"),
        Index("idx_running_routes_geometry", "route_geometry", postgresql_using="gist"),
    )


class BikeRouteTrainingRecord(Base):
    __tablename__ = "bike_route_training_records"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_id = Column(String, unique=True, index=True, nullable=False)

    user_id = Column(UUID(as_uuid=True), nullable=False)
    route_id = Column(UUID(as_uuid=True), nullable=False)
    path_id = Column(UUID(as_uuid=True), nullable=False)

    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    duration_seconds = Column(Float, nullable=False)
    penalty_seconds = Column(Float, default=0, nullable=False)
    local_date = Column(Date, index=True, nullable=False)
    settlement_rewards = Column(MutableDict.as_mutable(JSONB), nullable=False)       # 此次训练的结算，可能包含 xp/state_value/familiarity...

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # ORM 关系
    user = relationship("User", primaryjoin="foreign(BikeRouteTrainingRecord.user_id)==User.id", uselist=False)
    route = relationship("BikeTrainingRoute", primaryjoin="foreign(BikeRouteTrainingRecord.route_id)==BikeTrainingRoute.id", uselist=False)
    path = relationship("BikeRouteTrainingPath", primaryjoin="foreign(BikeRouteTrainingRecord.path_id)==BikeRouteTrainingPath.id", uselist=False)
    card_bonus = relationship("CardBonusInBikeRouteTrainingRecord", primaryjoin="BikeRouteTrainingRecord.id==foreign(CardBonusInBikeRouteTrainingRecord.record_id)", uselist=True)

class BikeRouteTrainingPath(Base):
    __tablename__ = "bike_route_training_paths"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    path_id = Column(String, unique=True, index=True, nullable=False)

    path = Column(JSONB, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class CardBonusInBikeRouteTrainingRecord(Base):
    __tablename__ = "card_bonus_in_bike_route_training_records"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_id = Column(UUID(as_uuid=True), nullable=False)
    card_id = Column(UUID(as_uuid=True), nullable=False)
    bonus_ratio = Column(Float, nullable=True)
    bonus_time = Column(Float, default=0, nullable=False)

    card = relationship("UserEquipmentCard", primaryjoin="foreign(CardBonusInBikeRouteTrainingRecord.card_id)==UserEquipmentCard.id")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class RunningRouteTrainingRecord(Base):
    __tablename__ = "running_route_training_records"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_id = Column(String, unique=True, index=True, nullable=False)

    user_id = Column(UUID(as_uuid=True), nullable=False)
    route_id = Column(UUID(as_uuid=True), nullable=False)
    path_id = Column(UUID(as_uuid=True), nullable=False)

    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    duration_seconds = Column(Float, nullable=False)
    penalty_seconds = Column(Float, default=0, nullable=False)
    local_date = Column(Date, index=True, nullable=False)
    settlement_rewards = Column(MutableDict.as_mutable(JSONB), nullable=False)       # 此次训练的结算，可能包含 xp/state_value/familiarity...

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # ORM 关系
    user = relationship("User", primaryjoin="foreign(RunningRouteTrainingRecord.user_id)==User.id", uselist=False)
    route = relationship("RunningTrainingRoute", primaryjoin="foreign(RunningRouteTrainingRecord.route_id)==RunningTrainingRoute.id", uselist=False)
    path = relationship("RunningRouteTrainingPath", primaryjoin="foreign(RunningRouteTrainingRecord.path_id)==RunningRouteTrainingPath.id", uselist=False)
    card_bonus = relationship("CardBonusInRunningRouteTrainingRecord", primaryjoin="RunningRouteTrainingRecord.id==foreign(CardBonusInRunningRouteTrainingRecord.record_id)", uselist=True)

class RunningRouteTrainingPath(Base):
    __tablename__ = "running_route_training_paths"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    path_id = Column(String, unique=True, index=True, nullable=False)

    path = Column(JSONB, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class CardBonusInRunningRouteTrainingRecord(Base):
    __tablename__ = "card_bonus_in_running_route_training_records"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_id = Column(UUID(as_uuid=True), nullable=False)
    card_id = Column(UUID(as_uuid=True), nullable=False)
    bonus_ratio = Column(Float, nullable=True)
    bonus_time = Column(Float, default=0, nullable=False)

    card = relationship("UserEquipmentCard", primaryjoin="foreign(CardBonusInRunningRouteTrainingRecord.card_id)==UserEquipmentCard.id")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)