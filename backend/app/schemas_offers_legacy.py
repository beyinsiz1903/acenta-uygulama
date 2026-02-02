from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# NOTE: CanonicalHotelOfferOut is imported lazily in routers/offers.py to avoid circular import.
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - only for type checkers
    from app.routers.offers import CanonicalHotelOfferOut
else:
    CanonicalHotelOfferOut = dict  # runtime placeholder; real shape handled in router


class SupplierWarningOut(BaseModel):
    scope: str = "supplier"
    supplier_code: str
    code: str
    message: str
    retryable: bool
    http_status: Optional[int] = None
    timeout_ms: Optional[int] = None
    duration_ms: Optional[int] = None


from datetime import date


class OfferSearchRequest(BaseModel):
    destination: str
    check_in: date
    check_out: date
    adults: int
    children: int
    supplier_codes: Optional[List[str]] = None


class OfferSearchResponse(BaseModel):
    session_id: str
    expires_at: str
    offers: List[CanonicalHotelOfferOut] = Field(default_factory=list)
    warnings: Optional[List[SupplierWarningOut]] = None
