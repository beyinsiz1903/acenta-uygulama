from __future__ import annotations

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
