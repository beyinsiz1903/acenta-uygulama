"""Pricing & Distribution Engine - Syroce Core Pipeline

Unified pricing orchestration layer that transforms supplier rates
into channel-specific sell prices.

Pipeline:
  supplier_price -> normalization -> base_markup -> channel_rule ->
  agency_rule -> promotion_rule -> currency_conversion -> final_sell_price

This engine is INDEPENDENT of supplier adapters.
It receives a normalized rate and applies the full pricing pipeline.
"""
from __future__ import annotations

import hashlib
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Optional

from app.db import get_db
from app.utils import now_utc
from app.constants.currencies import convert_amount, DEFAULT_EXCHANGE_RATES

logger = logging.getLogger("pricing_engine")


# --- Pricing Cache ---

class PricingCache:
    """In-memory pricing cache with TTL, telemetry, and supplier-aware invalidation."""

    def __init__(self, ttl_seconds: int = 300, max_size: int = 5000):
        self._store: dict[str, tuple[float, dict, str]] = {}  # key -> (expires_at, result_dict, supplier_code)
        self.ttl = ttl_seconds
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
        # Telemetry: per-supplier metrics
        self._supplier_hits: dict[str, int] = {}
        self._supplier_misses: dict[str, int] = {}
        # Telemetry: latency tracking
        self._hit_latencies: list[float] = []
        self._miss_latencies: list[float] = []
        self._max_latency_samples = 500
        # Telemetry: invalidation log
        self._invalidations: list[dict] = []
        self._max_invalidation_log = 50
        self._created_at = time.time()

    def _make_key(self, ctx: "PricingContext") -> str:
        """Composite cache key: normalized_rate + channel + agency + supplier + destination + season + promo."""
        raw = f"{ctx.supplier_code}|{ctx.supplier_price}|{ctx.supplier_currency}|{ctx.destination}|{ctx.channel}|{ctx.agency_tier}|{ctx.season}|{ctx.product_type}|{ctx.nights}|{ctx.sell_currency}|{ctx.promo_code}|{ctx.organization_id}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def get(self, ctx: "PricingContext") -> Optional[dict]:
        t0 = time.time()
        key = self._make_key(ctx)
        entry = self._store.get(key)
        if entry is None:
            self.misses += 1
            self._supplier_misses[ctx.supplier_code] = self._supplier_misses.get(ctx.supplier_code, 0) + 1
            elapsed = (time.time() - t0) * 1000
            if len(self._miss_latencies) < self._max_latency_samples:
                self._miss_latencies.append(elapsed)
            return None
        expires_at, result, _supplier = entry
        if time.time() > expires_at:
            del self._store[key]
            self.misses += 1
            self._supplier_misses[ctx.supplier_code] = self._supplier_misses.get(ctx.supplier_code, 0) + 1
            elapsed = (time.time() - t0) * 1000
            if len(self._miss_latencies) < self._max_latency_samples:
                self._miss_latencies.append(elapsed)
            return None
        self.hits += 1
        self._supplier_hits[ctx.supplier_code] = self._supplier_hits.get(ctx.supplier_code, 0) + 1
        elapsed = (time.time() - t0) * 1000
        if len(self._hit_latencies) < self._max_latency_samples:
            self._hit_latencies.append(elapsed)
        return result

    def put(self, ctx: "PricingContext", result: dict) -> str:
        key = self._make_key(ctx)
        if len(self._store) >= self.max_size:
            self._evict()
        self._store[key] = (time.time() + self.ttl, result, ctx.supplier_code)
        return key

    def _evict(self):
        """Remove expired entries first, then oldest 20%."""
        now = time.time()
        expired = [k for k, (exp, _, _s) in self._store.items() if now > exp]
        for k in expired:
            del self._store[k]
        if len(self._store) >= self.max_size:
            to_remove = sorted(self._store.items(), key=lambda x: x[1][0])[:self.max_size // 5]
            for k, _ in to_remove:
                del self._store[k]

    def clear(self):
        cleared = len(self._store)
        self._store.clear()
        self.hits = 0
        self.misses = 0
        self._supplier_hits.clear()
        self._supplier_misses.clear()
        self._hit_latencies.clear()
        self._miss_latencies.clear()
        self._log_invalidation("manual_clear", cleared=cleared)

    def invalidate_by_supplier(self, supplier_code: str) -> int:
        """Remove all cache entries for a specific supplier. Called after supplier sync."""
        keys_to_remove = [
            k for k, (_exp, _res, sup) in self._store.items()
            if sup == supplier_code
        ]
        for k in keys_to_remove:
            del self._store[k]
        if keys_to_remove:
            logger.info("pricing_cache: invalidated %d entries for supplier=%s", len(keys_to_remove), supplier_code)
            self._log_invalidation(f"supplier_sync:{supplier_code}", cleared=len(keys_to_remove))
        return len(keys_to_remove)

    def _log_invalidation(self, reason: str, cleared: int = 0):
        entry = {
            "reason": reason,
            "cleared": cleared,
            "timestamp": datetime.now().isoformat(),
        }
        self._invalidations.append(entry)
        if len(self._invalidations) > self._max_invalidation_log:
            self._invalidations = self._invalidations[-self._max_invalidation_log:]

    def stats(self) -> dict:
        now = time.time()
        active = sum(1 for _, (exp, _, _s) in self._store.items() if now <= exp)
        total_requests = self.hits + self.misses
        avg_hit_latency = round(sum(self._hit_latencies) / max(len(self._hit_latencies), 1), 3)
        avg_miss_latency = round(sum(self._miss_latencies) / max(len(self._miss_latencies), 1), 3)
        return {
            "total_entries": len(self._store),
            "active_entries": active,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate_pct": round(self.hits / max(total_requests, 1) * 100, 1),
            "ttl_seconds": self.ttl,
            "max_size": self.max_size,
        }

    def telemetry(self) -> dict:
        """Extended telemetry: per-supplier metrics, latencies, invalidation log."""
        now = time.time()
        active = sum(1 for _, (exp, _, _s) in self._store.items() if now <= exp)
        total_requests = self.hits + self.misses
        avg_hit_latency = round(sum(self._hit_latencies) / max(len(self._hit_latencies), 1), 3)
        avg_miss_latency = round(sum(self._miss_latencies) / max(len(self._miss_latencies), 1), 3)

        # Per-supplier breakdown
        all_suppliers = set(list(self._supplier_hits.keys()) + list(self._supplier_misses.keys()))
        supplier_breakdown = {}
        for s in sorted(all_suppliers):
            s_hits = self._supplier_hits.get(s, 0)
            s_misses = self._supplier_misses.get(s, 0)
            s_total = s_hits + s_misses
            s_entries = sum(1 for _, (_exp, _res, sup) in self._store.items() if sup == s and now <= _exp)
            supplier_breakdown[s] = {
                "hits": s_hits,
                "misses": s_misses,
                "hit_rate_pct": round(s_hits / max(s_total, 1) * 100, 1),
                "active_entries": s_entries,
            }

        return {
            "total_entries": len(self._store),
            "active_entries": active,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate_pct": round(self.hits / max(total_requests, 1) * 100, 1),
            "total_requests": total_requests,
            "avg_hit_latency_ms": avg_hit_latency,
            "avg_miss_latency_ms": avg_miss_latency,
            "ttl_seconds": self.ttl,
            "max_size": self.max_size,
            "uptime_seconds": round(now - self._created_at),
            "supplier_breakdown": supplier_breakdown,
            "recent_invalidations": self._invalidations[-10:],
        }


# Singleton cache instance
pricing_cache = PricingCache(ttl_seconds=300, max_size=5000)


# --- Data Models ---

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
class PipelineStep:
    """Single step in the pricing pipeline."""
    step: str
    label: str
    input_price: float
    adjustment_pct: float
    adjustment_amount: float
    output_price: float
    rule_id: str = ""
    rule_name: str = ""
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "label": self.label,
            "input_price": round(self.input_price, 2),
            "adjustment_pct": self.adjustment_pct,
            "adjustment_amount": round(self.adjustment_amount, 2),
            "output_price": round(self.output_price, 2),
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "detail": self.detail,
        }


