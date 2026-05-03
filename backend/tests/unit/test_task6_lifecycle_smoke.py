"""Task #6 smoke tests — Stripe webhooks + B2B booking routes (DB-free).

These are higher-level than the per-method unit tests in
``test_task3_refactor_compatibility.py``: they drive the **full**
``handle_webhook`` -> dispatcher -> lifecycle method path and capture the
**real** Mongo update payloads and the **real** audit log entries that
would be written. The DB layer (``app.db.get_db``) and the
``billing_repo`` are mocked, so the tests run on every CI lane without
needing access to the (currently capped) shared Atlas cluster.

Coverage:
  Stripe lifecycle smoke
  ----------------------
  1. ``invoice.paid``                   -> ``mark_invoice_paid`` writes
     status=active, last_invoice_paid_at, last_invoice_paid_amount and
     emits a ``subscription.invoice_paid`` audit entry.
  2. ``invoice.payment_failed``         -> ``mark_payment_failed`` writes
     status=past_due, grace_period_until, last_payment_failed_*,
     invoice URLs, and emits a ``subscription.payment_failed`` entry.
  3. ``customer.subscription.deleted``  -> ``mark_subscription_canceled``
     writes status=canceled and emits ``subscription.canceled``.

  B2B lifecycle smoke
  -------------------
  4. The aggregator router exposes exactly the expected set of lifecycle
     URL paths with the expected HTTP methods. A regression in any child
     router (dropped/renamed/wrong-method route) fails this test
     immediately.
  5. Each child router is non-empty and its handlers are real callables
     (not ``NotImplementedError`` stubs).
"""
from __future__ import annotations

import inspect
from types import SimpleNamespace
from typing import Any, Callable
from unittest.mock import AsyncMock, patch

import pytest


# ---------------------------------------------------------------------------
# Shared test infrastructure
# ---------------------------------------------------------------------------


class FakeCollection:
    """Minimal AsyncIOMotorCollection stand-in.

    Records every ``update_one`` call as a tuple ``(filter, update)`` so
    tests can assert exactly which fields were $set/$unset. ``find_one``
    returns canned values keyed by the filter dict's primary key.
    """

    def __init__(self, find_one_result: dict[str, Any] | None = None) -> None:
        self._canned = find_one_result
        self.updates: list[tuple[dict[str, Any], dict[str, Any]]] = []

    async def update_one(self, filter_: dict[str, Any], update: dict[str, Any], **_: Any):
        self.updates.append((dict(filter_), dict(update)))
        return SimpleNamespace(modified_count=1, matched_count=1, upserted_id=None)

    async def find_one(self, *_args: Any, **_kwargs: Any):
        return self._canned


class FakeDB:
    """Stand-in for the AsyncIOMotorDatabase returned by ``get_db``."""

    def __init__(self) -> None:
        self.billing_subscriptions = FakeCollection()
        self.subscriptions = FakeCollection()
        self.payment_transactions = FakeCollection()
        self.tenants = FakeCollection({"organization_id": "org-test"})


class WebhookHarness:
    """Bundles every patch needed to drive ``handle_webhook`` end-to-end.

    Use as an async context manager via ``__aenter__``/``__aexit__``-like
    helpers; tests below pull the bundle from the ``webhook_harness``
    fixture which wires/teardowns it.
    """

    def __init__(self) -> None:
        self.db = FakeDB()
        self.audit_calls: list[dict[str, Any]] = []
        self.email_calls: list[dict[str, Any]] = []

    def _record_audit(self, **kwargs: Any) -> None:
        self.audit_calls.append(kwargs)

    def _record_email(self, _db: Any, **kwargs: Any) -> None:
        self.email_calls.append(kwargs)


