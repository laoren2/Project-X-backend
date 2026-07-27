from sqlalchemy import Column, String, Boolean, DateTime, func, UniqueConstraint, Integer, Float, Enum, Date, Index
from sqlalchemy.dialects.postgresql import UUID
from app.schemas.competition.bike import BikeTrackTerrainType
from app.schemas.competition.running import RunningTrackTerrainType
from app.schemas.training.common import RouteType, GridEffectType, RouteApplyStatus, TrackLifecycle
from app.schemas.training.bike import BikeGridConditionType
from app.schemas.training.running import RunningGridConditionType
from app.schemas.user import Gender
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
class BikeEffectGrid(Base):
    __tablename__ = "bike_effect_grids"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    region_id = Column(UUID(as_uuid=True), index=True, nullable=False)      # 所属区域
    grid_x = Column(Integer, nullable=False)
    grid_y = Column(Integer, nullable=False)

    description_i18n = Column(JSONB, nullable=False)
    effect_type = Column(Enum(GridEffectType), nullable=False)            # buff / debuff
    condition_type = Column(Enum(BikeGridConditionType), nullable=False)     # e.g. "visit_count", "distance", "unique_grids"
    condition_params = Column(JSONB, nullable=False)    # e.g. {"min": 3}
    reward_type = Column(String, nullable=False)
    reward_count = Column(Integer, nullable=False)
    active_date = Column(Date, nullable=False, index=True)      # 生命周期（用于每日刷新）

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "grid_x", "grid_y", "active_date",
            name="uq_bike_effect_grids_grid_date"
        ),
    )

# 记录用户 buff 网格的应用情况（应用后不可重复展示和应用）
class BikeEffectGridHistory(Base):
    __tablename__ = "bike_effect_grids_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    grid_x = Column(Integer, nullable=False)
    grid_y = Column(Integer, nullable=False)
    active_date = Column(Date, nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "user_id", "grid_x", "grid_y", "active_date",
            name="uq_bike_effect_grids_history_user_grid_date"
        ),
    )

class BikeEffectGridTileAgg(Base):
    __tablename__ = "bike_effect_grid_tile_aggs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    active_date = Column(Date, nullable=False, index=True)
    level = Column(Integer, nullable=False)
    grid_x = Column(Integer, nullable=False)
    grid_y = Column(Integer, nullable=False)

    grid_previews = Column(JSONB, nullable=False)      # tile 内所有 buff grid 预览信息

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "active_date", "level", "grid_x", "grid_y",
            name="uq_bike_effect_grid_tile_aggs_level_grid_date"
        ),
    )

class RunningEffectGrid(Base):
    __tablename__ = "running_effect_grids"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    region_id = Column(UUID(as_uuid=True), index=True, nullable=False)      # 所属区域
    grid_x = Column(Integer, nullable=False)
    grid_y = Column(Integer, nullable=False)

    description_i18n = Column(JSONB, nullable=False)
    effect_type = Column(Enum(GridEffectType), nullable=False)            # buff / debuff
    condition_type = Column(Enum(RunningGridConditionType), nullable=False)     # e.g. "visit_count", "distance", "unique_grids"
    condition_params = Column(JSONB, nullable=False)    # e.g. {"min": 3}
    reward_type = Column(String, nullable=False)
    reward_count = Column(Integer, nullable=False)
    active_date = Column(Date, nullable=False, index=True)      # 生命周期（用于每日刷新）

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "grid_x", "grid_y", "active_date",
            name="uq_running_effect_grids_grid_date"
        ),
    )

# 记录用户 buff 网格的应用情况（应用后不可重复展示和应用）
class RunningEffectGridHistory(Base):
    __tablename__ = "running_effect_grids_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    grid_x = Column(Integer, nullable=False)
    grid_y = Column(Integer, nullable=False)
    active_date = Column(Date, nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "user_id", "grid_x", "grid_y", "active_date",
            name="uq_running_effect_grids_history_user_grid_date"
        ),
    )

