"""Apple Sign in with Apple server-to-server notification handling."""

import asyncio
from datetime import datetime, timezone
import logging

import jwt
from jwt import PyJWKClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.crud.email_campaign import upsert_email_campaign_suppression
from app.crud.user import get_exist_user_by_apple_id


logger = logging.getLogger(__name__)


def _verify_apple_notification_payload(signed_payload: str) -> dict:
    jwks_client = PyJWKClient(settings.APPLE_KEYS_URL)
    signing_key = jwks_client.get_signing_key_from_jwt(signed_payload)
    return jwt.decode(
        signed_payload,
        signing_key.key,
        algorithms=["ES256"],
        audience=settings.APPLE_SIGN_IN_CLIENT_ID,
        issuer="https://appleid.apple.com",
        options={"require": ["aud", "events", "iat", "iss"]},
    )


def _event_time(payload: dict) -> datetime | None:
    issued_at = payload.get("iat")
    if not isinstance(issued_at, (int, float)):
        return None
    return datetime.fromtimestamp(issued_at, tz=timezone.utc)


async def handle_apple_sign_in_notification_service(db: AsyncSession, signed_payload: str) -> bool:
    """Apply forwarding changes to campaign-only email suppression records.

    Invalid notifications deliberately return False to the route, which still sends a
    successful HTTP response so arbitrary invalid requests cannot induce Apple retries.
    """
    try:
        payload = await asyncio.to_thread(_verify_apple_notification_payload, signed_payload)
    except Exception:
        logger.warning("Discarded invalid Sign in with Apple server notification", exc_info=True)
        return False

    event = payload.get("events")
    if not isinstance(event, dict):
        logger.warning("Discarded Sign in with Apple notification without events")
        return False

    event_type = event.get("type")
    apple_id = event.get("sub")
    if not isinstance(event_type, str) or not isinstance(apple_id, str):
        logger.warning("Discarded Sign in with Apple notification without type or sub")
        return False

    if event_type not in {"email-disabled", "email-enabled", "consent-revoked", "account-deleted"}:
        logger.info("Ignored unsupported Sign in with Apple event type: %s", event_type)
        return True

    user = await get_exist_user_by_apple_id(db, apple_id)
    event_email = event.get("email")
    email = event_email if isinstance(event_email, str) and event_email else (user.apple_email if user else None)
    if not email:
        logger.info("No relay email for Sign in with Apple event type=%s sub=%s", event_type, apple_id)
        return True

    is_active = event_type != "email-enabled"
    reason = "apple_email_disabled" if event_type == "email-disabled" else (
        "apple_identity_revoked" if event_type in {"consent-revoked", "account-deleted"} else "apple_email_enabled"
    )
    await upsert_email_campaign_suppression(
        db,
        email=email,
        user_id=user.id if user else None,
        reason=reason,
        is_active=is_active,
        event_at=_event_time(payload),
    )
    await db.commit()
    return True
