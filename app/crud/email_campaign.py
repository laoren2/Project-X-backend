from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.email_campaign import EmailCampaign, EmailCampaignRecipient, EmailCampaignSuppression
from app.db.models.user import User, UserSetting
from app.schemas.base import Language
from app.schemas.user import UserStatus


async def get_email_campaign_by_campaign_id(db: AsyncSession, campaign_id: str) -> EmailCampaign | None:
    result = await db.execute(select(EmailCampaign).where(EmailCampaign.campaign_id == campaign_id))
    return result.scalar_one_or_none()


async def get_email_campaign_by_id(db: AsyncSession, campaign_id: object) -> EmailCampaign | None:
    result = await db.execute(select(EmailCampaign).where(EmailCampaign.id == campaign_id))
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
    campaign_email = func.lower(func.trim(func.coalesce(User.email, User.apple_email, User.google_email)))
    suppression_exists = (
        select(EmailCampaignSuppression.id)
        .where(
            EmailCampaignSuppression.email == campaign_email,
            EmailCampaignSuppression.is_active.is_(True),
        )
        .exists()
    )
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
            ~suppression_exists,
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


async def has_accepted_email_campaign_recipients(db: AsyncSession, campaign_id: object) -> bool:
    result = await db.execute(
        select(EmailCampaignRecipient.id)
        .where(
            EmailCampaignRecipient.campaign_id == campaign_id,
            EmailCampaignRecipient.status == "accepted",
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def get_email_campaign_recipient_by_message_id(
    db: AsyncSession,
    message_id: str,
) -> EmailCampaignRecipient | None:
    normalized_message_id = message_id.strip()
    bare_message_id = normalized_message_id.strip("<>")
    accepted_values = {normalized_message_id, f"<{bare_message_id}>"}
    result = await db.execute(
        select(EmailCampaignRecipient).where(EmailCampaignRecipient.message_id.in_(accepted_values))
    )
    return result.scalar_one_or_none()


async def upsert_email_campaign_suppression(
    db: AsyncSession,
    *,
    email: str,
    reason: str,
    is_active: bool,
    user_id: object | None = None,
    event_at: datetime | None = None,
) -> None:
    normalized_email = email.strip().lower()
    stmt = insert(EmailCampaignSuppression).values(
        email=normalized_email,
        user_id=user_id,
        reason=reason,
        is_active=is_active,
        last_event_at=event_at,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[EmailCampaignSuppression.email],
        set_={
            "user_id": user_id,
            "reason": reason,
            "is_active": is_active,
            "last_event_at": event_at,
            "updated_at": func.now(),
        },
        where=(
            None
            if event_at is None
            else (
                EmailCampaignSuppression.last_event_at.is_(None)
                | (EmailCampaignSuppression.last_event_at <= event_at)
            )
        ),
    )
    await db.execute(stmt)


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
