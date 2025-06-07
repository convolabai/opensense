"""Database models for subscription management."""


from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Subscription(Base):
    """Database model for natural language subscriptions."""

    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    subscriber_id = Column(String(255), nullable=False, index=True)  # JWT sub claim or other subscriber identifier
    description = Column(Text, nullable=False)  # Natural language description
    pattern = Column(String(255), nullable=False)  # Generated NATS filter subject pattern
    channel_type = Column(String(50), nullable=False)  # 'webhook'
    channel_config = Column(Text, nullable=False)  # JSON config for channel
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
