from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import Language
from app.crud.homepage import (
    get_latest_annoucements, get_displayed_ads
)
from app.db.models.homepage import Announcement, BannerAds
from app.schemas.homepage import (
    AnnouncementInfo, AnnouncementInfoResponse, BannerAdsInfoResponse,
    AdsInfo, AdCreateForm
)
from app.schemas.base import pick_i18n_text
import uuid


async def query_annoucements_service(db: AsyncSession, lang: Language) -> AnnouncementInfoResponse:
    annoucements = await get_latest_annoucements(db)
    annoucement_infos = [AnnouncementInfo(
        content=pick_i18n_text(announcement.content_i18n, lang),
        date=announcement.created_at.isoformat()
    ) for announcement in annoucements]
    return AnnouncementInfoResponse(announcements=annoucement_infos)


async def update_announcements_service(
    db: AsyncSession,
    content: dict
):
    db.add(Announcement(content_i18n=content))
    await db.commit()


async def query_banner_ads_service(db: AsyncSession) -> BannerAdsInfoResponse:
    ads = await get_displayed_ads(db)
    ads_infos = [AdsInfo(
        image_url=ad.image_url,
        web_url=ad.web_url
    ) for ad in ads]
    return BannerAdsInfoResponse(ads=ads_infos)


async def create_banner_ad_service(
    db: AsyncSession,
    form: AdCreateForm,
    image_url: str
):
    new_ad = BannerAds(
        ad_id=f"ad_{str(uuid.uuid4())[:8]}",
        image_url=image_url,
        web_url=form.web_url,
        is_displayed=form.is_displayed
    )
    db.add(new_ad)
    await db.commit()