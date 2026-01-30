from __future__ import annotations

from typing import Optional

from fastapi import status

from app.errors import AppError


def ensure_try(currency: Optional[str]) -> str:
    """Normalize and enforce TRY-only currency.

    Raises AppError(422, UNSUPPORTED_CURRENCY) with standard details if the
    given currency is not TRY. Returns the normalized currency ("TRY") on
    success.
    """

    cur = (currency or "").strip().upper()
    if cur != "TRY":
        # Use None instead of empty string in details when currency missing
        normalized = cur or None
        raise AppError(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="UNSUPPORTED_CURRENCY",
            message="Only TRY is supported in this phase.",
            details={"currency": normalized, "expected": "TRY"},
        )

    return "TRY"
