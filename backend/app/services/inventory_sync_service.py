"""Inventory Sync Engine — MEGA PROMPT #37 + #38 Sandbox.

Travel Inventory Platform core: Supplier → Inventory Cache → Search Engine.

Collections:
  - supplier_inventory:    Hotel/product records synced from suppliers
  - supplier_prices:       Cached prices per hotel per date per supplier
  - supplier_availability: Room availability per hotel per date per supplier
  - inventory_sync_jobs:   Sync job tracking (status, records, timing)
  - inventory_index:       Flattened search-optimized documents

Architecture:
  search → Redis/Mongo cache (NOT supplier API)
  booking → supplier API (revalidation with diff tracking)

Sync modes:
  - simulation: Generated data (no credentials)
  - sandbox:    Real API calls to sandbox environment
  - production: Real API calls to production environment
"""
from __future__ import annotations

import json
import logging
import random
import time
from datetime import datetime, timezone, timedelta
from typing import Any

from app.db import get_db

logger = logging.getLogger("inventory.sync")


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Supplier Sync Configuration ───────────────────────────────────────
SUPPLIER_SYNC_CONFIG = {
    "ratehawk": {
        "sync_interval_minutes": 5,
        "product_types": ["hotel"],
        "priority": 1,
        "status": "active",
    },
    "paximum": {
        "sync_interval_minutes": 15,
        "product_types": ["hotel", "tour"],
        "priority": 2,
        "status": "active",
    },
    "wtatil": {
        "sync_interval_minutes": 60,
        "product_types": ["hotel"],
        "priority": 3,
        "status": "active",
    },
    "tbo": {
        "sync_interval_minutes": 30,
        "product_types": ["hotel", "flight"],
        "priority": 4,
        "status": "pending",
    },
}

# Sample hotel data for simulation
_SIMULATED_HOTELS = [
    {"name": "Hilton Dubai Marina", "city": "Dubai", "country": "AE", "stars": 5, "rooms": [{"room_type": "Deluxe", "capacity": 2}, {"room_type": "Suite", "capacity": 3}]},
    {"name": "Rixos Premium Belek", "city": "Antalya", "country": "TR", "stars": 5, "rooms": [{"room_type": "Standard", "capacity": 2}, {"room_type": "Family", "capacity": 4}]},
    {"name": "Titanic Mardan Palace", "city": "Antalya", "country": "TR", "stars": 5, "rooms": [{"room_type": "Deluxe", "capacity": 2}]},
    {"name": "Calista Luxury Resort", "city": "Belek", "country": "TR", "stars": 5, "rooms": [{"room_type": "Superior", "capacity": 2}, {"room_type": "Villa", "capacity": 6}]},
    {"name": "Kempinski Hotel Barbaros Bay", "city": "Bodrum", "country": "TR", "stars": 5, "rooms": [{"room_type": "Sea View", "capacity": 2}]},
    {"name": "Jumeirah Beach Hotel", "city": "Dubai", "country": "AE", "stars": 5, "rooms": [{"room_type": "Ocean", "capacity": 2}, {"room_type": "Penthouse", "capacity": 4}]},
    {"name": "Concorde De Luxe Resort", "city": "Antalya", "country": "TR", "stars": 5, "rooms": [{"room_type": "Standard", "capacity": 2}]},
    {"name": "Susesi Luxury Resort", "city": "Belek", "country": "TR", "stars": 5, "rooms": [{"room_type": "Standard", "capacity": 2}, {"room_type": "Suite", "capacity": 3}]},
    {"name": "Liberty Hotels Lara", "city": "Antalya", "country": "TR", "stars": 5, "rooms": [{"room_type": "Deluxe", "capacity": 2}]},
    {"name": "Voyage Belek Golf & Spa", "city": "Belek", "country": "TR", "stars": 5, "rooms": [{"room_type": "Standard", "capacity": 2}, {"room_type": "Family", "capacity": 4}]},
    {"name": "Swissotel The Bosphorus", "city": "Istanbul", "country": "TR", "stars": 5, "rooms": [{"room_type": "Classic", "capacity": 2}]},
    {"name": "Four Seasons Sultanahmet", "city": "Istanbul", "country": "TR", "stars": 5, "rooms": [{"room_type": "Superior", "capacity": 2}]},
    {"name": "Mandarin Oriental Bodrum", "city": "Bodrum", "country": "TR", "stars": 5, "rooms": [{"room_type": "Sea View", "capacity": 2}, {"room_type": "Villa", "capacity": 6}]},
    {"name": "Regnum Carya Golf Resort", "city": "Belek", "country": "TR", "stars": 5, "rooms": [{"room_type": "Standard", "capacity": 2}]},
    {"name": "Atlantis The Palm", "city": "Dubai", "country": "AE", "stars": 5, "rooms": [{"room_type": "Ocean Queen", "capacity": 2}, {"room_type": "Suite", "capacity": 4}]},
    {"name": "LykiaWorld Antalya", "city": "Antalya", "country": "TR", "stars": 4, "rooms": [{"room_type": "Standard", "capacity": 2}]},
    {"name": "Barut Lara", "city": "Antalya", "country": "TR", "stars": 5, "rooms": [{"room_type": "Standard", "capacity": 2}, {"room_type": "Suite", "capacity": 3}]},
    {"name": "Gloria Serenity Resort", "city": "Belek", "country": "TR", "stars": 5, "rooms": [{"room_type": "Deluxe", "capacity": 2}]},
    {"name": "IC Hotels Green Palace", "city": "Antalya", "country": "TR", "stars": 5, "rooms": [{"room_type": "Standard", "capacity": 2}]},
    {"name": "Maxx Royal Belek", "city": "Belek", "country": "TR", "stars": 5, "rooms": [{"room_type": "Royal", "capacity": 2}, {"room_type": "Villa", "capacity": 8}]},
]


