"""Configuration settings for the ingest gateway."""

from typing import Optional
from pydantic import BaseModel
from langhook.core.config import app_config


class Settings(BaseModel):
    """Application settings loaded from environment variables."""
    
    # Basic app settings
    debug: bool
    log_level: str
    
    # Request limits
    max_body_bytes: int
    rate_limit: str
    
    # NATS settings
    nats_url: str
    nats_stream_events: str
    
    # Redis settings (for rate limiting)
    redis_url: str
    
    # HMAC secrets for different sources
    github_secret: Optional[str]
    stripe_secret: Optional[str]
    
    def get_secret(self, source: str) -> Optional[str]:
        """Get HMAC secret for a specific source."""
        return getattr(self, f"{source.lower()}_secret", None)


def load_settings() -> Settings:
    """Load settings from core configuration."""
    return Settings(
        debug=app_config.debug,
        log_level=app_config.log_level,
        max_body_bytes=app_config.ingest.max_body_bytes,
        rate_limit=app_config.ingest.rate_limit,
        nats_url=app_config.nats_url,
        nats_stream_events=app_config.nats_stream_events,
        redis_url=app_config.ingest.redis_url,
        github_secret=app_config.ingest.github_secret,
        stripe_secret=app_config.ingest.stripe_secret,
    )


# Global settings instance
settings = load_settings()
