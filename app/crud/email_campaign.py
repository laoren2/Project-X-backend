from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.email_campaign import EmailCampaign, EmailCampaignRecipient
from app.db.models.user import User, UserSetting
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


async def get_subscribed_email_campaign_candidates(db: AsyncSession) -> list[tuple[object, str]]:
    result = await db.execute(
        select(User.id, User.email)
        .join(UserSetting, UserSetting.user_id == User.id)
        .where(
            User.status == UserStatus.normal,
            User.email.is_not(None),
            UserSetting.is_email_subscribed.is_(True),
        )
    )
    return [(row[0], row[1]) for row in result.all()]


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
            User.email == recipient.email,
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
