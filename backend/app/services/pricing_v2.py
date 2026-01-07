from __future__ import annotations

from datetime import datetime, date
from typing import Any, Dict, List, Optional, Tuple

from bson import ObjectId
from pymongo import DESCENDING

from app.errors import AppError
from app.utils import now_utc, safe_int, safe_float, model_dump
from app.schemas_pricing import (
    PricingTraceRequestContext,
    PricingTraceStep,
    PricingTraceFinal,
    PricingTraceResponse,
)


def _parse_date(s: str) -> date:
    return date.fromisoformat(s[:10])


# ---- Contract selection: tek kazanan ----


async def select_best_contract(
    db,
    organization_id: str,
    ctx: PricingTraceRequestContext,
) -> dict[str, Any]:
    """Single winning contract selection.

    Specificity priority:
    1) agency_id match > channel_id match > market match > product match > org default
    2) valid_from/valid_to covers check-in
    3) created_at DESC (tie-breaker)
    """

    ci = _parse_date(ctx.check_in)
    base_and: List[Dict[str, Any]] = [
        {"$or": [{"valid_from": None}, {"valid_from": {"$lte": ci}}]},
        {"$or": [{"valid_to": None}, {"valid_to": {"$gte": ci}}]},
    ]

    # Agency: exact match or unbound
    if ctx.agency_id:
        base_and.append({"$or": [{"agency_id": ctx.agency_id}, {"agency_id": None}]})

    # Channel: exact match or unbound
    if ctx.channel_id:
        base_and.append({"$or": [{"channel_id": ctx.channel_id}, {"channel_id": None}]})

    # Market: contains market or markets empty/unset
    if ctx.market:
        base_and.append(
            {
                "$or": [
                    {"markets": ctx.market},
                    {"markets": {"$size": 0}},
                    {"markets": None},
                ]
            }
        )

    # Product: includes product_id or empty/unset
    base_and.append(
        {
            "$or": [
                {"product_ids": ctx.product_id},
                {"product_ids": {"$size": 0}},
                {"product_ids": None},
            ]
        }
    )

    q: Dict[str, Any] = {
        "organization_id": organization_id,
        "status": "active",
        "$and": base_and,
    }

    docs = await db.pricing_contracts.find(q).sort("created_at", DESCENDING).to_list(500)

    if not docs:
        raise AppError(404, "no_contract_found", "No pricing contract found for context", {"ctx": model_dump(ctx)})

    def specificity_score(c: dict[str, Any]) -> int:
        score = 0
        if ctx.agency_id and c.get("agency_id") == ctx.agency_id:
            score += 16
        if ctx.channel_id and c.get("channel_id") == ctx.channel_id:
            score += 8
        if ctx.market and ctx.market in (c.get("markets") or []):
            score += 4
        if ctx.product_id and ctx.product_id in (c.get("product_ids") or []):
            score += 2
        return score

    best = max(docs, key=specificity_score)
    best_score = specificity_score(best)

    # Org-default contract'a izin veriyoruz (score 0 olabilir)
    best["_match_score"] = best_score
    return best


# ---- Rate grid row selection: deterministik fallback ----


def _grid_row_matches(row: dict[str, Any], ctx: PricingTraceRequestContext) -> bool:
    ci = _parse_date(ctx.check_in)
    co = _parse_date(ctx.check_out)
    los = (co - ci).days

    if not (row["valid_from"] <= ci <= row["valid_to"]):
        return False
    if not (row["min_los"] <= los <= row["max_los"]):
        return False
    return True


async def select_grid_row(
    db,
    contract: dict[str, Any],
    ctx: PricingTraceRequestContext,
) -> Tuple[dict[str, Any], dict[str, Any]]:
    """Deterministic fallback order:

    1) product + rate_plan + room_type + board + occupancy
    2) room_type = null
    3) occupancy = null
    4) board = null
    (ileride explicit default flag eklenebilir)
    """

    org_id = contract["organization_id"]
    contract_id = contract["_id"]

    grids = await db.pricing_rate_grids.find(
        {
            "organization_id": org_id,
            "contract_id": contract_id,
            "product_id": ctx.product_id,
            "rate_plan_id": ctx.rate_plan_id,
        }
    ).to_list(50)

    if not grids:
        raise AppError(
            404,
            "no_rate_grid_found",
            "No pricing rate grid found for product/rate_plan",
            {"product_id": ctx.product_id, "rate_plan_id": ctx.rate_plan_id},
        )

    candidates: List[Tuple[int, dict[str, Any], dict[str, Any]]] = []

    ctx_board = (ctx.board or "").upper() or None

    for g in grids:
        for row in g.get("rows") or []:
            if not _grid_row_matches(row, ctx):
                continue

            score = 0

            # room_type exact vs null
            if ctx.room_type_id and g.get("room_type_id") == ctx.room_type_id:
                score += 8
            elif g.get("room_type_id") is None:
                score += 1

            # occupancy exact vs null
            occ = safe_int(row.get("occupancy")) if row.get("occupancy") is not None else None
            if occ is not None and occ == ctx.occupancy:
                score += 4
            elif row.get("occupancy") is None:
                score += 1

            # board exact vs null
            row_board = (row.get("board") or "").upper() or None
            if ctx_board and row_board and row_board == ctx_board:
                score += 2
            elif row.get("board") is None:
                score += 1

            candidates.append((score, g, row))

    if not candidates:
        raise AppError(
            404,
            "no_rate_grid_row_found",
            "No matching rate grid row found",
            {"product_id": ctx.product_id, "rate_plan_id": ctx.rate_plan_id},
        )

    best_score, best_grid, best_row = max(candidates, key=lambda x: x[0])
    best_grid["_match_score"] = best_score
    return best_grid, best_row


