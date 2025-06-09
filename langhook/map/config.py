"""Configuration settings for the canonicaliser service."""


from pydantic import BaseModel

from langhook.core.config import app_config


class Settings(BaseModel):
    """Application settings loaded from environment variables."""

    # Basic app settings
    debug: bool
    log_level: str

    # NATS settings
    nats_url: str
    nats_stream_events: str
    nats_consumer_group: str

    # Mappings directory
    mappings_dir: str

    # LLM settings
    openai_api_key: str | None
    ollama_base_url: str | None

    # Postgres settings for mapping suggestions cache
    postgres_dsn: str | None

    # Performance settings
    max_events_per_second: int

    # Prometheus settings
    prometheus_pushgateway_url: str | None
    prometheus_job_name: str
    prometheus_push_interval: int


def load_settings() -> Settings:
    """Load settings from core configuration."""
    return Settings(
        debug=app_config.debug,
        log_level=app_config.log_level,
        nats_url=app_config.nats_url,
        nats_stream_events=app_config.nats_stream_events,
        nats_consumer_group=app_config.map.nats_consumer_group,
        mappings_dir=app_config.map.mappings_dir,
        openai_api_key=app_config.openai_api_key,
        ollama_base_url=app_config.map.ollama_base_url,
        postgres_dsn=app_config.postgres_dsn,
        max_events_per_second=app_config.map.max_events_per_second,
        prometheus_pushgateway_url=app_config.map.prometheus_pushgateway_url,
        prometheus_job_name=app_config.map.prometheus_job_name,
        prometheus_push_interval=app_config.map.prometheus_push_interval,
    )


# Global settings instance
settings = load_settings()
