"""Task #3 refactor — back-compat & behaviour tests (DB-free).

These tests exist to prove that the Stripe and B2B router refactors did
not silently change the public surface or behaviour of the modules they
touched. They are intentionally hermetic (no Mongo, no network) so they
run on every CI lane, including environments where the shared Atlas
cluster is at its collection cap.

Coverage:
  1. Legacy import paths still resolve every previously-public name on
     `app.services.stripe_checkout_service` and
     `app.modules.b2b.routers.b2b_bookings`.
  2. The composed `StripeCheckoutService` exposes every public method
     of the original monolithic class.
  3. No two Stripe mixins define the same method name (MRO shadow guard).
  4. Route inventory hash matches the recorded baseline (proves no route
     was dropped, added, or renamed during the split).
  5. Pure helpers (`_validate_origin`, `_normalize_path`, `_plan_config`)
     keep their pre-refactor behaviour and error contracts.
  6. Webhook dispatcher routes each event type to the correct mixin
     method with the expected arguments.
"""
from __future__ import annotations

import hashlib
import inspect
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

# ---------------------------------------------------------------------------
# 1. Back-compat: legacy import paths must still resolve.
# ---------------------------------------------------------------------------

LEGACY_STRIPE_NAMES = (
    # Class & singleton
    "StripeCheckoutService",
    "stripe_checkout_service",
    # Module-level constants
    "PLAN_CHECKOUT_MATRIX",
    "STRIPE_PROXY_BASE",
    "PORTAL_CONFIG_MARKER",
    # Re-exported pure helpers (legacy import sites depend on these —
    # e.g. modules/finance/routers/billing_webhooks.py imports
    # _iso_from_unix from this module).
    "PLAN_ORDER",
    "REAL_CUSTOMER_PREFIX",
    "REAL_PRICE_PREFIX",
    "REAL_SUBSCRIPTION_PREFIX",
    "_billing_mode",
    "_coerce_datetime",
    "_coerce_minor_amount",
    "_format_try_minor",
    "_interval_label",
    "_is_missing_stripe_resource_error",
    "_is_real_customer_id",
    "_is_real_price_id",
    "_is_real_subscription_id",
    "_iso_from_unix",
    "_now",
    "_plan_change_mode",
    "_schedule_id",
    "_should_refresh_subscription_snapshot",
    "_stripe_value",
    "_subscription_first_item",
)

LEGACY_B2B_BOOKINGS_NAMES = (
    "router",
    "_get_visible_listing",
    "get_pricing_service",
    "get_booking_service",
    "get_idem_repo",
)

# Public methods that existed on the original `StripeCheckoutService`
# class. If any of these disappear, Stripe webhook handling, billing UI,
# or self-serve plan changes will silently break in production.
ORIGINAL_STRIPE_PUBLIC_METHODS = (
    "create_checkout_session",
    "sync_checkout_status",
    "handle_webhook",
    "change_plan",
    "get_billing_overview",
    "create_customer_portal_session",
    "cancel_subscription_at_period_end",
    "reactivate_subscription",
    "mark_invoice_paid",
    "mark_payment_failed",
    "mark_subscription_canceled",
    "sync_provider_subscription_record",
    # Private-but-relied-upon (called from other services and from tests):
    "_repair_customer_reference",
    "_sync_subscription_document",
    "_apply_successful_checkout",
    "_validate_origin",
    "_normalize_path",
    "_plan_config",
    "_get_real_customer_id",
    "_resolve_org_id_for_tenant",
    "_ensure_recurring_price",
    "_ensure_portal_configuration",
    "_retrieve_checkout_session",
    "_retrieve_subscription",
    "_release_schedule_if_present",
    "_clear_scheduled_change",
    "_demote_stale_subscription_reference",
    "_clear_stale_customer_reference",
    "_find_tenant_by_subscription",
    "_stripe_call",
    "_configure_stripe_sdk",
    "_checkout_client",
    "_api_key",
)


def test_stripe_checkout_service_legacy_imports_resolve():
    import app.services.stripe_checkout_service as scs

    missing = [name for name in LEGACY_STRIPE_NAMES if not hasattr(scs, name)]
    assert not missing, (
        f"Legacy public symbols missing from app.services.stripe_checkout_service: {missing}. "
        "External modules (notably billing_webhooks.py) import these by name."
    )


