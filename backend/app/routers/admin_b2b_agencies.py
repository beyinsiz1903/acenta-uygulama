from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.utils import serialize_doc

router = APIRouter(prefix="/api/admin/b2b/agencies", tags=["admin_b2b_agencies"])


AdminDep = Depends(require_roles(["super_admin"]))


async def _list_agency_summaries(db, org_id: str, limit: int = 200) -> List[Dict[str, Any]]:
    """Join agencies with finance_accounts, account_balances and credit_profiles.

    Simplified, read-only view for admin dashboard.
    """
    agencies = await db.agencies.find({"organization_id": org_id}).sort("created_at", -1).limit(limit).to_list(limit)

    if not agencies:
        return []

    agency_ids = [a["_id"] for a in agencies]

    # Finance accounts (type=agency)
    accounts = await db.finance_accounts.find(
        {"organization_id": org_id, "type": "agency", "owner_id": {"$in": agency_ids}}
    ).to_list(len(agency_ids))
    account_by_owner: Dict[str, Dict[str, Any]] = {acc["owner_id"]: acc for acc in accounts}

    # Balances (EUR only for now)
    account_ids = [acc["_id"] for acc in accounts]
    balances = await db.account_balances.find(
        {"organization_id": org_id, "account_id": {"$in": account_ids}, "currency": "EUR"}
    ).to_list(len(account_ids))
    balance_by_account: Dict[str, Dict[str, Any]] = {b["account_id"]: b for b in balances}

    # Credit profiles
    profiles = await db.credit_profiles.find({"organization_id": org_id, "agency_id": {"$in": agency_ids}}).to_list(
        len(agency_ids)
    )
    profile_by_agency: Dict[str, Dict[str, Any]] = {p["agency_id"]: p for p in profiles}

    items: List[Dict[str, Any]] = []

    for agency in agencies:
        aid = agency["_id"]
        account = account_by_owner.get(aid)
        profile = profile_by_agency.get(aid)

        currency = "EUR"
        exposure = 0.0
        credit_limit: Optional[float] = None
        soft_limit: Optional[float] = None
        payment_terms: Optional[str] = None

        if account:
            currency = account.get("currency", currency) or currency
            bal = balance_by_account.get(account["_id"])
            if bal is not None:
                exposure = float(bal.get("balance") or 0.0)

        if profile:
            credit_limit = float(profile.get("limit") or 0.0)
            soft_limit = profile.get("soft_limit")
            payment_terms = profile.get("payment_terms")

        if credit_limit is not None and exposure >= credit_limit:
            risk_status = "over_limit"
        elif soft_limit is not None and exposure >= soft_limit:
            risk_status = "near_limit"
        else:
            risk_status = "ok"

        parent_id = agency.get("parent_agency_id")

        items.append(
            {
                "id": str(aid),
                "organization_id": org_id,
                "name": agency.get("name"),
                "status": agency.get("status", "active"),
                "parent_agency_id": str(parent_id) if parent_id else None,
                "currency": currency,
                "exposure": round(exposure, 2),
                "credit_limit": round(credit_limit, 2) if credit_limit is not None else None,
                "soft_limit": round(soft_limit, 2) if soft_limit is not None else None,
                "payment_terms": payment_terms,
                "risk_status": risk_status,
                "created_at": agency.get("created_at"),
                "updated_at": agency.get("updated_at"),
            }
        )

    return items


@router.get("/summary", dependencies=[AdminDep])
async def list_b2b_agency_summaries(user=Depends(get_current_user), db=Depends(get_db)) -> Dict[str, Any]:
    org_id = user["organization_id"]
    items = await _list_agency_summaries(db, org_id)
    # serialize_doc ensures ObjectId and dates are json-friendly where needed
    return {"items": [serialize_doc(it) for it in items]}
