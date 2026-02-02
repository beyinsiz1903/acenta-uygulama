from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, List

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.booking_repository import BookingRepository
from app.services.credit_exposure_service import _get_credit_limit, _calculate_exposure


class RiskDecision(str, Enum):
    ALLOW = "allow"
    REVIEW = "review"
    BLOCK = "block"


@dataclass
class RiskResult:
    score: float
    decision: RiskDecision
    reasons: List[str]
    model_version: str = "risk_v1"


async def _get_tenant_booking_count(db: AsyncIOMotorDatabase, organization_id: str, tenant_id: str | None) -> int:
    """Return count of bookings for a given tenant.

    v1: simple count over all time; if tenant_id is missing, returns 0.
    """

    if not tenant_id:
        return 0

    repo = BookingRepository(db)
    flt: dict[str, Any] = {"offer_ref.buyer_tenant_id": tenant_id}
    # we intentionally do not filter by state to keep definition simple
    col = repo._col  # internal but stable within this codebase
    return await col.count_documents({"organization_id": organization_id, **flt})


async def _has_pricing_mismatch_audit(
    db: AsyncIOMotorDatabase,
    organization_id: str,
    booking_id: str,
) -> bool:
    """Detect if PRICING_MISMATCH_DETECTED audit exists for this booking.

    Best-effort: any error reading audit logs should be treated as no-mismatch
    so that risk engine never breaks confirm flow.
    """

    try:
        doc = await db.audit_logs.find_one(
            {
                "organization_id": organization_id,
                "action": "PRICING_MISMATCH_DETECTED",
                "meta.booking_id": booking_id,
            }
        )
        return doc is not None
    except Exception:
        return False


async def evaluate_booking_risk(
    db: AsyncIOMotorDatabase,
    organization_id: str,
    booking: dict,
) -> RiskResult:
    """Deterministic v1 risk scoring for a single booking.

    Inputs:
    - booking.amount
    - booking.pricing.applied_markup_pct
    - org credit profile & current exposure
    - tenant historical booking count
    - pricing mismatch flag (via audit logs)
    """

    score = 0.0
    reasons: list[str] = []

    # Base signals
    amount = float(booking.get("amount") or 0.0)
    pricing = booking.get("pricing") or {}
    applied_markup_pct = float(pricing.get("applied_markup_pct") or 0.0)

    offer_ref = booking.get("offer_ref") or {}
    buyer_tenant_id = offer_ref.get("buyer_tenant_id") or None
    booking_id = str(booking.get("_id") or "")

    # Amount-based rules
    if amount > 50_000:
        score += 30.0
        reasons.append("high_amount_>50000")
    elif amount > 20_000:
        score += 15.0
        reasons.append("medium_amount_>20000")

    # Markup-based rule
    if applied_markup_pct > 25.0:
        score += 10.0
        reasons.append("high_markup_>25pct")

    # Credit utilization rule
    try:
        limit = await _get_credit_limit(db, organization_id)
        if limit is not None and limit > 0:
            exposure = await _calculate_exposure(db, organization_id)
            utilization = ((exposure + amount) / float(limit)) * 100.0
            if utilization > 80.0:
                score += 25.0
                reasons.append("high_utilization_>80pct")
    except Exception:
        # fail-open: if credit lookups fail, skip utilization signal
        pass

    # Mismatch rule
    mismatch = await _has_pricing_mismatch_audit(db, organization_id, booking_id)
    if mismatch:
        score += 20.0
        reasons.append("pricing_mismatch_detected")

    # Tenant history rule
    try:
        tenant_count = await _get_tenant_booking_count(db, organization_id, buyer_tenant_id)
        if tenant_count < 3:
            score += 10.0
            reasons.append("low_tenant_history_<3_bookings")
    except Exception:
        # If count fails, treat as neutral
        pass

    # Clamp score
    if score < 0:
        score = 0.0
    if score > 100:
        score = 100.0

    # Decision thresholds
    if score < 40.0:
        decision = RiskDecision.ALLOW
    elif score < 70.0:
        decision = RiskDecision.REVIEW
    else:
        decision = RiskDecision.BLOCK

    return RiskResult(score=score, decision=decision, reasons=list(reasons))
