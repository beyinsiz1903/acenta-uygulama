"""Multi-currency support constants and utilities."""
from __future__ import annotations

from enum import Enum


class SupportedCurrency(str, Enum):
    """Supported currencies for multi-currency reconciliation."""
    TRY = "TRY"
    EUR = "EUR"
    USD = "USD"
    GBP = "GBP"


# Default fallback exchange rates (updated periodically from external source)
DEFAULT_EXCHANGE_RATES: dict[str, float] = {
    "EUR_TRY": 36.50,
    "USD_TRY": 33.80,
    "GBP_TRY": 43.20,
    "EUR_USD": 1.08,
    "EUR_GBP": 0.845,
    "USD_GBP": 0.783,
    "TRY_EUR": 0.0274,
    "TRY_USD": 0.0296,
    "TRY_GBP": 0.0231,
    "USD_EUR": 0.926,
    "GBP_EUR": 1.183,
    "GBP_USD": 1.277,
}

CURRENCY_SYMBOLS: dict[str, str] = {
    "TRY": "₺",
    "EUR": "€",
    "USD": "$",
    "GBP": "£",
}


def get_exchange_rate_key(from_currency: str, to_currency: str) -> str:
    return f"{from_currency}_{to_currency}"


def convert_amount(
    amount: float,
    from_currency: str,
    to_currency: str,
    rates: dict[str, float] | None = None,
) -> float:
    """Convert amount between currencies."""
    if from_currency == to_currency:
        return amount
    lookup = rates or DEFAULT_EXCHANGE_RATES
    key = get_exchange_rate_key(from_currency, to_currency)
    rate = lookup.get(key)
    if rate is None:
        # Try inverse
        inverse_key = get_exchange_rate_key(to_currency, from_currency)
        inverse_rate = lookup.get(inverse_key)
        if inverse_rate and inverse_rate != 0:
            rate = 1.0 / inverse_rate
        else:
            raise ValueError(f"Exchange rate not found: {key}")
    return round(amount * rate, 2)


def get_supported_currencies() -> list[dict[str, str]]:
    return [
        {"code": c.value, "symbol": CURRENCY_SYMBOLS.get(c.value, c.value)}
        for c in SupportedCurrency
    ]
