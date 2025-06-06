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

                    # Generate JSONata mapping using LLM
                    jsonata_mapping = await llm_service.suggest_mapping(source, payload)
                    
                    if jsonata_mapping is None:
                        await self._send_mapping_failure(
                            raw_event,
                            "LLM failed to generate mapping suggestion"
                        )
                        metrics.record_event_failed(source or "unknown", "llm_generation_failed")
                        return
                    
                    # Apply the LLM-generated mapping
                    canonical_data = self._apply_generated_mapping(jsonata_mapping, payload, source)
                    
                    if canonical_data is None:
                        await self._send_mapping_failure(
                            raw_event,
                            "Generated mapping failed to produce valid canonical data"
                        )
                        metrics.record_event_failed(source or "unknown", "llm_mapping_invalid")
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

    def _apply_generated_mapping(self, mapping_expr: str, raw_payload: dict[str, Any], source: str) -> dict[str, Any] | None:
        """
        Apply a generated JSONata mapping to transform raw payload to canonical format.
        
        This uses the same validation logic as the mapping engine but applies a dynamically
        generated mapping expression.
        
        Args:
            mapping_expr: JSONata expression string generated by LLM
            raw_payload: Raw webhook payload
            source: Source identifier for logging
            
        Returns:
            Canonical event dict or None if mapping fails
        """
        try:
            import jsonata
            
            # Apply JSONata transformation using the transform function
            result = jsonata.transform(mapping_expr, raw_payload)

            # Ensure result has required fields for new canonical format
            if not isinstance(result, dict):
                logger.error(
                    "Generated mapping result is not a dictionary",
                    source=source,
                    result_type=type(result).__name__
                )
                return None

            # Validate new canonical format requirements
            required_fields = ['publisher', 'resource', 'action']
            missing_fields = [field for field in required_fields if field not in result]

            if missing_fields:
                logger.error(
                    "Generated mapping result missing required fields",
                    source=source,
                    missing_fields=missing_fields,
                    result=result
                )
                return None

            # Validate resource structure
            if not isinstance(result.get('resource'), dict):
                logger.error(
                    "Generated mapping resource must be an object with type and id fields",
                    source=source,
                    resource=result.get('resource')
                )
                return None

            resource = result['resource']
            if 'type' not in resource or 'id' not in resource:
                logger.error(
                    "Generated mapping resource object missing type or id field",
                    source=source,
                    resource=resource
                )
                return None

            # Validate action is CRUD enum
            valid_actions = ['create', 'read', 'update', 'delete']
            if result['action'] not in valid_actions:
                logger.error(
                    "Generated mapping invalid action - must be one of: create, read, update, delete",
                    source=source,
                    action=result['action']
                )
                return None

            # Validate atomic ID (no composite keys with /, #, or space)
            resource_id = str(resource['id'])
            invalid_chars = ['/', '#', ' ']
            if any(char in resource_id for char in invalid_chars):
                logger.error(
                    "Generated mapping resource ID contains invalid characters (/, #, space) - atomic IDs only",
                    source=source,
                    resource_id=resource_id
                )
                return None

            logger.debug(
                "Generated mapping applied successfully",
                source=source,
                result=result
            )

            return result

        except Exception as e:
            logger.error(
                "Failed to apply generated mapping",
                source=source,
                mapping_expr=mapping_expr,
                error=str(e),
                exc_info=True
            )
            return None

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
