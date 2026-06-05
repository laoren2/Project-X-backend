from app.crud.competition.common import (
    create_region_crud, get_regions_by_country_code,
    get_region_by_coordinate
)
from app.crud.asset_manage import reward_ccasset
import app.crud.competition.bike as bike
import app.crud.competition.running as running
import app.schemas.competition.bike as bike_schema
import app.schemas.competition.running as running_schema
from app.core.errors import ErrorCode
from app.core.tools import get_user_local_date
from app.db.models.user import User
from app.db.models.mailbox import Mailbox
from app.schemas.base import BizException, Language, pick_i18n_text
from app.schemas.user import Gender
from app.schemas.competition.common import RegionCreate, RecordStatus, TeamStatus, LocationPoint, RegionResponse, MatchFinishInfo
from app.schemas.asset import CCAssetType, AssetOperation
from app.schemas.common import CCAssetRewardResponse, CCAssetBaseInfo
from app.schemas.mailbox import MailType
from typing import List
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import redis_client
from sqlalchemy import select
from app.db.models.competition import (
    BikeRaceRecord, RunningRaceRecord, BikeEvent, RunningEvent,
    BikeTrack, RunningTrack, BikeTeam, RunningTeam, Region,
    BikeSeason, RunningSeason
)
from app.core.tools import format_time_duration
from math import radians, sin, cos, sqrt, atan2
from sqlalchemy.orm import selectinload
from app.schemas.training.common import RouteType
from geoalchemy2.shape import from_shape
from shapely.geometry import Point, LineString
import logging, json, random, uuid

scheduler_logger = logging.getLogger("scheduler")
leaderboard_logger = logging.getLogger("leaderboard")

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
            .options(selectinload(BikeRaceRecord.user))
        )
        running_recording_stmt = (
            select(RunningRaceRecord)
            .where(
                RunningRaceRecord.status == RecordStatus.recording,
                RunningRaceRecord.start_time.is_not(None),
                RunningRaceRecord.start_time < timeout_threshold,
            )
            .options(selectinload(RunningRaceRecord.user))
        )

        bike_recording_records = (await db.execute(bike_recording_stmt)).scalars().all()
        running_recording_records = (await db.execute(running_recording_stmt)).scalars().all()

        for r in bike_recording_records:
            end_time = r.start_time + timedelta(hours=2)
            await bike.update_record_crud(db, r, {
                "status": RecordStatus.expired,
                "end_time": end_time,
                "duration_seconds": 2 * 60 * 60,
                "local_date": get_user_local_date(r.user, end_time)
            })
            # 处理队伍里使用组队 magiccard 的记录
            if r.team_id:
                bike_team_bonus_record = await bike.get_bonus_record_with_team_magic_card_by_team_user(db, r.team_id, r.user_id)
                if bike_team_bonus_record:
                    bike_team_bonus_record.is_applied = True

        for r in running_recording_records:
            end_time = r.start_time + timedelta(hours=2)
            await running.update_record_crud(db, r, {
                "status": RecordStatus.expired,
                "end_time": end_time,
                "duration_seconds": 2 * 60 * 60,
                "local_date": get_user_local_date(r.user, end_time)
            })
            if r.team_id:
                running_team_bonus_record = await running.get_bonus_record_with_team_magic_card_by_team_user(db, r.team_id, r.user_id)
                if running_team_bonus_record:
                    running_team_bonus_record.is_applied = True
        
        # 4) 组队记录中已完成但有效成绩尚未计算完成，重新校验进行结算
        bike_wait_for_computed_stmt = (
            select(BikeRaceRecord)
            .where(
                BikeRaceRecord.status == RecordStatus.completed,
                BikeRaceRecord.is_finish_bonus_computing == False,
                BikeRaceRecord.team_id.is_not(None)
            )
            .options(
                selectinload(BikeRaceRecord.user),
                selectinload(BikeRaceRecord.track)
                    .selectinload(BikeTrack.event)
                    .selectinload(BikeEvent.season),
                selectinload(BikeRaceRecord.path)
            )
        )
        running_wait_for_computed_stmt = (
            select(RunningRaceRecord)
            .where(
                RunningRaceRecord.status == RecordStatus.completed,
                RunningRaceRecord.is_finish_bonus_computing == False,
                RunningRaceRecord.team_id.is_not(None)
            )
            .options(
                selectinload(RunningRaceRecord.user),
                selectinload(RunningRaceRecord.track)
                    .selectinload(RunningTrack.event)
                    .selectinload(RunningEvent.season),
                selectinload(RunningRaceRecord.path)
            )
        )
        bike_recording_records = (await db.execute(bike_wait_for_computed_stmt)).scalars().all()
        running_recording_records = (await db.execute(running_wait_for_computed_stmt)).scalars().all()

        for r in bike_recording_records:
            await handle_not_finish_computed_bike_records(db, r)
        for r in running_recording_records:
            await handle_not_finish_computed_running_records(db, r)

        scheduler_logger.info(f"✅ 比赛记录清理完成")


