# app/api/v1/__init__.py
from fastapi import APIRouter
from app.api.v1 import user, user_follow

router = APIRouter()
router.include_router(user.router, prefix="/user", tags=["用户"])
router.include_router(user_follow.router, prefix="/user", tags=["用户关系"])