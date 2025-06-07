"""Kafka consumer and producer for the mapping service."""

from typing import Any

import structlog

from langhook.core.kafka import BaseKafkaConsumer, BaseKafkaProducer
from langhook.map.config import settings

logger = structlog.get_logger("langhook")


class MapKafkaProducer(BaseKafkaProducer):
    """Kafka producer for sending canonical events and DLQ messages."""

    def __init__(self) -> None:
        super().__init__(settings.kafka_brokers)

    async def send_canonical_event(self, event: dict[str, Any]) -> None:
        """Send canonical event to the langhook.events topic."""
        await self.send_message(
            settings.kafka_topic_canonical,
            event,
            key=event["id"],
            log_success=True
        )
        logger.debug(
            "Canonical event sent to Kafka",
            event_id=event["id"],
            publisher=event["data"]["publisher"],
            resource_type=event["data"]["resource"]["type"],
            action=event["data"]["action"]
        )

    async def send_mapping_failure(self, failure_event: dict[str, Any]) -> None:
        """Send mapping failure to the langhook.map_fail topic."""
        try:
            await self.send_message(
                settings.kafka_topic_map_fail,
                failure_event,
                key=failure_event["id"],
                log_success=False
            )
            logger.debug(
                "Mapping failure sent to DLQ",
                event_id=failure_event["id"],
                source=failure_event["source"],
            )
        except Exception as e:
            logger.error(
                "Failed to send mapping failure to DLQ",
                event_id=failure_event["id"],
                source=failure_event["source"],
                error=str(e),
                exc_info=True,
            )
            # Don't re-raise DLQ errors to avoid infinite loops


class MapKafkaConsumer(BaseKafkaConsumer):
    """Kafka consumer for reading raw events from raw_ingest topic."""

    def __init__(self, message_handler) -> None:
        super().__init__(
            topics=[settings.kafka_topic_raw_ingest],
            brokers=settings.kafka_brokers,
            group_id=settings.kafka_consumer_group,
            message_handler=message_handler,
            auto_offset_reset="earliest"
        )


# Global producer instance
map_producer = MapKafkaProducer()
