"""Configuration settings for the ingest gateway."""

import os

from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Application settings loaded from environment variables."""

    # Basic app settings
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # Request limits
    max_body_bytes: int = Field(default=1048576, env="MAX_BODY_BYTES")  # 1 MiB
    rate_limit: str = Field(default="200/minute", env="RATE_LIMIT")

    # NATS settings
    nats_url: str = Field(default="nats://localhost:4222", env="NATS_URL")
    nats_stream_events: str = Field(default="events", env="NATS_STREAM_EVENTS")

    # Redis settings (for rate limiting)
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")

    # HMAC secrets for different sources
    github_secret: str | None = Field(default=None, env="GITHUB_SECRET")
    stripe_secret: str | None = Field(default=None, env="STRIPE_SECRET")

    model_config = {
        "env_file": ".env.ingest",
        "env_file_encoding": "utf-8"
    }

    def get_secret(self, source: str) -> str | None:
        """Get HMAC secret for a specific source."""
        return getattr(self, f"{source.lower()}_secret", None)


# Global settings instance
def load_settings() -> Settings:
    """Load settings from environment variables."""
    env_vars = {}

    # Read from .env.ingest if it exists
    env_file = ".env.ingest"
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()

    # Override with actual environment variables
    env_vars.update({
        'DEBUG': os.getenv('DEBUG', 'false'),
        'LOG_LEVEL': os.getenv('LOG_LEVEL', 'INFO'),
        'MAX_BODY_BYTES': os.getenv('MAX_BODY_BYTES', '1048576'),
        'RATE_LIMIT': os.getenv('RATE_LIMIT', '200/minute'),
        'NATS_URL': os.getenv('NATS_URL', 'nats://localhost:4222'),
        'NATS_STREAM_EVENTS': os.getenv('NATS_STREAM_EVENTS', 'events'),
        'REDIS_URL': os.getenv('REDIS_URL', 'redis://localhost:6379'),
        'GITHUB_SECRET': os.getenv('GITHUB_SECRET'),
        'STRIPE_SECRET': os.getenv('STRIPE_SECRET'),
    })

    # Convert string values to appropriate types
    debug_val = env_vars['DEBUG'].lower() in ('true', '1', 'yes', 'on')
    max_body_bytes_val = int(env_vars['MAX_BODY_BYTES'])

    return Settings(
        debug=debug_val,
        log_level=env_vars['LOG_LEVEL'],
        max_body_bytes=max_body_bytes_val,
        rate_limit=env_vars['RATE_LIMIT'],
        nats_url=env_vars['NATS_URL'],
        nats_stream_events=env_vars['NATS_STREAM_EVENTS'],
        redis_url=env_vars['REDIS_URL'],
        github_secret=env_vars.get('GITHUB_SECRET'),
        stripe_secret=env_vars.get('STRIPE_SECRET'),
    )

settings = load_settings()
