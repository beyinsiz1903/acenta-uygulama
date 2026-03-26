"""PMS Accounting & Invoicing API.

Folio (cari hesap) management for reservations and invoice generation.

Endpoints:
  GET  /api/agency/pms/accounting/folios              — List folios
  GET  /api/agency/pms/accounting/folios/{res_id}      — Get folio for reservation
  POST /api/agency/pms/accounting/folios/{res_id}/charge  — Post a charge
  POST /api/agency/pms/accounting/folios/{res_id}/payment — Post a payment
  DELETE /api/agency/pms/accounting/transactions/{tx_id}  — Delete a transaction
  GET  /api/agency/pms/accounting/invoices             — List invoices
  POST /api/agency/pms/accounting/invoices             — Create invoice from folio
  GET  /api/agency/pms/accounting/invoices/{inv_id}    — Get invoice detail
  PUT  /api/agency/pms/accounting/invoices/{inv_id}    — Update invoice
  GET  /api/agency/pms/accounting/summary              — Financial summary
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone, date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.auth import get_current_user, require_roles
from app.db import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agency/pms/accounting", tags=["agency_pms_accounting"])

AgencyDep = Depends(require_roles(["agency_admin", "agency_agent", "admin", "super_admin"]))


def _now():
    return datetime.now(timezone.utc)


def _today_str():
    return date.today().isoformat()


def _serialize(doc: dict) -> dict:
    result = {k: v for k, v in doc.items() if k != "_id"}
    result["id"] = str(doc.get("_id", ""))
    for key in ("created_at", "updated_at", "issued_at", "paid_at", "cancelled_at"):
        if key in result and isinstance(result[key], datetime):
            result[key] = result[key].isoformat()
    return result


CHARGE_TYPES = ["room", "extra_bed", "food", "minibar", "laundry", "transfer", "tour", "tax", "other"]
PAYMENT_METHODS = ["cash", "credit_card", "bank_transfer", "online", "other"]
INVOICE_STATUSES = ["draft", "issued", "paid", "cancelled"]


# ---------------------------------------------------------------------------
# Folio (Cari Hesap) Endpoints
# ---------------------------------------------------------------------------

@router.get("/folios", dependencies=[AgencyDep])
async def list_folios(
    hotel_id: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    user=Depends(get_current_user),
):
    """List all folios with balance information."""
    db = await get_db()
    agency_id = user.get("agency_id")
    org_id = user["organization_id"]

    if not agency_id:
        return {"items": [], "total": 0}

    # Get reservations that have transactions
    res_query = {
        "organization_id": org_id,
        "agency_id": agency_id,
    }
    if hotel_id:
        res_query["hotel_id"] = hotel_id
    if search:
        res_query["$or"] = [
            {"guest_name": {"$regex": search, "$options": "i"}},
            {"pnr": {"$regex": search, "$options": "i"}},
        ]

    reservations = await db.reservations.find(res_query).sort("check_in", -1).to_list(limit)

    items = []
    for res in reservations:
        res_id = str(res.get("_id", ""))
        # Calculate balance from transactions
        tx_query = {
            "organization_id": org_id,
            "reservation_id": res_id,
        }
        txs = await db.pms_transactions.find(tx_query).to_list(500)
        total_charges = sum(t.get("amount", 0) for t in txs if t.get("type") == "charge")
        total_payments = sum(t.get("amount", 0) for t in txs if t.get("type") == "payment")
        balance = total_charges - total_payments

        item = {
            "reservation_id": res_id,
            "guest_name": res.get("guest_name", ""),
            "hotel_name": res.get("hotel_name", ""),
            "hotel_id": res.get("hotel_id", ""),
            "check_in": res.get("check_in", ""),
            "check_out": res.get("check_out", ""),
            "room_number": res.get("room_number", ""),
            "pnr": res.get("pnr", ""),
            "pms_status": res.get("pms_status", ""),
            "total_charges": round(total_charges, 2),
            "total_payments": round(total_payments, 2),
            "balance": round(balance, 2),
            "currency": res.get("currency", "TRY"),
            "transaction_count": len(txs),
        }
        items.append(item)

    # Filter by status if requested
    if status == "has_balance":
        items = [i for i in items if i["balance"] > 0]
    elif status == "settled":
        items = [i for i in items if i["balance"] <= 0 and i["transaction_count"] > 0]
    elif status == "no_transactions":
        items = [i for i in items if i["transaction_count"] == 0]

    return {"items": items, "total": len(items)}


@router.get("/folios/{reservation_id}", dependencies=[AgencyDep])
async def get_folio(
    reservation_id: str,
    user=Depends(get_current_user),
):
    """Get folio detail for a reservation with all transactions."""
    db = await get_db()
    agency_id = user.get("agency_id")
    org_id = user["organization_id"]

    # Get reservation
    res = await db.reservations.find_one({
        "_id": reservation_id,
        "organization_id": org_id,
        "agency_id": agency_id,
    })
    if not res:
        raise HTTPException(status_code=404, detail="Rezervasyon bulunamadi")

    # Get transactions
    txs = await db.pms_transactions.find({
        "organization_id": org_id,
        "reservation_id": reservation_id,
    }).sort("created_at", 1).to_list(500)

    total_charges = sum(t.get("amount", 0) for t in txs if t.get("type") == "charge")
    total_payments = sum(t.get("amount", 0) for t in txs if t.get("type") == "payment")

    # Get related invoices
    invoices = await db.pms_invoices.find({
        "organization_id": org_id,
        "reservation_id": reservation_id,
    }).sort("created_at", -1).to_list(50)

    return {
        "reservation": {
            "id": str(res.get("_id", "")),
            "guest_name": res.get("guest_name", ""),
            "hotel_name": res.get("hotel_name", ""),
            "hotel_id": res.get("hotel_id", ""),
            "check_in": res.get("check_in", ""),
            "check_out": res.get("check_out", ""),
            "room_number": res.get("room_number", ""),
            "pnr": res.get("pnr", ""),
            "pms_status": res.get("pms_status", ""),
            "total_price": res.get("total_price", 0),
            "currency": res.get("currency", "TRY"),
        },
        "transactions": [_serialize(t) for t in txs],
        "total_charges": round(total_charges, 2),
        "total_payments": round(total_payments, 2),
        "balance": round(total_charges - total_payments, 2),
        "invoices": [_serialize(inv) for inv in invoices],
    }


# ---------------------------------------------------------------------------
# Transaction Endpoints (Charge / Payment)
# ---------------------------------------------------------------------------

class ChargeIn(BaseModel):
    amount: float
    description: str
    charge_type: str = "room"
    currency: str = "TRY"
    notes: Optional[str] = None


@router.post("/folios/{reservation_id}/charge", dependencies=[AgencyDep])
async def post_charge(
    reservation_id: str,
    payload: ChargeIn,
    user=Depends(get_current_user),
):
    """Post a charge to a reservation's folio."""
    db = await get_db()
    agency_id = user.get("agency_id")
    org_id = user["organization_id"]

    res = await db.reservations.find_one({
        "_id": reservation_id,
        "organization_id": org_id,
        "agency_id": agency_id,
    })
    if not res:
        raise HTTPException(status_code=404, detail="Rezervasyon bulunamadi")

    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="Tutar sifirdan buyuk olmali")

    now = _now()
    tx = {
        "_id": str(uuid.uuid4()),
        "organization_id": org_id,
        "agency_id": agency_id,
        "reservation_id": reservation_id,
        "hotel_id": res.get("hotel_id", ""),
        "type": "charge",
        "charge_type": payload.charge_type,
        "amount": round(payload.amount, 2),
        "currency": payload.currency,
        "description": payload.description,
        "notes": payload.notes,
        "created_by": user.get("email"),
        "created_at": now,
    }

    await db.pms_transactions.insert_one(tx)
    return _serialize(tx)


