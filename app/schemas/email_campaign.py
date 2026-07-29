from datetime import datetime

from pydantic import BaseModel


class EmailCampaignInfo(BaseModel):
    campaign_id: str
    template_key: str
    subject: str
    status: str
    total_count: int
    sent_count: int
    failed_count: int
    skipped_count: int
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
