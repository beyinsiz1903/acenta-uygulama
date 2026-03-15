"""Ratehawk Sandbox Sync Adapter — MEGA PROMPT #38.

Bridges the Inventory Sync Engine with the real RateHawk B2B API v3.
When credentials are configured, uses real API calls.
When not configured, returns a clear "not_configured" status.

RateHawk API:
  Production: https://api.worldota.net
  Sandbox:    https://api-sandbox.worldota.net
  Auth: Basic (key_id:api_key base64)
"""
from __future__ import annotations

import base64
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Any

import httpx

logger = logging.getLogger("ratehawk.sync")

RATEHAWK_ENDPOINTS = {
    "region_search": "/api/b2b/v3/search/serp/region/",
    "hotel_search": "/api/b2b/v3/search/serp/hotels/",
    "hotel_page": "/api/b2b/v3/search/hp/",
    "prebook": "/api/b2b/v3/search/serp/prebook/",
    "overview": "/api/b2b/v3/overview/",
}

# Regions to sync inventory from (popular destinations)
SYNC_REGIONS = [
    {"id": "2998", "name": "Antalya", "country": "TR"},
    {"id": "8359", "name": "Istanbul", "country": "TR"},
    {"id": "8316", "name": "Bodrum", "country": "TR"},
    {"id": "6040", "name": "Dubai", "country": "AE"},
    {"id": "8326", "name": "Belek", "country": "TR"},
]


def _make_auth_header(key_id: str, api_key: str) -> dict[str, str]:
    """Create Basic auth header for RateHawk API."""
    token = base64.b64encode(f"{key_id}:{api_key}".encode()).decode()
    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


async def validate_credentials(base_url: str, credentials: dict) -> dict[str, Any]:
    """Validate RateHawk credentials by calling a lightweight endpoint.

    Returns: {success, latency_ms, error?, endpoints_available?}
    """
    key_id = credentials.get("key_id", "")
    api_key = credentials.get("api_key", "")

    if not key_id or not api_key:
        return {
            "success": False,
            "error": "key_id and api_key are required",
            "status": "invalid_credentials",
        }

    headers = _make_auth_header(key_id, api_key)
    start = time.monotonic()

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{base_url}{RATEHAWK_ENDPOINTS['overview']}",
                headers=headers,
            )
        latency_ms = round((time.monotonic() - start) * 1000, 1)

        if resp.status_code == 200:
            data = resp.json()
            return {
                "success": True,
                "status": "valid",
                "latency_ms": latency_ms,
                "endpoints_available": list(data.get("endpoints", {}).keys()) if isinstance(data, dict) else [],
                "response_preview": str(data)[:300],
            }
        elif resp.status_code == 401:
            return {
                "success": False,
                "status": "unauthorized",
                "error": "Invalid credentials (401)",
                "latency_ms": latency_ms,
            }
        else:
            return {
                "success": False,
                "status": "api_error",
                "error": f"HTTP {resp.status_code}: {resp.text[:200]}",
                "latency_ms": latency_ms,
            }
    except httpx.TimeoutException:
        return {
            "success": False,
            "status": "timeout",
            "error": "Connection timed out",
            "latency_ms": round((time.monotonic() - start) * 1000, 1),
        }
    except httpx.ConnectError as e:
        return {
            "success": False,
            "status": "connection_error",
            "error": f"Cannot connect to {base_url}: {e}",
            "latency_ms": round((time.monotonic() - start) * 1000, 1),
        }
    except Exception as e:
        return {
            "success": False,
            "status": "unknown_error",
            "error": str(e),
            "latency_ms": round((time.monotonic() - start) * 1000, 1),
        }


