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
    winner_rule_id: Optional[str] = None
    winner_rule_name: Optional[str] = None
    fallback: Optional[bool] = None
    discount_group_id: Optional[str] = None
    discount_group_name: Optional[str] = None
    discount_percent: Optional[float] = None
    discount_amount: Optional[float] = None


class QuoteOffer(BaseModel):
    item_key: str
    currency: Currency
    net: float
    sell: float
    restrictions: PriceRestriction
    trace: PricingTrace
    # Money model breakdown (optional, for B2B pricing transparency)
    supplier_cost: Optional[float] = None
    base_markup_percent: Optional[float] = None
    list_sell: Optional[float] = None
    commission_rate: Optional[float] = None
    commission_amount: Optional[float] = None
    our_margin_before_coupon: Optional[float] = None


class QuoteCreateResponse(BaseModel):
    quote_id: str
    expires_at: datetime
    offers: List[QuoteOffer]
    winner_rule_id: Optional[str] = None
    winner_rule_name: Optional[str] = None
    pricing_trace: Optional[Dict[str, Any]] = None
