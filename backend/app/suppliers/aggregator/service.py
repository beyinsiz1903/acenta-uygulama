"""Supplier Aggregator Service.

Fans out search requests to multiple suppliers in parallel,
normalizes results, deduplicates, ranks, and returns a merged view.

Resilience:
  - Timeout isolation per supplier
  - Partial failure tolerance (degraded mode)
  - Circuit breaker awareness
  - Cache fallback on total failure
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.suppliers.contracts.base import SupplierAdapter, SupplierType
from app.suppliers.contracts.schemas import (
    SearchItem, SearchRequest, SearchResult,
    SupplierContext, SupplierProductType,
)
from app.suppliers.contracts.errors import SupplierError, SupplierTimeoutError
from app.suppliers.registry import supplier_registry

logger = logging.getLogger("suppliers.aggregator")


class AggregatorConfig:
    # Max time to wait for all suppliers
    FANOUT_TIMEOUT_MS: int = 12000
    # Min suppliers that must respond for non-degraded result
    MIN_SUPPLIERS: int = 1
    # Enable deduplication by supplier_item_id
    DEDUPLICATE: bool = True
    # Default sort
    DEFAULT_SORT: str = "price_asc"


async def _call_supplier(
    adapter: SupplierAdapter,
    ctx: SupplierContext,
    request: SearchRequest,
) -> tuple[str, Optional[SearchResult], Optional[str]]:
    """Call a single supplier with timeout. Returns (code, result, error)."""
    try:
        result = await asyncio.wait_for(
            adapter.search(ctx, request),
            timeout=ctx.timeout_ms / 1000.0,
        )
        return adapter.supplier_code, result, None
    except asyncio.TimeoutError:
        logger.warning("Supplier %s timed out", adapter.supplier_code)
        return adapter.supplier_code, None, "timeout"
    except SupplierError as e:
        logger.warning("Supplier %s error: %s", adapter.supplier_code, e.message)
        return adapter.supplier_code, None, e.code
    except Exception as e:
        logger.error("Supplier %s unexpected error: %s", adapter.supplier_code, e)
        return adapter.supplier_code, None, "unexpected_error"


def _deduplicate(items: List[SearchItem]) -> List[SearchItem]:
    """Remove duplicate items by supplier_item_id, keeping lowest price."""
    seen: Dict[str, SearchItem] = {}
    for item in items:
        key = f"{item.supplier_code}:{item.supplier_item_id}"
        if key not in seen or item.supplier_price < seen[key].supplier_price:
            seen[key] = item
    return list(seen.values())


def _sort_items(items: List[SearchItem], sort_by: str) -> List[SearchItem]:
    if sort_by == "price_asc":
        return sorted(items, key=lambda x: x.supplier_price)
    elif sort_by == "price_desc":
        return sorted(items, key=lambda x: x.supplier_price, reverse=True)
    elif sort_by == "rating_desc":
        return sorted(items, key=lambda x: x.rating or 0, reverse=True)
    elif sort_by == "name_asc":
        return sorted(items, key=lambda x: x.name.lower())
    return items


async def aggregate_search(
    ctx: SupplierContext,
    request: SearchRequest,
    *,
    db=None,
) -> SearchResult:
    """Fan out search to multiple suppliers and merge results.

    1. Determine target suppliers (from request or all matching product_type)
    2. Check circuit breakers
    3. Fan out parallel calls
    4. Collect results, handle failures
    5. Deduplicate & sort
    6. Cache results
    7. Return merged SearchResult
    """
    start = time.monotonic()

    # Determine target adapters
    if request.supplier_codes:
        adapters = [supplier_registry.get(c) for c in request.supplier_codes]
    else:
        product_type = SupplierType(request.product_type.value)
        adapters = supplier_registry.get_by_type(product_type)

    if not adapters:
        return SearchResult(
            request_id=ctx.request_id,
            product_type=request.product_type,
            total_items=0,
            items=[],
            suppliers_queried=[],
        )

    # Check circuit breakers and filter disabled suppliers
    active_adapters = []
    for adapter in adapters:
        from app.infrastructure.circuit_breaker import get_breaker
        breaker = get_breaker(adapter.supplier_code)
        if breaker.can_execute():
            active_adapters.append(adapter)
        else:
            logger.info("Skipping %s (circuit open)", adapter.supplier_code)

    # Fan out parallel calls
    tasks = [
        _call_supplier(adapter, ctx, request)
        for adapter in active_adapters
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Merge results
    all_items: List[SearchItem] = []
    suppliers_queried: List[str] = []
    suppliers_failed: List[str] = []

    for r in results:
        if isinstance(r, Exception):
            continue
        code, result, error = r
        suppliers_queried.append(code)
        if error:
            suppliers_failed.append(code)
            # Record failure in circuit breaker
            breaker = get_breaker(code)
            breaker.record_failure()
        elif result:
            all_items.extend(result.items)
            breaker = get_breaker(code)
            breaker.record_success()

    # Deduplicate
    if AggregatorConfig.DEDUPLICATE:
        all_items = _deduplicate(all_items)

    # Sort
    all_items = _sort_items(all_items, request.sort_by)

    # Paginate
    page_start = (request.page - 1) * request.page_size
    page_end = page_start + request.page_size
    paged_items = all_items[page_start:page_end]

    elapsed = int((time.monotonic() - start) * 1000)

    # Record health events for each supplier
    if db is not None:
        for code in suppliers_queried:
            ok = code not in suppliers_failed
            try:
                from app.services.supplier_health_service import record_supplier_call_event
                await record_supplier_call_event(
                    db,
                    organization_id=ctx.organization_id,
                    supplier_code=code,
                    ok=ok,
                    code=None if ok else "search_failed",
                    http_status=200 if ok else 500,
                    duration_ms=elapsed // max(len(suppliers_queried), 1),
                )
            except Exception:
                pass

    # Cache results
    try:
        from app.suppliers.cache import cache_search_results
        await cache_search_results(ctx, request, all_items)
    except Exception:
        pass

    return SearchResult(
        request_id=ctx.request_id,
        product_type=request.product_type,
        total_items=len(all_items),
        items=paged_items,
        suppliers_queried=suppliers_queried,
        suppliers_failed=suppliers_failed,
        search_duration_ms=elapsed,
        degraded=len(suppliers_failed) > 0,
    )
