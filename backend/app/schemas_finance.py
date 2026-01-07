"""
Finance / Ledger OS Schemas (Phase 1)
Double-entry ledger system for agency credit management
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional, Any
from pydantic import BaseModel, Field


# ============================================================================
# 1) Finance Accounts
# ============================================================================

class FinanceAccountCreate(BaseModel):
    """Create a finance account"""
    type: Literal["agency", "platform", "supplier"]
    owner_id: str = Field(..., description="agency_id, org_id, or supplier_id")
    code: str = Field(..., description="Unique account code per org")
    name: str
    currency: str = Field(default="EUR", description="Phase 1: single currency per account")
    status: Literal["active", "suspended"] = "active"


class FinanceAccount(BaseModel):
    """Finance account (ledger account)"""
    id: str = Field(..., alias="account_id")
    organization_id: str
    type: Literal["agency", "platform", "supplier"]
    owner_id: str
    code: str
    name: str
    currency: str
    status: Literal["active", "suspended"]
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True


class FinanceAccountListResponse(BaseModel):
    """List of finance accounts"""
    items: list[FinanceAccount]


# ============================================================================
# 2) Ledger Entries (immutable)
# ============================================================================

class LedgerEntrySource(BaseModel):
    """Source of ledger entry"""
    type: Literal["booking", "refund", "adjustment", "payment"]
    id: str


class LedgerEntryMeta(BaseModel):
    """Optional metadata for ledger entry"""
    agency_id: Optional[str] = None
    booking_id: Optional[str] = None
    channel_id: Optional[str] = None
    case_id: Optional[str] = None


class LedgerEntry(BaseModel):
    """Single ledger entry (immutable)"""
    id: str = Field(..., alias="entry_id")
    organization_id: str
    account_id: str
    currency: str
    direction: Literal["debit", "credit"]
    amount: float
    occurred_at: datetime = Field(..., description="Business event timestamp")
    posted_at: datetime = Field(..., description="System write timestamp")
    source: LedgerEntrySource
    event: str = Field(..., description="BOOKING_CONFIRMED, PAYMENT_RECEIVED, etc.")
    memo: str
    meta: LedgerEntryMeta = Field(default_factory=LedgerEntryMeta)

    class Config:
        populate_by_name = True


# ============================================================================
# 3) Ledger Postings (atomic double-entry header)
# ============================================================================

class LedgerPostingLine(BaseModel):
    """Single line in a posting"""
    account_id: str
    direction: Literal["debit", "credit"]
    amount: float


class LedgerPosting(BaseModel):
    """Posting header (idempotency + audit)"""
    id: str = Field(..., alias="posting_id")
    organization_id: str
    source: LedgerEntrySource
    event: str
    currency: str
    lines: list[LedgerPostingLine]
    checksum: str = Field(..., description="SHA256 of lines+source for integrity")
    created_at: datetime
    created_by: str = Field(default="system")

    class Config:
        populate_by_name = True


# ============================================================================
# 4) Credit Profiles
# ============================================================================

class CreditProfileUpdate(BaseModel):
    """Update credit profile"""
    limit: float = Field(..., ge=0)
    soft_limit: Optional[float] = Field(None, ge=0)
    payment_terms: Literal["PREPAY", "NET7", "NET14", "NET30"]
    status: Literal["active", "suspended"] = "active"


class CreditProfile(BaseModel):
    """Agency credit profile"""
    id: str = Field(..., alias="profile_id")
    organization_id: str
    agency_id: str
    currency: str
    limit: float
    soft_limit: Optional[float] = None
    payment_terms: Literal["PREPAY", "NET7", "NET14", "NET30"]
    status: Literal["active", "suspended"]
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True


class CreditProfileListResponse(BaseModel):
    """List of credit profiles"""
    items: list[CreditProfile]


# ============================================================================
# 5) Account Balances (derived/cached)
# ============================================================================

class AccountBalance(BaseModel):
    """Cached account balance"""
    id: str = Field(..., alias="balance_id")
    organization_id: str
    account_id: str
    currency: str
    balance: float = Field(..., description="Net balance (debit - credit for agencies)")
    as_of: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True


# ============================================================================
# 6) Payments
# ============================================================================

class PaymentCreate(BaseModel):
    """Create manual payment entry"""
    account_id: str
    currency: str
    amount: float = Field(..., gt=0)
    method: Literal["bank_transfer", "cash", "virtual"]
    reference: str = Field(..., description="Bank reference or payment ID")
    received_at: Optional[datetime] = None  # defaults to now


class Payment(BaseModel):
    """Payment record"""
    id: str = Field(..., alias="payment_id")
    organization_id: str
    account_id: str
    currency: str
    amount: float
    method: Literal["bank_transfer", "cash", "virtual"]
    reference: str
    received_at: datetime
    created_at: datetime
    created_by_email: str

    class Config:
        populate_by_name = True


# ============================================================================
# 7) Statement & Exposure (API responses)
# ============================================================================

class StatementItem(BaseModel):
    """Single line in account statement"""
    posted_at: datetime
    direction: Literal["debit", "credit"]
    amount: float
    event: str
    source: LedgerEntrySource
    memo: str


class AccountStatement(BaseModel):
    """Account statement response"""
    account_id: str
    currency: str
    opening_balance: float
    closing_balance: float
    items: list[StatementItem]


class ExposureItem(BaseModel):
    """Single agency exposure item"""
    agency_id: str
    agency_name: str
    currency: str
    exposure: float = Field(..., description="Total debit - credit")
    credit_limit: float
    soft_limit: Optional[float] = None
    payment_terms: str
    status: Literal["ok", "near_limit", "over_limit"]


class ExposureResponse(BaseModel):
    """Exposure dashboard response"""
    items: list[ExposureItem]


# ============================================================================
# 8) Generic responses
# ============================================================================

class OkResponse(BaseModel):
    """Generic OK response"""
    ok: bool = True
    message: Optional[str] = None