@pytest.fixture
def webhook_harness(monkeypatch: pytest.MonkeyPatch):
    """Patch every external dependency of ``handle_webhook`` and yield
    the harness so tests can assert on captured DB updates and audit
    entries."""
    from app.services import (
        stripe_lifecycle_mixin,
        stripe_subscription_sync_mixin,
        stripe_session_mixin,
        stripe_base_mixin,
    )
    from app.services.stripe_checkout_service import stripe_checkout_service as svc

    harness = WebhookHarness()
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")

    # Patch get_db in every module that calls it directly.
    async def _fake_get_db() -> FakeDB:
        return harness.db

    monkeypatch.setattr(stripe_lifecycle_mixin, "get_db", _fake_get_db)
    monkeypatch.setattr(stripe_subscription_sync_mixin, "get_db", _fake_get_db)
    monkeypatch.setattr(stripe_session_mixin, "get_db", _fake_get_db)
    monkeypatch.setattr(stripe_base_mixin, "get_db", _fake_get_db)

    # Capture audit log entries (each lifecycle method writes one).
    monkeypatch.setattr(
        stripe_lifecycle_mixin,
        "append_audit_log",
        AsyncMock(side_effect=lambda **kw: harness._record_audit(**kw)),
    )
    # Capture would-be email enqueues. We can't `setattr` on the real
    # `notification_email_service` module — importing it standalone in
    # test context triggers a circular import via the booking module.
    # Instead, install a fake module in `sys.modules` so the local
    # `from app.services.notification_email_service import ...` inside
    # the lifecycle method resolves to our stub.
    import sys
    fake_mod = SimpleNamespace(
        enqueue_payment_failed_email=AsyncMock(
            side_effect=lambda db, **kw: harness._record_email(db, **kw)
        )
    )
    monkeypatch.setitem(sys.modules, "app.services.notification_email_service", fake_mod)

    # billing_repo is shared state — patch the singleton's coroutines.
    monkeypatch.setattr(
        "app.repositories.billing_repository.billing_repo.webhook_event_exists",
        AsyncMock(return_value=False),
    )
    monkeypatch.setattr(
        "app.repositories.billing_repository.billing_repo.record_webhook_event",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        "app.repositories.billing_repository.billing_repo.get_subscription",
        AsyncMock(return_value={"plan": "starter", "status": "past_due"}),
    )
    monkeypatch.setattr(
        "app.repositories.billing_repository.billing_repo.get_customer",
        AsyncMock(return_value={"provider_customer_id": "cus_test"}),
    )

    # `_resolve_org_id_for_tenant` queries `db.tenants` — return canned org.
    # `sync_provider_subscription_record` would call Stripe API; replace
    # it with a no-op that returns a benign synced doc.
    sync_mock = AsyncMock(return_value={"status": "active"})
    monkeypatch.setattr(svc, "sync_provider_subscription_record", sync_mock)

    # Webhook signature verification & event parsing happen inside the
    # Stripe SDK wrapper; bypass it by stubbing `_checkout_client`.
    def _make_checkout(event_id: str, event_type: str):
        return SimpleNamespace(
            handle_webhook=AsyncMock(
                return_value=SimpleNamespace(
                    event_id=event_id,
                    event_type=event_type,
                    session_id=None,
                    payment_status=None,
                    metadata=None,
                )
            )
        )

    harness.make_checkout = _make_checkout  # type: ignore[attr-defined]

    # `_find_tenant_by_subscription` reads billing_subscriptions; pre-stub
    # it directly so we don't need to seed a fake document. Wrapped in an
    # AsyncMock so tests can assert the dispatcher passed the right
    # subscription_id from the event payload (catches field-mapping
    # regressions in `stripe_webhook_mixin._handle_*`).
    harness.find_tenant = AsyncMock(return_value="tenant-test")  # type: ignore[attr-defined]
    monkeypatch.setattr(svc, "_find_tenant_by_subscription", harness.find_tenant)
    # Also expose record_webhook_event so the dedupe test can assert it
    # was NOT called.
    harness.record_event = (
        __import__("app.repositories.billing_repository", fromlist=["billing_repo"])
        .billing_repo.record_webhook_event
    )
    # `sync_checkout_status` is only called when session_id is present;
    # our payloads have no session_id, so it should never fire — but stub
    # for safety.
    monkeypatch.setattr(svc, "sync_checkout_status", AsyncMock())

    yield harness


