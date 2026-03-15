"""Provider Failover Strategy (MEGA PROMPT #34).

Accounting providers do NOT support automatic cross-provider failover.
Instead, the strategy is:
  1. Retry (with backoff)
  2. Queue for deferred processing
  3. Manual intervention (ops escalation)

This module provides the retry + escalation logic.
"""
from __future__ import annotations

import logging
from typing import Any

from app.accounting.providers.base_provider import (
    ERR_RATE_LIMIT,
    ERR_TIMEOUT,
    ERR_TRANSIENT,
    ERR_UNREACHABLE,
    ProviderResponse,
)

logger = logging.getLogger("accounting.failover")

# Retry-eligible error codes
RETRYABLE_ERRORS = {ERR_TRANSIENT, ERR_TIMEOUT, ERR_UNREACHABLE, ERR_RATE_LIMIT}

# Max retry attempts per strategy tier
MAX_IMMEDIATE_RETRIES = 2
MAX_QUEUE_RETRIES = 3

# Backoff delays in seconds
BACKOFF_SCHEDULE = [5, 30, 120, 600, 3600]  # 5s, 30s, 2m, 10m, 1h


def should_retry(response: ProviderResponse, attempt: int) -> bool:
    """Determine if the failed request should be retried immediately."""
    if response.success:
        return False
    if response.error_code not in RETRYABLE_ERRORS:
        return False
    return attempt < MAX_IMMEDIATE_RETRIES


def should_queue(response: ProviderResponse, attempt: int) -> bool:
    """Determine if the failed request should be queued for deferred processing."""
    if response.success:
        return False
    if response.error_code not in RETRYABLE_ERRORS:
        return False
    return attempt >= MAX_IMMEDIATE_RETRIES and attempt < (MAX_IMMEDIATE_RETRIES + MAX_QUEUE_RETRIES)


def should_escalate(response: ProviderResponse, attempt: int) -> bool:
    """Determine if the failure should be escalated to manual ops."""
    if response.success:
        return False
    # Escalate if non-retryable or all retries exhausted
    if response.error_code not in RETRYABLE_ERRORS:
        return True
    return attempt >= (MAX_IMMEDIATE_RETRIES + MAX_QUEUE_RETRIES)


def get_backoff_seconds(attempt: int) -> int:
    """Get the backoff delay for the given attempt number."""
    idx = min(attempt, len(BACKOFF_SCHEDULE) - 1)
    return BACKOFF_SCHEDULE[idx]


def classify_failure(response: ProviderResponse, attempt: int) -> dict[str, Any]:
    """Classify a provider failure and return the recommended action.

    Returns:
        {
            "action": "retry" | "queue" | "escalate",
            "backoff_seconds": int,
            "reason": str,
        }
    """
    if response.success:
        return {"action": "none", "backoff_seconds": 0, "reason": "basarili"}

    if should_retry(response, attempt):
        return {
            "action": "retry",
            "backoff_seconds": get_backoff_seconds(attempt),
            "reason": f"Gecici hata, deneme {attempt + 1}/{MAX_IMMEDIATE_RETRIES}",
        }

    if should_queue(response, attempt):
        return {
            "action": "queue",
            "backoff_seconds": get_backoff_seconds(attempt),
            "reason": f"Kuyruga aliniyor, deneme {attempt + 1}",
        }

    return {
        "action": "escalate",
        "backoff_seconds": 0,
        "reason": f"Manuel mudahale gerekli: {response.error_code} - {response.error_message}",
    }
