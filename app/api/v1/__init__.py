# app/api/v1/__init__.py
from fastapi import APIRouter
from app.api.v1 import user, user_follow, asset, common, mailbox, iap, homepage
from app.api.v1.competition import bike, running, competition

router = APIRouter()
router.include_router(user.router, prefix="/user", tags=["用户"])
router.include_router(user_follow.router, prefix="/user", tags=["用户关系"])
router.include_router(competition.router, prefix="/competition", tags=["比赛"])
router.include_router(bike.router, prefix="/competition/bike", tags=["bike比赛"])
router.include_router(running.router, prefix="/competition/running", tags=["running比赛"])
router.include_router(asset.router, prefix="/asset", tags=["资产"])
router.include_router(mailbox.router, prefix="/mailbox", tags=["邮箱"])
router.include_router(common.router, prefix="/common", tags=["通用API"])
router.include_router(iap.router, prefix="/iap", tags=["IAP"])
router.include_router(homepage.router, prefix="/homepage", tags="首页")