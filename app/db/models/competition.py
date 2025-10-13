import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime, func, UniqueConstraint, Integer, Float, Enum, Numeric
from sqlalchemy.dialects.postgresql import UUID
from app.schemas.competition.common import RecordStatus, TeamStatus
from app.schemas.user import Gender
from app.db.base import Base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB



# 地区表
# 说明：采用外键方式便于规范化区域管理，支持多赛事共享同一区域、支持未来添加区域元数据（如地图、天气等）
class Region(Base):
    __tablename__ = "regions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)
    country_code = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    bike_events = relationship("BikeEvent", primaryjoin="Region.id==foreign(BikeEvent.region_id)", back_populates="region")
    running_events = relationship("RunningEvent", primaryjoin="Region.id==foreign(RunningEvent.region_id)", back_populates="region")

# Bike赛季表
class BikeSeason(Base):
    __tablename__ = "bike_seasons"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    season_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    image_url = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    bike_events = relationship("BikeEvent", primaryjoin="BikeSeason.id==foreign(BikeEvent.season_id)", back_populates="season")

# Running赛季表
class RunningSeason(Base):
    __tablename__ = "running_seasons"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    season_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    image_url = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    running_events = relationship("RunningEvent", primaryjoin="RunningSeason.id==foreign(RunningEvent.season_id)", back_populates="season")

# Bike赛事表
class BikeEvent(Base):
    __tablename__ = "bike_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    region_id = Column(UUID(as_uuid=True), nullable=False)
    season_id = Column(UUID(as_uuid=True), nullable=False)
    image_url = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    region = relationship("Region", primaryjoin="foreign(BikeEvent.region_id)==Region.id", back_populates="bike_events")
    season = relationship("BikeSeason", primaryjoin="foreign(BikeEvent.season_id)==BikeSeason.id", back_populates="bike_events")
    tracks = relationship("BikeTrack", primaryjoin="BikeEvent.id==foreign(BikeTrack.event_id)", back_populates="event")


# Bike赛道表
class BikeTrack(Base):
    __tablename__ = "bike_tracks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    track_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    event_id = Column(UUID(as_uuid=True), nullable=False)
    from_lat = Column(Float, nullable=False)
    from_lng = Column(Float, nullable=False)
    to_lat = Column(Float, nullable=False)
    to_lng = Column(Float, nullable=False)

    elevation_difference = Column(Integer, default=0, nullable=False)
    sub_region_name = Column(String, nullable=False)
    prize_pool = Column(Integer, default=0, nullable=False)     # 暂只支持金券
    score = Column(Integer, default=0, nullable=False)          # 赛道冠军对应积分

    image_url = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    event = relationship("BikeEvent", primaryjoin="foreign(BikeTrack.event_id)==BikeEvent.id", back_populates="tracks")


# Running赛事表
class RunningEvent(Base):
    __tablename__ = "running_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    region_id = Column(UUID(as_uuid=True), nullable=False)
    season_id = Column(UUID(as_uuid=True), nullable=False)
    image_url = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    region = relationship("Region", primaryjoin="foreign(RunningEvent.region_id)==Region.id", back_populates="running_events")
    season = relationship("RunningSeason", primaryjoin="foreign(RunningEvent.season_id)==RunningSeason.id", back_populates="running_events")
    tracks = relationship("RunningTrack", primaryjoin="RunningEvent.id==foreign(RunningTrack.event_id)", back_populates="event")


# Running赛道表
class RunningTrack(Base):
    __tablename__ = "running_tracks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    track_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    event_id = Column(UUID(as_uuid=True), nullable=False)
    from_lat = Column(Float, nullable=False)
    from_lng = Column(Float, nullable=False)
    to_lat = Column(Float, nullable=False)
    to_lng = Column(Float, nullable=False)

    elevation_difference = Column(Integer, default=0, nullable=False)
    sub_region_name = Column(String, nullable=False)
    prize_pool = Column(Integer, default=0, nullable=False)
    score = Column(Integer, default=0, nullable=False)          # 赛道冠军对应积分
    distance = Column(Float, nullable=False)

    image_url = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    event = relationship("RunningEvent", primaryjoin="foreign(RunningTrack.event_id)==RunningEvent.id", back_populates="tracks")


