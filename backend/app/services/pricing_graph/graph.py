from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Literal

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services.pricing_rules import PricingRulesService
from app.errors import AppError


PricingNodeType = Literal["seller", "reseller", "buyer"]


@dataclass
class PricingStep:
    level: int
    tenant_id: Optional[str]
    node_type: PricingNodeType
    rule_id: Optional[str]
    markup_pct: float
    base_amount: float
    delta_amount: float
    amount_after: float
    currency: str
    notes: List[str]


@dataclass
class PricingGraphResult:
    base_price: Dict[str, Any]
    final_price: Dict[str, Any]
    applied_total_markup_pct: Optional[float]
    pricing_rule_ids: List[str]
    pricing_trace: List[str]
    graph_path: List[str]
    steps: List[PricingStep]
    model_version: str = "pricing_graph_v1"


async def resolve_tenant_path(
    db: AsyncIOMotorDatabase,
    *,
    organization_id: str,
    buyer_tenant_id: str,
) -> List[str]:
    """Resolve buyer -> parent1 -> parent2 ... chain (max 10 hops).

    - Uses tenant_pricing_links collection
    - Fails open on cycles or >10 hops by truncating the path
    """

    path: List[str] = []
    seen: set[str] = set()
    current = buyer_tenant_id

    for _ in range(10):
        if not current or current in seen:
            break
        path.append(current)
        seen.add(current)

        link = await db.tenant_pricing_links.find_one(
            {"organization_id": organization_id, "tenant_id": current},
            {"_id": 0, "parent_tenant_id": 1},
        )
        parent = (link or {}).get("parent_tenant_id")
        if not parent:
            break
        current = str(parent)

    return path


async def _resolve_markup_for_tenant(
    db: AsyncIOMotorDatabase,
    *,
    organization_id: str,
    tenant_id: Optional[str],
    currency: str,
    base_amount: float,
    context: Dict[str, Any],
) -> tuple[float, Optional[str], List[str]]:
    """Resolve markup_pct and rule_id for a single tenant node.

    - Reuses existing PricingRulesService (agency_id == tenant_id)
    - currency mismatch handled at caller level
    """

    notes: List[str] = []
    if not tenant_id:
        # No tenant: no rule, zero markup
        return 0.0, None, ["base"]

    rules_svc = PricingRulesService(db)

    check_in = context.get("check_in")
    product_type = context.get("product_type") or "hotel"
    product_id = context.get("product_id")

    winner_rule = None
    try:
        if check_in is not None:
            winner_rule = await rules_svc.resolve_winner_rule(
                organization_id=organization_id,
                agency_id=tenant_id,
                product_id=product_id,
                product_type=product_type,
                check_in=check_in,
            )
    except AppError as exc:
        # Fail-open for pricing rule misconfiguration
        notes.append(f"pricing_rule_error:{exc.code}")
        return 0.0, None, notes

    if not winner_rule:
        notes.append("no_rule")
        return 0.0, None, notes

    try:
        pct = await rules_svc.resolve_markup_percent(
            organization_id,
            agency_id=tenant_id,
            product_id=product_id,
            product_type=product_type,
            check_in=check_in,
        )
    except AppError as exc:
        notes.append(f"pricing_rule_error:{exc.code}")
        return 0.0, None, notes

    rule_id = str(winner_rule.get("_id")) if winner_rule.get("_id") is not None else None
    return float(pct or 0.0), rule_id, notes


