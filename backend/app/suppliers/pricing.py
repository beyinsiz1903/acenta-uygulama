"""Supplier Pricing Engine Integration.

Applies agency-specific pricing rules on top of supplier net prices.

Pipeline (in order):
  1. Supplier net price (base)
  2. Markup rules (per product type, supplier, agency tier)
  3. Commission calculation
  4. Channel pricing override (B2B, direct, API)
  5. Promotional overrides
  6. Currency conversion (if needed)
  7. Final sell price

Rule types:
  - percentage_markup: +X% on supplier price
  - fixed_markup: +X TRY on supplier price
  - commission_rate: X% commission (deducted from sell price)
  - channel_override: different markup per channel
  - promo_discount: -X% or -X TRY promotional discount
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.suppliers.contracts.schemas import PriceBreakdown

logger = logging.getLogger("suppliers.pricing")


class PricingRuleType:
    PERCENTAGE_MARKUP = "percentage_markup"
    FIXED_MARKUP = "fixed_markup"
    COMMISSION_RATE = "commission_rate"
    CHANNEL_OVERRIDE = "channel_override"
    PROMO_DISCOUNT = "promo_discount"


@dataclass
class PricingRule:
    rule_id: str
    rule_type: str
    value: float
    applies_to_product_type: Optional[str] = None  # None = all
    applies_to_supplier: Optional[str] = None  # None = all
    applies_to_agency_tier: Optional[str] = None  # None = all
    applies_to_channel: Optional[str] = None  # None = all
    priority: int = 0  # higher = later in pipeline
    active: bool = True


# Default rules (loaded from DB at runtime)
DEFAULT_RULES = [
    PricingRule("default_hotel_markup", PricingRuleType.PERCENTAGE_MARKUP, 15.0,
                applies_to_product_type="hotel", priority=10),
    PricingRule("default_flight_markup", PricingRuleType.PERCENTAGE_MARKUP, 8.0,
                applies_to_product_type="flight", priority=10),
    PricingRule("default_tour_markup", PricingRuleType.PERCENTAGE_MARKUP, 18.0,
                applies_to_product_type="tour", priority=10),
    PricingRule("default_insurance_markup", PricingRuleType.PERCENTAGE_MARKUP, 10.0,
                applies_to_product_type="insurance", priority=10),
    PricingRule("default_transport_markup", PricingRuleType.PERCENTAGE_MARKUP, 20.0,
                applies_to_product_type="transport", priority=10),
    PricingRule("b2b_discount", PricingRuleType.PERCENTAGE_MARKUP, -3.0,
                applies_to_channel="b2b", priority=20),
    PricingRule("premium_agency_discount", PricingRuleType.PERCENTAGE_MARKUP, -5.0,
                applies_to_agency_tier="premium", priority=25),
]

# Agency tiers and their default commission rates
AGENCY_TIERS = {
    "starter": {"commission_rate": 5.0, "markup_adjustment": 0.0},
    "standard": {"commission_rate": 8.0, "markup_adjustment": -2.0},
    "premium": {"commission_rate": 12.0, "markup_adjustment": -5.0},
    "enterprise": {"commission_rate": 15.0, "markup_adjustment": -8.0},
}


def _matches_rule(rule: PricingRule, product_type: str, supplier_code: str,
                   agency_tier: str, channel: str) -> bool:
    """Check if a rule applies to the given context."""
    if not rule.active:
        return False
    if rule.applies_to_product_type and rule.applies_to_product_type != product_type:
        return False
    if rule.applies_to_supplier and rule.applies_to_supplier != supplier_code:
        return False
    if rule.applies_to_agency_tier and rule.applies_to_agency_tier != agency_tier:
        return False
    if rule.applies_to_channel and rule.applies_to_channel != channel:
        return False
    return True


def compute_sell_price(
    supplier_price: PriceBreakdown,
    *,
    product_type: str = "hotel",
    supplier_code: str = "",
    agency_tier: str = "standard",
    channel: str = "direct",
    promo_code: Optional[str] = None,
    custom_rules: Optional[List[PricingRule]] = None,
) -> PriceBreakdown:
    """Apply pricing pipeline to supplier net price and return sell price.

    Returns a new PriceBreakdown with sell-side values.
    """
    rules = custom_rules or DEFAULT_RULES
    rules = sorted(
        [r for r in rules if _matches_rule(r, product_type, supplier_code, agency_tier, channel)],
        key=lambda r: r.priority,
    )

    base = supplier_price.base_price
    tax = supplier_price.tax
    running_price = base

    total_markup = 0.0
    total_commission = 0.0

    for rule in rules:
        if rule.rule_type == PricingRuleType.PERCENTAGE_MARKUP:
            delta = base * (rule.value / 100.0)
            running_price += delta
            total_markup += delta
        elif rule.rule_type == PricingRuleType.FIXED_MARKUP:
            running_price += rule.value
            total_markup += rule.value
        elif rule.rule_type == PricingRuleType.COMMISSION_RATE:
            total_commission = running_price * (rule.value / 100.0)
        elif rule.rule_type == PricingRuleType.PROMO_DISCOUNT:
            discount = running_price * (rule.value / 100.0)
            running_price -= discount

    # Apply agency tier commission
    tier_config = AGENCY_TIERS.get(agency_tier, AGENCY_TIERS["standard"])
    if total_commission == 0:
        total_commission = running_price * (tier_config["commission_rate"] / 100.0)

    service_fee = supplier_price.service_fee
    total = running_price + tax + service_fee

    return PriceBreakdown(
        base_price=round(running_price, 2),
        tax=round(tax, 2),
        service_fee=round(service_fee, 2),
        discount=round(supplier_price.discount, 2),
        total=round(total, 2),
        currency=supplier_price.currency,
        per_night=round(running_price / max(supplier_price.per_night or 1, 1), 2) if supplier_price.per_night else None,
        per_person=supplier_price.per_person,
    )


async def load_pricing_rules(db, organization_id: str) -> List[PricingRule]:
    """Load pricing rules from MongoDB for an organization."""
    try:
        cursor = db.supplier_pricing_rules.find(
            {"organization_id": organization_id, "active": True},
            {"_id": 0},
        )
        rules = []
        async for doc in cursor:
            rules.append(PricingRule(
                rule_id=doc.get("rule_id", ""),
                rule_type=doc.get("rule_type", ""),
                value=doc.get("value", 0),
                applies_to_product_type=doc.get("applies_to_product_type"),
                applies_to_supplier=doc.get("applies_to_supplier"),
                applies_to_agency_tier=doc.get("applies_to_agency_tier"),
                applies_to_channel=doc.get("applies_to_channel"),
                priority=doc.get("priority", 0),
                active=True,
            ))
        return rules if rules else DEFAULT_RULES
    except Exception:
        return DEFAULT_RULES
