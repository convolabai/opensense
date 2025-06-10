"""DLQ logging service for writing failed events to PostgreSQL."""

import json
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy.exc import SQLAlchemyError

from langhook.core.nats import BaseNATSConsumer
from langhook.subscriptions.config import subscription_settings
from langhook.subscriptions.database import db_service
from langhook.subscriptions.models import EventLog

logger = structlog.get_logger("langhook")


class DLQLoggingService:
    """Service for logging DLQ events to PostgreSQL."""

    def __init__(self) -> None:
        self.consumer: DLQLoggingConsumer | None = None
        self._running = False

    async def start(self) -> None:
        """Start the DLQ logging service."""
        if not subscription_settings.event_logging_enabled:
            logger.info("Event logging is disabled, skipping DLQ logging start")
            return

        logger.info("Starting DLQ logging service")

        # Ensure event logs table exists
        db_service.create_event_logs_table()

        # Create and start consumer
        self.consumer = DLQLoggingConsumer(self._log_dlq_event)
        await self.consumer.start()

        self._running = True
        logger.info("DLQ logging service started successfully")

    async def stop(self) -> None:
        """Stop the DLQ logging service."""
        if not self._running:
            return

        logger.info("Stopping DLQ logging service")
        self._running = False

        if self.consumer:
            await self.consumer.stop()

        logger.info("DLQ logging service stopped")

    async def run(self) -> None:
        """Run the DLQ logging service (consume messages)."""
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

    async def _log_dlq_event(self, dlq_data: dict[str, Any]) -> None:
        """
        Log a DLQ event to PostgreSQL.

        Args:
            dlq_data: DLQ event data containing error information
        """
        try:
            # Extract DLQ metadata
            event_id = dlq_data.get("id")
            source = dlq_data.get("source", "unknown")
            error_msg = dlq_data.get("error", "Unknown error")
            timestamp_str = dlq_data.get("timestamp")
            headers = dlq_data.get("headers", {})
            raw_payload_str = dlq_data.get("payload", "")

            if not event_id:
                logger.warning("No event ID found in DLQ message", dlq_data=dlq_data)
                return

            # Parse timestamp
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                except ValueError:
                    timestamp = datetime.now(UTC)
            else:
                timestamp = datetime.now(UTC)

            # Try to parse the raw payload as JSON, if it fails keep as string
            try:
                raw_payload = json.loads(raw_payload_str) if raw_payload_str else None
            except (json.JSONDecodeError, TypeError):
                raw_payload = {"raw_text": raw_payload_str} if raw_payload_str else None

            # Create error canonical data structure
            error_canonical_data = {
                "error": True,
                "error_message": error_msg,
                "error_type": "dlq_processing_failed",
                "publisher": source,
                "resource": {
                    "type": "webhook_failure",
                    "id": event_id
                },
                "action": "failed",
                "timestamp": timestamp_str or timestamp.isoformat(),
                "summary": f"Processing failed: {error_msg}",
                "headers": headers,
                "payload": raw_payload
            }

            # Create event log entry with error structure
            event_log = EventLog(
                event_id=event_id,
                source=source,
                subject=f"dlq.{source}.{event_id}",
                publisher=source,
                resource_type="webhook_failure",
                resource_id=event_id,
                action="failed",
                canonical_data=error_canonical_data,
                raw_payload=raw_payload,
                timestamp=timestamp,
            )

            # Save to database
            with db_service.get_session() as session:
                session.add(event_log)
                session.commit()

            logger.info(
                "DLQ event logged successfully",
                event_id=event_id,
                source=source,
                error=error_msg
            )

        except SQLAlchemyError as e:
            logger.error(
                "Database error while logging DLQ event",
                event_id=dlq_data.get("id"),
                error=str(e),
                exc_info=True
            )
        except Exception as e:
            logger.error(
                "Unexpected error while logging DLQ event",
                event_id=dlq_data.get("id"),
                error=str(e),
                exc_info=True
            )


class DLQLoggingConsumer(BaseNATSConsumer):
    """NATS consumer for DLQ events to log to PostgreSQL."""

    def __init__(self, message_handler) -> None:
        super().__init__(
            nats_url=subscription_settings.nats_url,
            stream_name=subscription_settings.nats_stream_events,
            consumer_name=f"{subscription_settings.nats_consumer_group}_dlq_logger",
            filter_subject="dlq.>",  # Listen to all DLQ events
            message_handler=message_handler,
        )


# Global DLQ logging service instance
dlq_logging_service = DLQLoggingService()
