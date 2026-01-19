from __future__ import annotations

from fastapi import APIRouter, Depends, BackgroundTasks, Request

from app.db import get_db
from app.security.deps_b2b import CurrentB2BUser, current_b2b_user
from app.services.crm_events import log_crm_event

router = APIRouter(prefix="/b2b", tags=["b2b-portal"])


async def _log_b2b_login_success(db, user: CurrentB2BUser):
    """Best-effort logging for B2B login success.

    Any exception here must not break the main /me response.
    """
    try:
        if user.organization_id:
            await log_crm_event(
                db,
                user.organization_id,
                entity_type="auth",
                entity_id=user.id,
                action="b2b.login.success",
                payload={"roles": user.roles},
                actor={"id": user.id, "roles": user.roles},
                source="b2b_portal",
            )
    except Exception:
        # Swallow all errors – logging is best-effort only
        pass


@router.get("/me")
async def b2b_me(
    request: Request,
    background: BackgroundTasks,
    user: CurrentB2BUser = Depends(current_b2b_user),
    db=Depends(get_db),
):
    """Return minimal identity + scope info for B2B users.

    - Only users with B2B-allowed roles can access (enforced by current_b2b_user)
    - Used by frontend B2BAuthGuard and login flows
    """

    # Fire-and-forget: log event in background so main response is not blocked
    background.add_task(_log_b2b_login_success, db, user)

    return {
        "user_id": user.id,
        "roles": user.roles,
        "organization_id": user.organization_id,
        "agency_id": user.agency_id,
    }


@router.get("/account/summary")
async def b2b_account_summary(user: CurrentB2BUser = Depends(current_b2b_user), db=Depends(get_db)):
    """Return read-only account summary for B2B agency user.

    MVP behaviour:
    - If a dedicated ledger / account collection exists, use it.
    - Otherwise, derive a simple summary from bookings for this agency.
    - Always returns 200 with zero/empty defaults when no data.
    """
    org_id = user.organization_id
    agency_id = user.agency_id
    if not org_id or not agency_id:
        # Should not happen for valid B2B users, but keep contract explicit
        from app.errors import AppError

        raise AppError(403, "forbidden", "Only agency users can view B2B account summary")

    # Defaults
    total_debit = 0.0
    total_credit = 0.0
    currency = "EUR"
    recent: list[dict] = []

    # ------------------------------------------------------------------
    # Strategy A: use ledger-backed finance data if available
    # ------------------------------------------------------------------
    # Try to locate finance account + credit profile + account balance
    credit_profile = await db.credit_profiles.find_one(
        {"organization_id": org_id, "agency_id": agency_id}
    )
    account = await db.finance_accounts.find_one(
        {"organization_id": org_id, "type": "agency", "owner_id": agency_id}
    )

    exposure_eur = 0.0
    credit_limit = None
    soft_limit = None
    payment_terms = None
    status = "ok"
    aging = {"age_0_30": 0.0, "age_31_60": 0.0, "age_61_plus": 0.0}

    if account:
        currency = account.get("currency", currency)
        balance = await db.account_balances.find_one(
            {
                "organization_id": org_id,
                "account_id": account["_id"],
                "currency": currency,
            }
        )
        exposure_eur = float(balance.get("balance", 0.0)) if balance else 0.0

    if credit_profile:
        credit_limit = float(credit_profile.get("limit") or 0.0)
        soft_limit = credit_profile.get("soft_limit")
        payment_terms = credit_profile.get("payment_terms") or None

        # Status hesaplama (ops_finance.exposure ile aynı mantık)
        if credit_limit and exposure_eur >= credit_limit:
            status = "over_limit"
        elif soft_limit and exposure_eur >= soft_limit:
            status = "near_limit"

    # Optional: basic aging approximation from ledger_entries (same pattern as exposure dashboard)
    from datetime import datetime, timedelta

    now = datetime.utcnow()
    thirty_days_ago = now - timedelta(days=30)
    sixty_days_ago = now - timedelta(days=60)

    if account:
        cursor_le = db.ledger_entries.find(
            {
                "organization_id": org_id,
                "account_id": account["_id"],
                "currency": currency,
            }
        )
        entries = await cursor_le.to_list(length=1000)
        for le in entries:
            posted_at = le.get("posted_at")
            if not isinstance(posted_at, datetime):
                continue
            amount = float(le.get("amount") or 0.0)
            direction = (le.get("direction") or "").lower()
            if direction == "credit":
                amount = -amount

            if posted_at >= thirty_days_ago:
                aging["age_0_30"] += amount
            elif posted_at >= sixty_days_ago:
                aging["age_31_60"] += amount
            else:
                aging["age_61_plus"] += amount

    # ------------------------------------------------------------------
    # Strategy B: fallback to bookings-derived summary when no ledger data
    # ------------------------------------------------------------------
    if not account and not credit_profile:
        from datetime import datetime

        cursor = (
            db.bookings.find(
                {
                    "organization_id": org_id,
                    "agency_id": agency_id,
                }
            )
            .sort("created_at", -1)
            .limit(50)
        )
        docs = await cursor.to_list(length=50)

        for doc in docs:
            amounts = doc.get("amounts") or {}
            sell = float(amounts.get("sell") or 0.0)
            cur = doc.get("currency") or currency
            currency = cur or currency

            status_b = (doc.get("status") or "").upper()
            pay_status = (doc.get("payment_status") or "").lower()

            # Treat CONFIRMED + unpaid/partial bookings as debit exposure
            direction = None
            if status_b == "CONFIRMED" and pay_status in {"unpaid", "partial", ""} and sell > 0:
                direction = "debit"
                total_debit += sell

            created_at = doc.get("created_at")
            if isinstance(created_at, datetime):
                dt = created_at.isoformat()
            else:
                dt = str(created_at) if created_at else None

            if direction:
                recent.append(
                    {
                        "id": str(doc.get("_id")),
                        "date": dt,
                        "type": "booking",
                        "description": doc.get("booking_code")
                        or f"Booking {str(doc.get('_id'))[:8]}",
                        "direction": direction,
                        "amount": sell,
                        "currency": cur,
                        "ref_id": str(doc.get("_id")),
                    }
                )

        recent = recent[:20]
        net = total_credit - total_debit
        data_source = "derived_from_bookings"
    else:
        # When ledger-backed data is available, keep recent movements empty for now
        net = -exposure_eur
        data_source = "ledger_based"

    return {
        "total_debit": round(total_debit, 2),
        "total_credit": round(total_credit, 2),
        "net": round(net, 2),
        "currency": currency,
        "recent": recent,
        "data_source": data_source,
        "exposure_eur": round(exposure_eur, 2),
        "credit_limit": credit_limit,
        "soft_limit": soft_limit,
        "payment_terms": payment_terms,
        "status": status,
        "aging": aging,
    }

