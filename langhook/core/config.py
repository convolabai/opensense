"""Consolidated configuration for all LangHook services."""

import os
from typing import Optional

from pydantic import BaseModel, Field


class IngestSettings(BaseModel):
    """Configuration for the ingest service."""
    
    # Request limits
    max_body_bytes: int = Field(default=1048576, env="MAX_BODY_BYTES")  # 1 MiB
    rate_limit: str = Field(default="200/minute", env="RATE_LIMIT")
    
    # Redis settings (for rate limiting)
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    
    # HMAC secrets for different sources
    github_secret: Optional[str] = Field(default=None, env="GITHUB_SECRET")
    stripe_secret: Optional[str] = Field(default=None, env="STRIPE_SECRET")
    
    def get_secret(self, source: str) -> Optional[str]:
        """Get HMAC secret for a specific source."""
        return getattr(self, f"{source.lower()}_secret", None)


class MapSettings(BaseModel):
    """Configuration for the mapping service."""
    
    # NATS consumer settings
    nats_consumer_group: str = Field(default="svc-map", env="NATS_CONSUMER_GROUP")
    
    # Mappings directory
    mappings_dir: str = Field(default="/app/mappings", env="MAPPINGS_DIR")
    
    # LLM settings
    ollama_base_url: Optional[str] = Field(default=None, env="OLLAMA_BASE_URL")
    
    # Performance settings
    max_events_per_second: int = Field(default=2000, env="MAX_EVENTS_PER_SECOND")
    
    # Prometheus settings
    prometheus_pushgateway_url: Optional[str] = Field(default=None, env="PROMETHEUS_PUSHGATEWAY_URL")
    prometheus_job_name: str = Field(default="langhook-map", env="PROMETHEUS_JOB_NAME")
    prometheus_push_interval: int = Field(default=30, env="PROMETHEUS_PUSH_INTERVAL")


