from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.email_campaign import unsubscribe_email_campaign_recipient_service


router = APIRouter()


@router.get("/unsubscribe", response_class=HTMLResponse, summary="取消订阅产品邮件")
async def unsubscribe_email_campaign(
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    await unsubscribe_email_campaign_recipient_service(db, token)
    return HTMLResponse(
        "<html><body style='font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;padding:48px;text-align:center;color:#16213e;'><h1>已取消订阅</h1><p>你将不再收到 Movmov 的产品宣传邮件。</p></body></html>"
    )