async def handle_not_finish_computed_bike_records(db: AsyncSession, record: BikeRaceRecord):
    # 处理is_finished_computed & 结算
    bonus_records = await bike.get_bonus_record_with_team_magic_card_by_team_id(db, record.team_id)
    need_to_handle = True
    for br in bonus_records:
        if not br.is_applied:
            need_to_handle = False
            break
    if need_to_handle:
        record.is_finish_bonus_computing = True
        await send_bike_match_rewards(db, record)
        await update_bike_leaderboard_for_record(record)
        if record.user and record.track and record.track.event and record.track.event.season and record.path and record.path.path:
            points = [bike_schema.BikePathPoint.model_validate(p) for p in record.path.path]
            distance = compute_distance([p.base for p in points])
            await bike.add_or_update_career_statistic_data(db, record.track.event.season.id, record.user.id, distance, record.duration_seconds)
            await bike.add_or_update_daily_task_record(db, record.user, distance, record.duration_seconds)

async def handle_not_finish_computed_running_records(db: AsyncSession, record: RunningRaceRecord):
    # 处理is_finished_computed & 结算
    bonus_records = await running.get_bonus_record_with_team_magic_card_by_team_id(db, record.team_id)
    need_to_handle = True
    for br in bonus_records:
        if not br.is_applied:
            need_to_handle = False
            break
    if need_to_handle:
        record.is_finish_bonus_computing = True
        await send_running_match_rewards(db, record)
        await update_running_leaderboard_for_record(record)
        if record.user and record.track and record.track.event and record.track.event.season and record.path and record.path.path:
            points = [running_schema.RunningPathPoint.model_validate(p) for p in record.path.path]
            distance = compute_distance([p.base for p in points])
            await running.add_or_update_career_statistic_data(db, record.track.event.season.id, record.user.id, distance, record.duration_seconds)
            await running.add_or_update_daily_task_record(db, record.user, distance, record.duration_seconds)


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
        
        scheduler_logger.info("✅ 比赛队伍清理完成")

async def generate_all_leaderboard_snapshots_service(db: AsyncSession):
    bike_track_ids = await get_bike_active_track_ids(db)
    for track_id in bike_track_ids:
        try:
            snapshot_key = await generate_bike_leaderboard_snapshot(db, track_id)
            scheduler_logger.info(f"✅ 已生成排行榜快照: {snapshot_key}")
        except Exception:
            scheduler_logger.exception(f"❌ 生成排行榜快照失败: {track_id}")
    running_track_ids = await get_running_active_track_ids(db)
    for track_id in running_track_ids:
        try:
            snapshot_key = await generate_running_leaderboard_snapshot(db, track_id)
            scheduler_logger.info(f"✅ 已生成排行榜快照: {snapshot_key}")
        except Exception:
            scheduler_logger.exception(f"❌ 生成排行榜快照失败: {track_id}")

def calculate_points(rank: int, total_players: int, total_score: int) -> int:
    """
    根据排名百分比发放阶梯式积分
    :param rank: 名次
    :param total_players: 参赛总人数
    :param total_score: 参积分
    """
    if total_players <= 0 or rank <= 0 or rank > total_players:
        return 0

    percentile = rank / total_players  # 排名百分比（越小越强）

    tiers = [
        (0.01, total_score),  # 前1%
        (0.02, total_score * 0.8),   # 前2%
        (0.03, total_score * 0.7),
        (0.05, total_score * 0.6),
        (0.10, total_score * 0.5),
        (0.20, total_score * 0.4),
        (0.40, total_score * 0.3),
        (0.60, total_score * 0.2),
        (0.80, total_score * 0.1),
        (1.00, total_score * 0.05),    # 其余所有完赛者
    ]

    for threshold, points in tiers:
        if percentile <= threshold:
            return int(points)
    return 0

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

    # 组装结果
    settled = []
    for i, (user_id, record_id, duration) in enumerate(entries):
        # 阶梯式分配积分
        score = calculate_points(1 + i, leaderboard_len, base_score)
        settled.append((user_id, record_id, duration, vouchers[i], score, 1 + i))
    return settled