# 需要定期迁移,不要外部依赖
class BikeRaceRecord(Base):
    __tablename__ = "bike_race_records"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_id = Column(String, unique=True, index=True, nullable=False)

    user_id = Column(UUID(as_uuid=True), nullable=False)
    track_id = Column(UUID(as_uuid=True), nullable=False)
    team_id = Column(UUID(as_uuid=True), nullable=True)
    path_id = Column(UUID(as_uuid=True), nullable=True)

    status = Column(Enum(RecordStatus), default=RecordStatus.notStarted, nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)         # 有效成绩

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # ORM 关系
    user = relationship("User", primaryjoin="foreign(BikeRaceRecord.user_id)==User.id")
    track = relationship("BikeTrack", primaryjoin="foreign(BikeRaceRecord.track_id)==BikeTrack.id")
    team = relationship("BikeTeam", primaryjoin="foreign(BikeRaceRecord.team_id)==BikeTeam.id")
    path = relationship("BikeRacePath", primaryjoin="foreign(BikeRaceRecord.path_id)==BikeRacePath.id")
    card_bonus = relationship("CardBonusInBikeRecord", primaryjoin="BikeRaceRecord.id==foreign(CardBonusInBikeRecord.record_id)")


'''class BikeRaceRecordHistory(Base):
    __tablename__ = "bike_race_records_history"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_id = Column(String, unique=True, index=True, nullable=False)

    user_id = Column(UUID(as_uuid=True), nullable=False)
    track_id = Column(UUID(as_uuid=True), nullable=False)
    team_id = Column(UUID(as_uuid=True), nullable=True)
    path_id = Column(UUID(as_uuid=True), nullable=True)

    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    duration_seconds = Column(Float, nullable=False)

    created_at = Column(DateTime(timezone=True), nullable=False)

    user = relationship("User", primaryjoin="foreign(BikeRaceRecordHistory.user_id)==User.id")
    track = relationship("BikeTrack", primaryjoin="foreign(BikeRaceRecordHistory.track_id)==BikeTrack.id")
    #members = relationship("BikeTeamMemberHistory", primaryjoin="foreign(BikeRaceRecordHistory.team_id)==BikeTeamMemberHistory.team_id")
    path = relationship("BikeRacePathHistory", primaryjoin="foreign(BikeRaceRecordHistory.path_id)==BikeRacePathHistory.id")
    card_bonus = relationship("CardBonusInRecordHistory", primaryjoin="BikeRaceRecordHistory.id==foreign(CardBonusInRecordHistory.record_id)")'''


