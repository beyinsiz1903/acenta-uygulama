"""Pure helper functions extracted from `stripe_checkout_service.py` (T009).

These functions have no dependency on the `StripeCheckoutService` class
state, no DB access, and no I/O beyond reading environment variables.
Extracted into their own module so the main service file can shrink and
each helper can be unit-tested in isolation.

The original module re-exports every name defined here for backward
compatibility (e.g. `billing_webhooks.py` imports `_iso_from_unix`
directly from `app.services.stripe_checkout_service`).
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import stripe

REAL_PRICE_PREFIX = "price_"
REAL_SUBSCRIPTION_PREFIX = "sub_"
REAL_CUSTOMER_PREFIX = "cus_"

PLAN_ORDER = {"trial": 0, "starter": 1, "pro": 2, "enterprise": 3}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _billing_mode() -> str:
    key = os.environ.get("STRIPE_API_KEY", "")
    return "live" if "live" in key else "test"


def _iso_from_unix(value: Any) -> Optional[str]:
    if value in (None, ""):
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat()
    except Exception:
        return None


def _is_real_price_id(value: Optional[str]) -> bool:
    return bool(value and value.startswith(REAL_PRICE_PREFIX))


def _is_real_subscription_id(value: Optional[str]) -> bool:
    return bool(value and value.startswith(REAL_SUBSCRIPTION_PREFIX))


def _is_real_customer_id(value: Optional[str]) -> bool:
    return bool(value and value.startswith(REAL_CUSTOMER_PREFIX))


def _schedule_id(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return getattr(value, "id", None)


def _coerce_datetime(value: Any) -> Optional[datetime]:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except Exception:
            return None
    return None


def _should_refresh_subscription_snapshot(
    subscription: Optional[dict[str, Any]], *, max_age_minutes: int = 10
) -> bool:
    if not subscription:
        return False
    updated_at = _coerce_datetime(subscription.get("updated_at"))
    if updated_at is None:
        return True
    return (_now() - updated_at) >= timedelta(minutes=max_age_minutes)


def _subscription_first_item(subscription: Any) -> Any:
    if not subscription:
        return None
    items_container = (
        subscription.get("items", {})
        if hasattr(subscription, "get")
        else getattr(subscription, "items", {})
    )
    if callable(items_container):
        items_container = {}
    data = (
        items_container.get("data")
        if isinstance(items_container, dict)
        else getattr(items_container, "data", None)
    )
    return (data or [None])[0]


def _stripe_value(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if hasattr(obj, "get"):
        try:
            return obj.get(key, default)
        except Exception:
            pass
    return getattr(obj, key, default)


def _interval_label(interval: str) -> str:
    return "Yıllık" if interval == "yearly" else "Aylık"


def _coerce_minor_amount(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except Exception:
        try:
            return int(float(value))
        except Exception:
            return None


def _format_try_minor(value: Any) -> Optional[str]:
    amount_minor = _coerce_minor_amount(value)
    if amount_minor is None:
        return None
    amount = amount_minor / 100.0
    formatted = (
        f"{amount:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    )
    return f"₺{formatted}"


def _plan_change_mode(
    current_plan: str,
    current_interval: str,
    target_plan: str,
    target_interval: str,
) -> str:
    current_rank = PLAN_ORDER.get(current_plan or "trial", 0)
    target_rank = PLAN_ORDER.get(target_plan, 0)
    if target_rank > current_rank:
        return "upgrade_now"
    if target_rank < current_rank:
        return "downgrade_later"
    if current_interval == target_interval:
        return "none"
    if current_interval == "monthly" and target_interval == "yearly":
        return "upgrade_now"
    return "downgrade_later"


def _is_missing_stripe_resource_error(exc: Exception) -> bool:
    return isinstance(exc, stripe.error.InvalidRequestError) and "No such" in str(exc)


__all__ = [
    "REAL_PRICE_PREFIX",
    "REAL_SUBSCRIPTION_PREFIX",
    "REAL_CUSTOMER_PREFIX",
    "PLAN_ORDER",
    "_now",
    "_billing_mode",
    "_iso_from_unix",
    "_is_real_price_id",
    "_is_real_subscription_id",
    "_is_real_customer_id",
    "_schedule_id",
    "_coerce_datetime",
    "_should_refresh_subscription_snapshot",
    "_subscription_first_item",
    "_stripe_value",
    "_interval_label",
    "_coerce_minor_amount",
    "_format_try_minor",
    "_plan_change_mode",
    "_is_missing_stripe_resource_error",
]