async def get_bike_active_track_ids(db: AsyncSession) -> List[str]:
    bike_season = await bike.get_season_now(db)
    if not bike_season:
        scheduler_logger.warning("❌ 当前没有进行中的bike赛季")
        return []
    events = await bike.get_active_events_by_season_id(db, bike_season.id)
    track_ids = []
    for event in events:
        for track in event.tracks:
            if track.start_date < datetime.now(timezone.utc) and track.end_date > datetime.now(timezone.utc):
                track_ids.append(track.track_id)
    return track_ids


async def get_running_active_track_ids(db: AsyncSession) -> List[str]:
    running_season = await running.get_season_now(db)
    if not running_season:
        scheduler_logger.warning("❌ 当前没有进行中的running赛季")
        return []
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
        raise BizException(code=ErrorCode.TRACK_ERROR, message="赛道不存在")
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
        raise BizException(code=ErrorCode.TRACK_ERROR, message="赛道不存在")
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


async def query_regions_with_events_service(db: AsyncSession, sport_type: str, country_code: str) -> List[str]:
    regions = await get_regions_by_country_code(db, country_code)
    if not regions:
        raise BizException(code=ErrorCode.REGION_ERROR, message="region.no_events")
    result = []
    now = datetime.now(timezone.utc)
    for region in regions:
        if sport_type == "bike":
            for event in region.bike_events:
                if event.start_date <= now <= event.end_date:
                    result.append(region.region_id)
                    break
        elif sport_type == "running":
            for event in region.running_events:
                if event.start_date <= now <= event.end_date:
                    result.append(region.region_id)
                    break
    return result


async def query_region_with_coordinate_service(db: AsyncSession, user_id: str | None, lat: float, lon: float) -> RegionResponse:
    if user_id == "176987647574535":
        # 审核账号更新测试赛道信息
        track = await running.get_track_by_track_id(db, "track_8b576bc44ff0")
        if track:
            # 用审核员当前位置就地生成一条 2 点测试赛道
            end_lat, end_lng = lat + 0.001, lon + 0.001
            track.route_type = RouteType.pointToPoint
            track.route_data = {
                "type": "pointToPoint",
                "steps": [
                    {"kind": "checkpoint", "lat": lat, "lng": lon, "radius": 10},
                    {"kind": "checkpoint", "lat": end_lat, "lng": end_lng, "radius": 10},
                ]
            }
            track.route_geometry = from_shape(LineString([(lon, lat), (end_lng, end_lat)]), srid=4326)
            track.start_point = from_shape(Point(lon, lat), srid=4326)
            track.end_point = from_shape(Point(end_lng, end_lat), srid=4326)
            await db.commit()
    region = await get_region_by_coordinate(db, lat, lon)
    result = RegionResponse(
        region_id=region.region_id if region else None,
        country_code=region.country_code if region else None
    )
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

# 插入新记录更新 running 排行榜 ( record 的 user 和 track 需提前 selectinload )
async def update_running_leaderboard_for_record(record: RunningRaceRecord):
    try:
        if record.status != RecordStatus.completed or record.duration_seconds is None:
            return
        if record.track is None:
            return
        gender = record.user.gender if record.user.gender else Gender.male
        key = f"leaderboard:running:{record.track.track_id}:{gender.value}"
        # 1. 查找旧成绩
        best_score = None
        best_member = None
        members = await redis_client.zrange(key, 0, -1, withscores=True)
        for m, score in members:
            if m.startswith(f"{record.user.user_id}:"):
                best_score = score
                best_member = m
                break  # 只会有一条
        # 2. 比较成绩
        if best_score is None or record.duration_seconds < best_score:
            if best_member:
                await redis_client.zrem(key, best_member)
            member = f"{record.user.user_id}:{record.record_id}"
            await redis_client.zadd(key, {member: record.duration_seconds})
    except Exception:
        # todo: 记录错误日志，后续由定时任务补偿
        leaderboard_logger.exception(f"Failed to update leaderboard {key} for record {record.record_id}")
        raise

