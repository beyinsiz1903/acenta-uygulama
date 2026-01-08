from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


BookingAmendStatus = Literal["PROPOSED", "CONFIRMED", "EXPIRED"]


class BookingAmendSnapshot(BaseModel):
    """Minimal before/after financial snapshot used in amend flow.

    Dates are kept as ISO strings (YYYY-MM-DD) to mirror Mongo booking docs
    without adding date parsing concerns to the frontend.
    """

    check_in: str
    check_out: str
    sell: float
    sell_eur: float
    currency: str


class BookingAmendDelta(BaseModel):
    sell: float = Field(description="Delta in selling currency (after - before)")
    sell_eur: float = Field(description="Delta in EUR (after - before)")


class BookingAmendmentOut(BaseModel):
    """API-friendly view of a booking_amendments document."""

    amend_id: str
    booking_id: str
    status: BookingAmendStatus
    before: BookingAmendSnapshot
    after: BookingAmendSnapshot
    delta: BookingAmendDelta


class BookingAmendQuoteRequest(BaseModel):
    """Quote request for a booking amendment (date change)."""

    check_in: date
    check_out: date
    request_id: str = Field(min_length=1, description="Idempotency key for proposal")


class BookingAmendConfirmRequest(BaseModel):
    """Confirm a previously created amendment proposal."""

    amend_id: str = Field(min_length=1)


class BookingAmendQuoteResponse(BookingAmendmentOut):
    """Alias for response model clarity."""

    pass


class BookingAmendConfirmResponse(BookingAmendmentOut):
    """Alias for confirm response; shape identical to amendment view."""

    pass
