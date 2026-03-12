"""PART 5 — Supplier Debugging Tools.

Allows ops team to inspect:
  - Raw supplier requests/responses
  - Normalization results
  - Request replay (dry-run)
"""
from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("suppliers.ops.debug")


async def log_supplier_interaction(
    db,
    organization_id: str,
    *,
    supplier_code: str,
    operation: str,
    request_payload: Dict[str, Any],
    response_payload: Optional[Dict[str, Any]] = None,
    normalized_result: Optional[Dict[str, Any]] = None,
    duration_ms: int = 0,
    success: bool = True,
    error: Optional[str] = None,
    request_id: Optional[str] = None,
) -> str:
    """Log a supplier interaction for debugging."""

    now = datetime.now(timezone.utc)
    trace_id = request_id or str(uuid.uuid4())

    doc = {
        "trace_id": trace_id,
        "organization_id": organization_id,
        "supplier_code": supplier_code,
        "operation": operation,
        "request_payload": request_payload,
        "response_payload": response_payload,
        "normalized_result": normalized_result,
        "duration_ms": duration_ms,
        "success": success,
        "error": error,
        "created_at": now,
    }

    await db.supplier_debug_logs.insert_one({"_id": trace_id, **doc})
    return trace_id


async def get_supplier_interactions(
    db,
    organization_id: str,
    *,
    supplier_code: Optional[str] = None,
    operation: Optional[str] = None,
    success_only: Optional[bool] = None,
    trace_id: Optional[str] = None,
    window_hours: int = 24,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Query supplier interaction logs."""

    now = datetime.now(timezone.utc)
    query: Dict[str, Any] = {
        "organization_id": organization_id,
        "created_at": {"$gte": now - timedelta(hours=window_hours)},
    }
    if supplier_code:
        query["supplier_code"] = supplier_code
    if operation:
        query["operation"] = operation
    if success_only is not None:
        query["success"] = success_only
    if trace_id:
        query["trace_id"] = trace_id

    cursor = db.supplier_debug_logs.find(query, {"_id": 0}).sort("created_at", -1).limit(limit)
    return await cursor.to_list(length=limit)


async def get_interaction_detail(
    db,
    organization_id: str,
    trace_id: str,
) -> Optional[Dict[str, Any]]:
    """Get full detail of a single supplier interaction."""

    doc = await db.supplier_debug_logs.find_one(
        {"_id": trace_id, "organization_id": organization_id},
        {"_id": 0},
    )
    return doc


async def replay_supplier_request(
    db,
    organization_id: str,
    trace_id: str,
    *,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """Replay a supplier request (dry-run by default)."""

    original = await db.supplier_debug_logs.find_one(
        {"_id": trace_id, "organization_id": organization_id}
    )
    if not original:
        return {"error": "trace_not_found"}

    if dry_run:
        return {
            "mode": "dry_run",
            "original_trace_id": trace_id,
            "supplier_code": original.get("supplier_code"),
            "operation": original.get("operation"),
            "request_payload": original.get("request_payload"),
            "original_response": original.get("response_payload"),
            "original_duration_ms": original.get("duration_ms"),
            "note": "Dry run — no actual supplier call made",
        }

    # Live replay
    from app.suppliers.registry import supplier_registry
    from app.suppliers.contracts.schemas import SupplierContext

    supplier_code = original.get("supplier_code")
    adapter = supplier_registry.get(supplier_code)

    ctx = SupplierContext(
        request_id=str(uuid.uuid4()),
        organization_id=organization_id,
    )

    start = time.monotonic()
    try:
        # For replay, we call healthcheck as a safe operation
        result = await adapter.healthcheck(ctx)
        duration_ms = int((time.monotonic() - start) * 1000)
        return {
            "mode": "live_replay",
            "original_trace_id": trace_id,
            "supplier_code": supplier_code,
            "healthcheck_result": result,
            "duration_ms": duration_ms,
            "success": True,
        }
    except Exception as e:
        duration_ms = int((time.monotonic() - start) * 1000)
        return {
            "mode": "live_replay",
            "original_trace_id": trace_id,
            "supplier_code": supplier_code,
            "error": str(e),
            "duration_ms": duration_ms,
            "success": False,
        }
