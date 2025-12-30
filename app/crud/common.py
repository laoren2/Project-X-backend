from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.common import Device
from typing import Optional, List
import uuid, random, time


async def get_device_by_id(db: AsyncSession, device_id: str) -> Device | None:
    result = await db.execute(
        select(Device)
        .where(Device.device_id == device_id)
    )
    return result.scalar_one_or_none()