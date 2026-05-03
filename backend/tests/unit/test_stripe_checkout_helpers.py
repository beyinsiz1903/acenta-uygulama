"""DB-free unit tests for the helpers extracted in T009.

These exercise every pure function in
`app.services.stripe_checkout_helpers` without touching the
`StripeCheckoutService` class or the database. They also assert that the
re-export from `stripe_checkout_service` is still wired up so legacy
import sites (e.g. `billing_webhooks._iso_from_unix`) keep working.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.services import stripe_checkout_helpers as h


def test_now_is_utc_aware():
    n = h._now()
    assert n.tzinfo is not None
    assert n.utcoffset() == timedelta(0)


def test_billing_mode_default_is_test(monkeypatch):
    monkeypatch.delenv("STRIPE_API_KEY", raising=False)
    assert h._billing_mode() == "test"


def test_billing_mode_live(monkeypatch):
    monkeypatch.setenv("STRIPE_API_KEY", "sk_live_abc123")
    assert h._billing_mode() == "live"


def test_billing_mode_test(monkeypatch):
    monkeypatch.setenv("STRIPE_API_KEY", "sk_test_xyz789")
    assert h._billing_mode() == "test"


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, None),
        ("", None),
        ("already-iso-string", "already-iso-string"),
        (1700000000, "2023-11-14T22:13:20+00:00"),
    ],
)
def test_iso_from_unix(value, expected):
    assert h._iso_from_unix(value) == expected


def test_iso_from_unix_datetime_passthrough():
    dt = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)
    assert h._iso_from_unix(dt) == "2024-06-01T12:00:00+00:00"


def test_iso_from_unix_string_passthrough():
    # The helper treats any string as already-ISO and returns it as-is —
    # this is the documented behavior that callers rely on (cached values).
    assert h._iso_from_unix("not-a-number") == "not-a-number"


def test_iso_from_unix_unconvertible_object_returns_none():
    class _Weird:
        def __int__(self):
            raise ValueError("nope")

    assert h._iso_from_unix(_Weird()) is None


def test_real_id_predicates():
    assert h._is_real_price_id("price_abc")
    assert not h._is_real_price_id("manual_xyz")
    assert not h._is_real_price_id(None)
    assert h._is_real_subscription_id("sub_123")
    assert not h._is_real_subscription_id("local_sub_123")
    assert h._is_real_customer_id("cus_xxx")
    assert not h._is_real_customer_id("test_cus_xxx")


def test_schedule_id_variants():
    assert h._schedule_id(None) is None
    assert h._schedule_id("sched_1") == "sched_1"

    class _Obj:
        id = "sched_2"

    assert h._schedule_id(_Obj()) == "sched_2"


def test_coerce_datetime_naive_becomes_utc():
    naive = datetime(2024, 1, 1, 0, 0)
    out = h._coerce_datetime(naive)
    assert out is not None
    assert out.tzinfo == timezone.utc


def test_coerce_datetime_iso_string_with_z():
    out = h._coerce_datetime("2024-01-01T00:00:00Z")
    assert out is not None
    assert out.tzinfo is not None


def test_coerce_datetime_invalid():
    assert h._coerce_datetime("not-a-date") is None
    assert h._coerce_datetime(None) is None


def test_should_refresh_subscription_snapshot():
    # Falsy (None / empty dict) short-circuits to False — see the
    # `if not subscription: return False` guard.
    assert h._should_refresh_subscription_snapshot(None) is False
    assert h._should_refresh_subscription_snapshot({}) is False
    # Truthy with missing updated_at → refresh.
    assert (
        h._should_refresh_subscription_snapshot({"id": "sub_1"}) is True
    )
    # Fresh (within max_age) → no refresh.
    fresh = {"id": "sub_1", "updated_at": h._now().isoformat()}
    assert h._should_refresh_subscription_snapshot(fresh, max_age_minutes=10) is False
    # Stale → refresh.
    stale_dt = (h._now() - timedelta(minutes=30)).isoformat()
    assert (
        h._should_refresh_subscription_snapshot(
            {"id": "sub_1", "updated_at": stale_dt}, max_age_minutes=10
        )
        is True
    )


def test_subscription_first_item():
    assert h._subscription_first_item(None) is None
    assert h._subscription_first_item({}) is None
    sub = {"items": {"data": [{"id": "si_1"}, {"id": "si_2"}]}}
    assert h._subscription_first_item(sub) == {"id": "si_1"}


def test_stripe_value_dict_and_attr():
    assert h._stripe_value(None, "x", "fallback") == "fallback"
    assert h._stripe_value({"a": 1}, "a") == 1
    assert h._stripe_value({"a": 1}, "missing", 99) == 99

    class _Obj:
        b = 2

    assert h._stripe_value(_Obj(), "b") == 2
    assert h._stripe_value(_Obj(), "missing", "d") == "d"


def test_interval_label():
    assert h._interval_label("yearly") == "Yıllık"
    assert h._interval_label("monthly") == "Aylık"
    assert h._interval_label("anything-else") == "Aylık"


def test_coerce_minor_amount():
    assert h._coerce_minor_amount(None) is None
    assert h._coerce_minor_amount("") is None
    assert h._coerce_minor_amount(1234) == 1234
    assert h._coerce_minor_amount("1234") == 1234
    assert h._coerce_minor_amount("12.34") == 12
    assert h._coerce_minor_amount("not-a-number") is None


def test_format_try_minor_locale():
    # 99000 minor → 990.00 TRY → "₺990,00"
    assert h._format_try_minor(99000) == "₺990,00"
    # 249000 minor → 2490.00 TRY → "₺2.490,00" (Turkish formatting)
    assert h._format_try_minor(249000) == "₺2.490,00"
    assert h._format_try_minor(None) is None


@pytest.mark.parametrize(
    "current_plan,current_int,target_plan,target_int,expected",
    [
        ("trial", "monthly", "starter", "monthly", "upgrade_now"),
        ("starter", "monthly", "pro", "monthly", "upgrade_now"),
        ("pro", "monthly", "starter", "monthly", "downgrade_later"),
        ("pro", "monthly", "pro", "monthly", "none"),
        ("pro", "monthly", "pro", "yearly", "upgrade_now"),
        ("pro", "yearly", "pro", "monthly", "downgrade_later"),
        ("", "monthly", "starter", "monthly", "upgrade_now"),  # empty current_plan → trial
    ],
)
def test_plan_change_mode(current_plan, current_int, target_plan, target_int, expected):
    assert (
        h._plan_change_mode(current_plan, current_int, target_plan, target_int)
        == expected
    )


def test_is_missing_stripe_resource_error():
    import stripe

    real_err = stripe.error.InvalidRequestError(
        "No such customer: cus_xxx", param="customer"
    )
    assert h._is_missing_stripe_resource_error(real_err) is True

    other = stripe.error.InvalidRequestError("Invalid input", param="x")
    assert h._is_missing_stripe_resource_error(other) is False

    assert h._is_missing_stripe_resource_error(ValueError("nope")) is False


def test_helpers_reexported_from_service_module():
    """Critical back-compat: legacy imports from
    `app.services.stripe_checkout_service` must still resolve.
    """
    from app.services import stripe_checkout_service as svc

    assert svc._iso_from_unix is h._iso_from_unix
    assert svc._plan_change_mode is h._plan_change_mode
    assert svc.PLAN_ORDER is h.PLAN_ORDER
    assert svc.REAL_PRICE_PREFIX == "price_"
