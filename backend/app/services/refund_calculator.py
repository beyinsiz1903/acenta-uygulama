from __future__ import annotations

"""Refund / Penalty calculator (Phase 2B)

MVP rules (single-currency EUR):
- gross_sell = booking["amounts"]["sell"]
- If booking.policy_snapshot.cancellation_policy exists -> policy-based penalty
- Else -> manual/refund-case requested amount (clamped)
- No PENALTY_RECOGNIZED ledger event in Phase 2B; penalty is a reporting concept
  tracked in refund_cases.computed and optionally booking_financials.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Optional


@dataclass
class RefundComputation:
    gross_sell: float
    penalty: float
    refundable: float
    basis: Literal["policy", "manual", "none"]
    policy_ref: dict[str, Any]


class RefundCalculatorService:
    """Pure calculator for refund/penalty amounts.

    Phase 2B is EUR-only; FX/multi-currency is Phase 2C.
    """

    def __init__(self, currency: str = "EUR") -> None:
        self.currency = currency

    def compute_refund(
        self,
        booking: dict,
        now: datetime,
        mode: Literal["policy_first"] = "policy_first",
        manual_requested_amount: Optional[float] = None,
    ) -> RefundComputation:
        """Compute gross_sell, penalty, refundable, basis and policy_ref.

        - booking.currency must match self.currency in Phase 2B.
        - gross_sell = booking["amounts"]["sell"]
        - If cancellation_policy exists: use it (basis="policy").
        - Else: fall back to manual_requested_amount (basis="manual").
        """
        currency = booking.get("currency")
        if currency != self.currency:
            raise ValueError("currency_not_supported")

        amounts = booking.get("amounts") or {}
        gross_sell_raw = float(amounts.get("sell", 0.0))
        gross_sell = max(0.0, gross_sell_raw)

        policy = (
            (booking.get("policy_snapshot") or {}).get("cancellation_policy")
            if booking.get("policy_snapshot")
            else None
        )

        if mode == "policy_first" and policy:
            comp = self._compute_policy_based(gross_sell, booking, policy, now)
        else:
            comp = self._compute_manual(gross_sell, manual_requested_amount)

        # Round to 2 decimals for EUR
        comp.gross_sell = round(comp.gross_sell, 2)
        comp.penalty = round(comp.penalty, 2)
        comp.refundable = round(comp.refundable, 2)
        return comp

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_policy_based(
        self,
        gross_sell: float,
        booking: dict,
        policy: dict[str, Any],
        now: datetime,
    ) -> RefundComputation:
        p_type = policy.get("type")
        basis = "policy"
        policy_ref: dict[str, Any] = {
            "type": p_type or "none",
            "value": policy.get("value"),
            "applied_rule": None,
        }

        penalty = 0.0

        if p_type == "percent":
            value = float(policy.get("value", 0.0))
            penalty = gross_sell * (value / 100.0)
            policy_ref["applied_rule"] = f"percent={value}"  # e.g. 20 => 20%
        elif p_type == "fixed":
            penalty = float(policy.get("fixed", 0.0))
            policy_ref["applied_rule"] = f"fixed={policy.get('fixed')}"
        elif p_type == "nights":
            # MVP: if nights >= 1, treat as full penalty for now
            nights = int(policy.get("nights", 1) or 1)
            if nights >= 1:
                penalty = gross_sell
                policy_ref["applied_rule"] = f"nights={nights}:full_penalty"
            else:
                penalty = 0.0
                policy_ref["applied_rule"] = f"nights={nights}:no_penalty"
        else:
            # Unknown/none policy
            penalty = 0.0
            basis = "none"
            policy_ref["applied_rule"] = "none"

        # Clamp penalty between 0 and gross_sell
        penalty = max(0.0, min(penalty, gross_sell))
        refundable = max(0.0, gross_sell - penalty)

        return RefundComputation(
            gross_sell=gross_sell,
            penalty=penalty,
            refundable=refundable,
            basis=basis,
            policy_ref=policy_ref,
        )

    def _compute_manual(
        self,
        gross_sell: float,
        manual_requested_amount: Optional[float],
    ) -> RefundComputation:
        basis: Literal["policy", "manual", "none"]
        policy_ref: dict[str, Any] = {
            "type": "none",
            "value": None,
            "applied_rule": "manual",
        }

        if manual_requested_amount is None:
            # Default: refund full amount
            refundable = gross_sell
            basis = "manual"
        else:
            refundable = float(manual_requested_amount)
            refundable = max(0.0, min(refundable, gross_sell))
            basis = "manual"

        penalty = max(0.0, gross_sell - refundable)

        return RefundComputation(
            gross_sell=gross_sell,
            penalty=penalty,
            refundable=refundable,
            basis=basis,
            policy_ref=policy_ref,
        )
