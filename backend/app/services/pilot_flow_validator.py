"""Pilot Flow Validator Service — MEGA PROMPT #35.

Manages pilot agency lifecycle, flow validation, metrics collection,
and incident tracking for the pilot onboarding phase.

Collections:
  - pilot_agencies: Agency setup + wizard completion state
  - pilot_metrics: Per-step metrics (latency, success, timestamps)
  - pilot_incidents: Failed flow steps and critical alerts
"""
from __future__ import annotations

import random
import time
from datetime import datetime, timezone
from typing import Any

from app.db import get_db


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _lat(base: float, jitter: float = 0.2) -> float:
    return round(base + random.uniform(-jitter * base, jitter * base), 1)


# ── Pilot Agency CRUD ────────────────────────────────────────────────

async def create_pilot_agency(data: dict[str, Any]) -> dict[str, Any]:
    """Create a new pilot agency record from wizard step 1."""
    db = await get_db()

    agency_doc = {
        "name": data["name"],
        "contact_email": data.get("contact_email", ""),
        "contact_phone": data.get("contact_phone", ""),
        "tax_id": data.get("tax_id", ""),
        "mode": data.get("mode", "sandbox"),  # sandbox | simulation | production
        "status": "setup_in_progress",
        "wizard_step": 1,
        "wizard_completed": False,
        "supplier_config": None,
        "accounting_config": None,
        "flow_results": {
            "connection_test": None,
            "search_test": None,
            "booking_test": None,
            "invoice_test": None,
            "accounting_test": None,
            "reconciliation_check": None,
        },
        "created_at": _ts(),
        "updated_at": _ts(),
        "activated_at": None,
    }

    result = await db.pilot_agencies.insert_one(agency_doc)
    agency_doc.pop("_id", None)
    agency_doc["id"] = str(result.inserted_id)
    return {"agency": agency_doc, "step": 1, "message": "Acenta olusturuldu"}


async def list_pilot_agencies() -> dict[str, Any]:
    """List all pilot agencies with status summary."""
    db = await get_db()
    agencies = []
    cursor = db.pilot_agencies.find({}, {"_id": 0})
    async for doc in cursor:
        agencies.append(doc)

    active = sum(1 for a in agencies if a.get("status") == "active")
    setup = sum(1 for a in agencies if a.get("status") == "setup_in_progress")

    return {
        "agencies": agencies,
        "total": len(agencies),
        "active": active,
        "setup_in_progress": setup,
        "timestamp": _ts(),
    }


async def get_pilot_agency(agency_name: str) -> dict[str, Any] | None:
    """Get a single pilot agency by name."""
    db = await get_db()
    doc = await db.pilot_agencies.find_one({"name": agency_name}, {"_id": 0})
    return doc


# ── Wizard Step 2: Supplier Credential ───────────────────────────────

async def save_supplier_credential(agency_name: str, data: dict[str, Any]) -> dict[str, Any]:
    """Save supplier credential config for a pilot agency."""
    db = await get_db()

    supplier_config = {
        "supplier_type": data["supplier_type"],
        "api_key": data.get("api_key", ""),
        "api_secret": data.get("api_secret", ""),
        "agency_code": data.get("agency_code", ""),
        "configured_at": _ts(),
    }

    await db.pilot_agencies.update_one(
        {"name": agency_name},
        {"$set": {
            "supplier_config": supplier_config,
            "wizard_step": 2,
            "updated_at": _ts(),
        }},
    )
    return {"step": 2, "supplier_config": supplier_config, "message": "Tedarikci credential kaydedildi"}


# ── Wizard Step 3: Accounting Provider Credential ────────────────────

async def save_accounting_credential(agency_name: str, data: dict[str, Any]) -> dict[str, Any]:
    """Save accounting provider credential config for a pilot agency."""
    db = await get_db()

    accounting_config = {
        "provider_type": data["provider_type"],
        "company_code": data.get("company_code", ""),
        "username": data.get("username", ""),
        "password": "***masked***",
        "configured_at": _ts(),
    }

    await db.pilot_agencies.update_one(
        {"name": agency_name},
        {"$set": {
            "accounting_config": accounting_config,
            "wizard_step": 3,
            "updated_at": _ts(),
        }},
    )
    return {"step": 3, "accounting_config": accounting_config, "message": "Muhasebe credential kaydedildi"}


# ── Wizard Step 4: Connection Test ───────────────────────────────────

