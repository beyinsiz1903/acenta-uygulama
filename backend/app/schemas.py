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
    organization: Optional[dict] = None  # FAZ-1: Organization with merged features


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
    # Phase-2: simple package / feature flag for hotel
    package: str = Field(default="basic", pattern="^(basic|pro|channel)$")


class HotelPackagePatchIn(BaseModel):
    package: str = Field(..., pattern="^(basic|pro|channel)$")




class HotelForceSalesOverrideIn(BaseModel):
    force_sales_open: bool
    ttl_hours: Optional[int] = Field(default=6, ge=1, le=48)
    reason: Optional[str] = Field(default=None, max_length=280)


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



class BookingPublicView(BaseModel):
    id: str
    code: str
    status: str
    status_tr: str
    status_en: str
    hotel_name: str | None = None
    destination: str | None = None
    agency_name: str | None = None
    guest_name: str | None = None
    guest_email: str | None = None
    guest_phone: str | None = None
    check_in_date: str | None = None
    check_out_date: str | None = None
    nights: int | None = None


class AgencyHotelCatalogCommission(BaseModel):
    """Commission config for agency-hotel catalog.

    MVP: only "percent" type is supported, but schema is flexible for future.
    """

    type: str = Field("percent", description="percent|absolute")
    value: float = Field(0.0, ge=0.0, le=99.0)
    currency: str = Field("TRY", max_length=8)


class AgencyHotelPricingPolicy(BaseModel):
    """Pricing policy for public/agency-facing hotel prices.

    MVP: mode="pms_plus" and markup_percent is used.
    """

    mode: str = Field("pms_plus", description="pms|pms_plus|net")
    markup_percent: float = Field(0.0, ge=0.0, le=100.0)
    markup_absolute: float | None = Field(default=None, ge=0.0)
    currency: str = Field("TRY", max_length=8)


class AgencyHotelBookingPolicy(BaseModel):
    """Booking behaviour for public bookings.

    MVP: confirmation_mode="pending", payment_mode="none".
    """

    confirmation_mode: str = Field("pending", description="pending|instant")
    payment_mode: str = Field("none", description="none|link|bank")


class AgencyHotelCatalogUpsertIn(BaseModel):
    """Upsert payload for agency-hotel catalog config.

    MVP constraints (enforced at router level):
    - commission.type is effectively "percent"
    - pricing_policy.mode is effectively "pms_plus" and markup_percent is used
    """

    sale_enabled: bool = True
    visibility: str = Field("private", pattern="^(private|public)$")

    commission: AgencyHotelCatalogCommission = Field(default_factory=AgencyHotelCatalogCommission)
    min_nights: int = Field(1, ge=1, le=30)

    pricing_policy: AgencyHotelPricingPolicy = Field(default_factory=AgencyHotelPricingPolicy)
    booking_policy: AgencyHotelBookingPolicy | None = None

    # Slugs are reserved for public booking URLs (Phase 2.0+). Not used in MVP UI.
    public_slug: str | None = Field(default=None, max_length=120)
    public_hotel_slug: str | None = Field(default=None, max_length=120)

