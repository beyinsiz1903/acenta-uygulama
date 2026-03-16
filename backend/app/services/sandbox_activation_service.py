"""RateHawk Sandbox Activation Service.

Provides real API execution paths for the Certification Console.
When sandbox credentials are configured, each lifecycle step calls
the actual RateHawk API instead of returning simulated data.

Architecture:
  - Reads credentials from supplier_config_service OR env vars
  - Uses ratehawk_sync_adapter for search/revalidation
  - Uses ratehawk_booking_service for booking/cancel
  - Classifies errors into supplier taxonomy
  - Returns structured results compatible with e2e_demo_service format
"""
from __future__ import annotations

import logging
import os
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

from app.db import get_db

logger = logging.getLogger("sandbox.activation")


async def get_sandbox_credentials(supplier: str = "ratehawk") -> dict[str, Any] | None:
    """Get sandbox credentials from config store or env vars.

    Priority:
      1. DB supplier_credentials (set via Admin UI)
      2. Environment variables (RATEHAWK_SANDBOX_KEY_ID / RATEHAWK_SANDBOX_API_KEY)
    """
    if supplier != "ratehawk":
        return None

    # Priority 1: Check DB config
    try:
        from app.services.supplier_config_service import get_raw_credentials
        config = await get_raw_credentials("ratehawk")
        if config and config.get("credentials"):
            creds = config["credentials"]
            if creds.get("key_id") and creds.get("api_key"):
                return {
                    "base_url": config.get("base_url", "https://api-sandbox.worldota.net"),
                    "credentials": creds,
                    "mode": config.get("mode", "sandbox"),
                    "source": "db_config",
                }
    except Exception as e:
        logger.warning("DB credential check failed: %s", e)

    # Priority 2: Check env vars
    key_id = os.environ.get("RATEHAWK_SANDBOX_KEY_ID", "").strip()
    api_key = os.environ.get("RATEHAWK_SANDBOX_API_KEY", "").strip()
    if key_id and api_key:
        return {
            "base_url": os.environ.get("RATEHAWK_SANDBOX_URL", "https://api-sandbox.worldota.net"),
            "credentials": {"key_id": key_id, "api_key": api_key},
            "mode": "sandbox",
            "source": "env_vars",
        }

    return None


async def get_sandbox_status(supplier: str = "ratehawk") -> dict[str, Any]:
    """Get comprehensive sandbox activation status.

    Resolves one of 4 modes:
      - simulation:        No credentials configured
      - sandbox_ready:     Credentials exist, health not yet validated
      - sandbox_connected: Credentials exist AND API health check passed
      - sandbox_blocked:   Credentials exist but API is unreachable (env restriction)
    """
    creds = await get_sandbox_credentials(supplier)

    if not creds:
        return {
            "supplier": supplier,
            "mode": "simulation",
            "credentials_configured": False,
            "credential_source": None,
            "health": {"status": "not_configured", "message": "Sandbox kimlik bilgileri yapilandirilmamis"},
            "readiness": {
                "credential_wiring": False,
                "health_validated": False,
                "search_tested": False,
                "booking_tested": False,
                "cancel_tested": False,
                "go_live_ready": False,
            },
        }

    # Credentials exist — check health
    from app.services.sandbox_telemetry_service import increment_counter
    await increment_counter("sandbox_connection_attempts", supplier)

    health = await _check_health(creds)
    api_reachable = health.get("reachable", False)

    # Determine granular mode
    if api_reachable:
        mode = "sandbox_connected"
    elif health.get("error") and _is_env_blocked(health["error"]):
        mode = "sandbox_blocked"
        await increment_counter("sandbox_blocked_events", supplier)
    else:
        mode = "sandbox_ready"

    # Check test history for readiness
    db = await get_db()
    last_sandbox_test = await db.e2e_demo_tests.find_one(
        {"supplier": supplier, "mode": "sandbox"},
        {"_id": 0},
        sort=[("timestamp", -1)],
    )

    readiness = {
        "credential_wiring": True,
        "health_validated": api_reachable,
        "search_tested": False,
        "booking_tested": False,
        "cancel_tested": False,
        "go_live_ready": False,
    }

    if last_sandbox_test:
        steps = {s["id"]: s["status"] for s in last_sandbox_test.get("steps", [])}
        readiness["search_tested"] = steps.get("search") == "pass"
        readiness["booking_tested"] = steps.get("booking") == "pass"
        readiness["cancel_tested"] = steps.get("cancel") == "pass"
        readiness["go_live_ready"] = all(readiness.values())

    return {
        "supplier": supplier,
        "mode": mode,
        "credentials_configured": True,
        "credential_source": creds["source"],
        "base_url": _mask_url(creds["base_url"]),
        "health": health,
        "readiness": readiness,
        "last_sandbox_test": {
            "run_id": last_sandbox_test["run_id"],
            "score": last_sandbox_test.get("certification", {}).get("score", 0),
            "timestamp": last_sandbox_test.get("timestamp"),
        } if last_sandbox_test else None,
    }