# ── Inventory Sync Engine ────────────────────────────────────────────

async def _determine_sync_mode(supplier: str) -> tuple[str, dict | None]:
    """Determine sync mode for a supplier based on credential configuration.

    Returns: (mode, config) where mode is 'sandbox', 'production', or 'simulation'
    Respects SUPPLIER_SIMULATION_ALLOWED config flag for production safety.
    """
    try:
        from app.services.supplier_config_service import get_raw_credentials
        config = await get_raw_credentials(supplier)
        if config and config.get("credentials"):
            return config.get("mode", "sandbox"), config
    except Exception as e:
        logger.warning("Could not check credentials for %s: %s", supplier, e)

    # Check if simulation is allowed (production guard)
    from app.config import SUPPLIER_SIMULATION_ALLOWED
    if not SUPPLIER_SIMULATION_ALLOWED:
        logger.error("Simulation not allowed for %s — SUPPLIER_SIMULATION_ALLOWED=false", supplier)
        return "disabled", None
    return "simulation", None


async def trigger_supplier_sync(supplier: str) -> dict[str, Any]:
    """Trigger a full inventory sync for a given supplier.

    Sync modes:
      - simulation: Generated data (no credentials configured)
      - sandbox/production: Real API calls via supplier adapter

    Guards (P4.2):
      - Circuit breaker check (skip if supplier is down)
      - Stuck job detection with auto-retry scheduling
      - Duplicate sync prevention (skip if a job is already running)
      - Idempotency via distributed lock
    """
    from app.services.sync_job_state import SyncJobStatus

    if supplier not in SUPPLIER_SYNC_CONFIG:
        return {"error": f"Unknown supplier: {supplier}", "available": list(SUPPLIER_SYNC_CONFIG.keys())}

    db = await get_db()

    # ── Guard: Circuit breaker check (P4.2) ──
    from app.services.sync_stability_service import should_skip_sync_due_to_downtime
    skip, reason = await should_skip_sync_due_to_downtime(supplier)
    if skip:
        logger.warning("Sync skipped for %s: %s", supplier, reason)
        return {"status": "skipped_downtime", "message": reason, "supplier": supplier}

    # ── Guard: Detect and handle stuck jobs (P4.2 enhanced) ──
    from app.services.sync_stability_service import detect_and_handle_stuck_jobs
    stuck_result = await detect_and_handle_stuck_jobs()

    # ── Guard: Duplicate sync prevention (idempotency) ──
    running_job = await db.inventory_sync_jobs.find_one(
        {"supplier": supplier, "status": {"$in": SyncJobStatus.ACTIVE}},
        {"_id": 0},
    )
    if running_job:
        return {
            "status": "already_running",
            "message": f"A sync job for {supplier} is already active",
            "existing_job": {
                "started_at": running_job.get("started_at"),
                "sync_mode": running_job.get("sync_mode"),
                "job_status": running_job.get("status"),
            },
        }

    sync_mode, cred_config = await _determine_sync_mode(supplier)

    # Handle disabled mode (production guard)
    if sync_mode == "disabled":
        return {
            "error": f"Simulation disabled for {supplier} — credentials required (SUPPLIER_SIMULATION_ALLOWED=false)",
            "sync_mode": "disabled",
        }

    db = await get_db()
    sync_start = time.monotonic()

    # Create sync job record with enhanced state model (P4.2)
    job_doc = {
        "supplier": supplier,
        "job_type": "full_sync",
        "status": SyncJobStatus.RUNNING,
        "started_at": _ts(),
        "finished_at": None,
        "records_updated": 0,
        "records_total": 0,
        "records_succeeded": 0,
        "records_failed": 0,
        "prices_updated": 0,
        "availability_updated": 0,
        "errors": [],
        "error_count": 0,
        "sync_mode": sync_mode,
        "retry_count": 0,
        "retry_eligible": False,
        "region_results": [],
    }
    job_result = await db.inventory_sync_jobs.insert_one(job_doc)
    job_id = str(job_result.inserted_id)

    # Route to appropriate sync handler
    if sync_mode in ("sandbox", "production") and supplier == "ratehawk" and cred_config:
        result = await _sync_ratehawk_real(db, supplier, job_id, cred_config, sync_start, job_result.inserted_id)
    else:
        result = await _sync_simulation(db, supplier, job_id, sync_start, job_result.inserted_id)

    # Record outcome to circuit breaker (P4.2)
    from app.services.sync_stability_service import record_sync_outcome_to_breaker
    is_success = result.get("status") in [SyncJobStatus.COMPLETED, SyncJobStatus.COMPLETED_WITH_PARTIAL_ERRORS, "completed"]
    await record_sync_outcome_to_breaker(supplier, is_success)

    result["sync_mode"] = sync_mode
    return result


