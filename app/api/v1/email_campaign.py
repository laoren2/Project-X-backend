import hmac
import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.base import Language
from app.core.config import settings
from app.services.email_campaign import (
    handle_aliyun_delivery_event_service,
    render_email_unsubscribe_page,
    unsubscribe_email_campaign_recipient_service,
)


router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/delivery-events", status_code=204, summary="接收阿里云邮件投递事件")
async def direct_mail_delivery_events(
    event: dict[str, Any],
    eventbridge_token: str | None = Header(default=None, alias="x-eventbridge-signature-token"),
    db: AsyncSession = Depends(get_db),
):
    if not settings.ALIYUN_EVENTBRIDGE_TOKEN:
        logger.error("Rejected Direct Mail delivery event because ALIYUN_EVENTBRIDGE_TOKEN is not configured")
        raise HTTPException(status_code=503, detail="Delivery event webhook is not configured")
    if eventbridge_token is None or not hmac.compare_digest(eventbridge_token, settings.ALIYUN_EVENTBRIDGE_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid EventBridge token")

    await handle_aliyun_delivery_event_service(db, event)
    return Response(status_code=204)


@router.get("/unsubscribe", response_class=HTMLResponse, summary="取消订阅产品邮件")
async def unsubscribe_email_campaign(
    token: str = Query(...),
    lang: Language = Query(default=Language.en),
    db: AsyncSession = Depends(get_db),
):
    await unsubscribe_email_campaign_recipient_service(db, token)
    return HTMLResponse(render_email_unsubscribe_page(lang))
