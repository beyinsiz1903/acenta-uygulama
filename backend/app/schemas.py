from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthUser(BaseModel):
    id: str
    email: str
    name: str | None = None
    roles: list[str] = Field(default_factory=list)
    organization_id: str
    agency_id: str | None = None
    hotel_id: str | None = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUser


class CustomerIn(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None


class CustomerOut(CustomerIn):
    id: str
    created_at: datetime
    updated_at: datetime


class ProductIn(BaseModel):
    type: str = Field(description="tour|activity|accommodation|transfer")
    title: str
    description: Optional[str] = None


class ProductOut(ProductIn):
    id: str
    created_at: datetime
    updated_at: datetime


class RatePlanIn(BaseModel):
    product_id: str
    name: str
    currency: str = "TRY"
    base_price: float = 0.0
    seasons: list[dict[str, Any]] = Field(default_factory=list)  # [{start,end,price}]
    actions: list[dict[str, Any]] = Field(default_factory=list)  # [{type, value, start,end}]


    # FAZ-8: data ownership marker
    source: str = "local"  # local|pms


class RatePlanOut(RatePlanIn):
    id: str
    created_at: datetime
    updated_at: datetime


class InventoryUpsertIn(BaseModel):
    product_id: str
    date: str  # YYYY-MM-DD
    capacity_total: int

    # FAZ-8: data ownership marker
    source: str = "local"  # local|pms

    capacity_available: int
    price: Optional[float] = None
    restrictions: dict[str, Any] = Field(default_factory=lambda: {"closed": False, "cta": False, "ctd": False})


class InventoryBulkUpsertIn(BaseModel):

    # FAZ-8: data ownership marker
    source: str = "local"  # local|pms

    product_id: str
    start_date: str  # YYYY-MM-DD
    end_date: str  # YYYY-MM-DD (inclusive)
    capacity_total: int
    capacity_available: int
    price: Optional[float] = None
    closed: bool = False


class ReservationCreateIn(BaseModel):
    idempotency_key: Optional[str] = None
    product_id: str
    customer_id: str
    start_date: str
    end_date: Optional[str] = None  # if None => single date (tour/activity)
    pax: int = 1
    channel: str = "direct"  # direct|b2b|public
    agency_id: Optional[str] = None


class ReservationOut(BaseModel):
    id: str
    pnr: str
    voucher_no: str
    product_id: str
    customer_id: str
    start_date: str
    end_date: Optional[str] = None
    pax: int
    status: str
    currency: str
    total_price: float
    paid_amount: float
    due_amount: float
    channel: str
    agency_id: Optional[str] = None
    commission_amount: float = 0.0
    created_at: datetime
    updated_at: datetime


class PaymentCreateIn(BaseModel):
    reservation_id: str
    method: str = "manual"  # manual|bank_transfer|card|cash
    amount: float
    currency: str = "TRY"
    reference: Optional[str] = None
    status: str = "paid"  # paid|pending|failed


class LeadIn(BaseModel):
    source: Optional[str] = None
    customer_id: str
    notes: Optional[str] = None
    status: str = "new"  # new|contacted|won|lost
    # Kanban sıralaması için (yüksek değer = daha üstte). Opsiyonel.
    sort_index: Optional[float] = None


class LeadOut(LeadIn):
    id: str
    created_at: datetime
    updated_at: datetime


class LeadStatusPatchIn(BaseModel):
    status: str
    # Drag-drop sonrası aynı anda sütun içi sıralamayı da güncelleyebilmek için.
    sort_index: Optional[float] = None


class QuoteIn(BaseModel):
    lead_id: Optional[str] = None
    customer_id: str
    items: list[dict[str, Any]] = Field(default_factory=list)
    currency: str = "TRY"
    status: str = "draft"  # draft|sent|accepted|rejected|converted


class QuoteOut(QuoteIn):
    id: str
    total: float
    created_at: datetime
    updated_at: datetime


class QuoteConvertIn(BaseModel):
    quote_id: str
    idempotency_key: Optional[str] = None


class AgencyIn(BaseModel):
    name: str
    discount_percent: float = 0.0
    commission_percent: float = 0.0


class AgencyOut(AgencyIn):
    id: str
    created_at: datetime
    updated_at: datetime


class UserCreateIn(BaseModel):
    email: str
    name: Optional[str] = None
    password: str
    roles: list[str] = Field(default_factory=list)
    agency_id: Optional[str] = None

    hotel_id: Optional[str] = None


class HotelCreateIn(BaseModel):
    name: str
    city: Optional[str] = None
    country: Optional[str] = None
    active: bool = True


class AgencyHotelLinkCreateIn(BaseModel):
    agency_id: str
    hotel_id: str
    active: bool = True

    # FAZ-6: Commission settings
    commission_type: str = "percent"  # percent|fixed_per_booking
    commission_value: float = 0.0


class AgencyHotelLinkPatchIn(BaseModel):
    active: Optional[bool] = None

    # FAZ-6: Commission settings
    commission_type: Optional[str] = None
    commission_value: Optional[float] = None
