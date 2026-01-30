from __future__ import annotations

from typing import Any, Dict

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.risk_rule_repository import RiskRuleRepository
from app.services.audit import write_audit_log

# For Sprint 2 P1 we hard-code a single high-amount rule; configuration will
# be expanded in later phases. Threshold in TRY.
_AMOUNT_THRESHOLD = 100_000.0


async def evaluate_booking_risk(
    db: AsyncIOMotorDatabase,
    organization_id: str,
    booking: Dict[str, Any],
    actor: Dict[str, Any],
    request: Any,
) -> None:
    """Evaluate simple risk rules for a booking and emit audit events.

    P1 contract:
    - If booking.amount > THRESHOLD, emit RISK_ALERT_CREATED with meta
      {"rule": "amount_threshold", "threshold": THRESHOLD, "amount": amount}.
    - Otherwise do nothing.
    - Org scoping is enforced via organization_id and existing audit infra.
    """

    # Ensure default risk rules exist for the org (idempotent)
    repo = RiskRuleRepository(db)
    await repo.ensure_default_rules(organization_id, actor.get("email"))

    amount = float(booking.get("amount", 0.0))
    if amount <= _AMOUNT_THRESHOLD:
        return

    await write_audit_log(
        db,
        organization_id=organization_id,
        actor=actor,
        request=request,
        action="RISK_ALERT_CREATED",
        target_type="booking",
        target_id=booking.get("id") or booking.get("_id"),
        before=None,
        after=None,
        meta={
            "rule": "amount_threshold",
            "threshold": _AMOUNT_THRESHOLD,
            "amount": amount,
        },
    )