@dataclass
class EvaluatedRule:
    """A rule that was evaluated during matching."""
    rule_id: str
    name: str
    category: str
    match_score: int
    priority: int
    value: float
    scope: dict
    won: bool = False
    reject_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "category": self.category,
            "match_score": self.match_score,
            "priority": self.priority,
            "value": self.value,
            "scope": self.scope,
            "won": self.won,
            "reject_reason": self.reject_reason,
        }


@dataclass
class GuardrailWarning:
    """Warning from margin guardrail validation."""
    guardrail: str
    message: str
    severity: str  # "error" | "warning"
    expected: float
    actual: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "guardrail": self.guardrail,
            "message": self.message,
            "severity": self.severity,
            "expected": self.expected,
            "actual": self.actual,
        }


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
    pipeline_steps: list = field(default_factory=list)
    evaluated_rules: list = field(default_factory=list)
    guardrail_warnings: list = field(default_factory=list)
    guardrails_passed: bool = True
    pricing_trace_id: str = ""
    cache_hit: bool = False
    cache_key: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "pricing_trace_id": self.pricing_trace_id,
            "cache_hit": self.cache_hit,
            "cache_key": self.cache_key,
            "latency_ms": self.latency_ms,
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
            "pipeline_steps": [s.to_dict() if hasattr(s, 'to_dict') else s for s in self.pipeline_steps],
            "evaluated_rules": [r.to_dict() if hasattr(r, 'to_dict') else r for r in self.evaluated_rules],
            "guardrail_warnings": [w.to_dict() if hasattr(w, 'to_dict') else w for w in self.guardrail_warnings],
            "guardrails_passed": self.guardrails_passed,
        }


