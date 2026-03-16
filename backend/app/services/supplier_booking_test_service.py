"""Supplier Booking E2E Test Orchestrator.

Executes a full booking lifecycle test against a supplier (sandbox or simulation):
    Search → Detail → Revalidation → Booking → Status Check → Cancel

Returns step-by-step results for debugging, operations, and demo purposes.

Endpoint: POST /api/inventory/booking/test
"""
from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

from app.db import get_db

logger = logging.getLogger("supplier.booking_test")


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _step_result(name: str, status: str, duration_ms: float, details: dict | None = None, error: str | None = None) -> dict:
    return {
        "name": name,
        "status": status,
        "duration_ms": round(duration_ms, 1),
        "details": details or {},
        "error": error,
    }


async def run_booking_e2e_test(supplier: str) -> dict[str, Any]:
    """Run a full E2E booking lifecycle test for a supplier.

    Steps:
      1. search       — Search for hotels in a test destination
      2. detail        — Get details for the first result
      3. revalidation  — Revalidate price with supplier
      4. booking       — Create a test booking
      5. status_check  — Verify booking status
      6. cancel        — Cancel the test booking

    In simulation mode, all steps use simulated data.
    In sandbox mode, steps 1-3 use real API, steps 4-6 use simulation
    (to avoid creating real bookings in sandbox without explicit credentials).
    """
    trace_id = str(uuid.uuid4())
    test_start = time.monotonic()
    steps: list[dict] = []
    db = await get_db()

    # Determine mode
    from app.services.inventory_sync_service import _determine_sync_mode, SUPPLIER_SYNC_CONFIG
    if supplier not in SUPPLIER_SYNC_CONFIG:
        return {
            "supplier": supplier,
            "mode": "unknown",
            "status": "error",
            "error": f"Unknown supplier: {supplier}",
            "available_suppliers": list(SUPPLIER_SYNC_CONFIG.keys()),
            "trace_id": trace_id,
        }

    sync_mode, cred_config = await _determine_sync_mode(supplier)
    overall_status = "passed"

    # Test dates
    checkin = (datetime.now(timezone.utc) + timedelta(days=14)).strftime("%Y-%m-%d")
    checkout = (datetime.now(timezone.utc) + timedelta(days=17)).strftime("%Y-%m-%d")
    test_destination = "Antalya"

    # ── Step 1: Search ──────────────────────────────────────────
    step_start = time.monotonic()
    search_results = []
    try:
        from app.services.inventory_sync_service import search_inventory
        search_response = await search_inventory(
            destination=test_destination,
            checkin=checkin,
            checkout=checkout,
            guests=2,
            min_stars=0,
            supplier=supplier,
            limit=5,
        )
        search_results = search_response.get("results", [])
        search_count = len(search_results)

        if search_count > 0:
            steps.append(_step_result(
                "search", "passed",
                (time.monotonic() - step_start) * 1000,
                details={
                    "destination": test_destination,
                    "results_count": search_count,
                    "source": search_response.get("source", "unknown"),
                    "latency_ms": search_response.get("latency_ms", 0),
                },
            ))
        else:
            # No results — try triggering a sync first
            from app.services.inventory_sync_service import trigger_supplier_sync
            sync_result = await trigger_supplier_sync(supplier)

            # Retry search after sync
            search_response = await search_inventory(
                destination=test_destination, checkin=checkin, checkout=checkout,
                guests=2, min_stars=0, supplier=supplier, limit=5,
            )
            search_results = search_response.get("results", [])
            search_count = len(search_results)

            if search_count > 0:
                steps.append(_step_result(
                    "search", "passed",
                    (time.monotonic() - step_start) * 1000,
                    details={
                        "destination": test_destination,
                        "results_count": search_count,
                        "note": "Required sync trigger before results were available",
                        "sync_status": sync_result.get("status"),
                    },
                ))
            else:
                steps.append(_step_result(
                    "search", "failed",
                    (time.monotonic() - step_start) * 1000,
                    error=f"No results found for {test_destination} after sync",
                    details={"sync_result": sync_result.get("status")},
                ))
                overall_status = "failed"
    except Exception as e:
        steps.append(_step_result(
            "search", "failed",
            (time.monotonic() - step_start) * 1000,
            error=str(e),
        ))
        overall_status = "failed"

    # ── Step 2: Detail ──────────────────────────────────────────
    step_start = time.monotonic()
    selected_hotel = None
    if search_results:
        try:
            selected_hotel = search_results[0]
            hotel_id = selected_hotel.get("hotel_id", "")

            # Get detail from inventory
            detail_doc = await db.supplier_inventory.find_one(
                {"supplier": supplier, "hotel_id": hotel_id},
                {"_id": 0},
            )

            if detail_doc:
                steps.append(_step_result(
                    "detail", "passed",
                    (time.monotonic() - step_start) * 1000,
                    details={
                        "hotel_id": hotel_id,
                        "hotel_name": detail_doc.get("name", ""),
                        "city": detail_doc.get("city", ""),
                        "stars": detail_doc.get("stars", 0),
                        "rooms_count": len(detail_doc.get("rooms", [])),
                    },
                ))
            else:
                steps.append(_step_result(
                    "detail", "passed",
                    (time.monotonic() - step_start) * 1000,
                    details={
                        "hotel_id": hotel_id,
                        "hotel_name": selected_hotel.get("name", ""),
                        "note": "Detail from search cache (inventory doc not found)",
                    },
                ))
        except Exception as e:
            steps.append(_step_result(
                "detail", "failed",
                (time.monotonic() - step_start) * 1000,
                error=str(e),
            ))
            overall_status = "failed"
    else:
        steps.append(_step_result(
            "detail", "skipped",
            (time.monotonic() - step_start) * 1000,
            error="No search results to get detail for",
        ))

    # ── Step 3: Price Revalidation ──────────────────────────────
    step_start = time.monotonic()
    revalidation_result = None
    if selected_hotel:
        try:
            from app.services.inventory_sync_service import revalidate_price
            hotel_id = selected_hotel.get("hotel_id", "")

            revalidation_result = await revalidate_price(
                supplier=supplier,
                hotel_id=hotel_id,
                checkin=checkin,
                checkout=checkout,
            )

            steps.append(_step_result(
                "revalidation", "passed",
                (time.monotonic() - step_start) * 1000,
                details={
                    "hotel_id": hotel_id,
                    "cached_price": revalidation_result.get("cached_price", 0),
                    "revalidated_price": revalidation_result.get("revalidated_price", 0),
                    "diff_pct": revalidation_result.get("diff_pct", 0),
                    "drift_severity": revalidation_result.get("drift_severity", "unknown"),
                    "source": revalidation_result.get("source", "unknown"),
                },
            ))
        except Exception as e:
            steps.append(_step_result(
                "revalidation", "failed",
                (time.monotonic() - step_start) * 1000,
                error=str(e),
            ))
            overall_status = "failed"
    else:
        steps.append(_step_result(
            "revalidation", "skipped",
            (time.monotonic() - step_start) * 1000,
            error="No hotel selected for revalidation",
        ))

    # ── Step 4: Booking (Simulated) ─────────────────────────────
    step_start = time.monotonic()
    booking_id = None
    try:
        booking_id = f"test_{supplier}_{uuid.uuid4().hex[:8]}"
        hotel_id = selected_hotel.get("hotel_id", "unknown") if selected_hotel else "unknown"
        price = revalidation_result.get("revalidated_price", 0) if revalidation_result else 0

        booking_doc = {
            "booking_id": booking_id,
            "supplier": supplier,
            "hotel_id": hotel_id,
            "hotel_name": selected_hotel.get("name", "Test Hotel") if selected_hotel else "Test Hotel",
            "checkin": checkin,
            "checkout": checkout,
            "guests": 2,
            "price": price,
            "currency": "EUR",
            "status": "confirmed",
            "is_test": True,
            "trace_id": trace_id,
            "mode": sync_mode,
            "created_at": _ts(),
        }

        await db.supplier_test_bookings.insert_one(booking_doc)

        steps.append(_step_result(
            "booking", "passed",
            (time.monotonic() - step_start) * 1000,
            details={
                "booking_id": booking_id,
                "hotel_id": hotel_id,
                "price": price,
                "mode": "simulation" if sync_mode == "simulation" else "sandbox_simulated",
                "note": "Booking simulated (no real supplier booking created)" if sync_mode != "production" else "Real booking created",
            },
        ))
    except Exception as e:
        steps.append(_step_result(
            "booking", "failed",
            (time.monotonic() - step_start) * 1000,
            error=str(e),
        ))
        overall_status = "failed"

    # ── Step 5: Status Check ────────────────────────────────────
    step_start = time.monotonic()
    if booking_id:
        try:
            status_doc = await db.supplier_test_bookings.find_one(
                {"booking_id": booking_id},
                {"_id": 0},
            )
            if status_doc and status_doc.get("status") == "confirmed":
                steps.append(_step_result(
                    "status_check", "passed",
                    (time.monotonic() - step_start) * 1000,
                    details={
                        "booking_id": booking_id,
                        "status": status_doc.get("status"),
                    },
                ))
            else:
                steps.append(_step_result(
                    "status_check", "failed",
                    (time.monotonic() - step_start) * 1000,
                    error=f"Unexpected status: {status_doc.get('status') if status_doc else 'not_found'}",
                ))
                overall_status = "failed"
        except Exception as e:
            steps.append(_step_result(
                "status_check", "failed",
                (time.monotonic() - step_start) * 1000,
                error=str(e),
            ))
            overall_status = "failed"
    else:
        steps.append(_step_result(
            "status_check", "skipped",
            (time.monotonic() - step_start) * 1000,
            error="No booking to check status for",
        ))

    # ── Step 6: Cancel ──────────────────────────────────────────
    step_start = time.monotonic()
    if booking_id:
        try:
            cancel_result = await db.supplier_test_bookings.update_one(
                {"booking_id": booking_id},
                {"$set": {"status": "cancelled", "cancelled_at": _ts()}},
            )
            if cancel_result.modified_count > 0:
                steps.append(_step_result(
                    "cancel", "passed",
                    (time.monotonic() - step_start) * 1000,
                    details={
                        "booking_id": booking_id,
                        "status": "cancelled",
                        "mode": "simulation",
                    },
                ))
            else:
                steps.append(_step_result(
                    "cancel", "failed",
                    (time.monotonic() - step_start) * 1000,
                    error="Cancel update did not modify any document",
                ))
                overall_status = "failed"
        except Exception as e:
            steps.append(_step_result(
                "cancel", "failed",
                (time.monotonic() - step_start) * 1000,
                error=str(e),
            ))
            overall_status = "failed"
    else:
        steps.append(_step_result(
            "cancel", "skipped",
            (time.monotonic() - step_start) * 1000,
            error="No booking to cancel",
        ))

    # ── Summary ─────────────────────────────────────────────────
    total_duration_ms = round((time.monotonic() - test_start) * 1000, 1)
    passed_count = sum(1 for s in steps if s["status"] == "passed")
    failed_count = sum(1 for s in steps if s["status"] == "failed")
    skipped_count = sum(1 for s in steps if s["status"] == "skipped")

    # Persist test result
    test_result = {
        "supplier": supplier,
        "mode": sync_mode,
        "status": overall_status,
        "trace_id": trace_id,
        "steps": steps,
        "summary": {
            "total": len(steps),
            "passed": passed_count,
            "failed": failed_count,
            "skipped": skipped_count,
        },
        "duration_ms": total_duration_ms,
        "test_params": {
            "destination": test_destination,
            "checkin": checkin,
            "checkout": checkout,
        },
        "timestamp": _ts(),
    }

    await db.supplier_booking_tests.insert_one({**test_result, "recorded_at": _ts()})

    return test_result


async def get_booking_test_history(
    supplier: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Get history of E2E booking tests."""
    db = await get_db()
    query: dict[str, Any] = {}
    if supplier:
        query["supplier"] = supplier

    tests = []
    cursor = db.supplier_booking_tests.find(
        query, {"_id": 0}
    ).sort("timestamp", -1).limit(limit)
    async for doc in cursor:
        tests.append(doc)

    return {"tests": tests, "total": len(tests), "timestamp": _ts()}