async def _check_health(creds: dict) -> dict[str, Any]:
    """Validate credentials and API reachability."""
    from app.services.ratehawk_sync_adapter import validate_credentials
    result = await validate_credentials(creds["base_url"], creds["credentials"])
    return {
        "status": "healthy" if result.get("success") else "unhealthy",
        "reachable": result.get("success", False),
        "latency_ms": result.get("latency_ms", 0),
        "auth_valid": result.get("success", False),
        "error": result.get("error") if not result.get("success") else None,
        "attempts": result.get("attempts", 1),
    }


# ── Real Sandbox Step Execution ───────────────────────────────────────

async def execute_real_step(
    step_id: str, creds: dict, scenario: str, context: dict
) -> dict[str, Any]:
    """Execute a single certification step against the real RateHawk API."""
    executor = {
        "search": _real_search,
        "detail": _real_detail,
        "revalidation": _real_revalidation,
        "booking": _real_booking,
        "status_check": _real_status_check,
        "cancel": _real_cancel,
    }

    fn = executor.get(step_id)
    if not fn:
        return {"status": "fail", "error": f"Unknown step: {step_id}", "latency_ms": 0}

    start = time.monotonic()
    try:
        result = await fn(creds, scenario, context)
        result["latency_ms"] = result.get("latency_ms", round((time.monotonic() - start) * 1000, 1))
        return result
    except Exception as e:
        latency = round((time.monotonic() - start) * 1000, 1)
        error_class = _classify_error(e)
        return {
            "status": "fail",
            "latency_ms": latency,
            "message": f"Step failed: {error_class['category']}",
            "error": str(e),
            "error_classification": error_class,
            "supplier_request": {},
            "supplier_response": {},
        }


