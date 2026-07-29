from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.base import Language
from app.services.email_campaign import render_email_unsubscribe_page, unsubscribe_email_campaign_recipient_service


router = APIRouter()


@router.get("/unsubscribe", response_class=HTMLResponse, summary="取消订阅产品邮件")
async def unsubscribe_email_campaign(
    token: str = Query(...),
    lang: Language = Query(default=Language.en),
    db: AsyncSession = Depends(get_db),
):
    await unsubscribe_email_campaign_recipient_service(db, token)
    return HTMLResponse(render_email_unsubscribe_page(lang))
