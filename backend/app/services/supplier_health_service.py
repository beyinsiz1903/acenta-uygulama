from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from app.schemas_supplier_health import SupplierCircuitOut, SupplierHealthItemOut, SupplierMetricsOut
from app.utils import now_utc

WINDOW_SEC_DEFAULT = 900
CIRCUIT_OPEN_FAIL_THRESHOLD = 3
CIRCUIT_OPEN_DURATION_SEC = 120


async def _compute_metrics_from_events(
    db,
    *,
    organization_id: str,
    supplier_code: str,
    window_sec: int = WINDOW_SEC_DEFAULT,
) -> Tuple[SupplierMetricsOut, list[Dict[str, Any]]]:
    """Aggregate metrics from supplier_health_events for the given window.

    Returns (metrics_model, raw_events).
    """

    now = now_utc()
    window_start = now - timedelta(seconds=window_sec)

    flt = {
        "organization_id": organization_id,
        "supplier_code": supplier_code,
        "created_at": {"$gte": window_start},
    }

    events: list[Dict[str, Any]] = []
    async for ev in db.supplier_health_events.find(flt, {"_id": 0}).sort("created_at", 1):
        events.append(ev)

    total = len(events)
    success = sum(1 for e in events if e.get("ok"))
    fail = total - success

    if total > 0:
        success_rate = success / total
        error_rate = fail / total
    else:
        success_rate = 0.0
        error_rate = 0.0

    durations = [int(e.get("duration_ms") or 0) for e in events if e.get("duration_ms") is not None]
    if durations:
        durations_sorted = sorted(durations)
        avg_latency = int(sum(durations_sorted) / len(durations_sorted))
        idx = max(int(0.95 * len(durations_sorted)) - 1, 0)
        p95_latency = int(durations_sorted[idx])
    else:
        avg_latency = 0
        p95_latency = 0

    last_error_codes: list[str] = [
        e.get("code")
        for e in events
        if not e.get("ok") and e.get("code")
    ]
    # keep only last 10
    if len(last_error_codes) > 10:
        last_error_codes = last_error_codes[-10:]

    metrics = SupplierMetricsOut(
        total_calls=total,
        success_calls=success,
        fail_calls=fail,
        success_rate=success_rate,
        error_rate=error_rate,
        avg_latency_ms=avg_latency,
        p95_latency_ms=p95_latency,
        last_error_codes=last_error_codes,
    )
    return metrics, events


async def _load_circuit_state(db, *, organization_id: str, supplier_code: str) -> SupplierCircuitOut:
    doc = await db.supplier_health.find_one(
        {"organization_id": organization_id, "supplier_code": supplier_code},
        {"_id": 0, "circuit": 1},
    )
    base = {
        "state": "closed",
        "opened_at": None,
        "until": None,
        "reason_code": None,
        "consecutive_failures": 0,
        "last_transition_at": None,
    }
    if doc and doc.get("circuit"):
        base.update(doc["circuit"])
    return SupplierCircuitOut(**base)


async def record_supplier_call_event(
    db,
    *,
    organization_id: str,
    supplier_code: str,
    ok: bool,
    code: Optional[str],
    http_status: Optional[int],
    duration_ms: Optional[int],
    window_sec: int = WINDOW_SEC_DEFAULT,
) -> None:
    """Append a health event and recompute snapshot + circuit (fail-open)."""

    try:
        now = now_utc()
        ev = {
            "organization_id": organization_id,
            "supplier_code": supplier_code,
            "created_at": now,
            "ok": bool(ok),
            "code": code,
            "http_status": http_status,
            "duration_ms": int(duration_ms) if duration_ms is not None else None,
        }
        await db.supplier_health_events.insert_one(ev)

        metrics, events = await _compute_metrics_from_events(
            db,
            organization_id=organization_id,
            supplier_code=supplier_code,
            window_sec=window_sec,
        )

        circuit = await _load_circuit_state(db, organization_id=organization_id, supplier_code=supplier_code)
        now = now_utc()

        # Auto-close if window has passed for open circuits
        if circuit.state == "open" and circuit.until and now >= circuit.until:
            previous_state = circuit.state
            circuit = SupplierCircuitOut(
                state="closed",
                opened_at=None,
                until=None,
                reason_code=None,
                consecutive_failures=0,
                last_transition_at=now,
            )
            try:
                from uuid import uuid4

                await db.audit_logs.insert_one(
                    {
                        "_id": str(uuid4()),
                        "organization_id": organization_id,
                        "actor": {
                            "actor_type": "system",
                            "actor_id": "system",
                            "email": None,
                            "roles": [],
                        },
                        "origin": {},
                        "action": "SUPPLIER_CIRCUIT_CLOSED",
                        "target": {"type": "supplier", "id": supplier_code},
                        "diff": {},
                        "meta": {
                            "supplier_code": supplier_code,
                            "previous_state": previous_state,
                            "new_state": "closed",
                            "window_sec": window_sec,
                        },
                        "created_at": now_utc(),
                    }
                )
            except Exception:
                pass

        # Compute consecutive failures as trailing failures in the current window
        consecutive_failures = 0
        for ev in reversed(events):
            if ev.get("ok"):
                break
            consecutive_failures += 1

        new_state = circuit.state
        opened_at = circuit.opened_at
        until = circuit.until
        reason_code = circuit.reason_code
        last_transition_at = circuit.last_transition_at

        # Possibly open circuit
        if not ok and circuit.state == "closed" and consecutive_failures >= CIRCUIT_OPEN_FAIL_THRESHOLD:
            previous_state = circuit.state
            new_state = "open"
            opened_at = now
            until = now + timedelta(seconds=CIRCUIT_OPEN_DURATION_SEC)
            reason_code = code
            last_transition_at = now

            try:
                from uuid import uuid4

                await db.audit_logs.insert_one(
                    {
                        "_id": str(uuid4()),
                        "organization_id": organization_id,
                        "actor": {
                            "actor_type": "system",
                            "actor_id": "system",
                            "email": None,
                            "roles": [],
                        },
                        "origin": {},
                        "action": "SUPPLIER_CIRCUIT_OPENED",
                        "target": {"type": "supplier", "id": supplier_code},
                        "diff": {},
                        "meta": {
                            "supplier_code": supplier_code,
                            "previous_state": previous_state,
                            "new_state": new_state,
                            "reason_code": reason_code,
                            "until": until.isoformat() if until else None,
                            "window_sec": window_sec,
                            "consecutive_failures": consecutive_failures,
                        },
                        "created_at": now_utc(),
                    }
                )
            except Exception:
                pass

        circuit_doc: Dict[str, Any] = {
            "state": new_state,
            "opened_at": opened_at,
            "until": until,
            "reason_code": reason_code,
            "consecutive_failures": consecutive_failures,
            "last_transition_at": last_transition_at,
        }

        await db.supplier_health.update_one(
            {"organization_id": organization_id, "supplier_code": supplier_code},
            {
                "$set": {
                    "organization_id": organization_id,
                    "supplier_code": supplier_code,
                    "window_sec": window_sec,
                    "metrics": metrics.model_dump(),
                    "circuit": circuit_doc,
                    "updated_at": now,
                }
            },
            upsert=True,
        )

    except Exception:
        # Fail-open: supplier calls must not break because of health bookkeeping
        return None


