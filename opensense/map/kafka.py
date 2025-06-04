"""Kafka consumer and producer for the mapping service."""

import json
import asyncio
from typing import Any, Dict

import structlog
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from opensense.map.config import settings

logger = structlog.get_logger()


class MapKafkaProducer:
    """Kafka producer for sending canonical events and DLQ messages."""
    
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
    
    async def send_canonical_event(self, event: Dict[str, Any]) -> None:
        """Send canonical event to the opensense.events topic."""
        if not self.producer:
            await self.start()
        
        try:
            await self.producer.send_and_wait(
                settings.kafka_topic_canonical,
                value=event,
                key=event["id"].encode("utf-8"),
            )
            logger.debug(
                "Canonical event sent to Kafka",
                topic=settings.kafka_topic_canonical,
                event_id=event["id"],
                publisher=event["data"]["publisher"],
            )
        except Exception as e:
            logger.error(
                "Failed to send canonical event to Kafka",
                topic=settings.kafka_topic_canonical,
                event_id=event["id"],
                error=str(e),
                exc_info=True,
            )
            raise
    
    async def send_mapping_failure(self, failure_event: Dict[str, Any]) -> None:
        """Send mapping failure to the opensense.map_fail topic."""
        if not self.producer:
            await self.start()
        
        try:
            await self.producer.send_and_wait(
                settings.kafka_topic_map_fail,
                value=failure_event,
                key=failure_event["id"].encode("utf-8"),
            )
            logger.debug(
                "Mapping failure sent to DLQ",
                topic=settings.kafka_topic_map_fail,
                event_id=failure_event["id"],
                source=failure_event["source"],
            )
        except Exception as e:
            logger.error(
                "Failed to send mapping failure to DLQ",
                topic=settings.kafka_topic_map_fail,
                event_id=failure_event["id"],
                source=failure_event["source"],
                error=str(e),
                exc_info=True,
            )
            # Don't re-raise DLQ errors to avoid infinite loops


class MapKafkaConsumer:
    """Kafka consumer for reading raw events from raw_ingest topic."""
    
    def __init__(self, message_handler) -> None:
        self.consumer: AIOKafkaConsumer | None = None
        self.message_handler = message_handler
        self._running = False
    
    async def start(self) -> None:
        """Start the Kafka consumer."""
        if self.consumer is None:
            self.consumer = AIOKafkaConsumer(
                settings.kafka_topic_raw_ingest,
                bootstrap_servers=settings.kafka_brokers,
                group_id=settings.kafka_consumer_group,
                auto_offset_reset="earliest",
                enable_auto_commit=True,
                auto_commit_interval_ms=1000,
                value_deserializer=lambda x: json.loads(x.decode("utf-8")),
                max_poll_records=100,  # Process in batches
            )
            await self.consumer.start()
            logger.info(
                "Kafka consumer started",
                brokers=settings.kafka_brokers,
                topic=settings.kafka_topic_raw_ingest,
                group_id=settings.kafka_consumer_group,
            )
    
    async def stop(self) -> None:
        """Stop the Kafka consumer."""
        self._running = False
        if self.consumer:
            await self.consumer.stop()
            self.consumer = None
            logger.info("Kafka consumer stopped")
    
    async def consume_messages(self) -> None:
        """Consume messages from the raw_ingest topic."""
        if not self.consumer:
            await self.start()
        
        self._running = True
        logger.info("Starting message consumption")
        
        try:
            async for message in self.consumer:
                if not self._running:
                    break
                
                try:
                    await self.message_handler(message.value)
                except Exception as e:
                    logger.error(
                        "Error processing message",
                        message_key=message.key.decode("utf-8") if message.key else None,
                        error=str(e),
                        exc_info=True,
                    )
                    # Continue processing other messages
                    
        except Exception as e:
            logger.error(
                "Error in message consumption loop",
                error=str(e),
                exc_info=True,
            )
            raise


# Global producer instance
map_producer = MapKafkaProducer()