from fastapi import APIRouter
from app.api.internal import user

router = APIRouter()
router.include_router(user.router, prefix="/user", tags=["用户"])