# 插入新记录更新排行榜
async def update_bike_leaderboard_for_record(record: BikeRaceRecord):
    try:
        if record.status != RecordStatus.completed or record.duration_seconds is None:
            return
        if record.track is None:
            return
        gender = record.user.gender if record.user.gender else Gender.male
        key = f"leaderboard:bike:{record.track.track_id}:{gender.value}"
        # 1. 查找旧成绩
        best_score = None
        best_member = None
        members = await redis_client.zrange(key, 0, -1, withscores=True)
        for m, score in members:
            if m.startswith(f"{record.user.user_id}:"):
                best_score = score
                best_member = m
                break  # 只会有一条
        # 2. 比较成绩
        if best_score is None or record.duration_seconds < best_score:
            if best_member:
                await redis_client.zrem(key, best_member)
            member = f"{record.user.user_id}:{record.record_id}"
            await redis_client.zadd(key, {member: record.duration_seconds})
    except Exception:
        # todo: 记录错误日志，后续由定时任务补偿
        leaderboard_logger.exception(f"Failed to update leaderboard {key} for record {record.record_id}")
        raise


async def query_pb_and_tb_in_bike_track(record: BikeRaceRecord) -> tuple[float | None, float | None]:
    user = record.user
    gender = user.gender if user.gender else Gender.male
    leaderboard_key = f"leaderboard:bike:{record.track.track_id}:{gender.value}"
    members = await redis_client.zrange(leaderboard_key, 0, -1, withscores=True)
    # 查询用户的最佳成绩
    user_best_time = None
    for member, score in members:
        if member.startswith(f"{user.user_id}:"):
            user_best_time = score
    # 查询赛道最佳成绩
    track_best_time = None
    if members:
        _, track_best_time = members[0]
    return user_best_time, track_best_time

# 结算单场比赛完成后的 XP
async def settle_bike_match_xp(db: AsyncSession, record: BikeRaceRecord) -> tuple[int, int]:
    if record.duration_seconds is None:
        return 0
    user = record.user
    track = record.track
    gender = user.gender if user.gender else Gender.male
    season_data = await bike.get_score_by_season_and_user(db, user.id, track.event.season_id)
    current_xp = season_data.xp if season_data else 0

    user_best_time, track_best_time = await query_pb_and_tb_in_bike_track(record)
    # 1 基础XP
    BASE_XP = 30

    # 2 段位衰减
    tier = current_xp // 100
    rank_factor = max(0.3, 1 - tier * 0.03)

    # 3 表现奖励
    performance_factor = 1.0

    # 刷新个人记录
    if user_best_time and record.duration_seconds < user_best_time:
        performance_factor += 1.0

        improvement = (user_best_time - record.duration_seconds) / user_best_time
        improvement_bonus = min(improvement * 5, 1)

        performance_factor += improvement_bonus

    # 刷新赛道记录
    if track_best_time and record.duration_seconds < track_best_time:
        performance_factor += 1.0

    # 4 赛道信息加成
    track_factor = 1.0
    track_improvement = max(0, min(0.15, (track.distance - 5.0) / 100.0))
    track_factor += track_improvement

    # 5 最终XP
    xp = BASE_XP * rank_factor * performance_factor * track_factor
    xp = int(round(xp))
    xp = max(0, min(120, xp))

    settlements = record.settlement_rewards or {}
    settlements["xp"] = xp
    record.settlement_rewards = settlements
    await bike.add_or_update_career_xp(db, track.event.season_id, gender, user.id, xp)
    return current_xp, xp

