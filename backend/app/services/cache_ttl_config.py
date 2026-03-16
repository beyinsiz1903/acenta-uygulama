"""Centralized TTL Configuration for Cache Layers.

Domain-driven TTL management with supplier-specific overrides.

TTL Philosophy:
  - search_results:   SHORT   (60-120s)  — prices change frequently
  - hotel_details:    MEDIUM  (300-600s)  — semi-static content
  - static_metadata:  LONG    (1800-3600s) — rarely changes
  - supplier_inventory: JOB-BASED — tied to sync job frequency

Each category has L1 (Redis) and L2 (MongoDB) TTLs.
L1 is always shorter than L2 for freshness.
"""
from __future__ import annotations

from typing import Any


# ── Default TTL Matrix (seconds) ──────────────────────────────────────

TTL_MATRIX: dict[str, dict[str, int]] = {
    # Search & pricing — volatile, short-lived
    "search_results": {"redis": 60, "mongo": 180},
    "price_revalidation": {"redis": 30, "mongo": 90},
    "availability_check": {"redis": 45, "mongo": 120},

    # Hotel & product details — semi-static
    "hotel_detail": {"redis": 300, "mongo": 900},
    "product_detail": {"redis": 300, "mongo": 900},
    "room_types": {"redis": 300, "mongo": 600},

    # Static metadata — rarely changes
    "supplier_registry": {"redis": 1800, "mongo": 3600},
    "cms_pages": {"redis": 600, "mongo": 1800},
    "tenant_features": {"redis": 300, "mongo": 900},
    "fx_rates": {"redis": 600, "mongo": 1800},
    "pricing_rules": {"redis": 300, "mongo": 900},

    # Supplier inventory — tied to sync jobs
    "supplier_inventory": {"redis": 600, "mongo": 1800},
    "supplier_city_index": {"redis": 600, "mongo": 1800},

    # Dashboard & analytics
    "dashboard_kpi": {"redis": 120, "mongo": 300},
    "dashboard_charts": {"redis": 180, "mongo": 600},
    "agency_list": {"redis": 300, "mongo": 900},

    # Booking lifecycle — very short
    "booking_status": {"redis": 15, "mongo": 60},
    "booking_precheck": {"redis": 10, "mongo": 30},

    # System
    "health_check": {"redis": 30, "mongo": 60},
    "warmup_data": {"redis": 300, "mongo": 600},
}

# ── Supplier-Specific Overrides ───────────────────────────────────────

SUPPLIER_TTL_OVERRIDES: dict[str, dict[str, dict[str, int]]] = {
    "ratehawk": {
        "search_results": {"redis": 90, "mongo": 240},
        "supplier_inventory": {"redis": 600, "mongo": 1800},
    },
    "paximum": {
        "search_results": {"redis": 120, "mongo": 300},
        "supplier_inventory": {"redis": 900, "mongo": 2700},
    },
    "tbo": {
        "search_results": {"redis": 60, "mongo": 180},
        "supplier_inventory": {"redis": 600, "mongo": 1800},
    },
    "wtatil": {
        "search_results": {"redis": 180, "mongo": 600},
        "supplier_inventory": {"redis": 1200, "mongo": 3600},
    },
    "hotelbeds": {
        "search_results": {"redis": 90, "mongo": 240},
        "supplier_inventory": {"redis": 600, "mongo": 1800},
    },
    "juniper": {
        "search_results": {"redis": 120, "mongo": 300},
        "supplier_inventory": {"redis": 900, "mongo": 2700},
    },
}


# ── Public API ────────────────────────────────────────────────────────

def get_ttl(category: str, layer: str = "redis", supplier: str | None = None) -> int:
    """Get TTL in seconds for a cache category and layer.

    Args:
        category: Cache category key (e.g. 'search_results', 'hotel_detail')
        layer: 'redis' or 'mongo'
        supplier: Optional supplier code for supplier-specific overrides

    Returns:
        TTL in seconds
    """
    if supplier and supplier in SUPPLIER_TTL_OVERRIDES:
        override = SUPPLIER_TTL_OVERRIDES[supplier].get(category)
        if override:
            return override.get(layer, override.get("redis", 300))

    default = TTL_MATRIX.get(category, TTL_MATRIX.get("warmup_data", {"redis": 300, "mongo": 600}))
    return default.get(layer, 300)


def get_ttl_pair(category: str, supplier: str | None = None) -> tuple[int, int]:
    """Get both Redis and Mongo TTLs as a tuple.

    Returns:
        (redis_ttl, mongo_ttl)
    """
    return get_ttl(category, "redis", supplier), get_ttl(category, "mongo", supplier)


def get_freshness_threshold(category: str) -> int:
    """Get the freshness threshold — data older than this is considered stale.

    Uses the Redis TTL as the freshness boundary.
    """
    return get_ttl(category, "redis")


def get_full_config() -> dict[str, Any]:
    """Return the full TTL configuration for diagnostics."""
    return {
        "default_matrix": TTL_MATRIX,
        "supplier_overrides": SUPPLIER_TTL_OVERRIDES,
    }