class PaymentIn(BaseModel):
    amount: float
    description: str = "Odeme"
    payment_method: str = "cash"
    currency: str = "TRY"
    reference: Optional[str] = None
    notes: Optional[str] = None


@router.post("/folios/{reservation_id}/payment", dependencies=[AgencyDep])
async def post_payment(
    reservation_id: str,
    payload: PaymentIn,
    user=Depends(get_current_user),
):
    """Post a payment to a reservation's folio."""
    db = await get_db()
    agency_id = user.get("agency_id")
    org_id = user["organization_id"]

    res = await db.reservations.find_one({
        "_id": reservation_id,
        "organization_id": org_id,
        "agency_id": agency_id,
    })
    if not res:
        raise HTTPException(status_code=404, detail="Rezervasyon bulunamadi")

    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="Tutar sifirdan buyuk olmali")

    now = _now()
    tx = {
        "_id": str(uuid.uuid4()),
        "organization_id": org_id,
        "agency_id": agency_id,
        "reservation_id": reservation_id,
        "hotel_id": res.get("hotel_id", ""),
        "type": "payment",
        "payment_method": payload.payment_method,
        "amount": round(payload.amount, 2),
        "currency": payload.currency,
        "description": payload.description,
        "reference": payload.reference,
        "notes": payload.notes,
        "created_by": user.get("email"),
        "created_at": now,
    }

    await db.pms_transactions.insert_one(tx)
    return _serialize(tx)


