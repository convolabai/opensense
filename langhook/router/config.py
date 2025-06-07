"""Configuration settings for the router service (svc-router)."""

import os

from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Router service settings loaded from environment variables."""

    # Basic app settings
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # Kafka settings
    kafka_brokers: str = Field(default="localhost:19092", env="KAFKA_BROKERS")
    kafka_topic_canonical: str = Field(default="opensense.events", env="KAFKA_TOPIC_CANONICAL")
    kafka_topic_matches: str = Field(default="opensense.matches", env="KAFKA_TOPIC_MATCHES")

    # Kafka consumer settings
    kafka_consumer_group: str = Field(default="svc-router", env="KAFKA_CONSUMER_GROUP")

    # Rules engine settings
    rules_dir: str = Field(default="/app/rules", env="RULES_DIR")

    # Performance settings
    max_events_per_second: int = Field(default=5000, env="MAX_EVENTS_PER_SECOND")

    model_config = {
        "env_file": ".env.router",
        "env_file_encoding": "utf-8"
    }


def load_settings() -> Settings:
    """Load settings from environment variables."""
    env_vars = {}

    # Read from .env.router if it exists
    env_file = ".env.router"
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
        'KAFKA_TOPIC_CANONICAL': os.getenv('KAFKA_TOPIC_CANONICAL', 'opensense.events'),
        'KAFKA_TOPIC_MATCHES': os.getenv('KAFKA_TOPIC_MATCHES', 'opensense.matches'),
        'KAFKA_CONSUMER_GROUP': os.getenv('KAFKA_CONSUMER_GROUP', 'svc-router'),
        'RULES_DIR': os.getenv('RULES_DIR', '/app/rules'),
        'MAX_EVENTS_PER_SECOND': os.getenv('MAX_EVENTS_PER_SECOND', '5000'),
    })

    # Convert string values to appropriate types
    debug_val = env_vars['DEBUG'].lower() in ('true', '1', 'yes', 'on')
    max_events_per_second_val = int(env_vars['MAX_EVENTS_PER_SECOND'])

    return Settings(
        debug=debug_val,
        log_level=env_vars['LOG_LEVEL'],
        kafka_brokers=env_vars['KAFKA_BROKERS'],
        kafka_topic_canonical=env_vars['KAFKA_TOPIC_CANONICAL'],
        kafka_topic_matches=env_vars['KAFKA_TOPIC_MATCHES'],
        kafka_consumer_group=env_vars['KAFKA_CONSUMER_GROUP'],
        rules_dir=env_vars['RULES_DIR'],
        max_events_per_second=max_events_per_second_val,
    )


settings = load_settings()
