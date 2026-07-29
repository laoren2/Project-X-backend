from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.email_campaign import EmailCampaign, EmailCampaignRecipient
from app.db.models.user import User, UserSetting
from app.schemas.base import Language
from app.schemas.user import UserStatus


async def get_email_campaign_by_campaign_id(db: AsyncSession, campaign_id: str) -> EmailCampaign | None:
    result = await db.execute(select(EmailCampaign).where(EmailCampaign.campaign_id == campaign_id))
    return result.scalar_one_or_none()


async def get_next_active_email_campaign(db: AsyncSession) -> EmailCampaign | None:
    result = await db.execute(
        select(EmailCampaign)
        .where(EmailCampaign.status.in_(["queued", "sending"]))
        .order_by(EmailCampaign.created_at.asc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_subscribed_email_campaign_candidates(db: AsyncSession) -> list[tuple[object, str, Language]]:
    result = await db.execute(
        select(
            User.id,
            func.coalesce(User.email, User.apple_email, User.google_email).label("email_address"),
            UserSetting.preferred_language,
        )
        .join(UserSetting, UserSetting.user_id == User.id)
        .where(
            User.status == UserStatus.normal,
            or_(
                User.email.is_not(None),
                User.apple_email.is_not(None),
                User.google_email.is_not(None),
            ),
            UserSetting.is_email_subscribed.is_(True),
        )
        .order_by(User.created_at.asc())
    )
    # 同一邮箱可能出现在不同登录身份中；每个 campaign 只保留一条收件人记录。
    candidates: list[tuple[object, str, Language]] = []
    seen_emails: set[str] = set()
    for user_id, email, language in result.all():
        normalized_email = email.strip().lower()
        if normalized_email in seen_emails:
            continue
        seen_emails.add(normalized_email)
        candidates.append((user_id, normalized_email, language))
    return candidates


async def get_pending_email_campaign_recipients(
    db: AsyncSession,
    campaign_id: object,
    batch_size: int,
) -> list[EmailCampaignRecipient]:
    result = await db.execute(
        select(EmailCampaignRecipient)
        .where(
            EmailCampaignRecipient.campaign_id == campaign_id,
            EmailCampaignRecipient.status == "pending",
        )
        .order_by(EmailCampaignRecipient.created_at.asc())
        .limit(batch_size)
    )
    return list(result.scalars().all())


async def is_email_campaign_recipient_subscribed(
    db: AsyncSession,
    recipient: EmailCampaignRecipient,
) -> bool:
    result = await db.execute(
        select(User.id)
        .join(UserSetting, UserSetting.user_id == User.id)
        .where(
            User.id == recipient.user_id,
            User.status == UserStatus.normal,
            or_(
                func.lower(User.email) == recipient.email,
                func.lower(User.apple_email) == recipient.email,
                func.lower(User.google_email) == recipient.email,
            ),
            UserSetting.is_email_subscribed.is_(True),
        )
    )
    return result.scalar_one_or_none() is not None


async def get_email_campaign_recipient_by_unsubscribe_token(
    db: AsyncSession,
    unsubscribe_token: str,
) -> EmailCampaignRecipient | None:
    result = await db.execute(
        select(EmailCampaignRecipient).where(EmailCampaignRecipient.unsubscribe_token == unsubscribe_token)
    )
    return result.scalar_one_or_none()
