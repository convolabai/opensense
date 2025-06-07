"""Configuration for subscription service."""

import os
from typing import Optional

from pydantic import BaseModel, Field


class SubscriptionSettings(BaseModel):
    """Settings for subscription management."""
    
    # Database settings
    postgres_dsn: str = Field(default="postgresql://langhook:langhook@localhost:5432/langhook", env="POSTGRES_DSN")
    
    # JWT settings
    jwt_secret: str = Field(default="dev-secret-key", env="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    
    # NLP service settings
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    
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
        'JWT_SECRET': os.getenv('JWT_SECRET', 'dev-secret-key'),
        'JWT_ALGORITHM': os.getenv('JWT_ALGORITHM', 'HS256'),
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
    })

    return SubscriptionSettings(
        postgres_dsn=env_vars['POSTGRES_DSN'],
        jwt_secret=env_vars['JWT_SECRET'],
        jwt_algorithm=env_vars['JWT_ALGORITHM'],
        openai_api_key=env_vars.get('OPENAI_API_KEY'),
    )


subscription_settings = load_subscription_settings()