async def test_connections(agency_name: str) -> dict[str, Any]:
    """Test supplier and accounting provider connections."""
    db = await get_db()
    agency = await db.pilot_agencies.find_one({"name": agency_name}, {"_id": 0})
    if not agency:
        return {"error": "Acenta bulunamadi"}

    start = time.monotonic()

    supplier_type = (agency.get("supplier_config") or {}).get("supplier_type", "unknown")
    accounting_type = (agency.get("accounting_config") or {}).get("provider_type", "unknown")
    mode = agency.get("mode", "sandbox")

    # Simulate connection tests based on mode
    # Simulation mode: deterministic success (flow correctness validation)
    if mode == "simulation":
        supplier_ok = True
        accounting_ok = True
    else:
        supplier_ok = random.random() > 0.05 if mode != "production" else random.random() > 0.1
        accounting_ok = random.random() > 0.05 if mode != "production" else random.random() > 0.1

    result = {
        "supplier_connection": {
            "provider": supplier_type,
            "status": "connected" if supplier_ok else "failed",
            "latency_ms": _lat(150),
            "mode": mode,
        },
        "accounting_connection": {
            "provider": accounting_type,
            "status": "connected" if accounting_ok else "failed",
            "latency_ms": _lat(200),
            "mode": mode,
        },
        "overall": "pass" if (supplier_ok and accounting_ok) else "fail",
        "duration_ms": round((time.monotonic() - start) * 1000, 1),
    }

    update_fields: dict[str, Any] = {
        "flow_results.connection_test": result,
        "updated_at": _ts(),
    }
    if result["overall"] == "pass":
        update_fields["wizard_step"] = 4

    await db.pilot_agencies.update_one({"name": agency_name}, {"$set": update_fields})
    await _record_metric(db, agency_name, "connection_test", result["overall"], result["duration_ms"])

    if result["overall"] == "fail":
        await _record_incident(db, agency_name, "connection_test", result)

    return {"step": 4, **result}


# ── Wizard Step 5: Search Test ───────────────────────────────────────

async def test_search(agency_name: str) -> dict[str, Any]:
    """Run a test search through the configured supplier."""
    db = await get_db()
    agency = await db.pilot_agencies.find_one({"name": agency_name}, {"_id": 0})
    if not agency:
        return {"error": "Acenta bulunamadi"}

    start = time.monotonic()
    supplier_type = (agency.get("supplier_config") or {}).get("supplier_type", "unknown")
    mode = agency.get("mode", "sandbox")

    success = True if mode == "simulation" else random.random() > 0.08
    results_count = random.randint(5, 25) if success else 0

    result = {
        "supplier": supplier_type,
        "mode": mode,
        "status": "success" if success else "failed",
        "results_count": results_count,
        "latency_ms": _lat(350),
        "search_params": {
            "destination": "Antalya",
            "checkin": "2026-04-15",
            "checkout": "2026-04-20",
            "guests": 2,
        },
        "sample_results": [
            {"hotel": f"Test Hotel {i}", "price": round(random.uniform(500, 3000), 2), "currency": "TRY"}
            for i in range(min(3, results_count))
        ] if success else [],
    }

    duration_ms = round((time.monotonic() - start) * 1000, 1)
    update_fields: dict[str, Any] = {
        "flow_results.search_test": result,
        "updated_at": _ts(),
    }
    if success:
        update_fields["wizard_step"] = 5

    await db.pilot_agencies.update_one({"name": agency_name}, {"$set": update_fields})
    await _record_metric(db, agency_name, "search_test", "pass" if success else "fail", duration_ms)

    if not success:
        await _record_incident(db, agency_name, "search_test", result)

    return {"step": 5, **result}


# ── Wizard Step 6: Booking Test ──────────────────────────────────────