async def _sync_ratehawk_real(
    db, supplier: str, job_id: str, cred_config: dict, sync_start: float, job_oid
) -> dict[str, Any]:
    """Sync Ratehawk using real API adapter with partial failure handling (P4.2)."""
    from app.services.ratehawk_sync_adapter import sync_inventory_from_ratehawk
    from app.services.sync_stability_service import finalize_sync_job
    from app.services.sync_job_state import SyncJobStatus, REGION_SYNC_CONFIG

    inventory_count = 0
    price_count = 0
    avail_count = 0
    errors = []
    failed_records = 0
    region_results = []

    try:
        sync_result = await sync_inventory_from_ratehawk(
            cred_config["base_url"], cred_config["credentials"]
        )

        # Persist hotels to MongoDB with per-record error handling (P4.2)
        for hotel in sync_result.get("hotels", []):
            try:
                hotel["updated_at"] = _ts()
                hotel["sync_job_id"] = job_id
                await db.supplier_inventory.update_one(
                    {"supplier": supplier, "hotel_id": hotel["hotel_id"]},
                    {"$set": hotel},
                    upsert=True,
                )
                inventory_count += 1
            except Exception as e:
                failed_records += 1
                errors.append({"hotel_id": hotel.get("hotel_id"), "phase": "inventory", "error": str(e)})

        # Persist prices with per-record error handling
        for price in sync_result.get("prices", []):
            try:
                price["updated_at"] = _ts()
                await db.supplier_prices.update_one(
                    {"supplier": supplier, "hotel_id": price["hotel_id"], "date": price["date"]},
                    {"$set": price},
                    upsert=True,
                )
                price_count += 1
            except Exception as e:
                errors.append({"hotel_id": price.get("hotel_id"), "phase": "price", "error": str(e)})

        # Persist availability with per-record error handling
        for avail in sync_result.get("availability", []):
            try:
                avail["updated_at"] = _ts()
                await db.supplier_availability.update_one(
                    {"supplier": supplier, "hotel_id": avail["hotel_id"], "date": avail["date"]},
                    {"$set": avail},
                    upsert=True,
                )
                avail_count += 1
            except Exception as e:
                errors.append({"hotel_id": avail.get("hotel_id"), "phase": "availability", "error": str(e)})

        # Build search index and Redis cache
        await _build_search_index(db, supplier)
        redis_status = await _populate_redis_cache(db, supplier)

        api_errors = sync_result.get("errors", [])
        if api_errors:
            errors.extend([{"phase": "api", "error": str(e)} for e in api_errors])

        metrics = sync_result.get("metrics", {})

    except Exception as e:
        logger.error("Real sync error for %s: %s", supplier, e, exc_info=True)
        errors.append({"error": str(e), "phase": "sync_execution"})
        metrics = {}
        redis_status = "skipped"
        failed_records = max(failed_records, 1)

    sync_duration_ms = round((time.monotonic() - sync_start) * 1000, 1)
    total_records = inventory_count + failed_records

    # Use stability service for finalization (P4.2)
    status = await finalize_sync_job(
        job_oid,
        total_records=total_records,
        successful_records=inventory_count,
        failed_records=failed_records + len([e for e in errors if e.get("phase") != "api"]),
        errors=errors,
        region_results=region_results,
        sync_duration_ms=sync_duration_ms,
        extra_fields={
            "records_updated": inventory_count,
            "prices_updated": price_count,
            "availability_updated": avail_count,
            "api_metrics": metrics,
            "redis_cache": redis_status if failed_records == 0 else "partial",
        },
    )

    # Record supplier metrics for dashboard
    await _record_supplier_metrics(db, supplier, metrics, status)

    return {
        "job_id": job_id,
        "supplier": supplier,
        "status": status,
        "records_updated": inventory_count,
        "records_total": total_records,
        "records_failed": failed_records,
        "prices_updated": price_count,
        "availability_updated": avail_count,
        "duration_ms": sync_duration_ms,
        "redis_cache": redis_status if status != SyncJobStatus.FAILED else "skipped",
        "errors": errors[:20],
        "error_count": len(errors),
        "api_metrics": metrics,
        "timestamp": _ts(),
    }


