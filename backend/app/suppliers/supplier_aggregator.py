"""Supplier Aggregator — Unified search across all connected suppliers.

Fans out search requests to all suppliers with active credentials,
normalizes results into a unified product model, and returns
combined results sorted by price.

Architecture:
  Search Request -> Aggregator -> [RateHawk, TBO, Paximum, WWTatil]
                                         |
                                  Unified Product List
                                  (price comparison, fallback, inventory merge)
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

logger = logging.getLogger("suppliers.aggregator")

# Map supplier codes to adapter classes
ADAPTER_MAP = {
    "ratehawk": ("app.suppliers.adapters.ratehawk_adapter", "RateHawkAdapter"),
    "tbo": ("app.suppliers.adapters.tbo_adapter", "TBOAdapter"),
    "paximum": ("app.suppliers.adapters.paximum_adapter", "PaximumAdapter"),
    "wwtatil": ("app.suppliers.adapters.wwtatil_adapter", "WWTatilAdapter"),
}

# Supplier capability matrix
SUPPLIER_CAPABILITIES = {
    "ratehawk": {"hotel"},
    "tbo": {"hotel", "flight", "tour"},
    "paximum": {"hotel", "transfer", "activity"},
    "wwtatil": {"tour"},
}


def _get_adapter_class(supplier: str):
    """Dynamically import adapter class."""
    if supplier not in ADAPTER_MAP:
        return None
    module_path, class_name = ADAPTER_MAP[supplier]
    import importlib
    mod = importlib.import_module(module_path)
    return getattr(mod, class_name)


async def _get_connected_suppliers(db, organization_id: str) -> list[dict]:
    """Get all suppliers with saved/connected credentials for an agency."""
    from app.domain.suppliers.supplier_credentials_service import get_decrypted_credentials
    connected = []
    for supplier_code in ADAPTER_MAP:
        creds = await get_decrypted_credentials(db, organization_id, supplier_code)
        if creds:
            connected.append({"supplier": supplier_code, "credentials": creds})
    return connected


async def _create_authenticated_adapter(db, organization_id: str, supplier_code: str, creds: dict):
    """Create and authenticate an adapter instance."""
    from app.domain.suppliers.supplier_credentials_service import get_cached_token

    AdapterClass = _get_adapter_class(supplier_code)
    if not AdapterClass:
        return None

    base_url = creds.get("base_url", "")
    if not base_url:
        return None

    # Try cached token first
    token = await get_cached_token(db, organization_id, supplier_code)
    adapter = AdapterClass(base_url, token)

    if not token:
        auth_result = await adapter.authenticate(creds)
        if not auth_result.get("success"):
            logger.warning(f"Auth failed for {supplier_code}: {auth_result.get('error')}")
            return None
        # Update token on adapter
        token = auth_result.get("token", "")
        adapter.token = token
        # Cache token
        from app.domain.suppliers.supplier_credentials_service import _ts
        await db["supplier_tokens"].update_one(
            {"organization_id": organization_id, "supplier": supplier_code},
            {"$set": {"token": token, "obtained_at": _ts(), "expires_hours": 24}},
            upsert=True,
        )

    return adapter


async def _search_single_supplier(
    adapter, supplier_code: str, product_type: str, request: dict
) -> dict[str, Any]:
    """Execute search on a single supplier."""
    start = time.monotonic()
    try:
        method_map = {
            "hotel": adapter.search_hotels,
            "tour": adapter.search_tours,
            "flight": adapter.search_flights,
            "transfer": adapter.search_transfers,
            "activity": adapter.search_activities,
        }
        method = method_map.get(product_type)
        if not method:
            return {"supplier": supplier_code, "products": [], "error": f"No {product_type} method"}

        result = await method(request)
        latency_ms = round((time.monotonic() - start) * 1000, 1)
        return {
            "supplier": supplier_code,
            "products": result.get("products", []),
            "total": result.get("total", 0),
            "success": result.get("success", False),
            "latency_ms": latency_ms,
            "error": result.get("error"),
        }
    except Exception as e:
        latency_ms = round((time.monotonic() - start) * 1000, 1)
        logger.error(f"Aggregator search error for {supplier_code}: {e}", exc_info=True)
        return {"supplier": supplier_code, "products": [], "error": str(e), "latency_ms": latency_ms}


async def aggregated_search(
    db,
    organization_id: str,
    product_type: str,
    request: dict,
    suppliers: list[str] | None = None,
) -> dict[str, Any]:
    """Fan-out search to all connected suppliers that support the product type.

    Args:
        db: MongoDB database instance
        organization_id: Agency tenant ID
        product_type: "hotel", "tour", "flight", "transfer", "activity"
        request: Search parameters (dates, destination, guests, etc.)
        suppliers: Optional list of specific suppliers to search. If None, search all connected.

    Returns:
        Unified response with products from all suppliers, sorted by price.
    """
    start = time.monotonic()
    connected = await _get_connected_suppliers(db, organization_id)

    if not connected:
        return {
            "products": [],
            "total": 0,
            "suppliers_searched": [],
            "error": "No connected suppliers found. Configure credentials in Supplier Settings.",
        }

    # Filter to suppliers that support the product type
    eligible = []
    for s in connected:
        code = s["supplier"]
        if suppliers and code not in suppliers:
            continue
        if product_type in SUPPLIER_CAPABILITIES.get(code, set()):
            eligible.append(s)

    if not eligible:
        return {
            "products": [],
            "total": 0,
            "suppliers_searched": [],
            "message": f"No connected suppliers support '{product_type}'. "
                       f"Capable suppliers: {[k for k, v in SUPPLIER_CAPABILITIES.items() if product_type in v]}",
        }

    # Create adapters
    tasks = []
    supplier_names = []
    for s in eligible:
        adapter = await _create_authenticated_adapter(db, organization_id, s["supplier"], s["credentials"])
        if adapter:
            tasks.append(_search_single_supplier(adapter, s["supplier"], product_type, request))
            supplier_names.append(s["supplier"])

    if not tasks:
        return {
            "products": [],
            "total": 0,
            "suppliers_searched": [],
            "error": "Authentication failed for all eligible suppliers.",
        }

    # Fan-out parallel search
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Merge results
    all_products = []
    supplier_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            supplier_results.append({
                "supplier": supplier_names[i],
                "success": False,
                "error": str(result),
                "product_count": 0,
            })
            continue
        products = result.get("products", [])
        all_products.extend(products)
        supplier_results.append({
            "supplier": result.get("supplier", supplier_names[i]),
            "success": result.get("success", False),
            "product_count": len(products),
            "latency_ms": result.get("latency_ms", 0),
            "error": result.get("error"),
        })

    # Sort by price (ascending)
    all_products.sort(key=lambda p: float(p.get("price", 0) or 0))

    total_latency = round((time.monotonic() - start) * 1000, 1)

    return {
        "products": all_products,
        "total": len(all_products),
        "product_type": product_type,
        "suppliers_searched": supplier_results,
        "total_latency_ms": total_latency,
        "organization_id": organization_id,
    }


async def get_supplier_capabilities(db, organization_id: str) -> dict[str, Any]:
    """Get a matrix of what each connected supplier supports."""
    connected = await _get_connected_suppliers(db, organization_id)
    connected_codes = {s["supplier"] for s in connected}

    matrix = []
    for code, capabilities in SUPPLIER_CAPABILITIES.items():
        matrix.append({
            "supplier": code,
            "connected": code in connected_codes,
            "capabilities": sorted(capabilities),
        })

    # Aggregate by product type
    product_coverage = {}
    for code, caps in SUPPLIER_CAPABILITIES.items():
        for cap in caps:
            if cap not in product_coverage:
                product_coverage[cap] = {"total": 0, "connected": 0, "suppliers": []}
            product_coverage[cap]["total"] += 1
            if code in connected_codes:
                product_coverage[cap]["connected"] += 1
            product_coverage[cap]["suppliers"].append({"code": code, "connected": code in connected_codes})

    return {
        "suppliers": matrix,
        "product_coverage": product_coverage,
        "total_connected": len(connected_codes),
        "total_available": len(SUPPLIER_CAPABILITIES),
    }
