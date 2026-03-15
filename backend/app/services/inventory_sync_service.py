"""Inventory Sync Engine — MEGA PROMPT #37.

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
    "wwtatil": {
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

async def trigger_supplier_sync(supplier: str) -> dict[str, Any]:
    """Trigger a full inventory sync for a given supplier.
    
    In simulation mode: generates realistic hotel inventory, prices, and availability.
    In sandbox/production mode: would call actual supplier APIs.
    """
    if supplier not in SUPPLIER_SYNC_CONFIG:
        return {"error": f"Unknown supplier: {supplier}", "available": list(SUPPLIER_SYNC_CONFIG.keys())}

    db = await get_db()
    sync_start = time.monotonic()

    # Create sync job record
    job_doc = {
        "supplier": supplier,
        "job_type": "full_sync",
        "status": "running",
        "started_at": _ts(),
        "finished_at": None,
        "records_updated": 0,
        "prices_updated": 0,
        "availability_updated": 0,
        "errors": [],
        "sync_mode": "simulation",
    }
    job_result = await db.inventory_sync_jobs.insert_one(job_doc)
    job_id = str(job_result.inserted_id)

    inventory_count = 0
    price_count = 0
    avail_count = 0
    errors = []

    try:
        # Phase 1: Sync inventory (hotels)
        hotels_for_supplier = _SIMULATED_HOTELS[: random.randint(8, len(_SIMULATED_HOTELS))]
        for idx, hotel_template in enumerate(hotels_for_supplier):
            hotel_id = f"{supplier[:2]}_{idx + 1:06d}"
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

            # Phase 2: Sync prices for next 30 days
            base_date = _now().date()
            for day_offset in range(30):
                target_date = (base_date + timedelta(days=day_offset)).isoformat()
                base_price = round(random.uniform(80, 600), 2)
                # Weekend markup
                if (base_date + timedelta(days=day_offset)).weekday() >= 5:
                    base_price = round(base_price * 1.15, 2)

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

            # Phase 3: Sync availability
            for day_offset in range(30):
                target_date = (base_date + timedelta(days=day_offset)).isoformat()
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

        # Phase 4: Build search index
        await _build_search_index(db, supplier)

        # Phase 5: Populate Redis cache
        redis_status = await _populate_redis_cache(db, supplier)

        status = "completed"
    except Exception as e:
        logger.error("Sync error for %s: %s", supplier, e, exc_info=True)
        errors.append(str(e))
        status = "failed"

    sync_duration_ms = round((time.monotonic() - sync_start) * 1000, 1)

    # Update job record
    await db.inventory_sync_jobs.update_one(
        {"_id": job_result.inserted_id},
        {"$set": {
            "status": status,
            "finished_at": _ts(),
            "records_updated": inventory_count,
            "prices_updated": price_count,
            "availability_updated": avail_count,
            "duration_ms": sync_duration_ms,
            "errors": errors,
        }},
    )

    return {
        "job_id": job_id,
        "supplier": supplier,
        "status": status,
        "records_updated": inventory_count,
        "prices_updated": price_count,
        "availability_updated": avail_count,
        "duration_ms": sync_duration_ms,
        "redis_cache": redis_status if status == "completed" else "skipped",
        "errors": errors,
        "timestamp": _ts(),
    }


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
    search_start = time.monotonic()
    source = "unknown"
    results = []

    # Try Redis first (fast path)
    try:
        from app.infrastructure.redis_client import get_async_redis
        r = await get_async_redis()
        if r:
            results, source = await _search_redis(r, destination, supplier, min_stars, limit)
    except Exception as e:
        logger.warning("Redis search failed, falling back to MongoDB: %s", e)

    # Fallback to MongoDB
    if not results:
        results, source = await _search_mongo(destination, supplier, min_stars, limit)

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
    """
    db = await get_db()
    reval_start = time.monotonic()

    # Get cached price
    cached = await db.supplier_prices.find_one(
        {"supplier": supplier, "hotel_id": hotel_id, "date": checkin},
        {"_id": 0},
    )
    cached_price = cached["price"] if cached else 0

    # Simulate supplier revalidation (in production: actual API call)
    # Price drift simulation based on supplier reliability
    drift_ranges = {
        "ratehawk": (-0.02, 0.05),
        "paximum": (-0.03, 0.08),
        "wwtatil": (-0.05, 0.12),
        "tbo": (-0.02, 0.06),
    }
    drift_min, drift_max = drift_ranges.get(supplier, (-0.03, 0.08))
    drift_pct = random.uniform(drift_min, drift_max)
    revalidated_price = round(cached_price * (1 + drift_pct), 2) if cached_price > 0 else round(random.uniform(100, 500), 2)

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
        "source": "simulation",
        "timestamp": _ts(),
    }

    # Record revalidation event
    await db.inventory_revalidations.insert_one({
        **result,
        "recorded_at": _ts(),
    })

    return result


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

    logger.info("Inventory indexes created successfully")
