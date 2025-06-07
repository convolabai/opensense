"""Configuration settings for the canonicaliser service."""

import os

from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Application settings loaded from environment variables."""

    # Basic app settings
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # NATS settings
    nats_url: str = Field(default="nats://localhost:4222", env="NATS_URL")
    nats_stream_events: str = Field(default="events", env="NATS_STREAM_EVENTS")
    nats_consumer_group: str = Field(default="svc-map", env="NATS_CONSUMER_GROUP")

    # Mappings directory
    mappings_dir: str = Field(default="/app/mappings", env="MAPPINGS_DIR")

    # LLM settings
    openai_api_key: str | None = Field(default=None, env="OPENAI_API_KEY")
    ollama_base_url: str | None = Field(default=None, env="OLLAMA_BASE_URL")

    # Postgres settings for mapping suggestions cache
    postgres_dsn: str | None = Field(default=None, env="POSTGRES_DSN")

    # Performance settings
    max_events_per_second: int = Field(default=2000, env="MAX_EVENTS_PER_SECOND")

    model_config = {
        "env_file": ".env.map",
        "env_file_encoding": "utf-8"
    }


def load_settings() -> Settings:
    """Load settings from environment variables."""
    env_vars = {}

    # Read from .env.map if it exists
    env_file = ".env.map"
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
        'NATS_URL': os.getenv('NATS_URL', 'nats://localhost:4222'),
        'NATS_STREAM_EVENTS': os.getenv('NATS_STREAM_EVENTS', 'events'),
        'NATS_CONSUMER_GROUP': os.getenv('NATS_CONSUMER_GROUP', 'svc-map'),
        'MAPPINGS_DIR': os.getenv('MAPPINGS_DIR', '/app/mappings'),
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
        'OLLAMA_BASE_URL': os.getenv('OLLAMA_BASE_URL'),
        'POSTGRES_DSN': os.getenv('POSTGRES_DSN'),
        'MAX_EVENTS_PER_SECOND': os.getenv('MAX_EVENTS_PER_SECOND', '2000'),
    })

    # Convert string values to appropriate types
    debug_val = env_vars['DEBUG'].lower() in ('true', '1', 'yes', 'on')
    max_events_per_second_val = int(env_vars['MAX_EVENTS_PER_SECOND'])

    return Settings(
        debug=debug_val,
        log_level=env_vars['LOG_LEVEL'],
        nats_url=env_vars['NATS_URL'],
        nats_stream_events=env_vars['NATS_STREAM_EVENTS'],
        nats_consumer_group=env_vars['NATS_CONSUMER_GROUP'],
        mappings_dir=env_vars['MAPPINGS_DIR'],
        openai_api_key=env_vars.get('OPENAI_API_KEY'),
        ollama_base_url=env_vars.get('OLLAMA_BASE_URL'),
        postgres_dsn=env_vars.get('POSTGRES_DSN'),
        max_events_per_second=max_events_per_second_val,
    )


settings = load_settings()
