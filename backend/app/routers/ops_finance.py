"""
Finance OS Phase 1.2: Basic Finance APIs
Ops/Admin endpoints for account and credit profile management
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Literal, Optional
from datetime import datetime

from app.db import get_db
from app.auth import require_roles, get_current_user
from app.errors import ErrorResponse
from app.utils import now_utc
from app.schemas_finance import (
    FinanceAccount,
    FinanceAccountCreate,
    FinanceAccountListResponse,
    CreditProfile,
    CreditProfileUpdate,
    CreditProfileListResponse,
)

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
        raise HTTPException(
            status_code=409,
            detail=ErrorResponse(
                code="account_code_exists",
                message=f"Account with code '{payload.code}' already exists",
            ).model_dump(),
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
    
    # Validation: soft_limit >= limit
    if payload.soft_limit is not None and payload.soft_limit < payload.limit:
        raise HTTPException(
            status_code=422,
            detail=ErrorResponse(
                code="validation_error",
                message="soft_limit must be >= limit",
            ).model_dump(),
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
    profile = await _upsert_credit_profile(
        db,
        current_user["organization_id"],
        agency_id,
        payload,
    )
    
    return profile
