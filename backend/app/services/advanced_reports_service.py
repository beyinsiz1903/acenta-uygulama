from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.db import get_db
from app.errors import AppError

logger = logging.getLogger(__name__)

# Default timezone for reports
DEFAULT_TZ = "Europe/Istanbul"


def _parse_date_range(from_date: Optional[str], to_date: Optional[str]) -> tuple:
    """Parse date range or default to last 30 days."""
    now = datetime.now(timezone.utc)
    if from_date:
        try:
            start = datetime.strptime(from_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise AppError(400, "invalid_date", "Geçersiz tarih formatı. YYYY-MM-DD kullanın.", {})
    else:
        start = now - timedelta(days=30)

    if to_date:
        try:
            end = datetime.strptime(to_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
        except ValueError:
            raise AppError(400, "invalid_date", "Geçersiz tarih formatı. YYYY-MM-DD kullanın.", {})
    else:
        end = now

    return start, end


class AdvancedReportsService:
    """Snapshot-safe reports – all date-range parameterized."""

    async def financial_summary(
        self,
        org_id: str,
        tenant_id: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        db = await get_db()
        start, end = _parse_date_range(from_date, to_date)

        # Revenue from ledger (debits)
        debit_pipeline = [
            {"$match": {
                "tenant_id": tenant_id,
                "organization_id": org_id,
                "type": "debit",
                "timestamp": {"$gte": start, "$lte": end},
            }},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}, "count": {"$sum": 1}}},
        ]
        debit_result = await db.webpos_ledger.aggregate(debit_pipeline).to_list(1)

        # Refunds from ledger (credits)
        credit_pipeline = [
            {"$match": {
                "tenant_id": tenant_id,
                "organization_id": org_id,
                "type": "credit",
                "timestamp": {"$gte": start, "$lte": end},
            }},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}, "count": {"$sum": 1}}},
        ]
        credit_result = await db.webpos_ledger.aggregate(credit_pipeline).to_list(1)

        # Outstanding from payments (recorded, not refunded)
        outstanding_pipeline = [
            {"$match": {
                "tenant_id": tenant_id,
                "organization_id": org_id,
                "status": "recorded",
                "created_at": {"$gte": start, "$lte": end},
            }},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}, "count": {"$sum": 1}}},
        ]
        outstanding_result = await db.webpos_payments.aggregate(outstanding_pipeline).to_list(1)

        total_revenue = debit_result[0]["total"] if debit_result else 0
        total_payments = debit_result[0]["count"] if debit_result else 0
        total_refunds = credit_result[0]["total"] if credit_result else 0
        refund_count = credit_result[0]["count"] if credit_result else 0
        outstanding = outstanding_result[0]["total"] if outstanding_result else 0

        return {
            "period": {"from": start.isoformat(), "to": end.isoformat()},
            "total_revenue": total_revenue,
            "total_payments": total_payments,
            "total_refunds": total_refunds,
            "refund_count": refund_count,
            "outstanding_balance": outstanding,
            "net_revenue": total_revenue - total_refunds,
        }

    async def product_performance(
        self,
        org_id: str,
        tenant_id: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        db = await get_db()
        start, end = _parse_date_range(from_date, to_date)

        # Reservations per product
        pipeline = [
            {"$match": {
                "organization_id": org_id,
                "created_at": {"$gte": start, "$lte": end},
            }},
            {"$group": {
                "_id": "$product_id",
                "reservation_count": {"$sum": 1},
                "total_revenue": {"$sum": {"$ifNull": ["$total_price", 0]}},
            }},
            {"$sort": {"total_revenue": -1}},
            {"$limit": 50},
        ]
        rows = await db.reservations.aggregate(pipeline).to_list(50)

        # Enrich with product titles
        product_ids = [r["_id"] for r in rows if r["_id"]]
        products = {}
        if product_ids:
            async for p in db.products.find({"_id": {"$in": product_ids}}):
                products[str(p["_id"])] = p.get("title", "")

        result = []
        for r in rows:
            pid = str(r["_id"]) if r["_id"] else "unknown"
            result.append({
                "product_id": pid,
                "product_title": products.get(pid, "Bilinmeyen Ürün"),
                "reservation_count": r["reservation_count"],
                "total_revenue": r["total_revenue"],
            })
        return result

    async def partner_performance(
        self,
        org_id: str,
        tenant_id: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        db = await get_db()
        start, end = _parse_date_range(from_date, to_date)

        # B2B match requests by partner
        pipeline = [
            {"$match": {
                "created_at": {"$gte": start, "$lte": end},
            }},
            {"$group": {
                "_id": "$seller_tenant_id",
                "match_count": {"$sum": 1},
                "revenue": {"$sum": {"$ifNull": ["$platform_fee_amount", 0]}},
            }},
            {"$sort": {"match_count": -1}},
            {"$limit": 50},
        ]
        rows = await db.b2b_match_requests.aggregate(pipeline).to_list(50)

        # Enrich with tenant names
        tenant_ids = [r["_id"] for r in rows if r["_id"]]
        tenants = {}
        if tenant_ids:
            async for t in db.tenants.find({"_id": {"$in": tenant_ids}}):
                tenants[str(t["_id"])] = t.get("name", "")

        return [
            {
                "partner_id": str(r["_id"]) if r["_id"] else "unknown",
                "partner_name": tenants.get(str(r["_id"]), "Bilinmeyen Partner") if r["_id"] else "Bilinmeyen",
                "match_count": r["match_count"],
                "revenue": r["revenue"],
            }
            for r in rows
        ]

    async def aging_report(
        self,
        org_id: str,
        tenant_id: str,
    ) -> Dict[str, Any]:
        db = await get_db()
        now = datetime.now(timezone.utc)

        cutoff_7 = now - timedelta(days=7)
        cutoff_30 = now - timedelta(days=30)

        # Unpaid > 7 days
        over_7 = await db.webpos_payments.count_documents({
            "tenant_id": tenant_id,
            "organization_id": org_id,
            "status": "recorded",
            "created_at": {"$lt": cutoff_7},
        })

        # Unpaid > 30 days
        over_30 = await db.webpos_payments.count_documents({
            "tenant_id": tenant_id,
            "organization_id": org_id,
            "status": "recorded",
            "created_at": {"$lt": cutoff_30},
        })

        # Amounts
        over_7_amount_pipeline = [
            {"$match": {
                "tenant_id": tenant_id,
                "organization_id": org_id,
                "status": "recorded",
                "created_at": {"$lt": cutoff_7},
            }},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
        ]
        over_30_amount_pipeline = [
            {"$match": {
                "tenant_id": tenant_id,
                "organization_id": org_id,
                "status": "recorded",
                "created_at": {"$lt": cutoff_30},
            }},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
        ]

        over_7_amt = await db.webpos_payments.aggregate(over_7_amount_pipeline).to_list(1)
        over_30_amt = await db.webpos_payments.aggregate(over_30_amount_pipeline).to_list(1)

        return {
            "aging": {
                "over_7_days": {
                    "count": over_7,
                    "amount": over_7_amt[0]["total"] if over_7_amt else 0,
                },
                "over_30_days": {
                    "count": over_30,
                    "amount": over_30_amt[0]["total"] if over_30_amt else 0,
                },
            },
            "generated_at": now.isoformat(),
        }


advanced_reports_service = AdvancedReportsService()
