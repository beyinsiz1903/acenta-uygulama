"""P2 — Supplier Sandbox Service.

Provides: mock responses, test bookings, fault injection.
"""
from __future__ import annotations

import logging
import random
import uuid
from datetime import datetime, timezone
from typing import Any

from app.domain.reliability.models import FAULT_TYPES, SANDBOX_MODES

logger = logging.getLogger("reliability.sandbox")


async def get_sandbox_config(db, org_id: str) -> dict[str, Any]:
    """Get sandbox configuration."""
    doc = await db.rel_sandbox_config.find_one({"organization_id": org_id}, {"_id": 0})
    if not doc:
        return {
            "organization_id": org_id,
            "enabled": False,
            "mode": "mock",
            "available_modes": SANDBOX_MODES,
            "fault_injection": {"enabled": False, "fault_types": FAULT_TYPES, "probability": 0.0},
            "suppliers": {},
        }
    return doc


async def update_sandbox_config(db, org_id: str, config: dict, actor: str) -> dict[str, Any]:
    """Update sandbox configuration."""
    now = datetime.now(timezone.utc).isoformat()
    config["organization_id"] = org_id
    config["updated_at"] = now
    config["updated_by"] = actor
    await db.rel_sandbox_config.update_one(
        {"organization_id": org_id},
        {"$set": config, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    return {"status": "updated", "config": config}


async def execute_sandbox_call(
    db, org_id: str, supplier_code: str, method: str, payload: dict
) -> dict[str, Any]:
    """Execute a call through the sandbox (mock/fault injection)."""
    config = await get_sandbox_config(db, org_id)
    mode = config.get("mode", "mock")
    fault_cfg = config.get("fault_injection", {})

    # Check fault injection
    if fault_cfg.get("enabled") and random.random() < fault_cfg.get("probability", 0):
        fault = random.choice(fault_cfg.get("fault_types", FAULT_TYPES[:3]))
        result = _generate_fault_response(supplier_code, method, fault)
    else:
        result = _generate_mock_response(supplier_code, method, payload)

    # Log sandbox call
    await db.rel_sandbox_log.insert_one({
        "organization_id": org_id,
        "supplier_code": supplier_code,
        "method": method,
        "mode": mode,
        "payload": payload,
        "result": result,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return result


async def get_sandbox_log(db, org_id: str, supplier_code: str | None = None, limit: int = 50) -> list[dict]:
    """Get sandbox call history."""
    match = {"organization_id": org_id}
    if supplier_code:
        match["supplier_code"] = supplier_code
    cursor = db.rel_sandbox_log.find(match, {"_id": 0}).sort("timestamp", -1).limit(limit)
    return await cursor.to_list(limit)


def _generate_mock_response(supplier_code: str, method: str, payload: dict) -> dict[str, Any]:
    """Generate realistic mock response."""
    base = {
        "sandbox": True,
        "supplier_code": supplier_code,
        "method": method,
        "request_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if method == "search":
        base["items"] = [
            {"item_id": str(uuid.uuid4()), "name": f"Sandbox Item {i+1}", "price": round(1000 + i * 500, 2), "available": True}
            for i in range(3)
        ]
        base["total_items"] = 3
    elif method == "confirm":
        base["booking_id"] = f"SBX-{uuid.uuid4().hex[:8].upper()}"
        base["status"] = "confirmed"
        base["confirmation_code"] = f"SCONF-{uuid.uuid4().hex[:6].upper()}"
    elif method == "cancel":
        base["status"] = "cancelled"
        base["refund_amount"] = 1500.0
    elif method == "hold":
        base["hold_id"] = f"SHOLD-{uuid.uuid4().hex[:8].upper()}"
        base["status"] = "held"
    else:
        base["status"] = "ok"
    return base


def _generate_fault_response(supplier_code: str, method: str, fault_type: str) -> dict[str, Any]:
    """Generate a faulty response for fault injection."""
    base = {
        "sandbox": True,
        "fault_injected": True,
        "fault_type": fault_type,
        "supplier_code": supplier_code,
        "method": method,
    }
    if fault_type == "timeout":
        base["error"] = "Request timed out after 8000ms"
        base["status_code"] = 504
    elif fault_type == "error_500":
        base["error"] = "Internal Server Error"
        base["status_code"] = 500
    elif fault_type == "error_429":
        base["error"] = "Too Many Requests"
        base["status_code"] = 429
        base["retry_after"] = 60
    elif fault_type == "partial_response":
        base["items"] = [{"item_id": str(uuid.uuid4()), "name": "Partial Item"}]
        base["degraded"] = True
        base["warning"] = "Partial response — some fields missing"
    elif fault_type == "schema_mismatch":
        base["unexpected_field"] = "this_should_not_be_here"
        base["items"] = "invalid_type_should_be_array"
    elif fault_type == "empty_response":
        base = {}
    elif fault_type == "invalid_json":
        base["error"] = "Simulated invalid JSON parse error"
        base["raw_body"] = "{broken json..."
    else:
        base["error"] = f"Simulated fault: {fault_type}"
        base["status_code"] = 503
    return base