# ---- Rule evaluation ----


async def load_applicable_rules(
    db,
    organization_id: str,
    contract: dict[str, Any],
    ctx: PricingTraceRequestContext,
) -> List[dict[str, Any]]:
    """Load active rules roughly filtered by org.

    İnce filtreleme _rule_matches_scope içinde yapılır.
    """

    docs = await db.pricing_rules.find(
        {
            "organization_id": organization_id,
            "status": "active",
        }
    ).sort("priority", DESCENDING).to_list(500)
    return docs


def _rule_matches_scope(rule: dict[str, Any], contract: dict[str, Any], ctx: PricingTraceRequestContext) -> bool:
    s = rule.get("scope") or {}
    # contract_ids
    if s.get("contract_ids") and str(contract["_id"]) not in s["contract_ids"]:
        return False
    # channel_ids
    if s.get("channel_ids") and ctx.channel_id not in s["channel_ids"]:
        return False
    # agency_ids
    if s.get("agency_ids") and ctx.agency_id not in s["agency_ids"]:
        return False
    # markets
    if s.get("markets"):
        if not ctx.market or ctx.market not in s["markets"]:
            return False
    # product_ids
    if s.get("product_ids") and ctx.product_id not in s["product_ids"]:
        return False
    # rate_plan_ids
    if s.get("rate_plan_ids") and ctx.rate_plan_id not in s["rate_plan_ids"]:
        return False

    # date_from/date_to, booking window kontrolleri v2.0 için basit bırakıldı
    return True


def apply_rules_with_trace(
    rules: List[dict[str, Any]],
    contract: dict[str, Any],
    ctx: PricingTraceRequestContext,
    base_net: float,
) -> Tuple[float, float, List[PricingTraceStep]]:
    """Kuralları priority DESC sırasıyla uygula ve trace üret.

    v2.0 için: constraint ihlalinde CLAMP semantiğine hazır meta alanları var,
    ancak gerçek clamp mantığı sonraki iterasyonda eklenecek.
    """

    net = base_net
    sell = base_net
    steps: List[PricingTraceStep] = []

    # Base step
    steps.append(
        PricingTraceStep(
            type="grid_base",
            label="Base net from grid",
            net_before=None,
            net_after=net,
            sell_before=None,
            sell_after=sell,
            meta={},
        )
    )

    for r in rules:
        if not _rule_matches_scope(r, contract, ctx):
            continue

        action = r.get("action") or {}
        rule_id = str(r.get("_id"))
        rule_code = r.get("code") or ""
        label = r.get("label") or r.get("name") or rule_code

        before_net = net
        before_sell = sell

        t = action.get("type")
        mode = action.get("mode")
        value = safe_float(action.get("value"), 0.0)

        if t == "markup":
            if mode == "percent":
                sell = sell * (1.0 + value / 100.0)
            elif mode == "absolute":
                sell = sell + value
        elif t == "markdown":
            if mode == "percent":
                sell = sell * (1.0 - value / 100.0)
            elif mode == "absolute":
                sell = max(0.0, sell - value)
        elif t == "override":
            if mode == "absolute":
                sell = value

        meta: Dict[str, Any] = {
            "mode": mode,
            "value": value,
            "clamped": False,
            "clamp_reason": None,
            "min_margin": action.get("min_margin"),
            "max_discount": action.get("max_discount"),
        }

        steps.append(
            PricingTraceStep(
                type="rule",
                label=label,
                rule_id=rule_id,
                rule_code=rule_code,
                net_before=before_net,
                net_after=net,
                sell_before=before_sell,
                sell_after=sell,
                meta=meta,
            )
        )

    return net, sell, steps


# ---- Main entrypoint: quote pricing ----


async def price_quote_for_context(
    db,
    organization_id: str,
    ctx: PricingTraceRequestContext,
    quote_id: Optional[str] = None,
) -> Tuple[dict[str, Any], PricingTraceResponse]:
    """Main pricing entrypoint.

    - Single contract select
    - Grid row select
    - Apply rules with priority
    - Insert immutable trace
    - Return amounts + trace response
    """

    contract = await select_best_contract(db, organization_id, ctx)
    grid, row = await select_grid_row(db, contract, ctx)
    rules = await load_applicable_rules(db, organization_id, contract, ctx)

    base_net = safe_float(row.get("base_net"))
    net, sell, steps = apply_rules_with_trace(rules, contract, ctx, base_net)

    currency = grid.get("currency") or "EUR"
    final = PricingTraceFinal(net=net, sell=sell, currency=currency)

    trace_doc = {
        "organization_id": organization_id,
        "quote_id": quote_id,
        "request": model_dump(ctx),
        "contract": {
            "contract_id": str(contract["_id"]),
            "code": contract.get("code"),
            "match_score": contract.get("_match_score"),
        },
        "grid_match": {
            "grid_id": str(grid["_id"]),
            "match_score": grid.get("_match_score"),
            "row": row,
        },
        "steps": [s.dict() for s in steps],
        "final": final.dict(),
        "created_at": now_utc(),
    }

    res = await db.pricing_traces.insert_one(trace_doc)
    trace_id = str(res.inserted_id)

    trace_response = PricingTraceResponse(
        trace_id=trace_id,
        organization_id=organization_id,
        quote_id=quote_id,
        request=ctx,
        contract=trace_doc["contract"],
        grid_match=trace_doc["grid_match"],
        steps=steps,
        final=final,
        created_at=trace_doc["created_at"],
    )

    amounts = {"net": net, "sell": sell, "currency": currency, "pricing_trace_id": trace_id}
    return amounts, trace_response