async def _real_search(creds: dict, scenario: str, ctx: dict) -> dict[str, Any]:
    """Real search against RateHawk sandbox."""
    from app.services.ratehawk_sync_adapter import _make_auth_header, _api_call_with_retry
    import httpx

    base_url = creds["base_url"]
    headers = _make_auth_header(creds["credentials"]["key_id"], creds["credentials"]["api_key"])

    checkin = ctx.get("checkin", (datetime.now(timezone.utc) + timedelta(days=14)).strftime("%Y-%m-%d"))
    checkout = ctx.get("checkout", (datetime.now(timezone.utc) + timedelta(days=17)).strftime("%Y-%m-%d"))

    request_payload = {
        "checkin": checkin,
        "checkout": checkout,
        "residency": "tr",
        "language": "en",
        "guests": [{"adults": 2, "children": []}],
        "region_id": 2998,  # Antalya
        "currency": "EUR",
    }

    masked_headers = {k: ("***" if "auth" in k.lower() else v) for k, v in headers.items()}

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp, meta = await _api_call_with_retry(
            client, "POST",
            f"{base_url}/api/b2b/v3/search/serp/region/",
            headers, json_payload=request_payload,
            max_retries=2, base_delay=1.5,
            operation="sandbox_search",
        )

    if resp is None or resp.status_code != 200:
        error_msg = meta.get("error", "Search failed")
        return {
            "status": "fail",
            "message": f"Sandbox search failed: {error_msg}",
            "error": error_msg,
            "supplier_request": {"method": "POST", "url": f"{base_url}/api/b2b/v3/search/serp/region/", "headers": masked_headers, "body": request_payload},
            "supplier_response": {"http_status": resp.status_code if resp else 0, "error": error_msg},
        }

    data = resp.json()
    hotels = data.get("data", {}).get("hotels", data.get("hotels", []))
    hotel_count = len(hotels)

    # Store search results for subsequent steps
    ctx["search_results"] = hotels[:5] if hotels else []
    ctx["search_hotel_count"] = hotel_count

    if hotel_count == 0:
        # Region search returned OK but no hotels — still valid
        return {
            "status": "warn",
            "message": "Search completed but 0 hotels found for region. API is reachable.",
            "warnings": ["No hotels returned — region may be empty or dates unavailable"],
            "supplier_request": {"method": "POST", "url": f"{base_url}/api/b2b/v3/search/serp/region/", "headers": masked_headers, "body": request_payload},
            "supplier_response": {"total_results": 0, "response_preview": str(data)[:500]},
        }

    cheapest = min(hotels, key=lambda h: h.get("min_price", float("inf"))) if hotels else {}

    return {
        "status": "pass",
        "message": f"Sandbox search completed — {hotel_count} properties found (Antalya, 2 adults, 3 nights)",
        "supplier_request": {"method": "POST", "url": f"{base_url}/api/b2b/v3/search/serp/region/", "headers": masked_headers, "body": request_payload},
        "supplier_response": {
            "total_results": hotel_count,
            "destination": "Antalya",
            "cheapest": {"hotel": cheapest.get("name", "N/A"), "price": cheapest.get("min_price", 0), "currency": "EUR"},
            "response_time_ms": meta.get("latency_ms", 0),
            "api_source": "ratehawk_sandbox",
        },
        "latency_ms": meta.get("latency_ms", 0),
    }