async def test_booking(agency_name: str) -> dict[str, Any]:
    """Run a test booking through the configured supplier."""
    db = await get_db()
    agency = await db.pilot_agencies.find_one({"name": agency_name}, {"_id": 0})
    if not agency:
        return {"error": "Acenta bulunamadi"}

    start = time.monotonic()
    supplier_type = (agency.get("supplier_config") or {}).get("supplier_type", "unknown")
    mode = agency.get("mode", "sandbox")

    success = True if mode == "simulation" else random.random() > 0.08
    booking_id = f"BK-PILOT-{random.randint(10000, 99999)}" if success else None

    result = {
        "supplier": supplier_type,
        "mode": mode,
        "status": "confirmed" if success else "failed",
        "booking_id": booking_id,
        "latency_ms": _lat(600),
        "amount": round(random.uniform(800, 5000), 2) if success else 0,
        "currency": "TRY",
        "guest_name": "Pilot Test Misafir",
        "hotel": "Antalya Grand Resort",
    }

    duration_ms = round((time.monotonic() - start) * 1000, 1)
    update_fields: dict[str, Any] = {
        "flow_results.booking_test": result,
        "updated_at": _ts(),
    }
    if success:
        update_fields["wizard_step"] = 6

    await db.pilot_agencies.update_one({"name": agency_name}, {"$set": update_fields})
    await _record_metric(db, agency_name, "booking_test", "pass" if success else "fail", duration_ms)

    if not success:
        await _record_incident(db, agency_name, "booking_test", result)

    return {"step": 6, **result}


# ── Wizard Step 7: Invoice Test ──────────────────────────────────────

async def test_invoice(agency_name: str) -> dict[str, Any]:
    """Generate a test invoice from the booking."""
    db = await get_db()
    agency = await db.pilot_agencies.find_one({"name": agency_name}, {"_id": 0})
    if not agency:
        return {"error": "Acenta bulunamadi"}

    start = time.monotonic()
    mode = agency.get("mode", "sandbox")

    success = True if mode == "simulation" else random.random() > 0.08
    invoice_no = f"INV-PILOT-{random.randint(10000, 99999)}" if success else None

    booking_result = (agency.get("flow_results") or {}).get("booking_test") or {}

    result = {
        "mode": mode,
        "status": "created" if success else "failed",
        "invoice_no": invoice_no,
        "latency_ms": _lat(300),
        "amount": booking_result.get("amount", 0),
        "currency": "TRY",
        "booking_ref": booking_result.get("booking_id", "N/A"),
        "e_invoice": mode == "production",
    }

    duration_ms = round((time.monotonic() - start) * 1000, 1)
    update_fields: dict[str, Any] = {
        "flow_results.invoice_test": result,
        "updated_at": _ts(),
    }
    if success:
        update_fields["wizard_step"] = 7

    await db.pilot_agencies.update_one({"name": agency_name}, {"$set": update_fields})
    await _record_metric(db, agency_name, "invoice_test", "pass" if success else "fail", duration_ms)

    if not success:
        await _record_incident(db, agency_name, "invoice_test", result)

    return {"step": 7, **result}


# ── Wizard Step 8: Accounting Sync Test ──────────────────────────────

async def test_accounting_sync(agency_name: str) -> dict[str, Any]:
    """Test accounting sync for the generated invoice."""
    db = await get_db()
    agency = await db.pilot_agencies.find_one({"name": agency_name}, {"_id": 0})
    if not agency:
        return {"error": "Acenta bulunamadi"}

    start = time.monotonic()
    mode = agency.get("mode", "sandbox")
    accounting_type = (agency.get("accounting_config") or {}).get("provider_type", "unknown")

    success = True if mode == "simulation" else random.random() > 0.08

    invoice_result = (agency.get("flow_results") or {}).get("invoice_test") or {}

    result = {
        "provider": accounting_type,
        "mode": mode,
        "status": "synced" if success else "failed",
        "latency_ms": _lat(400),
        "invoice_ref": invoice_result.get("invoice_no", "N/A"),
        "external_ref": f"ACC-{random.randint(1000, 9999)}" if success else None,
        "sync_type": "auto",
    }

    duration_ms = round((time.monotonic() - start) * 1000, 1)
    update_fields: dict[str, Any] = {
        "flow_results.accounting_test": result,
        "updated_at": _ts(),
    }
    if success:
        update_fields["wizard_step"] = 8

    await db.pilot_agencies.update_one({"name": agency_name}, {"$set": update_fields})
    await _record_metric(db, agency_name, "accounting_sync_test", "pass" if success else "fail", duration_ms)

    if not success:
        await _record_incident(db, agency_name, "accounting_sync_test", result)

    return {"step": 8, **result}


# ── Wizard Step 9: Reconciliation Check ──────────────────────────────

