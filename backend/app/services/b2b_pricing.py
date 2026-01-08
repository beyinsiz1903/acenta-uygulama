from __future__ import annotations

from datetime import timedelta
from typing import List, Dict, Any

from bson import ObjectId
from app.schemas_b2b_quotes import (
    QuoteItemRequest,
    QuoteCreateRequest,
    QuoteCreateResponse,
    QuoteOffer,
    PriceRestriction,
    PricingTrace,
)
from app.errors import AppError
from app.utils import now_utc


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

    async def _ensure_product_sellable(self, organization_id: str, product_id: str) -> dict:
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
        await self._ensure_product_sellable(organization_id, item.product_id)

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
        # Determine target selling currency (EUR or TRY)
        target_currency = (target_currency or "EUR").upper()

        # For now, we only support EUR and TRY explicitly
        if target_currency not in {"EUR", "TRY"}:
            raise AppError(
                422,
                "unsupported_currency",
                f"Unsupported selling currency: {target_currency}",
                {"target_currency": target_currency},
            )

        # Dummy pricing in base currency (EUR) from inventory
        base_price_eur = float(inv_doc.get("price") or 100.0)

        # P1.1: simple FX handling for TRY; functional currency is EUR
        if target_currency == "EUR":
            net = round(base_price_eur, 2)
            sell = round(base_price_eur * 1.1, 2)
            currency = "EUR"
        else:
            # SELLING IN TRY: convert EUR base to TRY using FXService
            from decimal import Decimal, ROUND_HALF_UP
            from app.services.fx import FXService

            fx_svc = FXService(self.db)
            fx = await fx_svc.get_rate(organization_id, quote="TRY")

            rate = Decimal(str(fx.rate))
            net_eur = Decimal(str(base_price_eur))
        # Determine selling currency from agency settings (feature flag)
        agency = await self.db.agencies.find_one({"_id": agency_id, "organization_id": organization_id})
        settings = (agency or {}).get("settings") or {}
        target_currency = (settings.get("selling_currency") or "EUR").upper()


            net_try_internal = (net_eur * rate).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            sell_try_internal = (net_try_internal * Decimal("1.1")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

            net = float(net_try_internal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
            sell = float(sell_try_internal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
            currency = "TRY"


        # NOTE: net/sell/currency are now computed above based on target_currency

        restrictions = PriceRestriction(
            min_stay=1,
            stop_sell=False,
            allotment_available=int(inv_doc.get("capacity_available", 0)),
        )
        trace = PricingTrace(applied_rules=[])

        return QuoteOffer(
            item_key="0",  # caller will override with actual index
            currency=currency,
            net=net,
            sell=sell,
            restrictions=restrictions,
            trace=trace,
        )

    async def create_quote(
        self,
        *,
        organization_id: str,
        agency_id: str,
        channel_id: str,
        payload: QuoteCreateRequest,
        requested_by_email: str | None,
    ) -> QuoteCreateResponse:
        # Price each item
        offers: List[QuoteOffer] = []
        for idx, item in enumerate(payload.items):
            offer = await self._price_item(
                organization_id,
                agency_id,
                channel_id,
                item,
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
        }
        res = await self.price_quotes.insert_one(doc)
        quote_id = str(res.inserted_id)

        return QuoteCreateResponse(quote_id=quote_id, expires_at=expires_at, offers=offers)

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
