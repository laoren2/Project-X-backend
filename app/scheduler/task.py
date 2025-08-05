from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
from app.services.competition.common import generate_all_leaderboard_snapshots_service
from app.db.session import AsyncSessionLocal
import logging

logger = logging.getLogger("scheduler")

scheduler = AsyncIOScheduler()



def start_scheduler():
    """启动定时任务调度器"""
    scheduler.start()
    logger.info("📅 定时任务调度器已启动")
    # 示例任务：每分钟为每个性别生成一次排行榜快照
    scheduler.add_job(
        generate_all_leaderboard_snapshots,
        trigger=IntervalTrigger(minutes=1),
        next_run_time=datetime.now()
    )

def stop_scheduler():
    """停止定时任务调度器"""
    try:
        scheduler.shutdown(wait=True)  # wait=True 确保所有任务完成后再关闭
        logger.info("📅 定时任务调度器已关闭")
    except Exception as e:
        logger.error(f"❌ 关闭定时任务调度器时出错: {e}")

# 示例任务逻辑
async def generate_all_leaderboard_snapshots():
    """生成自行车排行榜快照的定时任务"""
    try:
        # 创建数据库会话
        async with AsyncSessionLocal() as db:
            await generate_all_leaderboard_snapshots_service(db)
                        
    except Exception as e:
        logger.error(f"❌ 定时任务执行失败: {e}")