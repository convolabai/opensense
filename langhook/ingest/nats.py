"""NATS producer for sending events to the event bus."""

from typing import Any

import structlog

from langhook.core.nats import BaseNATSProducer
from langhook.ingest.config import settings

logger = structlog.get_logger("langhook")


class NATSEventProducer(BaseNATSProducer):
    """NATS producer for publishing events to JetStream."""

    def __init__(self) -> None:
        super().__init__(settings.nats_url)

    def _build_subject(self, canonical_data: dict[str, Any]) -> str:
        """
        Build NATS subject from canonical event data.
        
        Subject pattern: langhook.events.<publisher>.<resource_type>.<resource_id>.<action>
        
        Args:
            canonical_data: Canonical event data with publisher, resource, action
            
        Returns:
            NATS subject string
        """
        publisher = canonical_data.get("publisher", "unknown")
        resource = canonical_data.get("resource", {})
        resource_type = resource.get("type", "unknown")
        resource_id = str(resource.get("id", "unknown"))
        action = canonical_data.get("action", "unknown")

        # Clean up resource_id to be NATS-subject safe
        # Replace any problematic characters with underscores
        resource_id = resource_id.replace("/", "_").replace("#", "_").replace(" ", "_")

        return f"langhook.events.{publisher}.{resource_type}.{resource_id}.{action}"

    async def send_canonical_event(self, canonical_data: dict[str, Any]) -> None:
        """
        Send canonical event to the events stream using subject routing.
        
        Args:
            canonical_data: Canonical event data to publish
        """
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
            canonical_data,
            headers=headers,
            log_success=True
        )

        logger.debug(
            "Canonical event published to NATS",
            subject=subject,
            publisher=canonical_data.get("publisher"),
            resource_type=canonical_data.get("resource", {}).get("type"),
            resource_id=canonical_data.get("resource", {}).get("id"),
            action=canonical_data.get("action"),
        )

    async def send_raw_event(self, event: dict[str, Any]) -> None:
        """
        Send raw ingest event to a processing subject.
        For now, we'll send these to a special subject for the mapper service.
        
        Args:
            event: Raw event data from ingest
        """
        # Use a special subject for raw events that need processing
        subject = f"raw.{event.get('source', 'unknown')}.{event['id']}"

        await self.publish_message(
            subject,
            event,
            log_success=True
        )

        logger.debug(
            "Raw event published to NATS for processing",
            subject=subject,
            event_id=event["id"],
            source=event.get("source"),
        )

    async def send_dlq(self, dlq_event: dict[str, Any]) -> None:
        """
        Send malformed event to the dead letter queue subject.
        
        Args:
            dlq_event: DLQ event data
        """
        # Use a special DLQ subject
        subject = f"dlq.{dlq_event.get('source', 'unknown')}.{dlq_event['id']}"

        try:
            await self.publish_message(
                subject,
                dlq_event,
                log_success=False
            )
            logger.debug(
                "Event sent to DLQ",
                subject=subject,
                event_id=dlq_event["id"],
                source=dlq_event.get("source"),
                error=dlq_event.get("error"),
            )
        except Exception as e:
            logger.error(
                "Failed to send event to DLQ",
                event_id=dlq_event["id"],
                source=dlq_event.get("source"),
                error=str(e),
                exc_info=True,
            )
            # Don't re-raise DLQ errors to avoid infinite loops


# Global producer instance
nats_producer = NATSEventProducer()
