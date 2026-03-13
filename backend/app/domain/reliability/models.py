"""Integration Reliability — Domain Models & Constants."""
from __future__ import annotations

# ============================================================================
# PART 1 — SUPPLIER API RESILIENCE STRATEGIES
# ============================================================================

RESILIENCE_STRATEGIES = {
    "timeout": "Configurable per-supplier timeout with adaptive adjustment",
    "rate_limit": "Token-bucket rate limiter per supplier API",
    "schema_change": "Contract validation rejects unexpected payloads",
    "partial_response": "Graceful degradation with partial result acceptance",
    "adapter_isolation": "Each adapter runs in isolated context; failures don't cascade",
    "automatic_retry": "Exponential backoff with jitter for transient failures",
}

DEFAULT_TIMEOUT_MS = 8000
MAX_TIMEOUT_MS = 30000
MIN_TIMEOUT_MS = 2000

RATE_LIMIT_DEFAULTS = {
    "requests_per_second": 50,
    "burst_size": 100,
    "cooldown_seconds": 60,
}

# ============================================================================
# PART 2 — SANDBOX MODES
# ============================================================================

SANDBOX_MODES = ["mock", "record", "replay", "fault_injection"]

FAULT_TYPES = [
    "timeout", "error_500", "error_429", "partial_response",
    "schema_mismatch", "slow_response", "connection_reset",
    "invalid_json", "empty_response",
]

# ============================================================================
# PART 3 — RETRY STRATEGIES
# ============================================================================

RETRY_CATEGORIES = {
    "supplier_call": {
        "max_retries": 3,
        "base_delay_ms": 500,
        "max_delay_ms": 10000,
        "backoff_multiplier": 2.0,
        "jitter": True,
        "retryable_errors": ["timeout", "502", "503", "429"],
    },
    "payment": {
        "max_retries": 2,
        "base_delay_ms": 1000,
        "max_delay_ms": 5000,
        "backoff_multiplier": 2.0,
        "jitter": True,
        "retryable_errors": ["timeout", "502", "503"],
    },
    "voucher_generation": {
        "max_retries": 5,
        "base_delay_ms": 2000,
        "max_delay_ms": 30000,
        "backoff_multiplier": 2.0,
        "jitter": True,
        "retryable_errors": ["timeout", "502", "503", "render_failure"],
    },
}

DLQ_CATEGORIES = ["supplier_call", "payment", "voucher_generation", "webhook", "notification"]

# ============================================================================
# PART 4 — IDEMPOTENCY
# ============================================================================

IDEMPOTENT_OPERATIONS = [
    "booking.confirm", "booking.cancel", "payment.charge",
    "payment.refund", "voucher.generate", "supplier.hold",
]

IDEMPOTENCY_TTL_SECONDS = 86400  # 24h

# ============================================================================
# PART 5 — API VERSIONING
# ============================================================================

SUPPLIER_API_VERSIONS = {
    "mock_hotel": {"current": "v1", "supported": ["v1"]},
    "mock_flight": {"current": "v1", "supported": ["v1"]},
    "mock_tour": {"current": "v1", "supported": ["v1"]},
    "mock_insurance": {"current": "v1", "supported": ["v1"]},
    "mock_transport": {"current": "v1", "supported": ["v1"]},
}

# ============================================================================
# PART 6 — CONTRACT VALIDATION
# ============================================================================

VALIDATION_MODES = ["strict", "warn", "permissive"]

REQUIRED_SEARCH_FIELDS = ["item_id", "supplier_code", "name", "supplier_price", "sell_price", "currency"]
REQUIRED_CONFIRM_FIELDS = ["supplier_booking_id", "status"]
REQUIRED_CANCEL_FIELDS = ["supplier_booking_id", "status"]

# ============================================================================
# PART 7 — INTEGRATION METRICS
# ============================================================================

METRIC_TYPES = [
    "api_call_count", "api_error_count", "api_latency_ms",
    "api_timeout_count", "api_success_rate",
    "retry_count", "dlq_size", "circuit_state",
    "contract_violation_count", "idempotency_hit_count",
]

METRIC_WINDOWS = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3600,
    "24h": 86400,
}

# ============================================================================
# PART 8 — INCIDENT RESPONSE
# ============================================================================

INCIDENT_TYPES = [
    "supplier_outage", "high_error_rate", "high_latency",
    "circuit_breaker_open", "rate_limit_exceeded",
    "contract_violation_spike", "dlq_overflow",
]

INCIDENT_SEVERITY = ["critical", "high", "medium", "low"]

AUTO_ACTIONS = {
    "supplier_outage": "disable_supplier",
    "high_error_rate": "degrade_supplier",
    "high_latency": "increase_timeout",
    "circuit_breaker_open": "notify_ops",
    "rate_limit_exceeded": "throttle_requests",
    "contract_violation_spike": "disable_supplier",
    "dlq_overflow": "alert_critical",
}

# ============================================================================
# PART 10 — MATURITY SCORE WEIGHTS
# ============================================================================

MATURITY_DIMENSIONS = {
    "resilience": 0.20,
    "observability": 0.15,
    "idempotency": 0.15,
    "contract_safety": 0.15,
    "incident_response": 0.15,
    "retry_dlq": 0.10,
    "versioning": 0.05,
    "sandbox": 0.05,
}