# 需要定期迁移,不要外部依赖
class RunningRaceRecord(Base):
    __tablename__ = "running_race_records"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_id = Column(String, unique=True, index=True, nullable=False)

    user_id = Column(UUID(as_uuid=True), nullable=False)
    track_id = Column(UUID(as_uuid=True), nullable=False)
    team_id = Column(UUID(as_uuid=True), nullable=True)
    path_id = Column(UUID(as_uuid=True), nullable=True)

    status = Column(Enum(RecordStatus), default=RecordStatus.notStarted, nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # ORM 关系
    user = relationship("User", primaryjoin="foreign(RunningRaceRecord.user_id)==User.id")
    track = relationship("RunningTrack", primaryjoin="foreign(RunningRaceRecord.track_id)==RunningTrack.id")
    team = relationship("RunningTeam", primaryjoin="foreign(RunningRaceRecord.team_id)==RunningTeam.id")
    path = relationship("RunningRacePath", primaryjoin="foreign(RunningRaceRecord.path_id)==RunningRacePath.id")
    card_bonus = relationship("CardBonusInRunningRecord", primaryjoin="RunningRaceRecord.id==foreign(CardBonusInRunningRecord.record_id)")


'''class RunningRaceRecordHistory(Base):
    __tablename__ = "running_race_records_history"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_id = Column(String, unique=True, index=True, nullable=False)

    user_id = Column(UUID(as_uuid=True), nullable=False)
    track_id = Column(UUID(as_uuid=True), nullable=False)
    team_id = Column(UUID(as_uuid=True), nullable=True)
    path_id = Column(UUID(as_uuid=True), nullable=True)

    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    duration_seconds = Column(Float, nullable=False)

    created_at = Column(DateTime(timezone=True), nullable=False)

    user = relationship("User", primaryjoin="foreign(RunningRaceRecordHistory.user_id)==User.id")
    track = relationship("RunningTrack", primaryjoin="foreign(RunningRaceRecordHistory.track_id)==RunningTrack.id")
    #members = relationship("RunningTeamMemberHistory", primaryjoin="foreign(RunningRaceRecordHistory.team_id)==RunningTeamMemberHistory.team_id")
    path = relationship("RunningRacePathHistory", primaryjoin="foreign(RunningRaceRecordHistory.path_id)==RunningRacePathHistory.id")
    card_bonus = relationship("CardBonusInRecordHistory", primaryjoin="RunningRaceRecordHistory.id==foreign(CardBonusInRecordHistory.record_id)")'''


# 需要定期迁移,不要外部依赖
class BikeTeam(Base):
    __tablename__ = "bike_teams"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(String, unique=True, index=True, nullable=False)
    team_code = Column(String, unique=True, index=True, nullable=False)
    track_id = Column(UUID(as_uuid=True), nullable=False)

    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    members_count_max = Column(Integer, default=2, nullable=False)
    is_public = Column(Boolean, default=True, nullable=False)
    status = Column(Enum(TeamStatus), default=TeamStatus.prepared, nullable=False)

    track = relationship("BikeTrack", primaryjoin="foreign(BikeTeam.track_id)==BikeTrack.id")
    members = relationship("BikeTeamMember", primaryjoin="BikeTeam.id==foreign(BikeTeamMember.team_id)", back_populates="team", cascade="all, delete")
    applied_members = relationship("BikeTeamAppliedMember", primaryjoin="BikeTeam.id==foreign(BikeTeamAppliedMember.team_id)", back_populates="team", cascade="all, delete")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=False)
    start_date_real = Column(DateTime(timezone=True), nullable=True)


class BikeTeamMember(Base):
    __tablename__ = "bike_team_members"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    member_id = Column(String, unique=True, index=True, nullable=False)
    team_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)

    is_leader = Column(Boolean, default=False, nullable=False)
    is_registered = Column(Boolean, default=False, nullable=False)

    team = relationship("BikeTeam", primaryjoin="foreign(BikeTeamMember.team_id)==BikeTeam.id", back_populates="members")
    user = relationship("User", primaryjoin="foreign(BikeTeamMember.user_id)==User.id")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

# 需要定期迁移,不要外部依赖
'''class BikeTeamMemberHistory(Base):
    __tablename__ = "bike_team_members_history"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)

    is_leader = Column(Boolean, nullable=False)

    created_at = Column(DateTime(timezone=True), nullable=False)'''


class BikeTeamAppliedMember(Base):
    __tablename__ = "bike_team_applied_members"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    member_id = Column(String, unique=True, index=True, nullable=False)
    team_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)

    introduction = Column(String, nullable=True)

    team = relationship("BikeTeam", primaryjoin="foreign(BikeTeamAppliedMember.team_id)==BikeTeam.id", back_populates="applied_members")
    user = relationship("User", primaryjoin="foreign(BikeTeamAppliedMember.user_id)==User.id")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class RunningTeam(Base):
    __tablename__ = "running_teams"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(String, unique=True, index=True, nullable=False)
    team_code = Column(String, unique=True, index=True, nullable=False)
    track_id = Column(UUID(as_uuid=True), nullable=False)

    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    members_count_max = Column(Integer, default=2, nullable=False)
    is_public = Column(Boolean, default=True, nullable=False)
    status = Column(Enum(TeamStatus), default=TeamStatus.prepared, nullable=False)

    track = relationship("RunningTrack", primaryjoin="foreign(RunningTeam.track_id)==RunningTrack.id")
    members = relationship("RunningTeamMember", primaryjoin="RunningTeam.id==foreign(RunningTeamMember.team_id)", back_populates="team", cascade="all, delete")
    applied_members = relationship("RunningTeamAppliedMember", primaryjoin="RunningTeam.id==foreign(RunningTeamAppliedMember.team_id)", back_populates="team", cascade="all, delete")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=False)
    start_date_real = Column(DateTime(timezone=True), nullable=True)

