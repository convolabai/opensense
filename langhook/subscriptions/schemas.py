"""Pydantic schemas for subscription API."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ChannelConfig(BaseModel):
    """Base configuration for notification channels."""
    pass


class WebhookChannelConfig(ChannelConfig):
    """Webhook channel configuration."""
    url: str
    headers: dict[str, str] | None = None
    method: str = "POST"


class GateConfig(BaseModel):
    """LLM gate configuration for subscription filtering."""
    enabled: bool = Field(default=False, description="Whether the LLM gate is enabled")
    prompt: str = Field(default="", description="Prompt for gate evaluation")


class SubscriptionCreate(BaseModel):
    """Schema for creating a new subscription."""
    description: str = Field(..., description="Natural language description of what to watch for")
    channel_type: str | None = Field(None, description="Type of notification channel")
    channel_config: dict[str, Any] | None = Field(None, description="Configuration for the notification channel")
    gate: GateConfig | None = Field(None, description="LLM gate configuration")
    disposable: bool = Field(False, description="Whether this subscription is for one-time use only")

    @field_validator('channel_type')
    @classmethod
    def validate_channel_type(cls, v):
        if v is not None and v not in ['webhook']:
            raise ValueError('channel_type must be: webhook')
        return v


class SubscriptionUpdate(BaseModel):
    """Schema for updating a subscription."""
    description: str | None = None
    channel_type: str | None = None
    channel_config: dict[str, Any] | None = None
    active: bool | None = None
    gate: GateConfig | None = None
    disposable: bool | None = None

    @field_validator('channel_type')
    @classmethod
    def validate_channel_type(cls, v):
        if v is not None and v not in ['webhook']:
            raise ValueError('channel_type must be: webhook')
        return v


class SubscriptionResponse(BaseModel):
    """Schema for subscription response."""
    id: int
    subscriber_id: str
    description: str
    pattern: str
    channel_type: str | None
    channel_config: dict[str, Any] | None
    active: bool
    disposable: bool
    used: bool
    gate: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class SubscriptionListResponse(BaseModel):
    """Schema for listing subscriptions."""
    subscriptions: list[SubscriptionResponse]
    total: int
    page: int
    size: int


class EventLogResponse(BaseModel):
    """Schema for event log response."""
    id: int
    event_id: str
    source: str
    subject: str
    publisher: str
    resource_type: str
    resource_id: str
    action: str
    canonical_data: dict[str, Any]
    raw_payload: dict[str, Any] | None = None
    timestamp: datetime
    logged_at: datetime

    class Config:
        from_attributes = True


class EventLogListResponse(BaseModel):
    """Schema for listing event logs."""
    event_logs: list[EventLogResponse]
    total: int
    page: int
    size: int


class SubscriptionEventLogResponse(BaseModel):
    """Schema for subscription event log response."""
    id: int
    subscription_id: int
    event_id: str
    source: str
    subject: str
    publisher: str
    resource_type: str
    resource_id: str
    action: str
    canonical_data: dict[str, Any]
    raw_payload: dict[str, Any] | None = None
    timestamp: datetime
    webhook_sent: bool
    webhook_response_status: int | None = None
    gate_passed: bool | None = None
    gate_reason: str | None = None
    logged_at: datetime

    class Config:
        from_attributes = True


class SubscriptionEventLogListResponse(BaseModel):
    """Schema for listing subscription event logs."""
    event_logs: list[SubscriptionEventLogResponse]
    total: int
    page: int
    size: int


class IngestMappingResponse(BaseModel):
    """Schema for ingest mapping response."""
    fingerprint: str
    publisher: str
    event_name: str
    mapping_expr: str
    event_field_expr: str | None = None
    structure: dict[str, Any]
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class IngestMappingListResponse(BaseModel):
    """Schema for listing ingest mappings."""
    mappings: list[IngestMappingResponse]
    total: int
    page: int
    size: int
