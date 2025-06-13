"""Database models for subscription management."""


from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text
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
    channel_type = Column(String(50), nullable=True)  # 'webhook' or None for polling-only
    channel_config = Column(Text, nullable=True)  # JSON config for channel or None
    active = Column(Boolean, default=True, nullable=False)
    disposable = Column(Boolean, default=False, nullable=False)  # Whether subscription is one-time use
    used = Column(Boolean, default=False, nullable=False)  # Whether disposable subscription has been triggered
    gate = Column(JSON, nullable=True)  # LLM gate configuration
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


class SubscriptionEventLog(Base):
    """Database model for logging events that match specific subscriptions."""

    __tablename__ = "subscription_event_logs"

    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, nullable=False, index=True)  # Reference to subscription
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
    webhook_sent = Column(Boolean, default=False, nullable=False)  # Whether webhook was sent
    webhook_response_status = Column(Integer, nullable=True)  # HTTP status if webhook sent
    gate_passed = Column(Boolean, nullable=True)  # Whether LLM gate passed (null if gate not enabled)
    gate_reason = Column(Text, nullable=True)  # Reason from LLM gate evaluation
    logged_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)  # Log timestamp


class IngestMapping(Base):
    """Database model for ingest mappings with fingerprints."""

    __tablename__ = "ingest_mappings"

    fingerprint = Column(String(64), primary_key=True, nullable=False)  # SHA-256 fingerprint
    publisher = Column(String(255), nullable=False, index=True)  # Publisher (source)
    event_name = Column(String(255), nullable=False, index=True)  # Event name description
    mapping_expr = Column(Text, nullable=False)  # JSONata mapping expression
    event_field_expr = Column(Text, nullable=True)  # JSONata expression to extract event/action field
    structure = Column(JSON, nullable=False)  # Unhashed type skeleton structure
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