async def _sync_simulation(
    db, supplier: str, job_id: str, sync_start: float, job_oid
) -> dict[str, Any]:
    """Simulation sync with partial failure handling (P4.2).

    Preserves successful records even if some fail.
    Tracks per-region results for region-level retry.
    """
    from app.services.sync_stability_service import finalize_sync_job
    from app.services.sync_job_state import SyncJobStatus, REGION_SYNC_CONFIG

    inventory_count = 0
    price_count = 0
    avail_count = 0
    errors = []
    failed_records = 0
    region_results = []

    try:
        hotels_for_supplier = _SIMULATED_HOTELS[: random.randint(8, len(_SIMULATED_HOTELS))]

        # Group hotels by city/region for region-level tracking (P4.2)
        regions = REGION_SYNC_CONFIG.get(supplier, [])
        region_hotel_map: dict[str, list] = {}
        for hotel in hotels_for_supplier:
            city = hotel["city"]
            region_hotel_map.setdefault(city, []).append(hotel)

        for idx, hotel_template in enumerate(hotels_for_supplier):
            hotel_id = f"{supplier[:2]}_{idx + 1:06d}"
            try:
                inventory_doc = {
                    "supplier": supplier,
                    "hotel_id": hotel_id,
                    "name": hotel_template["name"],
                    "city": hotel_template["city"],
                    "country": hotel_template["country"],
                    "stars": hotel_template["stars"],
                    "rooms": hotel_template["rooms"],
                    "updated_at": _ts(),
                    "sync_job_id": job_id,
                }
                await db.supplier_inventory.update_one(
                    {"supplier": supplier, "hotel_id": hotel_id},
                    {"$set": inventory_doc},
                    upsert=True,
                )
                inventory_count += 1
            except Exception as e:
                failed_records += 1
                errors.append({"hotel_id": hotel_id, "phase": "inventory", "error": str(e), "region": hotel_template["city"]})
                continue

            base_date = _now().date()
            for day_offset in range(30):
                target_date = (base_date + timedelta(days=day_offset)).isoformat()
                base_price = round(random.uniform(80, 600), 2)
                if (base_date + timedelta(days=day_offset)).weekday() >= 5:
                    base_price = round(base_price * 1.15, 2)

                try:
                    price_doc = {
                        "supplier": supplier,
                        "hotel_id": hotel_id,
                        "date": target_date,
                        "price": base_price,
                        "currency": "EUR",
                        "updated_at": _ts(),
                    }
                    await db.supplier_prices.update_one(
                        {"supplier": supplier, "hotel_id": hotel_id, "date": target_date},
                        {"$set": price_doc},
                        upsert=True,
                    )
                    price_count += 1
                except Exception as e:
                    errors.append({"hotel_id": hotel_id, "phase": "price", "error": str(e)})

            for day_offset in range(30):
                target_date = (base_date + timedelta(days=day_offset)).isoformat()
                try:
                    avail_doc = {
                        "supplier": supplier,
                        "hotel_id": hotel_id,
                        "date": target_date,
                        "rooms_available": random.randint(0, 12),
                        "updated_at": _ts(),
                    }
                    await db.supplier_availability.update_one(
                        {"supplier": supplier, "hotel_id": hotel_id, "date": target_date},
                        {"$set": avail_doc},
                        upsert=True,
                    )
                    avail_count += 1
                except Exception as e:
                    errors.append({"hotel_id": hotel_id, "phase": "availability", "error": str(e)})

        # Build region results (P4.2)
        for region in regions:
            region_city = region["name"]
            region_hotel_count = len([h for h in hotels_for_supplier if h["city"] == region_city])
            region_errors = [e for e in errors if e.get("region") == region_city]
            region_results.append({
                "region_id": region["id"],
                "region_name": region_city,
                "hotels_synced": region_hotel_count - len(region_errors),
                "hotels_failed": len(region_errors),
                "status": "failed" if len(region_errors) == region_hotel_count and region_hotel_count > 0
                    else "partial" if region_errors
                    else "completed",
            })

        await _build_search_index(db, supplier)
        redis_status = await _populate_redis_cache(db, supplier)

    except Exception as e:
        logger.error("Sync error for %s: %s", supplier, e, exc_info=True)
        errors.append({"error": str(e), "phase": "sync_execution"})
        redis_status = "skipped"
        failed_records = max(failed_records, 1)

    sync_duration_ms = round((time.monotonic() - sync_start) * 1000, 1)
    total_records = inventory_count + failed_records

    # Use stability service for finalization (P4.2)
    status = await finalize_sync_job(
        job_oid,
        total_records=total_records,
        successful_records=inventory_count,
        failed_records=failed_records,
        errors=errors,
        region_results=region_results,
        sync_duration_ms=sync_duration_ms,
        extra_fields={
            "records_updated": inventory_count,
            "prices_updated": price_count,
            "availability_updated": avail_count,
            "redis_cache": redis_status if failed_records == 0 else "partial",
        },
    )

    return {
        "job_id": job_id,
        "supplier": supplier,
        "status": status,
        "records_updated": inventory_count,
        "records_total": total_records,
        "records_failed": failed_records,
        "prices_updated": price_count,
        "availability_updated": avail_count,
        "duration_ms": sync_duration_ms,
        "redis_cache": redis_status if status == SyncJobStatus.COMPLETED else "partial",
        "errors": errors[:20],
        "error_count": len(errors),
        "region_results": region_results,
        "timestamp": _ts(),
    }


async def _record_supplier_metrics(
    db, supplier: str, metrics: dict, status: str
) -> None:
    """Record supplier-level performance metrics for the dashboard."""
    try:
        api_calls = metrics.get("api_calls", 0)
        errors_count = metrics.get("errors_count", 0)
        hotels_count = metrics.get("hotels_count", 0)
        avail_count = metrics.get("availability_count", 0)

        success_rate = round(((api_calls - errors_count) / max(api_calls, 1)) * 100, 2)
        availability_rate = round((avail_count / max(hotels_count, 1)) * 100, 2) if hotels_count > 0 else 0.0

        await db.supplier_sync_metrics.insert_one({
            "supplier": supplier,
            "timestamp": _ts(),
            "status": status,
            "api_calls": api_calls,
            "avg_latency_ms": metrics.get("avg_latency_ms", 0),
            "error_rate_pct": metrics.get("error_rate_pct", 0),
            "success_rate_pct": success_rate,
            "availability_rate_pct": availability_rate,
            "hotels_synced": hotels_count,
            "prices_synced": metrics.get("prices_count", 0),
            "availability_synced": avail_count,
            "sync_duration_ms": metrics.get("sync_duration_ms", 0),
        })
    except Exception as e:
        logger.warning("Failed to record supplier metrics: %s", e)


async def _build_search_index(db, supplier: str) -> int:
    """Build flattened search index from inventory + latest prices."""
    count = 0
    cursor = db.supplier_inventory.find({"supplier": supplier}, {"_id": 0})
    async for inv in cursor:
        hotel_id = inv["hotel_id"]
        # Get latest price for this hotel
        price_doc = await db.supplier_prices.find_one(
            {"supplier": supplier, "hotel_id": hotel_id},
            {"_id": 0},
            sort=[("date", 1)],
        )
        # Get availability
        avail_doc = await db.supplier_availability.find_one(
            {"supplier": supplier, "hotel_id": hotel_id},
            {"_id": 0},
            sort=[("date", 1)],
        )

        index_doc = {
            "supplier": supplier,
            "hotel_id": hotel_id,
            "name": inv["name"],
            "city": inv["city"],
            "country": inv["country"],
            "stars": inv["stars"],
            "rooms": inv.get("rooms", []),
            "min_price": price_doc["price"] if price_doc else 0,
            "currency": price_doc["currency"] if price_doc else "EUR",
            "rooms_available": avail_doc["rooms_available"] if avail_doc else 0,
            "available": (avail_doc["rooms_available"] if avail_doc else 0) > 0,
            "updated_at": _ts(),
        }

        await db.inventory_index.update_one(
            {"supplier": supplier, "hotel_id": hotel_id},
            {"$set": index_doc},
            upsert=True,
        )
        count += 1

    logger.info("Built search index for %s: %d entries", supplier, count)
    return count