def _q2(val: float) -> float:
    return float(Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


# --- Core Pipeline ---

class PricingDistributionEngine:
    """Stateless pricing pipeline orchestrator."""

    def __init__(self, db):
        self.db = db

    async def calculate(self, ctx: PricingContext) -> PricingBreakdown:
        """Run the full pricing pipeline and return a breakdown."""
        start_time = time.time()
        trace_id = f"prc_{uuid.uuid4().hex[:8]}"
        logger.info("pricing_trace_id: %s | supplier=%s price=%s channel=%s agency=%s",
                     trace_id, ctx.supplier_code, ctx.supplier_price, ctx.channel, ctx.agency_tier)

        # Check cache
        cached = pricing_cache.get(ctx)
        if cached is not None:
            cached["pricing_trace_id"] = trace_id
            cached["cache_hit"] = True
            cached["latency_ms"] = round((time.time() - start_time) * 1000, 2)
            logger.info("pricing_trace_id: %s | CACHE HIT | latency=%.2fms", trace_id, cached["latency_ms"])
            # Return as PricingBreakdown for consistency
            result = PricingBreakdown()
            result.pricing_trace_id = trace_id
            result.cache_hit = True
            result.latency_ms = cached["latency_ms"]
            # Return the dict directly from router; we'll handle this
            return cached  # type: ignore

        result = PricingBreakdown(
            supplier_price=ctx.supplier_price,
            supplier_currency=ctx.supplier_currency,
            sell_currency=ctx.sell_currency,
            pricing_trace_id=trace_id,
        )

        running = ctx.supplier_price
        all_evaluated = []

        # Step 0: Supplier Price (initial)
        result.pipeline_steps.append(PipelineStep(
            step="supplier_price",
            label="Supplier Fiyat",
            input_price=running,
            adjustment_pct=0,
            adjustment_amount=0,
            output_price=running,
            detail=f"{ctx.supplier_code} / {ctx.supplier_currency}",
        ))

        # Step 1: Base Markup
        markup_rule, markup_evaluated = await self._resolve_base_markup_with_trace(ctx)
        all_evaluated.extend(markup_evaluated)
        markup_pct = markup_rule.get("value", 0.0) if markup_rule else 0.0
        markup_amount = _q2(running * markup_pct / 100.0)
        prev = running
        running = _q2(running + markup_amount)
        result.base_markup_pct = markup_pct
        result.base_markup_amount = markup_amount
        result.pipeline_steps.append(PipelineStep(
            step="base_markup",
            label="Baz Markup",
            input_price=prev,
            adjustment_pct=markup_pct,
            adjustment_amount=markup_amount,
            output_price=running,
            rule_id=markup_rule.get("rule_id", "") if markup_rule else "",
            rule_name=markup_rule.get("name", "") if markup_rule else "",
            detail=f"+%{markup_pct}",
        ))
        if markup_rule:
            result.applied_rules.append({"stage": "base_markup", "rule_id": markup_rule.get("rule_id", ""), "type": "markup", "value": markup_pct})

        # Step 2: Channel Adjustment
        channel_rule = await self._resolve_channel_rule(ctx)
        ch_pct = channel_rule.get("adjustment_pct", 0.0) if channel_rule else 0.0
        ch_amount = _q2(running * ch_pct / 100.0)
        prev = running
        running = _q2(running + ch_amount)
        result.channel_adjustment_pct = ch_pct
        result.channel_adjustment_amount = ch_amount
        result.pipeline_steps.append(PipelineStep(
            step="channel_rule",
            label=f"Kanal ({ctx.channel.upper()})",
            input_price=prev,
            adjustment_pct=ch_pct,
            adjustment_amount=ch_amount,
            output_price=running,
            rule_id=channel_rule.get("rule_id", "") if channel_rule else "",
            rule_name=channel_rule.get("label", "") if channel_rule else "",
            detail=f"{'+' if ch_pct >= 0 else ''}{ch_pct}%",
        ))
        if channel_rule:
            result.applied_rules.append({"stage": "channel", "rule_id": channel_rule.get("rule_id", ""), "channel": ctx.channel, "value": ch_pct})

        # Step 3: Agency Adjustment
        agency_rule = await self._resolve_agency_rule(ctx)
        ag_pct = agency_rule.get("adjustment_pct", 0.0) if agency_rule else 0.0
        ag_amount = _q2(running * ag_pct / 100.0)
        prev = running
        running = _q2(running + ag_amount)
        result.agency_adjustment_pct = ag_pct
        result.agency_adjustment_amount = ag_amount
        result.pipeline_steps.append(PipelineStep(
            step="agency_rule",
            label=f"Acente ({ctx.agency_tier})",
            input_price=prev,
            adjustment_pct=ag_pct,
            adjustment_amount=ag_amount,
            output_price=running,
            rule_id=agency_rule.get("rule_id", "") if agency_rule else "",
            rule_name=agency_rule.get("agency_tier", "") if agency_rule else "",
            detail=f"{'+' if ag_pct >= 0 else ''}{ag_pct}%",
        ))
        if agency_rule:
            result.applied_rules.append({"stage": "agency", "rule_id": agency_rule.get("rule_id", ""), "tier": ctx.agency_tier, "value": ag_pct})

        # Step 4: Promotion
        promo, promo_evaluated = await self._resolve_promotion_with_trace(ctx)
        all_evaluated.extend(promo_evaluated)
        promo_pct = promo.get("discount_pct", 0.0) if promo else 0.0
        promo_amount = _q2(running * promo_pct / 100.0)
        prev = running
        running = _q2(running - promo_amount)
        result.promotion_discount_pct = promo_pct
        result.promotion_discount_amount = promo_amount
        result.pipeline_steps.append(PipelineStep(
            step="promotion",
            label="Promosyon",
            input_price=prev,
            adjustment_pct=-promo_pct if promo_pct else 0,
            adjustment_amount=-promo_amount if promo_amount else 0,
            output_price=running,
            rule_id=promo.get("rule_id", "") if promo else "",
            rule_name=promo.get("name", "") if promo else "",
            detail=f"-%{promo_pct}" if promo_pct else "Yok",
        ))
        if promo:
            result.applied_rules.append({"stage": "promotion", "rule_id": promo.get("rule_id", ""), "promo_type": promo.get("promo_type", ""), "value": promo_pct})

        result.subtotal_before_tax = running

        # Step 5: Tax
        tax_rate = await self._resolve_tax_rate(ctx)
        tax_amount = _q2(running * tax_rate / 100.0)
        result.tax_rate = tax_rate
        result.tax_amount = tax_amount
        prev = running
        sell_in_supplier_ccy = _q2(running + tax_amount)
        result.pipeline_steps.append(PipelineStep(
            step="tax",
            label="Vergi",
            input_price=prev,
            adjustment_pct=tax_rate,
            adjustment_amount=tax_amount,
            output_price=sell_in_supplier_ccy,
            detail=f"+%{tax_rate}",
        ))

        # Step 6: Currency Conversion
        fx_rate = 1.0
        if ctx.supplier_currency != ctx.sell_currency:
            fx_rate = await self._get_fx_rate(ctx.organization_id, ctx.supplier_currency, ctx.sell_currency)
        result.fx_rate = fx_rate
        result.sell_price = _q2(sell_in_supplier_ccy * fx_rate)
        result.pipeline_steps.append(PipelineStep(
            step="currency_conversion",
            label="Kur Donusumu",
            input_price=sell_in_supplier_ccy,
            adjustment_pct=0,
            adjustment_amount=0,
            output_price=result.sell_price,
            detail=f"{ctx.supplier_currency} -> {ctx.sell_currency} (x{fx_rate})" if fx_rate != 1.0 else "Ayni para birimi",
        ))

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

        # Store evaluated rules
        result.evaluated_rules = all_evaluated

        # Step 8: Guardrails validation
        guardrail_warnings = await self._validate_guardrails(ctx, result)
        result.guardrail_warnings = guardrail_warnings
        result.guardrails_passed = not any(w.severity == "error" for w in guardrail_warnings)

        # Finalize trace & cache
        elapsed = round((time.time() - start_time) * 1000, 2)
        result.latency_ms = elapsed
        result_dict = result.to_dict()
        cache_key = pricing_cache.put(ctx, result_dict)
        result.cache_key = cache_key
        result_dict["cache_key"] = cache_key

        logger.info("pricing_trace_id: %s | CALCULATED | sell_price=%.2f margin_pct=%.2f latency=%.2fms cache_key=%s",
                     trace_id, result.sell_price, result.margin_pct, elapsed, cache_key)

        return result

    # --- Rule Resolvers ---

    async def _resolve_base_markup_with_trace(self, ctx: PricingContext) -> tuple[Optional[dict], list[EvaluatedRule]]:
        """Find the best matching distribution rule for base markup, with evaluation trace."""
        rules = await self.db.distribution_rules.find({
            "organization_id": ctx.organization_id,
            "rule_category": "base_markup",
            "active": True,
        }).to_list(500)

        winner, evaluated = self._best_match_with_trace(rules, ctx, "base_markup")
        return winner, evaluated

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

    async def _resolve_promotion_with_trace(self, ctx: PricingContext) -> tuple[Optional[dict], list[EvaluatedRule]]:
        """Find applicable promotion with evaluation trace."""
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

        evaluated = []
        best = None
        best_score = -1
        for p in promos:
            valid_to = p.get("valid_to")
            expired = valid_to and valid_to < now
            score = self._promo_match_score(p, ctx)

            reject_reason = ""
            if expired:
                reject_reason = "Suresi dolmus"
                score = -1
            elif score < 0:
                reject_reason = "Scope uyumsuz"

            ev = EvaluatedRule(
                rule_id=p.get("rule_id", ""),
                name=p.get("name", ""),
                category=f"promotion/{p.get('promo_type', '')}",
                match_score=score,
                priority=0,
                value=p.get("discount_pct", 0),
                scope=p.get("scope", {}),
                won=False,
                reject_reason=reject_reason,
            )
            evaluated.append(ev)

            if score > best_score and not expired:
                best_score = score
                best = p

        # Mark winner
        if best:
            for ev in evaluated:
                if ev.rule_id == best.get("rule_id"):
                    ev.won = True
                    break

        return best, evaluated

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

    # --- Guardrails ---

    async def _validate_guardrails(self, ctx: PricingContext, result: PricingBreakdown) -> list[GuardrailWarning]:
        """Validate pricing result against guardrails."""
        warnings = []

        guardrails = await self.db.pricing_guardrails.find({
            "organization_id": ctx.organization_id,
            "active": True,
        }).to_list(50)

        for g in guardrails:
            gtype = g.get("guardrail_type", "")
            gvalue = float(g.get("value", 0))
            scope = g.get("scope", {})

            # Check scope match
            if scope.get("supplier") and scope["supplier"] != ctx.supplier_code:
                continue
            if scope.get("channel") and scope["channel"] != ctx.channel:
                continue
            if scope.get("destination") and scope["destination"].lower() != ctx.destination.lower():
                continue

            if gtype == "min_margin_pct":
                if result.margin_pct < gvalue:
                    warnings.append(GuardrailWarning(
                        guardrail="min_margin_pct",
                        message=f"Marj (%{result.margin_pct}) minimum sinirin (%{gvalue}) altinda",
                        severity="error",
                        expected=gvalue,
                        actual=result.margin_pct,
                    ))

            elif gtype == "max_discount_pct":
                if result.promotion_discount_pct > gvalue:
                    warnings.append(GuardrailWarning(
                        guardrail="max_discount_pct",
                        message=f"Indirim (%{result.promotion_discount_pct}) maksimum sinirin (%{gvalue}) ustunde",
                        severity="error",
                        expected=gvalue,
                        actual=result.promotion_discount_pct,
                    ))

            elif gtype == "channel_floor_price":
                if result.sell_price < gvalue:
                    warnings.append(GuardrailWarning(
                        guardrail="channel_floor_price",
                        message=f"Satis fiyati ({result.sell_price}) kanal taban fiyatinin ({gvalue}) altinda",
                        severity="error",
                        expected=gvalue,
                        actual=result.sell_price,
                    ))

            elif gtype == "supplier_max_markup_pct":
                if result.base_markup_pct > gvalue:
                    warnings.append(GuardrailWarning(
                        guardrail="supplier_max_markup_pct",
                        message=f"Markup (%{result.base_markup_pct}) supplier sinirinin (%{gvalue}) ustunde",
                        severity="warning",
                        expected=gvalue,
                        actual=result.base_markup_pct,
                    ))

        return warnings

    # --- Matching Logic ---

    def _best_match_with_trace(self, rules: list[dict], ctx: PricingContext, category: str) -> tuple[Optional[dict], list[EvaluatedRule]]:
        """Score and select the best matching rule with full trace."""
        evaluated = []
        if not rules:
            return None, evaluated

        scored = []
        for r in rules:
            score = self._rule_match_score(r, ctx)
            reject_reason = ""
            if score < 0:
                reject_reason = "Scope uyumsuz"

            ev = EvaluatedRule(
                rule_id=r.get("rule_id", ""),
                name=r.get("name", ""),
                category=category,
                match_score=score,
                priority=r.get("priority", 0),
                value=r.get("value", 0),
                scope=r.get("scope", {}),
                won=False,
                reject_reason=reject_reason,
            )
            evaluated.append(ev)

            if score >= 0:
                scored.append((score, r.get("priority", 0), r))

        if not scored:
            return None, evaluated

        scored.sort(key=lambda x: (-x[0], -x[1]))
        winner = scored[0][2]

        # Mark winner
        for ev in evaluated:
            if ev.rule_id == winner.get("rule_id"):
                ev.won = True
                break

        return winner, evaluated

    def _best_match(self, rules: list[dict], ctx: PricingContext) -> Optional[dict]:
        """Score and select the best matching rule. Higher specificity wins."""
        winner, _ = self._best_match_with_trace(rules, ctx, "unknown")
        return winner

    def _rule_match_score(self, rule: dict, ctx: PricingContext) -> int:
        """Calculate match score. -1 means no match. Higher = more specific."""
        scope = rule.get("scope") or {}
        score = 0

        if scope.get("supplier"):
            if scope["supplier"] != ctx.supplier_code:
                return -1
            score += 10

        if scope.get("destination"):
            if scope["destination"].lower() != ctx.destination.lower():
                return -1
            score += 8

        if scope.get("season"):
            if scope["season"] != ctx.season:
                return -1
            score += 6

        if scope.get("channel"):
            if scope["channel"] != ctx.channel:
                return -1
            score += 4

        if scope.get("agency_tier"):
            if scope["agency_tier"] != ctx.agency_tier:
                return -1
            score += 4

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


# --- Dashboard Aggregation ---

async def get_pricing_engine_stats(organization_id: str) -> dict[str, Any]:
    """Aggregate pricing engine stats for the dashboard."""
    db = await get_db()

    rule_count = await db.distribution_rules.count_documents({"organization_id": organization_id})
    active_rules = await db.distribution_rules.count_documents({"organization_id": organization_id, "active": True})
    channel_count = await db.channel_configs.count_documents({"organization_id": organization_id})
    promo_count = await db.promotions.count_documents({"organization_id": organization_id, "active": True})
    guardrail_count = await db.pricing_guardrails.count_documents({"organization_id": organization_id, "active": True})

    pipeline = [
        {"$match": {"organization_id": organization_id, "active": True}},
        {"$group": {"_id": "$rule_category", "count": {"$sum": 1}}},
    ]
    by_category = {doc["_id"]: doc["count"] async for doc in db.distribution_rules.aggregate(pipeline)}

    channels = await db.channel_configs.find(
        {"organization_id": organization_id, "active": True},
        {"_id": 0, "channel": 1, "adjustment_pct": 1, "label": 1},
    ).to_list(20)

    return {
        "total_rules": rule_count,
        "active_rules": active_rules,
        "channel_count": channel_count,
        "active_promotions": promo_count,
        "active_guardrails": guardrail_count,
        "rules_by_category": by_category,
        "active_channels": channels,
    }
