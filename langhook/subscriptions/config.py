"""Configuration for subscription service."""

from typing import Optional
from pydantic import BaseModel
from langhook.core.config import app_config


class SubscriptionSettings(BaseModel):
    """Settings for subscription management."""

    # Database settings
    postgres_dsn: str

    # LLM service settings
    llm_provider: str
    llm_api_key: Optional[str]
    llm_model: str
    llm_base_url: Optional[str]
    llm_temperature: float
    llm_max_tokens: int

    # Legacy OpenAI support (deprecated - use LLM_* settings)
    openai_api_key: Optional[str]

    # Event logging settings
    event_logging_enabled: bool
    nats_url: str
    nats_stream_events: str
    nats_consumer_group: str


def load_subscription_settings() -> SubscriptionSettings:
    """Load subscription settings from core configuration."""
    # Reload core config to pick up environment changes
    from langhook.core.config import load_app_config
    app_config = load_app_config(reload=True)
    
    return SubscriptionSettings(
        postgres_dsn=app_config.postgres_dsn or "postgresql://langhook:langhook@localhost:5432/langhook",
        llm_provider=app_config.subscriptions.llm_provider,
        llm_api_key=app_config.subscriptions.llm_api_key,
        llm_model=app_config.subscriptions.llm_model,
        llm_base_url=app_config.subscriptions.llm_base_url,
        llm_temperature=app_config.subscriptions.llm_temperature,
        llm_max_tokens=app_config.subscriptions.llm_max_tokens,
        openai_api_key=app_config.openai_api_key,
        event_logging_enabled=app_config.subscriptions.event_logging_enabled,
        nats_url=app_config.nats_url,
        nats_stream_events=app_config.nats_stream_events,
        nats_consumer_group=app_config.subscriptions.nats_consumer_group,
    )


# Global subscription settings instance
subscription_settings = load_subscription_settings()