@router.delete("/transactions/{tx_id}", dependencies=[AgencyDep])
async def delete_transaction(
    tx_id: str,
    user=Depends(get_current_user),
):
    """Delete a transaction (charge or payment)."""
    db = await get_db()
    org_id = user["organization_id"]

    doc = await db.pms_transactions.find_one({
        "_id": tx_id,
        "organization_id": org_id,
    })
    if not doc:
        raise HTTPException(status_code=404, detail="Islem bulunamadi")

    await db.pms_transactions.delete_one({"_id": tx_id})
    return {"status": "deleted", "id": tx_id}


# ---------------------------------------------------------------------------
# Invoice Endpoints
# ---------------------------------------------------------------------------

class InvoiceCreateIn(BaseModel):
    reservation_id: str
    invoice_to: Optional[str] = None
    tax_id: Optional[str] = None
    tax_office: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    include_transactions: Optional[list[str]] = None


@router.post("/invoices", dependencies=[AgencyDep])
async def create_invoice(
    payload: InvoiceCreateIn,
    user=Depends(get_current_user),
):
    """Create an invoice from a reservation's folio."""
    db = await get_db()
    agency_id = user.get("agency_id")
    org_id = user["organization_id"]

    res = await db.reservations.find_one({
        "_id": payload.reservation_id,
        "organization_id": org_id,
        "agency_id": agency_id,
    })
    if not res:
        raise HTTPException(status_code=404, detail="Rezervasyon bulunamadi")

    # Get charges for the reservation
    charge_query = {
        "organization_id": org_id,
        "reservation_id": payload.reservation_id,
        "type": "charge",
    }
    if payload.include_transactions:
        charge_query["_id"] = {"$in": payload.include_transactions}

    charges = await db.pms_transactions.find(charge_query).to_list(500)
    if not charges:
        raise HTTPException(status_code=400, detail="Faturlanacak islem bulunamadi")

    subtotal = sum(c.get("amount", 0) for c in charges)
    tax_rate = 0.20  # %20 KDV
    tax_amount = round(subtotal * tax_rate, 2)
    total = round(subtotal + tax_amount, 2)

    # Generate invoice number
    count = await db.pms_invoices.count_documents({"organization_id": org_id})
    invoice_no = f"INV-{date.today().strftime('%Y%m')}-{str(count + 1).zfill(4)}"

    now = _now()
    invoice = {
        "_id": str(uuid.uuid4()),
        "organization_id": org_id,
        "agency_id": agency_id,
        "reservation_id": payload.reservation_id,
        "hotel_id": res.get("hotel_id", ""),
        "invoice_no": invoice_no,
        "status": "draft",
        "invoice_to": payload.invoice_to or res.get("guest_name", ""),
        "tax_id": payload.tax_id or "",
        "tax_office": payload.tax_office or "",
        "address": payload.address or "",
        "guest_name": res.get("guest_name", ""),
        "hotel_name": res.get("hotel_name", ""),
        "check_in": res.get("check_in", ""),
        "check_out": res.get("check_out", ""),
        "room_number": res.get("room_number", ""),
        "items": [
            {
                "description": c.get("description", ""),
                "charge_type": c.get("charge_type", "other"),
                "amount": c.get("amount", 0),
                "transaction_id": str(c.get("_id", "")),
            }
            for c in charges
        ],
        "subtotal": round(subtotal, 2),
        "tax_rate": tax_rate,
        "tax_amount": tax_amount,
        "total": total,
        "currency": res.get("currency", "TRY"),
        "notes": payload.notes or "",
        "created_by": user.get("email"),
        "created_at": now,
        "updated_at": now,
    }

    await db.pms_invoices.insert_one(invoice)
    return _serialize(invoice)


@router.get("/invoices", dependencies=[AgencyDep])
async def list_invoices(
    hotel_id: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    user=Depends(get_current_user),
):
    """List invoices."""
    db = await get_db()
    agency_id = user.get("agency_id")
    org_id = user["organization_id"]

    if not agency_id:
        return {"items": [], "total": 0}

    query = {
        "organization_id": org_id,
        "agency_id": agency_id,
    }
    if hotel_id:
        query["hotel_id"] = hotel_id
    if status:
        query["status"] = status
    if search:
        query["$or"] = [
            {"guest_name": {"$regex": search, "$options": "i"}},
            {"invoice_no": {"$regex": search, "$options": "i"}},
            {"invoice_to": {"$regex": search, "$options": "i"}},
        ]

    docs = await db.pms_invoices.find(query).sort("created_at", -1).to_list(limit)
    return {"items": [_serialize(d) for d in docs], "total": len(docs)}


