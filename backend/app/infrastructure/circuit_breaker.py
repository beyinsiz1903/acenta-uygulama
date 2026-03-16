"""Circuit Breaker pattern for external service calls.

Travel platforms must survive supplier failures gracefully.

States:
  CLOSED  → Normal operation, requests pass through
  OPEN    → Failures exceeded threshold, requests fail-fast
  HALF_OPEN → Testing recovery, limited requests allowed

Wrapped services:
  - AviationStack (flight lookup)
  - Paximum (hotel supplier)
  - Stripe (payments)
  - Iyzico (Turkish payments)
  - Google Sheets API
  - Email/SMS providers
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("infrastructure.circuit_breaker")


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_max_calls: int = 3
    success_threshold: int = 2  # successes in half-open to close


@dataclass
class CircuitBreaker:
    """In-process circuit breaker.

    Usage:
        breaker = get_breaker("aviationstack")
        if breaker.can_execute():
            try:
                result = await call_external_api()
                breaker.record_success()
            except Exception:
                breaker.record_failure()
                # use fallback
    """
    name: str
    config: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0.0
    half_open_calls: int = 0
    total_requests: int = 0
    total_failures: int = 0
    total_successes: int = 0

    def can_execute(self) -> bool:
        """Check if a request should be allowed."""
        self.total_requests += 1

        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            elapsed = time.monotonic() - self.last_failure_time
            if elapsed >= self.config.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                self.success_count = 0
                logger.info("Circuit %s: OPEN → HALF_OPEN", self.name)
                return True
            return False

        # HALF_OPEN
        if self.half_open_calls < self.config.half_open_max_calls:
            self.half_open_calls += 1
            return True
        return False

    def record_success(self):
        """Record a successful call."""
        self.total_successes += 1

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                logger.info("Circuit %s: HALF_OPEN → CLOSED (recovered)", self.name)
        elif self.state == CircuitState.CLOSED:
            self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self):
        """Record a failed call."""
        self.failure_count += 1
        self.total_failures += 1
        self.last_failure_time = time.monotonic()

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning("Circuit %s: HALF_OPEN → OPEN (failed recovery)", self.name)
        elif self.state == CircuitState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning(
                    "Circuit %s: CLOSED → OPEN (threshold=%d reached)",
                    self.name, self.config.failure_threshold,
                )

    def reset(self):
        """Manual reset."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.half_open_calls = 0

    def get_status(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "total_requests": self.total_requests,
            "total_failures": self.total_failures,
            "total_successes": self.total_successes,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout_s": self.config.recovery_timeout,
            },
        }


# Global breaker registry
_breakers: dict[str, CircuitBreaker] = {}

# Pre-configured breakers for known external services
BREAKER_CONFIGS = {
    "aviationstack": CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=60.0,
        half_open_max_calls=2,
    ),
    "paximum": CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=30.0,
        half_open_max_calls=3,
    ),
    "stripe": CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=45.0,
        half_open_max_calls=2,
    ),
    "iyzico": CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=45.0,
        half_open_max_calls=2,
    ),
    "google_sheets": CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=120.0,
        half_open_max_calls=1,
    ),
    "email_provider": CircuitBreakerConfig(
        failure_threshold=10,
        recovery_timeout=60.0,
        half_open_max_calls=3,
    ),
    # Supplier-specific circuit breakers (P4.2)
    "supplier_ratehawk": CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=120.0,
        half_open_max_calls=2,
        success_threshold=2,
    ),
    "supplier_paximum": CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=120.0,
        half_open_max_calls=2,
        success_threshold=2,
    ),
    "supplier_tbo": CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=120.0,
        half_open_max_calls=2,
        success_threshold=2,
    ),
    "supplier_wtatil": CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=120.0,
        half_open_max_calls=2,
        success_threshold=2,
    ),
}


def get_breaker(name: str) -> CircuitBreaker:
    """Get or create a circuit breaker by name."""
    if name not in _breakers:
        config = BREAKER_CONFIGS.get(name, CircuitBreakerConfig())
        _breakers[name] = CircuitBreaker(name=name, config=config)
    return _breakers[name]


def get_all_breaker_statuses() -> list[dict]:
    """Get status of all circuit breakers."""
    # Ensure all predefined breakers exist
    for name in BREAKER_CONFIGS:
        get_breaker(name)
    return [b.get_status() for b in _breakers.values()]
