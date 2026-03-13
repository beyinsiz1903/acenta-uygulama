"""Supplier Failover Engine.

When a primary supplier fails (circuit open, timeout, error), the engine
selects the next best supplier based on health score, pricing, and
business rules.

Algorithm:
  1. Get ordered supplier list for product type
  2. Filter out circuit-open suppliers
  3. Score remaining by: health_score * 0.4 + price_competitiveness * 0.3 + reliability * 0.3
  4. Return ranked fallback list
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("suppliers.failover")


@dataclass
class SupplierRank:
    supplier_code: str
    health_score: float = 1.0
    price_score: float = 1.0  # lower = better
    reliability_score: float = 1.0
    composite_score: float = 0.0
    circuit_open: bool = False
    disabled: bool = False

    def compute_composite(self) -> float:
        if self.circuit_open or self.disabled:
            return 0.0
        self.composite_score = (
            self.health_score * 0.4
            + self.price_score * 0.3
            + self.reliability_score * 0.3
        )
        return self.composite_score


@dataclass
class FailoverDecision:
    primary_supplier: str
    primary_failed: bool
    selected_supplier: str
    fallback_chain: List[str]
    reason: str
    attempt: int = 1
    decided_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class FailoverEngine:
    """Determines the best supplier to use when the primary fails."""

    def __init__(self):
        # supplier_code -> list of fallback supplier_codes (ordered)
        self._fallback_chains: Dict[str, List[str]] = {}
        # supplier_code -> SupplierRank
        self._rankings: Dict[str, SupplierRank] = {}

    def register_fallback_chain(self, primary: str, fallbacks: List[str]):
        self._fallback_chains[primary] = fallbacks

    def get_fallback_chain(self, primary: str) -> List[str]:
        """Get the fallback chain for a supplier."""
        return self._fallback_chains.get(primary, [])


    def update_ranking(self, supplier_code: str, rank: SupplierRank):
        self._rankings[supplier_code] = rank

    def update_health_score(self, supplier_code: str, score: float):
        if supplier_code not in self._rankings:
            self._rankings[supplier_code] = SupplierRank(supplier_code=supplier_code)
        self._rankings[supplier_code].health_score = score
        self._rankings[supplier_code].compute_composite()

    def mark_circuit_open(self, supplier_code: str):
        if supplier_code not in self._rankings:
            self._rankings[supplier_code] = SupplierRank(supplier_code=supplier_code)
        self._rankings[supplier_code].circuit_open = True

    def mark_circuit_closed(self, supplier_code: str):
        if supplier_code in self._rankings:
            self._rankings[supplier_code].circuit_open = False

    def get_fallback(
        self,
        primary_supplier: str,
        *,
        exclude: Optional[List[str]] = None,
        product_type: Optional[str] = None,
    ) -> FailoverDecision:
        """Select the best fallback supplier.

        Returns FailoverDecision with the selected supplier and reasoning.
        """
        exclude_set = set(exclude or [])
        exclude_set.add(primary_supplier)

        # Get explicit fallback chain
        chain = self._fallback_chains.get(primary_supplier, [])

        # Filter and score candidates
        candidates: List[SupplierRank] = []
        for code in chain:
            if code in exclude_set:
                continue
            rank = self._rankings.get(code, SupplierRank(supplier_code=code))
            rank.compute_composite()
            if not rank.circuit_open and not rank.disabled:
                candidates.append(rank)

        # Also include any suppliers not in chain but ranked (dynamic fallback)
        for code, rank in self._rankings.items():
            if code in exclude_set or code in [c.supplier_code for c in candidates]:
                continue
            rank.compute_composite()
            if not rank.circuit_open and not rank.disabled and rank.composite_score > 0:
                candidates.append(rank)

        # Sort by composite score descending
        candidates.sort(key=lambda r: r.composite_score, reverse=True)

        if not candidates:
            return FailoverDecision(
                primary_supplier=primary_supplier,
                primary_failed=True,
                selected_supplier=primary_supplier,  # no alternative
                fallback_chain=[],
                reason="no_available_fallback",
            )

        selected = candidates[0]
        return FailoverDecision(
            primary_supplier=primary_supplier,
            primary_failed=True,
            selected_supplier=selected.supplier_code,
            fallback_chain=[c.supplier_code for c in candidates],
            reason=f"failover_to_{selected.supplier_code}_score_{selected.composite_score:.2f}",
        )

    async def log_failover(self, db, decision: FailoverDecision, organization_id: str):
        """Persist failover decision for audit."""
        try:
            from app.utils import now_utc
            await db.supplier_failover_logs.insert_one({
                "organization_id": organization_id,
                "primary_supplier": decision.primary_supplier,
                "selected_supplier": decision.selected_supplier,
                "fallback_chain": decision.fallback_chain,
                "reason": decision.reason,
                "attempt": decision.attempt,
                "decided_at": decision.decided_at,
                "created_at": now_utc(),
            })
        except Exception as e:
            logger.warning("Failed to log failover: %s", e)

        # Emit event
        try:
            from app.infrastructure.event_bus import publish
            await publish(
                "supplier.failover_triggered",
                payload={
                    "primary_supplier": decision.primary_supplier,
                    "selected_supplier": decision.selected_supplier,
                    "reason": decision.reason,
                },
                organization_id=organization_id,
                source="failover_engine",
            )
        except Exception:
            pass


# Singleton
failover_engine = FailoverEngine()
