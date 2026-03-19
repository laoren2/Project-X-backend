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



# 国家网格表
class CountryGridCell(Base):
    __tablename__ = "country_grid_cells"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    country_code = Column(String, index=True, nullable=False)  # 例如 HK, TW
    grid_code = Column(String, nullable=False)  # 例如 HK_100_99(x:100, y:99)，后续可优化为存储 grid_x, grid_y 先过滤
    geom = Column(Geometry("POLYGON", srid=4326), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("country_code", "grid_code", name="uq_country_grid_cells_country_code_grid_code"),
        Index("idx_country_grid_cells_geom", "geom", postgresql_using="gist"),
    )

# region网格表
class RegionGridCell(Base):
    __tablename__ = "region_grid_cells"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    region_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    grid_id = Column(UUID(as_uuid=True), index=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("region_id", "grid_id", name="uq_region_grid_cells_region_grid"),
    )


# 用户网格熟悉度表
class UserGridFamiliarityBike(Base):
    __tablename__ = "user_grid_familiarity_bike"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    season_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    grid_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    familiarity_count = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("season_id", "user_id", "grid_id", name="uq_season_user_grid_familiarity_bike"),
    )

    grid = relationship(
        "CountryGridCell",
        primaryjoin="foreign(UserGridFamiliarityBike.grid_id)==CountryGridCell.id"
    )

class UserGridFamiliarityRunning(Base):
    __tablename__ = "user_grid_familiarity_running"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    season_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    grid_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    familiarity_count = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("season_id", "user_id", "grid_id", name="uq_season_user_grid_familiarity_running"),
    )

    grid = relationship(
        "CountryGridCell",
        primaryjoin="foreign(UserGridFamiliarityRunning.grid_id)==CountryGridCell.id"
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