# 计算单场比赛完成后的奖励结算信息
async def compute_bike_match_rewards(record: BikeRaceRecord) -> tuple[bool, bool, List[CCAssetBaseInfo]] | None:
    reward_result = []
    if record.duration_seconds is None:
        return None
    
    # 计算提升幅度和奖励
    base_reward_coin = 50
    improvement_bonus_coin = 0
    # 随机选择一种 STONE 类型作为奖励类型
    reward_stone_type = random.choice(
        [CCAssetType.STONE1, CCAssetType.STONE2, CCAssetType.STONE3]
    )
    reward_stone = 0

    user_best_time, track_best_time = await query_pb_and_tb_in_bike_track(record)
    is_track_best: bool = False
    is_user_best: bool = False

    if track_best_time is None:
        is_track_best = True
    elif record.duration_seconds < track_best_time:
        is_track_best = True
    else:
        is_track_best = False
        
    if user_best_time is None:
        is_user_best = True
    elif record.duration_seconds < user_best_time:
        is_user_best = True
    else:
        is_user_best = False

    if is_track_best:
        # 赛道最佳成绩：基础200金币 + 根据赛道成绩提升幅度计算的额外金币
        base_reward_coin = 200
        reward_stone = 2
        improvement_ratio = (track_best_time - record.duration_seconds) / track_best_time if track_best_time and track_best_time > 0 else 0
        improvement_bonus_coin = max(min(int(improvement_ratio * 100 * 10), 500), 0)
    elif is_user_best:
        # 用户最佳成绩：基础100金币 + 根据用户成绩提升幅度计算的额外金币
        base_reward_coin = 100
        reward_stone = 1
        improvement_ratio = (user_best_time - record.duration_seconds) / user_best_time if user_best_time and user_best_time > 0 else 0
        improvement_bonus_coin = max(min(int(improvement_ratio * 100 * 5), 250), 0)
    else:
        # 均不是：基础50金币 + 根据用户成绩提升幅度计算的额外金币
        base_reward_coin = 50
        improvement_ratio = (record.duration_seconds - user_best_time) / user_best_time if user_best_time and user_best_time > 0 else 0
        improvement_bonus_coin = max(min(int((0.2 - improvement_ratio) * 100 * 3), 60), 0)

    settlements = record.settlement_rewards or {}
    settlements["coin"] = base_reward_coin + improvement_bonus_coin

    coin_reward = CCAssetBaseInfo(
        ccasset_type=CCAssetType.COIN,
        new_ccamount=base_reward_coin + improvement_bonus_coin
    )
    reward_result.append(coin_reward)
    if reward_stone > 0:
        settlements[reward_stone_type.value] = reward_stone
        stone_reward = CCAssetBaseInfo(
            ccasset_type=reward_stone_type,
            new_ccamount=reward_stone
        )
        reward_result.append(stone_reward)
    record.settlement_rewards = settlements
    return is_user_best, is_track_best, reward_result

async def query_pb_and_tb_in_running_track(record: RunningRaceRecord) -> tuple[float | None, float | None]:
    user = record.user
    gender = user.gender if user.gender else Gender.male
    leaderboard_key = f"leaderboard:running:{record.track.track_id}:{gender.value}"
    members = await redis_client.zrange(leaderboard_key, 0, -1, withscores=True)
    # 查询用户的最佳成绩
    user_best_time = None
    for member, score in members:
        if member.startswith(f"{user.user_id}:"):
            user_best_time = score
    # 查询赛道最佳成绩
    track_best_time = None
    if members:
        _, track_best_time = members[0]
    return user_best_time, track_best_time

async def settle_running_match_xp(db: AsyncSession, record: RunningRaceRecord) -> tuple[int, int]:
    if record.duration_seconds is None:
        return 0
    user = record.user
    track = record.track
    gender = user.gender if user.gender else Gender.male
    season_data = await running.get_score_by_season_and_user(db, user.id, track.event.season_id)
    current_xp = season_data.xp if season_data else 0

    user_best_time, track_best_time = await query_pb_and_tb_in_running_track(record)
    # 1 基础XP
    BASE_XP = 30

    # 2 段位衰减
    tier = current_xp // 100
    rank_factor = max(0.3, 1 - tier * 0.03)

    # 3 表现奖励
    performance_factor = 1.0

    if user_best_time and record.duration_seconds > user_best_time:
        base_decreasement = (record.duration_seconds - user_best_time) / record.duration_seconds
        base_decreasement_bonus = min(base_decreasement, 0.5)
        performance_factor -= base_decreasement_bonus

    # 刷新个人记录
    if user_best_time and record.duration_seconds < user_best_time:
        performance_factor += 1.0

        improvement = (user_best_time - record.duration_seconds) / user_best_time
        improvement_bonus = min(improvement * 5, 1)

        performance_factor += improvement_bonus

    # 刷新赛道记录
    if track_best_time and record.duration_seconds < track_best_time:
        performance_factor += 1.0

    # 4 赛道信息加成
    track_factor = 1.0
    track_improvement = max(0, min(0.15, (track.distance - 5.0) / 100.0))
    track_factor += track_improvement

    # 5 最终XP
    xp = BASE_XP * rank_factor * performance_factor * track_factor
    xp = int(round(xp))
    xp = max(0, min(120, xp))

    settlements = record.settlement_rewards or {}
    settlements["xp"] = xp
    record.settlement_rewards = settlements
    await running.add_or_update_career_xp(db, track.event.season_id, gender, user.id, xp)
    return current_xp, xp

