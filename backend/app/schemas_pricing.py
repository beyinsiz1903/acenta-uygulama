from __future__ import annotations

from datetime import datetime, date
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


ContractStatus = Literal["draft", "active", "archived"]
GridStatus = Literal["draft", "active", "archived"]
RuleStatus = Literal["draft", "active", "archived"]

RuleActionType = Literal["markup", "markdown", "override"]
RuleActionMode = Literal["percent", "absolute"]


# ---- Contracts ----


class PricingContractBase(BaseModel):
    code: str = Field(min_length=2, max_length=64)
    status: ContractStatus = "draft"
    supplier_id: Optional[str] = None
    agency_id: Optional[str] = None
    channel_id: Optional[str] = None
    markets: list[str] = Field(default_factory=list)
    product_ids: list[str] = Field(default_factory=list)
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None

    default_markup_type: Optional[RuleActionMode] = None  # percent | absolute
    default_markup_value: Optional[float] = None


class PricingContractCreateRequest(PricingContractBase):
    pass


class PricingContractResponse(PricingContractBase):
    contract_id: str
    organization_id: str
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime] = None
    published_by_email: Optional[str] = None


# ---- Rate grids ----


class RateGridRow(BaseModel):
    valid_from: date
    valid_to: date
    min_los: int = Field(ge=1, le=365)
    max_los: int = Field(ge=1, le=365)
    occupancy: Optional[int] = Field(default=None, ge=1, le=20)
    board: Optional[str] = Field(default=None, max_length=8)
    base_net: float = Field(ge=0)


class PricingRateGridCreateRequest(BaseModel):
    contract_id: str
    product_id: str
    rate_plan_id: str
    room_type_id: Optional[str] = None
    currency: str = Field(min_length=3, max_length=3)
    status: GridStatus = "draft"
    rows: list[RateGridRow]


class PricingRateGridResponse(PricingRateGridCreateRequest):
    grid_id: str
    organization_id: str
    created_at: datetime
    updated_at: datetime


# ---- Rules ----


class PricingRuleScope(BaseModel):
    contract_ids: list[str] = Field(default_factory=list)
    channel_ids: list[str] = Field(default_factory=list)
    agency_ids: list[str] = Field(default_factory=list)
    markets: list[str] = Field(default_factory=list)
    product_ids: list[str] = Field(default_factory=list)
    rate_plan_ids: list[str] = Field(default_factory=list)
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    booking_window_from: Optional[int] = Field(default=None, ge=0, le=3650)
    booking_window_to: Optional[int] = Field(default=None, ge=0, le=3650)


class PricingRuleAction(BaseModel):
    type: RuleActionType  # markup | markdown | override
    mode: RuleActionMode  # percent | absolute
    value: float
    min_margin: Optional[float] = None   # percent
    max_discount: Optional[float] = None # percent


class PricingRuleCreateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=64)
    status: RuleStatus = "draft"
    priority: int = 100
    scope: PricingRuleScope
    action: PricingRuleAction


class PricingRuleResponse(PricingRuleCreateRequest):
    rule_id: str
    organization_id: str
    created_at: datetime
    updated_at: datetime
    created_by_email: Optional[str] = None


# ---- Pricing trace ----


# ---- P1.2 Simple pricing rules (markup_percent only) ----


class SimpleRuleValidity(BaseModel):
    """Validity window for simple rules (P1.2 MVP).

    Semantics: from <= check_in < to  (to is exclusive).
    """

    from_: date = Field(alias="from")
    to: date

    class Config:
        allow_population_by_field_name = True


class SimpleRuleScope(BaseModel):
    agency_id: Optional[str] = None
    product_id: Optional[str] = None
    product_type: Optional[str] = None  # v1: "hotel" expected


class SimpleRuleAction(BaseModel):
    type: Literal["markup_percent"] = "markup_percent"
    value: float = Field(ge=0.0, le=100.0)


class SimplePricingRuleCreate(BaseModel):
    priority: int = 100
    scope: SimpleRuleScope
    validity: SimpleRuleValidity
    action: SimpleRuleAction
    notes: Optional[str] = None


class SimplePricingRuleUpdate(BaseModel):
    priority: Optional[int] = None
    scope: Optional[SimpleRuleScope] = None
    validity: Optional[SimpleRuleValidity] = None
    action: Optional[SimpleRuleAction] = None
    status: Optional[Literal["active", "inactive"]] = None
    notes: Optional[str] = None


class SimplePricingRuleResponse(BaseModel):
    rule_id: str
    organization_id: str
    status: str
    priority: int
    scope: dict[str, Any]
    validity: dict[str, Any]
    action: dict[str, Any]
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    created_by_email: Optional[str] = None




class PricingTraceStep(BaseModel):
    type: Literal["grid_base", "rule"]
    label: str
    net_before: Optional[float] = None
    net_after: Optional[float] = None
    sell_before: Optional[float] = None
    sell_after: Optional[float] = None
    rule_id: Optional[str] = None
    rule_code: Optional[str] = None
    meta: dict[str, Any] = Field(default_factory=dict)


class PricingTraceFinal(BaseModel):
    net: float
    sell: float
    currency: str


class PricingTraceRequestContext(BaseModel):
    channel_id: Optional[str] = None
    agency_id: Optional[str] = None
    product_id: str
    rate_plan_id: str
    room_type_id: Optional[str] = None
    board: Optional[str] = None
    check_in: str  # YYYY-MM-DD
    check_out: str # YYYY-MM-DD
    occupancy: int
    market: Optional[str] = None


class PricingTraceResponse(BaseModel):
    trace_id: str
    organization_id: str
    quote_id: Optional[str] = None
    request: PricingTraceRequestContext
    contract: dict[str, Any]
    grid_match: dict[str, Any]
    steps: list[PricingTraceStep]
    final: PricingTraceFinal
    created_at: datetime