async def _populate_redis_cache(db, supplier: str) -> dict[str, Any]:
    """Populate Redis with search index for ultra-fast lookups."""
    try:
        from app.infrastructure.redis_client import get_async_redis
        r = await get_async_redis()
        if not r:
            return {"status": "unavailable", "reason": "Redis not connected"}

        count = 0
        cursor = db.inventory_index.find({"supplier": supplier}, {"_id": 0})
        async for doc in cursor:
            cache_key = f"inv:{supplier}:{doc['hotel_id']}"
            await r.setex(cache_key, 600, json.dumps(doc, default=str))
            count += 1

            # City-level index for search
            city_key = f"inv_city:{supplier}:{doc['city'].lower()}"
            await r.sadd(city_key, doc["hotel_id"])
            await r.expire(city_key, 600)

        return {"status": "populated", "entries": count}
    except Exception as e:
        logger.warning("Redis cache population failed: %s", e)
        return {"status": "fallback_to_mongo", "reason": str(e)}


# ── Cached Search Engine ─────────────────────────────────────────────

async def search_inventory(
    destination: str,
    checkin: str | None = None,
    checkout: str | None = None,
    guests: int = 2,
    min_stars: int = 0,
    supplier: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Search inventory from cache (Redis → MongoDB fallback).

    This is the core of the Inventory Platform architecture:
    search → cache, NOT search → supplier API.
    """
    from app.services import cache_metrics as cm

    search_start = time.monotonic()
    source = "unknown"
    results = []

    # Try Redis first (fast path)
    try:
        from app.infrastructure.redis_client import get_async_redis
        r = await get_async_redis()
        if r:
            t0 = time.monotonic()
            results, source = await _search_redis(r, destination, supplier, min_stars, limit)
            redis_ms = round((time.monotonic() - t0) * 1000, 1)
            cm.record_latency("redis_search", redis_ms)
            if results:
                cm.hit("redis")
            else:
                cm.miss("redis")
        else:
            cm.redis_down()
    except Exception as e:
        logger.warning("Redis search failed, falling back to MongoDB: %s", e)
        cm.redis_down()

    # Fallback to MongoDB
    if not results:
        t1 = time.monotonic()
        results, source = await _search_mongo(destination, supplier, min_stars, limit)
        mongo_ms = round((time.monotonic() - t1) * 1000, 1)
        cm.record_latency("mongo_search", mongo_ms)
        if source == "mongodb":
            cm.fallback("redis", "mongo")
            cm.hit("mongo")

    # Filter by availability if dates provided
    if checkin and checkout:
        results = await _filter_by_availability(results, checkin, checkout)

    search_duration_ms = round((time.monotonic() - search_start) * 1000, 1)

    return {
        "results": results[:limit],
        "total": len(results),
        "source": source,
        "search_params": {
            "destination": destination,
            "checkin": checkin,
            "checkout": checkout,
            "guests": guests,
            "min_stars": min_stars,
            "supplier": supplier,
        },
        "latency_ms": search_duration_ms,
        "timestamp": _ts(),
    }


async def _search_redis(r, destination: str, supplier: str | None, min_stars: int, limit: int) -> tuple[list, str]:
    """Search via Redis cache."""
    results = []
    dest_lower = destination.lower()

    # Determine which suppliers to search
    suppliers_to_search = [supplier] if supplier else list(SUPPLIER_SYNC_CONFIG.keys())

    for sup in suppliers_to_search:
        city_key = f"inv_city:{sup}:{dest_lower}"
        hotel_ids = await r.smembers(city_key)
        for hotel_id in hotel_ids:
            cache_key = f"inv:{sup}:{hotel_id}"
            raw = await r.get(cache_key)
            if raw:
                doc = json.loads(raw)
                if doc.get("stars", 0) >= min_stars and doc.get("available", False):
                    results.append(doc)
            if len(results) >= limit:
                break
        if len(results) >= limit:
            break

    return results, "redis" if results else "redis_miss"


async def _search_mongo(destination: str, supplier: str | None, min_stars: int, limit: int) -> tuple[list, str]:
    """Fallback search via MongoDB inventory_index."""
    db = await get_db()
    query: dict[str, Any] = {
        "city": {"$regex": f"^{destination}$", "$options": "i"},
        "available": True,
    }
    if min_stars > 0:
        query["stars"] = {"$gte": min_stars}
    if supplier:
        query["supplier"] = supplier

    results = []
    cursor = db.inventory_index.find(query, {"_id": 0}).sort("min_price", 1).limit(limit)
    async for doc in cursor:
        results.append(doc)

    return results, "mongodb"


async def _filter_by_availability(results: list, checkin: str, checkout: str) -> list:
    """Filter results by date-specific availability."""
    db = await get_db()
    filtered = []
    for item in results:
        avail = await db.supplier_availability.find_one(
            {
                "supplier": item["supplier"],
                "hotel_id": item["hotel_id"],
                "date": checkin,
                "rooms_available": {"$gt": 0},
            },
            {"_id": 0},
        )
        if avail:
            item["rooms_available_checkin"] = avail["rooms_available"]
            filtered.append(item)
    return filtered


# ── Supplier Revalidation ─────────────────────────────────────────────

async def revalidate_price(supplier: str, hotel_id: str, checkin: str, checkout: str) -> dict[str, Any]:
    """Revalidate price with supplier at booking time.

    This is the only step that contacts the supplier API directly.
    cached_price → supplier_price → diff calculation.

    Uses real API when credentials configured, simulation otherwise.
    """
    db = await get_db()
    reval_start = time.monotonic()

    # Get cached price
    cached = await db.supplier_prices.find_one(
        {"supplier": supplier, "hotel_id": hotel_id, "date": checkin},
        {"_id": 0},
    )
    cached_price = cached["price"] if cached else 0

    # Determine if we use real API or simulation
    sync_mode, cred_config = await _determine_sync_mode(supplier)
    source = sync_mode

    revalidated_price = 0
    supplier_latency_ms = 0

    if sync_mode in ("sandbox", "production") and supplier == "ratehawk" and cred_config:
        # Real API revalidation
        from app.services.ratehawk_sync_adapter import revalidate_price_from_ratehawk
        reval_result = await revalidate_price_from_ratehawk(
            cred_config["base_url"], cred_config["credentials"],
            hotel_id, checkin, checkout,
        )
        if reval_result.get("success"):
            revalidated_price = reval_result["price"]
            supplier_latency_ms = reval_result.get("latency_ms", 0)
            source = reval_result.get("source", "ratehawk_api")
        else:
            # Fallback to simulation if API fails
            logger.warning("Ratehawk revalidation failed, using simulation: %s", reval_result.get("error"))
            source = "simulation_fallback"
            revalidated_price = _simulate_revalidation_price(supplier, cached_price)
    else:
        # Simulation revalidation
        revalidated_price = _simulate_revalidation_price(supplier, cached_price)

    diff_amount = round(revalidated_price - cached_price, 2)
    diff_pct = round((diff_amount / cached_price) * 100, 2) if cached_price > 0 else 0

    # Drift severity classification
    abs_diff = abs(diff_pct)
    if abs_diff <= 2:
        severity = "normal"
    elif abs_diff <= 5:
        severity = "warning"
    elif abs_diff <= 10:
        severity = "high"
    else:
        severity = "critical"

    reval_duration_ms = round((time.monotonic() - reval_start) * 1000, 1)

    result = {
        "supplier": supplier,
        "hotel_id": hotel_id,
        "checkin": checkin,
        "checkout": checkout,
        "cached_price": cached_price,
        "revalidated_price": revalidated_price,
        "diff_amount": diff_amount,
        "diff_pct": diff_pct,
        "drift_direction": "up" if diff_amount > 0 else ("down" if diff_amount < 0 else "stable"),
        "drift_severity": severity,
        "currency": cached.get("currency", "EUR") if cached else "EUR",
        "latency_ms": reval_duration_ms,
        "supplier_latency_ms": supplier_latency_ms,
        "source": source,
        "timestamp": _ts(),
    }

    # Record revalidation event
    await db.inventory_revalidations.insert_one({
        **result,
        "recorded_at": _ts(),
    })

    return result


def _simulate_revalidation_price(supplier: str, cached_price: float) -> float:
    """Generate a simulated revalidation price with realistic drift."""
    drift_ranges = {
        "ratehawk": (-0.02, 0.05),
        "paximum": (-0.03, 0.08),
        "wtatil": (-0.05, 0.12),
        "tbo": (-0.02, 0.06),
    }
    drift_min, drift_max = drift_ranges.get(supplier, (-0.03, 0.08))
    drift_pct = random.uniform(drift_min, drift_max)
    if cached_price > 0:
        return round(cached_price * (1 + drift_pct), 2)
    return round(random.uniform(100, 500), 2)


# ── Sync Job Management ──────────────────────────────────────────────

async def get_sync_jobs(supplier: str | None = None, limit: int = 20) -> dict[str, Any]:
    """List sync jobs with optional supplier filter."""
    db = await get_db()
    query: dict[str, Any] = {}
    if supplier:
        query["supplier"] = supplier

    jobs = []
    cursor = db.inventory_sync_jobs.find(query, {"_id": 0}).sort("started_at", -1).limit(limit)
    async for doc in cursor:
        jobs.append(doc)

    return {
        "jobs": jobs,
        "total": len(jobs),
        "timestamp": _ts(),
    }


async def get_sync_status() -> dict[str, Any]:
    """Get overall sync status for all suppliers."""
    db = await get_db()
    status = {}

    for supplier, config in SUPPLIER_SYNC_CONFIG.items():
        # Last sync job for this supplier
        last_job = await db.inventory_sync_jobs.find_one(
            {"supplier": supplier},
            {"_id": 0},
            sort=[("started_at", -1)],
        )

        # Inventory count
        inv_count = await db.supplier_inventory.count_documents({"supplier": supplier})
        price_count = await db.supplier_prices.count_documents({"supplier": supplier})
        avail_count = await db.supplier_availability.count_documents({"supplier": supplier})
        index_count = await db.inventory_index.count_documents({"supplier": supplier})

        status[supplier] = {
            "config": config,
            "last_sync": {
                "status": last_job["status"] if last_job else "never",
                "started_at": last_job.get("started_at") if last_job else None,
                "finished_at": last_job.get("finished_at") if last_job else None,
                "duration_ms": last_job.get("duration_ms", 0) if last_job else 0,
                "records_updated": last_job.get("records_updated", 0) if last_job else 0,
            },
            "inventory": {
                "hotels": inv_count,
                "prices": price_count,
                "availability": avail_count,
                "search_index": index_count,
            },
        }

    return {
        "suppliers": status,
        "timestamp": _ts(),
    }


async def get_inventory_stats() -> dict[str, Any]:
    """Get comprehensive inventory statistics."""
    db = await get_db()

    total_hotels = await db.supplier_inventory.count_documents({})
    total_prices = await db.supplier_prices.count_documents({})
    total_avail = await db.supplier_availability.count_documents({})
    total_index = await db.inventory_index.count_documents({})
    total_jobs = await db.inventory_sync_jobs.count_documents({})
    total_revalidations = await db.inventory_revalidations.count_documents({})

    # Supplier breakdown
    suppliers = {}
    for sup in SUPPLIER_SYNC_CONFIG:
        suppliers[sup] = {
            "hotels": await db.supplier_inventory.count_documents({"supplier": sup}),
            "prices": await db.supplier_prices.count_documents({"supplier": sup}),
            "availability": await db.supplier_availability.count_documents({"supplier": sup}),
            "index": await db.inventory_index.count_documents({"supplier": sup}),
        }

    # City breakdown from index
    cities = {}
    pipeline = [
        {"$group": {"_id": "$city", "count": {"$sum": 1}, "avg_price": {"$avg": "$min_price"}}},
        {"$sort": {"count": -1}},
        {"$limit": 10},
    ]
    async for doc in db.inventory_index.aggregate(pipeline):
        cities[doc["_id"]] = {
            "hotels": doc["count"],
            "avg_price": round(doc.get("avg_price", 0), 2),
        }

    # Recent revalidations with drift info
    recent_revals = []
    cursor = db.inventory_revalidations.find({}, {"_id": 0}).sort("recorded_at", -1).limit(10)
    async for doc in cursor:
        recent_revals.append(doc)

    # Redis cache status
    redis_status = {"status": "unknown"}
    try:
        from app.infrastructure.redis_client import get_async_redis
        r = await get_async_redis()
        if r:
            inv_keys = 0
            async for _ in r.scan_iter(match="inv:*", count=100):
                inv_keys += 1
            redis_status = {"status": "connected", "cached_entries": inv_keys}
        else:
            redis_status = {"status": "unavailable"}
    except Exception as e:
        redis_status = {"status": "error", "reason": str(e)}

    return {
        "totals": {
            "hotels": total_hotels,
            "prices": total_prices,
            "availability": total_avail,
            "search_index": total_index,
            "sync_jobs": total_jobs,
            "revalidations": total_revalidations,
        },
        "by_supplier": suppliers,
        "by_city": cities,
        "redis_cache": redis_status,
        "recent_revalidations": recent_revals,
        "sync_config": SUPPLIER_SYNC_CONFIG,
        "timestamp": _ts(),
    }


# ── Supplier Health ───────────────────────────────────────────────────

async def get_supplier_health(supplier: str | None = None) -> dict[str, Any]:
    """Get supplier health status based on recent metrics.

    Status logic:
      healthy  — success_rate >= 95% AND avg_latency < 2000ms
      degraded — success_rate >= 80% OR avg_latency < 5000ms
      down     — success_rate < 80% OR no recent data
    """
    db = await get_db()
    results = {}

    suppliers_list = [supplier] if supplier else list(SUPPLIER_SYNC_CONFIG.keys())

    for sup in suppliers_list:
        # Get last 10 metrics for averaging
        metrics_cursor = db.supplier_sync_metrics.find(
            {"supplier": sup}, {"_id": 0}
        ).sort("timestamp", -1).limit(10)
        recent_metrics = []
        async for doc in metrics_cursor:
            recent_metrics.append(doc)

        # Get last sync job
        last_sync = await db.inventory_sync_jobs.find_one(
            {"supplier": sup}, {"_id": 0},
            sort=[("started_at", -1)],
        )

        # Get last validation
        from app.services.supplier_config_service import get_supplier_config
        config = await get_supplier_config(sup)
        last_validation = config.get("last_validated") if config else None
        validation_status = config.get("validation_status", "not_tested") if config else "not_configured"

        if recent_metrics:
            avg_latency = round(sum(m.get("avg_latency_ms", 0) for m in recent_metrics) / len(recent_metrics), 1)
            avg_error_rate = round(sum(m.get("error_rate_pct", 0) for m in recent_metrics) / len(recent_metrics), 2)
            avg_success_rate = round(sum(m.get("success_rate_pct", 100) for m in recent_metrics) / len(recent_metrics), 2)
            avg_availability_rate = round(sum(m.get("availability_rate_pct", 0) for m in recent_metrics) / len(recent_metrics), 2)

            if avg_success_rate >= 95 and avg_latency < 2000:
                status = "healthy"
            elif avg_success_rate >= 80 or avg_latency < 5000:
                status = "degraded"
            else:
                status = "down"
        else:
            avg_latency = 0
            avg_error_rate = 0
            avg_success_rate = 0
            avg_availability_rate = 0
            status = "down" if not last_sync else "healthy"

        results[sup] = {
            "supplier": sup,
            "latency_avg": avg_latency,
            "error_rate": avg_error_rate,
            "success_rate": avg_success_rate,
            "availability_rate": avg_availability_rate,
            "last_sync": last_sync.get("started_at") if last_sync else None,
            "last_sync_status": last_sync.get("status") if last_sync else "never",
            "last_sync_duration_ms": last_sync.get("duration_ms", 0) if last_sync else 0,
            "last_validation": last_validation,
            "validation_status": validation_status,
            "status": status,
            "metrics_count": len(recent_metrics),
        }

    return {"suppliers": results, "timestamp": _ts()}


# ── KPI Data ─────────────────────────────────────────────────────────

async def get_kpi_data(supplier: str | None = None) -> dict[str, Any]:
    """Calculate KPI data for the dashboard.

    Returns:
      - drift_rate: drift > 2% / total revalidations per supplier
      - severity_breakdown: count by severity per supplier
      - price_drift_timeline: recent diffs with timestamps for charting
      - price_consistency: 1 - drift_rate
    """
    db = await get_db()
    query: dict[str, Any] = {}
    if supplier:
        query["supplier"] = supplier

    # Get all revalidations
    total_revals = await db.inventory_revalidations.count_documents(query)

    # Count drifted (abs diff > 2%)
    drift_query = {**query, "$expr": {"$gt": [{"$abs": "$diff_pct"}, 2]}}
    drifted_count = await db.inventory_revalidations.count_documents(drift_query)

    drift_rate = round((drifted_count / max(total_revals, 1)) * 100, 2)
    price_consistency = round(1 - (drift_rate / 100), 4)

    # Severity breakdown (aggregate per supplier)
    severity_pipeline = [
        {"$match": query} if query else {"$match": {}},
        {"$group": {
            "_id": {"supplier": "$supplier", "severity": "$drift_severity"},
            "count": {"$sum": 1},
        }},
        {"$sort": {"_id.supplier": 1, "count": -1}},
    ]
    severity_breakdown = {}
    async for doc in db.inventory_revalidations.aggregate(severity_pipeline):
        sup = doc["_id"]["supplier"]
        sev = doc["_id"]["severity"]
        if sup not in severity_breakdown:
            severity_breakdown[sup] = {"normal": 0, "warning": 0, "high": 0, "critical": 0, "total": 0}
        severity_breakdown[sup][sev] = doc["count"]
        severity_breakdown[sup]["total"] += doc["count"]

    # Per-supplier drift rates
    supplier_drift_rates = {}
    for sup in severity_breakdown:
        sup_total = severity_breakdown[sup]["total"]
        sup_drifted = sup_total - severity_breakdown[sup].get("normal", 0)
        supplier_drift_rates[sup] = {
            "drift_rate": round((sup_drifted / max(sup_total, 1)) * 100, 2),
            "price_consistency": round(1 - (sup_drifted / max(sup_total, 1)), 4),
            "total_revalidations": sup_total,
            "drifted_count": sup_drifted,
        }

    # Price drift timeline (last 50 revalidations)
    timeline_cursor = db.inventory_revalidations.find(
        query, {"_id": 0, "supplier": 1, "diff_pct": 1, "drift_severity": 1, "timestamp": 1, "recorded_at": 1}
    ).sort("recorded_at", -1).limit(50)
    timeline = []
    async for doc in timeline_cursor:
        timeline.append({
            "supplier": doc.get("supplier"),
            "diff_pct": doc.get("diff_pct", 0),
            "severity": doc.get("drift_severity", "normal"),
            "timestamp": doc.get("recorded_at", doc.get("timestamp")),
        })
    timeline.reverse()  # oldest first for chart

    return {
        "drift_rate": drift_rate,
        "price_consistency": price_consistency,
        "total_revalidations": total_revals,
        "drifted_count": drifted_count,
        "severity_breakdown": severity_breakdown,
        "supplier_drift_rates": supplier_drift_rates,
        "price_drift_timeline": timeline,
        "timestamp": _ts(),
    }


# ── Ensure Indexes ───────────────────────────────────────────────────

async def ensure_inventory_indexes():
    """Create MongoDB indexes for inventory collections."""
    db = await get_db()

    # supplier_inventory indexes
    await db.supplier_inventory.create_index([("supplier", 1), ("hotel_id", 1)], unique=True)
    await db.supplier_inventory.create_index([("city", 1)])
    await db.supplier_inventory.create_index([("country", 1)])

    # supplier_prices indexes
    await db.supplier_prices.create_index([("supplier", 1), ("hotel_id", 1), ("date", 1)], unique=True)
    await db.supplier_prices.create_index([("date", 1)])

    # supplier_availability indexes
    await db.supplier_availability.create_index([("supplier", 1), ("hotel_id", 1), ("date", 1)], unique=True)
    await db.supplier_availability.create_index([("date", 1), ("rooms_available", 1)])

    # inventory_index indexes (search optimized)
    await db.inventory_index.create_index([("supplier", 1), ("hotel_id", 1)], unique=True)
    await db.inventory_index.create_index([("city", 1), ("available", 1), ("min_price", 1)])
    await db.inventory_index.create_index([("stars", 1)])
    await db.inventory_index.create_index([("country", 1), ("city", 1)])

    # inventory_sync_jobs indexes
    await db.inventory_sync_jobs.create_index([("supplier", 1), ("started_at", -1)])
    await db.inventory_sync_jobs.create_index([("status", 1)])

    # inventory_revalidations indexes
    await db.inventory_revalidations.create_index([("supplier", 1), ("hotel_id", 1)])
    await db.inventory_revalidations.create_index([("recorded_at", -1)])
    await db.inventory_revalidations.create_index([("drift_severity", 1)])
    await db.inventory_revalidations.create_index([("diff_pct", 1)])

    # supplier_sync_metrics indexes
    await db.supplier_sync_metrics.create_index([("supplier", 1), ("timestamp", -1)])

    logger.info("Inventory indexes created successfully")
