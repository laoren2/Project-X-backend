import asyncio
import email.utils
import smtplib
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from app.core.config import settings


def send_smtp_email(receivers: list[str], message: str) -> None:
    client = smtplib.SMTP_SSL(settings.ALIYUN_EMAIL_ENDPOINT, 465, timeout=10)
    try:
        client.login(settings.NOREPLY_EMAIL_ADDRESS, settings.NOREPLY_EMAIL_PASSWORD)
        client.sendmail(settings.NOREPLY_EMAIL_ADDRESS, receivers, message)
    finally:
        client.quit()


async def send_marketing_email(to_email: str, subject: str, html: str, unsubscribe_url: str) -> None:
    message = MIMEMultipart("alternative")
    message["Subject"] = Header(subject, "UTF-8")
    message["From"] = formataddr(("Movmov", settings.NOREPLY_EMAIL_ADDRESS))
    message["To"] = to_email
    message["Date"] = email.utils.formatdate()
    message["Message-id"] = email.utils.make_msgid()
    message["List-Unsubscribe"] = f"<{unsubscribe_url}>"
    message.attach(MIMEText("Movmov 推出了新的运动视频水印功能。请在 Movmov App 内体验。", _subtype="plain", _charset="UTF-8"))
    message.attach(MIMEText(html, _subtype="html", _charset="UTF-8"))
    await asyncio.wait_for(
        asyncio.to_thread(send_smtp_email, [to_email], message.as_string()),
        timeout=15,
    )
