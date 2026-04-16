from fastapi import APIRouter, Depends, File, UploadFile, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.base import BaseResponse
from app.schemas.user import AuthContext
from app.schemas.competition.common import RegionCreate
from app.core.errors import ErrorCode
from app.api.deps import get_current_admin
from typing import Optional
from pathlib import Path
from datetime import datetime


router = APIRouter()