def test_b2b_bookings_aggregator_reexports_legacy_names():
    import app.modules.b2b.routers.b2b_bookings as bb

    missing = [name for name in LEGACY_B2B_BOOKINGS_NAMES if not hasattr(bb, name)]
    assert not missing, (
        f"Legacy public symbols missing from b2b_bookings aggregator: {missing}. "
        "b2b_bookings_list and bootstrap wiring depend on these."
    )


def test_legacy_compat_shim_still_exposes_router():
    """`app.routers.b2b_bookings` is a sys.modules redirect kept for old imports."""
    from app.routers.b2b_bookings import router as legacy_router
    from app.modules.b2b.routers.b2b_bookings import router as canonical_router

    assert legacy_router is canonical_router, (
        "The legacy app.routers.b2b_bookings shim must point at the canonical router."
    )


def test_billing_webhooks_legacy_helper_import_path_works():
    """`billing_webhooks.py` imports `_iso_from_unix` *through* the service."""
    from app.services.stripe_checkout_service import _iso_from_unix as via_service
    from app.services.stripe_checkout_helpers import _iso_from_unix as via_helpers

    assert via_service is via_helpers, (
        "_iso_from_unix re-exported from stripe_checkout_service must be the "
        "same callable as the canonical helper — otherwise legacy importers "
        "see a stale copy."
    )


# ---------------------------------------------------------------------------
# 2 & 3. Composition guarantees: every method present, no MRO shadowing.
# ---------------------------------------------------------------------------


def test_composed_service_exposes_every_original_public_method():
    from app.services.stripe_checkout_service import stripe_checkout_service

    missing = [m for m in ORIGINAL_STRIPE_PUBLIC_METHODS if not hasattr(stripe_checkout_service, m)]
    assert not missing, (
        f"StripeCheckoutService is missing methods after refactor: {missing}"
    )


def test_no_method_name_collisions_across_stripe_mixins():
    """Two mixins defining the same method name would silently shadow each
    other through MRO. This guard catches that class of bug at import time."""
    from app.services.stripe_base_mixin import StripeBaseMixin
    from app.services.stripe_lifecycle_mixin import StripeLifecycleMixin
    from app.services.stripe_overview_mixin import StripeOverviewMixin
    from app.services.stripe_plan_change_mixin import StripePlanChangeMixin
    from app.services.stripe_portal_mixin import StripePortalMixin
    from app.services.stripe_session_mixin import StripeSessionMixin
    from app.services.stripe_subscription_sync_mixin import StripeSubscriptionSyncMixin
    from app.services.stripe_webhook_mixin import StripeWebhookMixin

    mixins = [
        StripeBaseMixin,
        StripeLifecycleMixin,
        StripeOverviewMixin,
        StripePlanChangeMixin,
        StripePortalMixin,
        StripeSessionMixin,
        StripeSubscriptionSyncMixin,
        StripeWebhookMixin,
    ]

    seen: dict[str, str] = {}
    collisions: list[str] = []
    for cls in mixins:
        for name, value in cls.__dict__.items():
            if name.startswith("__") or not callable(value):
                continue
            if name in seen:
                collisions.append(f"{name}: {seen[name]} vs {cls.__name__}")
            else:
                seen[name] = cls.__name__

    assert not collisions, (
        "Stripe mixins define overlapping method names — MRO shadowing risk:\n  "
        + "\n  ".join(collisions)
    )


# ---------------------------------------------------------------------------
# 4. Route inventory parity — protects every URL the API exposes.
# ---------------------------------------------------------------------------

# Captured pre-refactor on the same baseline (tasks #1 & #2 merged).
EXPECTED_ROUTE_COUNT = 1598
EXPECTED_ROUTE_HASH = "ecdaf3ab57f42363c84e2ff2e8fc5617"


