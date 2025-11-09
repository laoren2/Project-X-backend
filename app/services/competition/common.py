from app.crud.competition.common import (
    get_region_by_name, create_region_crud, get_regions_by_country_code
)
import app.crud.competition.bike as bike
import app.crud.competition.running as running
from app.core.errors import ErrorCode
from app.schemas.base import BizException
from app.schemas.user import Gender
from app.schemas.competition.common import RegionCreate, RecordStatus, TeamStatus, LocationPoint
from app.schemas.common import SportType
from app.db.models.competition import BikeSeason, Region, RunningSeason
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import redis_client
from sqlalchemy import select
from app.db.models.competition import (
    BikeRaceRecord, RunningRaceRecord,
    BikeTrack, RunningTrack, BikeTeam, RunningTeam
)
from math import radians, sin, cos, sqrt, atan2
import logging, json

scheduler_logger = logging.getLogger("scheduler")


async def clean_expired_records_service(db: AsyncSession):
    """
    规则:
    - 单人未开始(notStarted 且 team_id 为空): 赛道已过期(track.end_date < now) -> completed
    - 组队未开始(notStarted 且 team_id 非空): 队伍状态为 completed -> completed
    - 进行中(recording): 开始超过2小时 -> completed (补全end_time/duration_seconds)
    """
    now = datetime.now(timezone.utc)
    timeout_threshold = now - timedelta(hours=2)
    async with db.begin():
        # 1) 单人未开始且赛道过期 -> completed
        bike_single_stmt = (
            select(BikeRaceRecord)
            .join(BikeTrack, BikeRaceRecord.track_id == BikeTrack.id)
            .where(
                BikeRaceRecord.status == RecordStatus.notStarted,
                BikeRaceRecord.team_id.is_(None),
                BikeTrack.end_date < now,
            )
        )
        running_single_stmt = (
            select(RunningRaceRecord)
            .join(RunningTrack, RunningRaceRecord.track_id == RunningTrack.id)
            .where(
                RunningRaceRecord.status == RecordStatus.notStarted,
                RunningRaceRecord.team_id.is_(None),
                RunningTrack.end_date < now,
            )
        )

        bike_single_records = (await db.execute(bike_single_stmt)).scalars().all()
        running_single_records = (await db.execute(running_single_stmt)).scalars().all()

        for r in bike_single_records:
            await bike.update_record_crud(db, r, {"status": RecordStatus.expired})
        for r in running_single_records:
            await running.update_record_crud(db, r, {"status": RecordStatus.expired})

        # 2) 组队未开始且队伍完成 -> completed
        bike_team_stmt = (
            select(BikeRaceRecord)
            .join(BikeTeam, BikeRaceRecord.team_id == BikeTeam.id)
            .where(
                BikeRaceRecord.status == RecordStatus.notStarted,
                BikeRaceRecord.team_id.is_not(None),
                BikeTeam.status == TeamStatus.completed,
            )
        )
        running_team_stmt = (
            select(RunningRaceRecord)
            .join(RunningTeam, RunningRaceRecord.team_id == RunningTeam.id)
            .where(
                RunningRaceRecord.status == RecordStatus.notStarted,
                RunningRaceRecord.team_id.is_not(None),
                RunningTeam.status == TeamStatus.completed,
            )
        )

        bike_team_records = (await db.execute(bike_team_stmt)).scalars().all()
        running_team_records = (await db.execute(running_team_stmt)).scalars().all()

        for r in bike_team_records:
            await bike.update_record_crud(db, r, {"status": RecordStatus.expired})
        for r in running_team_records:
            await running.update_record_crud(db, r, {"status": RecordStatus.expired})

        # 3) 进行中且超过2小时 -> completed，并补全结束时间/成绩
        bike_recording_stmt = (
            select(BikeRaceRecord)
            .where(
                BikeRaceRecord.status == RecordStatus.recording,
                BikeRaceRecord.start_time.is_not(None),
                BikeRaceRecord.start_time < timeout_threshold,
            )
        )
        running_recording_stmt = (
            select(RunningRaceRecord)
            .where(
                RunningRaceRecord.status == RecordStatus.recording,
                RunningRaceRecord.start_time.is_not(None),
                RunningRaceRecord.start_time < timeout_threshold,
            )
        )

        bike_recording_records = (await db.execute(bike_recording_stmt)).scalars().all()
        running_recording_records = (await db.execute(running_recording_stmt)).scalars().all()

        for r in bike_recording_records:
            end_time = r.start_time + timedelta(hours=2)
            await bike.update_record_crud(db, r, {
                "status": RecordStatus.expired,
                "end_time": end_time,
                "duration_seconds": 2 * 60 * 60,
            })
        for r in running_recording_records:
            end_time = r.start_time + timedelta(hours=2)
            await running.update_record_crud(db, r, {
                "status": RecordStatus.expired,
                "end_time": end_time,
                "duration_seconds": 2 * 60 * 60,
            })
        scheduler_logger.info(f"比赛记录清理完成")