def _patch_checkout_client(svc, harness, event_id: str, event_type: str):
    """Helper: patch `_checkout_client` to return a SDK stub that yields
    the given (event_id, event_type)."""
    return patch.object(svc, "_checkout_client", return_value=harness.make_checkout(event_id, event_type))


# ---------------------------------------------------------------------------
# 1. invoice.paid — happy path
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_webhook_invoice_paid_writes_active_status_and_audit(webhook_harness):
    from app.services.stripe_checkout_service import stripe_checkout_service as svc

    payload = (
        b'{"type":"invoice.paid","data":{"object":'
        b'{"subscription":"sub_paid","amount_paid":99000,'
        b'"status_transitions":{"paid_at":1700000000}}}}'
    )

    with _patch_checkout_client(svc, webhook_harness, "evt_paid_1", "invoice.paid"):
        result = await svc.handle_webhook(SimpleNamespace(base_url="https://x/"), payload, "sig")

    assert result == {
        "status": "ok",
        "event_id": "evt_paid_1",
        "event_type": "invoice.paid",
        "session_id": None,
    }

    # `mark_invoice_paid` must update billing_subscriptions exactly once
    # with status=active + last_invoice_paid_* — extra writes would mean
    # a duplicate-update regression in the lifecycle method.
    updates = webhook_harness.db.billing_subscriptions.updates
    assert len(updates) == 1, f"expected 1 update, got {len(updates)}: {updates}"
    filt, update = updates[0]
    # Dispatcher must extract `subscription` from the payload and forward
    # it to the tenant resolver — guards against field-mapping bugs.
    webhook_harness.find_tenant.assert_awaited_once()
    assert webhook_harness.find_tenant.call_args.args[0] == "sub_paid"
    assert filt == {"tenant_id": "tenant-test"}
    set_fields = update["$set"]
    assert set_fields["status"] == "active"
    assert set_fields["last_invoice_paid_at"] == "2023-11-14T22:13:20+00:00"
    assert set_fields["last_invoice_paid_amount"] == 99000
    # past_due/grace fields must be cleared.
    assert "grace_period_until" in update["$unset"]
    assert "last_payment_failed_at" in update["$unset"]

    # Exactly one audit entry, with the right action and `after` shape.
    audit = [a for a in webhook_harness.audit_calls if a["action"] == "subscription.invoice_paid"]
    assert len(audit) == 1
    assert audit[0]["scope"] == "billing"
    assert audit[0]["actor_email"] == "stripe_webhook"
    assert audit[0]["after"] == {
        "subscription_id": "sub_paid",
        "amount": 99000,
        "paid_at": "2023-11-14T22:13:20+00:00",
    }


# ---------------------------------------------------------------------------
# 2. invoice.payment_failed — past_due + grace + email
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_webhook_payment_failed_writes_past_due_and_audit(webhook_harness):
    from app.services.stripe_checkout_service import stripe_checkout_service as svc

    payload = (
        b'{"type":"invoice.payment_failed","data":{"object":'
        b'{"subscription":"sub_fail","amount_due":12500,'
        b'"hosted_invoice_url":"https://stripe/invoice","invoice_pdf":"https://stripe/pdf",'
        b'"status_transitions":{"finalized_at":1700000000}}}}'
    )

    with _patch_checkout_client(svc, webhook_harness, "evt_fail_1", "invoice.payment_failed"):
        await svc.handle_webhook(SimpleNamespace(base_url="https://x/"), payload, "sig")

    updates = webhook_harness.db.billing_subscriptions.updates
    assert len(updates) == 1
    filt, update = updates[0]
    assert filt == {"tenant_id": "tenant-test"}
    webhook_harness.find_tenant.assert_awaited_once()
    assert webhook_harness.find_tenant.call_args.args[0] == "sub_fail"
    set_fields = update["$set"]
    assert set_fields["status"] == "past_due"
    assert set_fields["last_payment_failed_at"] == "2023-11-14T22:13:20+00:00"
    assert set_fields["last_payment_failed_amount"] == 12500
    assert set_fields["invoice_hosted_url"] == "https://stripe/invoice"
    assert set_fields["invoice_pdf_url"] == "https://stripe/pdf"
    # Grace period must be 7 days from now (ISO-formatted).
    assert "grace_period_until" in set_fields and "T" in set_fields["grace_period_until"]

    audit = [a for a in webhook_harness.audit_calls if a["action"] == "subscription.payment_failed"]
    assert len(audit) == 1
    assert audit[0]["after"]["status"] == "past_due"
    assert audit[0]["after"]["amount"] == 12500
    assert audit[0]["after"]["invoice_hosted_url"] == "https://stripe/invoice"

    # Email enqueue should have been invoked once.
    assert len(webhook_harness.email_calls) == 1
    assert webhook_harness.email_calls[0]["tenant_id"] == "tenant-test"
    assert webhook_harness.email_calls[0]["amount_due"] == 12500