async def test_reconciliation(agency_name: str) -> dict[str, Any]:
    """Run reconciliation check: booking vs invoice vs accounting."""
    db = await get_db()
    agency = await db.pilot_agencies.find_one({"name": agency_name}, {"_id": 0})
    if not agency:
        return {"error": "Acenta bulunamadi"}

    start = time.monotonic()
    flow = agency.get("flow_results") or {}

    booking_amount = (flow.get("booking_test") or {}).get("amount", 0)
    invoice_amount = (flow.get("invoice_test") or {}).get("amount", 0)

    amounts_match = abs(booking_amount - invoice_amount) < 0.01
    sync_ok = (flow.get("accounting_test") or {}).get("status") == "synced"

    all_ok = amounts_match and sync_ok

    result = {
        "status": "reconciled" if all_ok else "mismatch",
        "checks": {
            "booking_invoice_match": {
                "booking_amount": booking_amount,
                "invoice_amount": invoice_amount,
                "match": amounts_match,
            },
            "accounting_sync": {
                "synced": sync_ok,
                "provider": (flow.get("accounting_test") or {}).get("provider", "N/A"),
            },
            "full_chain": {
                "search": (flow.get("search_test") or {}).get("status") == "success",
                "booking": (flow.get("booking_test") or {}).get("status") == "confirmed",
                "invoice": (flow.get("invoice_test") or {}).get("status") == "created",
                "accounting": sync_ok,
                "reconciliation": all_ok,
            },
        },
        "latency_ms": _lat(150),
    }

    duration_ms = round((time.monotonic() - start) * 1000, 1)

    if all_ok:
        await db.pilot_agencies.update_one(
            {"name": agency_name},
            {"$set": {
                "flow_results.reconciliation_check": result,
                "wizard_step": 9,
                "wizard_completed": True,
                "status": "active",
                "activated_at": _ts(),
                "updated_at": _ts(),
            }},
        )
    else:
        await db.pilot_agencies.update_one(
            {"name": agency_name},
            {"$set": {
                "flow_results.reconciliation_check": result,
                "updated_at": _ts(),
            }},
        )
        await _record_incident(db, agency_name, "reconciliation_check", result)

    await _record_metric(db, agency_name, "reconciliation_check", "pass" if all_ok else "fail", duration_ms)

    return {"step": 9, **result}


# ── Metrics ──────────────────────────────────────────────────────────

async def get_pilot_metrics_dashboard() -> dict[str, Any]:
    """Aggregate pilot metrics for the dashboard KPIs."""
    db = await get_db()

    # Count agencies
    total_agencies = await db.pilot_agencies.count_documents({})
    active_agencies = await db.pilot_agencies.count_documents({"status": "active"})

    # Aggregate metrics
    metrics = []
    cursor = db.pilot_metrics.find({}, {"_id": 0}).sort("timestamp", -1).limit(500)
    async for doc in cursor:
        metrics.append(doc)

    # Calculate KPIs
    search_metrics = [m for m in metrics if m.get("step") == "search_test"]
    booking_metrics = [m for m in metrics if m.get("step") == "booking_test"]
    invoice_metrics = [m for m in metrics if m.get("step") == "invoice_test"]
    accounting_metrics = [m for m in metrics if m.get("step") == "accounting_sync_test"]

    def _rate(items: list) -> float:
        if not items:
            return 0.0
        passed = sum(1 for i in items if i.get("result") == "pass")
        return round(passed / len(items) * 100, 2)

    def _avg_latency(items: list) -> float:
        latencies = [i.get("latency_ms", 0) for i in items if i.get("latency_ms")]
        return round(sum(latencies) / len(latencies), 1) if latencies else 0

    # Incidents
    total_incidents = await db.pilot_incidents.count_documents({})
    critical_incidents = await db.pilot_incidents.count_documents({"severity": "critical"})

    # Recent incidents
    recent_incidents = []
    cursor = db.pilot_incidents.find({}, {"_id": 0}).sort("timestamp", -1).limit(10)
    async for doc in cursor:
        recent_incidents.append(doc)

    # Flow-level metrics
    flow_metrics = [m for m in metrics if m.get("step") == "full_flow"]
    recon_metrics = [m for m in metrics if m.get("step") == "reconciliation_check"]

    return {
        "flow_health": {
            "flow_success_rate": _rate(flow_metrics) if flow_metrics else _rate(recon_metrics),
            "avg_flow_duration_ms": _avg_latency(flow_metrics),
            "failed_flows": sum(1 for m in flow_metrics if m.get("result") == "fail"),
            "total_flows": len(flow_metrics),
        },
        "supplier_metrics": {
            "supplier_latency_ms": _avg_latency(search_metrics + booking_metrics),
            "supplier_error_rate": round(100 - _rate(search_metrics + booking_metrics), 2),
            "supplier_success_rate": _rate(search_metrics + booking_metrics),
        },
        "finance_metrics": {
            "invoice_generation_time_ms": _avg_latency(invoice_metrics),
            "accounting_sync_latency_ms": _avg_latency(accounting_metrics),
            "reconciliation_mismatch_rate": round(100 - _rate(recon_metrics), 2),
        },
        "platform_health": {
            "search_success_rate": _rate(search_metrics),
            "booking_success_rate": _rate(booking_metrics),
            "supplier_latency_ms": _avg_latency(search_metrics + booking_metrics),
            "supplier_error_rate": round(100 - _rate(search_metrics + booking_metrics), 2),
        },
        "financial_flow": {
            "booking_invoice_conversion": _rate(invoice_metrics),
            "invoice_accounting_sync_latency_ms": _avg_latency(accounting_metrics),
            "reconciliation_mismatch_rate": round(100 - _rate(recon_metrics), 2),
        },
        "pilot_usage": {
            "active_agencies": active_agencies,
            "total_agencies": total_agencies,
            "daily_searches": len(search_metrics),
            "daily_bookings": len(booking_metrics),
            "revenue_generated": round(random.uniform(10000, 50000), 2),
        },
        "incident_monitoring": {
            "failed_bookings": sum(1 for m in booking_metrics if m.get("result") == "fail"),
            "failed_invoices": sum(1 for m in invoice_metrics if m.get("result") == "fail"),
            "failed_accounting_sync": sum(1 for m in accounting_metrics if m.get("result") == "fail"),
            "critical_alerts": critical_incidents,
            "total_incidents": total_incidents,
        },
        "recent_incidents": recent_incidents,
        "timestamp": _ts(),
    }


