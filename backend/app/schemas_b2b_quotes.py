from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional, Literal, Dict, Any

from pydantic import BaseModel, Field, conint, constr

Currency = constr(min_length=3, max_length=3)


class QuoteItemRequest(BaseModel):
    product_id: str
    room_type_id: str
    rate_plan_id: str
    check_in: date
    check_out: date
    occupancy: conint(ge=1, le=8) = 2


class QuoteCreateRequest(BaseModel):
    channel_id: str
    items: List[QuoteItemRequest] = Field(min_length=1)
    client_context: Optional[Dict[str, Any]] = None


class PriceRestriction(BaseModel):
    min_stay: Optional[int] = None
    stop_sell: bool = False
    allotment_available: Optional[int] = None


class PricingTrace(BaseModel):
    applied_rules: List[str] = []
    fx: Optional[Dict[str, Any]] = None
    rule_effects: Optional[List[Dict[str, Any]]] = None


class QuoteOffer(BaseModel):
    item_key: str
    currency: Currency
    net: float
    sell: float
    restrictions: PriceRestriction
    trace: PricingTrace


class QuoteCreateResponse(BaseModel):
    quote_id: str
    expires_at: datetime
    offers: List[QuoteOffer]
