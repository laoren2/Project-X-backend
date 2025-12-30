from sqlalchemy import Column, String, Boolean, DateTime, Date, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base
import uuid


# 设备的登记记录表
class Device(Base):
    __tablename__ = "devices"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(String, index=True, unique=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)