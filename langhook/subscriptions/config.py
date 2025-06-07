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
    llm_model: str = Field(default="gpt-4", env="LLM_MODEL")
    llm_base_url: str | None = Field(default=None, env="LLM_BASE_URL")  # For local LLMs or custom endpoints
    llm_temperature: float = Field(default=0.1, env="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=500, env="LLM_MAX_TOKENS")

    # Legacy OpenAI support (deprecated - use LLM_* settings)
    openai_api_key: str | None = Field(default=None, env="OPENAI_API_KEY")

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
    )


subscription_settings = load_subscription_settings()
