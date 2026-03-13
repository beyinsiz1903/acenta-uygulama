"""PART 3 — Full Observability Stack.

Prometheus metrics, Grafana dashboards, OpenTelemetry tracing.
Tracks: API latency, queue depth, supplier error rate, booking conversion.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger("hardening.observability")


# Metric definitions for Prometheus
PROMETHEUS_METRICS = {
    "counters": {
        "syroce_http_requests_total": {"help": "Total HTTP requests", "labels": ["method", "endpoint", "status"]},
        "syroce_bookings_total": {"help": "Total bookings created", "labels": ["status", "supplier", "tenant"]},
        "syroce_payments_total": {"help": "Total payments processed", "labels": ["status", "method", "currency"]},
        "syroce_supplier_calls_total": {"help": "Total supplier API calls", "labels": ["supplier", "operation", "status"]},
        "syroce_auth_events_total": {"help": "Auth events", "labels": ["type", "result"]},
        "syroce_queue_tasks_total": {"help": "Queue tasks processed", "labels": ["queue", "status"]},
        "syroce_notifications_total": {"help": "Notifications sent", "labels": ["channel", "status"]},
        "syroce_circuit_breaker_trips": {"help": "Circuit breaker trips", "labels": ["supplier", "reason"]},
    },
    "histograms": {
        "syroce_http_duration_seconds": {"help": "HTTP request duration", "labels": ["method", "endpoint"], "buckets": [0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]},
        "syroce_supplier_latency_seconds": {"help": "Supplier API latency", "labels": ["supplier", "operation"], "buckets": [0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 15.0, 30.0]},
        "syroce_db_query_seconds": {"help": "Database query duration", "labels": ["collection", "operation"], "buckets": [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]},
        "syroce_queue_wait_seconds": {"help": "Queue task wait time", "labels": ["queue"], "buckets": [0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0]},
    },
    "gauges": {
        "syroce_active_connections": {"help": "Active connections", "labels": ["type"]},
        "syroce_queue_depth": {"help": "Current queue depth", "labels": ["queue"]},
        "syroce_circuit_breaker_state": {"help": "Circuit breaker state (0=closed, 1=open, 2=half)", "labels": ["supplier"]},
        "syroce_active_bookings": {"help": "Active bookings in progress", "labels": ["tenant"]},
        "syroce_supplier_health_score": {"help": "Supplier health 0-100", "labels": ["supplier"]},
    },
}


# OpenTelemetry trace configuration
OTEL_CONFIG = {
    "service_name": "syroce-api",
    "traces": {
        "sample_rate": float(os.environ.get("OTEL_TRACES_SAMPLE_RATE", "1.0")),
        "exporter": os.environ.get("OTEL_EXPORTER", "console"),
        "endpoint": os.environ.get("OTEL_ENDPOINT", ""),
    },
    "spans": {
        "http_server": True,
        "db_queries": True,
        "supplier_calls": True,
        "queue_tasks": True,
        "cache_operations": True,
    },
}


# Grafana dashboard definitions
GRAFANA_DASHBOARDS = {
    "platform_overview": {
        "title": "Syroce Platform Overview",
        "panels": [
            {"title": "Request Rate", "metric": "rate(syroce_http_requests_total[5m])", "type": "graph"},
            {"title": "Error Rate", "metric": "rate(syroce_http_requests_total{status=~'5..'}[5m])", "type": "graph"},
            {"title": "P99 Latency", "metric": "histogram_quantile(0.99, rate(syroce_http_duration_seconds_bucket[5m]))", "type": "stat"},
            {"title": "Active Bookings", "metric": "syroce_active_bookings", "type": "gauge"},
        ],
    },
    "supplier_health": {
        "title": "Supplier Health Dashboard",
        "panels": [
            {"title": "Supplier Call Rate", "metric": "rate(syroce_supplier_calls_total[5m])", "type": "graph"},
            {"title": "Supplier Error Rate", "metric": "rate(syroce_supplier_calls_total{status='error'}[5m]) / rate(syroce_supplier_calls_total[5m])", "type": "graph"},
            {"title": "Supplier P95 Latency", "metric": "histogram_quantile(0.95, rate(syroce_supplier_latency_seconds_bucket[5m]))", "type": "graph"},
            {"title": "Circuit Breaker States", "metric": "syroce_circuit_breaker_state", "type": "table"},
            {"title": "Health Score", "metric": "syroce_supplier_health_score", "type": "gauge"},
        ],
    },
    "booking_conversion": {
        "title": "Booking Conversion Funnel",
        "panels": [
            {"title": "Search → Hold Rate", "metric": "rate(syroce_bookings_total{status='held'}[1h]) / rate(syroce_bookings_total{status='searched'}[1h])", "type": "stat"},
            {"title": "Hold → Confirm Rate", "metric": "rate(syroce_bookings_total{status='confirmed'}[1h]) / rate(syroce_bookings_total{status='held'}[1h])", "type": "stat"},
            {"title": "Booking by Supplier", "metric": "sum by (supplier) (rate(syroce_bookings_total[1h]))", "type": "pie"},
            {"title": "Revenue by Tenant", "metric": "sum by (tenant) (syroce_payments_total{status='success'})", "type": "bar"},
        ],
    },
    "queue_monitoring": {
        "title": "Queue & Worker Monitoring",
        "panels": [
            {"title": "Queue Depth", "metric": "syroce_queue_depth", "type": "graph"},
            {"title": "Task Processing Rate", "metric": "rate(syroce_queue_tasks_total[5m])", "type": "graph"},
            {"title": "Task Wait Time P95", "metric": "histogram_quantile(0.95, rate(syroce_queue_wait_seconds_bucket[5m]))", "type": "stat"},
            {"title": "DLQ Messages", "metric": "syroce_queue_depth{queue=~'dlq.*'}", "type": "graph"},
        ],
    },
}


# Alert rules
ALERT_RULES = [
    {
        "name": "HighErrorRate",
        "expr": "rate(syroce_http_requests_total{status=~'5..'}[5m]) / rate(syroce_http_requests_total[5m]) > 0.05",
        "for": "5m",
        "severity": "critical",
        "summary": "HTTP 5xx error rate exceeds 5%",
    },
    {
        "name": "HighLatency",
        "expr": "histogram_quantile(0.99, rate(syroce_http_duration_seconds_bucket[5m])) > 5",
        "for": "5m",
        "severity": "warning",
        "summary": "P99 latency exceeds 5 seconds",
    },
    {
        "name": "SupplierDown",
        "expr": "syroce_circuit_breaker_state == 1",
        "for": "2m",
        "severity": "critical",
        "summary": "Supplier circuit breaker is open",
    },
    {
        "name": "QueueBacklog",
        "expr": "syroce_queue_depth{queue='critical'} > 50",
        "for": "3m",
        "severity": "critical",
        "summary": "Critical queue depth exceeds 50",
    },
    {
        "name": "DLQGrowing",
        "expr": "rate(syroce_queue_depth{queue=~'dlq.*'}[10m]) > 0",
        "for": "10m",
        "severity": "warning",
        "summary": "DLQ is accumulating messages",
    },
    {
        "name": "PaymentFailures",
        "expr": "rate(syroce_payments_total{status='failed'}[5m]) > 0.1",
        "for": "3m",
        "severity": "critical",
        "summary": "Payment failure rate is elevated",
    },
]


async def get_observability_status(db) -> dict:
    """Get full observability stack status."""
    from app.infrastructure.observability import get_metrics_summary, get_prometheus_text

    metrics_summary = get_metrics_summary()
    prom_text_len = len(get_prometheus_text())

    return {
        "prometheus": {
            "metrics_defined": sum(len(v) for v in PROMETHEUS_METRICS.values()),
            "counters": len(PROMETHEUS_METRICS["counters"]),
            "histograms": len(PROMETHEUS_METRICS["histograms"]),
            "gauges": len(PROMETHEUS_METRICS["gauges"]),
            "current_text_bytes": prom_text_len,
        },
        "opentelemetry": OTEL_CONFIG,
        "grafana_dashboards": {k: {"title": v["title"], "panels": len(v["panels"])} for k, v in GRAFANA_DASHBOARDS.items()},
        "alert_rules": [{"name": r["name"], "severity": r["severity"]} for r in ALERT_RULES],
        "live_metrics": metrics_summary,
    }
