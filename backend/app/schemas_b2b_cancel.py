from __future__ import annotations

from typing import Optional, Literal
from pydantic import BaseModel, Field, validator, constr

Currency = constr(min_length=3, max_length=3)


class CancelRequest(BaseModel):
    reason: Optional[str] = None
    requested_refund_currency: Optional[Currency] = None
    requested_refund_amount: Optional[float] = Field(default=None)

    @validator("requested_refund_amount")
    def non_negative_amount(cls, v):  # type: ignore[override]
        if v is not None and v < 0:
            raise ValueError("requested_refund_amount must be non-negative")
        return v


class CancelRequestResponse(BaseModel):
    case_id: str
    status: Literal["open", "pending_approval"] = "open"
