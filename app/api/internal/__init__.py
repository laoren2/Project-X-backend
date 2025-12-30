from fastapi import APIRouter
from app.api.internal import user, asset, mailbox, homepage
from app.api.internal.competition import bike, running, competition


router = APIRouter()
router.include_router(user.router, prefix="/user", tags=["用户"])
router.include_router(competition.router, prefix="/competition", tags="比赛")
router.include_router(bike.router, prefix="/competition/bike", tags="自行车比赛")
router.include_router(running.router, prefix="/competition/running", tags="跑步比赛")
router.include_router(asset.router, prefix="/asset", tags="资产")
router.include_router(mailbox.router, prefix="/mailbox", tags="邮箱")
router.include_router(homepage.router, prefix="/homepage", tags="首页")