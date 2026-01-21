from __future__ import annotations

"""Public checkout & quote services for FAZ 2 / F2.T2.

Responsibilities:
- Create tenant-aware public quotes backed by products + rate_plans
- Enforce quote TTL and basic validation
- Provide helpers for public checkout (quote resolution, idempotency bookkeeping)

Pricing model (MVP):
- Uses the lowest active rate_plan.base_net_price for the product
- Multiplies by nights * rooms
- Applies a naive 10% tax/fee placeholder
- Returns canonical amount in cents
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from bson import ObjectId

from app.errors import AppError, PublicCheckoutErrorCode
from app.utils import now_utc
from app.services.b2b_discounts import resolve_discount_group, apply_discount


PUBLIC_QUOTE_TTL_MINUTES = 30


async def _resolve_partner_agency(db, organization_id: str, partner: str) -> Optional[Dict[str, Any]]:
    """Resolve partner (agency) document for public/partner flows.

    Accepts either string _id or ObjectId-compatible hex string. Returns the
    agency document or None when not found.
    """

    if not partner:
        return None

    # First, try direct string _id match (some schemas store _id as string)
    agency = await db.agencies.find_one({"_id": partner, "organization_id": organization_id})
    if agency:
        return agency

    # Fallback: attempt ObjectId
    try:
        from bson import ObjectId

        oid = ObjectId(partner)
    except Exception:
        return None

    agency = await db.agencies.find_one({"_id": oid, "organization_id": organization_id})
    return agency



@dataclass
class PublicQuote:
    quote_id: str
    organization_id: str
    product_id: str
    product_type: str
    date_from: date
    date_to: date
    nights: int
    adults: int
    children: int
    rooms: int
    currency: str
    amount_cents: int


async def create_public_quote(
    db,
    *,
    organization_id: str,
    product_id: str,
    date_from: date,
    date_to: date,
    adults: int,
    children: int,
    rooms: int,
    currency: str,
    partner: Optional[str] = None,
    client_ip: Optional[str] = None,
) -> Tuple[PublicQuote, Dict[str, Any]]:
    """Create a public quote from catalog + rate_plans.

    Returns both the PublicQuote dataclass and a minimal product snapshot
    suitable for embedding in API responses.
    """

    if date_to <= date_from:
        raise AppError(422, "invalid_date_range", "Check-out must be after check-in")
    if adults < 1:
        raise AppError(422, "invalid_occupancy", "At least 1 adult is required")
    if rooms < 1:
        raise AppError(422, "invalid_rooms", "At least 1 room is required")

    # Load product and ensure it belongs to this org and is active
    try:
        pid = ObjectId(product_id)
    except Exception:
        raise AppError(404, "product_not_found", "Product not found")

    product = await db.products.find_one(
        {"_id": pid, "organization_id": organization_id, "status": "active"}
    )
    if not product:
        raise AppError(404, "product_not_found", "Product not found")

    # Ensure there is at least one published version
    pv = await db.product_versions.find_one(
        {"organization_id": organization_id, "product_id": pid, "status": "published"}
    )
    if not pv:
        raise AppError(422, "no_published_version", "Product is not published")

    # Fetch active rate plans to derive a rough from-price
    rp_cursor = db.rate_plans.find(
        {
            "organization_id": organization_id,
            "product_id": pid,
            "status": "active",
        },
        {"currency": 1, "base_net_price": 1},
    )
    rate_plans = await rp_cursor.to_list(length=1000)
    if not rate_plans:
        raise AppError(422, "no_pricing_available", "No active rate plans for product")

    nightly_best: Optional[Dict[str, Any]] = None
    for rp in rate_plans:
        base_net = float(rp.get("base_net_price") or 0.0)
        if base_net <= 0:
            continue
        if nightly_best is None or base_net < float(nightly_best.get("base_net_price") or 0.0):
            nightly_best = rp

    if nightly_best is None:
        raise AppError(422, "no_pricing_available", "No valid net price for product")

    nights = max((date_to - date_from).days, 1)
    rooms = max(rooms, 1)

    base_net = float(nightly_best.get("base_net_price") or 0.0)
    base_total = base_net * nights * rooms
    taxes = round(base_total * 0.1, 2)
    grand_total = base_total + taxes

    # Partner bazlı B2B indirimleri (varsa) uygula
    agency_id: Optional[str] = None
    if partner:
        agency_doc = await _resolve_partner_agency(db, organization_id, partner)
        if agency_doc is None:
            # Geçersiz partner parametresini yok say (güvenlik): indirim ve partner kanalı uygulanmaz
            partner = None
        else:
            agency_id = str(agency_doc.get("_id"))

    if agency_id:
        try:
            group = await resolve_discount_group(
                db,
                organization_id=organization_id,
                agency_id=agency_id,
                product_id=str(pid),
                product_type=product.get("type") or "hotel",
                check_in=date_from,
            )
            if group:
                discount_result = apply_discount(
                    base_net=base_total,
                    base_sell=grand_total,
                    markup_percent=10.0,
                    group=group,
                )
                breakdown = discount_result["breakdown"]
                base_total = breakdown["base"]
                grand_total = discount_result["final_sell"]
                taxes = breakdown["markup_amount"]
                discount_amount = breakdown["discount_amount"]
            else:
                discount_amount = 0.0
        except Exception:
            # İndirim hesaplanamazsa sessizce devam et (fiyatı bozma)
            discount_amount = 0.0
    else:
        discount_amount = 0.0

    amount_cents = int(round(grand_total * 100))
    base_cents = int(round(base_total * 100))
    taxes_cents = int(round(taxes * 100))
    discount_cents = int(round(discount_amount * 100)) if discount_amount else 0

    # Determine currency: rate_plan currency or product default
    rp_currency = (nightly_best.get("currency") or product.get("default_currency") or "EUR").upper()
    currency = (currency or rp_currency).upper()

    # Build minimal product snapshot for API
    name = product.get("name") or {}
    title = name.get("tr") or name.get("en") or "Ürün"
    product_type = product.get("type") or "hotel"

    content = (pv.get("content") or {})
    desc = content.get("description") or {}
    summary = desc.get("tr") or desc.get("en") or ""

    images = content.get("images") or []
    image_url = None
    if images:
        first = images[0]
        image_url = first.get("url") or first.get("src")

    product_snapshot = {
        "title": title,
        "type": product_type,
        "summary": summary,
        "image_url": image_url,
    }

    # Persist quote
    from uuid import uuid4

    quote_id = f"qt_{uuid4().hex[:16]}"
    now = now_utc()
    expires_at = now + timedelta(minutes=PUBLIC_QUOTE_TTL_MINUTES)

    doc = {
        "quote_id": quote_id,
        "organization_id": organization_id,
        "product_id": pid,
        "product_type": product_type,
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "nights": nights,
        "pax": {"adults": adults, "children": children, "rooms": rooms},
        "currency": currency,
        "amount_cents": amount_cents,
        "breakdown": {"base": base_cents, "taxes": taxes_cents, "discount": discount_cents},
        "line_items": [],
        "status": "pending",
        "expires_at": expires_at,
        "created_at": now,
        "created_ip": client_ip,
        "channel": "partner" if partner else "web",
        "partner": partner,
        "b2b_context": {
            "agency_id": agency_id,
        }
        if agency_id
        else None,
    }

    await db.public_quotes.insert_one(doc)

    quote = PublicQuote(
        quote_id=quote_id,
        organization_id=organization_id,
        product_id=str(pid),
        product_type=product_type,
        date_from=date_from,
        date_to=date_to,
        nights=nights,
        adults=adults,
        children=children,
        rooms=rooms,
        currency=currency,
        amount_cents=amount_cents,
    )

    return quote, product_snapshot


async def get_valid_quote(db, *, organization_id: str, quote_id: str) -> Dict[str, Any]:
    """Resolve a quote_id to a non-expired pending quote document.

    Distinguishes between not-found and expired quotes for clearer public API errors.
    """

    # Normalise timestamps to naive datetimes for robust comparison with MongoDB values
    now = now_utc().replace(tzinfo=None)
    doc = await db.public_quotes.find_one(
        {
            "quote_id": quote_id,
            "organization_id": organization_id,
        }
    )
    if not doc:
        raise AppError(
            404,
            PublicCheckoutErrorCode.QUOTE_NOT_FOUND.value,
            "Quote not found",
        )

    expires_at = doc.get("expires_at")
    status = doc.get("status")
    if not expires_at:
        # Missing expiry is treated as expired/invalid for safety
        raise AppError(
            404,
            PublicCheckoutErrorCode.QUOTE_EXPIRED.value,
            "Quote expired or inactive",
        )

    # Make sure expires_at is comparable with naive now
    if getattr(expires_at, "tzinfo", None) is not None:
        expires_at = expires_at.replace(tzinfo=None)

    if expires_at <= now or status != "pending":
        raise AppError(
            404,
            PublicCheckoutErrorCode.QUOTE_EXPIRED.value,
            "Quote expired or inactive",
        )

    return doc


async def get_or_create_public_checkout_record(
    db,
    *,
    organization_id: str,
    quote_id: str,
    idempotency_key: str,
    booking_id: Optional[str] = None,
    payment_intent_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Idempotency helper for public checkout.

    If a record already exists for (org, quote_id, idempotency_key), it is
    returned unchanged. Otherwise, when booking_id and payment_intent_id are
    provided, a new record is inserted.
    """

    existing = await db.public_checkouts.find_one(
        {
            "organization_id": organization_id,
            "quote_id": quote_id,
            "idempotency_key": idempotency_key,
        }
    )
    if existing:
        return existing

    if not booking_id or not payment_intent_id:
        # Caller wants to check for existing record only.
        raise AppError(404, "checkout_not_found", "Checkout record not found")

    now = now_utc()
    doc = {
        "organization_id": organization_id,
        "quote_id": quote_id,
        "idempotency_key": idempotency_key,
        "booking_id": booking_id,
        "payment_intent_id": payment_intent_id,
        "status": "created",
        "created_at": now,
    }
    await db.public_checkouts.insert_one(doc)
    return doc