class RunningTeamMember(Base):
    __tablename__ = "running_team_members"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    member_id = Column(String, unique=True, index=True, nullable=False)
    team_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)

    is_leader = Column(Boolean, default=False, nullable=False)
    is_registered = Column(Boolean, default=False, nullable=False)

    team = relationship("RunningTeam", primaryjoin="foreign(RunningTeamMember.team_id)==RunningTeam.id", back_populates="members")
    user = relationship("User", primaryjoin="foreign(RunningTeamMember.user_id)==User.id")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

'''class RunningTeamMemberHistory(Base):
    __tablename__ = "running_team_members_history"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)

    is_leader = Column(Boolean, nullable=False)

    created_at = Column(DateTime(timezone=True), nullable=False)'''


class RunningTeamAppliedMember(Base):
    __tablename__ = "running_team_applied_members"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    member_id = Column(String, unique=True, index=True, nullable=False)
    team_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)

    introduction = Column(String, nullable=True)

    team = relationship("RunningTeam", primaryjoin="foreign(RunningTeamAppliedMember.team_id)==RunningTeam.id", back_populates="applied_members")
    user = relationship("User", primaryjoin="foreign(RunningTeamAppliedMember.user_id)==User.id")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# 自行车比赛路径表
class BikeRacePath(Base):
    __tablename__ = "bike_race_paths"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    path_id = Column(String, unique=True, index=True, nullable=False)
    record_id = Column(UUID(as_uuid=True), nullable=False)

    # 路径点数组，例如 [{"lat": xx, "lon": xx, "timestamp": xx}, ...]
    path = Column(JSONB, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


'''class BikeRacePathHistory(Base):
    __tablename__ = "bike_race_path_history"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    path_id = Column(String, unique=True, index=True, nullable=False)
    record_id = Column(UUID(as_uuid=True), nullable=False)

    # 路径点数组，例如 [{"lat": xx, "lon": xx, "timestamp": xx}, ...]
    path = Column(JSONB, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)'''


class RunningRacePath(Base):
    __tablename__ = "running_race_paths"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    path_id = Column(String, unique=True, index=True, nullable=False)
    record_id = Column(UUID(as_uuid=True), nullable=False)

    # 路径点数组，例如 [{"lat": xx, "lon": xx, "timestamp": xx}, ...]
    path = Column(JSONB, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# 跑步比赛路径表
'''class RunningRacePathHistory(Base):
    __tablename__ = "running_race_paths_history"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    path_id = Column(String, unique=True, index=True, nullable=False)
    record_id = Column(UUID(as_uuid=True), nullable=False)

    path = Column(JSONB, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)'''


class CardBonusInBikeRecord(Base):
    __tablename__ = "card_bonus_in_bike_records"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_id = Column(UUID(as_uuid=True), nullable=False)
    card_id = Column(UUID(as_uuid=True), nullable=False)
    bonus_time = Column(Float, default=0, nullable=False)

    card = relationship("UserEquipmentCard", primaryjoin="foreign(CardBonusInBikeRecord.card_id)==UserEquipmentCard.id")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CardBonusInRunningRecord(Base):
    __tablename__ = "card_bonus_in_running_records"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_id = Column(UUID(as_uuid=True), nullable=False)
    card_id = Column(UUID(as_uuid=True), nullable=False)
    bonus_time = Column(Float, default=0, nullable=False)

    card = relationship("UserEquipmentCard", primaryjoin="foreign(CardBonusInRunningRecord.card_id)==UserEquipmentCard.id")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


'''class CardBonusInRecordHistory(Base):
    __tablename__ = "card_bonus_in_records_history"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_id = Column(UUID(as_uuid=True), nullable=False)
    card_id = Column(UUID(as_uuid=True), nullable=False)
    bonus_time = Column(Integer, default=0, nullable=False)

    card = relationship("UserEquipmentCard", primaryjoin="foreign(CardBonusInRecordHistory.card_id)==UserEquipmentCard.id")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)'''

class BikeLeaderboard(Base):
    __tablename__ = "bike_leaderboard"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    track_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    gender = Column(Enum(Gender), nullable=False)
    rank_position = Column(Integer, nullable=False)
    user_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    record_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    duration_seconds = Column(Float, nullable=False)
    reward = Column(JSONB, nullable=False)        # 暂只支持金券
    score = Column(Integer, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # 每个赛道性别组合的排名唯一
    __table_args__ = (
        UniqueConstraint('track_id', 'gender', 'rank_position', name='uq_bike_leaderboard_track_gender_rank'),
    )
    # 每个赛道的用户记录唯一
    __table_args__ = (
        UniqueConstraint('track_id', 'user_id', name='uq_bike_leaderboard_track_user'),
    )
    
    # ORM 关系
    record = relationship("BikeRaceRecord",primaryjoin="foreign(BikeLeaderboard.record_id)==BikeRaceRecord.id")
    track = relationship("BikeTrack", primaryjoin="foreign(BikeLeaderboard.track_id)==BikeTrack.id")
    user = relationship("User", primaryjoin="foreign(BikeLeaderboard.user_id)==User.id")

class BikeCareerScore(Base):
    __tablename__ = "bike_career_scores"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    season_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    gender = Column(Enum(Gender), nullable=False)
    user_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    score = Column(Integer, default=0, nullable=False)
    voucher_bonus = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), server_onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('season_id', 'user_id', name='uq_bike_career_score_season_user'),
    )

    user = relationship("User", primaryjoin="foreign(BikeCareerScore.user_id)==User.id")

class BikeCareerStatisticData(Base):
    __tablename__ = "bike_career_statistic_data"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    season_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    total_distance = Column(Float, default=0, nullable=False)   # km
    total_time = Column(Float, default=0, nullable=False)       # s

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), server_onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('season_id', 'user_id', name='uq_bike_career_statistic_season_user'),
    )

    user = relationship("User", primaryjoin="foreign(BikeCareerStatisticData.user_id)==User.id")

