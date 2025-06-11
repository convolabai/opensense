"""Main mapping service that processes raw events into canonical events."""

import time
from datetime import UTC, datetime
from typing import Any

import structlog

from langhook.map.cloudevents import cloud_event_wrapper
from langhook.map.config import settings
from langhook.map.llm import LLMSuggestionService
from langhook.map.mapper import mapping_engine
from langhook.map.metrics import metrics
from langhook.map.nats import MapNATSConsumer, map_producer
from langhook.subscriptions.schema_registry import schema_registry_service

logger = structlog.get_logger("langhook")


class MappingService:
    """Main service that orchestrates the mapping process."""

    def __init__(self) -> None:
        self.consumer: MapNATSConsumer | None = None
        self._running = False

        # Initialize LLM service - will fail fast if not properly configured
        self.llm_service = LLMSuggestionService()

        # Legacy metrics (for backward compatibility)
        self.events_processed = 0
        self.events_mapped = 0
        self.events_failed = 0
        self.llm_invocations = 0

    async def start(self) -> None:
        """Start the mapping service."""
        logger.info("Starting LangHook Canonicaliser", version="0.3.0")

        # Configure Prometheus push gateway if enabled
        if settings.prometheus_pushgateway_url:
            metrics.configure_push_gateway(
                settings.prometheus_pushgateway_url,
                settings.prometheus_job_name,
                settings.prometheus_push_interval
            )
            await metrics.start_push_task()

        # No file-based mappings to count anymore
        metrics.update_active_mappings(0)

        # Start NATS producer
        await map_producer.start()

        # Create and start consumer
        self.consumer = MapNATSConsumer(self._process_raw_event)
        await self.consumer.start()

        self._running = True
        logger.info("Mapping service started successfully")

    async def stop(self) -> None:
        """Stop the mapping service."""
        logger.info("Stopping mapping service")
        self._running = False

        # Stop metrics push task
        await metrics.stop_push_task()

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
            # Try to apply existing mapping first (fingerprint or file-based)
            canonical_data = await mapping_engine.apply_mapping(source, payload)

            if canonical_data is None:
                # No mapping available, use LLM to generate JSONata expression directly
                logger.info(
                    "No mapping found, using LLM to generate JSONata expression",
                    event_id=event_id,
                    source=source
                )

                self.llm_invocations += 1
                metrics.record_llm_invocation(source or "unknown")

                # Generate JSONata expression with event field using LLM
                mapping_result = await self.llm_service.generate_jsonata_mapping_with_event_field(source, payload)

                if mapping_result is None:
                    # include LLM response detail in error message
                    error_detail = getattr(self.llm_service, 'get_last_response', lambda: 'No response')()
                    await self._send_mapping_failure(
                        raw_event,
                        f"LLM failed to generate valid JSONata expression with event field: {error_detail}"
                    )
                    metrics.record_event_failed(source or "unknown", "llm_jsonata_generation_failed")
                    return

                jsonata_expr, event_field_expr = mapping_result

                # Apply the generated JSONata expression
                canonical_data = await mapping_engine._apply_jsonata_mapping(jsonata_expr, payload, source)

                if canonical_data is None:
                    # include the expression in the error message
                    await self._send_mapping_failure(
                        raw_event,
                        f"Generated JSONata expression '{jsonata_expr}' failed to produce valid canonical data"
                    )
                    metrics.record_event_failed(source or "unknown", "jsonata_expression_invalid")
                    return

                # Store the generated JSONata expression with event field for future use
                try:
                    await mapping_engine.store_jsonata_mapping_with_event_field(source, payload, jsonata_expr, event_field_expr)
                except Exception as e:
                    # Log the error but don't fail the event processing
                    logger.warning(
                        "Failed to store generated JSONata mapping with event field",
                        event_id=event_id,
                        source=source,
                        has_event_field_expr=event_field_expr is not None,
                        error=str(e)
                    )

            # Create canonical CloudEvent
            canonical_event = cloud_event_wrapper.wrap_and_validate(
                event_id=event_id,
                source=source,
                canonical_data=canonical_data,
                raw_payload=payload
            )

            # Send to canonical events topic
            await map_producer.send_canonical_event(canonical_event)

            # Register schema in registry
            await self._register_event_schema(canonical_data)

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

    async def _register_event_schema(self, canonical_data: dict[str, Any]) -> None:
        """Register event schema in the schema registry."""
        try:
            publisher = canonical_data.get("publisher")
            resource = canonical_data.get("resource", {})
            resource_type = resource.get("type")
            action = canonical_data.get("action")

            if publisher and resource_type and action:
                await schema_registry_service.register_event_schema(
                    publisher=publisher,
                    resource_type=resource_type,
                    action=action
                )
        except Exception as e:
            # Log but don't fail event processing
            logger.warning(
                "Failed to register event schema",
                publisher=canonical_data.get("publisher"),
                resource_type=canonical_data.get("resource", {}).get("type"),
                action=canonical_data.get("action"),
                error=str(e)
            )

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
# Note: Service initialization moved to calling code to avoid import-time failures
# when LLM is not configured. Use MappingService() directly where needed.

# Global mapping service instance
mapping_service = MappingService()
