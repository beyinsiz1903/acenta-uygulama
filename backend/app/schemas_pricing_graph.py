from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class PricingGraphStepOut(BaseModel):
    level: int
    tenant_id: Optional[str] = None
    node_type: Literal["seller", "reseller", "buyer"]
    rule_id: Optional[str] = None
    markup_pct: float
    base_amount: float
    delta_amount: float
    amount_after: float
    currency: str
    notes: list[str] = Field(default_factory=list)


class PricingGraphTraceResponse(BaseModel):
    source: Literal["booking", "search_session"]
    organization_id: str
    buyer_tenant_id: Optional[str] = None
    booking_id: Optional[str] = None
    session_id: Optional[str] = None
    offer_token: Optional[str] = None

    currency: Optional[str] = None
    base_amount: Optional[float] = None
    final_amount: Optional[float] = None
    applied_total_markup_pct: Optional[float] = None

    model_version: Optional[str] = None

    graph_path: list[str] = Field(default_factory=list)
    pricing_rule_ids: list[str] = Field(default_factory=list)

    steps: list[PricingGraphStepOut] = Field(default_factory=list)

    notes: list[str] = Field(default_factory=list)
