from sqlalchemy import select, func, case
from app.db.models.homepage import Announcement, BannerAds
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List


async def get_latest_annoucements(db: AsyncSession) -> List[Announcement]:
    stmt = (
        select(Announcement)
        .order_by(Announcement.created_at.desc()).offset(0).limit(3)
    )
    result = await db.execute(stmt)
    return result.scalars().all()

async def get_displayed_ads(db: AsyncSession) -> List[BannerAds]:
    stmt = (
        select(BannerAds)
        .where(BannerAds.is_displayed == True)
        .order_by(BannerAds.created_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()