class RunningLeaderboard(Base):
    __tablename__ = "running_leaderboard"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    track_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    gender = Column(Enum(Gender), nullable=False)
    rank_position = Column(Integer, nullable=False)
    user_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    record_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    duration_seconds = Column(Float, nullable=False)
    reward = Column(JSONB, nullable=False)        # 暂只支持金券
    score = Column(Integer, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # 每个赛道性别组合的排名唯一
    __table_args__ = (
        UniqueConstraint('track_id', 'gender', 'rank_position', name='uq_running_leaderboard_track_gender_rank'),
    )
    # 每个赛道的用户记录唯一
    __table_args__ = (
        UniqueConstraint('track_id', 'user_id', name='uq_running_leaderboard_track_user'),
    )
    # ORM 关系
    record = relationship("RunningRaceRecord",primaryjoin="foreign(RunningLeaderboard.record_id)==RunningRaceRecord.id")
    track = relationship("RunningTrack", primaryjoin="foreign(RunningLeaderboard.track_id)==RunningTrack.id")
    user = relationship("User", primaryjoin="foreign(RunningLeaderboard.user_id)==User.id")

class RunningCareerScore(Base):
    __tablename__ = "running_career_scores"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    season_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    gender = Column(Enum(Gender), nullable=False)
    user_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    score = Column(Integer, default=0, nullable=False)
    voucher_bonus = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), server_onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('season_id', 'user_id', name='uq_running_career_score_season_user'),
    )

    user = relationship("User", primaryjoin="foreign(RunningCareerScore.user_id)==User.id")

class RunningCareerStatisticData(Base):
    __tablename__ = "running_career_statistic_data"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    season_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    total_distance = Column(Float, default=0, nullable=False)
    total_time = Column(Float, default=0, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), server_onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('season_id', 'user_id', name='uq_running_career_statistic_season_user'),
    )

    user = relationship("User", primaryjoin="foreign(RunningCareerStatisticData.user_id)==User.id")