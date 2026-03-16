"""E2E Demo & Certification Console Service.

Executes full booking lifecycle tests with configurable edge-case scenarios.
Provides rich operational data for the Supplier Certification Console UI.

Scenarios:
  - success:              Normal happy-path flow
  - price_mismatch:       Price changes between search and revalidation
  - delayed_confirmation: Booking confirmation takes multiple polling rounds
  - booking_timeout:      Booking creation exceeds timeout threshold
  - cancel_success:       Normal cancel after successful booking
  - supplier_unavailable: Supplier API is unreachable during search
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

from app.db import get_db

logger = logging.getLogger("e2e_demo")

SCENARIOS = {
    "success": {
        "name": "Success Flow",
        "description": "All steps pass — happy path end-to-end booking",
        "icon": "check-circle",
    },
    "price_mismatch": {
        "name": "Price Mismatch",
        "description": "Price changes between search and revalidation (+12% drift)",
        "icon": "alert-triangle",
    },
    "delayed_confirmation": {
        "name": "Delayed Confirmation",
        "description": "Booking requires extended polling (5 rounds, 8s total)",
        "icon": "clock",
    },
    "booking_timeout": {
        "name": "Booking Timeout",
        "description": "Booking creation exceeds the 30s timeout threshold",
        "icon": "x-circle",
    },
    "cancel_success": {
        "name": "Cancel Success",
        "description": "Full flow with successful cancellation and refund",
        "icon": "rotate-ccw",
    },
    "supplier_unavailable": {
        "name": "Supplier Unavailable",
        "description": "Supplier API returns HTTP 503 during search",
        "icon": "wifi-off",
    },
}

LIFECYCLE_STEPS = [
    {"id": "search", "name": "Search", "description": "Availability search query"},
    {"id": "detail", "name": "Hotel Detail", "description": "Hotel/product detail fetch"},
    {"id": "revalidation", "name": "Revalidation", "description": "Price revalidation / precheck"},
    {"id": "booking", "name": "Booking", "description": "Booking creation"},
    {"id": "status_check", "name": "Status Polling", "description": "Booking status check"},
    {"id": "cancel", "name": "Cancel", "description": "Booking cancellation"},
]


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _req_id() -> str:
    return f"req_{uuid.uuid4().hex[:12]}"


SUPPLIER_META = {
    "ratehawk": {"name": "RateHawk", "mode": "simulation", "base_url": "api.worldota.net"},
    "paximum": {"name": "Paximum", "mode": "simulation", "base_url": "api.paximum.com"},
    "tbo": {"name": "TBO Holidays", "mode": "simulation", "base_url": "api.tbotechnology.in"},
    "wtatil": {"name": "WTatil", "mode": "simulation", "base_url": "b2b-api.wtatil.com"},
}


async def get_scenarios() -> dict[str, Any]:
    return {"scenarios": [{"id": k, **v} for k, v in SCENARIOS.items()]}


async def run_e2e_test(supplier: str, scenario: str = "success") -> dict[str, Any]:
    """Run a full E2E lifecycle test with a specific scenario."""
    if supplier not in SUPPLIER_META:
        return {"error": f"Unknown supplier: {supplier}", "available": list(SUPPLIER_META.keys())}
    if scenario not in SCENARIOS:
        return {"error": f"Unknown scenario: {scenario}", "available": list(SCENARIOS.keys())}

    meta = SUPPLIER_META[supplier]
    trace_id = f"trace_{uuid.uuid4().hex[:16]}"
    run_id = f"e2e_{supplier}_{uuid.uuid4().hex[:8]}"
    test_start = time.monotonic()
    steps = []

    checkin = (datetime.now(timezone.utc) + timedelta(days=14)).strftime("%Y-%m-%d")
    checkout = (datetime.now(timezone.utc) + timedelta(days=17)).strftime("%Y-%m-%d")

    for step_def in LIFECYCLE_STEPS:
        step_id = step_def["id"]
        request_id = _req_id()
        step_start = time.monotonic()

        result = await _execute_step(supplier, step_id, scenario, meta)

        duration_ms = round((time.monotonic() - step_start) * 1000, 1)
        steps.append({
            "id": step_id,
            "name": step_def["name"],
            "description": step_def["description"],
            "status": result["status"],
            "latency_ms": result.get("latency_ms", duration_ms),
            "request_id": request_id,
            "trace_id": trace_id,
            "supplier_request": result.get("supplier_request", {}),
            "supplier_response": result.get("supplier_response", {}),
            "message": result.get("message", ""),
            "error": result.get("error"),
            "warnings": result.get("warnings", []),
        })

        if result["status"] == "fail":
            for remaining in LIFECYCLE_STEPS[LIFECYCLE_STEPS.index(step_def) + 1:]:
                steps.append({
                    "id": remaining["id"],
                    "name": remaining["name"],
                    "description": remaining["description"],
                    "status": "skipped",
                    "latency_ms": 0,
                    "request_id": _req_id(),
                    "trace_id": trace_id,
                    "supplier_request": {},
                    "supplier_response": {},
                    "message": "Skipped — previous step failed",
                    "error": None,
                    "warnings": [],
                })
            break

    total_ms = round((time.monotonic() - test_start) * 1000, 1)
    passed = sum(1 for s in steps if s["status"] == "pass")
    failed = sum(1 for s in steps if s["status"] == "fail")
    warned = sum(1 for s in steps if s["status"] == "warn")
    skipped = sum(1 for s in steps if s["status"] == "skipped")
    total = len(steps)
    score = round((passed / total) * 100) if total > 0 else 0

    certification = {
        "score": score,
        "go_live_eligible": score >= 80,
        "threshold": 80,
        "passed": passed,
        "failed": failed,
        "warnings": warned,
        "skipped": skipped,
        "total": total,
        "failed_steps": [s["name"] for s in steps if s["status"] == "fail"],
        "warning_steps": [s["name"] for s in steps if s["status"] == "warn"],
    }

    test_result = {
        "run_id": run_id,
        "supplier": supplier,
        "supplier_name": meta["name"],
        "scenario": scenario,
        "scenario_name": SCENARIOS[scenario]["name"],
        "mode": meta["mode"],
        "trace_id": trace_id,
        "steps": steps,
        "summary": {
            "passed": passed,
            "failed": failed,
            "warned": warned,
            "skipped": skipped,
            "total": total,
        },
        "certification": certification,
        "total_duration_ms": total_ms,
        "test_params": {
            "destination": "Antalya",
            "checkin": checkin,
            "checkout": checkout,
            "guests": "2 adults",
        },
        "timestamp": _ts(),
    }

    db = await get_db()
    await db.e2e_demo_tests.insert_one({**test_result, "_recorded_at": _ts()})

    return test_result


async def _execute_step(supplier: str, step_id: str, scenario: str, meta: dict) -> dict[str, Any]:
    """Execute a single lifecycle step based on the scenario."""

    if scenario == "supplier_unavailable" and step_id == "search":
        await asyncio.sleep(0.8)
        return {
            "status": "fail",
            "latency_ms": 3200,
            "message": f"Supplier API unreachable — HTTP 503 from {meta['base_url']}",
            "error": f"ConnectionError: {meta['base_url']} returned 503 Service Unavailable",
            "supplier_request": {
                "method": "POST",
                "url": f"https://{meta['base_url']}/v1/search/availability",
                "headers": {"Authorization": "Bearer ***", "Content-Type": "application/json", "X-Request-ID": _req_id()},
                "body": {"destination": "Antalya", "checkin": "2026-03-30", "checkout": "2026-04-02", "guests": [{"adults": 2}]},
            },
            "supplier_response": {"http_status": 503, "body": "Service Unavailable"},
        }

    if scenario == "price_mismatch" and step_id == "revalidation":
        await asyncio.sleep(0.5)
        return {
            "status": "warn",
            "latency_ms": 890,
            "message": "Price drift detected — search: EUR 142.50, revalidation: EUR 159.60 (+12.0%)",
            "supplier_request": {
                "method": "POST",
                "url": f"https://{meta['base_url']}/v1/revalidate",
                "headers": {"Authorization": "Bearer ***", "Content-Type": "application/json"},
                "body": {"offer_id": f"OFR-{uuid.uuid4().hex[:8].upper()}", "original_price": 142.50, "currency": "EUR"},
            },
            "supplier_response": {
                "original_price": 142.50,
                "revalidated_price": 159.60,
                "drift_pct": 12.0,
                "currency": "EUR",
                "action": "manual_review_required",
            },
            "warnings": ["Price drift exceeds 5% threshold", "Rate may have expired"],
        }

    if scenario == "booking_timeout" and step_id == "booking":
        await asyncio.sleep(1.0)
        return {
            "status": "fail",
            "latency_ms": 30100,
            "message": "Booking creation timed out after 30s",
            "supplier_request": {
                "method": "POST",
                "url": f"https://{meta['base_url']}/v1/bookings",
                "headers": {"Authorization": "Bearer ***", "Content-Type": "application/json", "X-Timeout": "30000"},
                "body": {"offer_id": f"OFR-{uuid.uuid4().hex[:8].upper()}", "guest": {"name": "Test Guest"}, "payment": {"type": "credit"}},
            },
            "supplier_response": {"http_status": 504, "body": "Gateway Timeout"},
        }

    if scenario == "delayed_confirmation" and step_id == "status_check":
        await asyncio.sleep(0.6)
        return {
            "status": "warn",
            "latency_ms": 8200,
            "message": "Booking confirmed after extended polling — 5 rounds, 8.2s total",
            "supplier_request": {
                "method": "GET",
                "url": f"https://{meta['base_url']}/v1/bookings/SBX-POLL/status",
                "headers": {"Authorization": "Bearer ***"},
                "body": None,
            },
            "supplier_response": {
                "polling_rounds": 5,
                "final_status": "confirmed",
                "confirmation_id": f"CNF-{uuid.uuid4().hex[:6].upper()}",
                "total_poll_time_ms": 8200,
            },
            "warnings": ["Confirmation delayed — exceeded 3-round SLA"],
        }

    step_data = _simulate_success_step(supplier, step_id, meta)
    base_latency = {"search": 0.3, "detail": 0.2, "revalidation": 0.25, "booking": 0.4, "status_check": 0.15, "cancel": 0.2}
    await asyncio.sleep(base_latency.get(step_id, 0.2))
    return step_data


def _simulate_success_step(supplier: str, step_id: str, meta: dict) -> dict[str, Any]:
    """Generate realistic success data for each step."""
    booking_id = f"SBX-{uuid.uuid4().hex[:6].upper()}"
    base_url = meta["base_url"]

    data = {
        "search": {
            "status": "pass",
            "latency_ms": 680,
            "message": "Search completed — 47 properties found (Antalya, 2 adults, 3 nights)",
            "supplier_request": {
                "method": "POST",
                "url": f"https://{base_url}/v1/search/availability",
                "headers": {"Authorization": "Bearer ***", "Content-Type": "application/json", "X-Request-ID": _req_id()},
                "body": {"destination": "Antalya", "checkin": "2026-03-30", "checkout": "2026-04-02", "guests": [{"adults": 2}], "currency": "EUR"},
            },
            "supplier_response": {
                "total_results": 47,
                "destination": "Antalya",
                "cheapest": {"hotel": "Grand Resort & Spa", "price": 142.50, "currency": "EUR"},
                "most_expensive": {"hotel": "Luxury Palace", "price": 890.00, "currency": "EUR"},
                "response_time_ms": 680,
            },
        },
        "detail": {
            "status": "pass",
            "latency_ms": 420,
            "message": "Hotel detail fetched — Grand Resort & Spa (5-star, 312 reviews)",
            "supplier_request": {
                "method": "GET",
                "url": f"https://{base_url}/v1/hotels/HTL-GRS-001/details",
                "headers": {"Authorization": "Bearer ***", "Accept-Language": "tr"},
                "body": None,
            },
            "supplier_response": {
                "hotel_name": "Grand Resort & Spa",
                "star_rating": 5,
                "review_count": 312,
                "review_score": 8.7,
                "room_types": 4,
                "images": 18,
                "amenities": ["Pool", "Spa", "WiFi", "Restaurant", "Gym"],
                "cancellation_policy": "Free cancellation until 48h before check-in",
            },
        },
        "revalidation": {
            "status": "pass",
            "latency_ms": 510,
            "message": "Price revalidation OK — EUR 142.50/night confirmed (drift: 0.0%)",
            "supplier_request": {
                "method": "POST",
                "url": f"https://{base_url}/v1/revalidate",
                "headers": {"Authorization": "Bearer ***", "Content-Type": "application/json"},
                "body": {"offer_id": f"OFR-{uuid.uuid4().hex[:8].upper()}", "original_price": 142.50, "currency": "EUR"},
            },
            "supplier_response": {
                "original_price": 142.50,
                "revalidated_price": 142.50,
                "drift_pct": 0.0,
                "currency": "EUR",
                "rate_valid_until": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat(),
            },
        },
        "booking": {
            "status": "pass",
            "latency_ms": 1200,
            "message": f"Booking created — {booking_id} (confirmed)",
            "supplier_request": {
                "method": "POST",
                "url": f"https://{base_url}/v1/bookings",
                "headers": {"Authorization": "Bearer ***", "Content-Type": "application/json", "X-Idempotency-Key": uuid.uuid4().hex[:12]},
                "body": {"offer_id": f"OFR-{uuid.uuid4().hex[:8].upper()}", "guest": {"first_name": "Test", "last_name": "Guest", "email": "test@demo.com"}, "payment": {"type": "credit", "amount": 427.50, "currency": "EUR"}},
            },
            "supplier_response": {
                "booking_id": booking_id,
                "status": "confirmed",
                "total_price": 427.50,
                "currency": "EUR",
                "nights": 3,
                "guest_name": "Test Guest",
                "hotel": "Grand Resort & Spa",
            },
        },
        "status_check": {
            "status": "pass",
            "latency_ms": 340,
            "message": f"Booking {booking_id} confirmed — 1 poll round, 340ms",
            "supplier_request": {
                "method": "GET",
                "url": f"https://{base_url}/v1/bookings/{booking_id}/status",
                "headers": {"Authorization": "Bearer ***"},
                "body": None,
            },
            "supplier_response": {
                "booking_id": booking_id,
                "status": "confirmed",
                "polling_rounds": 1,
                "confirmation_id": f"CNF-{uuid.uuid4().hex[:6].upper()}",
            },
        },
        "cancel": {
            "status": "pass",
            "latency_ms": 780,
            "message": f"Cancellation successful — {booking_id} refunded in full",
            "supplier_request": {
                "method": "DELETE",
                "url": f"https://{base_url}/v1/bookings/{booking_id}",
                "headers": {"Authorization": "Bearer ***", "X-Cancel-Reason": "test_cancellation"},
                "body": {"reason": "test_cancellation", "refund_requested": True},
            },
            "supplier_response": {
                "booking_id": booking_id,
                "cancel_status": "cancelled",
                "refund_type": "full",
                "refund_amount": 427.50,
                "currency": "EUR",
                "penalty": 0,
                "cancellation_id": f"CXL-{uuid.uuid4().hex[:6].upper()}",
            },
        },
    }
    return data.get(step_id, {"status": "pass", "latency_ms": 100, "message": "Step completed"})


async def get_test_history(supplier: str | None = None, limit: int = 20) -> dict[str, Any]:
    """Get E2E test history with optional supplier filter."""
    db = await get_db()
    query: dict[str, Any] = {}
    if supplier:
        query["supplier"] = supplier

    tests = []
    cursor = db.e2e_demo_tests.find(query, {"_id": 0, "_recorded_at": 0}).sort("timestamp", -1).limit(limit)
    async for doc in cursor:
        doc.pop("_id", None)
        tests.append(doc)

    return {"tests": tests, "total": len(tests), "timestamp": _ts()}


async def get_supplier_status() -> dict[str, Any]:
    """Quick supplier health summary for the console."""
    db = await get_db()
    suppliers = []
    for code, meta in SUPPLIER_META.items():
        last_test = await db.e2e_demo_tests.find_one(
            {"supplier": code}, {"_id": 0}, sort=[("timestamp", -1)]
        )
        suppliers.append({
            "code": code,
            "name": meta["name"],
            "mode": meta["mode"],
            "last_test": {
                "run_id": last_test["run_id"],
                "scenario": last_test["scenario"],
                "score": last_test["certification"]["score"],
                "status": "passed" if last_test["certification"]["go_live_eligible"] else "failed",
                "timestamp": last_test["timestamp"],
            } if last_test else None,
        })
    return {"suppliers": suppliers, "timestamp": _ts()}


async def rerun_failed_step(run_id: str, step_id: str) -> dict[str, Any]:
    """Rerun a single failed step from a previous test run."""
    db = await get_db()
    test = await db.e2e_demo_tests.find_one({"run_id": run_id}, {"_id": 0})
    if not test:
        return {"error": f"Test run not found: {run_id}"}

    supplier = test["supplier"]
    meta = SUPPLIER_META.get(supplier, {})
    if not meta:
        return {"error": f"Unknown supplier: {supplier}"}

    request_id = _req_id()
    step_start = time.monotonic()

    result = await _execute_step(supplier, step_id, "success", meta)
    duration_ms = round((time.monotonic() - step_start) * 1000, 1)

    step_def = next((s for s in LIFECYCLE_STEPS if s["id"] == step_id), None)
    if not step_def:
        return {"error": f"Unknown step: {step_id}"}

    return {
        "run_id": run_id,
        "step": {
            "id": step_id,
            "name": step_def["name"],
            "status": result["status"],
            "latency_ms": result.get("latency_ms", duration_ms),
            "request_id": request_id,
            "trace_id": test.get("trace_id", ""),
            "supplier_request": result.get("supplier_request", {}),
            "supplier_response": result.get("supplier_response", {}),
            "message": result.get("message", ""),
            "error": result.get("error"),
            "warnings": result.get("warnings", []),
        },
        "rerun": True,
        "timestamp": _ts(),
    }
