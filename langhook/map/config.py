"""Configuration settings for the canonicaliser service."""

import os

from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Application settings loaded from environment variables."""

    # Basic app settings
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # Kafka settings
    kafka_brokers: str = Field(default="localhost:19092", env="KAFKA_BROKERS")
    kafka_topic_raw_ingest: str = Field(default="raw_ingest", env="KAFKA_TOPIC_RAW_INGEST")
    kafka_topic_canonical: str = Field(default="langhook.events", env="KAFKA_TOPIC_CANONICAL")
    kafka_topic_map_fail: str = Field(default="langhook.map_fail", env="KAFKA_TOPIC_MAP_FAIL")

    # Kafka consumer settings
    kafka_consumer_group: str = Field(default="svc-map", env="KAFKA_CONSUMER_GROUP")

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
        'KAFKA_BROKERS': os.getenv('KAFKA_BROKERS', 'localhost:19092'),
        'KAFKA_TOPIC_RAW_INGEST': os.getenv('KAFKA_TOPIC_RAW_INGEST', 'raw_ingest'),
        'KAFKA_TOPIC_CANONICAL': os.getenv('KAFKA_TOPIC_CANONICAL', 'langhook.events'),
        'KAFKA_TOPIC_MAP_FAIL': os.getenv('KAFKA_TOPIC_MAP_FAIL', 'langhook.map_fail'),
        'KAFKA_CONSUMER_GROUP': os.getenv('KAFKA_CONSUMER_GROUP', 'svc-map'),
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
        kafka_brokers=env_vars['KAFKA_BROKERS'],
        kafka_topic_raw_ingest=env_vars['KAFKA_TOPIC_RAW_INGEST'],
        kafka_topic_canonical=env_vars['KAFKA_TOPIC_CANONICAL'],
        kafka_topic_map_fail=env_vars['KAFKA_TOPIC_MAP_FAIL'],
        kafka_consumer_group=env_vars['KAFKA_CONSUMER_GROUP'],
        mappings_dir=env_vars['MAPPINGS_DIR'],
        openai_api_key=env_vars.get('OPENAI_API_KEY'),
        ollama_base_url=env_vars.get('OLLAMA_BASE_URL'),
        postgres_dsn=env_vars.get('POSTGRES_DSN'),
        max_events_per_second=max_events_per_second_val,
    )


settings = load_settings()