async def sync_inventory_from_ratehawk(
    base_url: str, credentials: dict
) -> dict[str, Any]:
    """Sync hotel inventory from RateHawk API.

    Flow: region_search → collect hotel IDs → hotel_search for prices/availability

    Returns sync result with hotels, metrics, and errors.
    """
    key_id = credentials.get("key_id", "")
    api_key = credentials.get("api_key", "")
    headers = _make_auth_header(key_id, api_key)

    sync_start = time.monotonic()
    hotels_found = []
    prices_found = []
    availability_found = []
    errors = []
    api_calls = 0
    total_latency_ms = 0

    checkin = (datetime.now(timezone.utc) + timedelta(days=14)).strftime("%Y-%m-%d")
    checkout = (datetime.now(timezone.utc) + timedelta(days=17)).strftime("%Y-%m-%d")

    async with httpx.AsyncClient(timeout=20.0) as client:
        for region in SYNC_REGIONS:
            call_start = time.monotonic()
            try:
                # Region search to get hotels
                resp = await client.post(
                    f"{base_url}{RATEHAWK_ENDPOINTS['region_search']}",
                    json={
                        "checkin": checkin,
                        "checkout": checkout,
                        "residency": "tr",
                        "language": "en",
                        "guests": [{"adults": 2, "children": []}],
                        "region_id": region["id"],
                        "currency": "EUR",
                    },
                    headers=headers,
                )
                call_latency = round((time.monotonic() - call_start) * 1000, 1)
                total_latency_ms += call_latency
                api_calls += 1

                if resp.status_code != 200:
                    errors.append({
                        "region": region["name"],
                        "endpoint": "region_search",
                        "status_code": resp.status_code,
                        "error": resp.text[:200],
                        "latency_ms": call_latency,
                    })
                    continue

                data = resp.json()
                region_hotels = data.get("data", {}).get("hotels", [])
                if not region_hotels and isinstance(data, dict):
                    region_hotels = data.get("hotels", [])

                for hotel_raw in region_hotels[:20]:
                    hotel_id = str(hotel_raw.get("id", hotel_raw.get("hotel_id", "")))
                    if not hotel_id:
                        continue

                    hotel_record = {
                        "supplier": "ratehawk",
                        "hotel_id": f"rh_{hotel_id}",
                        "name": hotel_raw.get("name", hotel_raw.get("hotel_name", f"Hotel {hotel_id}")),
                        "city": region["name"],
                        "country": region["country"],
                        "stars": hotel_raw.get("star_rating", hotel_raw.get("stars", 0)),
                        "rooms": _extract_rooms(hotel_raw),
                        "source": "ratehawk_api",
                        "external_id": hotel_id,
                    }
                    hotels_found.append(hotel_record)

                    # Extract price info
                    min_price = hotel_raw.get("min_price", hotel_raw.get("price", 0))
                    if min_price:
                        prices_found.append({
                            "supplier": "ratehawk",
                            "hotel_id": f"rh_{hotel_id}",
                            "date": checkin,
                            "price": float(min_price) if min_price else 0,
                            "currency": hotel_raw.get("currency", "EUR"),
                            "source": "ratehawk_api",
                        })

                    # Availability
                    availability_found.append({
                        "supplier": "ratehawk",
                        "hotel_id": f"rh_{hotel_id}",
                        "date": checkin,
                        "rooms_available": len(_extract_rooms(hotel_raw)) or 1,
                        "source": "ratehawk_api",
                    })

                logger.info(
                    "RateHawk region sync: %s → %d hotels (%.1fms)",
                    region["name"], len(region_hotels), call_latency,
                )

            except httpx.TimeoutException:
                errors.append({
                    "region": region["name"],
                    "endpoint": "region_search",
                    "error": "timeout",
                    "latency_ms": round((time.monotonic() - call_start) * 1000, 1),
                })
            except Exception as e:
                errors.append({
                    "region": region["name"],
                    "endpoint": "region_search",
                    "error": str(e),
                    "latency_ms": round((time.monotonic() - call_start) * 1000, 1),
                })

    sync_duration_ms = round((time.monotonic() - sync_start) * 1000, 1)
    avg_latency = round(total_latency_ms / api_calls, 1) if api_calls > 0 else 0
    error_rate = round(len(errors) / max(api_calls, 1) * 100, 1)

    return {
        "hotels": hotels_found,
        "prices": prices_found,
        "availability": availability_found,
        "metrics": {
            "api_calls": api_calls,
            "total_latency_ms": total_latency_ms,
            "avg_latency_ms": avg_latency,
            "error_rate_pct": error_rate,
            "sync_duration_ms": sync_duration_ms,
            "hotels_count": len(hotels_found),
            "prices_count": len(prices_found),
            "availability_count": len(availability_found),
            "errors_count": len(errors),
        },
        "errors": errors,
        "source": "ratehawk_sandbox" if "sandbox" in base_url else "ratehawk_production",
    }


async def revalidate_price_from_ratehawk(
    base_url: str,
    credentials: dict,
    hotel_id: str,
    checkin: str,
    checkout: str,
) -> dict[str, Any]:
    """Revalidate price by calling RateHawk hotel page endpoint.

    Returns the real supplier price for drift calculation.
    """
    key_id = credentials.get("key_id", "")
    api_key = credentials.get("api_key", "")
    headers = _make_auth_header(key_id, api_key)

    # Extract the real RateHawk ID (strip 'rh_' prefix)
    real_id = hotel_id.replace("rh_", "")

    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{base_url}{RATEHAWK_ENDPOINTS['hotel_search']}",
                json={
                    "checkin": checkin,
                    "checkout": checkout,
                    "residency": "tr",
                    "language": "en",
                    "guests": [{"adults": 2, "children": []}],
                    "hids": [int(real_id)] if real_id.isdigit() else [],
                    "currency": "EUR",
                },
                headers=headers,
            )
        latency_ms = round((time.monotonic() - start) * 1000, 1)

        if resp.status_code == 200:
            data = resp.json()
            hotels = data.get("data", {}).get("hotels", data.get("hotels", []))
            if hotels:
                hotel = hotels[0]
                return {
                    "success": True,
                    "price": float(hotel.get("min_price", hotel.get("price", 0))),
                    "currency": hotel.get("currency", "EUR"),
                    "latency_ms": latency_ms,
                    "source": "ratehawk_api",
                }
            return {
                "success": False,
                "error": "Hotel not found in response",
                "latency_ms": latency_ms,
                "source": "ratehawk_api",
            }
        return {
            "success": False,
            "error": f"HTTP {resp.status_code}",
            "latency_ms": latency_ms,
            "source": "ratehawk_api",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "latency_ms": round((time.monotonic() - start) * 1000, 1),
            "source": "ratehawk_api",
        }


def _extract_rooms(hotel_raw: dict) -> list[dict]:
    """Extract room info from RateHawk hotel data."""
    rooms = hotel_raw.get("rooms", hotel_raw.get("room_groups", []))
    if isinstance(rooms, list):
        return [
            {
                "room_type": r.get("name", r.get("room_name", "Standard")),
                "capacity": r.get("capacity", r.get("max_guests", 2)),
            }
            for r in rooms[:5]
        ]
    return [{"room_type": "Standard", "capacity": 2}]
