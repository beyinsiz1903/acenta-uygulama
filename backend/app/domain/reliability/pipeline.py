"""Reliability Pipeline — Wraps every supplier call through the full reliability chain.

Chain: timeout → retry → contract validation → metrics → incident logging → degrade/disable.

Usage:
    from app.domain.reliability.pipeline import reliable_supplier_call

    result = await reliable_supplier_call(
        db, org_id, supplier_code, "search",
        lambda: adapter.search(ctx, request),
    )
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine

from app.domain.reliability.resilience_service import (
    get_isolation_context,
)
from app.domain.reliability.contract_service import validate_and_log
from app.domain.reliability.metrics_service import record_metric
from app.domain.reliability.incident_service import detect_supplier_issues

logger = logging.getLogger("reliability.pipeline")

# Supplier status cache (in-memory, refreshed periodically)
_supplier_status_cache: dict[str, dict] = {}
_cache_ts: float = 0
_CACHE_TTL = 30.0  # seconds


async def _check_supplier_enabled(db, org_id: str, supplier_code: str) -> dict | None:
    """Check if supplier is disabled/degraded. Returns status doc or None if healthy."""
    global _supplier_status_cache, _cache_ts
    now = time.monotonic()
    if now - _cache_ts > _CACHE_TTL:
        docs = await db.rel_supplier_status.find(
            {"organization_id": org_id}, {"_id": 0}
        ).to_list(200)
        _supplier_status_cache = {d["supplier_code"]: d for d in docs}
        _cache_ts = now

    status_doc = _supplier_status_cache.get(supplier_code)
    if status_doc and status_doc.get("status") == "disabled":
        return status_doc
    return None


async def reliable_supplier_call(
    db,
    org_id: str,
    supplier_code: str,
    method: str,
    call_fn: Callable[[], Coroutine[Any, Any, Any]],
    *,
    timeout_ms: int = 10000,
    max_retries: int = 3,
    validate_contract: bool = True,
) -> dict[str, Any]:
    """Execute a supplier call through the full reliability pipeline.

    Pipeline stages:
    1. Degrade/Disable check — reject if supplier disabled
    2. Timeout guard — asyncio.wait_for
    3. Retry with exponential backoff
    4. Contract validation — schema check on response
    5. Metrics recording — latency, call count, error count
    6. Incident detection — auto-escalate on high error rates
    """
    pipeline_start = time.monotonic()
    now_iso = datetime.now(timezone.utc).isoformat()

    # Stage 1: Degrade/Disable check
    disabled = await _check_supplier_enabled(db, org_id, supplier_code)
    if disabled:
        await record_metric(db, org_id, supplier_code, "api_call_count", 1, method)
        await record_metric(db, org_id, supplier_code, "api_error_count", 1, method, {"reason": "supplier_disabled"})
        return {
            "ok": False,
            "error": "supplier_disabled",
            "supplier_code": supplier_code,
            "method": method,
            "disabled_reason": disabled.get("disabled_reason", "unknown"),
        }

    # Stage 2+3: Timeout + Retry with backoff
    ctx = get_isolation_context(supplier_code)
    effective_timeout = min(timeout_ms, 30000) / 1000.0  # convert to seconds
    last_error = None
    result_data = None
    attempts = 0

    for attempt in range(1, max_retries + 1):
        attempts = attempt
        step_start = time.monotonic()
        try:
            result_data = await asyncio.wait_for(call_fn(), timeout=effective_timeout)
            duration_ms = int((time.monotonic() - step_start) * 1000)

            # Stage 4: Contract validation
            contract_result = None
            if validate_contract and isinstance(result_data, dict):
                try:
                    contract_result = await validate_and_log(
                        db, org_id, supplier_code, method, result_data, mode="warn"
                    )
                except Exception as ce:
                    logger.warning("Contract validation failed: %s", ce)

            # Stage 5: Metrics — success
            await record_metric(db, org_id, supplier_code, "api_call_count", 1, method)
            await record_metric(db, org_id, supplier_code, "api_latency_ms", duration_ms, method)

            total_ms = int((time.monotonic() - pipeline_start) * 1000)
            return {
                "ok": True,
                "data": result_data,
                "supplier_code": supplier_code,
                "method": method,
                "duration_ms": duration_ms,
                "total_pipeline_ms": total_ms,
                "attempts": attempts,
                "contract": contract_result,
            }

        except asyncio.TimeoutError:
            duration_ms = int((time.monotonic() - step_start) * 1000)
            last_error = "timeout"
            await record_metric(db, org_id, supplier_code, "api_call_count", 1, method)
            await record_metric(db, org_id, supplier_code, "api_timeout_count", 1, method)
            await record_metric(db, org_id, supplier_code, "api_latency_ms", duration_ms, method)
            logger.warning("Supplier %s/%s timeout (attempt %d/%d)", supplier_code, method, attempt, max_retries)

        except Exception as exc:
            duration_ms = int((time.monotonic() - step_start) * 1000)
            last_error = str(exc)[:300]
            await record_metric(db, org_id, supplier_code, "api_call_count", 1, method)
            await record_metric(db, org_id, supplier_code, "api_error_count", 1, method, {"error": last_error[:100]})
            await record_metric(db, org_id, supplier_code, "api_latency_ms", duration_ms, method)
            logger.warning("Supplier %s/%s error (attempt %d/%d): %s", supplier_code, method, attempt, max_retries, last_error)

        # Backoff before retry
        if attempt < max_retries:
            import random
            delay = min(0.5 * (2 ** (attempt - 1)) + random.uniform(0, 0.3), 10.0)
            await asyncio.sleep(delay)

    # All retries exhausted
    total_ms = int((time.monotonic() - pipeline_start) * 1000)

    # Stage 6: Incident detection (async, best-effort)
    try:
        await _log_pipeline_failure(db, org_id, supplier_code, method, last_error, attempts, total_ms)
    except Exception:
        pass

    return {
        "ok": False,
        "error": last_error,
        "supplier_code": supplier_code,
        "method": method,
        "attempts": attempts,
        "total_pipeline_ms": total_ms,
    }


async def _log_pipeline_failure(db, org_id, supplier_code, method, error, attempts, total_ms):
    """Log pipeline failure for incident detection."""
    from app.domain.reliability.resilience_service import _log_resilience_event
    await _log_resilience_event(db, org_id, supplier_code, method, "error", total_ms, attempt=attempts, error=error)
