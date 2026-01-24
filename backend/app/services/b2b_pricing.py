from __future__ import annotations

from datetime import timedelta
from typing import List, Dict, Any
from decimal import Decimal, ROUND_HALF_UP

from bson import ObjectId
from app.schemas_b2b_quotes import (
    QuoteItemRequest,
    QuoteCreateRequest,
    QuoteCreateResponse,
    QuoteOffer,
    PriceRestriction,
    PricingTrace,
)
from app.services.coupons import CouponService
from app.errors import AppError
from app.utils import now_utc
from app.services.pricing_rules import PricingRulesService
from app.services.b2b_discounts import resolve_discount_group, apply_discount


class B2BPricingService:
    """Pricing & quote creation for B2B flow.

    NOTE: This is a first MVP shell that should be wired into real
    catalog + inventory + contract + rules logic.
    """

    def __init__(self, db):
        self.db = db
        self.products = db.products
        self.inventory = db.inventory
        self.price_quotes = db.price_quotes
        self.coupons = CouponService(db)

    async def _resolve_partner_for_agency(self, organization_id: str, agency_id: str | None) -> str | None:
        """Resolve linked partner for a given agency, if any.

        V1 semantics:
        - Uses partner_profiles.linked_agency_id to link an agency to a partner
        - Returns partner _id as string or None if no link is configured
        """

        if not agency_id:
            return None

        # linked_agency_id may store string or ObjectId-like; compare as string
        q: dict[str, Any] = {
            "organization_id": organization_id,
            "linked_agency_id": {"$in": [str(agency_id), agency_id]},
            "status": "approved",
        }
        doc = await self.db.partner_profiles.find_one(q, {"_id": 1})
        if not doc:
            return None
        return str(doc.get("_id"))

    async def _ensure_product_sellable(self, organization_id: str, product_id: str, agency_id: str | None) -> dict:
        # Convert string product_id to ObjectId for MongoDB lookup
        try:
            product_oid = ObjectId(product_id)
        except Exception:
            raise AppError(
                409,
                "product_not_available",
                "Invalid product ID format",
                {"product_id": str(product_id)},
            )

        doc = await self.products.find_one(
            {"organization_id": organization_id, "_id": product_oid, "status": "active"},
            {"_id": 1},
        )
        if not doc:
            raise AppError(
                409,
                "product_not_available",
                "Product is not available for sale",
                {"product_id": str(product_id)},
            )

        # Optional B2B Marketplace gating: if agency is linked to a partner and
        # there is an authorization document for this product, require it to be enabled.
        partner_id = await self._resolve_partner_for_agency(organization_id, agency_id)
        if partner_id:
            auth = await self.db.b2b_product_authorizations.find_one(
                {
                    "organization_id": organization_id,
                    "partner_id": partner_id,
                    "product_id": product_oid,
                }
            )
            is_enabled = bool(auth and auth.get("is_enabled"))
            if not is_enabled:
                raise AppError(
                    409,
                    "product_not_available",
                    "Product is not enabled for this partner",
                    {"product_id": str(product_id), "partner_id": partner_id},
                )

        return doc

    async def _price_item(
        self,
        organization_id: str,
        agency_id: str,
        channel_id: str,
        item: QuoteItemRequest,
        target_currency: str = "EUR",
    ) -> QuoteOffer:
        # TODO: integrate real inventory + contract + rules pricing.
        await self._ensure_product_sellable(organization_id, item.product_id, agency_id)

        # Convert string product_id to ObjectId for inventory lookup
        try:
            product_oid = ObjectId(item.product_id)
        except Exception:
            raise AppError(
                409,
                "product_not_available",
                "Invalid product ID format",
                {"product_id": str(item.product_id)},
            )

        # For now, we fake availability using inventory collection if present
        inv_doc = await self.inventory.find_one(
            {
                "organization_id": organization_id,
                "product_id": product_oid,
                "date": item.check_in.isoformat(),
            }
        )
        if not inv_doc or inv_doc.get("capacity_available", 0) <= 0 or inv_doc.get("restrictions", {}).get(
            "closed", False
        ):
            raise AppError(
                409,
                "unavailable",
                "No availability for requested dates",
                {
                    "product_id": item.product_id,
                    "room_type_id": item.room_type_id,
                    "check_in": item.check_in.isoformat(),
                    "check_out": item.check_out.isoformat(),
                },
            )

        # For now, we only support EUR and TRY explicitly
        if target_currency not in {"EUR", "TRY"}:
            raise AppError(
                422,
                "unsupported_currency",
                f"Unsupported selling currency: {target_currency}",
                {"target_currency": target_currency},
            )

        # Base price in functional currency (EUR) from inventory
        base_price_eur = float(inv_doc.get("price") or 100.0)
        net_eur_internal = Decimal(str(base_price_eur))

        # P1.2: resolve markup from pricing rules
        rules_svc = PricingRulesService(self.db)
        # QuoteItemRequest.check_in is already a date; service normalises datetime/date
        winner_rule = await rules_svc.resolve_winner_rule(
            organization_id=organization_id,
            agency_id=agency_id,
            product_id=item.product_id,
            product_type="hotel",
            check_in=item.check_in,
        )
        if winner_rule is not None:
            markup_percent = await rules_svc.resolve_markup_percent(
                organization_id,
                agency_id=agency_id,
                product_id=item.product_id,
                product_type="hotel",
                check_in=item.check_in,
            )
            winner_rule_id = str(winner_rule.get("_id"))
            notes = winner_rule.get("notes")
            if isinstance(notes, str):
                notes = notes.strip()
            priority = winner_rule.get("priority")
            winner_rule_name = notes or (f"priority={priority}" if priority is not None else "simple_rule")
            fallback = False
        else:
            markup_percent = 10.0
            winner_rule_id = None
            winner_rule_name = "DEFAULT_10"
            fallback = True

        # Phase 1 money model: supplier_cost and list_sell before discounts/commissions
        supplier_cost_eur = net_eur_internal
        factor = Decimal("1") + (Decimal(str(markup_percent)) / Decimal("100"))

        if target_currency == "EUR":
            # EUR selling: apply markup on EUR net
            sell_eur_internal = (supplier_cost_eur * factor).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            net = float(supplier_cost_eur.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
            list_sell = float(sell_eur_internal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
            currency = "EUR"
        else:
            # SELLING IN TRY: convert EUR base to TRY using FXService, then apply markup in TRY
            from app.services.fx import FXService

            fx_svc = FXService(self.db)
            fx = await fx_svc.get_rate(organization_id, quote="TRY")

            rate = Decimal(str(fx.rate))
            supplier_cost_try = (supplier_cost_eur * rate).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            list_sell_try = (supplier_cost_try * factor).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

            net = float(supplier_cost_try.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
            list_sell = float(list_sell_try.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
            currency = "TRY"

        # NOTE: net/list_sell/currency are now computed above based on target_currency and rules

        restrictions = PriceRestriction(
            min_stay=1,
            stop_sell=False,
            allotment_available=int(inv_doc.get("capacity_available", 0)),
        )
        trace = PricingTrace(
            applied_rules=[],
            winner_rule_id=winner_rule_id,
            winner_rule_name=winner_rule_name,
            fallback=fallback,
        )

        # Apply B2B discount group (markup_only v1)
        from datetime import date as _date

        check_in_date = item.check_in if isinstance(item.check_in, _date) else None
        discount_group = await resolve_discount_group(
            self.db,
            organization_id=organization_id,
            agency_id=agency_id,
            product_id=item.product_id,
            product_type="hotel",
            check_in=check_in_date,
        )

        discount_result = apply_discount(
            base_net=net,
            base_sell=list_sell,
            markup_percent=float(markup_percent or 0.0),
            group=discount_group,
        )

        final_net = discount_result["final_net"]
        final_sell = discount_result["final_sell"]
        trace_discount = discount_result["trace_discount"]

        # Extend trace with discount info (trace field names aligned with booking)
        if trace_discount:
            trace.rule_effects = (trace.rule_effects or []) + [
                {
                    "type": "b2b_discount",
                    "discount_group_id": trace_discount["discount_group_id"],
                    "discount_group_name": trace_discount["discount_group_name"],
                    "discount_percent": trace_discount["discount_percent"],
                    "discount_amount": trace_discount["discount_amount"],
                }
            ]
            # Only set fields that exist in PricingTrace model
            trace.discount_group_id = trace_discount["discount_group_id"]
            trace.discount_group_name = trace_discount["discount_group_name"]
            trace.discount_percent = trace_discount["discount_percent"]
            trace.discount_amount = trace_discount["discount_amount"]

        # Commission rate resolution will be applied at aggregate level in create_quote

        return QuoteOffer(
            item_key="0",  # caller will override with actual index
            currency=currency,
            net=final_net,
            sell=final_sell,
            restrictions=restrictions,
            trace=trace,
            supplier_cost=float(round(net, 2)),
            base_markup_percent=float(markup_percent or 0.0),
            list_sell=float(round(list_sell, 2)),
        )

    async def create_quote(
        self,
        *,
        organization_id: str,
        agency_id: str,
        # Resolve partner for commission purposes (if any)
        partner_id: str | None = await self._resolve_partner_for_agency(organization_id, agency_id)


        channel_id: str,
        payload: QuoteCreateRequest,
        requested_by_email: str | None,
    ) -> QuoteCreateResponse:
        # Price each item
        offers: List[QuoteOffer] = []

        # Determine selling currency once per quote based on agency settings
        agency = await self.db.agencies.find_one({"_id": str(agency_id), "organization_id": organization_id})
        settings = (agency or {}).get("settings") or {}
        target_currency = (settings.get("selling_currency") or "EUR").upper()

        for idx, item in enumerate(payload.items):
            offer = await self._price_item(
                organization_id=organization_id,
                agency_id=agency_id,
                channel_id=channel_id,
                item=item,
                target_currency=target_currency,
            )
            offer.item_key = str(idx)
            offers.append(offer)

        now = now_utc()
        expires_at = now + timedelta(minutes=10)

        # Serialize items for storage: ensure date fields are JSON/Mongo friendly (ISO strings)
        items_serialized = []
        for i in payload.items:
            data = i.model_dump()
            # Convert date objects to ISO strings for MongoDB compatibility
            if isinstance(data.get("check_in"), (str,)):
                pass
            else:
                data["check_in"] = i.check_in.isoformat()
            if isinstance(data.get("check_out"), (str,)):
                pass
            else:
                data["check_out"] = i.check_out.isoformat()
            items_serialized.append(data)

        # Winner rule trace at quote level (from first offer, if any)
        winner_rule_id = None
        winner_rule_name = None
        fallback = None
        if offers:
            first_trace = offers[0].trace
            winner_rule_id = first_trace.winner_rule_id
            winner_rule_name = first_trace.winner_rule_name
            fallback = first_trace.fallback

        doc = {
            "organization_id": organization_id,
            "agency_id": agency_id,
            "channel_id": channel_id,
            "items": items_serialized,
            "offers": [o.model_dump() for o in offers],
            "expires_at": expires_at,
            "created_at": now,
            "requested_by_email": requested_by_email,
            "client_context": payload.client_context or {},
            "winner_rule_id": winner_rule_id,
            "winner_rule_name": winner_rule_name,
            "pricing_trace": {
                "source": "simple_pricing_rules",
                "resolution": "winner_takes_all",
                "fallback": bool(fallback),
            } if winner_rule_name is not None else None,
        }
        res = await self.price_quotes.insert_one(doc)
        quote_id = str(res.inserted_id)
        return QuoteCreateResponse(quote_id=quote_id, expires_at=expires_at, offers=offers)

    async def apply_coupon_to_quote(
        self,
        *,
        organization_id: str,
        agency_id: str,
        quote_id: str,
        code: str,
    ) -> dict[str, Any]:
        """Apply a coupon code to an existing quote and recalculate totals.

        Returns the updated quote document (Mongo shape).
        """

        quote = await self.ensure_quote_valid(
            organization_id=organization_id,
            agency_id=agency_id,
            quote_id=quote_id,
        )

        coupon_doc, result = await self.coupons.evaluate_for_quote(
            organization_id=organization_id,
            agency_id=agency_id,
            quote=quote,
            code=code,
        )

        coupon_payload: dict[str, Any] = {
            "code": code.strip().upper(),
            "status": result["status"],
            "amount_cents": result["amount_cents"],
            "currency": result["currency"],
            "reason": result["reason"],
        }
        if coupon_doc:
            coupon_payload["coupon_id"] = str(coupon_doc.get("_id"))

        # Compute totals: base_total from offers, coupon_total from result
        offers = quote.get("offers") or []
        base_total = sum(float(o.get("sell") or 0.0) for o in offers)
        coupon_total = result["amount_cents"] / 100.0
        final_total = base_total - coupon_total

        totals = {
            "base_total": base_total,
            "coupon_total": coupon_total,
            "final_total": final_total,
            "currency": result["currency"],
        }

        update_doc = {
            "coupon": coupon_payload,
            "totals": totals,
        }

        from bson import ObjectId

        await self.price_quotes.update_one(
            {"_id": ObjectId(quote_id)},
            {"$set": update_doc},
        )

        quote.update(update_doc)
        
        # Convert ObjectId to string for JSON serialization
        if "_id" in quote:
            quote["_id"] = str(quote["_id"])
        
        return quote

    async def clear_coupon_from_quote(
        self,
        *,
        organization_id: str,
        agency_id: str,
        quote_id: str,
    ) -> dict[str, Any]:
        """Remove coupon info from a quote (reset totals to base)."""

        quote = await self.ensure_quote_valid(
            organization_id=organization_id,
            agency_id=agency_id,
            quote_id=quote_id,
        )

        offers = quote.get("offers") or []
        base_total = sum(float(o.get("sell") or 0.0) for o in offers)
        currency = offers[0].get("currency") if offers else "EUR"

        totals = {
            "base_total": base_total,
            "coupon_total": 0.0,
            "final_total": base_total,
            "currency": currency,
        }

        from bson import ObjectId

        await self.price_quotes.update_one(
            {"_id": ObjectId(quote_id)},
            {"$unset": {"coupon": ""}, "$set": {"totals": totals}},
        )

        quote.pop("coupon", None)
        quote["totals"] = totals
        
        # Convert ObjectId to string for JSON serialization
        if "_id" in quote:
            quote["_id"] = str(quote["_id"])
        
        return quote

    async def ensure_quote_valid(
        self,
        *,
        organization_id: str,
        agency_id: str,
        quote_id: str,
    ) -> dict[str, Any]:
        from bson import ObjectId

        try:
            oid = ObjectId(quote_id)
        except Exception:
            raise AppError(404, "not_found", "Quote not found", {"quote_id": quote_id})

        doc = await self.price_quotes.find_one(
            {"_id": oid, "organization_id": organization_id, "agency_id": agency_id}
        )
        if not doc:
            raise AppError(404, "not_found", "Quote not found", {"quote_id": quote_id})

        if doc.get("expires_at"):
            expires_at = doc["expires_at"]
            # Normalize to naive UTC for comparison if timezone-aware
            from datetime import timezone

            if hasattr(expires_at, "tzinfo") and expires_at.tzinfo is not None:
                expires_at_cmp = expires_at.astimezone(timezone.utc).replace(tzinfo=None)
            else:
                expires_at_cmp = expires_at

            now_naive = now_utc().replace(tzinfo=None)
            if expires_at_cmp < now_naive:
                raise AppError(409, "quote_expired", "Quote has expired", {"quote_id": quote_id})

        return doc
