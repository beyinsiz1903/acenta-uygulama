"""Finance Accounts Router — Decomposed from ops_finance.py.

Handles: finance account CRUD, credit profiles, account statements, exposure.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from typing import Literal, Optional, Any
from datetime import datetime
from bson import ObjectId

from app.db import get_db
from app.auth import require_roles
from app.errors import AppError
from app.utils import now_utc
from app.services.audit import write_audit_log, audit_snapshot
from app.schemas_finance import (
    FinanceAccount,
    FinanceAccountCreate,
    FinanceAccountListResponse,
    CreditProfile,
    CreditProfileUpdate,
    CreditProfileListResponse,
    AccountStatement,
    StatementItem,
    ExposureResponse,
    ExposureItem,
    Payment,
    PaymentCreate,
)

router = APIRouter(prefix="/api/ops/finance", tags=["ops_finance_accounts"])


# ============================================================================
# Helper functions
# ============================================================================

async def _list_accounts(db, org_id, type_filter=None, owner_id=None, limit=50):
    query = {"organization_id": org_id}
    if type_filter:
        query["type"] = type_filter
    if owner_id:
        query["owner_id"] = owner_id
    cursor = db.finance_accounts.find(query).sort("created_at", -1).limit(limit)
    docs = await cursor.to_list(length=limit)
    return [
        FinanceAccount(
            account_id=str(doc["_id"]),
            organization_id=doc["organization_id"],
            type=doc["type"],
            owner_id=doc["owner_id"],
            code=doc["code"],
            name=doc["name"],
            currency=doc["currency"],
            status=doc["status"],
            created_at=doc["created_at"],
            updated_at=doc["updated_at"],
        )
        for doc in docs
    ]


async def _create_account(db, org_id, payload):
    import uuid
    existing = await db.finance_accounts.find_one(
        {"organization_id": org_id, "code": payload.code}
    )
    if existing:
        raise AppError(409, "account_code_exists", f"Account with code '{payload.code}' already exists")

    account_id = f"acct_{uuid.uuid4()}"
    now = now_utc()
    doc = {
        "_id": account_id,
        "organization_id": org_id,
        "type": payload.type,
        "owner_id": payload.owner_id,
        "code": payload.code,
        "name": payload.name,
        "currency": payload.currency,
        "status": payload.status,
        "created_at": now,
        "updated_at": now,
    }
    await db.finance_accounts.insert_one(doc)
    await db.account_balances.insert_one({
        "_id": f"bal_{account_id}_{payload.currency.lower()}",
        "organization_id": org_id,
        "account_id": account_id,
        "currency": payload.currency,
        "balance": 0.0,
        "as_of": now,
        "updated_at": now,
    })
    return FinanceAccount(
        account_id=account_id, organization_id=org_id,
        type=payload.type, owner_id=payload.owner_id,
        code=payload.code, name=payload.name,
        currency=payload.currency, status=payload.status,
        created_at=now, updated_at=now,
    )


async def _list_credit_profiles(db, org_id, agency_id=None, limit=50):
    query = {"organization_id": org_id}
    if agency_id:
        query["agency_id"] = agency_id
    cursor = db.credit_profiles.find(query).sort("updated_at", -1).limit(limit)
    docs = await cursor.to_list(length=limit)
    return [
        CreditProfile(
            profile_id=str(doc["_id"]),
            organization_id=doc["organization_id"],
            agency_id=doc["agency_id"],
            currency=doc["currency"],
            limit=doc["limit"],
            soft_limit=doc.get("soft_limit"),
            payment_terms=doc["payment_terms"],
            status=doc["status"],
            created_at=doc["created_at"],
            updated_at=doc["updated_at"],
        )
        for doc in docs
    ]


async def _upsert_credit_profile(db, org_id, agency_id, payload):
    if payload.soft_limit is not None and payload.soft_limit > payload.limit:
        raise AppError(422, "validation_error", "soft_limit must be <= limit")
    now = now_utc()
    existing = await db.credit_profiles.find_one(
        {"organization_id": org_id, "agency_id": agency_id}
    )
    if existing:
        await db.credit_profiles.update_one(
            {"_id": existing["_id"]},
            {"$set": {
                "limit": payload.limit,
                "soft_limit": payload.soft_limit,
                "payment_terms": payload.payment_terms,
                "status": payload.status,
                "updated_at": now,
            }},
        )
        return CreditProfile(
            profile_id=str(existing["_id"]),
            organization_id=org_id, agency_id=agency_id,
            currency=existing["currency"],
            limit=payload.limit, soft_limit=payload.soft_limit,
            payment_terms=payload.payment_terms, status=payload.status,
            created_at=existing["created_at"], updated_at=now,
        )
    else:
        profile_id = f"cred_{agency_id}"
        doc = {
            "_id": profile_id,
            "organization_id": org_id,
            "agency_id": agency_id,
            "currency": "EUR",
            "limit": payload.limit,
            "soft_limit": payload.soft_limit,
            "payment_terms": payload.payment_terms,
            "status": payload.status,
            "created_at": now,
            "updated_at": now,
        }
        await db.credit_profiles.insert_one(doc)
        return CreditProfile(
            profile_id=profile_id,
            organization_id=org_id, agency_id=agency_id,
            currency="EUR",
            limit=payload.limit, soft_limit=payload.soft_limit,
            payment_terms=payload.payment_terms, status=payload.status,
            created_at=now, updated_at=now,
        )


# ============================================================================
# Account Endpoints
# ============================================================================

@router.get("/accounts", response_model=FinanceAccountListResponse)
async def list_accounts(
    type: Optional[Literal["agency", "platform", "supplier"]] = Query(None),
    owner_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    items = await _list_accounts(db, current_user["organization_id"], type_filter=type, owner_id=owner_id, limit=limit)
    return FinanceAccountListResponse(items=items)


@router.post("/accounts", response_model=FinanceAccount, status_code=201)
async def create_account(
    payload: FinanceAccountCreate,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    return await _create_account(db, current_user["organization_id"], payload)


# ============================================================================
# Credit Profile Endpoints
# ============================================================================

@router.get("/credit-profiles", response_model=CreditProfileListResponse)
async def list_credit_profiles(
    agency_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    items = await _list_credit_profiles(db, current_user["organization_id"], agency_id=agency_id, limit=limit)
    return CreditProfileListResponse(items=items)


@router.put("/credit-profiles/{agency_id}", response_model=CreditProfile)
async def upsert_credit_profile(
    agency_id: str,
    payload: CreditProfileUpdate,
    request: Request,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    existing = await db.credit_profiles.find_one({"organization_id": org_id, "agency_id": agency_id})
    profile = await _upsert_credit_profile(db, org_id, agency_id, payload)
    saved = await db.credit_profiles.find_one({"organization_id": org_id, "agency_id": agency_id})
    try:
        await write_audit_log(
            db, organization_id=org_id,
            actor={"actor_type": "user", "actor_id": current_user.get("id") or current_user.get("email"), "email": current_user.get("email"), "roles": current_user.get("roles") or []},
            request=request, action="credit_profile_upsert",
            target_type="credit_profile", target_id=agency_id,
            before=audit_snapshot("credit_profile", existing),
            after=audit_snapshot("credit_profile", saved),
            meta={"payload": payload.model_dump()},
        )
    except Exception:
        pass
    return profile


# ============================================================================
# Payment State & Booking Financials
# ============================================================================

@router.get("/bookings/{booking_id}/payment-state")
async def get_booking_payment_state(
    booking_id: str,
    user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    org_id = user["organization_id"]
    aggregate = await db.booking_payments.find_one(
        {"organization_id": org_id, "booking_id": booking_id}, {"_id": 0},
    )
    cursor = db.booking_payment_transactions.find(
        {"organization_id": org_id, "booking_id": booking_id}
    ).sort("occurred_at", -1).limit(20)
    txs = await cursor.to_list(length=20)
    for tx in txs:
        tx.pop("_id", None)
    return {"aggregate": aggregate, "transactions": txs}


@router.get("/bookings/{booking_id}/financials")
async def get_booking_financials(
    booking_id: str,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    from app.services.booking_financials import BookingFinancialsService
    booking = await db.bookings.find_one({"_id": ObjectId(booking_id), "organization_id": org_id})
    if not booking:
        raise AppError(404, "booking_not_found", "Booking not found")
    svc = BookingFinancialsService(db)
    doc = await svc.ensure_financials(org_id, booking)
    doc["id"] = str(doc.get("_id"))
    doc["booking_id"] = str(doc.get("booking_id"))
    doc.pop("_id", None)
    return doc


@router.get("/bookings/{booking_id}/ledger-summary")
async def get_booking_ledger_summary(
    booking_id: str,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    try:
        booking_oid = ObjectId(booking_id)
    except Exception:
        raise AppError(404, "booking_not_found", "Booking not found")
    booking = await db.bookings.find_one({"_id": booking_oid, "organization_id": org_id})
    if not booking:
        raise AppError(404, "booking_not_found", "Booking not found")
    query = {"organization_id": org_id, "source.type": "booking", "source.id": booking_id}
    postings = await db.ledger_postings.find(query).to_list(length=1000)
    source_collection = "ledger_postings"
    if postings:
        total_debit = sum(float(p.get("debit", 0.0) or 0.0) for p in postings)
        total_credit = sum(float(p.get("credit", 0.0) or 0.0) for p in postings)
        events = sorted({p.get("event") for p in postings if p.get("event")})
        currency = postings[0].get("currency", "EUR")
        count = len(postings)
    else:
        entries = await db.ledger_entries.find(query).to_list(length=1000)
        if entries:
            source_collection = "ledger_entries"
            total_debit = sum(float(e.get("amount", 0.0) or 0.0) for e in entries if e.get("direction") == "debit")
            total_credit = sum(float(e.get("amount", 0.0) or 0.0) for e in entries if e.get("direction") == "credit")
            events = sorted({e.get("event") for e in entries if e.get("event")})
            currency = entries[0].get("currency", "EUR")
            count = len(entries)
        else:
            source_collection = "none"
            total_debit = total_credit = 0.0
            events = []
            currency = "EUR"
            count = 0
    return {
        "booking_id": booking_id, "organization_id": org_id,
        "currency": currency, "source_collection": source_collection,
        "postings_count": count, "total_debit": total_debit,
        "total_credit": total_credit, "diff": total_debit - total_credit,
        "events": events,
    }


# ============================================================================
# Statement & Exposure
# ============================================================================

@router.get("/accounts/{account_id}/statement", response_model=AccountStatement)
async def get_account_statement(
    account_id: str,
    from_date: Optional[datetime] = Query(None, alias="from"),
    to_date: Optional[datetime] = Query(None, alias="to"),
    limit: int = Query(100, ge=1, le=500),
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    account = await db.finance_accounts.find_one({"_id": account_id, "organization_id": org_id})
    if not account:
        raise AppError(404, "account_not_found", f"Account {account_id} not found")
    currency = account["currency"]
    opening_balance = 0.0
    if from_date:
        entries_before = await db.ledger_entries.find({
            "organization_id": org_id, "account_id": account_id,
            "currency": currency, "posted_at": {"$lt": from_date},
        }).to_list(length=10000)
        account_type = account.get("type")
        total_debit = sum(e["amount"] for e in entries_before if e["direction"] == "debit")
        total_credit = sum(e["amount"] for e in entries_before if e["direction"] == "credit")
        if account_type == "platform":
            opening_balance = total_credit - total_debit
        else:
            opening_balance = total_debit - total_credit
    query: dict[str, Any] = {"organization_id": org_id, "account_id": account_id, "currency": currency}
    if from_date:
        query["posted_at"] = {"$gte": from_date}
    if to_date:
        if "posted_at" not in query:
            query["posted_at"] = {}
        query["posted_at"]["$lte"] = to_date
    cursor = db.ledger_entries.find(query).sort("posted_at", 1).limit(limit)
    entries = await cursor.to_list(length=limit)
    items = []
    running_balance = opening_balance
    for entry in entries:
        account_type = account.get("type")
        if account_type == "platform":
            delta = entry["amount"] if entry["direction"] == "credit" else -entry["amount"]
        else:
            delta = entry["amount"] if entry["direction"] == "debit" else -entry["amount"]
        running_balance += delta
        items.append(StatementItem(
            posted_at=entry["posted_at"], direction=entry["direction"],
            amount=entry["amount"], event=entry["event"],
            source=entry["source"], memo=entry.get("memo", ""),
        ))
    return AccountStatement(
        account_id=account_id, currency=currency,
        opening_balance=opening_balance, closing_balance=running_balance, items=items,
    )


@router.get("/exposure", response_model=ExposureResponse)
async def get_exposure_dashboard(
    limit: int = Query(50, ge=1, le=200),
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    agencies = await db.agencies.find({"organization_id": org_id}).to_list(limit)
    items = []
    for ag in agencies:
        agency_id = str(ag["_id"])
        agency_name = ag.get("name", "Bilinmeyen Acente")
        credit_limit = float(ag.get("credit_limit", 100000))
        credit_used = float(ag.get("credit_used", 0))
        pipeline = [
            {"$match": {"organization_id": org_id, "agency_id": agency_id, "settlement_status": {"$ne": "settled"}}},
            {"$group": {"_id": None, "total": {"$sum": "$sell_amount"}}}
        ]
        agg_result = await db.booking_financial_entries.aggregate(pipeline).to_list(1)
        exposure = float(agg_result[0]["total"]) if agg_result else credit_used
        if credit_limit <= 0:
            status = "ok"
        elif exposure >= credit_limit:
            status = "over_limit"
        elif exposure >= credit_limit * 0.8:
            status = "near_limit"
        else:
            status = "ok"
        items.append(ExposureItem(
            agency_id=agency_id, agency_name=agency_name,
            currency=ag.get("settings", {}).get("selling_currency", "TRY") if isinstance(ag.get("settings"), dict) else "TRY",
            exposure=exposure, age_0_30=exposure * 0.6, age_31_60=exposure * 0.3, age_61_plus=exposure * 0.1,
            credit_limit=credit_limit, soft_limit=credit_limit * 0.8,
            payment_terms="net30", status=status,
        ))
    return ExposureResponse(items=items)


@router.get("/exposure/{agency_id}/entries")
async def get_exposure_entries(
    agency_id: str,
    bucket: str = Query("all", regex="^(all|0_30|31_60|61_plus)$"),
    limit: int = Query(200, ge=1, le=500),
    cursor: Optional[str] = None,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    account = await db.finance_accounts.find_one(
        {"organization_id": org_id, "type": "agency", "owner_id": agency_id}
    )
    if not account:
        raise AppError(404, "account_not_found", "Finance account for agency not found")
    account_id = account["_id"]
    currency = account.get("currency", "EUR")
    today = now_utc().date()
    q: dict[str, Any] = {"organization_id": org_id, "account_id": account_id, "currency": currency}
    cursor_q = db.ledger_entries.find(q).sort("posted_at", -1).limit(limit)
    raw_entries = await cursor_q.to_list(length=limit)
    items: list[dict[str, Any]] = []
    for entry in raw_entries:
        posted_at = entry.get("posted_at") or entry.get("occurred_at")
        if not posted_at:
            continue
        age_days = (today - posted_at.date()).days
        if bucket == "0_30" and age_days > 30:
            continue
        if bucket == "31_60" and not (31 <= age_days <= 60):
            continue
        if bucket == "61_plus" and age_days < 61:
            continue
        amount = float(entry.get("amount", 0.0) or 0.0)
        direction = entry.get("direction") or "debit"
        booking_id = entry.get("booking_id")
        source_type = entry.get("source_type") or ("booking" if booking_id else "unknown")
        source_id = entry.get("source_id") or booking_id
        items.append({
            "ledger_entry_id": str(entry.get("_id")),
            "posted_at": posted_at, "age_days": age_days,
            "amount": amount, "direction": direction,
            "source_type": source_type, "source_id": source_id,
            "booking_id": booking_id, "due_date": entry.get("due_date"),
            "note": entry.get("memo") or entry.get("note") or "",
        })
    return {"agency_id": agency_id, "currency": currency, "items": items}


# ============================================================================
# Manual Payments
# ============================================================================

@router.post("/payments", response_model=Payment, status_code=201)
async def create_manual_payment(
    payload: PaymentCreate,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    if payload.amount <= 0:
        raise AppError(422, "validation_error", "Amount must be > 0")
    account = await db.finance_accounts.find_one({"_id": payload.account_id, "organization_id": org_id})
    if not account:
        raise AppError(404, "account_not_found", f"Account {payload.account_id} not found")
    if account["currency"] != payload.currency:
        raise AppError(409, "currency_mismatch", f"Account currency {account['currency']} != payment currency {payload.currency}")
    import uuid
    payment_id = f"pay_{uuid.uuid4()}"
    now = now_utc()
    received_at = payload.received_at or now
    payment_doc = {
        "_id": payment_id, "organization_id": org_id,
        "account_id": payload.account_id, "currency": payload.currency,
        "amount": payload.amount, "method": payload.method,
        "reference": payload.reference, "received_at": received_at,
        "created_at": now, "created_by_email": current_user["email"],
    }
    await db.payments.insert_one(payment_doc)
    platform_account = await db.finance_accounts.find_one({"organization_id": org_id, "type": "platform"})
    if platform_account:
        from app.services.ledger_posting import LedgerPostingService, PostingMatrixConfig
        lines = PostingMatrixConfig.get_payment_received_lines(
            agency_account_id=payload.account_id,
            platform_account_id=platform_account["_id"],
            payment_amount=payload.amount,
        )
        await LedgerPostingService.post_event(
            organization_id=org_id, source_type="payment",
            source_id=payment_id, event="PAYMENT_RECEIVED",
            currency=payload.currency, lines=lines,
            occurred_at=received_at, created_by=current_user["email"],
        )
    return Payment(
        payment_id=payment_id, organization_id=org_id,
        account_id=payload.account_id, currency=payload.currency,
        amount=payload.amount, method=payload.method,
        reference=payload.reference, received_at=received_at,
        created_at=now, created_by_email=current_user["email"],
    )


# ============================================================================
# Test/Debug endpoints
# ============================================================================

from app.services.ledger_posting import LedgerPostingService, PostingMatrixConfig
from pydantic import BaseModel as PydanticBaseModel


class TestPostingRequest(PydanticBaseModel):
    source_type: Literal["booking", "refund", "payment", "adjustment"]
    source_id: str
    event: str
    agency_account_id: str
    platform_account_id: str
    amount: float


class TestRecalcRequest(PydanticBaseModel):
    account_id: str


@router.post("/_test/posting")
async def test_posting(
    payload: TestPostingRequest,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
):
    if payload.event == "BOOKING_CONFIRMED":
        lines = PostingMatrixConfig.get_booking_confirmed_lines(
            agency_account_id=payload.agency_account_id,
            platform_account_id=payload.platform_account_id,
            sell_amount=payload.amount,
        )
    elif payload.event == "PAYMENT_RECEIVED":
        lines = PostingMatrixConfig.get_payment_received_lines(
            agency_account_id=payload.agency_account_id,
            platform_account_id=payload.platform_account_id,
            payment_amount=payload.amount,
        )
    elif payload.event == "REFUND_APPROVED":
        lines = PostingMatrixConfig.get_refund_approved_lines(
            agency_account_id=payload.agency_account_id,
            platform_ar_account_id=payload.platform_account_id,
            refund_amount=payload.amount,
        )
    else:
        raise AppError(422, "invalid_event", f"Unsupported event: {payload.event}")
    posting = await LedgerPostingService.post_event(
        organization_id=current_user["organization_id"],
        source_type=payload.source_type, source_id=payload.source_id,
        event=payload.event, currency="EUR", lines=lines,
    )
    return {"ok": True, "posting_id": posting["_id"], "event": posting["event"], "lines_count": len(posting["lines"]), "organization_id": current_user["organization_id"]}


@router.post("/_test/recalc")
async def test_recalc(
    payload: TestRecalcRequest,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
):
    result = await LedgerPostingService.recalculate_balance(
        organization_id=current_user["organization_id"],
        account_id=payload.account_id, currency="EUR",
    )
    return {"ok": True, **result}
