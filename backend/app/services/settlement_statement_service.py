from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from motor.motor_asyncio import AsyncIOMotorDatabase


@dataclass
class CurrencyTotals:
    count: int = 0
    gross_total: float = 0.0
    commission_total: float = 0.0
    net_total: float = 0.0


class SettlementStatementService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db.settlement_ledger

    async def fetch_items(
        self,
        tenant_id: str,
        perspective: str,
        month_start: datetime,
        month_end: datetime,
        statuses: List[str] | None,
        max_items: int,
    ) -> List[Dict[str, Any]]:
        q: Dict[str, Any] = {
            "created_at": {"$gte": month_start, "$lt": month_end},
        }
        if perspective == "seller":
            q["seller_tenant_id"] = tenant_id
        else:
            q["buyer_tenant_id"] = tenant_id

        if statuses:
            q["status"] = {"$in": statuses}

        cursor = (
            self._col.find(q)
            .sort([("created_at", 1), ("booking_id", 1)])
            .limit(max_items + 1)
        )

        items: List[Dict[str, Any]] = []
        async for doc in cursor:
            doc["settlement_id"] = str(doc.pop("_id"))
            items.append(doc)
        return items

    def compute_totals(self, items: List[Dict[str, Any]]) -> Tuple[Dict[str, CurrencyTotals], CurrencyTotals]:
        per_currency: Dict[str, CurrencyTotals] = defaultdict(CurrencyTotals)
        overall = CurrencyTotals()

        for it in items:
            cur = it.get("currency") or "UNKNOWN"
            gross = float(it.get("gross_amount") or 0.0)
            comm = float(it.get("commission_amount") or 0.0)
            net = float(it.get("net_amount") or 0.0)

            ct = per_currency[cur]
            ct.count += 1
            ct.gross_total += gross
            ct.commission_total += comm
            ct.net_total += net

            overall.count += 1
            overall.gross_total += gross
            overall.commission_total += comm
            overall.net_total += net

        return per_currency, overall

    def compute_counterparties(
        self,
        items: List[Dict[str, Any]],
        perspective: str,
    ) -> List[Dict[str, Any]]:
        # Group by counterparty tenant id
        by_counterparty: Dict[str, CurrencyTotals] = defaultdict(CurrencyTotals)

        for it in items:
            if perspective == "seller":
                cp = it.get("buyer_tenant_id") or ""
            else:
                cp = it.get("seller_tenant_id") or ""
            if not cp:
                continue

            gross = float(it.get("gross_amount") or 0.0)
            comm = float(it.get("commission_amount") or 0.0)
            net = float(it.get("net_amount") or 0.0)

            ct = by_counterparty[cp]
            ct.count += 1
            ct.gross_total += gross
            ct.commission_total += comm
            ct.net_total += net

        result: List[Dict[str, Any]] = []
        for cp_id, ct in by_counterparty.items():
            result.append(
                {
                    "counterparty_tenant_id": cp_id,
                    "count": ct.count,
                    "totals_by_currency": {
                        # For Phase 2.1-B we assume single-currency per statement; keep structure for future
                        "DEFAULT": {
                            "count": ct.count,
                            "gross_total": ct.gross_total,
                            "commission_total": ct.commission_total,
                            "net_total": ct.net_total,
                        }
                    },
                }
            )
        return result
