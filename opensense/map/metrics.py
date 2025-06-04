"""Prometheus metrics for the mapping service."""

from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
from typing import Dict, Any
import time

# Create a custom registry for the mapping service
mapping_registry = CollectorRegistry()

# Define metrics
events_processed_total = Counter(
    'opensense_events_processed_total',
    'Total number of events processed by the mapping service',
    ['source'],
    registry=mapping_registry
)

events_mapped_total = Counter(
    'opensense_events_mapped_total', 
    'Total number of events successfully mapped',
    ['source'],
    registry=mapping_registry
)

events_failed_total = Counter(
    'opensense_events_failed_total',
    'Total number of events that failed mapping',
    ['source', 'reason'],
    registry=mapping_registry
)

llm_invocations_total = Counter(
    'opensense_llm_invocations_total',
    'Total number of LLM invocations for mapping suggestions',
    ['source'],
    registry=mapping_registry
)

mapping_duration_seconds = Histogram(
    'opensense_mapping_duration_seconds',
    'Time spent processing each event',
    ['source'],
    registry=mapping_registry
)

active_mappings = Gauge(
    'opensense_active_mappings',
    'Number of active mapping rules loaded',
    registry=mapping_registry
)


class MetricsCollector:
    """Collector for mapping service metrics."""
    
    def __init__(self):
        self.start_time = time.time()
    
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
    
    def get_metrics_dict(self) -> Dict[str, Any]:
        """Get metrics as a dictionary for JSON API."""
        # Simple metrics for the /metrics endpoint
        return {
            'uptime_seconds': time.time() - self.start_time,
            'active_mappings': active_mappings._value._value if hasattr(active_mappings, '_value') else 0,
        }


# Global metrics collector
metrics = MetricsCollector()