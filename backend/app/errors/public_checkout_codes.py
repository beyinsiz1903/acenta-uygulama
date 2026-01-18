from __future__ import annotations

# Re-export canonical public checkout error codes from app.errors to keep a single source of truth.
from app.errors import PublicCheckoutErrorCode

CANONICAL_PUBLIC_CHECKOUT_ERROR_CODES = {code.value for code in PublicCheckoutErrorCode}