async def price_offer_with_graph(
    db: AsyncIOMotorDatabase,
    *,
    organization_id: str,
    buyer_tenant_id: Optional[str],
    base_amount: float,
    currency: str,
    context: Dict[str, Any],
) -> Optional[PricingGraphResult]:
    """Compute hierarchical B2B pricing graph for a single offer.

    Fail-open semantics:
    - If buyer_tenant_id missing or base_amount<=0 or no currency -> None (no overlay)
    - If internal error occurs, falls back to zero markup and records pricing_graph_error in notes
    """

    if not buyer_tenant_id or base_amount <= 0 or not currency:
        return None

    steps: List[PricingStep] = []
    pricing_rule_ids: List[str] = []
    pricing_trace: List[str] = []
    notes_global: List[str] = []

    # Level 0: base seller step (no tenant)
    current_amount = float(base_amount)
    step0 = PricingStep(
        level=0,
        tenant_id=None,
        node_type="seller",
        rule_id=None,
        markup_pct=0.0,
        base_amount=current_amount,
        delta_amount=0.0,
        amount_after=current_amount,
        currency=currency,
        notes=["base"],
    )
    steps.append(step0)
    pricing_trace.append(f"base={current_amount}")

    try:
        path = await resolve_tenant_path(db, organization_id=organization_id, buyer_tenant_id=buyer_tenant_id)
    except Exception as exc:  # pragma: no cover - defensive
        # Hard failure resolving path: fall back to zero markup but keep base
        notes_global.append(f"pricing_graph_error:path:{type(exc).__name__}")
        base_price = {"amount": float(base_amount), "currency": currency}
        final_price = {"amount": float(current_amount), "currency": currency}
        return PricingGraphResult(
            base_price=base_price,
            final_price=final_price,
            applied_total_markup_pct=0.0,
            pricing_rule_ids=[],
            pricing_trace=pricing_trace,
            graph_path=[],
            steps=steps,
        )

    graph_path = list(path)

    # Iterate buyer + parents
    for level_offset, tenant_id in enumerate(path, start=1):
        # Resolve rule for this tenant
        try:
            markup_pct, rule_id, node_notes = await _resolve_markup_for_tenant(
                db,
                organization_id=organization_id,
                tenant_id=tenant_id,
                currency=currency,
                base_amount=current_amount,
                context=context,
            )
        except Exception as exc:  # pragma: no cover - defensive
            # Fail-open: no markup change
            markup_pct = 0.0
            rule_id = None
            node_notes = [f"pricing_graph_error:node:{type(exc).__name__}"]

        node_type: PricingNodeType = "buyer" if level_offset == 1 else "reseller"

        # Currency mismatch handling is already external at rule layer (rules are currency-agnostic here).
        # Clamp negative results
        delta = current_amount * (markup_pct / 100.0)
        amount_after = current_amount + delta
        node_notes_local = list(node_notes)
        if amount_after < 0.0:
            amount_after = 0.0
            delta = -current_amount
            node_notes_local.append("clamped_to_zero")

        step = PricingStep(
            level=level_offset,
            tenant_id=tenant_id,
            node_type=node_type,
            rule_id=rule_id,
            markup_pct=float(markup_pct),
            base_amount=current_amount,
            delta_amount=delta,
            amount_after=amount_after,
            currency=currency,
            notes=node_notes_local,
        )
        steps.append(step)
        current_amount = amount_after

        if rule_id:
            pricing_rule_ids.append(rule_id)

        role_label = "buyer" if node_type == "buyer" else "parent"
        pricing_trace.append(f"{role_label}=+{markup_pct}% -> {amount_after}")

    # Final synthetic trace entry
    pricing_trace.append(f"final={current_amount}")

    base_price = {"amount": float(base_amount), "currency": currency}
    final_price = {"amount": float(current_amount), "currency": currency}

    applied_total_markup_pct: Optional[float]
    if base_amount > 0:
        applied_total_markup_pct = ((current_amount / float(base_amount)) - 1.0) * 100.0
    else:
        applied_total_markup_pct = None

    return PricingGraphResult(
        base_price=base_price,
        final_price=final_price,
        applied_total_markup_pct=applied_total_markup_pct,
        pricing_rule_ids=pricing_rule_ids,
        pricing_trace=pricing_trace,
        graph_path=graph_path,
        steps=steps,
    )
