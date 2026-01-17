from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol


@dataclass
class PaymentInitContext:
    """Minimal context needed to initialise a payment.

    This is intentionally B2C/public-funnel focused for now.
    """

    organization_id: str
    booking_id: str
    amount_cents: int
    currency: str
    # Optional correlation/idempotency metadata
    idempotency_key: Optional[str] = None
    correlation_id: Optional[str] = None


@dataclass
class PaymentInitResult:
    ok: bool
    provider: str
    external_id: Optional[str] = None
    client_secret: Optional[str] = None
    reason: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


class PaymentProvider(Protocol):
    """Common interface for payment providers.

    This is a very small surface for PROMPT 5; Stripe keeps its existing
    integration path, and TR POS mock uses this interface for experiments.
    """

    async def init_payment(self, ctx: PaymentInitContext) -> PaymentInitResult:  # pragma: no cover - interface
        ...
