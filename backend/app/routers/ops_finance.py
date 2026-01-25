"""
Finance OS Phase 1.2: Basic Finance APIs
Ops/Admin endpoints for account and credit profile management
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, File, UploadFile, Form
from fastapi.responses import StreamingResponse
from typing import Literal, Optional, Any
from datetime import datetime
from bson import ObjectId
import logging
import os
import hashlib

from app.db import get_db
from app.auth import require_roles, get_current_user
from app.errors import AppError
from app.utils import now_utc
from app.services.audit import write_audit_log, audit_snapshot
from app.services.refund_cases import RefundCaseService
from app.services.booking_events import emit_event
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
    SettlementRunCreateRequest,
    SettlementRunListResponse,
    SettlementRunDetail,
)
from app.services.settlement_runs import SettlementRunService
from app.services.booking_financials import BookingFinancialsService


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ops/finance", tags=["ops_finance"])


# ============================================================================
# Helper functions (simple repo layer)
# ============================================================================

async def _list_accounts(
    db,
    org_id: str,
    type_filter: Optional[str] = None,
    owner_id: Optional[str] = None,
    limit: int = 50,
):
    """List finance accounts with filters"""
    query = {"organization_id": org_id}
    if type_filter:
        query["type"] = type_filter
    if owner_id:
        query["owner_id"] = owner_id
    
    cursor = db.finance_accounts.find(query).sort("created_at", -1).limit(limit)
    docs = await cursor.to_list(length=limit)
    
    items = []
    for doc in docs:
        items.append(
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
        )
    
    return items


async def _create_account(db, org_id: str, payload: FinanceAccountCreate):
    """Create a new finance account"""
    import uuid
    
    # Check for duplicate code
    existing = await db.finance_accounts.find_one(
        {"organization_id": org_id, "code": payload.code}
    )
    if existing:
        raise AppError(
            status_code=409,
            code="account_code_exists",
            message=f"Account with code '{payload.code}' already exists",
        )
    
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
    
    # Auto-create initial balance cache
    balance_doc = {
        "_id": f"bal_{account_id}_{payload.currency.lower()}",
        "organization_id": org_id,
        "account_id": account_id,
        "currency": payload.currency,
        "balance": 0.0,
        "as_of": now,
        "updated_at": now,
    }
    await db.account_balances.insert_one(balance_doc)
    
    return FinanceAccount(
        account_id=account_id,
        organization_id=org_id,
        type=payload.type,
        owner_id=payload.owner_id,
        code=payload.code,
        name=payload.name,
        currency=payload.currency,
        status=payload.status,
        created_at=now,
        updated_at=now,
    )


async def _list_credit_profiles(
    db,
    org_id: str,
    agency_id: Optional[str] = None,
    limit: int = 50,
):
    """List credit profiles with filters"""
    query = {"organization_id": org_id}
    if agency_id:
        query["agency_id"] = agency_id
    
    cursor = db.credit_profiles.find(query).sort("updated_at", -1).limit(limit)
    docs = await cursor.to_list(length=limit)
    
    items = []
    for doc in docs:
        items.append(
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
        )
    
    return items


async def _upsert_credit_profile(
    db,
    org_id: str,
    agency_id: str,
    payload: CreditProfileUpdate,
):
    """Upsert credit profile (create if not exists, update if exists)"""
    
    # Validation: soft_limit <= limit (soft limit is warning threshold, must be below hard limit)
    if payload.soft_limit is not None and payload.soft_limit > payload.limit:
        raise AppError(
            status_code=422,
            code="validation_error",
            message="soft_limit must be <= limit (soft limit is warning threshold)",
        )
    
    now = now_utc()
    
    # Check if profile exists
    existing = await db.credit_profiles.find_one(
        {"organization_id": org_id, "agency_id": agency_id}
    )
    
    if existing:
        # Update existing
        update_doc = {
            "limit": payload.limit,
            "soft_limit": payload.soft_limit,
            "payment_terms": payload.payment_terms,
            "status": payload.status,
            "updated_at": now,
        }
        
        await db.credit_profiles.update_one(
            {"_id": existing["_id"]},
            {"$set": update_doc},
        )
        
        return CreditProfile(
            profile_id=str(existing["_id"]),
            organization_id=org_id,
            agency_id=agency_id,
            currency=existing["currency"],
            limit=payload.limit,
            soft_limit=payload.soft_limit,
            payment_terms=payload.payment_terms,
            status=payload.status,
            created_at=existing["created_at"],
            updated_at=now,
        )
    else:
        # Create new
        profile_id = f"cred_{agency_id}"
        
        doc = {
            "_id": profile_id,
            "organization_id": org_id,
            "agency_id": agency_id,
            "currency": "EUR",  # Phase 1: hardcoded EUR
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
            organization_id=org_id,
            agency_id=agency_id,
            currency="EUR",
            limit=payload.limit,
            soft_limit=payload.soft_limit,
            payment_terms=payload.payment_terms,
            status=payload.status,
            created_at=now,
            updated_at=now,
        )




@router.get("/bookings/{booking_id}/payment-state")
async def get_booking_payment_state(
    booking_id: str,
    user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Return booking payment aggregate + recent transactions summary.

    Used by admin/ops UI to display booking-level Stripe payment state.
    """

    org_id = user["organization_id"]

    aggregate = await db.booking_payments.find_one(
        {"organization_id": org_id, "booking_id": booking_id},
        {"_id": 0},
    )

    cursor = (
        db.booking_payment_transactions.find(
            {"organization_id": org_id, "booking_id": booking_id}
        )
        .sort("occurred_at", -1)
        .limit(20)
    )
    txs = await cursor.to_list(length=20)
    for tx in txs:
        tx.pop("_id", None)

    return {
        "aggregate": aggregate,
        "transactions": txs,
    }

# ============================================================================
# Endpoints
# ============================================================================

