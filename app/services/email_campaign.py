from datetime import datetime, timezone
from html import escape
from pathlib import Path
import asyncio
import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import ErrorCode
from app.core.storage import build_resource_url
from app.crud.email_campaign import (
    get_email_campaign_by_campaign_id,
    get_email_campaign_recipient_by_unsubscribe_token,
    get_next_active_email_campaign,
    get_pending_email_campaign_recipients,
    get_subscribed_email_campaign_candidates,
    is_email_campaign_recipient_subscribed,
)
from app.crud.user import get_settings_by_user_id
from app.db.models.email_campaign import EmailCampaign, EmailCampaignRecipient
from app.schemas.base import BizException
from app.schemas.email_campaign import EmailCampaignInfo
from app.services.common import upload_to_oss
from app.services.email import send_marketing_email


logger = logging.getLogger(__name__)

VIDEO_WATERMARK_TEMPLATE_KEY = "video_watermark_feature"
VIDEO_WATERMARK_SUBJECT = "【Movmov】给你的运动视频，加上专属数据水印"
VIDEO_WATERMARK_HERO_PATH = "resources/email/video_watermark_feature_hero.jpg"
VIDEO_WATERMARK_TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "templates/email/video_watermark_feature.html"
VIDEO_WATERMARK_HERO_SOURCE_PATH = VIDEO_WATERMARK_TEMPLATE_PATH.parent / "assets/video_watermark_feature_hero.jpg"
EMAIL_BATCH_SIZE = 20


def _to_campaign_info(campaign: EmailCampaign) -> EmailCampaignInfo:
    return EmailCampaignInfo.model_validate(campaign, from_attributes=True)


async def _ensure_video_watermark_hero_uploaded() -> None:
    asset_path = VIDEO_WATERMARK_HERO_SOURCE_PATH
    if not asset_path.is_file():
        raise RuntimeError(f"Missing email hero asset: {asset_path}")
    asset_data = await asyncio.to_thread(asset_path.read_bytes)
    await upload_to_oss(VIDEO_WATERMARK_HERO_PATH, asset_data)


def _render_video_watermark_email(unsubscribe_token: str) -> tuple[str, str]:
    template = VIDEO_WATERMARK_TEMPLATE_PATH.read_text(encoding="utf-8")
    hero_image_url = build_resource_url(f"/{VIDEO_WATERMARK_HERO_PATH}")
    unsubscribe_url = f"{settings.PUBLIC_APP_DOMAIN.rstrip('/')}/api/v1/email_campaign/unsubscribe?token={unsubscribe_token}"
    return (
        template.replace("{{ hero_image_url }}", escape(hero_image_url, quote=True))
        .replace("{{ unsubscribe_url }}", escape(unsubscribe_url, quote=True)),
        unsubscribe_url,
    )


async def create_video_watermark_email_campaign_service(db: AsyncSession, created_by: str) -> EmailCampaignInfo:
    await _ensure_video_watermark_hero_uploaded()
    candidates = await get_subscribed_email_campaign_candidates(db)
    campaign = EmailCampaign(
        campaign_id=f"campaign_{uuid.uuid4().hex}",
        template_key=VIDEO_WATERMARK_TEMPLATE_KEY,
        subject=VIDEO_WATERMARK_SUBJECT,
        created_by=created_by,
        total_count=len(candidates),
    )
    db.add(campaign)
    await db.flush()
    db.add_all([
        EmailCampaignRecipient(
            campaign_id=campaign.id,
            user_id=user_id,
            email=email,
            unsubscribe_token=uuid.uuid4().hex,
        )
        for user_id, email in candidates
    ])
    await db.commit()
    await db.refresh(campaign)
    return _to_campaign_info(campaign)


async def start_email_campaign_service(db: AsyncSession, campaign_id: str) -> EmailCampaignInfo:
    campaign = await get_email_campaign_by_campaign_id(db, campaign_id)
    if campaign is None:
        raise BizException(code=ErrorCode.EMAIL_CAMPAIGN_NOT_FOUND, message="email_campaign.not_found")
    if campaign.status not in {"draft", "failed"}:
        raise BizException(code=ErrorCode.EMAIL_CAMPAIGN_STATE_ERROR, message="email_campaign.invalid_state")
    campaign.status = "queued"
    campaign.started_at = None
    campaign.completed_at = None
    await db.commit()
    await db.refresh(campaign)
    return _to_campaign_info(campaign)


async def get_email_campaign_service(db: AsyncSession, campaign_id: str) -> EmailCampaignInfo:
    campaign = await get_email_campaign_by_campaign_id(db, campaign_id)
    if campaign is None:
        raise BizException(code=ErrorCode.EMAIL_CAMPAIGN_NOT_FOUND, message="email_campaign.not_found")
    return _to_campaign_info(campaign)


async def process_email_campaigns_service(db: AsyncSession) -> None:
    campaign = await get_next_active_email_campaign(db)
    if campaign is None:
        return
    if campaign.status == "queued":
        campaign.status = "sending"
        campaign.started_at = datetime.now(timezone.utc)
        await db.commit()

    recipients = await get_pending_email_campaign_recipients(db, campaign.id, EMAIL_BATCH_SIZE)
    if not recipients:
        campaign.status = "completed"
        campaign.completed_at = datetime.now(timezone.utc)
        await db.commit()
        return

    for recipient in recipients:
        if not await is_email_campaign_recipient_subscribed(db, recipient):
            recipient.status = "skipped"
            campaign.skipped_count += 1
            await db.commit()
            continue
        try:
            html, unsubscribe_url = _render_video_watermark_email(recipient.unsubscribe_token)
            await send_marketing_email(recipient.email, campaign.subject, html, unsubscribe_url)
            recipient.status = "sent"
            recipient.sent_at = datetime.now(timezone.utc)
            campaign.sent_count += 1
        except Exception as exc:
            logger.exception("Email campaign delivery failed: campaign=%s recipient=%s", campaign.campaign_id, recipient.id)
            recipient.status = "failed"
            recipient.error_message = str(exc)[:1000]
            campaign.failed_count += 1
        await db.commit()


async def unsubscribe_email_campaign_recipient_service(db: AsyncSession, unsubscribe_token: str) -> None:
    recipient = await get_email_campaign_recipient_by_unsubscribe_token(db, unsubscribe_token)
    if recipient is None:
        raise BizException(code=ErrorCode.EMAIL_CAMPAIGN_NOT_FOUND, message="email_campaign.not_found")
    user_settings = await get_settings_by_user_id(db, recipient.user_id)
    if user_settings:
        user_settings.is_email_subscribed = False
    if recipient.status == "pending":
        recipient.status = "skipped"
    await db.commit()
