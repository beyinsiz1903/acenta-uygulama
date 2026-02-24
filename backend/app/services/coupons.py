from __future__ import annotations

"""Coupon evaluation and application service (FAZ 5)."""

from typing import Any, Dict, Optional, Tuple

from bson import ObjectId

from app.utils import now_utc


class CouponService:
    def __init__(self, db):
        self.db = db

    async def _find_coupon(self, organization_id: str, code: str) -> Optional[Dict[str, Any]]:
        now = now_utc()
        doc = await self.db.coupons.find_one(
            {
                "organization_id": organization_id,
                "code": code,
                "active": True,
                "valid_from": {"$lte": now},
                "valid_to": {"$gte": now},
            }
        )
        return doc

    async def evaluate_for_quote(
        self,
        *,
        organization_id: str,
        agency_id: str,
        quote: Dict[str, Any],
        code: str,
    ) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
        """Evaluate coupon for a quote and compute discount.

        Returns (coupon_doc_or_None, result_dict).
        result_dict contains fields like:
        - status: "APPLIED" | "NOT_FOUND" | "EXPIRED" | "LIMIT_REACHED" | "NOT_ELIGIBLE"
        - amount_cents: int
        - currency: str
        - reason: str (human readable)
        """

        norm_code = code.strip().upper()
        if not norm_code:
            return None, {
                "status": "INVALID",
                "amount_cents": 0,
                "currency": quote.get("currency") or "EUR",
                "reason": "EMPTY_CODE",
            }

        coupon = await self._find_coupon(organization_id, norm_code)
        if not coupon:
            return None, {
                "status": "NOT_FOUND",
                "amount_cents": 0,
                "currency": quote.get("currency") or "EUR",
                "reason": "Coupon not found or inactive",
            }

        # Usage limit
        limit = coupon.get("usage_limit")
        used = int(coupon.get("usage_count") or 0)
        if limit is not None and used >= limit:
            return coupon, {
                "status": "LIMIT_REACHED",
                "amount_cents": 0,
                "currency": coupon.get("currency") or quote.get("currency") or "EUR",
                "reason": "Coupon usage limit reached",
            }

        scope = coupon.get("scope") or "B2B"
        if scope != "B2B":
            # Şimdilik sadece B2B quotes destekleniyor
            return coupon, {
                "status": "NOT_ELIGIBLE",
                "amount_cents": 0,
                "currency": coupon.get("currency") or quote.get("currency") or "EUR",
                "reason": "Coupon scope is not B2B",
            }

        # Quote toplamı: price_quotes dokümanında offers listesi var
        offers = quote.get("offers") or []
        if not offers:
            return coupon, {
                "status": "NOT_ELIGIBLE",
                "amount_cents": 0,
                "currency": coupon.get("currency") or quote.get("currency") or "EUR",
                "reason": "Quote has no offers",
            }

        # Varsayım: tüm offers aynı para biriminde
        currency = offers[0].get("currency") or quote.get("currency") or "EUR"
        total_sell = sum(float(o.get("sell") or 0.0) for o in offers)

        min_total = float(coupon.get("min_total") or 0.0)
        if total_sell < min_total:
            return coupon, {
                "status": "NOT_ELIGIBLE",
                "amount_cents": 0,
                "currency": currency,
                "reason": "Quote total below coupon minimum",
            }

        discount_type = coupon.get("discount_type") or "PERCENT"
        value = float(coupon.get("value") or 0.0)

        amount = 0.0
        if discount_type == "PERCENT":
            amount = total_sell * (value / 100.0)
        elif discount_type == "AMOUNT":
            amount = min(value, total_sell)

        if amount <= 0:
            return coupon, {
                "status": "NOT_ELIGIBLE",
                "amount_cents": 0,
                "currency": currency,
                "reason": "Coupon produces zero discount",
            }

        amount_cents = int(round(amount * 100))

        return coupon, {
            "status": "APPLIED",
            "amount_cents": amount_cents,
            "currency": currency,
            "reason": "OK",
        }

    async def increment_usage(self, coupon_id: Any) -> None:
        """Increment global usage counter only (B2B backward compatibility)."""
        try:
            oid = ObjectId(coupon_id)
        except Exception:
            return
        await self.db.coupons.update_one({"_id": oid}, {"$inc": {"usage_count": 1}})

    async def increment_usage_for_customer(self, coupon_id: Any, customer_key: Optional[str] = None) -> None:
        """Increment usage counters for public/B2C checkout.

        - Always increments global usage_count.
        - If customer_key sa1fe ise usage_per_customer.<key> alan31n31 art31r31r.
        """
        try:
            oid = ObjectId(coupon_id)
        except Exception:
            return

        inc: Dict[str, Any] = {"usage_count": 1}
        if customer_key:
            # Email gibi değerleri Mongo field key olarak güvenli hale getir
            safe_key = customer_key.strip().lower().replace(" ", "_").replace(".", "_").replace("$", "_")
            if safe_key:
                inc[f"usage_per_customer.{safe_key}"] = 1

        await self.db.coupons.update_one({"_id": oid}, {"$inc": inc})

    async def evaluate_for_public_quote(
        self,
        *,
        organization_id: str,
        quote: Dict[str, Any],
        code: str,
        customer_key: Optional[str] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
        """Evaluate coupon for a public (B2C) quote.

        Beklenen quote dokümanı public_quotes koleksiyonundan gelen kayıttır.
        amount_cents alanını kullanarak toplam tutar hesaplanır.
        """

        norm_code = code.strip().upper()
        if not norm_code:
            return None, {
                "status": "INVALID",
                "amount_cents": 0,
                "currency": (quote.get("currency") or "EUR").upper(),
                "reason": "EMPTY_CODE",
            }

        coupon = await self._find_coupon(organization_id, norm_code)
        if not coupon:
            return None, {
                "status": "NOT_FOUND",
                "amount_cents": 0,
                "currency": (quote.get("currency") or "EUR").upper(),
                "reason": "Coupon not found or inactive",
            }

        # Global usage limit
        limit = coupon.get("usage_limit")
        used = int(coupon.get("usage_count") or 0)
        if limit is not None and used >= limit:
            return coupon, {
                "status": "LIMIT_REACHED",
                "amount_cents": 0,
                "currency": (quote.get("currency") or "EUR").upper(),
                "reason": "Coupon usage limit reached",
            }

        # Per-customer limit (email bazlı)
        per_limit = coupon.get("per_customer_limit")
        if per_limit is not None and customer_key:
            usage_map = coupon.get("usage_per_customer") or {}
            safe_key = customer_key.strip().lower().replace(" ", "_").replace(".", "_").replace("$", "_")
            used_by_customer = int(usage_map.get(safe_key) or 0)
            if used_by_customer >= per_limit:
                return coupon, {
                    "status": "LIMIT_PER_CUSTOMER",
                    "amount_cents": 0,
                    "currency": (quote.get("currency") or "EUR").upper(),
                    "reason": "Customer usage limit reached",
                }

        # Scope: yalnızca B2C veya BOTH kabul edilir
        scope = (coupon.get("scope") or "B2C").upper()
        if scope not in {"B2C", "BOTH"}:
            return coupon, {
                "status": "NOT_ELIGIBLE",
                "amount_cents": 0,
                "currency": (quote.get("currency") or "EUR").upper(),
                "reason": "Coupon scope not allowed for B2C",
            }

        # Public quote toplam31: amount_cents alan31 (int)
        currency = (quote.get("currency") or "EUR").upper()
        total_amount_cents = int(quote.get("amount_cents") or 0)
        total_amount = total_amount_cents / 100.0

        min_total = float(coupon.get("min_total") or 0.0)
        if total_amount < min_total:
            return coupon, {
                "status": "NOT_ELIGIBLE",
                "amount_cents": 0,
                "currency": currency,
                "reason": "Quote total below coupon minimum",
            }

        discount_type = coupon.get("discount_type") or "PERCENT"
        value = float(coupon.get("value") or 0.0)

        amount = 0.0
        if discount_type == "PERCENT":
            amount = total_amount * (value / 100.0)
        elif discount_type == "AMOUNT":
            amount = min(value, total_amount)

        if amount <= 0:
            return coupon, {
                "status": "NOT_ELIGIBLE",
                "amount_cents": 0,
                "currency": currency,
                "reason": "Coupon produces zero discount",
            }

        amount_cents = int(round(amount * 100))

        return coupon, {
            "status": "APPLIED",
            "amount_cents": amount_cents,
            "currency": currency,
            "reason": "OK",
        }