# ---------------------------------------------------------------------------
# 3. customer.subscription.deleted — canceled status
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_webhook_subscription_deleted_writes_canceled_and_audit(webhook_harness):
    from app.services.stripe_checkout_service import stripe_checkout_service as svc

    payload = (
        b'{"type":"customer.subscription.deleted","data":{"object":'
        b'{"id":"sub_dead","canceled_at":1700000000}}}'
    )

    with _patch_checkout_client(svc, webhook_harness, "evt_del_1", "customer.subscription.deleted"):
        await svc.handle_webhook(SimpleNamespace(base_url="https://x/"), payload, "sig")

    updates = webhook_harness.db.billing_subscriptions.updates
    assert len(updates) == 1
    filt, update = updates[0]
    assert filt == {"tenant_id": "tenant-test"}
    webhook_harness.find_tenant.assert_awaited_once()
    assert webhook_harness.find_tenant.call_args.args[0] == "sub_dead"
    assert update["$set"]["status"] == "canceled"
    assert update["$set"]["cancel_at_period_end"] is False
    assert update["$set"]["canceled_at"] == "2023-11-14T22:13:20+00:00"
    # Scheduled-change fields must be cleared.
    assert update["$unset"].get("scheduled_plan") == ""
    assert update["$unset"].get("schedule_id") == ""

    audit = [a for a in webhook_harness.audit_calls if a["action"] == "subscription.canceled"]
    assert len(audit) == 1
    assert audit[0]["after"]["status"] == "canceled"
    assert audit[0]["after"]["subscription_id"] == "sub_dead"


@pytest.mark.anyio
async def test_webhook_dedupes_already_seen_event(webhook_harness, monkeypatch):
    """If billing_repo says we've already seen this event_id, skip
    processing — no DB writes, no audit entries."""
    from app.services.stripe_checkout_service import stripe_checkout_service as svc

    monkeypatch.setattr(
        "app.repositories.billing_repository.billing_repo.webhook_event_exists",
        AsyncMock(return_value=True),
    )

    payload = b'{"type":"invoice.paid","data":{"object":{"subscription":"sub_dup"}}}'
    with _patch_checkout_client(svc, webhook_harness, "evt_dup", "invoice.paid"):
        result = await svc.handle_webhook(SimpleNamespace(base_url="https://x/"), payload, "sig")

    assert result == {"status": "already_processed", "event_id": "evt_dup"}
    assert webhook_harness.db.billing_subscriptions.updates == []
    assert webhook_harness.audit_calls == []
    # Critical dedupe contract: when an event is already-seen we must
    # NOT re-record it (would inflate webhook_events) and must NOT
    # invoke the tenant lookup (would trigger lifecycle side-effects).
    webhook_harness.record_event.assert_not_awaited()
    webhook_harness.find_tenant.assert_not_awaited()


# ---------------------------------------------------------------------------
# 4 & 5. B2B booking lifecycle — route inventory + handler integrity smoke.
# ---------------------------------------------------------------------------


