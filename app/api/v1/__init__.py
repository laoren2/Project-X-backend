# app/api/v1/__init__.py
from fastapi import APIRouter
from app.api.v1 import user, user_follow, asset, common, mailbox, iap, homepage
import app.api.v1.competition.bike as bike_competition
import app.api.v1.competition.running as running_competition
import app.api.v1.competition.competition as common_competition
import app.api.v1.training.bike as bike_training
import app.api.v1.training.running as running_training

router = APIRouter()
router.include_router(user.router, prefix="/user", tags=["用户"])
router.include_router(user_follow.router, prefix="/user", tags=["用户关系"])
router.include_router(common_competition.router, prefix="/competition", tags=["比赛"])
router.include_router(bike_competition.router, prefix="/competition/bike", tags=["bike比赛"])
router.include_router(running_competition.router, prefix="/competition/running", tags=["running比赛"])
router.include_router(asset.router, prefix="/asset", tags=["资产"])
router.include_router(mailbox.router, prefix="/mailbox", tags=["邮箱"])
router.include_router(common.router, prefix="/common", tags=["通用API"])
router.include_router(iap.router, prefix="/iap", tags=["IAP"])
router.include_router(homepage.router, prefix="/homepage", tags="首页")
router.include_router(bike_training.router, prefix="/training/bike", tags=["bike训练"])
router.include_router(running_training.router, prefix="/training/running", tags=["running训练"])