from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.db import get_db
from app.errors import AppError

logger = logging.getLogger(__name__)


class WebPOSService:
    """WebPOS + Internal Ledger – append-only ledger design."""

    # ─── Payment CRUD ─────────────────────────────────────────────
    async def record_payment(
        self,
        *,
        tenant_id: str,
        org_id: str,
        amount: float,
        currency: str = "TRY",
        method: str = "cash",
        customer_id: Optional[str] = None,
        reservation_id: Optional[str] = None,
        description: Optional[str] = None,
        actor_email: str = "",
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        db = await get_db()
        now = datetime.now(timezone.utc)
        payment_id = f"pay_{uuid.uuid4().hex}"

        if amount <= 0:
            raise AppError(400, "invalid_amount", "Tutar sıfırdan büyük olmalıdır.", {})

        valid_methods = ["cash", "bank_transfer", "manual_card", "other"]
        if method not in valid_methods:
            raise AppError(400, "invalid_method", f"Geçersiz ödeme yöntemi: {method}", {"valid": valid_methods})

        payment_doc = {
            "_id": payment_id,
            "tenant_id": tenant_id,
            "organization_id": org_id,
            "reservation_id": reservation_id,
            "customer_id": customer_id,
            "amount": amount,
            "currency": currency,
            "method": method,
            "description": description or "",
            "status": "recorded",
            "created_at": now,
            "created_by": actor_email,
        }
        await db.webpos_payments.insert_one(payment_doc)

        # Create ledger entry (debit = money received)
        await self._append_ledger(
            db=db,
            tenant_id=tenant_id,
            org_id=org_id,
            entry_type="debit",
            category="sale",
            reference_id=payment_id,
            amount=amount,
            currency=currency,
            description=f"Ödeme: {description or method}",
        )

        payment_doc["id"] = payment_doc.pop("_id")
        return payment_doc

    async def refund_payment(
        self,
        *,
        tenant_id: str,
        org_id: str,
        payment_id: str,
        amount: Optional[float] = None,
        reason: str = "",
        actor_email: str = "",
    ) -> Dict[str, Any]:
        db = await get_db()
        now = datetime.now(timezone.utc)

        payment = await db.webpos_payments.find_one({"_id": payment_id, "tenant_id": tenant_id})
        if not payment:
            raise AppError(404, "payment_not_found", "Ödeme bulunamadı.", {})
        if payment.get("status") == "refunded":
            raise AppError(400, "already_refunded", "Bu ödeme zaten iade edildi.", {})

        refund_amount = amount if amount and amount > 0 else payment["amount"]
        if refund_amount > payment["amount"]:
            raise AppError(400, "refund_exceeds", "İade tutarı ödeme tutarını aşamaz.", {})

        refund_id = f"ref_{uuid.uuid4().hex}"
        refund_doc = {
            "_id": refund_id,
            "tenant_id": tenant_id,
            "organization_id": org_id,
            "original_payment_id": payment_id,
            "amount": refund_amount,
            "currency": payment.get("currency", "TRY"),
            "reason": reason,
            "status": "refunded",
            "created_at": now,
            "created_by": actor_email,
        }
        await db.webpos_payments.insert_one(refund_doc)

        # Mark original as refunded if full refund
        new_status = "refunded" if refund_amount >= payment["amount"] else "partial_refund"
        await db.webpos_payments.update_one(
            {"_id": payment_id},
            {"$set": {"status": new_status}},
        )

        # Append credit entry to ledger (reverse)
        await self._append_ledger(
            db=db,
            tenant_id=tenant_id,
            org_id=org_id,
            entry_type="credit",
            category="refund",
            reference_id=refund_id,
            amount=refund_amount,
            currency=payment.get("currency", "TRY"),
            description=f"İade: {reason or payment_id}",
        )

        refund_doc["id"] = refund_doc.pop("_id")
        return refund_doc

    async def list_payments(
        self,
        tenant_id: str,
        org_id: str,
        *,
        skip: int = 0,
        limit: int = 50,
        status_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        db = await get_db()
        query: Dict[str, Any] = {"tenant_id": tenant_id, "organization_id": org_id}
        if status_filter:
            query["status"] = status_filter

        total = await db.webpos_payments.count_documents(query)
        cursor = db.webpos_payments.find(query).sort("created_at", -1).skip(skip).limit(limit)
        items = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id", ""))
            items.append(doc)
        return {"items": items, "total": total}

    # ─── Ledger ───────────────────────────────────────────────────
    async def _append_ledger(
        self,
        *,
        db,
        tenant_id: str,
        org_id: str,
        entry_type: str,
        category: str,
        reference_id: str,
        amount: float,
        currency: str = "TRY",
        description: str = "",
    ) -> Dict[str, Any]:
        """Append-only ledger entry. NEVER update existing entries."""
        now = datetime.now(timezone.utc)
        entry_id = f"led_{uuid.uuid4().hex}"

        # Calculate balance_after from last entry
        last_entry = await db.webpos_ledger.find_one(
            {"tenant_id": tenant_id},
            sort=[("timestamp", -1)],
        )
        prev_balance = last_entry["balance_after"] if last_entry else 0.0

        if entry_type == "debit":
            balance_after = prev_balance + amount
        else:  # credit
            balance_after = prev_balance - amount

        entry_doc = {
            "_id": entry_id,
            "tenant_id": tenant_id,
            "organization_id": org_id,
            "type": entry_type,
            "category": category,
            "reference_id": reference_id,
            "amount": amount,
            "currency": currency,
            "balance_after": balance_after,
            "description": description,
            "timestamp": now,
        }
        await db.webpos_ledger.insert_one(entry_doc)
        return entry_doc

    async def get_ledger(
        self,
        tenant_id: str,
        org_id: str,
        *,
        skip: int = 0,
        limit: int = 50,
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        db = await get_db()
        query: Dict[str, Any] = {"tenant_id": tenant_id, "organization_id": org_id}
        if category:
            query["category"] = category

        total = await db.webpos_ledger.count_documents(query)
        cursor = db.webpos_ledger.find(query).sort("timestamp", -1).skip(skip).limit(limit)
        items = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id", ""))
            items.append(doc)
        return {"items": items, "total": total}

    async def get_balance(self, tenant_id: str) -> Dict[str, Any]:
        db = await get_db()
        last = await db.webpos_ledger.find_one(
            {"tenant_id": tenant_id},
            sort=[("timestamp", -1)],
        )
        balance = last["balance_after"] if last else 0.0
        return {"balance": balance, "currency": last.get("currency", "TRY") if last else "TRY"}

    async def daily_summary(self, tenant_id: str, org_id: str, date_str: str) -> Dict[str, Any]:
        """Daily summary for a given date (YYYY-MM-DD)."""
        db = await get_db()
        from datetime import datetime
        try:
            day_start = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise AppError(400, "invalid_date", "Geçersiz tarih formatı. YYYY-MM-DD kullanın.", {})

        day_end = day_start.replace(hour=23, minute=59, second=59)

        pipeline = [
            {"$match": {
                "tenant_id": tenant_id,
                "organization_id": org_id,
                "timestamp": {"$gte": day_start, "$lte": day_end},
            }},
            {"$group": {
                "_id": "$type",
                "total": {"$sum": "$amount"},
                "count": {"$sum": 1},
            }},
        ]
        rows = await db.webpos_ledger.aggregate(pipeline).to_list(10)
        result = {"date": date_str, "debit_total": 0, "credit_total": 0, "debit_count": 0, "credit_count": 0}
        for r in rows:
            if r["_id"] == "debit":
                result["debit_total"] = r["total"]
                result["debit_count"] = r["count"]
            elif r["_id"] == "credit":
                result["credit_total"] = r["total"]
                result["credit_count"] = r["count"]
        result["net"] = result["debit_total"] - result["credit_total"]
        return result


webpos_service = WebPOSService()
