from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, EmailStr, Field


class Traveller(BaseModel):
    first_name: str
    last_name: str


class Customer(BaseModel):
    name: str
    email: EmailStr


class BookingCreateRequest(BaseModel):
    quote_id: str
    customer: Customer
    travellers: List[Traveller] = Field(min_length=1)
    notes: Optional[str] = None


BookingStatus = Literal["PENDING", "CONFIRMED"]


class BookingCreateResponse(BaseModel):
    booking_id: str
    status: BookingStatus
    voucher_status: Literal["pending", "ready"] = "pending"
    finance_flags: Optional[dict] = None


class BookingListItem(BaseModel):
    booking_id: str
    status: str
    created_at: datetime
    currency: Optional[str] = None
    amount_sell: Optional[float] = None
    check_in: Optional[str] = None
    check_out: Optional[str] = None
    primary_guest_name: Optional[str] = None
    product_name: Optional[str] = None


class BookingListResponse(BaseModel):
    items: List[BookingListItem]