async def compute_running_match_rewards(record: RunningRaceRecord) -> tuple[bool, bool, List[CCAssetBaseInfo]] | None:
    reward_result = []
    if record.duration_seconds is None:
        return None
    
    # 计算提升幅度和奖励
    base_reward_coin = 50
    improvement_bonus_coin = 0
    # 随机选择一种 STONE 类型作为奖励类型
    reward_stone_type = random.choice(
        [CCAssetType.STONE1, CCAssetType.STONE2, CCAssetType.STONE3]
    )
    reward_stone = 0

    user_best_time, track_best_time = await query_pb_and_tb_in_running_track(record)
    is_track_best: bool = False
    is_user_best: bool = False

    if track_best_time is None:
        is_track_best = True
    elif record.duration_seconds < track_best_time:
        is_track_best = True
    else:
        is_track_best = False
        
    if user_best_time is None:
        is_user_best = True
    elif record.duration_seconds < user_best_time:
        is_user_best = True
    else:
        is_user_best = False

    if is_track_best:
        # 赛道最佳成绩：基础200金币 + 根据赛道成绩提升幅度计算的额外金币
        base_reward_coin = 200
        reward_stone = 2
        improvement_ratio = (track_best_time - record.duration_seconds) / track_best_time if track_best_time and track_best_time > 0 else 0
        improvement_bonus_coin = max(min(int(improvement_ratio * 100 * 10), 500), 0)
    elif is_user_best:
        # 用户最佳成绩：基础100金币 + 根据用户成绩提升幅度计算的额外金币
        base_reward_coin = 100
        reward_stone = 1
        improvement_ratio = (user_best_time - record.duration_seconds) / user_best_time if user_best_time and user_best_time > 0 else 0
        improvement_bonus_coin = max(min(int(improvement_ratio * 100 * 5), 250), 0)
    else:
        # 均不是：基础50金币 + 根据用户成绩提升幅度计算的额外金币
        base_reward_coin = 50
        improvement_ratio = (record.duration_seconds - user_best_time) / user_best_time if user_best_time and user_best_time > 0 else 0
        improvement_bonus_coin = max(min(int((0.2 - improvement_ratio) * 100 * 3), 60), 0)

    settlements = record.settlement_rewards or {}
    settlements["coin"] = base_reward_coin + improvement_bonus_coin

    coin_reward = CCAssetBaseInfo(
        ccasset_type=CCAssetType.COIN,
        new_ccamount=base_reward_coin + improvement_bonus_coin
    )
    reward_result.append(coin_reward)
    if reward_stone > 0:
        settlements[reward_stone_type.value] = reward_stone
        stone_reward = CCAssetBaseInfo(
            ccasset_type=reward_stone_type,
            new_ccamount=reward_stone
        )
        reward_result.append(stone_reward)
    record.settlement_rewards = settlements
    return is_user_best, is_track_best, reward_result