def test_route_inventory_unchanged_by_task3_refactor():
    from app.bootstrap.api_app import app

    sigs = sorted(
        f"{sorted(r.methods) if hasattr(r, 'methods') and r.methods else []} "
        f"{r.path if hasattr(r, 'path') else ''}"
        for r in app.routes
    )
    actual_count = len(sigs)
    actual_hash = hashlib.md5("\n".join(sigs).encode()).hexdigest()

    assert actual_count == EXPECTED_ROUTE_COUNT, (
        f"Route count drifted: expected {EXPECTED_ROUTE_COUNT}, got {actual_count}. "
        "A route was added or removed by the refactor."
    )
    assert actual_hash == EXPECTED_ROUTE_HASH, (
        f"Route signature hash drifted: expected {EXPECTED_ROUTE_HASH}, "
        f"got {actual_hash}. A route's method or path was changed."
    )


# ---------------------------------------------------------------------------
# 5. Pure-helper behaviour — preserved by extraction.
# ---------------------------------------------------------------------------


def test_validate_origin_accepts_https_and_strips_path():
    from app.services.stripe_checkout_service import stripe_checkout_service

    assert (
        stripe_checkout_service._validate_origin("https://app.syroce.com/some/path?x=1")
        == "https://app.syroce.com"
    )


def test_validate_origin_rejects_invalid_scheme():
    from app.errors import AppError
    from app.services.stripe_checkout_service import stripe_checkout_service

    with pytest.raises(AppError) as excinfo:
        stripe_checkout_service._validate_origin("ftp://hacker.example.com")
    assert excinfo.value.code == "invalid_origin_url"
    assert excinfo.value.status_code == 400


def test_normalize_path_prepends_slash_and_falls_back_to_default():
    from app.services.stripe_checkout_service import stripe_checkout_service

    svc = stripe_checkout_service
    assert svc._normalize_path("billing", "/pricing") == "/billing"
    assert svc._normalize_path("/billing", "/pricing") == "/billing"
    assert svc._normalize_path(None, "/pricing") == "/pricing"
    assert svc._normalize_path("   ", "/pricing") == "/pricing"


def test_plan_config_returns_known_plan_and_rejects_unknown():
    from app.errors import AppError
    from app.services.stripe_checkout_service import stripe_checkout_service

    cfg = stripe_checkout_service._plan_config("starter", "monthly")
    assert cfg["currency"] == "try"
    assert cfg["amount"] == 990.0

    with pytest.raises(AppError) as excinfo:
        stripe_checkout_service._plan_config("ultra", "monthly")
    assert excinfo.value.code == "plan_not_checkout_enabled"
    assert excinfo.value.status_code == 422


# ---------------------------------------------------------------------------
# 6. Webhook dispatcher — verify each event type reaches the right mixin
#    method with the expected arguments. Fully mocked, no Mongo, no Stripe.
# ---------------------------------------------------------------------------


@pytest.fixture
def patched_service():
    """Yield the singleton with all of its sync/lifecycle methods mocked."""
    from app.services.stripe_checkout_service import stripe_checkout_service as svc

    patches = {
        "_checkout_client": patch.object(svc, "_checkout_client"),
        "sync_checkout_status": patch.object(svc, "sync_checkout_status", new_callable=AsyncMock),
        "_find_tenant_by_subscription": patch.object(svc, "_find_tenant_by_subscription", new_callable=AsyncMock),
        "mark_invoice_paid": patch.object(svc, "mark_invoice_paid", new_callable=AsyncMock),
        "mark_payment_failed": patch.object(svc, "mark_payment_failed", new_callable=AsyncMock),
        "mark_subscription_canceled": patch.object(svc, "mark_subscription_canceled", new_callable=AsyncMock),
        "sync_provider_subscription_record": patch.object(svc, "sync_provider_subscription_record", new_callable=AsyncMock),
    }

    started = {name: p.start() for name, p in patches.items()}
    started["_find_tenant_by_subscription"].return_value = "tenant-xyz"

    fake_webhook_response = SimpleNamespace(
        event_id=None,  # skip dedupe path so we don't touch Mongo
        event_type=None,
        session_id=None,
        payment_status=None,
        metadata=None,
    )
    fake_client = SimpleNamespace(handle_webhook=AsyncMock(return_value=fake_webhook_response))
    started["_checkout_client"].return_value = fake_client

    try:
        yield svc, started, fake_client
    finally:
        for p in patches.values():
            p.stop()


