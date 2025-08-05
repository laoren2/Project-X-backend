from app.crud.competition.common import (
    get_region_by_name, create_region_crud, get_regions_by_country_code
)
import app.crud.competition.bike as bike
import app.crud.competition.running as running
from app.core.errors import ErrorCode
from app.schemas.base import BizException
from app.schemas.user import Gender
from app.schemas.competition.common import (
    SportType, RegionCreate
)
from app.db.models.competition import BikeSeason, Region, RunningSeason
from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import redis_client
import logging
import uuid

scheduler_logger = logging.getLogger("scheduler")


async def generate_all_leaderboard_snapshots_service(db: AsyncSession):
    bike_track_ids = await get_bike_active_track_ids(db)
    for track_id in bike_track_ids:
        for gender in [Gender.male, Gender.female]:
            try:
                snapshot_key = await generate_bike_leaderboard_snapshot(track_id, gender)
                scheduler_logger.info(f"✅ 已生成排行榜快照: {snapshot_key}")
            except Exception as e:
                scheduler_logger.error(f"❌ 生成排行榜快照失败: {track_id} - {gender.value}, 错误: {e}")
    running_track_ids = await get_running_active_track_ids(db)
    for track_id in running_track_ids:
        for gender in [Gender.male, Gender.female]:
            try:
                snapshot_key = await generate_running_leaderboard_snapshot(track_id, gender)
                scheduler_logger.info(f"✅ 已生成排行榜快照: {snapshot_key}")
            except Exception as e:
                scheduler_logger.error(f"❌ 生成排行榜快照失败: {track_id} - {gender.value}, 错误: {e}")


async def get_bike_active_track_ids(db: AsyncSession) -> List[str]:
    bike_seasons = await bike.get_season_now(db)
    if not bike_seasons:
        scheduler_logger.info("✅ 当前没有进行中的bike赛季")
        return []
    if len(bike_seasons) > 1:
        scheduler_logger.info("❌ 当前时间存在多个进行中的bike赛季")
        return []
    bike_season: BikeSeason = bike_seasons[0]
    events = await bike.get_active_events_by_season_id(db, bike_season.id)
    track_ids = []
    for event in events:
        for track in event.tracks:
            if track.start_date < datetime.now(timezone.utc) and track.end_date > datetime.now(timezone.utc):
                track_ids.append(track.track_id)
    return track_ids


async def get_running_active_track_ids(db: AsyncSession) -> List[str]:
    running_seasons = await running.get_season_now(db)
    if not running_seasons:
        scheduler_logger.info("✅ 当前没有进行中的running赛季")
        return []
    if len(running_seasons) > 1:
        scheduler_logger.info("❌ 当前时间存在多个进行中的running赛季")
        return []
    running_season: RunningSeason = running_seasons[0]
    events = await running.get_active_events_by_season_id(db, running_season.id)
    track_ids = []
    for event in events:
        for track in event.tracks:
            if track.start_date < datetime.now(timezone.utc) and track.end_date > datetime.now(timezone.utc):
                track_ids.append(track.track_id)
    return track_ids


# 生成排行榜快照
async def generate_bike_leaderboard_snapshot(track_id: str, gender: Gender) -> str:
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y%m%d%H%M")
    src_key = f"leaderboard:bike:{track_id}:{gender.value}"
    snapshot_key = f"{src_key}:snapshot:{timestamp}"
    # 复制当前排行榜快照
    await redis_client.zunionstore(snapshot_key, [src_key])
    # 设置快照自动过期时间为 5 分钟
    await redis_client.expire(snapshot_key, 300)
    return snapshot_key


async def generate_running_leaderboard_snapshot(track_id: str, gender: Gender) -> str:
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y%m%d%H%M")
    src_key = f"leaderboard:running:{track_id}:{gender.value}"
    snapshot_key = f"{src_key}:snapshot:{timestamp}"
    # 复制当前排行榜快照
    await redis_client.zunionstore(snapshot_key, [src_key])
    # 设置快照自动过期时间为 5 分钟
    await redis_client.expire(snapshot_key, 300)
    return snapshot_key


async def create_region_service(db: AsyncSession, region_create: RegionCreate):
    region = await get_region_by_name(db, region_create.name)
    if region is not None:
        raise BizException(code=ErrorCode.REGION_ALREADY_EXIST, message="地理区域已存在，不可重复创建")
    new_region = Region(
        name=region_create.name
    )
    await create_region_crud(db, new_region)
    await db.commit()


async def query_regions_with_events(db: AsyncSession, sport_type: str, country_code: str) -> List[str]:
    regions = await get_regions_by_country_code(db, country_code)
    if not regions:
        raise BizException(code=ErrorCode.REGION_NOT_FOUND, message="该国家地区暂无赛事")
    result = []
    now = datetime.now(timezone.utc)
    for region in regions:
        if sport_type == "bike":
            for event in region.bike_events:
                if event.start_date <= now <= event.end_date:
                    result.append(region.name)
                    break
        elif sport_type == "running":
            for event in region.running_events:
                if event.start_date <= now <= event.end_date:
                    result.append(region.name)
                    break
    return result