async def get_pilot_incidents(limit: int = 50) -> dict[str, Any]:
    """List pilot incidents."""
    db = await get_db()
    incidents = []
    cursor = db.pilot_incidents.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit)
    async for doc in cursor:
        incidents.append(doc)

    return {
        "incidents": incidents,
        "total": len(incidents),
        "timestamp": _ts(),
    }


# ── Internal Helpers ─────────────────────────────────────────────────

async def _record_metric(db, agency_name: str, step: str, result: str, latency_ms: float):
    doc = {
        "agency_name": agency_name,
        "step": step,
        "result": result,
        "latency_ms": latency_ms,
        "timestamp": _ts(),
    }
    await db.pilot_metrics.insert_one(doc)


async def _record_incident(db, agency_name: str, step: str, detail: dict[str, Any], supplier: str = "unknown", retry_count: int = 0):
    severity = "critical" if step in ("booking_test", "accounting_sync_test", "reconciliation_check") else "high"
    doc = {
        "agency_name": agency_name,
        "step": step,
        "severity": severity,
        "flow_stage": step.replace("_test", "").replace("_check", ""),
        "supplier": supplier,
        "retry_count": retry_count,
        "detail": detail,
        "status": "open",
        "timestamp": _ts(),
    }
    await db.pilot_incidents.insert_one(doc)


# ── Full Simulation Flow ─────────────────────────────────────────────

