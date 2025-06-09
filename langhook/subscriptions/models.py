"""Database models for subscription management."""


from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Subscription(Base):
    """Database model for natural language subscriptions."""

    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    subscriber_id = Column(String(255), nullable=False, index=True)  # Subscriber identifier
    description = Column(Text, nullable=False)  # Natural language description
    pattern = Column(String(255), nullable=False)  # Generated NATS filter subject pattern
    channel_type = Column(String(50), nullable=False)  # 'webhook'
    channel_config = Column(Text, nullable=False)  # JSON config for channel
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class EventSchemaRegistry(Base):
    """Database model for event schema registry."""

    __tablename__ = "event_schema_registry"

    publisher = Column(String(255), primary_key=True, nullable=False)
    resource_type = Column(String(255), primary_key=True, nullable=False)
    action = Column(String(255), primary_key=True, nullable=False)


class EventLog(Base):
    """Database model for logging canonical events."""

    __tablename__ = "event_logs"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(255), nullable=False, index=True)  # CloudEvent ID
    source = Column(String(255), nullable=False, index=True)  # Event source
    subject = Column(String(255), nullable=False, index=True)  # NATS subject
    publisher = Column(String(255), nullable=False, index=True)  # Canonical publisher
    resource_type = Column(String(255), nullable=False, index=True)  # Canonical resource type
    resource_id = Column(String(255), nullable=False, index=True)  # Canonical resource ID
    action = Column(String(255), nullable=False, index=True)  # Canonical action
    canonical_data = Column(JSON, nullable=False)  # Full canonical event data
    raw_payload = Column(JSON, nullable=True)  # Original raw payload
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)  # Event timestamp
    logged_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)  # Log timestamp
