"""NATS consumer and producer for the mapping service."""

from typing import Any

import structlog
from nats.js.api import DeliverPolicy

from langhook.core.nats import BaseNATSConsumer, BaseNATSProducer
from langhook.map.config import settings

logger = structlog.get_logger("langhook")


class MapNATSProducer(BaseNATSProducer):
    """NATS producer for sending canonical events and DLQ messages."""

    def __init__(self) -> None:
        super().__init__(settings.nats_url)

    def _build_subject(self, canonical_data: dict[str, Any]) -> str:
        """
        Build NATS subject from canonical event data.

        Subject pattern: langhook.events.<publisher>.<resource_type>.<resource_id>.<action>
        """
        publisher = canonical_data.get("publisher", "unknown")
        resource = canonical_data.get("resource", {})
        resource_type = resource.get("type", "unknown")
        resource_id = str(resource.get("id", "unknown"))
        action = canonical_data.get("action", "unknown")

        # Clean up resource_id to be NATS-subject safe
        resource_id = resource_id.replace("/", "_").replace("#", "_").replace(" ", "_")

        return f"langhook.events.{publisher}.{resource_type}.{resource_id}.{action}"

    async def send_canonical_event(self, event: dict[str, Any]) -> None:
        """Send canonical event to the events stream using subject routing."""
        # Extract canonical data from the CloudEvent wrapper
        canonical_data = event.get("data", {})

        # Build subject from canonical data
        subject = self._build_subject(canonical_data)

        # Build headers with timestamp and summary
        headers = {}
        if "timestamp" in canonical_data:
            headers["ts"] = canonical_data["timestamp"]
        if "summary" in canonical_data:
            headers["su"] = canonical_data["summary"]

        await self.publish_message(
            subject,
            event,  # Send the full CloudEvent
            headers=headers,
            log_success=True
        )

        logger.debug(
            "Canonical event sent to NATS",
            subject=subject,
            event_id=event.get("id"),
            publisher=canonical_data.get("publisher"),
            resource_type=canonical_data.get("resource", {}).get("type"),
            action=canonical_data.get("action")
        )

    async def send_mapping_failure(self, failure_event: dict[str, Any]) -> None:
        """Send mapping failure to a DLQ subject."""
        # Use a special DLQ subject
        subject = f"dlq.map_fail.{failure_event.get('source', 'unknown')}.{failure_event['id']}"

        try:
            await self.publish_message(
                subject,
                failure_event,
                log_success=False
            )
            logger.debug(
                "Mapping failure sent to DLQ",
                subject=subject,
                event_id=failure_event["id"],
                source=failure_event.get("source"),
                error=failure_event.get("error"),
            )
        except Exception as e:
            logger.error(
                "Failed to send mapping failure to DLQ",
                event_id=failure_event["id"],
                source=failure_event.get("source"),
                error=str(e),
                exc_info=True,
            )


class MapNATSConsumer(BaseNATSConsumer):
    """NATS consumer for reading raw events from raw.> subjects."""

    def __init__(self, message_handler) -> None:
        super().__init__(
            nats_url=settings.nats_url,
            stream_name=settings.nats_stream_events,
            consumer_name=f"{settings.nats_consumer_group}_raw_processor",
            filter_subject="raw.>",  # Listen to all raw events
            message_handler=message_handler,
            deliver_policy=DeliverPolicy.NEW,
        )


# Global producer instance
map_producer = MapNATSProducer()