class RunningEffectGridTileAgg(Base):
    __tablename__ = "running_effect_grid_tile_aggs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    active_date = Column(Date, nullable=False, index=True)
    level = Column(Integer, nullable=False)
    grid_x = Column(Integer, nullable=False)
    grid_y = Column(Integer, nullable=False)

    grid_previews = Column(JSONB, nullable=False)      # tile 内所有 buff grid 预览信息

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "active_date", "level", "grid_x", "grid_y",
            name="uq_running_effect_grid_tile_aggs_level_grid_date"
        ),
    )

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
        # 已占领网格数查询：NOT EXISTS 按 (season_id, grid_x, grid_y) 定位后用 count/updated_at 判定是否被超越
        Index("ix_user_grid_familiarity_bike_grid_rank", "season_id", "grid_x", "grid_y", "familiarity_count", "updated_at"),
    )


# 当前赛季基础网格的占领者。训练写入时按网格加事务锁后重算，作为区域排行榜的准确投影源。
class BikeGridOccupancyOwner(Base):
    __tablename__ = "bike_grid_occupancy_owners"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    season_id = Column(UUID(as_uuid=True), nullable=False)
    region_id = Column(UUID(as_uuid=True), nullable=False)
    grid_x = Column(Integer, nullable=False)
    grid_y = Column(Integer, nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("season_id", "grid_x", "grid_y", name="uq_bike_grid_occupancy_owner_season_grid"),
        Index("ix_bike_grid_occupancy_owner_season_region", "season_id", "region_id"),
    )


# 当前赛季用户在一个 region 内占领的基础网格数，供个人数值和排行榜直接读取。
class BikeRegionGridOccupancy(Base):
    __tablename__ = "bike_region_grid_occupancies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    season_id = Column(UUID(as_uuid=True), nullable=False)
    region_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    occupied_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("season_id", "region_id", "user_id", name="uq_bike_region_grid_occupancy_season_region_user"),
        Index("ix_bike_region_grid_occupancy_rank", "season_id", "region_id", occupied_count.desc(), "updated_at", "user_id"),
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
        # 已占领网格数查询：NOT EXISTS 按 (season_id, grid_x, grid_y) 定位后用 count/updated_at 判定是否被超越
        Index("ix_user_grid_familiarity_running_grid_rank", "season_id", "grid_x", "grid_y", "familiarity_count", "updated_at"),
    )


class RunningGridOccupancyOwner(Base):
    __tablename__ = "running_grid_occupancy_owners"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    season_id = Column(UUID(as_uuid=True), nullable=False)
    region_id = Column(UUID(as_uuid=True), nullable=False)
    grid_x = Column(Integer, nullable=False)
    grid_y = Column(Integer, nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("season_id", "grid_x", "grid_y", name="uq_running_grid_occupancy_owner_season_grid"),
        Index("ix_running_grid_occupancy_owner_season_region", "season_id", "region_id"),
    )