async def clean_expired_teams_service(db: AsyncSession):
    now = datetime.now(timezone.utc)
    two_hours = timedelta(hours=2)
    async with db.begin():
        # 1) prepared/locked 且赛道已结束 -> completed
        bike_prepared_locked_stmt = (
            select(BikeTeam)
            .join(BikeTrack, BikeTeam.track_id == BikeTrack.id)
            .where(
                BikeTeam.status.in_([TeamStatus.prepared, TeamStatus.locked]),
                BikeTrack.end_date < now,
            )
        )
        running_prepared_locked_stmt = (
            select(RunningTeam)
            .join(RunningTrack, RunningTeam.track_id == RunningTrack.id)
            .where(
                RunningTeam.status.in_([TeamStatus.prepared, TeamStatus.locked]),
                RunningTrack.end_date < now,
            )
        )

        bike_prepared_locked = (await db.execute(bike_prepared_locked_stmt)).scalars().all()
        running_prepared_locked = (await db.execute(running_prepared_locked_stmt)).scalars().all()

        for team in bike_prepared_locked:
            await bike.update_team_crud(db, team, {"status": TeamStatus.completed})
        for team in running_prepared_locked:
            await running.update_team_crud(db, team, {"status": TeamStatus.completed})

        # 2) ready 且 start_date 已超过 2 小时仍未开始 -> completed
        bike_ready_stmt = (
            select(BikeTeam)
            .where(
                BikeTeam.status == TeamStatus.ready,
                BikeTeam.start_date + two_hours < now,
            )
        )
        running_ready_stmt = (
            select(RunningTeam)
            .where(
                RunningTeam.status == TeamStatus.ready,
                RunningTeam.start_date + two_hours < now,
            )
        )

        bike_ready = (await db.execute(bike_ready_stmt)).scalars().all()
        running_ready = (await db.execute(running_ready_stmt)).scalars().all()

        for team in bike_ready:
            await bike.update_team_crud(db, team, {"status": TeamStatus.completed})
        for team in running_ready:
            await running.update_team_crud(db, team, {"status": TeamStatus.completed})

        # 3) recording 且 start_date_real 已超过 2 小时 -> completed
        bike_recording_stmt = (
            select(BikeTeam)
            .where(
                BikeTeam.status == TeamStatus.recording,
                BikeTeam.start_date_real.is_not(None),
                BikeTeam.start_date_real + two_hours < now,
            )
        )
        running_recording_stmt = (
            select(RunningTeam)
            .where(
                RunningTeam.status == TeamStatus.recording,
                RunningTeam.start_date_real.is_not(None),
                RunningTeam.start_date_real + two_hours < now,
            )
        )

        bike_recording = (await db.execute(bike_recording_stmt)).scalars().all()
        running_recording = (await db.execute(running_recording_stmt)).scalars().all()

        for team in bike_recording:
            await bike.update_team_crud(db, team, {"status": TeamStatus.completed})
        for team in running_recording:
            await running.update_team_crud(db, team, {"status": TeamStatus.completed})
        
        scheduler_logger.info("比赛队伍清理完成")

async def generate_all_leaderboard_snapshots_service(db: AsyncSession):
    bike_track_ids = await get_bike_active_track_ids(db)
    for track_id in bike_track_ids:
        try:
            snapshot_key = await generate_bike_leaderboard_snapshot(db, track_id)
            scheduler_logger.info(f"✅ 已生成排行榜快照: {snapshot_key}")
        except Exception as e:
            scheduler_logger.error(f"❌ 生成排行榜快照失败: {track_id} , 错误: {e}")
    running_track_ids = await get_running_active_track_ids(db)
    for track_id in running_track_ids:
        try:
            snapshot_key = await generate_running_leaderboard_snapshot(db, track_id)
            scheduler_logger.info(f"✅ 已生成排行榜快照: {snapshot_key}")
        except Exception as e:
            scheduler_logger.error(f"❌ 生成排行榜快照失败: {track_id} , 错误: {e}")

