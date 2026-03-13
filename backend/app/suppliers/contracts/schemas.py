"""Normalized supplier request/response schemas.

Every supplier adapter maps its proprietary format into these canonical models.
The orchestrator, aggregator, and pricing engine all operate on these schemas.
"""
from __future__ import annotations

from datetime import datetime, date
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Context — passed to every adapter call
# ---------------------------------------------------------------------------

class SupplierContext(BaseModel):
    request_id: str
    organization_id: str
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    channel: str = "direct"  # direct | b2b | api | widget
    currency: str = "TRY"
    locale: str = "tr"
    timeout_ms: int = 8000
    correlation_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Supplier type enum
# ---------------------------------------------------------------------------

class SupplierProductType(str, Enum):
    FLIGHT = "flight"
    HOTEL = "hotel"
    TOUR = "tour"
    INSURANCE = "insurance"
    TRANSPORT = "transport"
    TRANSFER = "transfer"
    ACTIVITY = "activity"


# ---------------------------------------------------------------------------
# Search — generic + type-specific items
# ---------------------------------------------------------------------------

class SearchRequest(BaseModel):
    supplier_codes: List[str] = Field(default_factory=list, description="Empty = all active suppliers")
    product_type: SupplierProductType
    destination: Optional[str] = None
    origin: Optional[str] = None
    check_in: Optional[date] = None
    check_out: Optional[date] = None
    departure_date: Optional[date] = None
    return_date: Optional[date] = None
    adults: int = 1
    children: int = 0
    children_ages: List[int] = Field(default_factory=list)
    rooms: int = 1
    filters: Dict[str, Any] = Field(default_factory=dict)
    sort_by: str = "price_asc"
    page: int = 1
    page_size: int = 20


class SearchItem(BaseModel):
    """Canonical search result item. Extended by type-specific subclasses."""
    item_id: str
    supplier_code: str
    supplier_item_id: str
    product_type: SupplierProductType
    name: str
    description: Optional[str] = None
    currency: str = "TRY"
    supplier_price: float  # net cost from supplier
    sell_price: float  # after markup
    tax_amount: float = 0.0
    commission_amount: float = 0.0
    images: List[str] = Field(default_factory=list)
    rating: Optional[float] = None
    available: bool = True
    cancellation_policy: Optional[str] = None
    supplier_metadata: Dict[str, Any] = Field(default_factory=dict)
    cached: bool = False
    fetched_at: Optional[datetime] = None


class FlightSearchItem(SearchItem):
    product_type: SupplierProductType = SupplierProductType.FLIGHT
    airline: Optional[str] = None
    flight_number: Optional[str] = None
    departure_airport: Optional[str] = None
    arrival_airport: Optional[str] = None
    departure_time: Optional[datetime] = None
    arrival_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    stops: int = 0
    cabin_class: Optional[str] = None
    baggage_allowance: Optional[str] = None


class HotelSearchItem(SearchItem):
    product_type: SupplierProductType = SupplierProductType.HOTEL
    hotel_name: Optional[str] = None
    star_rating: Optional[int] = None
    room_type: Optional[str] = None
    board_type: Optional[str] = None  # RO, BB, HB, FB, AI
    check_in: Optional[date] = None
    check_out: Optional[date] = None
    nights: Optional[int] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class TourSearchItem(SearchItem):
    product_type: SupplierProductType = SupplierProductType.TOUR
    tour_code: Optional[str] = None
    duration_days: Optional[int] = None
    departure_date: Optional[date] = None
    return_date: Optional[date] = None
    included_services: List[str] = Field(default_factory=list)
    itinerary_summary: Optional[str] = None
    guide_language: Optional[str] = None
    min_participants: Optional[int] = None
    max_participants: Optional[int] = None


class InsuranceSearchItem(SearchItem):
    product_type: SupplierProductType = SupplierProductType.INSURANCE
    coverage_type: Optional[str] = None  # basic, standard, premium
    coverage_amount: Optional[float] = None
    deductible: Optional[float] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    covered_regions: List[str] = Field(default_factory=list)
    policy_terms_url: Optional[str] = None


class TransportSearchItem(SearchItem):
    product_type: SupplierProductType = SupplierProductType.TRANSPORT
    vehicle_type: Optional[str] = None  # sedan, minivan, bus, vip
    capacity: Optional[int] = None
    pickup_location: Optional[str] = None
    dropoff_location: Optional[str] = None
    pickup_time: Optional[datetime] = None
    estimated_duration_minutes: Optional[int] = None
    distance_km: Optional[float] = None