@pytest.mark.anyio
async def test_webhook_dispatcher_routes_invoice_paid(patched_service, monkeypatch):
    svc, mocks, _ = patched_service
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")

    payload = (
        b'{"type":"invoice.paid","data":{"object":'
        b'{"subscription":"sub_xyz","amount_paid":12345,'
        b'"status_transitions":{"paid_at":1700000000}}}}'
    )
    result = await svc.handle_webhook(SimpleNamespace(base_url="https://x/"), payload, "sig")

    assert result["status"] == "ok"
    mocks["mark_invoice_paid"].assert_awaited_once()
    kwargs = mocks["mark_invoice_paid"].await_args.kwargs
    assert kwargs["subscription_id"] == "sub_xyz"
    assert kwargs["amount_paid"] == 12345
    mocks["mark_payment_failed"].assert_not_awaited()
    mocks["mark_subscription_canceled"].assert_not_awaited()


@pytest.mark.anyio
async def test_webhook_dispatcher_routes_payment_failed(patched_service, monkeypatch):
    svc, mocks, _ = patched_service
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")

    payload = (
        b'{"type":"invoice.payment_failed","data":{"object":'
        b'{"subscription":"sub_xyz","amount_due":999,'
        b'"hosted_invoice_url":"https://h","invoice_pdf":"https://p",'
        b'"status_transitions":{"finalized_at":1700000000}}}}'
    )
    await svc.handle_webhook(SimpleNamespace(base_url="https://x/"), payload, "sig")

    mocks["mark_payment_failed"].assert_awaited_once()
    kwargs = mocks["mark_payment_failed"].await_args.kwargs
    assert kwargs["subscription_id"] == "sub_xyz"
    assert kwargs["amount_due"] == 999
    assert kwargs["invoice_hosted_url"] == "https://h"
    assert kwargs["invoice_pdf_url"] == "https://p"


@pytest.mark.anyio
async def test_webhook_dispatcher_routes_subscription_deleted(patched_service, monkeypatch):
    svc, mocks, _ = patched_service
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")

    payload = (
        b'{"type":"customer.subscription.deleted","data":{"object":'
        b'{"id":"sub_xyz","canceled_at":1700000000}}}'
    )
    await svc.handle_webhook(SimpleNamespace(base_url="https://x/"), payload, "sig")

    mocks["mark_subscription_canceled"].assert_awaited_once()
    kwargs = mocks["mark_subscription_canceled"].await_args.kwargs
    assert kwargs["subscription_id"] == "sub_xyz"


@pytest.mark.anyio
async def test_webhook_dispatcher_routes_subscription_updated(patched_service, monkeypatch):
    svc, mocks, _ = patched_service
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")

    payload = (
        b'{"type":"customer.subscription.updated","data":{"object":'
        b'{"id":"sub_xyz"}}}'
    )
    await svc.handle_webhook(SimpleNamespace(base_url="https://x/"), payload, "sig")

    mocks["sync_provider_subscription_record"].assert_awaited_once()
    args = mocks["sync_provider_subscription_record"].await_args.args
    assert args == ("tenant-xyz", "sub_xyz")


@pytest.mark.anyio
async def test_webhook_dispatcher_rejects_when_secret_missing(monkeypatch):
    from app.errors import AppError
    from app.services.stripe_checkout_service import stripe_checkout_service

    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
    with pytest.raises(AppError) as excinfo:
        await stripe_checkout_service.handle_webhook(
            SimpleNamespace(base_url="https://x/"), b"{}", None
        )
    assert excinfo.value.status_code == 503
    assert excinfo.value.code == "webhook_secret_missing"


# ---------------------------------------------------------------------------
# 7. b2b_bookings re-exported helpers are real, callable, and identity-equal
#    to their canonical definitions — guards against accidental shadowing.
# ---------------------------------------------------------------------------


def test_b2b_aggregator_reexports_have_callable_identity():
    from app.modules.b2b.routers import b2b_bookings as agg
    from app.modules.b2b.routers import b2b_bookings_create as canonical

    assert agg._get_visible_listing is canonical._get_visible_listing
    assert agg.get_pricing_service is canonical.get_pricing_service
    assert agg.get_booking_service is canonical.get_booking_service
    assert agg.get_idem_repo is canonical.get_idem_repo
    assert inspect.iscoroutinefunction(agg._get_visible_listing)
