from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime, func, UniqueConstraint, Integer, Float, Enum, Date, Index
from sqlalchemy.dialects.postgresql import UUID
from app.schemas.competition.bike import BikeTrackTerrainType
from app.schemas.competition.running import RunningTrackTerrainType
from app.schemas.user import Gender
from app.schemas.common import CCAssetType
from app.db.base import Base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from geoalchemy2 import Geometry
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.mutable import MutableDict
import uuid


# 暂时保存国家 grid 范围
COUNTRY_GRIDS_BBOX = {
    "KR": (38.62226528, 125.34306912, 33.16020748, 130.92873665),
    "TW": (26.28872719, 118.26983294, 21.86414334, 122.02333580),
    "HK": (22.5630725, 113.82416054, 22.17282617, 114.41189433),
    "CN": (41.059233, 114.84595390, 29.41635100, 122.242919)
}


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