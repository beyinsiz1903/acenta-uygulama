from __future__ import annotations

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Response

from app.auth import get_current_user
from app.db import get_db
from app.schemas import ReservationCreateIn
from app.services.reservations import create_reservation, set_reservation_status
from app.utils import serialize_doc, to_object_id

router = APIRouter(prefix="/api/reservations", tags=["reservations"])


def _oid_or_400(id_str: str) -> ObjectId:
    try:
        return to_object_id(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Geçersiz id")


@router.post("/reserve", dependencies=[Depends(get_current_user)])
async def reserve(payload: ReservationCreateIn, user=Depends(get_current_user)):
    doc = await create_reservation(org_id=user["organization_id"], user_email=user.get("email"), payload=payload.model_dump())
    return serialize_doc(doc)


@router.get("", dependencies=[Depends(get_current_user)])
async def list_reservations(status: str | None = None, q: str | None = None, user=Depends(get_current_user)):
    db = await get_db()
    query: dict[str, object] = {"organization_id": user["organization_id"]}
    if status:
        query["status"] = status
    if q:
        query["pnr"] = {"$regex": q, "$options": "i"}

    docs = await db.reservations.find(query).sort("created_at", -1).to_list(300)
    return [serialize_doc(d) for d in docs]


@router.get("/{reservation_id}", dependencies=[Depends(get_current_user)])
async def get_reservation(reservation_id: str, user=Depends(get_current_user)):
    db = await get_db()
    res_oid = _oid_or_400(reservation_id)
    doc = await db.reservations.find_one({"organization_id": user["organization_id"], "_id": res_oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Rezervasyon bulunamadı")

    payments = await db.payments.find({"organization_id": user["organization_id"], "reservation_id": res_oid}).sort("created_at", -1).to_list(200)
    out = serialize_doc(doc)
    out["payments"] = [serialize_doc(p) for p in payments]
    out["due_amount"] = round(float(out.get("total_price") or 0) - float(out.get("paid_amount") or 0), 2)
    return out


@router.post("/{reservation_id}/confirm", dependencies=[Depends(get_current_user)])
async def confirm(reservation_id: str, user=Depends(get_current_user)):
    doc = await set_reservation_status(user["organization_id"], reservation_id, "confirmed", user.get("email"))
    return serialize_doc(doc)


@router.post("/{reservation_id}/cancel", dependencies=[Depends(get_current_user)])
async def cancel(reservation_id: str, user=Depends(get_current_user)):
    doc = await set_reservation_status(user["organization_id"], reservation_id, "cancelled", user.get("email"))
    return serialize_doc(doc)


@router.get("/{reservation_id}/voucher", dependencies=[Depends(get_current_user)])
async def voucher(reservation_id: str, user=Depends(get_current_user)):
    db = await get_db()
    res_oid = _oid_or_400(reservation_id)
    res = await db.reservations.find_one({"organization_id": user["organization_id"], "_id": res_oid})
    if not res:
        raise HTTPException(status_code=404, detail="Rezervasyon bulunamadı")

    product = await db.products.find_one({"organization_id": user["organization_id"], "_id": res["product_id"]})
    customer = await db.customers.find_one({"organization_id": user["organization_id"], "_id": res["customer_id"]})

    html = f"""<!doctype html>
<html lang=\"tr\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Voucher {res.get('voucher_no')}</title>
  <style>
    body {{ font-family: Arial, sans-serif; background:#f7fafc; padding:24px; }}
    .voucher {{ background:#ffffff; border:1px solid #e5e7eb; border-radius:14px; padding:24px; max-width:900px; margin:0 auto; }}
    .row {{ display:flex; gap:24px; flex-wrap:wrap; }}
    .col {{ flex:1; min-width:280px; }}
    .muted {{ color:#6b7280; font-size:12px; }}
    h1 {{ margin:0 0 8px 0; font-size:22px; }}
    h2 {{ margin:18px 0 8px 0; font-size:14px; color:#111827; }}
    .badge {{ display:inline-block; background:#e0f2fe; color:#075985; padding:4px 10px; border-radius:999px; font-size:12px; }}
    table {{ width:100%; border-collapse:collapse; }}
    td, th {{ border-top:1px solid #e5e7eb; padding:10px 0; text-align:left; font-size:13px; }}
    @media print {{ .no-print {{ display:none !important; }} body {{ background:#fff; padding:0; }} .voucher {{ border:none; }} }}
  </style>
</head>
<body>
  <div class=\"voucher\">
    <div class=\"row\">
      <div class=\"col\">
        <h1>Voucher</h1>
        <div class=\"muted\">Voucher No</div>
        <div class=\"badge\">{res.get('voucher_no')}</div>
      </div>
      <div class=\"col\">
        <div class=\"muted\">PNR</div>
        <div style=\"font-weight:700\">{res.get('pnr')}</div>
        <div class=\"muted\" style=\"margin-top:8px\">Durum</div>
        <div>{res.get('status')}</div>
      </div>
    </div>

    <h2>Müşteri</h2>
    <div>{(customer or {}).get('name','-')} — {(customer or {}).get('phone','')} {(customer or {}).get('email','')}</div>

    <h2>Ürün</h2>
    <div style=\"font-weight:600\">{(product or {}).get('title','-')}</div>
    <div class=\"muted\">{(product or {}).get('type','')}</div>

    <h2>Tarih & Pax</h2>
    <div>{res.get('start_date')} {(' - ' + res.get('end_date')) if res.get('end_date') else ''} — Pax: {res.get('pax')}</div>

    <h2>Ücret Detayı</h2>
    <table>
      <thead>
        <tr><th>Tarih</th><th>Birim</th><th>Pax</th><th>Toplam</th></tr>
      </thead>
      <tbody>
        {''.join([f"<tr><td>{it.get('date')}</td><td>{it.get('unit_price')} {res.get('currency')}</td><td>{it.get('pax')}</td><td>{it.get('total')} {res.get('currency')}</td></tr>" for it in (res.get('price_items') or [])])}
      </tbody>
      <tfoot>
        <tr><td colspan=\"3\" style=\"font-weight:700\">Genel Toplam</td><td style=\"font-weight:700\">{res.get('total_price')} {res.get('currency')}</td></tr>
      </tfoot>
    </table>

    <div class=\"muted\" style=\"margin-top:18px\">Not: Bu belge bilgilendirme amaçlıdır.</div>

    <div class=\"no-print\" style=\"margin-top:18px\">
      <button onclick=\"window.print()\" style=\"background:#0e7490;color:#fff;border:none;border-radius:10px;padding:10px 14px;cursor:pointer\">Yazdır</button>
    </div>
  </div>
</body>
</html>"""

    return Response(content=html, media_type="text/html")
