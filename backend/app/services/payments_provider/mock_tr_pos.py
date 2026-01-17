from __future__ import annotations

import uuid
from typing import Optional

from app.services.payments_provider.base import PaymentInitContext, PaymentInitResult, PaymentProvider


class MockTrPosProvider(PaymentProvider):
    """Mock Turkish bank POS provider.

    This adapter does not call any real bank API. It simply returns a
    deterministic approved response so that higher-level orchestration and
    accounting flows can be exercised safely.

    In later phases this can be replaced by real bank/iyzico adapters while
    keeping the public checkout contract stable.
    """

    def __init__(self, *, provider_name: str = "tr_pos_mock", decline: bool = False) -> None:
        self.provider_name = provider_name
        self.decline = decline

    async def init_payment(self, ctx: PaymentInitContext) -> PaymentInitResult:
        # For now we simply accept all payments unless `decline=True` is set.
        if self.decline:
            return PaymentInitResult(
                ok=False,
                provider=self.provider_name,
                external_id=None,
                client_secret=None,
                reason="mock_declined",
                raw={"booking_id": ctx.booking_id, "amount_cents": ctx.amount_cents},
            )

        external_id = f"trpos_{uuid.uuid4().hex[:16]}"
        return PaymentInitResult(
            ok=True,
            provider=self.provider_name,
            external_id=external_id,
            client_secret=None,
            reason=None,
            raw={"booking_id": ctx.booking_id, "amount_cents": ctx.amount_cents},
        )