async def send_running_match_rewards(db: AsyncSession, record: RunningRaceRecord):
    await settle_running_match_xp(db, record)
    reward_results = await compute_running_match_rewards(record)
    if reward_results:
        is_user_best = reward_results[0]
        is_track_best = reward_results[1]
        rewards = reward_results[2]
        attachment = {
            "description": "running赛道记录结算"
        }
        for reward in rewards:
            attachment[f"{reward.ccasset_type.value}"] = reward.new_ccamount
        content = {}
        final_duration = format_time_duration(record.duration_seconds)
        if is_track_best:
            content = {
                "en": f"Congratulations! You have just broken the {pick_i18n_text(record.track.name_i18n, Language.en)} running track record and become the new track record holder, the score is: {final_duration}. Please accept your reward!", 
                "zh-Hans": f"恭喜！你刚刚成功刷新了 {pick_i18n_text(record.track.name_i18n, Language.zh_hans)} 跑步赛道最好成绩，成为赛道记录的保持者，成绩为：{final_duration}，请收下你的奖励！",
                "zh-Hant": f"恭喜！你剛剛成功刷新了 {pick_i18n_text(record.track.name_i18n, Language.zh_hant)} 跑步賽道最佳成績，成為賽道記錄的保持者，成績為：{final_duration}，請收下你的獎勵！",
                "ko": f"축하합니다! 방금 {pick_i18n_text(record.track.name_i18n, Language.ko)} 육상 트랙에서 개인 최고 기록을 경신하여 트랙 기록 보유자가 되셨습니다. 기록은 {final_duration}입니다. 보상을 받으세요!",
                "ja": f"おめでとうございます！{pick_i18n_text(record.track.name_i18n, Language.ja)} ランニングコースの最高記録を更新し、新たなコース記録保持者となりました！タイムは {final_duration} です。報酬をお受け取りください！"
            }
        elif is_user_best:
            content = {
                "en": f"Congratulations! You have just broken your personal best in {pick_i18n_text(record.track.name_i18n, Language.en)} running track, the score is: {final_duration}, please accept your reward and keep up the good work!", 
                "zh-Hans": f"恭喜！你刚刚在 {pick_i18n_text(record.track.name_i18n, Language.zh_hans)} 跑步赛道成功刷新了自己的最好成绩，成绩为：{final_duration}，请收下你的奖励，再接再厉！",
                "zh-Hant": f"恭喜！你剛剛在 {pick_i18n_text(record.track.name_i18n, Language.zh_hant)} 跑步賽道成功刷新了自己的最佳成績，成績為：{final_duration}，請收下你的獎勵，再接再厲！",
                "ko": f"축하합니다! 방금 {pick_i18n_text(record.track.name_i18n, Language.ko)} 육상 트랙에서 개인 최고 기록을 경신하셨습니다. 기록은 {final_duration}입니다. 축하 메시지를 받으시고 앞으로도 좋은 성적을 유지하시길 바랍니다!",
                "ja": f"おめでとうございます！{pick_i18n_text(record.track.name_i18n, Language.ja)} ランニングコースで自己ベストを更新しました！タイムは {final_duration} です。報酬を受け取って、さらに上を目指しましょう！"
            }
        else:
            content = {
                "en": f"You have just finished a running race on track {pick_i18n_text(record.track.name_i18n, Language.en)}, the score is: {final_duration}. You're just a little bit away from your best score, we look forward to your next challenge!", 
                "zh-Hans": f"你刚刚完成了一场 {pick_i18n_text(record.track.name_i18n, Language.zh_hans)} 赛道的跑步比赛，成绩为：{final_duration}，距离自己的最好成绩只差一点点了，期待你的下一次挑战！",
                "zh-Hant": f"你剛剛完成了一場 {pick_i18n_text(record.track.name_i18n, Language.zh_hant)} 賽道的跑步比賽，成績為：{final_duration}，距離自己的最好成績只差一點點了，期待你的下一個挑戰！",
                "ko": f"방금 {pick_i18n_text(record.track.name_i18n, Language.ko)} 트랙에서 열린 달리기 경주를 {final_duration}의 기록으로 완주하셨습니다. 아쉽게도 개인 최고 기록에는 약간 못 미쳤지만, 다음 도전을 기대하겠습니다!",
                "ja": f"{pick_i18n_text(record.track.name_i18n, Language.ja)} ランニングコースを完走しました！タイムは {final_duration} です。自己ベストまであと少しです。次回のチャレンジを楽しみにしています！"
            }
        mail = Mailbox(
            mail_id=f"mail_{uuid.uuid4()}",
            user_id=record.user_id,
            mail_type=MailType.REWARD,
            title_i18n={"en": "Successfully completed match", "zh-Hans": "成功完成比赛", "zh-Hant": "成功完成比賽", "ko": "대회가 성공적으로 마무리되었습니다", "ja": "レース完了"},
            content_i18n=content,
            attachment = attachment,
            is_received = False,
            expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        )
        db.add(mail)