class RunningRegionGridOccupancy(Base):
    __tablename__ = "running_region_grid_occupancies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    season_id = Column(UUID(as_uuid=True), nullable=False)
    region_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    occupied_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("season_id", "region_id", "user_id", name="uq_running_region_grid_occupancy_season_region_user"),
        Index("ix_running_region_grid_occupancy_rank", "season_id", "region_id", occupied_count.desc(), "updated_at", "user_id"),
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
    distance = Column(Float, nullable=False, server_default="0")      # 本次训练距离(km)
    local_date = Column(Date, nullable=False)
    settlement_rewards = Column(MutableDict.as_mutable(JSONB), nullable=False)      # 此次训练的结算，可能包含 xp/state_value/familiarity...
    triggered_buffs = Column(JSONB, nullable=False, server_default="[]")            # 训练触发的 buff grids 快照
    weather_condition = Column(String, nullable=True)
    weather_temperature_c = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    client_upload_id = Column(String, nullable=True)        # 客户端幂等键，防止重传重复结算

    __table_args__ = (
        Index(
            "idx_bike_free_training_records_user_date",
            "user_id",
            "local_date"
        ),
        Index(
            "uq_bike_free_training_records_user_upload",
            "user_id",
            "client_upload_id",
            unique=True
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
    distance = Column(Float, nullable=False, server_default="0")      # 本次训练距离(km)
    local_date = Column(Date, nullable=False)
    settlement_rewards = Column(MutableDict.as_mutable(JSONB), nullable=False)
    triggered_buffs = Column(JSONB, nullable=False, server_default="[]")            # 训练触发的 buff grids 快照
    weather_condition = Column(String, nullable=True)
    weather_temperature_c = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    client_upload_id = Column(String, nullable=True)        # 客户端幂等键，防止重传重复结算

    __table_args__ = (
        Index(
            "idx_running_free_training_records_user_date",
            "user_id",
            "local_date"
        ),
        Index(
            "uq_running_free_training_records_user_upload",
            "user_id",
            "client_upload_id",
            unique=True
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
    apply_status = Column(Enum(RouteApplyStatus), default=RouteApplyStatus.none, nullable=False)  # 申请转为赛道的状态

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
    apply_status = Column(Enum(RouteApplyStatus), default=RouteApplyStatus.none, nullable=False)  # 申请转为赛道的状态

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
    distance = Column(Float, nullable=False, server_default="0")      # 本次训练距离(km)
    penalty_seconds = Column(Float, default=0, nullable=False)
    local_date = Column(Date, index=True, nullable=False)
    settlement_rewards = Column(MutableDict.as_mutable(JSONB), nullable=False)       # 此次训练的结算，可能包含 xp/state_value/familiarity...
    weather_condition = Column(String, nullable=True)
    weather_temperature_c = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    client_upload_id = Column(String, nullable=True)        # 客户端幂等键，防止重传重复结算
    pace_snapshot_id = Column(UUID(as_uuid=True), nullable=True)  # 视频水印配速快照（独立表）

    # ORM 关系
    user = relationship("User", primaryjoin="foreign(BikeRouteTrainingRecord.user_id)==User.id", uselist=False)
    route = relationship("BikeTrainingRoute", primaryjoin="foreign(BikeRouteTrainingRecord.route_id)==BikeTrainingRoute.id", uselist=False)
    path = relationship("BikeRouteTrainingPath", primaryjoin="foreign(BikeRouteTrainingRecord.path_id)==BikeRouteTrainingPath.id", uselist=False)
    card_bonus = relationship("CardBonusInBikeRouteTrainingRecord", primaryjoin="BikeRouteTrainingRecord.id==foreign(CardBonusInBikeRouteTrainingRecord.record_id)", uselist=True)

    __table_args__ = (
        Index(
            "idx_bike_route_training_records_route_user",
            "route_id",
            "user_id"
        ),
        Index(
            "uq_bike_route_training_records_user_upload",
            "user_id",
            "client_upload_id",
            unique=True
        ),
    )


class BikeRouteRanklist(Base):
    __tablename__ = "bike_route_ranklists"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    route_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    gender = Column(Enum(Gender), nullable=False)

    # 最佳成绩来源record
    record_id = Column(UUID(as_uuid=True), nullable=False)
    duration_seconds = Column(Float, nullable=False)
    split_profile = Column(JSONB, nullable=True)        # 最佳成绩的 split profile（实时自我对比 / 预测名次基线）

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint(
            "route_id",
            "user_id",
            name="uq_bike_route_ranklist_route_user"
        ),
        # 核心排行榜索引
        Index(
            "idx_bike_route_ranklist_route_score",
            "route_id",
            "gender",
            "duration_seconds",
            "user_id"
        ),
    )

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
    distance = Column(Float, nullable=False, server_default="0")      # 本次训练距离(km)
    penalty_seconds = Column(Float, default=0, nullable=False)
    local_date = Column(Date, index=True, nullable=False)
    settlement_rewards = Column(MutableDict.as_mutable(JSONB), nullable=False)       # 此次训练的结算，可能包含 xp/state_value/familiarity...
    weather_condition = Column(String, nullable=True)
    weather_temperature_c = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    client_upload_id = Column(String, nullable=True)        # 客户端幂等键，防止重传重复结算
    pace_snapshot_id = Column(UUID(as_uuid=True), nullable=True)  # 视频水印配速快照（独立表）

    # ORM 关系
    user = relationship("User", primaryjoin="foreign(RunningRouteTrainingRecord.user_id)==User.id", uselist=False)
    route = relationship("RunningTrainingRoute", primaryjoin="foreign(RunningRouteTrainingRecord.route_id)==RunningTrainingRoute.id", uselist=False)
    path = relationship("RunningRouteTrainingPath", primaryjoin="foreign(RunningRouteTrainingRecord.path_id)==RunningRouteTrainingPath.id", uselist=False)
    card_bonus = relationship("CardBonusInRunningRouteTrainingRecord", primaryjoin="RunningRouteTrainingRecord.id==foreign(CardBonusInRunningRouteTrainingRecord.record_id)", uselist=True)

    __table_args__ = (
        Index(
            "idx_running_route_training_records_route_user",
            "route_id",
            "user_id"
        ),
        Index(
            "uq_running_route_training_records_user_upload",
            "user_id",
            "client_upload_id",
            unique=True
        ),
    )


class RunningRouteRanklist(Base):
    __tablename__ = "running_route_ranklists"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    route_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    gender = Column(Enum(Gender), nullable=False)

    # 最佳成绩来源record
    record_id = Column(UUID(as_uuid=True), nullable=False)
    duration_seconds = Column(Float, nullable=False)
    split_profile = Column(JSONB, nullable=True)        # 最佳成绩的 split profile（实时自我对比 / 预测名次基线）

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint(
            "route_id",
            "user_id",
            name="uq_running_route_ranklist_route_user"
        ),
        # 核心排行榜索引
        Index(
            "idx_running_route_ranklist_route_score",
            "route_id",
            "gender",
            "duration_seconds",
            "user_id"
        ),
    )

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


# 热门路线申请转为赛道（Bike）
class BikeRouteTrackApplication(Base):
    __tablename__ = "bike_route_track_applications"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(String, unique=True, index=True, nullable=False)

    route_id = Column(UUID(as_uuid=True), index=True, nullable=False)    # 关联 BikeTrainingRoute.id
    user_id = Column(UUID(as_uuid=True), index=True, nullable=False)     # 申请人
    region_id = Column(UUID(as_uuid=True), nullable=False)              # 申请时路线所在 region 快照

    # 申请表单（i18n 仅保存申请语言一档，language 标记其语言）
    language = Column(String, nullable=False)
    title = Column(String, nullable=False)
    sub_region_name = Column(String, nullable=False)
    terrain_type = Column(Enum(BikeTrackTerrainType), nullable=False)
    lifecycle = Column(Enum(TrackLifecycle), nullable=False)
    is_premium = Column(Boolean, nullable=False)                        # 取自 route.is_premium，决定报名卡档位
    participate_count = Column(Integer, default=0, nullable=False)      # 申请时的热度快照

    status = Column(Enum(RouteApplyStatus), default=RouteApplyStatus.pending, nullable=False)
    review_note = Column(String, nullable=True)                        # 驳回原因 / 审核备注
    track_id = Column(String, nullable=True)                          # 审核通过后生成的赛道业务 id
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    route = relationship("BikeTrainingRoute", primaryjoin="foreign(BikeRouteTrackApplication.route_id)==BikeTrainingRoute.id", uselist=False)
    user = relationship("User", primaryjoin="foreign(BikeRouteTrackApplication.user_id)==User.id", uselist=False)

    __table_args__ = (
        Index("idx_bike_route_track_applications_status", "status", "created_at"),
    )


# 热门路线申请转为赛道（Running）
class RunningRouteTrackApplication(Base):
    __tablename__ = "running_route_track_applications"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(String, unique=True, index=True, nullable=False)

    route_id = Column(UUID(as_uuid=True), index=True, nullable=False)    # 关联 RunningTrainingRoute.id
    user_id = Column(UUID(as_uuid=True), index=True, nullable=False)     # 申请人
    region_id = Column(UUID(as_uuid=True), nullable=False)              # 申请时路线所在 region 快照

    # 申请表单（i18n 仅保存申请语言一档，language 标记其语言）
    language = Column(String, nullable=False)
    title = Column(String, nullable=False)
    sub_region_name = Column(String, nullable=False)
    terrain_type = Column(Enum(RunningTrackTerrainType), nullable=False)
    lifecycle = Column(Enum(TrackLifecycle), nullable=False)
    is_premium = Column(Boolean, nullable=False)                        # 取自 route.is_premium，决定报名卡档位
    participate_count = Column(Integer, default=0, nullable=False)      # 申请时的热度快照

    status = Column(Enum(RouteApplyStatus), default=RouteApplyStatus.pending, nullable=False)
    review_note = Column(String, nullable=True)                        # 驳回原因 / 审核备注
    track_id = Column(String, nullable=True)                          # 审核通过后生成的赛道业务 id
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    route = relationship("RunningTrainingRoute", primaryjoin="foreign(RunningRouteTrackApplication.route_id)==RunningTrainingRoute.id", uselist=False)
    user = relationship("User", primaryjoin="foreign(RunningRouteTrackApplication.user_id)==User.id", uselist=False)

    __table_args__ = (
        Index("idx_running_route_track_applications_status", "status", "created_at"),
    )
