"""Kafka producer for sending events to the event bus."""

from typing import Any

import structlog

from langhook.core.kafka import BaseKafkaProducer
from langhook.ingest.config import settings

logger = structlog.get_logger("langhook")


class KafkaEventProducer(BaseKafkaProducer):
    """Kafka producer for sending events to raw_ingest and DLQ topics."""

    def __init__(self) -> None:
        super().__init__(settings.kafka_brokers)

    async def send_event(self, event: dict[str, Any]) -> None:
        """Send event to the raw_ingest topic."""
        await self.send_message(
            settings.kafka_topic_raw_ingest,
            event,
            key=event["id"],
            log_success=True
        )
        logger.debug(
            "Event sent to raw_ingest topic",
            event_id=event["id"],
            source=event["source"],
        )

    async def send_dlq(self, dlq_event: dict[str, Any]) -> None:
        """Send malformed event to the dead letter queue."""
        try:
            await self.send_message(
                settings.kafka_topic_dlq,
                dlq_event,
                key=dlq_event["id"],
                log_success=False
            )
            logger.debug(
                "Event sent to DLQ",
                event_id=dlq_event["id"],
                source=dlq_event["source"],
                error=dlq_event["error"],
            )
        except Exception as e:
            logger.error(
                "Failed to send event to DLQ",
                event_id=dlq_event["id"],
                source=dlq_event["source"],
                error=str(e),
                exc_info=True,
            )
            # Don't re-raise DLQ errors to avoid infinite loops


# Global producer instance
kafka_producer = KafkaEventProducer()
