# app/api/v1/__init__.py
from fastapi import APIRouter
from app.api.v1 import user, user_follow
from app.api.v1.competition import bike, running, competition

router = APIRouter()
router.include_router(user.router, prefix="/user", tags=["用户"])
router.include_router(user_follow.router, prefix="/user", tags=["用户关系"])
router.include_router(competition.router, prefix="/competition", tags=["比赛"])
router.include_router(bike.router, prefix="/competition/bike", tags=["bike比赛"])
router.include_router(running.router, prefix="/competition/running", tags=["running比赛"])