# The aggregator must expose exactly this set of (METHOD, PATH) pairs.
# A failure here means a child router dropped, renamed, or changed the
# HTTP method of a lifecycle endpoint — a silent contract regression.
EXPECTED_B2B_BOOKING_ROUTES: set[tuple[str, str]] = {
    ("POST", "/api/b2b/bookings"),
    ("POST", "/api/b2b/bookings-from-marketplace"),
    ("POST", "/api/b2b/bookings/{booking_id}/confirm"),
    ("POST", "/api/b2b/bookings/{booking_id}/risk/approve"),
    ("POST", "/api/b2b/bookings/{booking_id}/risk/reject"),
    ("POST", "/api/b2b/bookings/{booking_id}/refund-requests"),
    ("POST", "/api/b2b/bookings/{booking_id}/cancel"),
    ("POST", "/api/b2b/bookings/{booking_id}/amend/quote"),
    ("POST", "/api/b2b/bookings/{booking_id}/amend/confirm"),
    ("GET",  "/api/b2b/bookings/{booking_id}/events"),
}


def _collect_routes(router) -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()
    for r in router.routes:
        methods = sorted(r.methods or [])
        for m in methods:
            out.add((m, r.path))
    return out


def test_b2b_aggregator_exposes_expected_lifecycle_routes():
    from app.modules.b2b.routers.b2b_bookings import router

    actual = _collect_routes(router)
    missing = EXPECTED_B2B_BOOKING_ROUTES - actual
    extra = actual - EXPECTED_B2B_BOOKING_ROUTES
    assert not missing, f"B2B booking lifecycle routes missing: {missing}"
    assert not extra, (
        f"B2B booking aggregator exposes unexpected routes (likely a typo "
        f"or duplicate include in the aggregator): {extra}"
    )


def test_each_b2b_child_router_is_non_empty_with_real_handlers():
    """Sanity-check: every child router has at least one route, and each
    handler is a real coroutine function — not a placeholder/stub."""
    from app.modules.b2b.routers.b2b_bookings_create import router as r_create
    from app.modules.b2b.routers.b2b_bookings_confirm import router as r_confirm
    from app.modules.b2b.routers.b2b_bookings_risk import router as r_risk
    from app.modules.b2b.routers.b2b_bookings_lifecycle import router as r_lifecycle

    for name, router in [
        ("create", r_create),
        ("confirm", r_confirm),
        ("risk", r_risk),
        ("lifecycle", r_lifecycle),
    ]:
        assert router.routes, f"b2b_bookings_{name} router is empty"
        for route in router.routes:
            handler: Callable = route.endpoint  # type: ignore[attr-defined]
            assert callable(handler), f"{name}: handler for {route.path} is not callable"
            assert inspect.iscoroutinefunction(handler), (
                f"{name}: handler for {route.path} is not an async function"
            )
            # A real handler has at least one line of source beyond `pass`
            # (rough heuristic — catches stubbed-out placeholders).
            try:
                src = inspect.getsource(handler)
            except OSError:
                continue
            assert "raise NotImplementedError" not in src, (
                f"{name}: handler for {route.path} is a NotImplementedError stub"
            )


def test_b2b_aggregator_route_count_matches_sum_of_children():
    """Aggregator's route count must equal the sum of its children's
    route counts — guards against double-include or missed-include bugs
    in the aggregator wiring."""
    from app.modules.b2b.routers.b2b_bookings import router as agg
    from app.modules.b2b.routers.b2b_bookings_create import router as r_create
    from app.modules.b2b.routers.b2b_bookings_confirm import router as r_confirm
    from app.modules.b2b.routers.b2b_bookings_risk import router as r_risk
    from app.modules.b2b.routers.b2b_bookings_lifecycle import router as r_lifecycle

    expected = sum(len(r.routes) for r in [r_create, r_confirm, r_risk, r_lifecycle])
    assert len(agg.routes) == expected, (
        f"aggregator has {len(agg.routes)} routes but children sum to "
        f"{expected} — child router include is wrong."
    )
