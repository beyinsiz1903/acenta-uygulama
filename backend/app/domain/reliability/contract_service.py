"""P6 — Contract Validation Service.

Schema validation to detect supplier API changes. Rejects unexpected payloads.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

from app.domain.reliability.models import (
    REQUIRED_CANCEL_FIELDS,
    REQUIRED_CONFIRM_FIELDS,
    REQUIRED_SEARCH_FIELDS,
    VALIDATION_MODES,
)

logger = logging.getLogger("reliability.contract")


def compute_schema_hash(payload: dict) -> str:
    """Compute a hash of the payload structure (keys only, not values)."""
    def _extract_keys(obj, prefix=""):
        keys = []
        if isinstance(obj, dict):
            for k in sorted(obj.keys()):
                full_key = f"{prefix}.{k}" if prefix else k
                keys.append(full_key)
                keys.extend(_extract_keys(obj[k], full_key))
        elif isinstance(obj, list) and obj:
            keys.extend(_extract_keys(obj[0], f"{prefix}[]"))
        return keys
    key_str = "|".join(_extract_keys(payload))
    return hashlib.sha256(key_str.encode()).hexdigest()[:16]


def validate_search_response(payload: dict) -> dict[str, Any]:
    """Validate a supplier search response against the expected contract."""
    violations = []
    items = payload.get("items", [])
    if not isinstance(items, list):
        return {"valid": False, "violations": [{"field": "items", "issue": "Expected array, got " + type(items).__name__}]}

    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            violations.append({"field": f"items[{idx}]", "issue": "Expected object"})
            continue
        for field in REQUIRED_SEARCH_FIELDS:
            if field not in item:
                violations.append({"field": f"items[{idx}].{field}", "issue": "Missing required field"})

    return {"valid": len(violations) == 0, "violations": violations, "items_checked": len(items)}


def validate_confirm_response(payload: dict) -> dict[str, Any]:
    """Validate a supplier confirm response."""
    violations = []
    for field in REQUIRED_CONFIRM_FIELDS:
        if field not in payload:
            violations.append({"field": field, "issue": "Missing required field"})
    return {"valid": len(violations) == 0, "violations": violations}


def validate_cancel_response(payload: dict) -> dict[str, Any]:
    """Validate a supplier cancel response."""
    violations = []
    for field in REQUIRED_CANCEL_FIELDS:
        if field not in payload:
            violations.append({"field": field, "issue": "Missing required field"})
    return {"valid": len(violations) == 0, "violations": violations}


async def validate_and_log(
    db, org_id: str, supplier_code: str, method: str, payload: dict, mode: str = "strict"
) -> dict[str, Any]:
    """Validate a supplier response and log violations."""
    if method == "search":
        result = validate_search_response(payload)
    elif method == "confirm":
        result = validate_confirm_response(payload)
    elif method == "cancel":
        result = validate_cancel_response(payload)
    else:
        result = {"valid": True, "violations": [], "note": f"No contract defined for '{method}'"}

    schema_hash = compute_schema_hash(payload)
    result["schema_hash"] = schema_hash
    result["mode"] = mode

    # Check for schema drift
    last_hash = await db.rel_contract_schemas.find_one(
        {"organization_id": org_id, "supplier_code": supplier_code, "method": method},
        {"_id": 0, "schema_hash": 1},
    )
    if last_hash and last_hash.get("schema_hash") != schema_hash:
        result["schema_drift"] = True
        result["previous_hash"] = last_hash["schema_hash"]
    else:
        result["schema_drift"] = False

    # Store current schema hash
    now = datetime.now(timezone.utc).isoformat()
    await db.rel_contract_schemas.update_one(
        {"organization_id": org_id, "supplier_code": supplier_code, "method": method},
        {
            "$set": {"schema_hash": schema_hash, "updated_at": now, "sample_keys": list(payload.keys())[:20]},
            "$setOnInsert": {"organization_id": org_id, "supplier_code": supplier_code, "method": method, "created_at": now},
        },
        upsert=True,
    )

    # Log violations
    if not result["valid"]:
        await db.rel_contract_violations.insert_one({
            "organization_id": org_id,
            "supplier_code": supplier_code,
            "method": method,
            "violations": result["violations"],
            "schema_hash": schema_hash,
            "mode": mode,
            "timestamp": now,
        })

    return result


async def get_contract_status(db, org_id: str) -> dict[str, Any]:
    """Get contract validation status for all suppliers."""
    schemas = await db.rel_contract_schemas.find({"organization_id": org_id}, {"_id": 0}).to_list(200)

    # Recent violations
    pipeline = [
        {"$match": {"organization_id": org_id}},
        {"$group": {
            "_id": {"supplier_code": "$supplier_code", "method": "$method"},
            "violation_count": {"$sum": 1},
            "last_violation": {"$max": "$timestamp"},
        }},
    ]
    violations = await db.rel_contract_violations.aggregate(pipeline).to_list(200)
    violation_map = {f"{v['_id']['supplier_code']}:{v['_id']['method']}": v for v in violations}

    results = []
    for s in schemas:
        key = f"{s['supplier_code']}:{s['method']}"
        v = violation_map.get(key, {})
        results.append({
            "supplier_code": s["supplier_code"],
            "method": s["method"],
            "schema_hash": s.get("schema_hash"),
            "last_updated": s.get("updated_at"),
            "violation_count": v.get("violation_count", 0),
            "last_violation": v.get("last_violation"),
        })
    return {"contracts": results, "validation_modes": VALIDATION_MODES}