def _distribute_voucher_and_scores(
    prize_pool: int,
    base_score: int,
    entries: List[tuple[str, str, float]],  # (user_id, record_id, duration)
    alpha_rank: float = 0.6,
    alpha_perf: float = 0.4
) -> List[tuple[str, str, float, int, int, int]]:
    """
    计算 完整排行榜的选手奖励和积分
    返回: (user_id, record_id, duration, voucher, score, rank)
    """
    if not entries:
        return []
    leaderboard_len = len(entries)

    durations = [d for (_, _, d) in entries]
    best = min(durations)

    # 名次权重
    rank_weights = [1.0 / (i + 1) for i in range(leaderboard_len)]
    rank_sum = sum(rank_weights)
    rank_norm = [w / rank_sum for w in rank_weights]

    # 成绩权重
    perf_raw = [(best / d) if d > 0 else 0.0 for d in durations]
    perf_sum = sum(perf_raw) or 1.0
    perf_norm = [w / perf_sum for w in perf_raw]

    # 综合权重
    weights = [alpha_rank * r + alpha_perf * p for r, p in zip(rank_norm, perf_norm)]
    total_w = sum(weights) or 1.0

    # 分配奖金（向下取整，保证不超额，暂忽略剩余零头）
    vouchers = [int(prize_pool * (w / total_w)) for w in weights]

    # 分配积分（保底+平滑衰减）
    min_score = max(int(base_score / leaderboard_len), 1)
    scores = []
    if leaderboard_len == 1:
        scores = [base_score]
    else:
        for i in range(leaderboard_len):
            score = base_score - i * (base_score - min_score) / (leaderboard_len - 1)
            scores.append(int(round(score)))

    # 组装结果
    settled = []
    for i, (user_id, record_id, duration) in enumerate(entries):
        settled.append((user_id, record_id, duration, vouchers[i], scores[i], 1 + i))
    return settled

async def get_bike_active_track_ids(db: AsyncSession) -> List[str]:
    bike_seasons = await bike.get_season_now(db)
    if not bike_seasons:
        scheduler_logger.info("❌ 当前没有进行中的bike赛季")
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
        scheduler_logger.info("❌ 当前没有进行中的running赛季")
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
async def generate_bike_leaderboard_snapshot(db: AsyncSession, track_id: str) -> str:
    track = await bike.get_track_by_track_id(db, track_id)
    if not track:
        raise BizException(code=ErrorCode.TRACK_NOT_FOUND, message="赛道不存在")
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y%m%d%H%M")
    male_src_key = f"leaderboard:bike:{track_id}:male"
    female_src_key = f"leaderboard:bike:{track_id}:female"
    male_snapshot_key = f"{male_src_key}:snapshot:{timestamp}"
    female_snapshot_key = f"{female_src_key}:snapshot:{timestamp}"

    # 复制当前排行榜
    await redis_client.zunionstore(male_snapshot_key, [male_src_key])
    await redis_client.expire(male_snapshot_key, 300)
    await redis_client.zunionstore(female_snapshot_key, [female_src_key])
    await redis_client.expire(female_snapshot_key, 300)

    # 拉取完整排行榜数据
    male_leaderboard_data = await redis_client.zrange(male_snapshot_key, 0, -1, withscores=True)
    female_leaderboard_data = await redis_client.zrange(female_snapshot_key, 0, -1, withscores=True)

    # 构造 entries: List[tuple[user_id, record_id, duration]]
    male_entries, female_entries = [], []
    if male_leaderboard_data:
        for member, duration_seconds in male_leaderboard_data:
            if ":" in member:
                user_id, record_id = member.split(":", 1)
            else:
                user_id, record_id = member, "None"
            male_entries.append((user_id, record_id, float(duration_seconds)))
    if female_leaderboard_data:
        for member, duration_seconds in female_leaderboard_data:
            if ":" in member:
                user_id, record_id = member.split(":", 1)
            else:
                user_id, record_id = member, "None"
            female_entries.append((user_id, record_id, float(duration_seconds)))
    
    # 获取总参与人数和奖池
    total_participants = len(male_entries) + len(female_entries)
    if total_participants == 0:
        return f"leaderboard:bike:{track_id} with no data"
    male_pool = int(track.prize_pool * (len(male_entries) / total_participants))
    female_pool = track.prize_pool - male_pool

    # 计算奖励和积分
    male_completed_data = _distribute_voucher_and_scores(
        prize_pool=male_pool,
        base_score=track.score,
        entries=male_entries
    )
    female_completed_data = _distribute_voucher_and_scores(
        prize_pool=female_pool,
        base_score=track.score,
        entries=female_entries
    )

    # 存储奖励信息到 hash
    male_rewards_hash_key = f"{male_snapshot_key}:rewards"
    female_rewards_hash_key = f"{female_snapshot_key}:rewards"

    async with redis_client.pipeline() as pipe:
        for user_id, record_id, _, voucher, score, rank in male_completed_data:
            member_key = f"{user_id}:{record_id}"
            value = {"voucher": voucher, "score": score, "rank": rank}
            await pipe.hset(male_rewards_hash_key, member_key, json.dumps(value))

        for user_id, record_id, _, voucher, score, rank in female_completed_data:
            member_key = f"{user_id}:{record_id}"
            value = {"voucher": voucher, "score": score, "rank": rank}
            await pipe.hset(female_rewards_hash_key, member_key, json.dumps(value))
        # 设置过期时间也放进 pipeline
        await pipe.expire(male_rewards_hash_key, 360)
        await pipe.expire(female_rewards_hash_key, 360)
        await pipe.execute()

    return f"leaderboard:bike:{track_id}"

