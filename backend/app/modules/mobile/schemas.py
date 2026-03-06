from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class MobileAuthMeResponse(BaseModel):
    id: str
    email: str
    name: Optional[str] = None
    roles: list[str] = Field(default_factory=list)
    organization_id: str
    tenant_id: Optional[str] = None
    current_session_id: Optional[str] = None
    allowed_tenant_ids: list[str] = Field(default_factory=list)


class MobileDashboardSummary(BaseModel):
    bookings_today: int
    bookings_month: int
    revenue_month: float
    currency: str = "TRY"


class MobileBookingSummary(BaseModel):
    id: str
    status: str
    total_price: float
    currency: str
    customer_name: Optional[str] = None
    hotel_name: Optional[str] = None
    check_in: Optional[str] = None
    check_out: Optional[str] = None
    source: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class MobileBookingDetail(MobileBookingSummary):
    tenant_id: Optional[str] = None
    agency_id: Optional[str] = None
    hotel_id: Optional[str] = None
    booking_ref: Optional[str] = None
    offer_ref: Optional[str] = None
    notes: Optional[str] = None


class MobileBookingsListResponse(BaseModel):
    total: int
    items: list[MobileBookingSummary] = Field(default_factory=list)


class MobileBookingCreate(BaseModel):
    amount: float = Field(default=0, ge=0)
    currency: str = Field(default="TRY", min_length=3, max_length=3)
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    guest_name: Optional[str] = None
    hotel_id: Optional[str] = None
    hotel_name: Optional[str] = None
    supplier_id: Optional[str] = None
    booking_ref: Optional[str] = None
    offer_ref: Optional[str] = None
    check_in: Optional[str] = None
    check_out: Optional[str] = None
    notes: Optional[str] = Field(default=None, max_length=1000)
    pricing: Optional[dict[str, Any]] = None
    occupancy: Optional[dict[str, Any]] = None
    source: str = Field(default="mobile", min_length=3, max_length=50)


class MobileStatusCount(BaseModel):
    status: str
    count: int


class MobileDailyRevenue(BaseModel):
    day: str
    revenue: float
    count: int


class MobileReportsSummary(BaseModel):
    total_bookings: int
    total_revenue: float
    currency: str = "TRY"
    status_breakdown: list[MobileStatusCount] = Field(default_factory=list)
    daily_sales: list[MobileDailyRevenue] = Field(default_factory=list)