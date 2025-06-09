"""Configuration settings for the router service (svc-router)."""

from typing import Optional
from pydantic import BaseModel
from langhook.core.config import app_config


class Settings(BaseModel):
    """Router service settings loaded from environment variables."""

    # Basic app settings
    debug: bool
    log_level: str

    # Kafka settings
    kafka_brokers: str
    kafka_topic_canonical: str
    kafka_topic_matches: str

    # Kafka consumer settings
    kafka_consumer_group: str

    # Rules engine settings
    rules_dir: str

    # Performance settings
    max_events_per_second: int


def load_settings() -> Settings:
    """Load settings from core configuration."""
    return Settings(
        debug=app_config.debug,
        log_level=app_config.log_level,
        kafka_brokers=app_config.router.kafka_brokers,
        kafka_topic_canonical=app_config.router.kafka_topic_canonical,
        kafka_topic_matches=app_config.router.kafka_topic_matches,
        kafka_consumer_group=app_config.router.kafka_consumer_group,
        rules_dir=app_config.router.rules_dir,
        max_events_per_second=app_config.router.max_events_per_second,
    )


# Global settings instance
settings = load_settings()