class TransferSearchItem(SearchItem):
    product_type: SupplierProductType = SupplierProductType.TRANSFER
    vehicle_type: Optional[str] = None
    capacity: Optional[int] = None
    pickup_location: Optional[str] = None
    dropoff_location: Optional[str] = None
    pickup_time: Optional[datetime] = None
    estimated_duration_minutes: Optional[int] = None
    distance_km: Optional[float] = None


class ActivitySearchItem(SearchItem):
    product_type: SupplierProductType = SupplierProductType.ACTIVITY
    activity_code: Optional[str] = None
    duration_hours: Optional[float] = None
    activity_date: Optional[date] = None
    location_name: Optional[str] = None
    included_services: List[str] = Field(default_factory=list)
    min_participants: Optional[int] = None
    max_participants: Optional[int] = None
    guide_language: Optional[str] = None


class SearchResult(BaseModel):
    request_id: str
    product_type: SupplierProductType
    total_items: int = 0
    items: List[SearchItem] = Field(default_factory=list)
    suppliers_queried: List[str] = Field(default_factory=list)
    suppliers_failed: List[str] = Field(default_factory=list)
    search_duration_ms: int = 0
    from_cache: bool = False
    degraded: bool = False  # True if some suppliers failed


# ---------------------------------------------------------------------------
# Availability
# ---------------------------------------------------------------------------

class AvailabilityRequest(BaseModel):
    supplier_code: str
    supplier_item_id: str
    product_type: SupplierProductType
    check_in: Optional[date] = None
    check_out: Optional[date] = None
    availability_date: Optional[date] = None  # Renamed from 'date' to avoid type shadowing
    adults: int = 1
    children: int = 0
    quantity: int = 1


class AvailabilitySlot(BaseModel):
    date: date
    available: bool
    remaining_units: Optional[int] = None
    price: Optional[float] = None
    currency: str = "TRY"
    restrictions: Dict[str, Any] = Field(default_factory=dict)


class AvailabilityResult(BaseModel):
    supplier_code: str
    supplier_item_id: str
    available: bool
    slots: List[AvailabilitySlot] = Field(default_factory=list)
    checked_at: datetime
    valid_until: Optional[datetime] = None
    supplier_metadata: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------

class PricingRequest(BaseModel):
    supplier_code: str
    supplier_item_id: str
    product_type: SupplierProductType
    check_in: Optional[date] = None
    check_out: Optional[date] = None
    adults: int = 1
    children: int = 0
    quantity: int = 1
    promo_code: Optional[str] = None


class PriceBreakdown(BaseModel):
    base_price: float
    tax: float = 0.0
    service_fee: float = 0.0
    discount: float = 0.0
    total: float
    currency: str = "TRY"
    per_night: Optional[float] = None
    per_person: Optional[float] = None


class PricingResult(BaseModel):
    supplier_code: str
    supplier_item_id: str
    supplier_price: PriceBreakdown  # net cost
    sell_price: Optional[PriceBreakdown] = None  # after markup (filled by pricing engine)
    valid_until: Optional[datetime] = None
    price_guarantee: bool = False
    priced_at: datetime
    currency: str = "TRY"
    supplier_metadata: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Hold (reservation)
# ---------------------------------------------------------------------------

class HoldRequest(BaseModel):
    supplier_code: str
    supplier_item_id: str
    product_type: SupplierProductType
    guests: List[Dict[str, Any]] = Field(default_factory=list)
    contact: Dict[str, Any] = Field(default_factory=dict)
    special_requests: Optional[str] = None
    pricing_snapshot: Optional[PriceBreakdown] = None


class HoldResult(BaseModel):
    supplier_code: str
    hold_id: str  # supplier-side hold reference
    status: str  # held | failed | pending
    expires_at: Optional[datetime] = None
    hold_price: Optional[PriceBreakdown] = None
    supplier_metadata: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Confirm
# ---------------------------------------------------------------------------

class ConfirmRequest(BaseModel):
    supplier_code: str
    hold_id: str
    payment_reference: Optional[str] = None
    idempotency_key: str


