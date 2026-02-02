from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.routers.offers import CanonicalHotelOfferOut


class SupplierWarningOut(BaseModel):
    scope: str = Field("supplier", const=True)
    supplier_code: str
    code: str
    message: str
    retryable: bool
    http_status: Optional[int] = None
    timeout_ms: Optional[int] = None
    duration_ms: Optional[int] = None


class OfferSearchRequest(BaseModel):
    destination: str
    check_in: Any
    check_out: Any
    adults: int
    children: int
    supplier_codes: Optional[List[str]] = None


class OfferSearchResponse(BaseModel):
    session_id: str
    expires_at: str
    offers: List[CanonicalHotelOfferOut] = Field(default_factory=list)
    warnings: Optional[List[SupplierWarningOut]] = None
