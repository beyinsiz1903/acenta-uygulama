from __future__ import annotations

from datetime import date
from typing import Any, Iterable, Optional

from bson import ObjectId

from app.errors import AppError
from app.repositories.base_repository import with_org_filter, with_tenant_filter


AGENCY_USER_ROLES = ("agency_admin", "agency_agent")

PAYMENT_STATUS_LABELS = {
    "paid": "Ödendi",
    "pending": "Bekliyor",
    "overdue": "Gecikmiş",
}

CONTRACT_STATUS_LABELS = {
    "active": "Aktif",
    "expiring_soon": "Süresi Doluyor",
    "expired": "Kısıtlı",
    "not_configured": "Tanımsız",
}


def _parse_contract_date(value: Any) -> Optional[date]:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    raw = str(value).strip()
    if not raw:
        return None
    return date.fromisoformat(raw[:10])


def _date_to_iso(value: Optional[date]) -> Optional[str]:
    return value.isoformat() if value else None


def build_agency_contract_summary(
    agency_doc: dict[str, Any],
    *,
    active_user_count: int = 0,
    today: Optional[date] = None,
) -> dict[str, Any]:
    today = today or date.today()

    start_date = _parse_contract_date(agency_doc.get("contract_start_date"))
    end_date = _parse_contract_date(agency_doc.get("contract_end_date"))
    payment_status = (agency_doc.get("payment_status") or "").strip().lower() or None
    package_type = (agency_doc.get("package_type") or "").strip() or None
    user_limit = agency_doc.get("user_limit")
    if user_limit in ("", None):
        user_limit = None
    elif isinstance(user_limit, bool):
        user_limit = None
    else:
        user_limit = int(user_limit)

    days_remaining: Optional[int] = None
    contract_status = "not_configured"
    warning_message: Optional[str] = None
    lock_message: Optional[str] = None
    access_blocked = False

    if end_date:
        days_remaining = (end_date - today).days
        if days_remaining < 0:
            contract_status = "expired"
            access_blocked = True
            lock_message = (
                f"Sözleşme süreniz {end_date.isoformat()} tarihinde sona erdi. "
                "Ödeme yenilenince erişim tekrar açılacaktır."
            )
        elif days_remaining <= 30:
            contract_status = "expiring_soon"
            warning_message = (
                f"Sözleşme süreniz {end_date.isoformat()} tarihinde doluyor. "
                "Bu tarihe kadar ödeme gelmezse erişim kısıtlanacaktır."
            )
        else:
            contract_status = "active"
    elif start_date or payment_status or package_type or user_limit is not None:
        contract_status = "active"

    remaining_user_slots = None if user_limit is None else max(user_limit - int(active_user_count or 0), 0)

    return {
        "contract_start_date": _date_to_iso(start_date),
        "contract_end_date": _date_to_iso(end_date),
        "payment_status": payment_status,
        "payment_status_label": PAYMENT_STATUS_LABELS.get(payment_status or "", "Tanımsız"),
        "package_type": package_type,
        "user_limit": user_limit,
        "active_user_count": int(active_user_count or 0),
        "remaining_user_slots": remaining_user_slots,
        "contract_status": contract_status,
        "contract_status_label": CONTRACT_STATUS_LABELS.get(contract_status, "Tanımsız"),
        "days_remaining": days_remaining,
        "warning_message": warning_message,
        "lock_message": lock_message,
        "access_blocked": access_blocked,
        "user_limit_reached": bool(user_limit is not None and remaining_user_slots == 0),
    }


async def get_agency_active_user_counts(
    db,
    *,
    organization_id: str,
    agency_ids: Iterable[Any],
    tenant_id: Optional[str] = None,
) -> dict[str, int]:
    agency_id_list = [agency_id for agency_id in agency_ids if agency_id not in (None, "")]
    if not agency_id_list:
        return {}

    query: dict[str, Any] = with_org_filter(
        {
            "agency_id": {"$in": agency_id_list},
            "roles": {"$in": list(AGENCY_USER_ROLES)},
            "is_active": {"$ne": False},
        },
        organization_id,
    )
    if tenant_id:
        query = with_tenant_filter(query, tenant_id, include_legacy_without_tenant=True)

    pipeline = [
        {"$match": query},
        {"$group": {"_id": "$agency_id", "count": {"$sum": 1}}},
    ]
    rows = await db.users.aggregate(pipeline).to_list(length=max(len(agency_id_list), 1) * 2)
    return {str(row.get("_id")): int(row.get("count") or 0) for row in rows}


def _exclude_user_filter(user_id: Any) -> dict[str, Any]:
    raw = str(user_id)
    try:
        oid = ObjectId(raw)
    except Exception:
        return {"$ne": raw}
    return {"$nin": [raw, oid]}


async def get_agency_active_user_count(
    db,
    *,
    organization_id: str,
    agency_id: Any,
    tenant_id: Optional[str] = None,
    exclude_user_id: Optional[Any] = None,
) -> int:
    query: dict[str, Any] = with_org_filter(
        {
            "agency_id": agency_id,
            "roles": {"$in": list(AGENCY_USER_ROLES)},
            "is_active": {"$ne": False},
        },
        organization_id,
    )
    if tenant_id:
        query = with_tenant_filter(query, tenant_id, include_legacy_without_tenant=True)
    if exclude_user_id is not None:
        query["_id"] = _exclude_user_filter(exclude_user_id)
    return await db.users.count_documents(query)


async def enforce_agency_user_limit(
    db,
    *,
    organization_id: str,
    agency_doc: dict[str, Any],
    tenant_id: Optional[str] = None,
    exclude_user_id: Optional[Any] = None,
    increment_by: int = 1,
) -> None:
    active_user_count = await get_agency_active_user_count(
        db,
        organization_id=organization_id,
        agency_id=agency_doc.get("_id"),
        tenant_id=tenant_id,
        exclude_user_id=exclude_user_id,
    )
    summary = build_agency_contract_summary(agency_doc, active_user_count=active_user_count)
    user_limit = summary.get("user_limit")
    if user_limit is None:
        return
    if active_user_count + max(int(increment_by or 0), 0) <= int(user_limit):
        return

    agency_name = agency_doc.get("name") or "Bu acenta"
    raise AppError(
        409,
        "agency_user_limit_reached",
        f"{agency_name} için kullanıcı limiti dolu. Yeni kullanıcı eklemeden önce limiti artırın.",
        details={
            "agency_id": str(agency_doc.get("_id") or ""),
            "agency_name": agency_name,
            "user_limit": int(user_limit),
            "active_user_count": int(active_user_count),
            "remaining_user_slots": summary.get("remaining_user_slots"),
        },
    )