async def generate_running_leaderboard_snapshot(db: AsyncSession, track_id: str) -> str:
    track = await running.get_track_by_track_id(db, track_id)
    if not track:
        raise BizException(code=ErrorCode.TRACK_NOT_FOUND, message="赛道不存在")
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y%m%d%H%M")
    male_src_key = f"leaderboard:running:{track_id}:male"
    female_src_key = f"leaderboard:running:{track_id}:female"
    male_snapshot_key = f"{male_src_key}:snapshot:{timestamp}"
    female_snapshot_key = f"{female_src_key}:snapshot:{timestamp}"

    # 复制当前排行榜
    await redis_client.zunionstore(male_snapshot_key, [male_src_key])
    await redis_client.expire(male_snapshot_key, 300)
    await redis_client.zunionstore(female_snapshot_key, [female_src_key])
    await redis_client.expire(female_snapshot_key, 300)

    # 拉取完整排行榜数据
    male_leaderboard_data = await redis_client.zrange(male_snapshot_key, 0, -1, withscores=True)
    female_leaderboard_data = await redis_client.zrange(female_snapshot_key, 0, -1, withscores=True)

    # 构造 entries: List[tuple[user_id, record_id, duration]]
    male_entries, female_entries = [], []
    if male_leaderboard_data:
        for member, duration_seconds in male_leaderboard_data:
            if ":" in member:
                user_id, record_id = member.split(":", 1)
            else:
                user_id, record_id = member, "None"
            male_entries.append((user_id, record_id, float(duration_seconds)))
    if female_leaderboard_data:
        for member, duration_seconds in female_leaderboard_data:
            if ":" in member:
                user_id, record_id = member.split(":", 1)
            else:
                user_id, record_id = member, "None"
            female_entries.append((user_id, record_id, float(duration_seconds)))
    
    # 获取总参与人数和奖池
    total_participants = len(male_entries) + len(female_entries)
    if total_participants == 0:
        return f"leaderboard:running:{track_id} with no data"
    male_pool = int(track.prize_pool * (len(male_entries) / total_participants))
    female_pool = track.prize_pool - male_pool

    # 计算奖励和积分
    male_completed_data = _distribute_voucher_and_scores(
        prize_pool=male_pool,
        base_score=track.score,
        entries=male_entries
    )
    female_completed_data = _distribute_voucher_and_scores(
        prize_pool=female_pool,
        base_score=track.score,
        entries=female_entries
    )

    # 存储奖励信息到 hash
    male_rewards_hash_key = f"{male_snapshot_key}:rewards"
    female_rewards_hash_key = f"{female_snapshot_key}:rewards"

    async with redis_client.pipeline() as pipe:
        for user_id, record_id, _, voucher, score, rank in male_completed_data:
            member_key = f"{user_id}:{record_id}"
            value = {"voucher": voucher, "score": score, "rank": rank}
            await pipe.hset(male_rewards_hash_key, member_key, json.dumps(value))

        for user_id, record_id, _, voucher, score, rank in female_completed_data:
            member_key = f"{user_id}:{record_id}"
            value = {"voucher": voucher, "score": score, "rank": rank}
            await pipe.hset(female_rewards_hash_key, member_key, json.dumps(value))
        # 设置过期时间也放进 pipeline
        await pipe.expire(male_rewards_hash_key, 360)
        await pipe.expire(female_rewards_hash_key, 360)
        await pipe.execute()

    return f"leaderboard:running:{track_id}"


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

def compute_distance(path: List[LocationPoint]) -> float:
    """
    使用 Haversine 公式计算相邻点之间的球面距离，总和以公里返回
    参数:
        path: 包含 lat 和 lon 属性的路径点列表（可以是 BikePathPoint、RunningPathPoint 或任何实现了 LocationPoint Protocol 的对象）
    返回:
        总距离（公里）
    """
    if not path or len(path) < 2:
        return 0.0
    R_km = 6371.0
    total_km = 0.0
    prev = path[0]
    for curr in path[1:]:
        lat1 = radians(prev.lat)
        lon1 = radians(prev.lon)
        lat2 = radians(curr.lat)
        lon2 = radians(curr.lon)
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        total_km += R_km * c
        prev = curr
    return float(total_km)