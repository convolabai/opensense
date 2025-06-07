"""Pydantic schemas for subscription API."""

from datetime import datetime
from typing import Dict, Any, Optional

from pydantic import BaseModel, Field, field_validator


class ChannelConfig(BaseModel):
    """Base configuration for notification channels."""
    pass


class SlackChannelConfig(ChannelConfig):
    """Slack channel configuration."""
    webhook_url: str
    channel: Optional[str] = None
    username: Optional[str] = "LangHook"


class WebhookChannelConfig(ChannelConfig):
    """Webhook channel configuration."""
    url: str
    headers: Optional[Dict[str, str]] = None
    method: str = "POST"


class EmailChannelConfig(ChannelConfig):
    """Email channel configuration."""
    to: str
    subject_template: Optional[str] = "LangHook Notification: {summary}"


class SubscriptionCreate(BaseModel):
    """Schema for creating a new subscription."""
    description: str = Field(..., description="Natural language description of what to watch for")
    channel_type: str = Field(..., description="Type of notification channel")
    channel_config: Dict[str, Any] = Field(..., description="Configuration for the notification channel")
    
    @field_validator('channel_type')
    @classmethod
    def validate_channel_type(cls, v):
        if v not in ['slack', 'webhook', 'email']:
            raise ValueError('channel_type must be one of: slack, webhook, email')
        return v


class SubscriptionUpdate(BaseModel):
    """Schema for updating a subscription."""
    description: Optional[str] = None
    channel_type: Optional[str] = None
    channel_config: Optional[Dict[str, Any]] = None
    active: Optional[bool] = None
    
    @field_validator('channel_type')
    @classmethod
    def validate_channel_type(cls, v):
        if v is not None and v not in ['slack', 'webhook', 'email']:
            raise ValueError('channel_type must be one of: slack, webhook, email')
        return v


class SubscriptionResponse(BaseModel):
    """Schema for subscription response."""
    id: int
    user_id: str
    description: str
    pattern: str
    channel_type: str
    channel_config: Dict[str, Any]
    active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SubscriptionListResponse(BaseModel):
    """Schema for listing subscriptions."""
    subscriptions: list[SubscriptionResponse]
    total: int
    page: int
    size: int