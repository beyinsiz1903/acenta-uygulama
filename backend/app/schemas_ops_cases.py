from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class OpsCaseBase(BaseModel):
    booking_id: str = Field(..., description="Related booking id")
    type: str = Field(
        ...,
        pattern="^(cancel|amend|refund|payment_followup|voucher_issue|missing_docs|supplier_approval|other)$",
    )
    source: str = Field(
        ..., pattern="^(guest_portal|ops_panel|system)$", description="Origin of the case"
    )
    status: str = Field(
        "open",
        pattern="^(open|waiting|in_progress|closed)$",
        description="Lifecycle status of the case",
    )
    waiting_on: Optional[str] = Field(
        None,
        pattern="^(customer|supplier|internal|payment_gateway)$",
        description="Who we are waiting on, if status=waiting",
    )
    note: Optional[str] = Field(None, max_length=5000)


class OpsCaseCreate(OpsCaseBase):
    pass


class OpsCaseUpdate(BaseModel):
    status: Optional[str] = Field(
        None,
        pattern="^(open|waiting|in_progress|closed)$",
    )
    waiting_on: Optional[str] = Field(
        None,
        pattern="^(customer|supplier|internal|payment_gateway)$",
    )
    note: Optional[str] = Field(None, max_length=5000)


class OpsCaseOut(BaseModel):
    case_id: str
    booking_id: str
    organization_id: str
    type: str
    source: str
    status: str
    waiting_on: Optional[str] = None
    note: Optional[str] = None
    booking_code: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None

    class Config:
        arbitrary_types_allowed = True