async def send_bike_match_rewards(db: AsyncSession, record: BikeRaceRecord):
    await settle_bike_match_xp(db, record)
    reward_results = await compute_bike_match_rewards(record)
    if reward_results:
        is_user_best = reward_results[0]
        is_track_best = reward_results[1]
        rewards = reward_results[2]
        attachment = {
            "description": "bike赛道记录结算"
        }
        for reward in rewards:
            attachment[f"{reward.ccasset_type.value}"] = reward.new_ccamount
        content = {}
        final_duration = format_time_duration(record.duration_seconds)
        if is_track_best:
            content = {
                "en": f"Congratulations! You have just broken the {pick_i18n_text(record.track.name_i18n, Language.en)} bike track record and become the new track record holder, the score is: {final_duration}. Please accept your reward!", 
                "zh-Hans": f"恭喜！你刚刚成功刷新了 {pick_i18n_text(record.track.name_i18n, Language.zh_hans)} 自行车赛道最好成绩，成为赛道记录的保持者，成绩为：{final_duration}，请收下你的奖励！",
                "zh-Hant": f"恭喜！你剛剛成功刷新了 {pick_i18n_text(record.track.name_i18n, Language.zh_hant)} 自行車賽道最佳成績，成為賽道記錄的保持者，成績為：{final_duration}，請收下你的獎勵！",
                "ko": f"축하합니다! 방금 {pick_i18n_text(record.track.name_i18n, Language.ko)} 사이클 트랙에서 최고 기록을 경신하여 트랙 레코드 보유자가 되셨습니다. 기록은 {final_duration}입니다. 보상을 받으세요!",
                "ja": f"おめでとうございます！{pick_i18n_text(record.track.name_i18n, Language.ja)} バイクコースの最高記録を更新し、新たなコース記録保持者となりました！タイムは {final_duration} です。報酬をお受け取りください！"
            }
        elif is_user_best:
            content = {
                "en": f"Congratulations! You have just broken your personal best in {pick_i18n_text(record.track.name_i18n, Language.en)} bike track, the score is: {final_duration}, please accept your reward and keep up the good work!", 
                "zh-Hans": f"恭喜！你刚刚在 {pick_i18n_text(record.track.name_i18n, Language.zh_hans)} 自行车赛道成功刷新了自己的最好成绩，成绩为：{final_duration}，请收下你的奖励，再接再厉！",
                "zh-Hant": f"恭喜！你剛剛在 {pick_i18n_text(record.track.name_i18n, Language.zh_hant)} 自行車賽道成功刷新了自己的最佳成績，成績為：{final_duration}，請收下你的獎勵，再接再厲！",
                "ko": f"축하합니다! {pick_i18n_text(record.track.name_i18n, Language.ko)} 사이클 트랙에서 개인 최고 기록을 경신하셨습니다. 기록은 {final_duration}입니다. 축하드립니다! 앞으로도 좋은 성적 기대하겠습니다!",
                "ja": f"おめでとうございます！{pick_i18n_text(record.track.name_i18n, Language.ja)} バイクコースで自己ベストを更新しました！タイムは {final_duration} です。報酬を受け取って、次の記録更新を目指しましょう！"
            }
        else:
            content = {
                "en": f"You have just finished a bike race on track {pick_i18n_text(record.track.name_i18n, Language.en)}, the score is: {final_duration}. You're just a little bit away from your best score, we look forward to your next challenge!", 
                "zh-Hans": f"你刚刚完成了一场 {pick_i18n_text(record.track.name_i18n, Language.zh_hans)} 赛道的自行车比赛，成绩为：{final_duration}，距离自己的最好成绩只差一点点了，期待你的下一次挑战！",
                "zh-Hant": f"你剛剛完成了一場 {pick_i18n_text(record.track.name_i18n, Language.zh_hant)} 賽道的自行車比賽，成績為：{final_duration}，距離自己的最好成績只差一點點了，期待你的下一個挑戰！",
                "ko": f"방금 {pick_i18n_text(record.track.name_i18n, Language.ko)} 트랙에서 자전거 경주를 마쳤습니다. 결과는 {final_duration}입니다. 아쉽게도 개인 최고 기록에는 약간 못 미치네요. 다음 도전을 기대하겠습니다!",
                "ja": f"{pick_i18n_text(record.track.name_i18n, Language.ja)} バイクコースを完走しました！タイムは {final_duration} です。自己ベストまであと少しです。次回のチャレンジを楽しみにしています！"
            }
        mail = Mailbox(
            mail_id=f"mail_{uuid.uuid4()}",
            user_id=record.user_id,
            mail_type=MailType.REWARD,
            title_i18n={"en": "Successfully completed match", "zh-Hans": "成功完成比赛", "zh-Hant": "成功完成比賽", "ko": "대회가 성공적으로 마무리되었습니다", "ja": "レース完了"},
            content_i18n=content,
            attachment = attachment,
            is_received = False,
            expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        )
        db.add(mail)
