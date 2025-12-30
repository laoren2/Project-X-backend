from fastapi import FastAPI, APIRouter
from app.core.config import CustomStaticFiles
from app.core.errors import ERROR_MESSAGES
from app.schemas.base import BizException, pick_i18n_text
from fastapi import Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.scheduler.task import start_scheduler, stop_scheduler
from app.api.internal import router as internal_router
from app.api.v1 import router as v1_router
from app.api.deps import Language, DEFAULT_LANGUAGE
from app.db.init_db import init_db, keep_event_loop_alive
from app.db.session import test_redis_connection, close_redis_connection, close_database_connection
from app.core.logging_config import setup_logging
import logging

logger = logging.getLogger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时的初始化操作
    logger.info("🚀 正在启动应用...")
    
    # 在 lifespan 开始时配置日志
    setup_logging(level="INFO")

    # 测试Redis连接
    try:
        redis_ok = await test_redis_connection()
        if redis_ok:
            logger.info("✅ Redis连接测试成功")
        else:
            logger.error("❌ Redis连接测试失败")
            raise Exception("Redis连接失败")
    except Exception as e:
        logger.error(f"❌ Redis连接测试失败: {e}")
        raise
    
    # 初始化数据库表结构
    try:
        await init_db()
        logger.info("✅ 数据库初始化完成")
    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}")
        raise
    
    # 启动事件循环保活任务
    #asyncio.create_task(keep_event_loop_alive())

    # 启动定时任务
    start_scheduler()
    logger.info("✅ 定时任务启动完成")
    
    yield
    
    # 关闭时的清理操作
    logger.info("🔄 正在关闭应用...")

    # 停止定时任务
    stop_scheduler()
    logger.info("✅ 定时任务停止完成")
    
    # 关闭Redis连接
    await close_redis_connection()
    
    # 关闭数据库连接池
    await close_database_connection()
    
    logger.info("✅ 应用关闭完成")

app = FastAPI(title="SportsX 用户中心", lifespan=lifespan)

app.include_router(internal_router, prefix="/api/internal", tags=["internal_api"])
app.include_router(v1_router, prefix="/api/v1", tags=["v1_version_api"])
app.mount("/resources", CustomStaticFiles(directory="resources"), name="resources")

# BizException处理器
@app.exception_handler(BizException)
async def biz_exception_handler(request: Request, exc: BizException):
    detail = exc.detail
    lang: Language = getattr(request.state, "lang", DEFAULT_LANGUAGE)
    raw_message = detail.get("message", "")
    params = detail.get("params", {})
    params = {
        k: render_param(v, lang)
        for k, v in params.items()
    }
    message = raw_message

    # 如果 message 是 i18n key，就翻译
    if raw_message in ERROR_MESSAGES:
        template = pick_i18n_text(
            ERROR_MESSAGES[raw_message],
            lang,
        )
        try:
            message = template.format(**params)
        except Exception:
            message = template

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "access_token": None,
            "code": detail["code"],
            "message": message,
            "data": None,
        },
    )

def render_param(value: str, lang: str) -> str:
    # 如果是 i18n key
    if value in ERROR_MESSAGES:
        return pick_i18n_text(ERROR_MESSAGES[value], lang)
    # 普通字符串
    return value