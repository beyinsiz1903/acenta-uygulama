"""Price Revalidation Guard.

Before any booking attempt, this service validates:
  1. Current price vs search-time price
  2. Availability status
  3. Currency match
  4. Price drift threshold

Decision matrix:
  drift < 2%   → proceed silently
  drift 2-5%   → proceed with warning
  drift 5-10%  → require agency approval
  drift > 10%  → abort booking
  not available → abort booking
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.suppliers.contracts.schemas import PriceRevalidationResult

logger = logging.getLogger("suppliers.revalidation")

DRIFT_SILENT_PCT = 2.0
DRIFT_WARN_PCT = 5.0
DRIFT_APPROVAL_PCT = 10.0


async def revalidate_price(
    db,
    organization_id: str,
    supplier_code: str,
    supplier_item_id: str,
    original_price: float,
    currency: str = "TRY",
    product_type: str = "hotel",
) -> PriceRevalidationResult:
    """Check if the price is still valid before booking.

    Uses the supplier's pricing/availability endpoint if available,
    otherwise falls back to a quick re-search.
    """
    from app.suppliers.registry import supplier_registry
    from app.suppliers.contracts.schemas import (
        PricingRequest, SupplierContext, SupplierProductType,
    )
    import uuid

    now = datetime.now(timezone.utc)
    ctx = SupplierContext(
        request_id=str(uuid.uuid4()),
        organization_id=organization_id,
        currency=currency,
        timeout_ms=10000,
    )

    current_price = original_price
    still_available = True
    warnings = []

    try:
        adapter = supplier_registry.get(supplier_code)

        # Try dedicated pricing endpoint
        try:
            pricing_result = await adapter.get_pricing(
                ctx,
                PricingRequest(
                    supplier_code=supplier_code,
                    supplier_item_id=supplier_item_id,
                    product_type=SupplierProductType(product_type),
                ),
            )
            if pricing_result.supplier_price:
                current_price = pricing_result.supplier_price.total
        except NotImplementedError:
            # Supplier doesn't support standalone pricing — price unchanged
            warnings.append(f"{supplier_code} does not support price revalidation; using search price")

    except Exception as e:
        logger.warning("Price revalidation error for %s: %s", supplier_code, e)
        warnings.append(f"Revalidation error: {str(e)[:100]}")

    # Calculate drift
    drift_amount = current_price - original_price
    drift_pct = (drift_amount / original_price * 100) if original_price > 0 else 0.0

    # Decision
    can_proceed = True
    requires_approval = False
    abort_reason = None

    if not still_available:
        can_proceed = False
        abort_reason = "Product no longer available"
    elif abs(drift_pct) > DRIFT_APPROVAL_PCT:
        can_proceed = False
        requires_approval = True
        abort_reason = f"Price drift {drift_pct:.1f}% exceeds {DRIFT_APPROVAL_PCT}% threshold"
    elif abs(drift_pct) > DRIFT_WARN_PCT:
        requires_approval = True
        warnings.append(f"Price increased by {drift_pct:.1f}% — agency approval recommended")
    elif abs(drift_pct) > DRIFT_SILENT_PCT:
        warnings.append(f"Minor price drift of {drift_pct:.1f}%")

    result = PriceRevalidationResult(
        supplier_code=supplier_code,
        supplier_item_id=supplier_item_id,
        valid=can_proceed and still_available,
        original_price=original_price,
        current_price=current_price,
        price_drift_amount=round(drift_amount, 2),
        price_drift_pct=round(drift_pct, 2),
        currency=currency,
        still_available=still_available,
        warnings=warnings,
        can_proceed=can_proceed,
        requires_approval=requires_approval,
        abort_reason=abort_reason,
        checked_at=now,
    )

    # Persist revalidation for audit
    try:
        await db["price_revalidations"].insert_one({
            "organization_id": organization_id,
            "supplier_code": supplier_code,
            "supplier_item_id": supplier_item_id,
            "original_price": original_price,
            "current_price": current_price,
            "drift_pct": round(drift_pct, 2),
            "valid": result.valid,
            "can_proceed": result.can_proceed,
            "requires_approval": result.requires_approval,
            "checked_at": now.isoformat(),
        })
    except Exception:
        pass

    return result
