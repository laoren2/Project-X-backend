from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.base import BaseResponse
from app.schemas.user import UserBaseInfo
from app.schemas.user_follow import PersonInfoResponse
from app.services.user import get_exist_user_by_phone
from app.core.errors import ErrorCode
from app.schemas.user import AuthContext
from app.api.deps import get_current_admin

router = APIRouter()

