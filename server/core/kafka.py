"""Shared Kafka producer and consumer base classes."""

import json
from typing import Any

import structlog
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

logger = structlog.get_logger("langhook")


class BaseKafkaProducer:
    """Base Kafka producer with common configuration and functionality."""

    def __init__(self, brokers: list[str]) -> None:
        self.brokers = brokers
        self.producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        """Start the Kafka producer."""
        if self.producer is None:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.brokers,
                value_serializer=lambda x: json.dumps(x).encode("utf-8"),
                compression_type="gzip",
                max_request_size=1048576,  # 1 MiB
                request_timeout_ms=30000,  # 30 seconds
                retry_backoff_ms=100,
            )
            await self.producer.start()
            logger.info("Kafka producer started", brokers=self.brokers)

    async def stop(self) -> None:
        """Stop the Kafka producer."""
        if self.producer:
            await self.producer.stop()
            self.producer = None
            logger.info("Kafka producer stopped")

    async def send_message(
        self,
        topic: str,
        message: dict[str, Any],
        key: str | None = None,
        log_success: bool = True
    ) -> None:
        """Send a message to a Kafka topic."""
        if not self.producer:
            await self.start()

        try:
            message_key = key.encode("utf-8") if key else None
            await self.producer.send_and_wait(
                topic,
                value=message,
                key=message_key,
            )
            if log_success:
                logger.debug(
                    "Message sent to Kafka",
                    topic=topic,
                    key=key,
                )
        except Exception as e:
            logger.error(
                "Failed to send message to Kafka",
                topic=topic,
                key=key,
                error=str(e),
                exc_info=True,
            )
            raise


class BaseKafkaConsumer:
    """Base Kafka consumer with common configuration."""

    def __init__(
        self,
        topics: list[str],
        brokers: list[str],
        group_id: str,
        message_handler,
        auto_offset_reset: str = "earliest"
    ) -> None:
        self.topics = topics
        self.brokers = brokers
        self.group_id = group_id
        self.message_handler = message_handler
        self.auto_offset_reset = auto_offset_reset
        self.consumer: AIOKafkaConsumer | None = None
        self._running = False

    async def start(self) -> None:
        """Start the Kafka consumer."""
        if self.consumer is None:
            self.consumer = AIOKafkaConsumer(
                *self.topics,
                bootstrap_servers=self.brokers,
                group_id=self.group_id,
                auto_offset_reset=self.auto_offset_reset,
                enable_auto_commit=True,
                auto_commit_interval_ms=1000,
                value_deserializer=lambda x: json.loads(x.decode("utf-8")),
                max_poll_records=100,  # Process in batches
            )
            await self.consumer.start()
            logger.info(
                "Kafka consumer started",
                brokers=self.brokers,
                topics=self.topics,
                group_id=self.group_id,
            )

    async def stop(self) -> None:
        """Stop the Kafka consumer."""
        self._running = False
        if self.consumer:
            await self.consumer.stop()
            self.consumer = None
            logger.info("Kafka consumer stopped")

    async def consume_messages(self) -> None:
        """Consume messages from the subscribed topics."""
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
                        topic=message.topic,
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
