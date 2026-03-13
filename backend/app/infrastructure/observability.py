"""Observability Stack — OpenTelemetry + Prometheus + Structured Metrics.

Components:
  1. Distributed Tracing (OpenTelemetry)
  2. Metrics Collection (Prometheus)
  3. Structured Logging (JSON)
  4. Health Dashboard aggregation

Prometheus metrics exposed at /api/metrics/prometheus
"""
from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger("infrastructure.observability")

# Metrics storage (in-memory counters, exported to Prometheus)
_counters: dict[str, float] = {}
_histograms: dict[str, list[float]] = {}
_gauges: dict[str, float] = {}


def increment_counter(name: str, value: float = 1.0, labels: Optional[dict] = None):
    """Increment a counter metric."""
    key = _make_key(name, labels)
    _counters[key] = _counters.get(key, 0) + value


def observe_histogram(name: str, value: float, labels: Optional[dict] = None):
    """Record a histogram observation."""
    key = _make_key(name, labels)
    if key not in _histograms:
        _histograms[key] = []
    _histograms[key].append(value)
    # Keep last 1000 observations
    if len(_histograms[key]) > 1000:
        _histograms[key] = _histograms[key][-1000:]


def set_gauge(name: str, value: float, labels: Optional[dict] = None):
    """Set a gauge value."""
    key = _make_key(name, labels)
    _gauges[key] = value


def _make_key(name: str, labels: Optional[dict] = None) -> str:
    if not labels:
        return name
    label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
    return f"{name}{{{label_str}}}"


# Pre-defined metrics
class Metrics:
    # HTTP
    HTTP_REQUESTS_TOTAL = "http_requests_total"
    HTTP_REQUEST_DURATION = "http_request_duration_seconds"
    HTTP_ERRORS_TOTAL = "http_errors_total"

    # Business
    BOOKINGS_CREATED = "bookings_created_total"
    BOOKINGS_CONFIRMED = "bookings_confirmed_total"
    BOOKINGS_CANCELLED = "bookings_cancelled_total"
    PAYMENTS_PROCESSED = "payments_processed_total"
    PAYMENTS_FAILED = "payments_failed_total"

    # Infrastructure
    REDIS_OPERATIONS = "redis_operations_total"
    REDIS_ERRORS = "redis_errors_total"
    REDIS_LATENCY = "redis_latency_seconds"
    DB_QUERIES = "db_queries_total"
    DB_LATENCY = "db_query_duration_seconds"

    # Rate Limiting
    RATE_LIMIT_HITS = "rate_limit_hits_total"
    RATE_LIMIT_REJECTIONS = "rate_limit_rejections_total"

    # Circuit Breaker
    CIRCUIT_BREAKER_STATE_CHANGES = "circuit_breaker_state_changes_total"

    # Jobs
    JOBS_ENQUEUED = "jobs_enqueued_total"
    JOBS_COMPLETED = "jobs_completed_total"
    JOBS_FAILED = "jobs_failed_total"
    JOBS_DEAD = "jobs_dead_total"

    # Events
    EVENTS_PUBLISHED = "events_published_total"
    EVENTS_HANDLED = "events_handled_total"


def get_prometheus_text() -> str:
    """Export all metrics in Prometheus text format."""
    lines = []

    # Counters
    for key, value in sorted(_counters.items()):
        name = key.split("{")[0] if "{" in key else key
        lines.append(f"# TYPE {name} counter")
        lines.append(f"{key} {value}")

    # Gauges
    for key, value in sorted(_gauges.items()):
        name = key.split("{")[0] if "{" in key else key
        lines.append(f"# TYPE {name} gauge")
        lines.append(f"{key} {value}")

    # Histograms (simplified: sum, count, avg)
    for key, values in sorted(_histograms.items()):
        name = key.split("{")[0] if "{" in key else key
        if values:
            total = sum(values)
            count = len(values)
            avg = total / count
            lines.append(f"# TYPE {name} summary")
            lines.append(f"{key}_sum {total:.6f}")
            lines.append(f"{key}_count {count}")
            lines.append(f"{key}_avg {avg:.6f}")

    return "\n".join(lines)


def get_metrics_summary() -> dict[str, Any]:
    """Get a JSON summary of all metrics."""
    histogram_summary = {}
    for key, values in _histograms.items():
        if values:
            histogram_summary[key] = {
                "count": len(values),
                "sum": round(sum(values), 4),
                "avg": round(sum(values) / len(values), 4),
                "min": round(min(values), 4),
                "max": round(max(values), 4),
            }

    return {
        "counters": dict(sorted(_counters.items())),
        "gauges": dict(sorted(_gauges.items())),
        "histograms": histogram_summary,
    }


# OpenTelemetry initialization
_tracer = None


def init_opentelemetry(service_name: str = "syroce-api"):
    """Initialize OpenTelemetry tracing."""
    global _tracer
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.resources import Resource

        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer(service_name)
        logger.info("OpenTelemetry initialized for %s", service_name)
    except Exception as e:
        logger.warning("OpenTelemetry init failed: %s", e)


def get_tracer():
    """Get the OpenTelemetry tracer."""
    if _tracer:
        return _tracer
    try:
        from opentelemetry import trace
        return trace.get_tracer("syroce-api")
    except Exception:
        return None
