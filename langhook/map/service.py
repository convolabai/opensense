"""Main mapping service that processes raw events into canonical events."""

import time
from datetime import UTC, datetime
from typing import Any

import structlog

from langhook.map.cloudevents import cloud_event_wrapper
from langhook.map.kafka import MapKafkaConsumer, map_producer
from langhook.map.llm import llm_service
from langhook.map.mapper import mapping_engine
from langhook.map.metrics import metrics

logger = structlog.get_logger()


class MappingService:
    """Main service that orchestrates the mapping process."""

    def __init__(self) -> None:
        self.consumer: MapKafkaConsumer | None = None
        self._running = False

        # Legacy metrics (for backward compatibility)
        self.events_processed = 0
        self.events_mapped = 0
        self.events_failed = 0
        self.llm_invocations = 0

    async def start(self) -> None:
        """Start the mapping service."""
        logger.info("Starting OpenSense Canonicaliser", version="0.3.0")

        # Update active mappings count in metrics
        metrics.update_active_mappings(len(mapping_engine._mappings))

        # Start Kafka producer
        await map_producer.start()

        # Create and start consumer
        self.consumer = MapKafkaConsumer(self._process_raw_event)
        await self.consumer.start()

        self._running = True
        logger.info("Mapping service started successfully")

    async def stop(self) -> None:
        """Stop the mapping service."""
        logger.info("Stopping mapping service")
        self._running = False

        if self.consumer:
            await self.consumer.stop()

        await map_producer.stop()
        logger.info("Mapping service stopped")

    async def run(self) -> None:
        """Run the mapping service (consume messages)."""
        if not self.consumer:
            await self.start()

        try:
            await self.consumer.consume_messages()
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            await self.stop()

    async def _process_raw_event(self, raw_event: dict[str, Any]) -> None:
        """
        Process a single raw event from the raw_ingest topic.
        
        Args:
            raw_event: Raw event from Kafka in the format produced by svc-ingest
        """
        start_time = time.time()

        event_id = raw_event.get("id")
        source = raw_event.get("source")
        payload = raw_event.get("payload", {})

        # Record metrics
        self.events_processed += 1
        metrics.record_event_processed(source or "unknown")

        logger.debug(
            "Processing raw event",
            event_id=event_id,
            source=source,
            payload_keys=list(payload.keys()) if payload else []
        )

        try:
            # Try to apply existing mapping
            canonical_data = mapping_engine.apply_mapping(source, payload)

            if canonical_data is None:
                # No mapping available, try LLM suggestion if enabled
                if llm_service.is_available():
                    logger.info(
                        "No mapping found, attempting LLM suggestion",
                        event_id=event_id,
                        source=source
                    )

                    self.llm_invocations += 1
                    metrics.record_llm_invocation(source or "unknown")

                    # For now, just log that we would use LLM
                    # In a full implementation, we would:
                    # 1. Generate JSONata suggestion
                    # 2. Cache it in Postgres
                    # 3. Apply it to transform the event

                    await self._send_mapping_failure(
                        raw_event,
                        "No mapping available and LLM suggestion not implemented"
                    )
                    metrics.record_event_failed(source or "unknown", "no_mapping_llm_todo")
                    return
                else:
                    await self._send_mapping_failure(raw_event, "No mapping available for source")
                    metrics.record_event_failed(source or "unknown", "no_mapping")
                    return

            # Create canonical CloudEvent
            canonical_event = cloud_event_wrapper.wrap_and_validate(
                event_id=event_id,
                source=source,
                canonical_data=canonical_data,
                raw_payload=payload
            )

            # Send to canonical events topic
            await map_producer.send_canonical_event(canonical_event)

            # Record success metrics
            self.events_mapped += 1
            metrics.record_event_mapped(source or "unknown")

            # Record processing duration
            duration = time.time() - start_time
            metrics.record_mapping_duration(source or "unknown", duration)

            logger.info(
                "Event mapped successfully",
                event_id=event_id,
                source=source,
                publisher=canonical_data["publisher"],
                resource_type=canonical_data["resource"]["type"],
                resource_id=canonical_data["resource"]["id"],
                action=canonical_data["action"],
                processing_time_ms=round(duration * 1000, 2)
            )

        except Exception as e:
            self.events_failed += 1
            metrics.record_event_failed(source or "unknown", "processing_error")
            await self._send_mapping_failure(raw_event, f"Mapping error: {str(e)}")

            logger.error(
                "Failed to process raw event",
                event_id=event_id,
                source=source,
                error=str(e),
                exc_info=True
            )

    async def _send_mapping_failure(
        self,
        raw_event: dict[str, Any],
        error_message: str
    ) -> None:
        """Send mapping failure to DLQ topic."""
        failure_event = {
            "id": raw_event.get("id"),
            "timestamp": datetime.now(UTC).isoformat(),
            "source": raw_event.get("source"),
            "error": error_message,
            "payload": raw_event.get("payload", {})
        }

        await map_producer.send_mapping_failure(failure_event)
        self.events_failed += 1

    def get_metrics(self) -> dict[str, Any]:
        """Get basic metrics for monitoring."""
        return {
            "events_processed": self.events_processed,
            "events_mapped": self.events_mapped,
            "events_failed": self.events_failed,
            "llm_invocations": self.llm_invocations,
            "mapping_success_rate": (
                self.events_mapped / self.events_processed
                if self.events_processed > 0 else 0.0
            ),
            "llm_usage_rate": (
                self.llm_invocations / self.events_processed
                if self.events_processed > 0 else 0.0
            )
        }


# Global mapping service instance
mapping_service = MappingService()