@router.get("/invoices/{invoice_id}", dependencies=[AgencyDep])
async def get_invoice(
    invoice_id: str,
    user=Depends(get_current_user),
):
    """Get invoice detail."""
    db = await get_db()
    org_id = user["organization_id"]

    doc = await db.pms_invoices.find_one({
        "_id": invoice_id,
        "organization_id": org_id,
    })
    if not doc:
        raise HTTPException(status_code=404, detail="Fatura bulunamadi")

    return _serialize(doc)


class InvoiceUpdateIn(BaseModel):
    status: Optional[str] = None
    invoice_to: Optional[str] = None
    tax_id: Optional[str] = None
    tax_office: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None


@router.put("/invoices/{invoice_id}", dependencies=[AgencyDep])
async def update_invoice(
    invoice_id: str,
    payload: InvoiceUpdateIn,
    user=Depends(get_current_user),
):
    """Update an invoice (status, billing details)."""
    db = await get_db()
    org_id = user["organization_id"]

    doc = await db.pms_invoices.find_one({
        "_id": invoice_id,
        "organization_id": org_id,
    })
    if not doc:
        raise HTTPException(status_code=404, detail="Fatura bulunamadi")

    update_fields = {"updated_at": _now()}

    if payload.status is not None:
        if payload.status not in INVOICE_STATUSES:
            raise HTTPException(status_code=400, detail=f"Gecersiz durum: {payload.status}")
        update_fields["status"] = payload.status
        if payload.status == "issued" and not doc.get("issued_at"):
            update_fields["issued_at"] = _now()
        elif payload.status == "paid" and not doc.get("paid_at"):
            update_fields["paid_at"] = _now()
        elif payload.status == "cancelled" and not doc.get("cancelled_at"):
            update_fields["cancelled_at"] = _now()

    if payload.invoice_to is not None:
        update_fields["invoice_to"] = payload.invoice_to
    if payload.tax_id is not None:
        update_fields["tax_id"] = payload.tax_id
    if payload.tax_office is not None:
        update_fields["tax_office"] = payload.tax_office
    if payload.address is not None:
        update_fields["address"] = payload.address
    if payload.notes is not None:
        update_fields["notes"] = payload.notes

    await db.pms_invoices.update_one({"_id": invoice_id}, {"$set": update_fields})
    updated = await db.pms_invoices.find_one({"_id": invoice_id})
    return _serialize(updated)


# ---------------------------------------------------------------------------
# Financial Summary
# ---------------------------------------------------------------------------

@router.get("/summary", dependencies=[AgencyDep])
async def accounting_summary(
    hotel_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    user=Depends(get_current_user),
):
    """Financial summary for the agency."""
    db = await get_db()
    agency_id = user.get("agency_id")
    org_id = user["organization_id"]

    if not agency_id:
        return {}

    tx_query = {
        "organization_id": org_id,
        "agency_id": agency_id,
    }
    if hotel_id:
        tx_query["hotel_id"] = hotel_id

    txs = await db.pms_transactions.find(tx_query).to_list(5000)

    total_charges = sum(t.get("amount", 0) for t in txs if t.get("type") == "charge")
    total_payments = sum(t.get("amount", 0) for t in txs if t.get("type") == "payment")

    # Charges by type
    charges_by_type = {}
    for t in txs:
        if t.get("type") == "charge":
            ct = t.get("charge_type", "other")
            charges_by_type[ct] = charges_by_type.get(ct, 0) + t.get("amount", 0)

    # Payments by method
    payments_by_method = {}
    for t in txs:
        if t.get("type") == "payment":
            pm = t.get("payment_method", "other")
            payments_by_method[pm] = payments_by_method.get(pm, 0) + t.get("amount", 0)

    # Invoice stats
    inv_query = {"organization_id": org_id, "agency_id": agency_id}
    if hotel_id:
        inv_query["hotel_id"] = hotel_id
    invoices = await db.pms_invoices.find(inv_query).to_list(1000)

    invoice_stats = {
        "total": len(invoices),
        "draft": len([i for i in invoices if i.get("status") == "draft"]),
        "issued": len([i for i in invoices if i.get("status") == "issued"]),
        "paid": len([i for i in invoices if i.get("status") == "paid"]),
        "cancelled": len([i for i in invoices if i.get("status") == "cancelled"]),
        "total_amount": round(sum(i.get("total", 0) for i in invoices if i.get("status") != "cancelled"), 2),
    }

    return {
        "total_charges": round(total_charges, 2),
        "total_payments": round(total_payments, 2),
        "balance": round(total_charges - total_payments, 2),
        "charges_by_type": {k: round(v, 2) for k, v in charges_by_type.items()},
        "payments_by_method": {k: round(v, 2) for k, v in payments_by_method.items()},
        "invoice_stats": invoice_stats,
        "transaction_count": len(txs),
    }
