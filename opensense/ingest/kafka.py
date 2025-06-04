"""Kafka producer for sending events to the event bus."""

import json
from typing import Any, Dict

import structlog
from aiokafka import AIOKafkaProducer

from opensense.ingest.config import settings

logger = structlog.get_logger()


class KafkaEventProducer:
    """Kafka producer for sending events to raw_ingest and DLQ topics."""
    
    def __init__(self) -> None:
        self.producer: AIOKafkaProducer | None = None
    
    async def start(self) -> None:
        """Start the Kafka producer."""
        if self.producer is None:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=settings.kafka_brokers,
                value_serializer=lambda x: json.dumps(x).encode("utf-8"),
                compression_type="gzip",
                max_request_size=1048576,  # 1 MiB
                request_timeout_ms=30000,  # 30 seconds
                retry_backoff_ms=100,
            )
            await self.producer.start()
            logger.info("Kafka producer started", brokers=settings.kafka_brokers)
    
    async def stop(self) -> None:
        """Stop the Kafka producer."""
        if self.producer:
            await self.producer.stop()
            self.producer = None
            logger.info("Kafka producer stopped")
    
    async def send_event(self, event: Dict[str, Any]) -> None:
        """Send event to the raw_ingest topic."""
        if not self.producer:
            await self.start()
        
        try:
            await self.producer.send_and_wait(
                settings.kafka_topic_raw_ingest,
                value=event,
                key=event["id"].encode("utf-8"),
            )
            logger.debug(
                "Event sent to Kafka",
                topic=settings.kafka_topic_raw_ingest,
                event_id=event["id"],
                source=event["source"],
            )
        except Exception as e:
            logger.error(
                "Failed to send event to Kafka",
                topic=settings.kafka_topic_raw_ingest,
                event_id=event["id"],
                source=event["source"],
                error=str(e),
                exc_info=True,
            )
            raise
    
    async def send_dlq(self, dlq_event: Dict[str, Any]) -> None:
        """Send malformed event to the dead letter queue."""
        if not self.producer:
            await self.start()
        
        try:
            await self.producer.send_and_wait(
                settings.kafka_topic_dlq,
                value=dlq_event,
                key=dlq_event["id"].encode("utf-8"),
            )
            logger.debug(
                "Event sent to DLQ",
                topic=settings.kafka_topic_dlq,
                event_id=dlq_event["id"],
                source=dlq_event["source"],
                error=dlq_event["error"],
            )
        except Exception as e:
            logger.error(
                "Failed to send event to DLQ",
                topic=settings.kafka_topic_dlq,
                event_id=dlq_event["id"],
                source=dlq_event["source"],
                error=str(e),
                exc_info=True,
            )
            # Don't re-raise DLQ errors to avoid infinite loops


# Global producer instance
kafka_producer = KafkaEventProducer()