class SubscriptionSettings(BaseModel):
    """Configuration for the subscription service."""
    
    # LLM service settings
    llm_provider: str = Field(default="openai", env="LLM_PROVIDER")  # openai, azure_openai, anthropic, google, local
    llm_api_key: Optional[str] = Field(default=None, env="LLM_API_KEY")
    llm_model: str = Field(default="gpt-4o-mini", env="LLM_MODEL")
    llm_base_url: Optional[str] = Field(default=None, env="LLM_BASE_URL")  # For local LLMs or custom endpoints
    llm_temperature: float = Field(default=0.1, env="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=500, env="LLM_MAX_TOKENS")
    
    # Event logging settings
    event_logging_enabled: bool = Field(default=False, env="EVENT_LOGGING_ENABLED")
    nats_consumer_group: str = Field(default="langhook_consumer", env="NATS_CONSUMER_GROUP")
    
    # LLM Gate settings - simplified
    # Gate configuration is now handled per-subscription


class RouterSettings(BaseModel):
    """Configuration for the router service."""
    
    # Kafka settings
    kafka_brokers: str = Field(default="localhost:19092", env="KAFKA_BROKERS")
    kafka_topic_canonical: str = Field(default="langhook.events", env="KAFKA_TOPIC_CANONICAL")
    kafka_topic_matches: str = Field(default="langhook.matches", env="KAFKA_TOPIC_MATCHES")
    
    # Kafka consumer settings
    kafka_consumer_group: str = Field(default="svc-router", env="KAFKA_CONSUMER_GROUP")
    
    # Rules engine settings
    rules_dir: str = Field(default="/app/rules", env="RULES_DIR")
    
    # Performance settings
    max_events_per_second: int = Field(default=5000, env="MAX_EVENTS_PER_SECOND")


class AppConfig(BaseModel):
    """Consolidated application configuration for all LangHook services."""
    
    # Basic app settings (common to all services)
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Server path configuration for reverse proxy deployments
    server_path: str = Field(default="", env="SERVER_PATH")
    
    # NATS settings (common to most services)
    nats_url: str = Field(default="nats://localhost:4222", env="NATS_URL")
    nats_stream_events: str = Field(default="events", env="NATS_STREAM_EVENTS")
    
    # Database settings (common to map and subscription services)
    postgres_dsn: Optional[str] = Field(default=None, env="POSTGRES_DSN")
    
    # LLM settings (common to map and subscription services)
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    
    # Service-specific settings
    ingest: IngestSettings = Field(default_factory=IngestSettings)
    map: MapSettings = Field(default_factory=MapSettings)
    subscriptions: SubscriptionSettings = Field(default_factory=SubscriptionSettings)
    router: RouterSettings = Field(default_factory=RouterSettings)
    
    model_config = {
        "env_file": [".env", ".env.local"],
        "env_file_encoding": "utf-8"
    }


def load_app_config(reload: bool = False) -> AppConfig:
    """Load application configuration from environment variables.
    
    Args:
        reload: If True, force reload the configuration even if cached.
    """
    env_vars = {}
    
    # Read from various .env files if they exist
    env_files = [".env", ".env.local", ".env.ingest", ".env.map", ".env.subscriptions", ".env.router"]
    
    for env_file in env_files:
        if os.path.exists(env_file):
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
    
    # Override with actual environment variables
    env_vars.update({
        # Basic app settings
        'DEBUG': os.getenv('DEBUG', 'false'),
        'LOG_LEVEL': os.getenv('LOG_LEVEL', 'INFO'),
        'SERVER_PATH': os.getenv('SERVER_PATH', ''),
        
        # NATS settings
        'NATS_URL': os.getenv('NATS_URL', 'nats://localhost:4222'),
        'NATS_STREAM_EVENTS': os.getenv('NATS_STREAM_EVENTS', 'events'),
        
        # Database settings
        'POSTGRES_DSN': os.getenv('POSTGRES_DSN'),
        
        # LLM settings
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
        
        # Ingest settings
        'MAX_BODY_BYTES': os.getenv('MAX_BODY_BYTES', '1048576'),
        'RATE_LIMIT': os.getenv('RATE_LIMIT', '200/minute'),
        'REDIS_URL': os.getenv('REDIS_URL', 'redis://localhost:6379'),
        'GITHUB_SECRET': os.getenv('GITHUB_SECRET'),
        'STRIPE_SECRET': os.getenv('STRIPE_SECRET'),
        
        # Map settings
        'NATS_CONSUMER_GROUP': os.getenv('NATS_CONSUMER_GROUP', 'svc-map'),
        'MAPPINGS_DIR': os.getenv('MAPPINGS_DIR', '/app/mappings'),
        'OLLAMA_BASE_URL': os.getenv('OLLAMA_BASE_URL'),
        'MAX_EVENTS_PER_SECOND': os.getenv('MAX_EVENTS_PER_SECOND', '2000'),
        'PROMETHEUS_PUSHGATEWAY_URL': os.getenv('PROMETHEUS_PUSHGATEWAY_URL'),
        'PROMETHEUS_JOB_NAME': os.getenv('PROMETHEUS_JOB_NAME', 'langhook-map'),
        'PROMETHEUS_PUSH_INTERVAL': os.getenv('PROMETHEUS_PUSH_INTERVAL', '30'),
        
        # Subscription settings
        'LLM_PROVIDER': os.getenv('LLM_PROVIDER', 'openai'),
        'LLM_API_KEY': os.getenv('LLM_API_KEY') or os.getenv('OPENAI_API_KEY'),
        'LLM_MODEL': os.getenv('LLM_MODEL', 'gpt-4o-mini'),
        'LLM_BASE_URL': os.getenv('LLM_BASE_URL'),
        'LLM_TEMPERATURE': float(os.getenv('LLM_TEMPERATURE', '0.1')),
        'LLM_MAX_TOKENS': int(os.getenv('LLM_MAX_TOKENS', '500')),
        'EVENT_LOGGING_ENABLED': os.getenv('EVENT_LOGGING_ENABLED', 'false').lower() in ('true', '1', 'yes', 'on'),
        
        # Router settings
        'KAFKA_BROKERS': os.getenv('KAFKA_BROKERS', 'localhost:19092'),
        'KAFKA_TOPIC_CANONICAL': os.getenv('KAFKA_TOPIC_CANONICAL', 'langhook.events'),
        'KAFKA_TOPIC_MATCHES': os.getenv('KAFKA_TOPIC_MATCHES', 'langhook.matches'),
        'RULES_DIR': os.getenv('RULES_DIR', '/app/rules'),
    })
    
    # Convert string values to appropriate types
    debug_val = env_vars['DEBUG'].lower() in ('true', '1', 'yes', 'on')
    max_body_bytes_val = int(env_vars['MAX_BODY_BYTES'])
    max_events_per_second_val = int(env_vars['MAX_EVENTS_PER_SECOND'])
    prometheus_push_interval_val = int(env_vars['PROMETHEUS_PUSH_INTERVAL'])
    
    # Handle service-specific consumer groups
    map_consumer_group = os.getenv('NATS_CONSUMER_GROUP', 'svc-map')
    subscription_consumer_group = os.getenv('NATS_CONSUMER_GROUP', 'langhook_consumer')
    router_consumer_group = os.getenv('KAFKA_CONSUMER_GROUP', 'svc-router')
    router_max_events = int(os.getenv('MAX_EVENTS_PER_SECOND', '5000'))
    
    return AppConfig(
        debug=debug_val,
        log_level=env_vars['LOG_LEVEL'],
        server_path=env_vars['SERVER_PATH'],
        nats_url=env_vars['NATS_URL'],
        nats_stream_events=env_vars['NATS_STREAM_EVENTS'],
        postgres_dsn=env_vars.get('POSTGRES_DSN'),
        openai_api_key=env_vars.get('OPENAI_API_KEY'),
        ingest=IngestSettings(
            max_body_bytes=max_body_bytes_val,
            rate_limit=env_vars['RATE_LIMIT'],
            redis_url=env_vars['REDIS_URL'],
            github_secret=env_vars.get('GITHUB_SECRET'),
            stripe_secret=env_vars.get('STRIPE_SECRET'),
        ),
        map=MapSettings(
            nats_consumer_group=map_consumer_group,
            mappings_dir=env_vars['MAPPINGS_DIR'],
            ollama_base_url=env_vars.get('OLLAMA_BASE_URL'),
            max_events_per_second=max_events_per_second_val,
            prometheus_pushgateway_url=env_vars.get('PROMETHEUS_PUSHGATEWAY_URL'),
            prometheus_job_name=env_vars['PROMETHEUS_JOB_NAME'],
            prometheus_push_interval=prometheus_push_interval_val,
        ),
        subscriptions=SubscriptionSettings(
            llm_provider=env_vars['LLM_PROVIDER'],
            llm_api_key=env_vars.get('LLM_API_KEY'),
            llm_model=env_vars['LLM_MODEL'],
            llm_base_url=env_vars.get('LLM_BASE_URL'),
            llm_temperature=env_vars['LLM_TEMPERATURE'],
            llm_max_tokens=env_vars['LLM_MAX_TOKENS'],
            event_logging_enabled=env_vars['EVENT_LOGGING_ENABLED'],
            nats_consumer_group=subscription_consumer_group,
        ),
        router=RouterSettings(
            kafka_brokers=env_vars['KAFKA_BROKERS'],
            kafka_topic_canonical=env_vars['KAFKA_TOPIC_CANONICAL'],
            kafka_topic_matches=env_vars['KAFKA_TOPIC_MATCHES'],
            kafka_consumer_group=router_consumer_group,
            rules_dir=env_vars['RULES_DIR'],
            max_events_per_second=router_max_events,
        ),
    )


# Global app configuration instance
app_config = load_app_config()