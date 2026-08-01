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


async def send_marketing_email(
    to_email: str,
    subject: str,
    plain_text: str,
    html: str,
    unsubscribe_url: str,
    message_id: str,
) -> None:
    message = MIMEMultipart("alternative")
    message["Subject"] = Header(subject, "UTF-8")
    message["From"] = formataddr(("Movmov", settings.NOREPLY_EMAIL_ADDRESS))
    message["To"] = to_email
    message["Date"] = email.utils.formatdate()
    message["Message-ID"] = message_id
    message["List-Unsubscribe"] = f"<{unsubscribe_url}>"
    message.attach(MIMEText(plain_text, _subtype="plain", _charset="UTF-8"))
    message.attach(MIMEText(html, _subtype="html", _charset="UTF-8"))
    await asyncio.wait_for(
        asyncio.to_thread(send_smtp_email, [to_email], message.as_string()),
        timeout=15,
    )
