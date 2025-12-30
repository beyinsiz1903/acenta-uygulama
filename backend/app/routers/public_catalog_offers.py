from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Response

from app.db import get_db
from app.utils import now_utc
from app.utils import VoucherTokenExpired, VoucherTokenInvalid, VoucherTokenMissing, verify_voucher_token, sign_voucher
from app.services.catalog_offer_pdf import render_catalog_offer_pdf
from app.utils import to_object_id

router = APIRouter(prefix="/api/public/catalog-offers", tags=["public:catalog-offers"])


@router.get("/{booking_id}.pdf")
async def get_public_catalog_offer_pdf(booking_id: str, t: Optional[str] = None):
    """Public offer PDF for catalog booking.

    - Protected with short-lived HMAC token (?t=...)
    - Uses agency_catalog_booking_requests + product/variant snapshot
    """

    if not t:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "OFFER_TOKEN_MISSING",
                "message": "Geçerli bir teklif erişim token'ı gerekli.",
            },
        )

    now = now_utc()
    try:
        # For catalog offers we reuse voucher_signing by treating booking_id as voucher_id
        verify_voucher_token(booking_id, t, now)
    except VoucherTokenMissing:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "OFFER_TOKEN_MISSING",
                "message": "Geçerli bir teklif erişim token'ı gerekli.",
            },
        )
    except VoucherTokenExpired:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "OFFER_TOKEN_INVALID_OR_EXPIRED",
                "message": "Teklif linkinin süresi dolmuş.",
            },
        )
    except VoucherTokenInvalid:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "OFFER_TOKEN_INVALID_OR_EXPIRED",
                "message": "Teklif linki geçersiz.",
            },
        )

    db = await get_db()

    try:
        booking_oid = to_object_id(booking_id)
    except Exception:
        raise HTTPException(
            status_code=404,
            detail={"code": "CATALOG_BOOKING_NOT_FOUND", "message": "Rezervasyon bulunamadı."},
        )

    booking = await db.agency_catalog_booking_requests.find_one({"_id": booking_oid})
    if not booking:
        raise HTTPException(
            status_code=404,
            detail={"code": "CATALOG_BOOKING_NOT_FOUND", "message": "Rezervasyon bulunamadı."},
        )

    product = None
    if booking.get("product_id"):
        product = await db.agency_catalog_products.find_one({"_id": booking["product_id"]})
    variant = None
    if booking.get("variant_id"):
        variant = await db.agency_catalog_variants.find_one({"_id": booking["variant_id"]})

    if product is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "CATALOG_PRODUCT_NOT_FOUND", "message": "Ürün bulunamadı."},
        )

    try:
        pdf_bytes = render_catalog_offer_pdf(booking=booking, product=product, variant=variant)
    except Exception as e:  # pragma: no cover - defensive
        raise HTTPException(
            status_code=500,
            detail={"code": "OFFER_PDF_RENDER_FAILED", "message": "Teklif PDF'i oluşturulamadı."},
        ) from e

    filename = f"catalog-offer-{booking_id}.pdf"
    headers = {
        "Content-Disposition": f'inline; filename="{filename}"',
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
        "Content-Length": str(len(pdf_bytes)),
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)