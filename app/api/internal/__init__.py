from fastapi import APIRouter
from app.api.internal import user, competition


router = APIRouter()
router.include_router(user.router, prefix="/user", tags=["用户"])
router.include_router(competition.router, prefix="/competition", tags="比赛")