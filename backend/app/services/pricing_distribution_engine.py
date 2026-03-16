"""Pricing & Distribution Engine - Syroce Core Pipeline

Unified pricing orchestration layer that transforms supplier rates
into channel-specific sell prices.

Pipeline:
  supplier_price → normalization → base_markup → channel_rule →
  agency_rule → promotion_rule → currency_conversion → final_sell_price

This engine is INDEPENDENT of supplier adapters.
It receives a normalized rate and applies the full pricing pipeline.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Optional

from app.db import get_db
from app.utils import now_utc
from app.constants.currencies import convert_amount, DEFAULT_EXCHANGE_RATES

logger = logging.getLogger("pricing_engine")


# ─── Data Models ─────────────────────────────────────────────────────

CHANNELS = ("b2b", "b2c", "corporate", "whitelabel")
SEASONS = ("peak", "high", "mid", "low", "off")
PROMOTION_TYPES = ("early_booking", "flash_sale", "campaign_discount", "fixed_price_override")


@dataclass
class PricingContext:
    """All inputs the pricing pipeline needs."""
    supplier_code: str
    supplier_price: float
    supplier_currency: str
    destination: str = ""
    channel: str = "b2c"
    agency_id: str = ""
    agency_tier: str = "standard"
    season: str = "mid"
    product_type: str = "hotel"
    check_in: Optional[date] = None
    nights: int = 1
    sell_currency: str = "EUR"
    promo_code: str = ""
    organization_id: str = ""


@dataclass
class PricingBreakdown:
    """Full pricing breakdown output."""
    supplier_price: float = 0.0
    supplier_currency: str = "EUR"
    base_markup_pct: float = 0.0
    base_markup_amount: float = 0.0
    channel_adjustment_pct: float = 0.0
    channel_adjustment_amount: float = 0.0
    agency_adjustment_pct: float = 0.0
    agency_adjustment_amount: float = 0.0
    promotion_discount_pct: float = 0.0
    promotion_discount_amount: float = 0.0
    subtotal_before_tax: float = 0.0
    tax_rate: float = 0.0
    tax_amount: float = 0.0
    sell_price: float = 0.0
    sell_currency: str = "EUR"
    fx_rate: float = 1.0
    margin: float = 0.0
    margin_pct: float = 0.0
    commission: float = 0.0
    commission_pct: float = 0.0
    applied_rules: list = field(default_factory=list)
    per_night: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "supplier_price": self.supplier_price,
            "supplier_currency": self.supplier_currency,
            "base_markup_pct": self.base_markup_pct,
            "base_markup_amount": round(self.base_markup_amount, 2),
            "channel_adjustment_pct": self.channel_adjustment_pct,
            "channel_adjustment_amount": round(self.channel_adjustment_amount, 2),
            "agency_adjustment_pct": self.agency_adjustment_pct,
            "agency_adjustment_amount": round(self.agency_adjustment_amount, 2),
            "promotion_discount_pct": self.promotion_discount_pct,
            "promotion_discount_amount": round(self.promotion_discount_amount, 2),
            "subtotal_before_tax": round(self.subtotal_before_tax, 2),
            "tax_rate": self.tax_rate,
            "tax_amount": round(self.tax_amount, 2),
            "sell_price": round(self.sell_price, 2),
            "sell_currency": self.sell_currency,
            "fx_rate": self.fx_rate,
            "margin": round(self.margin, 2),
            "margin_pct": round(self.margin_pct, 2),
            "commission": round(self.commission, 2),
            "commission_pct": self.commission_pct,
            "applied_rules": self.applied_rules,
            "per_night": round(self.per_night, 2),
        }


def _q2(val: float) -> float:
    return float(Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


# ─── Core Pipeline ───────────────────────────────────────────────────

class PricingDistributionEngine:
    """Stateless pricing pipeline orchestrator."""

    def __init__(self, db):
        self.db = db

    async def calculate(self, ctx: PricingContext) -> PricingBreakdown:
        """Run the full pricing pipeline and return a breakdown."""
        result = PricingBreakdown(
            supplier_price=ctx.supplier_price,
            supplier_currency=ctx.supplier_currency,
            sell_currency=ctx.sell_currency,
        )

        running = ctx.supplier_price

        # Step 1: Base Markup
        markup_rule = await self._resolve_base_markup(ctx)
        markup_pct = markup_rule.get("value", 0.0) if markup_rule else 0.0
        markup_amount = _q2(running * markup_pct / 100.0)
        running = _q2(running + markup_amount)
        result.base_markup_pct = markup_pct
        result.base_markup_amount = markup_amount
        if markup_rule:
            result.applied_rules.append({"stage": "base_markup", "rule_id": markup_rule.get("rule_id", ""), "type": "markup", "value": markup_pct})

        # Step 2: Channel Adjustment
        channel_rule = await self._resolve_channel_rule(ctx)
        ch_pct = channel_rule.get("adjustment_pct", 0.0) if channel_rule else 0.0
        ch_amount = _q2(running * ch_pct / 100.0)
        running = _q2(running + ch_amount)
        result.channel_adjustment_pct = ch_pct
        result.channel_adjustment_amount = ch_amount
        if channel_rule:
            result.applied_rules.append({"stage": "channel", "rule_id": channel_rule.get("rule_id", ""), "channel": ctx.channel, "value": ch_pct})

        # Step 3: Agency Adjustment
        agency_rule = await self._resolve_agency_rule(ctx)
        ag_pct = agency_rule.get("adjustment_pct", 0.0) if agency_rule else 0.0
        ag_amount = _q2(running * ag_pct / 100.0)
        running = _q2(running + ag_amount)
        result.agency_adjustment_pct = ag_pct
        result.agency_adjustment_amount = ag_amount
        if agency_rule:
            result.applied_rules.append({"stage": "agency", "rule_id": agency_rule.get("rule_id", ""), "tier": ctx.agency_tier, "value": ag_pct})

        # Step 4: Promotion
        promo = await self._resolve_promotion(ctx)
        promo_pct = promo.get("discount_pct", 0.0) if promo else 0.0
        promo_amount = _q2(running * promo_pct / 100.0)
        running = _q2(running - promo_amount)
        result.promotion_discount_pct = promo_pct
        result.promotion_discount_amount = promo_amount
        if promo:
            result.applied_rules.append({"stage": "promotion", "rule_id": promo.get("rule_id", ""), "promo_type": promo.get("promo_type", ""), "value": promo_pct})

        result.subtotal_before_tax = running

        # Step 5: Tax
        tax_rate = await self._resolve_tax_rate(ctx)
        tax_amount = _q2(running * tax_rate / 100.0)
        result.tax_rate = tax_rate
        result.tax_amount = tax_amount

        sell_in_supplier_ccy = _q2(running + tax_amount)

        # Step 6: Currency Conversion
        fx_rate = 1.0
        if ctx.supplier_currency != ctx.sell_currency:
            fx_rate = await self._get_fx_rate(ctx.organization_id, ctx.supplier_currency, ctx.sell_currency)
        result.fx_rate = fx_rate
        result.sell_price = _q2(sell_in_supplier_ccy * fx_rate)

        # Step 7: Margin & Commission
        supplier_in_sell_ccy = _q2(ctx.supplier_price * fx_rate)
        result.margin = _q2(result.sell_price - supplier_in_sell_ccy)
        result.margin_pct = round(result.margin / result.sell_price * 100, 2) if result.sell_price > 0 else 0.0

        commission_rule = await self._resolve_commission(ctx)
        comm_pct = commission_rule.get("value", 0.0) if commission_rule else 0.0
        result.commission_pct = comm_pct
        result.commission = _q2(result.sell_price * comm_pct / 100.0)

        # Per night
        result.per_night = _q2(result.sell_price / max(ctx.nights, 1))

        return result

    # ─── Rule Resolvers ──────────────────────────────────────────────

    async def _resolve_base_markup(self, ctx: PricingContext) -> Optional[dict]:
        """Find the best matching distribution rule for base markup."""
        rules = await self.db.distribution_rules.find({
            "organization_id": ctx.organization_id,
            "rule_category": "base_markup",
            "active": True,
        }).to_list(500)

        return self._best_match(rules, ctx)

    async def _resolve_channel_rule(self, ctx: PricingContext) -> Optional[dict]:
        """Find channel-specific pricing adjustment."""
        doc = await self.db.channel_configs.find_one({
            "organization_id": ctx.organization_id,
            "channel": ctx.channel,
            "active": True,
        })
        return doc

    async def _resolve_agency_rule(self, ctx: PricingContext) -> Optional[dict]:
        """Find agency tier pricing adjustment."""
        doc = await self.db.channel_configs.find_one({
            "organization_id": ctx.organization_id,
            "channel": ctx.channel,
            "agency_tier": ctx.agency_tier,
            "active": True,
        })
        if doc:
            return doc
        # Fallback: tier-level default
        tier_doc = await self.db.distribution_rules.find_one({
            "organization_id": ctx.organization_id,
            "rule_category": "agency_tier",
            "scope.agency_tier": ctx.agency_tier,
            "active": True,
        })
        return tier_doc

    async def _resolve_promotion(self, ctx: PricingContext) -> Optional[dict]:
        """Find applicable promotion."""
        now = now_utc()
        query: dict[str, Any] = {
            "organization_id": ctx.organization_id,
            "active": True,
            "$or": [
                {"valid_from": {"$exists": False}},
                {"valid_from": None},
                {"valid_from": {"$lte": now}},
            ],
        }
        promos = await self.db.promotions.find(query).to_list(200)

        best = None
        best_score = -1
        for p in promos:
            valid_to = p.get("valid_to")
            if valid_to and valid_to < now:
                continue
            score = self._promo_match_score(p, ctx)
            if score > best_score:
                best_score = score
                best = p

        return best

    async def _resolve_tax_rate(self, ctx: PricingContext) -> float:
        """Resolve tax rate for destination. Default 0 for international."""
        doc = await self.db.distribution_rules.find_one({
            "organization_id": ctx.organization_id,
            "rule_category": "tax",
            "scope.destination": ctx.destination,
            "active": True,
        })
        if doc:
            return float(doc.get("value", 0.0))
        return 0.0

    async def _resolve_commission(self, ctx: PricingContext) -> Optional[dict]:
        """Resolve commission rate for this context."""
        doc = await self.db.distribution_rules.find_one({
            "organization_id": ctx.organization_id,
            "rule_category": "commission",
            "active": True,
            "$or": [
                {"scope.channel": ctx.channel},
                {"scope.channel": {"$exists": False}},
            ],
        })
        return doc

    async def _get_fx_rate(self, organization_id: str, from_ccy: str, to_ccy: str) -> float:
        """Get exchange rate, falling back to defaults."""
        if from_ccy == to_ccy:
            return 1.0
        doc = await self.db.fx_rates.find_one({
            "organization_id": organization_id,
            "base": from_ccy.upper(),
            "quote": to_ccy.upper(),
        }, sort=[("updated_at", -1)])
        if doc:
            return float(doc["rate"])
        key = f"{from_ccy.upper()}_{to_ccy.upper()}"
        return DEFAULT_EXCHANGE_RATES.get(key, 1.0)

    # ─── Matching Logic ──────────────────────────────────────────────

    def _best_match(self, rules: list[dict], ctx: PricingContext) -> Optional[dict]:
        """Score and select the best matching rule. Higher specificity wins."""
        if not rules:
            return None

        scored = []
        for r in rules:
            score = self._rule_match_score(r, ctx)
            if score >= 0:
                scored.append((score, r.get("priority", 0), r))

        if not scored:
            return None

        scored.sort(key=lambda x: (-x[0], -x[1]))
        return scored[0][2]

    def _rule_match_score(self, rule: dict, ctx: PricingContext) -> int:
        """Calculate match score. -1 means no match. Higher = more specific."""
        scope = rule.get("scope") or {}
        score = 0

        # Supplier filter
        if scope.get("supplier"):
            if scope["supplier"] != ctx.supplier_code:
                return -1
            score += 10

        # Destination filter
        if scope.get("destination"):
            if scope["destination"].lower() != ctx.destination.lower():
                return -1
            score += 8

        # Season filter
        if scope.get("season"):
            if scope["season"] != ctx.season:
                return -1
            score += 6

        # Channel filter
        if scope.get("channel"):
            if scope["channel"] != ctx.channel:
                return -1
            score += 4

        # Agency tier filter
        if scope.get("agency_tier"):
            if scope["agency_tier"] != ctx.agency_tier:
                return -1
            score += 4

        # Product type filter
        if scope.get("product_type"):
            if scope["product_type"] != ctx.product_type:
                return -1
            score += 2

        return score

    def _promo_match_score(self, promo: dict, ctx: PricingContext) -> int:
        """Score promotion match. -1 means no match."""
        scope = promo.get("scope") or {}
        score = 0

        if scope.get("channel") and scope["channel"] != ctx.channel:
            return -1
        if scope.get("channel"):
            score += 2

        if scope.get("supplier") and scope["supplier"] != ctx.supplier_code:
            return -1
        if scope.get("supplier"):
            score += 2

        if scope.get("destination") and scope["destination"].lower() != ctx.destination.lower():
            return -1
        if scope.get("destination"):
            score += 2

        if promo.get("promo_code") and ctx.promo_code:
            if promo["promo_code"] != ctx.promo_code:
                return -1
            score += 10

        return score


# ─── Dashboard Aggregation ───────────────────────────────────────────

async def get_pricing_engine_stats(organization_id: str) -> dict[str, Any]:
    """Aggregate pricing engine stats for the dashboard."""
    db = await get_db()

    rule_count = await db.distribution_rules.count_documents({"organization_id": organization_id})
    active_rules = await db.distribution_rules.count_documents({"organization_id": organization_id, "active": True})
    channel_count = await db.channel_configs.count_documents({"organization_id": organization_id})
    promo_count = await db.promotions.count_documents({"organization_id": organization_id, "active": True})

    # Rules by category
    pipeline = [
        {"$match": {"organization_id": organization_id, "active": True}},
        {"$group": {"_id": "$rule_category", "count": {"$sum": 1}}},
    ]
    by_category = {doc["_id"]: doc["count"] async for doc in db.distribution_rules.aggregate(pipeline)}

    # Active channels
    channels = await db.channel_configs.find(
        {"organization_id": organization_id, "active": True},
        {"_id": 0, "channel": 1, "adjustment_pct": 1, "label": 1},
    ).to_list(20)

    return {
        "total_rules": rule_count,
        "active_rules": active_rules,
        "channel_count": channel_count,
        "active_promotions": promo_count,
        "rules_by_category": by_category,
        "active_channels": channels,
    }
