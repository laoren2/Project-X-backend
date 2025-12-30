from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.common import get_device_by_id
from app.db.models.common import Device
import uuid, random, time


async def generate_unique_device_id(db: AsyncSession) -> str:
    while True:
        device_id = f"{random.randint(100000000000000, 999999999999999)}"
        existing_device = await get_device_by_id(db, device_id)
        if not existing_device:
            return device_id

async def generate_did_service(db: AsyncSession) -> str:
    device_id = await generate_unique_device_id(db)
    new_device = Device(device_id=device_id)
    db.add(new_device)
    await db.commit()
    return device_id