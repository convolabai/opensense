"""Shared NATS producer and consumer base classes."""

import asyncio
import json
from collections.abc import Callable
from typing import Any

import nats
import structlog
from nats.js import JetStreamContext
from nats.js.api import ConsumerConfig, DeliverPolicy

logger = structlog.get_logger("langhook")


class BaseNATSProducer:
    """Base NATS producer with common configuration and functionality."""

    def __init__(self, nats_url: str) -> None:
        self.nats_url = nats_url
        self.nc: nats.NATS | None = None
        self.js: JetStreamContext | None = None

    async def start(self) -> None:
        """Start the NATS connection and JetStream context."""
        if self.nc is None:
            self.nc = await nats.connect(self.nats_url)
            self.js = self.nc.jetstream()
            logger.info(
                "NATS producer started",
                url=self.nats_url,
            )

    async def stop(self) -> None:
        """Stop the NATS connection."""
        if self.nc:
            await self.nc.close()
            self.nc = None
            self.js = None
            logger.info("NATS producer stopped")

    async def publish_message(
        self,
        subject: str,
        message: dict[str, Any],
        headers: dict[str, str] | None = None,
        log_success: bool = False,
    ) -> None:
        """
        Publish a message to a NATS subject.

        Args:
            subject: NATS subject to publish to
            message: Message data to serialize as JSON
            headers: Optional message headers
            log_success: Whether to log successful sends
        """
        if not self.js:
            await self.start()

        try:
            # Serialize message to JSON bytes
            message_bytes = json.dumps(message).encode('utf-8')

            # Publish to JetStream
            await self.js.publish(
                subject,
                message_bytes,
                headers=headers,
            )

            if log_success:
                logger.debug(
                    "Message published to NATS",
                    subject=subject,
                    headers=headers,
                )
        except Exception as e:
            logger.error(
                "Failed to publish message to NATS",
                subject=subject,
                headers=headers,
                error=str(e),
                exc_info=True,
            )
            raise


class BaseNATSConsumer:
    """Base NATS consumer with common configuration."""

    def __init__(
        self,
        nats_url: str,
        stream_name: str,
        consumer_name: str,
        filter_subject: str,
        message_handler: Callable[[dict[str, Any]], Any],
        deliver_policy: DeliverPolicy = DeliverPolicy.NEW,
    ) -> None:
        self.nats_url = nats_url
        self.stream_name = stream_name
        self.consumer_name = consumer_name
        self.filter_subject = filter_subject
        self.message_handler = message_handler
        self.deliver_policy = deliver_policy
        self.nc: nats.NATS | None = None
        self.js: JetStreamContext | None = None
        self._running = False
        self._subscription = None

    async def start(self) -> None:
        """Start the NATS consumer."""
        if self.nc is None:
            logger.info(
                "Starting NATS consumer",
                url=self.nats_url,
                stream=self.stream_name,
                consumer=self.consumer_name,
                filter_subject=self.filter_subject,
                deliver_policy=self.deliver_policy,
            )
            self.nc = await nats.connect(self.nats_url)
            self.js = self.nc.jetstream()

            # Create consumer if it doesn't exist
            consumer_config = ConsumerConfig(
                name=self.consumer_name,
                deliver_policy=self.deliver_policy,
                filter_subject=self.filter_subject,
            )

            try:
                await self.js.add_consumer(self.stream_name, consumer_config)
                logger.info(
                    "Created NATS consumer",
                    stream=self.stream_name,
                    consumer=self.consumer_name,
                    filter_subject=self.filter_subject,
                )
            except Exception as e:
                if "consumer name already in use" in str(e).lower():
                    logger.info(
                        "NATS consumer already exists",
                        stream=self.stream_name,
                        consumer=self.consumer_name,
                    )
                else:
                    logger.error(
                        "Failed to create NATS consumer",
                        stream=self.stream_name,
                        consumer=self.consumer_name,
                        error=str(e),
                    )
                    raise

            logger.info(
                "NATS consumer started",
                url=self.nats_url,
                stream=self.stream_name,
                consumer=self.consumer_name,
                filter_subject=self.filter_subject,
            )

    async def stop(self) -> None:
        """Stop the NATS consumer."""
        self._running = False
        if self._subscription:
            await self._subscription.unsubscribe()
            self._subscription = None
        if self.nc:
            await self.nc.close()
            self.nc = None
            self.js = None
            logger.info("NATS consumer stopped")

    async def consume_messages(self) -> None:
        """Consume messages from the NATS stream."""
        if not self.js:
            await self.start()

        self._running = True
        logger.info("Starting message consumption")

        try:
            # Subscribe to the consumer
            self._subscription = await self.js.pull_subscribe(
                self.filter_subject,
                durable=self.consumer_name,
                stream=self.stream_name,
            )

            while self._running:
                try:
                    # Fetch messages in batches
                    messages = await self._subscription.fetch(batch=10, timeout=1.0)

                    for msg in messages:
                        try:
                            # Parse JSON message
                            message_data = json.loads(msg.data.decode('utf-8'))

                            # Process message
                            await self.message_handler(message_data)

                            # Acknowledge message
                            await msg.ack()

                        except Exception as e:
                            logger.error(
                                "Error processing message",
                                subject=msg.subject,
                                error=str(e),
                                exc_info=True,
                            )
                            # NAK the message to retry later
                            await msg.nak()

                except TimeoutError:
                    # No messages available, continue loop
                    continue
                except Exception as e:
                    logger.error(
                        "Error fetching messages",
                        error=str(e),
                        exc_info=True,
                    )

                    # Wait a bit before retrying
                    await asyncio.sleep(1.0)

        except Exception as e:
            logger.error(
                "Error in message consumption loop",
                error=str(e),
                exc_info=True,
            )
            raise
