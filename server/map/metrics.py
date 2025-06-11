"""Prometheus metrics for the mapping service."""

import asyncio
import time
from typing import Any

import structlog
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    push_to_gateway,
)

logger = structlog.get_logger("langhook.metrics")

# Create a custom registry for the mapping service
mapping_registry = CollectorRegistry()

# Define metrics
events_processed_total = Counter(
    'langhook_events_processed_total',
    'Total number of events processed by the mapping service',
    ['source'],
    registry=mapping_registry
)

events_mapped_total = Counter(
    'langhook_events_mapped_total',
    'Total number of events successfully mapped',
    ['source'],
    registry=mapping_registry
)

events_failed_total = Counter(
    'langhook_events_failed_total',
    'Total number of events that failed mapping',
    ['source', 'reason'],
    registry=mapping_registry
)

llm_invocations_total = Counter(
    'langhook_llm_invocations_total',
    'Total number of LLM invocations for mapping suggestions',
    ['source'],
    registry=mapping_registry
)

mapping_duration_seconds = Histogram(
    'langhook_mapping_duration_seconds',
    'Time spent processing each event',
    ['source'],
    registry=mapping_registry
)

active_mappings = Gauge(
    'langhook_active_mappings',
    'Number of active mapping rules loaded',
    registry=mapping_registry
)


class MetricsCollector:
    """Collector for mapping service metrics."""

    def __init__(self):
        self.start_time = time.time()
        self._push_task: asyncio.Task | None = None
        self._push_enabled = False
        self._pushgateway_url: str | None = None
        self._job_name = "langhook-map"
        self._push_interval = 30

    def configure_push_gateway(self, pushgateway_url: str | None, job_name: str = "langhook-map", push_interval: int = 30) -> None:
        """Configure Prometheus push gateway settings."""
        self._pushgateway_url = pushgateway_url
        self._job_name = job_name
        self._push_interval = push_interval
        self._push_enabled = pushgateway_url is not None

        if self._push_enabled:
            logger.info(
                "Prometheus push gateway configured",
                url=self._pushgateway_url,
                job_name=self._job_name,
                interval=self._push_interval
            )

    async def start_push_task(self) -> None:
        """Start the background task to push metrics to gateway."""
        if not self._push_enabled or self._push_task is not None:
            return

        logger.info("Starting Prometheus metrics push task")
        self._push_task = asyncio.create_task(self._push_metrics_loop())

    async def stop_push_task(self) -> None:
        """Stop the background task."""
        if self._push_task is not None:
            logger.info("Stopping Prometheus metrics push task")
            self._push_task.cancel()
            try:
                await self._push_task
            except asyncio.CancelledError:
                pass
            self._push_task = None

    async def _push_metrics_loop(self) -> None:
        """Background loop to push metrics to gateway."""
        while True:
            try:
                await asyncio.sleep(self._push_interval)
                if self._push_enabled and self._pushgateway_url:
                    self._push_metrics_to_gateway()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error pushing metrics to gateway", error=str(e), exc_info=True)

    def _push_metrics_to_gateway(self) -> None:
        """Push current metrics to the configured push gateway."""
        if not self._push_enabled or not self._pushgateway_url:
            return

        try:
            push_to_gateway(
                self._pushgateway_url,
                job=self._job_name,
                registry=mapping_registry
            )
            logger.debug("Successfully pushed metrics to gateway")
        except Exception as e:
            logger.error("Failed to push metrics to gateway", error=str(e), exc_info=True)

    def record_event_processed(self, source: str) -> None:
        """Record that an event was processed."""
        events_processed_total.labels(source=source).inc()

    def record_event_mapped(self, source: str) -> None:
        """Record that an event was successfully mapped."""
        events_mapped_total.labels(source=source).inc()

    def record_event_failed(self, source: str, reason: str) -> None:
        """Record that an event failed mapping."""
        events_failed_total.labels(source=source, reason=reason).inc()

    def record_llm_invocation(self, source: str) -> None:
        """Record an LLM invocation."""
        llm_invocations_total.labels(source=source).inc()

    def record_mapping_duration(self, source: str, duration: float) -> None:
        """Record mapping processing duration."""
        mapping_duration_seconds.labels(source=source).observe(duration)

    def update_active_mappings(self, count: int) -> None:
        """Update the count of active mappings."""
        active_mappings.set(count)

    def get_metrics_text(self) -> str:
        """Get metrics in Prometheus text format."""
        return generate_latest(mapping_registry).decode('utf-8')

    def get_metrics_dict(self) -> dict[str, Any]:
        """Get metrics as a dictionary for JSON API."""
        # Simple metrics for the /metrics endpoint
        return {
            'uptime_seconds': time.time() - self.start_time,
            'active_mappings': active_mappings._value._value if hasattr(active_mappings, '_value') else 0,
        }


# Global metrics collector
metrics = MetricsCollector()