@router.get("/accounts", response_model=FinanceAccountListResponse)
async def list_accounts(
    type: Optional[Literal["agency", "platform", "supplier"]] = Query(None),
    owner_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    """
    List finance accounts
    
    Auth: admin|ops|super_admin
    Filters: type, owner_id
    Sorting: created_at desc
    """
    items = await _list_accounts(
        db,
        current_user["organization_id"],
        type_filter=type,
        owner_id=owner_id,
        limit=limit,
    )
    
    return FinanceAccountListResponse(items=items)


@router.post("/accounts", response_model=FinanceAccount, status_code=201)
async def create_account(
    payload: FinanceAccountCreate,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    """
    Create a new finance account
    
    Auth: admin|ops|super_admin
    Rules:
    - code must be unique per org (409 account_code_exists)
    - auto-creates initial balance cache (balance=0)
    """
    account = await _create_account(db, current_user["organization_id"], payload)
    return account


@router.get("/credit-profiles", response_model=CreditProfileListResponse)
async def list_credit_profiles(
    agency_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    """
    List credit profiles
    
    Auth: admin|ops|super_admin
    Filters: agency_id
    Sorting: updated_at desc
    """
    items = await _list_credit_profiles(
        db,
        current_user["organization_id"],
        agency_id=agency_id,
        limit=limit,
    )
    
    return CreditProfileListResponse(items=items)


@router.put("/credit-profiles/{agency_id}", response_model=CreditProfile)
async def upsert_credit_profile(
    agency_id: str,
    payload: CreditProfileUpdate,
    request: Request,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    """
    Upsert credit profile (create if not exists, update if exists)
    
    Auth: admin|ops|super_admin
    Rules:
    - soft_limit must be >= limit (422 validation_error)
    - upsert semantics (creates if not exists)
    """
    org_id = current_user["organization_id"]

    # Load existing profile for before snapshot
    existing = await db.credit_profiles.find_one({"organization_id": org_id, "agency_id": agency_id})

    profile = await _upsert_credit_profile(
        db,
        org_id,
        agency_id,
        payload,
    )

    # Reload for after snapshot (ensure latest doc)
    saved = await db.credit_profiles.find_one({"organization_id": org_id, "agency_id": agency_id})

    try:
        await write_audit_log(
            db,
            organization_id=org_id,
            actor={
                "actor_type": "user",
                "actor_id": current_user.get("id") or current_user.get("email"),
                "email": current_user.get("email"),
                "roles": current_user.get("roles") or [],
            },
            request=request,
            action="credit_profile_upsert",
            target_type="credit_profile",
            target_id=agency_id,
            before=audit_snapshot("credit_profile", existing),
            after=audit_snapshot("credit_profile", saved),
            meta={
                "payload": payload.model_dump(),
            },
        )
    except Exception:
        # best-effort audit; do not block main flow
        pass

    return profile

# ============================================================================
# Settlement runs (Phase 2A.4)
# ============================================================================


@router.post("/settlements")
async def create_settlement_run(
    payload: SettlementRunCreateRequest,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    svc = SettlementRunService(db)
    run = await svc.create_run(
        organization_id=org_id,
        supplier_id=payload.supplier_id,
        currency=payload.currency,
        period=payload.period,
        created_by=current_user["email"],
    )
    return run

# ============================================================================
# Refund cases (Phase 2B.3)
# ============================================================================


@router.get("/refunds")
async def list_refunds(
    status: Optional[str] = Query(None),
    booking_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    from app.services.refund_cases import RefundCaseService

    svc = RefundCaseService(db)
    return await svc.list_refunds(org_id, status, limit, booking_id)


@router.get("/refunds/{case_id}")
async def get_refund_case(
    case_id: str,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    from app.services.refund_cases import RefundCaseService

    svc = RefundCaseService(db)
    return await svc.get_case(org_id, case_id)


@router.post("/refunds/{case_id}/approve")
async def approve_refund_case(
    case_id: str,
    payload: dict,
    request: Request,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    """Compat endpoint: map to step1/step2 based on current status.

    New callers should prefer approve-step1/approve-step2/mark-paid.
    This wrapper reproduces the same audit + booking timeline events as the
    explicit step1/step2 endpoints but marks them with meta.via="compat".
    """
    org_id = current_user["organization_id"]
    approved_amount = float(payload.get("approved_amount") or 0.0)

    svc = RefundCaseService(db)

    # Load current case once for status + booking_id
    existing = await svc.get_case(org_id, case_id)
    if not existing:
        raise AppError(404, "refund_case_not_found", "Refund case not found")

    status = existing.get("status")
    booking_id = existing.get("booking_id")

    if status not in {"open", "pending_approval", "pending_approval_1", "pending_approval_2"}:
        raise AppError(
            status_code=409,
            code="invalid_case_state",
            message="Refund case is not open for approval",
        )

    actor = {
        "actor_type": "user",
        "actor_id": current_user.get("id") or current_user.get("email"),
        "email": current_user.get("email"),
        "roles": current_user.get("roles") or [],
    }

    result_step1 = None
    # 1) If case is open or in first pending state, run step1 first
    if status in {"open", "pending_approval", "pending_approval_1"}:
        status_from = status
        result_step1 = await svc.approve_step1(
            organization_id=org_id,
            case_id=case_id,
            approved_amount=approved_amount,
            actor_email=current_user["email"],
            actor_id=current_user.get("id"),
        )

        status_to = result_step1.get("status")
        # Audit for step1 (compat)
        try:
            await write_audit_log(
                db,
                organization_id=org_id,
                actor=actor,
                request=request,
                action="refund_approve_step1",
                target_type="refund_case",
                target_id=case_id,
                before=audit_snapshot("refund_case", existing),
                after=audit_snapshot("refund_case", result_step1),
                meta={
                    "approved_amount": approved_amount,
                    "status_from": status_from,
                    "status_to": status_to,
                    "case_id": case_id,
                    "by_email": current_user.get("email"),
                    "by_actor_id": current_user.get("id"),
                    "via": "compat",
                },
            )

            if booking_id:
                await emit_event(
                    db,
                    organization_id=org_id,
                    booking_id=booking_id,
                    type="REFUND_APPROVED_STEP1",
                    actor={
                        "email": current_user.get("email"),
                        "actor_id": current_user.get("id"),
                        "roles": current_user.get("roles") or [],
                    },
                    meta={
                        "case_id": case_id,
                        "approved_amount": approved_amount,
                        "status_from": status_from,
                        "status_to": status_to,
                        "by_email": current_user.get("email"),
                        "by_actor_id": current_user.get("id"),
                        "via": "compat",
                    },
                )
        except Exception:
            # compat audit/timeline is best-effort
            pass

        # Refresh existing snapshot for step2
        existing = result_step1
        status = result_step1.get("status")

    # 2) Then run step2 (this will perform ledger + financials and set status=approved)
    status_from_2 = status
    result = await svc.approve_step2(
        organization_id=org_id,
        case_id=case_id,
        actor_email=current_user["email"],
        actor_id=current_user.get("id"),
        note=payload.get("note"),
    )

    try:
        status_to_2 = result.get("status")
        await write_audit_log(
            db,
            organization_id=org_id,
            actor=actor,
            request=request,
            action="refund_approve_step2",
            target_type="refund_case",
            target_id=case_id,
            before=audit_snapshot("refund_case", existing),
            after=audit_snapshot("refund_case", result),
            meta={
                "note": payload.get("note"),
                "status_from": status_from_2,
                "status_to": status_to_2,
                "approved_amount": (result.get("approved") or {}).get("amount"),
                "case_id": case_id,
                "by_email": current_user.get("email"),
                "by_actor_id": current_user.get("id"),
                "via": "compat",
            },
        )

        if booking_id:
            await emit_event(
                db,
                organization_id=org_id,
                booking_id=booking_id,
                type="REFUND_APPROVED_STEP2",
                actor={
                    "email": current_user.get("email"),
                    "actor_id": current_user.get("id"),
                    "roles": current_user.get("roles") or [],
                },
                meta={
                    "case_id": case_id,
                    "note": payload.get("note"),
                    "status_from": status_from_2,
                    "status_to": status_to_2,
                    "approved_amount": (result.get("approved") or {}).get("amount"),
                    "by_email": current_user.get("email"),
                    "by_actor_id": current_user.get("id"),
                    "via": "compat",
                },
            )
    except Exception:
        pass

    return result


@router.post("/refunds/{case_id}/approve-step1")
async def approve_refund_step1(
    case_id: str,
    payload: dict,
    request: Request,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    approved_amount = float(payload.get("approved_amount") or 0.0)

    actor = {
        "actor_type": "user",
        "actor_id": current_user.get("id") or current_user.get("email"),
        "email": current_user.get("email"),
        "roles": current_user.get("roles") or [],
    }
    svc = RefundCaseService(db)

    # Load existing for audit before
    existing = await svc.get_case(org_id, case_id)
    status_from = existing.get("status") if existing else None

    result = await svc.approve_step1(
        organization_id=org_id,
        case_id=case_id,
        approved_amount=approved_amount,
        actor_email=current_user["email"],
        actor_id=current_user.get("id"),
    )

    # Audit + booking event (best-effort)
    try:
        status_to = result.get("status")
        await write_audit_log(
            db,
            organization_id=org_id,
            actor=actor,
            request=request,
            action="refund_approve_step1",
            target_type="refund_case",
            target_id=case_id,
            before=audit_snapshot("refund_case", existing),
            after=audit_snapshot("refund_case", result),
            meta={
                "approved_amount": approved_amount,
                "status_from": status_from,
                "status_to": status_to,
            },
        )

        # Booking timeline event
        booking_id = result.get("booking_id")
        if booking_id:
            await emit_event(
                db,
                organization_id=org_id,
                booking_id=booking_id,
                type="REFUND_APPROVED_STEP1",
                actor={
                    "email": current_user.get("email"),
                    "actor_id": current_user.get("id"),
                    "roles": current_user.get("roles") or [],
                },
                meta={
                    "case_id": case_id,
                    "approved_amount": approved_amount,
                    "status_from": status_from,
                    "status_to": status_to,
                    "by_email": current_user.get("email"),
                    "by_actor_id": current_user.get("id"),
                },
            )
    except Exception:
        pass

    return result


@router.post("/refunds/{case_id}/approve-step2")
async def approve_refund_step2(
    case_id: str,
    payload: dict,
    request: Request,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    note = payload.get("note")

    svc = RefundCaseService(db)

    existing = await svc.get_case(org_id, case_id)
    status_from = existing.get("status") if existing else None

    result = await svc.approve_step2(
        organization_id=org_id,
        case_id=case_id,
        actor_email=current_user["email"],
        actor_id=current_user.get("id"),
        note=note,
    )

    try:
        status_to = result.get("status")
        await write_audit_log(
            db,
            organization_id=org_id,
            actor={
                "actor_type": "user",
                "actor_id": current_user.get("id") or current_user.get("email"),
                "email": current_user.get("email"),
                "roles": current_user.get("roles") or [],
            },
            request=request,
            action="refund_approve_step2",
            target_type="refund_case",
            target_id=case_id,
            before=audit_snapshot("refund_case", existing),
            after=audit_snapshot("refund_case", result),
            meta={
                "note": note,
                "status_from": status_from,
                "status_to": status_to,
                "approved_amount": (result.get("approved") or {}).get("amount"),
            },
        )

        booking_id = result.get("booking_id")
        if booking_id:
            await emit_event(
                db,
                organization_id=org_id,
                booking_id=booking_id,
                type="REFUND_APPROVED_STEP2",
                actor={
                    "email": current_user.get("email"),
                    "actor_id": current_user.get("id"),
                    "roles": current_user.get("roles") or [],
                },
                meta={
                    "case_id": case_id,
                    "note": note,
                    "status_from": status_from,
                    "status_to": status_to,
                    "approved_amount": (result.get("approved") or {}).get("amount"),
                    "by_email": current_user.get("email"),
                    "by_actor_id": current_user.get("id"),
                },
            )
    except Exception:
        pass

    return result


@router.post("/refunds/{case_id}/mark-paid")
async def mark_refund_paid(
    case_id: str,
    payload: dict,
    request: Request,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    payment_reference = (payload.get("payment_reference") or "").strip()

    svc = RefundCaseService(db)

    existing = await svc.get_case(org_id, case_id)
    status_from = existing.get("status") if existing else None

    result = await svc.mark_paid(
        organization_id=org_id,
        case_id=case_id,
        payment_reference=payment_reference,
        actor_email=current_user["email"],
        actor_id=current_user.get("id"),
    )

    try:
        status_to = result.get("status")
        await write_audit_log(
            db,
            organization_id=org_id,
            actor={
                "actor_type": "user",
                "actor_id": current_user.get("id") or current_user.get("email"),
                "email": current_user.get("email"),
                "roles": current_user.get("roles") or [],
            },
            request=request,
            action="refund_mark_paid",
            target_type="refund_case",
            target_id=case_id,
            before=audit_snapshot("refund_case", existing),
            after=audit_snapshot("refund_case", result),
            meta={
                "payment_reference": payment_reference,
                "status_from": status_from,
                "status_to": status_to,
            },
        )

        booking_id = result.get("booking_id")
        if booking_id:
            await emit_event(
                db,
                organization_id=org_id,
                booking_id=booking_id,
                type="REFUND_MARKED_PAID",
                actor={
                    "email": current_user.get("email"),
                    "actor_id": current_user.get("id"),
                    "roles": current_user.get("roles") or [],
                },
                meta={
                    "refund_case_id": case_id,
                    "payment_reference": payment_reference,
                    "status_from": status_from,
                    "status_to": status_to,
                },
            )
    except Exception:
        pass

    return result


@router.post("/refunds/{case_id}/close")
async def close_refund_case(
    case_id: str,
    payload: dict,
    request: Request,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    note = payload.get("note")

    svc = RefundCaseService(db)

    existing = await svc.get_case(org_id, case_id)
    status_from = existing.get("status") if existing else None

    result = await svc.close_case(
        organization_id=org_id,
        case_id=case_id,
        actor_email=current_user["email"],
        actor_id=current_user.get("id"),
        note=note,
    )

    try:
        status_to = result.get("status")
        await write_audit_log(
            db,
            organization_id=org_id,
            actor={
                "actor_type": "user",
                "actor_id": current_user.get("id") or current_user.get("email"),
                "email": current_user.get("email"),
                "roles": current_user.get("roles") or [],
            },
            request=request,
            action="refund_close",
            target_type="refund_case",
            target_id=case_id,
            before=audit_snapshot("refund_case", existing),
            after=audit_snapshot("refund_case", result),
            meta={
                "note": note,
                "status_from": status_from,
                "status_to": status_to,
            },
        )

        booking_id = result.get("booking_id")
        if booking_id:
            await emit_event(
                db,
                organization_id=org_id,
                booking_id=booking_id,
                type="REFUND_CLOSED",
                actor={
                    "email": current_user.get("email"),
                    "actor_id": current_user.get("id"),
                    "roles": current_user.get("roles") or [],
                },
                meta={
                    "refund_case_id": case_id,
                    "note": note,
                    "status_from": status_from,
                    "status_to": status_to,
                },
            )
    except Exception:
        pass

    return result


@router.get("/bookings/{booking_id}/financials")
async def get_booking_financials(
    booking_id: str,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    """Get or initialize booking_financials snapshot for a booking (Phase 2B.4).

    - If booking does not exist: 404
    - If booking exists but financials doc is missing: ensure + return
    """
    org_id = current_user["organization_id"]

    from app.errors import AppError

    booking = await db.bookings.find_one({"_id": ObjectId(booking_id), "organization_id": org_id})
    if not booking:
        raise AppError(
            status_code=404,
            code="booking_not_found",
            message="Booking not found",
        )

    svc = BookingFinancialsService(db)
    doc = await svc.ensure_financials(org_id, booking)

    # Simple JSON-serializable dict (ObjectId -> str)
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
    """Return simple ledger balance proof for a booking.

    - Scope: source.type="booking" && source.id=booking_id
    - Implementation: önce ledger_postings, yoksa ledger_entries fallback
    - Bu endpoint yeni business rule eklemez; sadece mevcut ledger durumunu
      ops tarafında kolay okunabilir hale getirir.
    """
    org_id = current_user["organization_id"]

    # Booking'in bu org'da var oldugunu dogrula
    try:
        booking_oid = ObjectId(booking_id)
    except Exception:
        raise AppError(
            status_code=404,
            code="booking_not_found",
            message="Booking not found",
        )

    booking = await db.bookings.find_one({"_id": booking_oid, "organization_id": org_id})
    if not booking:
        raise AppError(
            status_code=404,
            code="booking_not_found",
            message="Booking not found",
        )

    query = {
        "organization_id": org_id,
        "source.type": "booking",
        "source.id": booking_id,
    }

    # 1) Önce ledger_postings uzerinden toplamlar
    postings = await db.ledger_postings.find(query).to_list(length=1000)
    source_collection = "ledger_postings"

    if postings:
        total_debit = sum(float(p.get("debit", 0.0) or 0.0) for p in postings)
        total_credit = sum(float(p.get("credit", 0.0) or 0.0) for p in postings)
        events = sorted({p.get("event") for p in postings if p.get("event")})
        currency = postings[0].get("currency", "EUR")
        count = len(postings)
    else:
        # 2) postings yoksa ledger_entries fallback
        entries = await db.ledger_entries.find(query).to_list(length=1000)
        if entries:
            source_collection = "ledger_entries"
            total_debit = sum(
                float(e.get("amount", 0.0) or 0.0)
                for e in entries
                if e.get("direction") == "debit"
            )
            total_credit = sum(
                float(e.get("amount", 0.0) or 0.0)
                for e in entries
                if e.get("direction") == "credit"
            )
            events = sorted({e.get("event") for e in entries if e.get("event")})
            currency = entries[0].get("currency", "EUR")
            count = len(entries)
        else:
            source_collection = "none"
            total_debit = 0.0
            total_credit = 0.0
            events: list[str] = []
            currency = "EUR"
            count = 0

    diff = total_debit - total_credit

    return {
        "booking_id": booking_id,
        "organization_id": org_id,
        "currency": currency,
        "source_collection": source_collection,
        "postings_count": count,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "diff": diff,
        "events": events,
    }



@router.post("/refunds/{case_id}/reject")
async def reject_refund_case(
    case_id: str,
    payload: dict,
    request: Request,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    from app.services.refund_cases import RefundCaseService

    reason = payload.get("reason")

    svc = RefundCaseService(db)

    existing = await svc.get_case(org_id, case_id)
    status_from = existing.get("status") if existing else None

    await svc.reject(
        organization_id=org_id,
        case_id=case_id,
        decided_by=current_user["email"],
        reason=reason,
    )

    # Reload after update for reliable snapshot
    saved = await svc.get_case(org_id, case_id)

    # Audit + booking event (best-effort)
    try:
        status_to = saved.get("status") if saved else None
        await write_audit_log(
            db,
            organization_id=org_id,
            actor={
                "actor_type": "user",
                "actor_id": current_user.get("id") or current_user.get("email"),
                "email": current_user.get("email"),
                "roles": current_user.get("roles") or [],
            },
            request=request,
            action="refund_reject",
            target_type="refund_case",
            target_id=case_id,
            before=audit_snapshot("refund_case", existing),
            after=audit_snapshot("refund_case", saved),
            meta={
                "reason": reason,
                "status_from": status_from,
                "status_to": status_to,
                "case_id": case_id,
                "by_email": current_user.get("email"),
                "by_actor_id": current_user.get("id"),
            },
        )

        booking_id = saved.get("booking_id") if saved else None
        if booking_id:
            await emit_event(
                db,
                organization_id=org_id,
                booking_id=booking_id,
                type="REFUND_REJECTED",
                actor={
                    "email": current_user.get("email"),
                    "actor_id": current_user.get("id"),
                    "roles": current_user.get("roles") or [],
                },
                meta={
                    "case_id": case_id,
                    "reason": reason,
                    "status_from": status_from,
                    "status_to": status_to,
                    "by_email": current_user.get("email"),
                    "by_actor_id": current_user.get("id"),
                },
            )
    except Exception as e:
        logger.warning("audit_write_failed refund_reject case_id=%s err=%s", case_id, str(e))

    return saved


@router.get("/settlements", response_model=SettlementRunListResponse)
async def list_settlement_runs(
    supplier_id: Optional[str] = Query(None),
    currency: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    svc = SettlementRunService(db)
    return await svc.list_runs(org_id, supplier_id, currency, status, limit)


@router.get("/settlements/{settlement_id}", response_model=SettlementRunDetail)
async def get_settlement_run(
    settlement_id: str,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    svc = SettlementRunService(db)
    return await svc.get_run(org_id, settlement_id)


@router.post("/settlements/{settlement_id}/items:add")
async def add_settlement_items(
    settlement_id: str,
    accrual_ids: list[str],
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    svc = SettlementRunService(db)
    return await svc.add_items(org_id, settlement_id, accrual_ids, current_user["email"])


@router.post("/settlements/{settlement_id}/items:remove")
async def remove_settlement_items(
    settlement_id: str,
    accrual_ids: list[str],
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    svc = SettlementRunService(db)
    return await svc.remove_items(org_id, settlement_id, accrual_ids, current_user["email"])


@router.post("/settlements/{settlement_id}/approve")
async def approve_settlement_run(
    settlement_id: str,
    approved_at: Optional[datetime] = None,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    svc = SettlementRunService(db)
    return await svc.approve(org_id, settlement_id, current_user["email"], approved_at)


@router.post("/settlements/{settlement_id}/cancel")
async def cancel_settlement_run(
    settlement_id: str,
    reason: Optional[str] = None,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    svc = SettlementRunService(db)
    return await svc.cancel(org_id, settlement_id, current_user["email"], reason)


@router.post("/settlements/{settlement_id}/mark-paid")
async def mark_settlement_paid(
    settlement_id: str,
    paid_at: Optional[datetime] = None,
    payment_reference: Optional[str] = None,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    svc = SettlementRunService(db)
    return await svc.mark_paid(
        org_id,
        settlement_id,
        paid_by=current_user["email"],
        paid_at=paid_at,
        payment_reference=payment_reference,
    )



# ============================================================================
# TEST/DEBUG endpoints (Phase 1 only)
# ============================================================================

from app.services.ledger_posting import LedgerPostingService, LedgerLine, PostingMatrixConfig
from pydantic import BaseModel as PydanticBaseModel


class TestPostingRequest(PydanticBaseModel):
    """Test posting request for Phase 1.3 testing"""
    source_type: Literal["booking", "refund", "payment", "adjustment"]
    source_id: str
    event: str
    agency_account_id: str
    platform_account_id: str
    amount: float


@router.post("/_test/posting")
async def test_posting(
    payload: TestPostingRequest,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
):
    """
    TEST ENDPOINT: Create a ledger posting (Phase 1.3 testing only)
    
    DO NOT USE IN PRODUCTION
    """
    # Determine lines based on event
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
        raise AppError(
            status_code=422,
            code="invalid_event",
            message=f"Unsupported event: {payload.event}",
        )
    
    posting = await LedgerPostingService.post_event(
        organization_id=current_user["organization_id"],
        source_type=payload.source_type,
        source_id=payload.source_id,
        event=payload.event,
        currency="EUR",
        lines=lines,
    )
    
    return {
        "ok": True,
        "posting_id": posting["_id"],
        "event": posting["event"],
        "lines_count": len(posting["lines"]),
        "organization_id": current_user["organization_id"],
    }


class TestRecalcRequest(PydanticBaseModel):
    """Test recalc request"""
    account_id: str


@router.post("/_test/recalc")
async def test_recalc(
    payload: TestRecalcRequest,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
):
    """
    TEST ENDPOINT: Recalculate account balance (Phase 1.3 testing only)
    """
    result = await LedgerPostingService.recalculate_balance(
        organization_id=current_user["organization_id"],
        account_id=payload.account_id,
        currency="EUR",
    )
    
    return {
        "ok": True,
        **result,
    }


# ============================================================================
# Phase 2A.1: Supplier Account Management
# ============================================================================

from app.services.supplier_finance import SupplierFinanceService


@router.get("/suppliers/{supplier_id}/accounts")
async def get_supplier_accounts(
    supplier_id: str,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    """
    Get all finance accounts for supplier (by currency)
    
    Auth: admin|ops|super_admin
    """
    org_id = current_user["organization_id"]
    
    svc = SupplierFinanceService(db)
    accounts = await svc.get_supplier_accounts(org_id, supplier_id)
    
    return {
        "supplier_id": supplier_id,
        "accounts": [
            {
                "account_id": acc["account_id"],
                "currency": acc["currency"],
                "code": acc["code"],
                "name": acc["name"],
                "status": acc["status"],
            }
            for acc in accounts
        ]
    }



# ============================================================================
# Documents (refund case evidence vault) - Phase 2.2
# ============================================================================


def _get_upload_dir() -> str:
    base = os.environ.get("UPLOAD_DIR") or "./uploads"
    return os.path.join(base, "refunds")


@router.post("/documents/upload")
async def upload_document(
    entity_type: str = Form(...),
    entity_id: str = Form(...),
    tag: str = Form(...),
    note: Optional[str] = Form(None),
    file: UploadFile = File(...),
    request: Request = None,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]

    if entity_type != "refund_case":
        raise AppError(400, "unsupported_entity_type", "Only refund_case is supported in Phase 2.2")

    # Validate refund case exists and belongs to org
    svc = RefundCaseService(db)
    case = await svc.get_case(org_id, entity_id)
    if not case:
        raise AppError(404, "refund_case_not_found", "Refund case not found")

    booking_id = case.get("booking_id")

    # Normalize tag
    allowed_tags = {"refund_proof", "invoice", "correspondence", "other"}
    if tag not in allowed_tags:
        tag = "other"

    now = now_utc()
    original_filename = file.filename or "upload.bin"
    safe_name = original_filename.replace("/", "_").replace("\\", "_")

    doc = {
        "organization_id": org_id,
        "created_at": now,
        "created_by_email": current_user.get("email"),
        "created_by_actor_id": current_user.get("id"),
        "filename": safe_name,
        "content_type": file.content_type or "application/octet-stream",
        "size_bytes": 0,
        "storage": {
            "provider": "local",
            "path": None,
        },
        "sha256": None,
        "status": "active",
    }

    res = await db.documents.insert_one(doc)
    doc_id = res.inserted_id

    # Build disk path
    base_dir = _get_upload_dir()
    case_dir = os.path.join(base_dir, entity_id)
    os.makedirs(case_dir, exist_ok=True)
    disk_path = os.path.join(case_dir, f"{doc_id}_{safe_name}")

    sha256 = hashlib.sha256()
    size = 0
    with open(disk_path, "wb") as f:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
            sha256.update(chunk)
            size += len(chunk)

    await db.documents.update_one(
        {"_id": doc_id},
        {
            "$set": {
                "size_bytes": size,
                "storage.path": disk_path,
                "sha256": sha256.hexdigest(),
            }
        },
    )

    link = {
        "organization_id": org_id,
        "created_at": now,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "document_id": doc_id,
        "tag": tag,
        "note": note,
    }
    link_res = await db.document_links.insert_one(link)
    link_id = link_res.inserted_id

    actor = {
        "actor_type": "user",
        "actor_id": current_user.get("id") or current_user.get("email"),
        "email": current_user.get("email"),
        "roles": current_user.get("roles") or [],
    }

    # Audit + timeline (best-effort)
    try:
        await write_audit_log(
            db,
            organization_id=org_id,
            actor=actor,
            request=request,
            action="document_upload",
            target_type="document",
            target_id=str(doc_id),
            before=None,
            after={
                "document_id": str(doc_id),
                "filename": safe_name,
                "tag": tag,
                "entity_type": entity_type,
                "entity_id": entity_id,
            },
            meta={
                "entity_type": entity_type,
                "entity_id": entity_id,
                "tag": tag,
                "filename": safe_name,
                "size_bytes": size,
                "content_type": file.content_type,
            },
        )
    except Exception:
        logger.exception(
            "audit_write_failed action=document_upload org=%s case=%s doc=%s",
            org_id,
            entity_id,
            str(doc_id),
        )

    if booking_id:
        try:
            await emit_event(
                db,
                organization_id=org_id,
                booking_id=booking_id,
                type="DOCUMENT_UPLOADED",
                actor={
                    "email": current_user.get("email"),
                    "actor_id": current_user.get("id"),
                    "roles": current_user.get("roles") or [],
                },
                meta={
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "document_id": str(doc_id),
                    "tag": tag,
                    "filename": safe_name,
                    "by_email": current_user.get("email"),
                    "by_actor_id": current_user.get("id"),
                },
            )
        except Exception:
            logger.exception(
                "event_emit_failed type=DOCUMENT_UPLOADED org=%s booking=%s case=%s doc=%s",
                org_id,
                booking_id,
                entity_id,
                str(doc_id),
            )

    return {
        "document_id": str(doc_id),
        "link_id": str(link_id),
        "filename": safe_name,
        "tag": tag,
        "size_bytes": size,
        "content_type": file.content_type,
        "created_at": now,
        "created_by_email": current_user.get("email"),
        "status": "active",
    }


@router.get("/documents")
async def list_documents(
    entity_type: str = Query(...),
    entity_id: str = Query(...),
    include_deleted: bool = Query(False),
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]

    if entity_type != "refund_case":
        raise AppError(400, "unsupported_entity_type", "Only refund_case is supported in Phase 2.2")

    # Join links + documents
    link_query: dict[str, Any] = {
        "organization_id": org_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
    }

    links = await db.document_links.find(link_query).to_list(length=500)
    if not links:
        return {"entity_type": entity_type, "entity_id": entity_id, "items": []}

    doc_ids = [link["document_id"] for link in links]
    doc_query: dict[str, Any] = {"_id": {"$in": doc_ids}, "organization_id": org_id}
    if not include_deleted:
        doc_query["status"] = {"$ne": "deleted"}

    docs = await db.documents.find(doc_query).to_list(length=len(doc_ids))
    docs_by_id = {d["_id"]: d for d in docs}

    items = []
    for link in links:
        d = docs_by_id.get(link["document_id"])
        if not d:
            continue
        items.append(
            {
                "document_id": str(d["_id"]),
                "link_id": str(link["_id"]),
                "tag": link.get("tag"),
                "note": link.get("note"),
                "filename": d.get("filename"),
                "content_type": d.get("content_type"),
                "size_bytes": d.get("size_bytes"),
                "created_at": d.get("created_at"),
                "created_by_email": d.get("created_by_email"),
                "status": d.get("status", "active"),
            }
        )

    return {"entity_type": entity_type, "entity_id": entity_id, "items": items}


@router.get("/documents/{document_id}/download")
async def download_document(
    document_id: str,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]

    try:
        oid = ObjectId(document_id)
    except Exception:
        raise AppError(404, "document_not_found", "Document not found")

    doc = await db.documents.find_one({"_id": oid, "organization_id": org_id})
    if not doc or doc.get("status") == "deleted":
        raise AppError(404, "document_not_found", "Document not found")

    storage = doc.get("storage") or {}
    path = storage.get("path")
    if not path or not os.path.exists(path):
        raise AppError(404, "file_not_found", "File content not found")

    filename = doc.get("filename") or "file.bin"
    content_type = doc.get("content_type") or "application/octet-stream"

    def iterfile():
        with open(path, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                yield chunk

    headers = {"Content-Disposition": f"attachment; filename=\"{filename}\""}
    return StreamingResponse(iterfile(), media_type=content_type, headers=headers)


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    payload: Optional[dict] = None,
    request: Request = None,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    org_id = current_user["organization_id"]
    reason = (payload or {}).get("reason") if isinstance(payload, dict) else None

    try:
        oid = ObjectId(document_id)
    except Exception:
        raise AppError(404, "document_not_found", "Document not found")

    doc = await db.documents.find_one({"_id": oid, "organization_id": org_id})
    if not doc:
        raise AppError(404, "document_not_found", "Document not found")

    # If already deleted, be idempotent and do not emit another event
    already_deleted = doc.get("status") == "deleted"

    if not already_deleted:
        await db.documents.update_one({"_id": oid}, {"$set": {"status": "deleted"}})

    links = await db.document_links.find({"organization_id": org_id, "document_id": oid}).to_list(length=100)
    # For now we keep links; they may be useful for history.

    entity_type = links[0].get("entity_type") if links else None
    entity_id = links[0].get("entity_id") if links else None
    tag = links[0].get("tag") if links else None

    actor = {
        "actor_type": "user",
        "actor_id": current_user.get("id") or current_user.get("email"),
        "email": current_user.get("email"),
        "roles": current_user.get("roles") or [],
    }

    # Audit + timeline (best-effort)
    try:
        await write_audit_log(
            db,
            organization_id=org_id,
            actor=actor,
            request=request,
            action="document_delete",
            target_type="document",
            target_id=document_id,
            before={
                "document_id": document_id,
                "filename": doc.get("filename"),
                "tag": tag,
                "entity_type": entity_type,
                "entity_id": entity_id,
            },
            after={
                "document_id": document_id,
                "status": "deleted",
            },
            meta={
                "reason": reason,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "filename": doc.get("filename"),
                "tag": tag,
            },
        )

        # Emit timeline event only once (when transitioning to deleted)
        if not already_deleted and entity_type == "refund_case" and entity_id:
            # Load refund case to find booking
            svc = RefundCaseService(db)
            case = await svc.get_case(org_id, entity_id)
            booking_id = case.get("booking_id") if case else None
            if booking_id:
                await emit_event(
                    db,
                    organization_id=org_id,
                    booking_id=booking_id,
                    type="DOCUMENT_DELETED",
                    actor={
                        "email": current_user.get("email"),
                        "actor_id": current_user.get("id"),
                        "roles": current_user.get("roles") or [],
                    },
                    meta={
                        "entity_type": entity_type,
                        "entity_id": entity_id,
                        "document_id": document_id,
                        "filename": doc.get("filename"),
                        "tag": tag,
                        "reason": reason,
                        "by_email": current_user.get("email"),
                        "by_actor_id": current_user.get("id"),
                    },
                )
    except Exception as e:
        logger.warning("document_delete_audit_failed doc_id=%s err=%s", document_id, str(e))

    return {"ok": True}

@router.get("/suppliers/{supplier_id}/balances")
async def get_supplier_balances(
    supplier_id: str,
    currency: str = Query("EUR"),
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    """
    Get supplier payable balance
    
    Auth: admin|ops|super_admin
    Balance rule: credit - debit (payables)
    """
    org_id = current_user["organization_id"]
    
    svc = SupplierFinanceService(db)
    balance = await svc.get_supplier_balance(org_id, supplier_id, currency)
    
    return {
        "supplier_id": supplier_id,
        "currency": currency,
        "balance": balance,
    }


@router.post("/suppliers/{supplier_id}/accounts/ensure")
async def ensure_supplier_account(
    supplier_id: str,
    currency: str = Query("EUR"),
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    """
    Ensure supplier account exists (create if not)
    
    Auth: admin|ops|super_admin
    Used by ops for manual account creation or verification
    """
    org_id = current_user["organization_id"]
    
    svc = SupplierFinanceService(db)
    account_id = await svc.get_or_create_supplier_account(
        org_id, supplier_id, currency
    )
    
    account = await db.finance_accounts.find_one({"_id": ObjectId(account_id)})
    
    return {
        "account_id": account_id,
        "supplier_id": supplier_id,
        "currency": currency,
        "code": account["code"],
        "name": account["name"],
        "status": account["status"],
    }


@router.get("/suppliers/payable-summary")
async def get_supplier_payable_summary(
    currency: str = Query("EUR"),
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    """
    Get supplier payable summary (dashboard view)
    
    Auth: admin|ops|super_admin
    Shows all suppliers with outstanding payables
    """
    org_id = current_user["organization_id"]
    
    svc = SupplierFinanceService(db)
    balances = await svc.get_all_supplier_balances(org_id, currency)
    
    return {
        "currency": currency,
        "total_payable": sum(b["balance"] for b in balances),
        "supplier_count": len(balances),
        "items": balances,
    }

@router.get("/supplier-accruals")
async def list_supplier_accruals(
    supplier_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    """List supplier accruals for ops/debug.

    Filters:
    - supplier_id (optional)
    - status (optional)
    """
    org_id = current_user["organization_id"]

    query: dict[str, Any] = {"organization_id": org_id}
    if supplier_id:
        query["supplier_id"] = supplier_id
    if status:
        query["status"] = status

    cursor = (
        db.supplier_accruals.find(query)
        .sort("accrued_at", -1)
        .limit(limit)
    )
    docs = await cursor.to_list(length=limit)

    items = []
    for doc in docs:
        amounts = doc.get("amounts") or {}
        items.append(
            {
                "accrual_id": str(doc.get("_id")),
                "booking_id": doc.get("booking_id"),
                "supplier_id": doc.get("supplier_id"),
                "currency": doc.get("currency"),
                "net_payable": amounts.get("net_payable"),
                "status": doc.get("status"),
                "accrued_at": doc.get("accrued_at"),
                "settlement_id": doc.get("settlement_id"),
            }
        )

    return {"items": items}


from pydantic import BaseModel as PydanticBaseModel


class SupplierAccrualAdjustRequest(PydanticBaseModel):
    new_sell: float
    new_commission: float
    trigger: Optional[str] = "ops_manual_adjust"


@router.post("/supplier-accruals/{booking_id}/reverse")
async def reverse_supplier_accrual(
    booking_id: str,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    """Manually reverse supplier accrual for a booking.

    Thin wrapper around SupplierAccrualService.reverse_accrual_for_booking.
    """
    org_id = current_user["organization_id"]
    from app.services.supplier_accrual import SupplierAccrualService

    svc = SupplierAccrualService(db)
    result = await svc.reverse_accrual_for_booking(
        organization_id=org_id,
        booking_id=str(booking_id),
        triggered_by=current_user["email"],
        trigger="ops_manual_reverse",
    )
    return result


@router.post("/supplier-accruals/{booking_id}/adjust")
async def adjust_supplier_accrual(
    booking_id: str,
    payload: SupplierAccrualAdjustRequest,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    """Manually adjust supplier accrual for a booking.

    Thin wrapper around SupplierAccrualService.adjust_accrual_for_booking.
    """
    org_id = current_user["organization_id"]
    from app.services.supplier_accrual import SupplierAccrualService

    svc = SupplierAccrualService(db)
    result = await svc.adjust_accrual_for_booking(
        organization_id=org_id,
        booking_id=str(booking_id),
        new_sell=payload.new_sell,
        new_commission=payload.new_commission,
        triggered_by=current_user["email"],
        trigger=payload.trigger or "ops_manual_adjust",
    )
    return result




# ============================================================================
# Phase 1.4: Statement & Exposure APIs
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
    """
    Get account statement (movement history)
    
    Auth: admin|ops|super_admin
    Query: from, to (ISO datetime), limit
    Sorting: posted_at asc (statement logic)
    """
    org_id = current_user["organization_id"]
    
    # Verify account exists and belongs to org
    account = await db.finance_accounts.find_one({
        "_id": account_id,
        "organization_id": org_id,
    })
    if not account:
        raise AppError(
            status_code=404,
            code="account_not_found",
            message=f"Account {account_id} not found",
        )
    
    currency = account["currency"]
    
    # Calculate opening balance (if from_date specified)
    opening_balance = 0.0
    if from_date:
        # Get all entries before from_date
        entries_before = await db.ledger_entries.find({
            "organization_id": org_id,
            "account_id": account_id,
            "currency": currency,
            "posted_at": {"$lt": from_date},
        }).to_list(length=10000)
        
        # Apply balance rules
        account_type = account.get("type")
        total_debit = sum(e["amount"] for e in entries_before if e["direction"] == "debit")
        total_credit = sum(e["amount"] for e in entries_before if e["direction"] == "credit")
        
        if account_type == "agency":
            opening_balance = total_debit - total_credit
        elif account_type == "platform":
            opening_balance = total_credit - total_debit
        else:
            opening_balance = total_debit - total_credit
    
    # Get entries for statement period
    query = {
        "organization_id": org_id,
        "account_id": account_id,
        "currency": currency,
    }
    
    if from_date:
        query["posted_at"] = {"$gte": from_date}
    if to_date:
        if "posted_at" not in query:
            query["posted_at"] = {}
        query["posted_at"]["$lte"] = to_date
    
    cursor = db.ledger_entries.find(query).sort("posted_at", 1).limit(limit)
    entries = await cursor.to_list(length=limit)
    
    # Build statement items
    items = []
    running_balance = opening_balance
    
    for entry in entries:
        # Apply delta based on direction and account type
        account_type = account.get("type")
        if account_type == "agency":
            delta = entry["amount"] if entry["direction"] == "debit" else -entry["amount"]
        elif account_type == "platform":
            delta = entry["amount"] if entry["direction"] == "credit" else -entry["amount"]
        else:
            delta = entry["amount"] if entry["direction"] == "debit" else -entry["amount"]
        
        running_balance += delta
        
        items.append(
            StatementItem(
                posted_at=entry["posted_at"],
                direction=entry["direction"],
                amount=entry["amount"],
                event=entry["event"],
                source=entry["source"],
                memo=entry.get("memo", ""),
            )
        )
    
    closing_balance = running_balance
    
    return AccountStatement(
        account_id=account_id,
        currency=currency,
        opening_balance=opening_balance,
        closing_balance=closing_balance,
        items=items,
    )


@router.get("/exposure", response_model=ExposureResponse)
async def get_exposure_dashboard(
    limit: int = Query(50, ge=1, le=200),
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    """
    Get exposure dashboard for all agencies
    
    Auth: admin|ops|super_admin
    Shows: agency exposure vs credit limit
    Status: ok | near_limit | over_limit
    
    Note: Implementation simplified - aging logic removed
    """
    # Return empty response since aging logic was removed
    # This function needs to be properly implemented based on requirements
    return ExposureResponse(items=[])


@router.get("/exposure/{agency_id}/entries")
async def get_exposure_entries(
    agency_id: str,
    bucket: str = Query("all", regex="^(all|0_30|31_60|61_plus)$"),
    limit: int = Query(200, ge=1, le=500),
    cursor: Optional[str] = None,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    """Drilldown endpoint: list ledger entries contributing to exposure/aging.

    Bucket semantics (age_days):
    - 0_30: age_days <= 30
    - 31_60: 31 <= age_days <= 60
    - 61_plus: age_days >= 61
    - all: no additional filter
    """
    org_id = current_user["organization_id"]

    # Find agency finance account (reuse exposure logic assumptions)
    account = await db.finance_accounts.find_one(
        {
            "organization_id": org_id,
            "type": "agency",
            "owner_id": agency_id,
        }
    )
    if not account:
        raise AppError(
            status_code=404,
            code="account_not_found",
            message="Finance account for agency not found",
        )

    account_id = account["_id"]
    currency = account.get("currency", "EUR")

    today = now_utc().date()

    # Basic query for ledger entries
    q: dict[str, Any] = {
        "organization_id": org_id,
        "account_id": account_id,
        "currency": currency,
    }

    cursor_q = db.ledger_entries.find(q).sort("posted_at", -1).limit(limit)
    raw_entries = await cursor_q.to_list(length=limit)

    items: list[dict[str, Any]] = []
    for entry in raw_entries:
        posted_at = entry.get("posted_at") or entry.get("occurred_at")
        if not posted_at:
            continue
        age_days = (today - posted_at.date()).days

        # Bucket filter
        if bucket == "0_30" and age_days > 30:
            continue
        if bucket == "31_60" and not (31 <= age_days <= 60):
            continue
        if bucket == "61_plus" and age_days < 61:
            continue

        amount = float(entry.get("amount", 0.0) or 0.0)
        direction = entry.get("direction") or "debit"

        # Source mapping
        booking_id = entry.get("booking_id")
        source_type = entry.get("source_type") or None
        source_id = entry.get("source_id") or None

        if booking_id:
            source_type = "booking"
            source_id = booking_id
        elif not source_type:
            source_type = "unknown"

        item = {
            "ledger_entry_id": str(entry.get("_id")),
            "posted_at": posted_at,
            "age_days": age_days,
            "amount": amount,
            "direction": direction,
            "source_type": source_type,
            "source_id": source_id,
            "booking_id": booking_id,
            "due_date": entry.get("due_date"),
            "note": entry.get("memo") or entry.get("note") or "",
        }
        items.append(item)

    return {
        "agency_id": agency_id,
        "currency": currency,
        "items": items,
    }

@router.post("/payments", response_model=Payment, status_code=201)
async def create_manual_payment(
    payload: PaymentCreate,
    current_user=Depends(require_roles(["admin", "ops", "super_admin"])),
    db=Depends(get_db),
):
    """
    Create manual payment entry
    
    Auth: admin|ops|super_admin
    Behavior:
    1. Create payment document
    2. Create ledger posting (agency credit, platform debit)
    3. Update balances automatically via posting service
    """
    org_id = current_user["organization_id"]
    
    # Validate amount
    if payload.amount <= 0:
        raise AppError(
            status_code=422,
            code="validation_error",
            message="Amount must be > 0",
        )
    
    # Verify account exists
    account = await db.finance_accounts.find_one({
        "_id": payload.account_id,
        "organization_id": org_id,
    })
    if not account:
        raise AppError(
            status_code=404,
            code="account_not_found",
            message=f"Account {payload.account_id} not found",
        )
    
    # Currency mismatch check
    if account["currency"] != payload.currency:
        raise AppError(
            status_code=409,
            code="currency_mismatch",
            message=f"Account currency {account['currency']} != payment currency {payload.currency}",
        )
    
    # Create payment document
    import uuid
    payment_id = f"pay_{uuid.uuid4()}"
    now = now_utc()
    received_at = payload.received_at or now
    
    payment_doc = {
        "_id": payment_id,
        "organization_id": org_id,
        "account_id": payload.account_id,
        "currency": payload.currency,
        "amount": payload.amount,
        "method": payload.method,
        "reference": payload.reference,
        "received_at": received_at,
        "created_at": now,
        "created_by_email": current_user["email"],
    }
    
    await db.payments.insert_one(payment_doc)
    
    # Create ledger posting
    # Payment: agency pays platform (credit agency, debit platform)
    # Get platform account
    platform_account = await db.finance_accounts.find_one({
        "organization_id": org_id,
        "type": "platform",
    })
    
    if platform_account:
        from app.services.ledger_posting import LedgerPostingService, PostingMatrixConfig
        
        lines = PostingMatrixConfig.get_payment_received_lines(
            agency_account_id=payload.account_id,
            platform_account_id=platform_account["_id"],
            payment_amount=payload.amount,
        )
        
        await LedgerPostingService.post_event(
            organization_id=org_id,
            source_type="payment",
            source_id=payment_id,
            event="PAYMENT_RECEIVED",
            currency=payload.currency,
            lines=lines,
            occurred_at=received_at,
            created_by=current_user["email"],
        )
    
    return Payment(
        payment_id=payment_id,
        organization_id=org_id,
        account_id=payload.account_id,
        currency=payload.currency,
        amount=payload.amount,
        method=payload.method,
        reference=payload.reference,
        received_at=received_at,
        created_at=now,
        created_by_email=current_user["email"],
    )