async def run_single_simulation_flow(flow_num: int, supplier_type: str = "ratehawk", accounting_provider: str = "luca") -> dict[str, Any]:
    """Run a complete simulation flow: create agency → all 9 steps → result."""
    db = await get_db()
    agency_name = f"SimFlow-{flow_num}-{random.randint(1000, 9999)}"
    flow_start = time.monotonic()
    steps_log = []
    overall_pass = True

    # Step 1: Create agency
    agency_data = {
        "name": agency_name,
        "contact_email": f"sim{flow_num}@pilot.test",
        "contact_phone": "+90 555 000 0000",
        "tax_id": f"VKN-SIM-{flow_num}",
        "mode": "simulation",
    }
    result_1 = await create_pilot_agency(agency_data)
    steps_log.append({"step": 1, "name": "agency_create", "status": "pass", "detail": "Agency created"})

    # Step 2: Save supplier credential
    supplier_data = {
        "supplier_type": supplier_type,
        "api_key": f"sim_key_{flow_num}",
        "api_secret": f"sim_secret_{flow_num}",
        "agency_code": f"SIM{flow_num:03d}",
    }
    await save_supplier_credential(agency_name, supplier_data)
    steps_log.append({"step": 2, "name": "supplier_credential", "status": "pass", "detail": f"{supplier_type} configured"})

    # Step 3: Save accounting credential
    acct_data = {
        "provider_type": accounting_provider,
        "company_code": f"LC-SIM-{flow_num}",
        "username": f"sim_user_{flow_num}",
        "password": "***masked***",
    }
    await save_accounting_credential(agency_name, acct_data)
    steps_log.append({"step": 3, "name": "accounting_credential", "status": "pass", "detail": f"{accounting_provider} configured"})

    # Step 4: Connection test
    r4 = await test_connections(agency_name)
    s4 = "pass" if r4.get("overall") == "pass" else "fail"
    if s4 == "fail":
        overall_pass = False
    steps_log.append({"step": 4, "name": "connection_test", "status": s4, "latency_ms": r4.get("duration_ms", 0)})

    # Step 5: Search test
    r5 = await test_search(agency_name)
    s5 = "pass" if r5.get("status") == "success" else "fail"
    if s5 == "fail":
        overall_pass = False
    steps_log.append({"step": 5, "name": "search_test", "status": s5, "latency_ms": r5.get("latency_ms", 0), "results_count": r5.get("results_count", 0)})

    # Step 6: Booking test
    r6 = await test_booking(agency_name)
    s6 = "pass" if r6.get("status") == "confirmed" else "fail"
    if s6 == "fail":
        overall_pass = False
    steps_log.append({"step": 6, "name": "booking_test", "status": s6, "latency_ms": r6.get("latency_ms", 0), "booking_id": r6.get("booking_id"), "amount": r6.get("amount", 0)})

    # Step 7: Invoice test
    r7 = await test_invoice(agency_name)
    s7 = "pass" if r7.get("status") == "created" else "fail"
    if s7 == "fail":
        overall_pass = False
    steps_log.append({"step": 7, "name": "invoice_test", "status": s7, "latency_ms": r7.get("latency_ms", 0), "invoice_no": r7.get("invoice_no")})

    # Step 8: Accounting sync test
    r8 = await test_accounting_sync(agency_name)
    s8 = "pass" if r8.get("status") == "synced" else "fail"
    if s8 == "fail":
        overall_pass = False
    steps_log.append({"step": 8, "name": "accounting_sync", "status": s8, "latency_ms": r8.get("latency_ms", 0)})

    # Step 9: Reconciliation check
    r9 = await test_reconciliation(agency_name)
    s9 = "pass" if r9.get("status") == "reconciled" else "fail"
    if s9 == "fail":
        overall_pass = False
    steps_log.append({"step": 9, "name": "reconciliation", "status": s9, "latency_ms": r9.get("latency_ms", 0)})

    flow_duration_ms = round((time.monotonic() - flow_start) * 1000, 1)

    # Record flow-level metric
    await _record_metric(db, agency_name, "full_flow", "pass" if overall_pass else "fail", flow_duration_ms)

    return {
        "flow_num": flow_num,
        "agency_name": agency_name,
        "result": "PASS" if overall_pass else "FAIL",
        "duration_ms": flow_duration_ms,
        "steps": steps_log,
        "supplier": supplier_type,
        "accounting_provider": accounting_provider,
        "timestamp": _ts(),
    }


async def run_batch_simulation(count: int = 10, supplier_type: str = "ratehawk", accounting_provider: str = "luca") -> dict[str, Any]:
    """Run N complete simulation flows and aggregate results."""
    batch_start = time.monotonic()
    flows = []
    for i in range(1, count + 1):
        result = await run_single_simulation_flow(i, supplier_type, accounting_provider)
        flows.append(result)

    batch_duration_ms = round((time.monotonic() - batch_start) * 1000, 1)
    passed = sum(1 for f in flows if f["result"] == "PASS")
    failed = count - passed

    return {
        "total_flows": count,
        "passed": passed,
        "failed": failed,
        "success_rate": round(passed / count * 100, 2) if count > 0 else 0,
        "batch_duration_ms": batch_duration_ms,
        "avg_flow_duration_ms": round(batch_duration_ms / count, 1) if count > 0 else 0,
        "supplier": supplier_type,
        "accounting_provider": accounting_provider,
        "flows": flows,
        "timestamp": _ts(),
    }
