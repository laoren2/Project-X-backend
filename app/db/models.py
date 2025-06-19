import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime, func, UniqueConstraint, Integer, Float
from sqlalchemy.dialects.postgresql import UUID
from app.schemas.user import UserRole
from app.db.base import Base
from sqlalchemy.orm import relationship

# 用户表
class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(String, unique=True, index=True, nullable=False)
    role = Column(String, nullable=False, default=UserRole.user.value)

    nickname = Column(String, unique=True, nullable=False)
    phone_number = Column(String, unique=True, index=True, nullable=False)
    avatar_image_url = Column(String, nullable=False)
    background_image_url = Column(String, nullable=False)
    introduction = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    birthday = Column(String, nullable=True)
    location = Column(String, nullable=True)
    identity_auth_name = Column(String, nullable=True)
    is_realname_auth = Column(Boolean, default=False)
    is_identity_auth = Column(Boolean, default=False)
    is_display_gender = Column(Boolean, default=False)
    is_display_age = Column(Boolean, default=False)
    is_display_location = Column(Boolean, default=False)
    enable_auto_location = Column(Boolean, default=False)
    is_display_identity = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

# 用户关注关系表
class UserFollow(Base):
    __tablename__ = "user_follows"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    follower_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    followed_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("follower_id", "followed_id", name="uq_follower_followed"),
    )

    # 与users表建立关联关系，可以方便的获取关注者和被关注者的User对象
    follower = relationship("User", foreign_keys=[follower_id])
    followed = relationship("User", foreign_keys=[followed_id])


# 地区表
# 说明：采用外键方式便于规范化区域管理，支持多赛事共享同一区域、支持未来添加区域元数据（如地图、天气等）
class Region(Base):
    __tablename__ = "regions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)
    country_code = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    bike_events = relationship("BikeEvent", back_populates="region", cascade="all, delete", passive_deletes=True)
    running_events = relationship("RunningEvent", back_populates="region", cascade="all, delete", passive_deletes=True)

# 赛季表
class Season(Base):
    __tablename__ = "seasons"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    season_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    sport_type = Column(String, nullable=False)  # 比如 "running", "bike"
    image_url = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    bike_events = relationship("BikeEvent", back_populates="season", cascade="all, delete", passive_deletes=True)
    running_events = relationship("RunningEvent", back_populates="season", cascade="all, delete", passive_deletes=True)

# Bike赛事表
class BikeEvent(Base):
    __tablename__ = "bike_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    region_id = Column(UUID(as_uuid=True), ForeignKey("regions.id", ondelete="CASCADE"), nullable=False)
    season_id = Column(UUID(as_uuid=True), ForeignKey("seasons.id", ondelete="CASCADE"), nullable=False)
    image_url = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    region = relationship("Region", back_populates="bike_events")
    season = relationship("Season", back_populates="bike_events")
    tracks = relationship("BikeTrack", back_populates="event", cascade="all, delete", passive_deletes=True)


# Bike赛道表
class BikeTrack(Base):
    __tablename__ = "bike_tracks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    track_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    event_id = Column(UUID(as_uuid=True), ForeignKey("bike_events.id", ondelete="CASCADE"), nullable=False)
    from_lat = Column(Float, nullable=False)
    from_lng = Column(Float, nullable=False)
    to_lat = Column(Float, nullable=False)
    to_lng = Column(Float, nullable=False)

    elevation_difference = Column(Integer, default=0)
    sub_region_name = Column(String, nullable=False)
    fee = Column(Integer, default=0)
    prize_pool = Column(Integer, default=0)

    image_url = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    event = relationship("BikeEvent", back_populates="tracks")


# Bike赛事表
class RunningEvent(Base):
    __tablename__ = "running_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    region_id = Column(UUID(as_uuid=True), ForeignKey("regions.id", ondelete="CASCADE"), nullable=False)
    season_id = Column(UUID(as_uuid=True), ForeignKey("seasons.id", ondelete="CASCADE"), nullable=False)
    image_url = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    region = relationship("Region", back_populates="running_events")
    season = relationship("Season", back_populates="running_events")
    tracks = relationship("RunningTrack", back_populates="event", cascade="all, delete", passive_deletes=True)


# Bike赛道表
class RunningTrack(Base):
    __tablename__ = "running_tracks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    track_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    event_id = Column(UUID(as_uuid=True), ForeignKey("running_events.id", ondelete="CASCADE"), nullable=False)
    from_lat = Column(Float, nullable=False)
    from_lng = Column(Float, nullable=False)
    to_lat = Column(Float, nullable=False)
    to_lng = Column(Float, nullable=False)

    elevation_difference = Column(Integer, default=0)
    sub_region_name = Column(String, nullable=False)
    fee = Column(Integer, default=0)
    prize_pool = Column(Integer, default=0)
    distance = Column(Float, nullable=False)

    image_url = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    event = relationship("RunningEvent", back_populates="tracks")


class BikeRaceRecord(Base):
    __tablename__ = "bike_race_records"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    track_id = Column(UUID(as_uuid=True), ForeignKey("bike_tracks.id"), nullable=False)

    status = Column(String, default="未完成")  # "未完成", "已完成"
    score = Column(Float, nullable=True)
    duration_seconds = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)

    is_team = Column(Boolean, default=False)
    team_code = Column(String, nullable=True)

    # ORM 关系
    user = relationship("User")
    track = relationship("BikeTrack")