from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class InstallmentPlan:
    installments: int
    monthly_amount_cents: int
    total_amount_cents: int
    total_interest_cents: int


def _distribute_cents(total_cents: int, installments: int) -> List[int]:
    """Distribute cents across installments deterministically.

    Example: 100 / 3 -> [34, 33, 33]
    We put any remainder on the first installments to keep sum stable.
    """

    base = total_cents // installments
    remainder = total_cents % installments
    amounts = []
    for i in range(installments):
        extra = 1 if i < remainder else 0
        amounts.append(base + extra)
    return amounts


def compute_mock_installment_plans(amount_cents: int, currency: str) -> List[InstallmentPlan]:
    """Return a small set of mock installment plans for TR Pack.

    This is intentionally simple and deterministic. Real bank/iyzico
    integrations can override this logic later.
    """

    if amount_cents <= 0:
        return []

    # For now we ignore currency and return the same structure; later we can
    # specialise for TRY vs EUR if needed.
    candidates = [3, 6]  # 3 and 6 installments as a starting point

    plans: List[InstallmentPlan] = []
    for n in candidates:
        # Simple mock: add 2% per 3 months as interest
        # 3 taksit -> 2%, 6 taksit -> 4%
        interest_rate = 0.02 * (n / 3)
        total_with_interest = int(round(amount_cents * (1 + interest_rate)))
        monthly_amounts = _distribute_cents(total_with_interest, n)
        total_interest = total_with_interest - amount_cents
        plans.append(
            InstallmentPlan(
                installments=n,
                monthly_amount_cents=monthly_amounts[0],  # first month (others are similar)
                total_amount_cents=total_with_interest,
                total_interest_cents=total_interest,
            )
        )

    return plans