async def _real_detail(creds: dict, scenario: str, ctx: dict) -> dict[str, Any]:
    """Real hotel detail fetch. Uses test_hotel for sandbox."""
    from app.services.ratehawk_sync_adapter import _make_auth_header, _api_call_with_retry
    import httpx

    base_url = creds["base_url"]
    headers = _make_auth_header(creds["credentials"]["key_id"], creds["credentials"]["api_key"])
    masked_headers = {k: ("***" if "auth" in k.lower() else v) for k, v in headers.items()}

    checkin = ctx.get("checkin", (datetime.now(timezone.utc) + timedelta(days=14)).strftime("%Y-%m-%d"))
    checkout = ctx.get("checkout", (datetime.now(timezone.utc) + timedelta(days=17)).strftime("%Y-%m-%d"))

    # Use test_hotel for sandbox or first search result
    hotel_id = "test_hotel"
    search_results = ctx.get("search_results", [])
    if search_results:
        hotel_id = str(search_results[0].get("id", search_results[0].get("hotel_id", "test_hotel")))

    request_payload = {
        "id": hotel_id,
        "checkin": checkin,
        "checkout": checkout,
        "guests": [{"adults": 2, "children": []}],
        "currency": "EUR",
        "language": "en",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp, meta = await _api_call_with_retry(
            client, "POST",
            f"{base_url}/api/b2b/v3/search/hp/",
            headers, json_payload=request_payload,
            max_retries=2, base_delay=1.0,
            operation="sandbox_hotel_detail",
        )

    if resp is None or resp.status_code != 200:
        error_msg = meta.get("error", "Hotel detail failed")
        return {
            "status": "fail",
            "message": f"Hotel detail fetch failed: {error_msg}",
            "error": error_msg,
            "supplier_request": {"method": "POST", "url": f"{base_url}/api/b2b/v3/search/hp/", "headers": masked_headers, "body": request_payload},
            "supplier_response": {"http_status": resp.status_code if resp else 0, "error": error_msg},
        }

    data = resp.json()
    hotel_data = data.get("data", data)

    # Extract room info and book_hash for next steps
    rooms = hotel_data.get("rooms", hotel_data.get("room_groups", []))
    book_hash = None
    rate_price = 0
    if isinstance(rooms, list) and rooms:
        first_room = rooms[0] if rooms else {}
        rates = first_room.get("rates", first_room.get("offers", []))
        if isinstance(rates, list) and rates:
            book_hash = rates[0].get("book_hash", rates[0].get("offer_hash"))
            rate_price = rates[0].get("daily_prices", [0])[0] if rates[0].get("daily_prices") else rates[0].get("payment_options", {}).get("payment_types", [{}])[0].get("amount", 0)

    ctx["hotel_id"] = hotel_id
    ctx["book_hash"] = book_hash
    ctx["hotel_detail_data"] = hotel_data
    ctx["rate_price"] = rate_price

    return {
        "status": "pass",
        "message": f"Hotel detail fetched — {hotel_data.get('name', hotel_id)} ({len(rooms)} room types)",
        "supplier_request": {"method": "POST", "url": f"{base_url}/api/b2b/v3/search/hp/", "headers": masked_headers, "body": request_payload},
        "supplier_response": {
            "hotel_id": hotel_id,
            "hotel_name": hotel_data.get("name", "N/A"),
            "star_rating": hotel_data.get("star_rating", 0),
            "room_types": len(rooms),
            "has_book_hash": bool(book_hash),
            "rate_price": rate_price,
            "api_source": "ratehawk_sandbox",
        },
        "latency_ms": meta.get("latency_ms", 0),
    }


async def _real_revalidation(creds: dict, scenario: str, ctx: dict) -> dict[str, Any]:
    """Real price revalidation via prebook."""
    from app.services.ratehawk_booking_service import booking_precheck

    hotel_id = ctx.get("hotel_id", "test_hotel")
    book_hash = ctx.get("book_hash")
    checkin = ctx.get("checkin", (datetime.now(timezone.utc) + timedelta(days=14)).strftime("%Y-%m-%d"))
    checkout = ctx.get("checkout", (datetime.now(timezone.utc) + timedelta(days=17)).strftime("%Y-%m-%d"))

    start = time.monotonic()
    result = await booking_precheck(
        supplier="ratehawk",
        hotel_id=hotel_id,
        book_hash=book_hash,
        checkin=checkin,
        checkout=checkout,
        guests=2,
        currency="EUR",
    )
    latency = round((time.monotonic() - start) * 1000, 1)

    ctx["precheck_id"] = result.get("precheck_id")
    ctx["book_hash"] = result.get("book_hash", book_hash)

    decision = result.get("decision", "proceed")
    pricing = result.get("pricing", {})
    drift_pct = pricing.get("drift_pct", 0)

    status = "pass"
    warnings = result.get("warnings", [])
    if decision == "abort":
        status = "fail"
    elif decision in ("requires_approval", "proceed_with_warning"):
        status = "warn"

    return {
        "status": status,
        "latency_ms": latency,
        "message": f"Revalidation {decision} — cached: EUR {pricing.get('cached_price', 0)}, live: EUR {pricing.get('revalidated_price', 0)} (drift: {drift_pct:.1f}%)",
        "warnings": warnings,
        "supplier_request": {"operation": "booking_precheck", "hotel_id": hotel_id, "book_hash": book_hash, "mode": result.get("mode", "sandbox")},
        "supplier_response": {
            "decision": decision,
            "cached_price": pricing.get("cached_price", 0),
            "revalidated_price": pricing.get("revalidated_price", 0),
            "drift_pct": round(drift_pct, 2),
            "currency": pricing.get("currency", "EUR"),
            "can_proceed": result.get("can_proceed", True),
            "precheck_id": result.get("precheck_id"),
            "api_latency_ms": result.get("api_latency_ms", 0),
        },
    }


async def _real_booking(creds: dict, scenario: str, ctx: dict) -> dict[str, Any]:
    """Real booking creation via RateHawk sandbox."""
    from app.services.ratehawk_booking_service import create_booking

    hotel_id = ctx.get("hotel_id", "test_hotel")
    book_hash = ctx.get("book_hash", f"bh_{uuid.uuid4().hex[:16]}")
    checkin = ctx.get("checkin", (datetime.now(timezone.utc) + timedelta(days=14)).strftime("%Y-%m-%d"))
    checkout = ctx.get("checkout", (datetime.now(timezone.utc) + timedelta(days=17)).strftime("%Y-%m-%d"))

    test_guests = [{"first_name": "Test", "last_name": "Sandbox", "title": "Mr", "type": "adult"}]
    test_contact = {"email": "sandbox@syroce.com", "phone": "+905551234567", "name": "Sandbox Test"}

    start = time.monotonic()
    result = await create_booking(
        supplier="ratehawk",
        hotel_id=hotel_id,
        book_hash=book_hash,
        checkin=checkin,
        checkout=checkout,
        guests=test_guests,
        contact=test_contact,
        user_ip="127.0.0.1",
        currency="EUR",
        precheck_id=ctx.get("precheck_id"),
    )
    latency = round((time.monotonic() - start) * 1000, 1)

    booking_id = result.get("booking_id")
    status = result.get("status", "failed")
    ctx["booking_id"] = booking_id
    ctx["booking_status"] = status

    if status == "confirmed":
        return {
            "status": "pass",
            "latency_ms": latency,
            "message": f"Booking confirmed — {booking_id} (confirmation: {result.get('confirmation_code', 'N/A')})",
            "supplier_request": {"operation": "create_booking", "hotel_id": hotel_id, "book_hash": book_hash[:20] + "..."},
            "supplier_response": {
                "booking_id": booking_id,
                "status": status,
                "confirmation_code": result.get("confirmation_code"),
                "duration_ms": result.get("total_duration_ms", latency),
                "api_source": "ratehawk_sandbox",
            },
        }
    elif status == "timeout":
        return {
            "status": "warn",
            "latency_ms": latency,
            "message": f"Booking timed out — {booking_id} (may still confirm asynchronously)",
            "warnings": ["Booking confirmation timed out — check status manually"],
            "supplier_request": {"operation": "create_booking", "hotel_id": hotel_id},
            "supplier_response": {"booking_id": booking_id, "status": status, "error": result.get("error")},
        }
    else:
        return {
            "status": "fail" if status == "failed" else "warn",
            "latency_ms": latency,
            "message": f"Booking {status} — {result.get('error', 'Unknown error')}",
            "error": result.get("error"),
            "supplier_request": {"operation": "create_booking", "hotel_id": hotel_id},
            "supplier_response": {"booking_id": booking_id, "status": status, "error": result.get("error")},
        }


async def _real_status_check(creds: dict, scenario: str, ctx: dict) -> dict[str, Any]:
    """Real booking status check."""
    from app.services.ratehawk_booking_service import get_booking_status

    booking_id = ctx.get("booking_id")
    if not booking_id:
        return {"status": "skipped", "message": "No booking ID from previous step", "latency_ms": 0, "supplier_request": {}, "supplier_response": {}}

    start = time.monotonic()
    result = await get_booking_status(booking_id)
    latency = round((time.monotonic() - start) * 1000, 1)

    current_status = result.get("status", "not_found")
    history_entries = len(result.get("status_history", []))

    status = "pass" if current_status in ("confirmed", "cancelled") else ("warn" if current_status in ("awaiting_confirmation", "timeout") else "fail")

    return {
        "status": status,
        "latency_ms": latency,
        "message": f"Booking {booking_id} status: {current_status} ({history_entries} history entries)",
        "warnings": [f"Booking in {current_status} state"] if current_status not in ("confirmed", "cancelled") else [],
        "supplier_request": {"operation": "get_booking_status", "booking_id": booking_id},
        "supplier_response": {
            "booking_id": booking_id,
            "status": current_status,
            "confirmation_code": result.get("confirmation_code"),
            "mode": result.get("mode", "unknown"),
            "history_entries": history_entries,
            "has_partner_order_id": bool(result.get("partner_order_id")),
        },
    }


async def _real_cancel(creds: dict, scenario: str, ctx: dict) -> dict[str, Any]:
    """Real booking cancellation."""
    from app.services.ratehawk_booking_service import cancel_booking

    booking_id = ctx.get("booking_id")
    booking_status = ctx.get("booking_status", "")

    if not booking_id:
        return {"status": "skipped", "message": "No booking ID for cancellation", "latency_ms": 0, "supplier_request": {}, "supplier_response": {}}

    if booking_status not in ("confirmed", "awaiting_confirmation", "booking_requested"):
        return {
            "status": "warn",
            "latency_ms": 0,
            "message": f"Skipping cancel — booking in '{booking_status}' state (not cancellable)",
            "warnings": [f"Cannot cancel booking in {booking_status} state"],
            "supplier_request": {},
            "supplier_response": {"booking_id": booking_id, "current_status": booking_status},
        }

    start = time.monotonic()
    result = await cancel_booking(booking_id)
    latency = round((time.monotonic() - start) * 1000, 1)

    cancel_status = result.get("status", "failed")

    if cancel_status == "cancelled":
        return {
            "status": "pass",
            "latency_ms": latency,
            "message": f"Cancellation successful — {booking_id}",
            "supplier_request": {"operation": "cancel_booking", "booking_id": booking_id},
            "supplier_response": {"booking_id": booking_id, "status": cancel_status, "api_source": "ratehawk_sandbox"},
        }

    return {
        "status": "fail",
        "latency_ms": latency,
        "message": f"Cancellation failed — {result.get('error', 'Unknown')}",
        "error": result.get("error"),
        "supplier_request": {"operation": "cancel_booking", "booking_id": booking_id},
        "supplier_response": {"booking_id": booking_id, "status": cancel_status, "error": result.get("error")},
    }


# ── Error Classification ──────────────────────────────────────────────

def _classify_error(exc: Exception) -> dict[str, Any]:
    """Classify exceptions into supplier error taxonomy."""
    import httpx

    exc_type = type(exc).__name__

    if isinstance(exc, httpx.TimeoutException):
        return {"category": "timeout", "retryable": True, "severity": "medium"}
    if isinstance(exc, httpx.ConnectError):
        return {"category": "connection_error", "retryable": True, "severity": "high"}
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        if code == 401:
            return {"category": "auth_error", "retryable": False, "severity": "critical"}
        if code == 429:
            return {"category": "rate_limited", "retryable": True, "severity": "medium"}
        if code >= 500:
            return {"category": "server_error", "retryable": True, "severity": "high"}
        return {"category": "client_error", "retryable": False, "severity": "medium"}

    return {"category": "unknown", "retryable": False, "severity": "medium", "exception_type": exc_type}


def _is_env_blocked(error_str: str) -> bool:
    """Detect if the error indicates an environment-level network block."""
    blocked_indicators = [
        "connect", "timeout", "refused", "unreachable", "resolve",
        "dns", "network", "ssl", "certificate", "eof", "reset",
        "no route", "host", "connection",
    ]
    err_lower = (error_str or "").lower()
    return any(ind in err_lower for ind in blocked_indicators)


def _mask_url(url: str) -> str:
    """Mask sensitive parts of URL for display."""
    if not url:
        return ""
    return url.replace("https://", "").replace("http://", "")
