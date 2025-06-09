"""Configuration for subscription service."""

import os

from pydantic import BaseModel, Field


class SubscriptionSettings(BaseModel):
    """Settings for subscription management."""

    # Database settings
    postgres_dsn: str = Field(default="postgresql://langhook:langhook@localhost:5432/langhook", env="POSTGRES_DSN")

    # LLM service settings
    llm_provider: str = Field(default="openai", env="LLM_PROVIDER")  # openai, azure_openai, anthropic, google, local
    llm_api_key: str | None = Field(default=None, env="LLM_API_KEY")
    llm_model: str = Field(default="gpt-4o-mini", env="LLM_MODEL")
    llm_base_url: str | None = Field(default=None, env="LLM_BASE_URL")  # For local LLMs or custom endpoints
    llm_temperature: float = Field(default=0.1, env="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=500, env="LLM_MAX_TOKENS")

    # Legacy OpenAI support (deprecated - use LLM_* settings)
    openai_api_key: str | None = Field(default=None, env="OPENAI_API_KEY")

    # Event logging settings
    event_logging_enabled: bool = Field(default=False, env="EVENT_LOGGING_ENABLED")
    nats_url: str = Field(default="nats://localhost:4222", env="NATS_URL")
    nats_stream_events: str = Field(default="events", env="NATS_STREAM_EVENTS")
    nats_consumer_group: str = Field(default="langhook_consumer", env="NATS_CONSUMER_GROUP")

    model_config = {
        "env_file": ".env.subscriptions",
        "env_file_encoding": "utf-8"
    }


def load_subscription_settings() -> SubscriptionSettings:
    """Load subscription settings from environment variables."""
    env_vars = {}

    # Read from .env.subscriptions if it exists
    env_file = ".env.subscriptions"
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()

    # Override with actual environment variables
    env_vars.update({
        'POSTGRES_DSN': os.getenv('POSTGRES_DSN', 'postgresql://langhook:langhook@localhost:5432/langhook'),
        'LLM_PROVIDER': os.getenv('LLM_PROVIDER', 'openai'),
        'LLM_API_KEY': os.getenv('LLM_API_KEY') or os.getenv('OPENAI_API_KEY'),  # Backward compatibility
        'LLM_MODEL': os.getenv('LLM_MODEL', 'gpt-4'),
        'LLM_BASE_URL': os.getenv('LLM_BASE_URL'),
        'LLM_TEMPERATURE': float(os.getenv('LLM_TEMPERATURE', '0.1')),
        'LLM_MAX_TOKENS': int(os.getenv('LLM_MAX_TOKENS', '500')),
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
        'EVENT_LOGGING_ENABLED': os.getenv('EVENT_LOGGING_ENABLED', 'false').lower() in ('true', '1', 'yes', 'on'),
        'NATS_URL': os.getenv('NATS_URL', 'nats://localhost:4222'),
        'NATS_STREAM_EVENTS': os.getenv('NATS_STREAM_EVENTS', 'events'),
        'NATS_CONSUMER_GROUP': os.getenv('NATS_CONSUMER_GROUP', 'langhook_consumer'),
    })

    return SubscriptionSettings(
        postgres_dsn=env_vars['POSTGRES_DSN'],
        llm_provider=env_vars['LLM_PROVIDER'],
        llm_api_key=env_vars.get('LLM_API_KEY'),
        llm_model=env_vars['LLM_MODEL'],
        llm_base_url=env_vars.get('LLM_BASE_URL'),
        llm_temperature=env_vars['LLM_TEMPERATURE'],
        llm_max_tokens=env_vars['LLM_MAX_TOKENS'],
        openai_api_key=env_vars.get('OPENAI_API_KEY'),
        event_logging_enabled=env_vars['EVENT_LOGGING_ENABLED'],
        nats_url=env_vars['NATS_URL'],
        nats_stream_events=env_vars['NATS_STREAM_EVENTS'],
        nats_consumer_group=env_vars['NATS_CONSUMER_GROUP'],
    )


subscription_settings = load_subscription_settings()