async def is_supplier_circuit_open(
    db,
    *,
    organization_id: str,
    supplier_code: str,
    window_sec: int = WINDOW_SEC_DEFAULT,
) -> bool:
    """Check if circuit is effectively open; auto-close when until has passed.

    Returns True if circuit is open *and* now < until, else False.
    """

    try:
        now = now_utc()
        doc = await db.supplier_health.find_one(
            {"organization_id": organization_id, "supplier_code": supplier_code},
            {"_id": 0},
        )
        if not doc or not doc.get("circuit"):
            return False

        circuit = SupplierCircuitOut(**doc["circuit"])

        if circuit.state != "open":
            return False

        if circuit.until and now >= circuit.until:
            # Auto-close and treat as closed (exactly-once via conditional update)
            from uuid import uuid4

            result = await db.supplier_health.update_one(
                {
                    "organization_id": organization_id,
                    "supplier_code": supplier_code,
                    "circuit.state": "open",
                    "circuit.until": {"$lte": now},
                },
                {
                    "$set": {
                        "circuit.state": "closed",
                        "circuit.opened_at": None,
                        "circuit.until": None,
                        "circuit.reason_code": None,
                        "circuit.consecutive_failures": 0,
                        "circuit.last_transition_at": now,
                    }
                },
            )
            if result.modified_count == 1:
                try:
                    await db.audit_logs.insert_one(
                        {
                            "_id": str(uuid4()),
                            "organization_id": organization_id,
                            "actor": {
                                "actor_type": "system",
                                "actor_id": "system",
                                "email": None,
                                "roles": [],
                            },
                            "origin": {},
                            "action": "SUPPLIER_CIRCUIT_CLOSED",
                            "target": {"type": "supplier", "id": supplier_code},
                            "diff": {},
                            "meta": {
                                "supplier_code": supplier_code,
                                "previous_state": "open",
                                "new_state": "closed",
                                "window_sec": window_sec,
                            },
                            "created_at": now,
                        }
                    )
                except Exception:
                    pass
            return False

        # still open and within until
        return True
    except Exception:
        return False


async def list_supplier_health(
    db,
    *,
    organization_id: str,
    supplier_codes: Optional[list[str]] = None,
    window_sec: int = WINDOW_SEC_DEFAULT,
) -> tuple[int, list[SupplierHealthItemOut], Optional[datetime]]:
    flt: Dict[str, Any] = {"organization_id": organization_id}
    if supplier_codes:
        flt["supplier_code"] = {"$in": supplier_codes}

    cursor = db.supplier_health.find(flt, {"_id": 0})
    docs: list[Dict[str, Any]] = []
    async for d in cursor:
        docs.append(d)

    updated_at: Optional[datetime] = None
    items: list[SupplierHealthItemOut] = []
    for d in docs:
        metrics = SupplierMetricsOut(**(d.get("metrics") or {}))
        circuit = SupplierCircuitOut(**(d.get("circuit") or {}))
        item = SupplierHealthItemOut(
            supplier_code=d.get("supplier_code"),
            metrics=metrics,
            circuit=circuit,
        )
        items.append(item)
        if d.get("updated_at") and (updated_at is None or d["updated_at"] > updated_at):
            updated_at = d["updated_at"]

    # Deterministic order by supplier_code
    items.sort(key=lambda x: x.supplier_code)

    return len(items), items, updated_at


async def get_supplier_health(
    db,
    *,
    organization_id: str,
    supplier_code: str,
) -> Optional[SupplierHealthItemOut]:
    doc = await db.supplier_health.find_one(
        {"organization_id": organization_id, "supplier_code": supplier_code},
        {"_id": 0},
    )
    if not doc:
        return None

    metrics = SupplierMetricsOut(**(doc.get("metrics") or {}))
    circuit = SupplierCircuitOut(**(doc.get("circuit") or {}))
    return SupplierHealthItemOut(
        supplier_code=doc.get("supplier_code"),
        metrics=metrics,
        circuit=circuit,
    )