class ConfirmResult(BaseModel):
    supplier_code: str
    supplier_booking_id: str
    status: str  # confirmed | rejected | pending
    confirmation_code: Optional[str] = None
    voucher_data: Dict[str, Any] = Field(default_factory=dict)
    confirmed_at: Optional[datetime] = None
    supplier_metadata: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------

class CancelRequest(BaseModel):
    supplier_code: str
    supplier_booking_id: str
    reason: Optional[str] = None
    idempotency_key: str


class CancelResult(BaseModel):
    supplier_code: str
    supplier_booking_id: str
    status: str  # cancelled | pending | rejected
    penalty_amount: float = 0.0
    refund_amount: float = 0.0
    currency: str = "TRY"
    cancelled_at: Optional[datetime] = None
    supplier_metadata: Dict[str, Any] = Field(default_factory=dict)



# ---------------------------------------------------------------------------
# Unified Booking Request / Response — canonical models for real suppliers
# ---------------------------------------------------------------------------

class Traveller(BaseModel):
    """Individual traveller in a booking."""
    title: str = ""  # Mr, Mrs, Ms
    first_name: str
    last_name: str
    date_of_birth: Optional[str] = None
    nationality: Optional[str] = None
    passport_number: Optional[str] = None
    passport_expiry: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    is_lead: bool = False
    type: str = "adult"  # adult, child, infant


class ContactInfo(BaseModel):
    email: str
    phone: str
    name: Optional[str] = None


class BillingInfo(BaseModel):
    company_name: Optional[str] = None
    tax_id: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None


class UnifiedBookingRequest(BaseModel):
    """Canonical booking request — transformed into supplier-specific payloads."""
    # Selection
    supplier_code: str
    supplier_item_id: str
    product_type: SupplierProductType
    # Travellers
    travellers: List[Traveller] = Field(default_factory=list)
    contact: ContactInfo
    billing: Optional[BillingInfo] = None
    # Agency context
    organization_id: str
    agency_id: Optional[str] = None
    agent_id: Optional[str] = None
    # Pricing
    pricing_snapshot: Optional[PriceBreakdown] = None
    expected_price: Optional[float] = None
    currency: str = "TRY"
    # Idempotency
    idempotency_key: str
    # Search reference
    search_result_id: Optional[str] = None
    # Extra
    special_requests: Optional[str] = None
    supplier_metadata: Dict[str, Any] = Field(default_factory=dict)


class SupplierCapabilityInfo(BaseModel):
    """Describes what a supplier supports in the booking lifecycle."""
    supplier_code: str
    product_types: List[str]
    supports_hold: bool = False
    supports_direct_confirm: bool = True
    supports_cancel: bool = False
    supports_pricing_check: bool = False
    requires_precheck: bool = False
    max_timeout_ms: int = 15000


class UnifiedBookingResponse(BaseModel):
    """Canonical booking response — normalized from supplier-specific responses."""
    # Internal
    internal_booking_id: str
    run_id: str
    # Supplier
    supplier_code: str
    supplier_booking_id: str
    product_type: str
    # Status
    status: str  # confirmed | failed | pending | cancelled
    # Pricing
    booked_price: Optional[float] = None
    confirmed_price: Optional[float] = None
    price_drift: Optional[float] = None
    currency: str = "TRY"
    # Travellers echo
    travellers: List[Traveller] = Field(default_factory=list)
    # Cancellation
    cancellation_deadline: Optional[datetime] = None
    cancellation_penalty: Optional[float] = None
    free_cancellation: bool = False
    # Confirmation
    confirmation_code: Optional[str] = None
    voucher_url: Optional[str] = None
    # Supplier raw
    supplier_confirmation: Dict[str, Any] = Field(default_factory=dict)
    notes: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    # Timing
    booked_at: Optional[datetime] = None
    total_duration_ms: int = 0


class PriceRevalidationResult(BaseModel):
    """Result of pre-booking price check."""
    supplier_code: str
    supplier_item_id: str
    valid: bool
    original_price: float
    current_price: float
    price_drift_amount: float = 0.0
    price_drift_pct: float = 0.0
    currency: str = "TRY"
    still_available: bool = True
    warnings: List[str] = Field(default_factory=list)
    # Decision
    can_proceed: bool = True
    requires_approval: bool = False
    abort_reason: Optional[str] = None
    checked_at: Optional[datetime] = None
