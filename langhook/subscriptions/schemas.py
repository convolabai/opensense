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


class SubscriptionCreate(BaseModel):
    """Schema for creating a new subscription."""
    description: str = Field(..., description="Natural language description of what to watch for")
    channel_type: str = Field(..., description="Type of notification channel")
    channel_config: dict[str, Any] = Field(..., description="Configuration for the notification channel")

    @field_validator('channel_type')
    @classmethod
    def validate_channel_type(cls, v):
        if v not in ['webhook']:
            raise ValueError('channel_type must be: webhook')
        return v


class SubscriptionUpdate(BaseModel):
    """Schema for updating a subscription."""
    description: str | None = None
    channel_type: str | None = None
    channel_config: dict[str, Any] | None = None
    active: bool | None = None

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
    channel_type: str
    channel_config: dict[str, Any]
    active: bool
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
