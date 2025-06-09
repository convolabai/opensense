"""Event logging service for writing canonical events to PostgreSQL."""

import json
from datetime import datetime, timezone
from typing import Any, Dict

import structlog
from sqlalchemy.exc import SQLAlchemyError

from langhook.core.nats import BaseNATSConsumer
from langhook.subscriptions.config import subscription_settings
from langhook.subscriptions.database import db_service
from langhook.subscriptions.models import EventLog

logger = structlog.get_logger("langhook")


class EventLoggingService:
    """Service for logging canonical events to PostgreSQL."""

    def __init__(self) -> None:
        self.consumer: EventLoggingConsumer | None = None
        self._running = False

    async def start(self) -> None:
        """Start the event logging service."""
        if not subscription_settings.event_logging_enabled:
            logger.info("Event logging is disabled, skipping start")
            return

        logger.info("Starting event logging service")

        # Ensure event logs table exists
        db_service.create_event_logs_table()

        # Create and start consumer
        self.consumer = EventLoggingConsumer(self._log_event)
        await self.consumer.start()

        self._running = True
        logger.info("Event logging service started successfully")

    async def stop(self) -> None:
        """Stop the event logging service."""
        if not self._running:
            return

        logger.info("Stopping event logging service")
        self._running = False

        if self.consumer:
            await self.consumer.stop()

        logger.info("Event logging service stopped")

    async def run(self) -> None:
        """Run the event logging service (consume messages)."""
        if not subscription_settings.event_logging_enabled:
            logger.info("Event logging is disabled")
            return

        if not self.consumer:
            await self.start()

        try:
            await self.consumer.consume_messages()
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            await self.stop()

    async def _log_event(self, event_data: Dict[str, Any]) -> None:
        """
        Log a canonical event to PostgreSQL.

        Args:
            event_data: CloudEvent containing canonical data
        """
        try:
            # Extract CloudEvent metadata
            event_id = event_data.get("id")
            source = event_data.get("source")
            subject = event_data.get("subject", "")
            
            # Extract canonical data from CloudEvent
            canonical_data = event_data.get("data", {})
            
            if not canonical_data:
                logger.warning("No canonical data found in event", event_id=event_id)
                return

            # Extract canonical fields
            publisher = canonical_data.get("publisher")
            resource = canonical_data.get("resource", {})
            resource_type = resource.get("type")
            resource_id = str(resource.get("id", ""))
            action = canonical_data.get("action")
            
            # Parse timestamp
            timestamp_str = canonical_data.get("timestamp")
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                except ValueError:
                    timestamp = datetime.now(timezone.utc)
            else:
                timestamp = datetime.now(timezone.utc)

            # Extract raw payload if available
            raw_payload = canonical_data.get("payload")

            # Validate required fields
            if not all([event_id, source, publisher, resource_type, action]):
                logger.warning(
                    "Missing required fields for event logging",
                    event_id=event_id,
                    source=source,
                    publisher=publisher,
                    resource_type=resource_type,
                    action=action
                )
                return

            # Create event log entry
            event_log = EventLog(
                event_id=event_id,
                source=source,
                subject=subject,
                publisher=publisher,
                resource_type=resource_type,
                resource_id=resource_id,
                action=action,
                canonical_data=canonical_data,
                raw_payload=raw_payload,
                timestamp=timestamp,
            )

            # Save to database
            with db_service.get_session() as session:
                session.add(event_log)
                session.commit()

            logger.debug(
                "Event logged successfully",
                event_id=event_id,
                source=source,
                publisher=publisher,
                resource_type=resource_type,
                resource_id=resource_id,
                action=action
            )

        except SQLAlchemyError as e:
            logger.error(
                "Database error while logging event",
                event_id=event_data.get("id"),
                error=str(e),
                exc_info=True
            )
        except Exception as e:
            logger.error(
                "Unexpected error while logging event",
                event_id=event_data.get("id"),
                error=str(e),
                exc_info=True
            )


class EventLoggingConsumer(BaseNATSConsumer):
    """NATS consumer for canonical events to log to PostgreSQL."""

    def __init__(self, message_handler) -> None:
        super().__init__(
            nats_url=subscription_settings.nats_url,
            stream_name=subscription_settings.nats_stream_events,
            consumer_name=f"{subscription_settings.nats_consumer_group}_event_logger",
            filter_subject="langhook.events.>",  # Listen to all canonical events
            message_handler=message_handler,
        )


# Global event logging service instance
event_logging_service = EventLoggingService()