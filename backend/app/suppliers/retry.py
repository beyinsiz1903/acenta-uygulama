"""Supplier Retry & Backoff Engine.

Provides exponential backoff with jitter for supplier API calls.
Integrates with the error taxonomy to decide retry vs abort.

Usage:
    from app.suppliers.retry import with_retry

    result = await with_retry(
        coro_factory=lambda: adapter.search_hotels(payload),
        supplier_code="ratehawk",
        operation="search",
        max_retries=3,
    )
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Any, Awaitable, Callable, Optional

from app.suppliers.contracts.errors import (
    SupplierAuthError,
    SupplierBookingError,
    SupplierError,
    SupplierRateLimitError,
    SupplierTimeoutError,
    SupplierUnavailableError,
    SupplierValidationError,
)

logger = logging.getLogger("suppliers.retry")

# Default retry configuration
DEFAULT_BASE_DELAY = 1.0
DEFAULT_MAX_DELAY = 30.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_JITTER_FACTOR = 0.25

# Per-operation timeout matrix (seconds)
TIMEOUT_MATRIX: dict[str, float] = {
    "healthcheck": 5.0,
    "search": 8.0,
    "check_availability": 5.0,
    "get_pricing": 5.0,
    "create_hold": 10.0,
    "confirm_booking": 15.0,
    "cancel_booking": 10.0,
    "credential_validation": 10.0,
    "inventory_sync": 60.0,
}

# Per-supplier timeout overrides
SUPPLIER_TIMEOUT_OVERRIDES: dict[str, dict[str, float]] = {
    "ratehawk": {"search": 8.0, "confirm_booking": 15.0, "cancel_booking": 10.0},
    "paximum": {"search": 12.0, "confirm_booking": 20.0, "cancel_booking": 15.0},
    "tbo": {"search": 10.0, "confirm_booking": 15.0, "cancel_booking": 10.0},
    "wtatil": {"search": 15.0, "confirm_booking": 25.0, "cancel_booking": 15.0},
}

# Rate limit configuration per supplier (requests per minute)
RATE_LIMITS: dict[str, dict[str, int]] = {
    "ratehawk": {"rpm": 300, "burst": 20},
    "paximum": {"rpm": 150, "burst": 10},
    "tbo": {"rpm": 240, "burst": 15},
    "wtatil": {"rpm": 90, "burst": 5},
}

# Non-retryable error types
_NON_RETRYABLE = (SupplierAuthError, SupplierValidationError, SupplierBookingError)


def get_timeout(supplier_code: str, operation: str) -> float:
    """Get the timeout for a specific supplier + operation combination."""
    overrides = SUPPLIER_TIMEOUT_OVERRIDES.get(supplier_code, {})
    return overrides.get(operation, TIMEOUT_MATRIX.get(operation, 10.0))


def _compute_delay(attempt: int, base_delay: float, max_delay: float, jitter_factor: float) -> float:
    """Compute delay with exponential backoff and jitter."""
    delay = min(base_delay * (2 ** attempt), max_delay)
    jitter = delay * jitter_factor
    return delay + random.uniform(-jitter, jitter)


def is_retryable_error(error: Exception) -> bool:
    """Determine if an error is retryable."""
    if isinstance(error, _NON_RETRYABLE):
        return False
    if isinstance(error, SupplierError):
        return error.retryable
    if isinstance(error, (SupplierTimeoutError, SupplierUnavailableError, SupplierRateLimitError)):
        return True
    if isinstance(error, asyncio.TimeoutError):
        return True
    return False


def classify_http_error(status_code: int, response_text: str = "") -> dict[str, Any]:
    """Classify an HTTP error response into the error taxonomy."""
    if status_code == 429:
        return {
            "error_type": "rate_limited",
            "retryable": True,
            "max_retries": 5,
            "base_delay": 2.0,
        }
    if status_code == 401:
        return {"error_type": "auth_error", "retryable": False}
    if status_code == 403:
        return {"error_type": "forbidden", "retryable": False}
    if status_code in (400, 422):
        return {"error_type": "validation_error", "retryable": False}
    if status_code in (502, 503, 504):
        return {"error_type": "server_error", "retryable": True, "max_retries": 3}
    if 500 <= status_code < 600:
        return {"error_type": "server_error", "retryable": True, "max_retries": 2}
    return {"error_type": "unknown", "retryable": False}


async def with_retry(
    coro_factory: Callable[[], Awaitable[Any]],
    *,
    supplier_code: str = "",
    operation: str = "unknown",
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    jitter_factor: float = DEFAULT_JITTER_FACTOR,
    timeout: Optional[float] = None,
    on_retry: Optional[Callable[[int, Exception, float], None]] = None,
) -> Any:
    """Execute an async operation with retry and exponential backoff.

    Args:
        coro_factory: Callable that returns a new coroutine on each call
        supplier_code: Supplier identifier for logging
        operation: Operation name for timeout lookup
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay cap
        jitter_factor: Jitter percentage (0.25 = +/- 25%)
        timeout: Override timeout (defaults to timeout matrix)
        on_retry: Optional callback on each retry (attempt, error, delay)

    Returns:
        The result of the coroutine

    Raises:
        The last error if all retries exhausted
    """
    effective_timeout = timeout or get_timeout(supplier_code, operation)
    last_error: Optional[Exception] = None

    for attempt in range(max_retries + 1):
        try:
            coro = coro_factory()
            if effective_timeout:
                result = await asyncio.wait_for(coro, timeout=effective_timeout)
            else:
                result = await coro
            return result

        except Exception as e:
            last_error = e
            is_last_attempt = attempt >= max_retries

            if not is_retryable_error(e) or is_last_attempt:
                logger.warning(
                    "[%s] %s failed (attempt %d/%d, non-retryable=%s): %s",
                    supplier_code, operation, attempt + 1, max_retries + 1,
                    not is_retryable_error(e), str(e)[:200],
                )
                raise

            delay = _compute_delay(attempt, base_delay, max_delay, jitter_factor)
            logger.info(
                "[%s] %s retry %d/%d after %.1fs: %s",
                supplier_code, operation, attempt + 1, max_retries,
                delay, str(e)[:100],
            )

            if on_retry:
                on_retry(attempt + 1, e, delay)

            await asyncio.sleep(delay)

    raise last_error


class RateLimiter:
    """Simple in-memory token bucket rate limiter per supplier."""

    def __init__(self):
        self._tokens: dict[str, float] = {}
        self._last_refill: dict[str, float] = {}

    def _refill(self, supplier_code: str) -> None:
        config = RATE_LIMITS.get(supplier_code, {"rpm": 300, "burst": 20})
        rpm = config["rpm"]
        burst = config["burst"]
        now = time.monotonic()
        last = self._last_refill.get(supplier_code, now)
        elapsed = now - last

        tokens_to_add = elapsed * (rpm / 60.0)
        current = self._tokens.get(supplier_code, float(burst))
        self._tokens[supplier_code] = min(current + tokens_to_add, float(burst))
        self._last_refill[supplier_code] = now

    async def acquire(self, supplier_code: str) -> bool:
        """Attempt to acquire a rate limit token. Returns False if rate limited."""
        self._refill(supplier_code)
        tokens = self._tokens.get(supplier_code, 1.0)
        if tokens >= 1.0:
            self._tokens[supplier_code] = tokens - 1.0
            return True
        return False

    async def wait_and_acquire(self, supplier_code: str, max_wait: float = 5.0) -> bool:
        """Wait for a token to become available."""
        start = time.monotonic()
        while time.monotonic() - start < max_wait:
            if await self.acquire(supplier_code):
                return True
            await asyncio.sleep(0.1)
        return False


# Singleton
rate_limiter = RateLimiter()
