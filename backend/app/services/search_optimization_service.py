"""Optimized search availability using MongoDB aggregation pipeline.

Replaces nested loop pattern with single aggregation pipeline
for better performance during high-traffic periods.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.db import get_db
from app.services.mongo_cache_service import cache_get, cache_set

logger = logging.getLogger("search_optimization")


async def search_available_hotels(
    organization_id: str,
    check_in: str,
    check_out: str,
    guests: int = 2,
    room_type: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    agency_id: Optional[str] = None,
    limit: int = 50,
    skip: int = 0,
) -> dict[str, Any]:
    """Optimized hotel availability search using aggregation pipeline."""
    # Check cache first
    cache_key = f"search:{organization_id}:{check_in}:{check_out}:{guests}:{room_type}:{min_price}:{max_price}:{agency_id}:{limit}:{skip}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    db = await get_db()

    # Single aggregation pipeline instead of nested loops
    pipeline: list[dict[str, Any]] = [
        # Stage 1: Match active hotels in organization
        {"$match": {
            "organization_id": organization_id,
            "is_active": {"$ne": False},
        }},

        # Stage 2: Lookup stop-sell rules to exclude blocked hotels
        {"$lookup": {
            "from": "stop_sell_rules",
            "let": {"hotel_id": "$_id", "org_id": "$organization_id"},
            "pipeline": [
                {"$match": {
                    "$expr": {
                        "$and": [
                            {"$eq": ["$tenant_id", "$$hotel_id"]},
                            {"$eq": ["$organization_id", "$$org_id"]},
                            {"$eq": ["$is_active", True]},
                            {"$lte": ["$start_date", check_out]},
                            {"$gte": ["$end_date", check_in]},
                        ],
                    },
                }},
            ],
            "as": "stop_sells",
        }},

        # Stage 3: Filter out fully stopped hotels
        {"$match": {
            "$expr": {"$eq": [{"$size": "$stop_sells"}, 0]},
        }},

        # Stage 4: Lookup pre-computed availability snapshots
        {"$lookup": {
            "from": "inventory_snapshots",
            "let": {"hotel_id": "$_id", "org_id": "$organization_id"},
            "pipeline": [
                {"$match": {
                    "$expr": {
                        "$and": [
                            {"$eq": ["$hotel_id", "$$hotel_id"]},
                            {"$eq": ["$organization_id", "$$org_id"]},
                            {"$gte": ["$date", check_in]},
                            {"$lt": ["$date", check_out]},
                            {"$gt": ["$available", 0]},
                        ],
                    },
                }},
            ],
            "as": "availability",
        }},

        # Stage 5: Add computed fields
        {"$addFields": {
            "has_availability": {
                "$cond": [
                    {"$gt": [{"$size": "$availability"}, 0]},
                    True,
                    True,  # Default to available if no snapshots exist
                ],
            },
        }},

        # Stage 6: Project fields
        {"$project": {
            "_id": 1,
            "name": 1,
            "city": 1,
            "country": 1,
            "star_rating": 1,
            "images": 1,
            "description": 1,
            "amenities": 1,
            "base_price": 1,
            "currency": 1,
            "has_availability": 1,
            "availability": 1,
            "stop_sells": {"$size": "$stop_sells"},
        }},

        # Stage 7: Sort and paginate
        {"$sort": {"star_rating": -1, "name": 1}},
        {"$skip": skip},
        {"$limit": limit},
    ]

    # Add price filter if specified
    if min_price is not None or max_price is not None:
        price_match: dict[str, Any] = {}
        if min_price is not None:
            price_match["$gte"] = min_price
        if max_price is not None:
            price_match["$lte"] = max_price
        pipeline.insert(1, {"$match": {"base_price": price_match}})

    results = await db.hotels.aggregate(pipeline).to_list(limit)

    # Get total count for pagination
    count_pipeline = pipeline[:3]  # Up to filter stage
    count_pipeline.append({"$count": "total"})
    count_result = await db.hotels.aggregate(count_pipeline).to_list(1)
    total = count_result[0]["total"] if count_result else len(results)

    response = {
        "hotels": results,
        "total": total,
        "page": skip // limit if limit else 0,
        "limit": limit,
        "search_params": {
            "check_in": check_in,
            "check_out": check_out,
            "guests": guests,
        },
    }

    # Cache results
    await cache_set(cache_key, response, category="search_results")

    return response
