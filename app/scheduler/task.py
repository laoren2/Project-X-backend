from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timezone, timedelta
from app.services.competition.common import (
    generate_all_leaderboard_snapshots_service,
    clean_expired_records_service, clean_expired_teams_service
)
from app.db.session import AsyncSessionLocal
import logging

logger = logging.getLogger("scheduler")

scheduler = AsyncIOScheduler()



def start_scheduler():
    """启动定时任务调度器"""
    scheduler.start()
    logger.info("📅 定时任务调度器已启动")
    # 每分钟为每个性别生成一次排行榜快照
    scheduler.add_job(
        generate_all_leaderboard_snapshots,
        trigger=IntervalTrigger(minutes=1),
        next_run_time=datetime.now()
    )
    # 每小时清理一次超时/失效的记录
    scheduler.add_job(
        clean_expired_records,
        trigger=IntervalTrigger(hours=1),
        next_run_time=datetime.now()
    )
    # 每小时清理一次超时/失效的队伍
    scheduler.add_job(
        clean_expired_teams,
        trigger=IntervalTrigger(hours=1),
        next_run_time=datetime.now()
    )

def stop_scheduler():
    """停止定时任务调度器"""
    try:
        scheduler.shutdown(wait=True)  # wait=True 确保所有任务完成后再关闭
        logger.info("📅 定时任务调度器已关闭")
    except Exception as e:
        logger.error(f"❌ 关闭定时任务调度器时出错: {e}")

async def generate_all_leaderboard_snapshots():
    """生成自行车排行榜快照的定时任务"""
    try:
        # 创建数据库会话
        async with AsyncSessionLocal() as db:
            await generate_all_leaderboard_snapshots_service(db)
                        
    except Exception as e:
        logger.error(f"❌ 定时任务执行失败: {e}")


async def clean_expired_records():
    """清理过期或应结束的比赛记录"""
    try:
        async with AsyncSessionLocal() as db:
            await clean_expired_records_service(db)
    except Exception as e:
        logger.error(f"❌ 比赛记录清理任务执行失败: {e}")

async def clean_expired_teams():
    """清理过期或应结束的比赛队伍"""
    try:
        async with AsyncSessionLocal() as db:
            await clean_expired_teams_service(db)
    except Exception as e:
        logger.error(f"❌ 比赛队伍清理任务执行失败: {e}")