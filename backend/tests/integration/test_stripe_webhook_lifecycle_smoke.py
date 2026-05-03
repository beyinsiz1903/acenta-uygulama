"""Smoke tests for Stripe webhook dispatch -> billing lifecycle (Task #6).

These tests post representative Stripe webhook payloads at the public
``/api/webhook/stripe`` endpoint and assert that:

- The dispatcher in ``StripeWebhookMixin.handle_webhook`` routes the event to
  the correct lifecycle method (``mark_invoice_paid`` /
  ``mark_payment_failed`` / ``mark_subscription_canceled``).
- The ``billing_subscriptions`` document for the tenant ends up in the
  expected state.
- An ``audit_logs`` entry with the expected ``action`` is written.

The Stripe SDK and emergent ``StripeCheckout`` adapter are mocked out so the
tests are deterministic and do not require network/Stripe-key access.
"""
from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest

from app.utils import now_utc


def _seed_subscription(test_db, *, tenant_id: str, org_id: str, sub_id: str) -> Any:
    return test_db.billing_subscriptions.insert_one(
        {
            "tenant_id": tenant_id,
            "provider": "stripe",
            "provider_subscription_id": sub_id,
            "plan": "pro",
            "interval": "monthly",
            "status": "active",
            "created_at": now_utc(),
            "updated_at": now_utc(),
        }
    )


async def _seed_org_tenant(test_db, *, slug: str) -> tuple[str, str]:
    """Create an isolated org+tenant pair for the smoke test."""

    now = now_utc()
    org_res = await test_db.organizations.insert_one(
        {"name": f"Org {slug}", "slug": slug, "created_at": now, "updated_at": now}
    )
    org_id = str(org_res.inserted_id)
    tenant_id = f"tenant_{slug}"
    await test_db.tenants.insert_one(
        {
            "_id": tenant_id,
            "organization_id": org_id,
            "name": f"Tenant {slug}",
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    return org_id, tenant_id


def _patch_webhook_pipeline(monkeypatch, *, event_id: str, event_type: str, raw_event: dict) -> None:
    """Replace the StripeCheckout adapter and provider sync with stubs.

    - ``_checkout_client`` returns an object whose ``handle_webhook`` returns a
      WebhookResponse-like namespace (no signature verification needed).
    - ``sync_provider_subscription_record`` becomes a no-op so we don't call
      the real Stripe API in the lifecycle methods.
    """

    from app.services.stripe_checkout_service import stripe_checkout_service

    fake_response = SimpleNamespace(
        event_id=event_id,
        event_type=event_type,
        session_id=None,
        payment_status=None,
        metadata={},
    )

    class _FakeCheckout:
        async def handle_webhook(self, payload, signature):  # noqa: D401
            return fake_response

    def _fake_checkout_client(self, http_request):  # noqa: ARG001
        return _FakeCheckout()

    async def _fake_sync(self, tenant_id, subscription_id, *args, **kwargs):  # noqa: ARG001
        return {"status": "active"}

    monkeypatch.setattr(
        type(stripe_checkout_service),
        "_checkout_client",
        _fake_checkout_client,
        raising=True,
    )
    monkeypatch.setattr(
        type(stripe_checkout_service),
        "sync_provider_subscription_record",
        _fake_sync,
        raising=True,
    )


@pytest.mark.anyio
async def test_invoice_paid_webhook_marks_subscription_active_and_audits(
    async_client, test_db, monkeypatch
):
    org_id, tenant_id = await _seed_org_tenant(test_db, slug="webhook_paid")
    sub_id = "sub_smoke_paid"
    await _seed_subscription(test_db, tenant_id=tenant_id, org_id=org_id, sub_id=sub_id)
    # Move into past_due so the lifecycle method must flip it back to active.
    await test_db.billing_subscriptions.update_one(
        {"tenant_id": tenant_id}, {"$set": {"status": "past_due"}}
    )

    raw_event = {
        "id": "evt_smoke_invoice_paid",
        "type": "invoice.paid",
        "data": {
            "object": {
                "subscription": sub_id,
                "amount_paid": 12900,
                "status_transitions": {"paid_at": 1_700_000_000},
            }
        },
    }
    _patch_webhook_pipeline(
        monkeypatch,
        event_id=raw_event["id"],
        event_type=raw_event["type"],
        raw_event=raw_event,
    )

    resp = await async_client.post(
        "/api/webhook/stripe",
        content=json.dumps(raw_event).encode("utf-8"),
        headers={"Stripe-Signature": "t=0,v1=stub"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    payload = body.get("data", body) if isinstance(body, dict) and "ok" in body else body
    assert payload.get("event_id") == raw_event["id"]
    assert payload.get("event_type") == raw_event["type"]

    sub_doc = await test_db.billing_subscriptions.find_one({"tenant_id": tenant_id})
    assert sub_doc is not None
    assert sub_doc["status"] == "active"
    assert sub_doc["last_invoice_paid_amount"] == 12900
    assert sub_doc.get("last_invoice_paid_at")
    # past-due cleanup must clear the failure markers
    assert "grace_period_until" not in sub_doc
    assert "last_payment_failed_at" not in sub_doc

    audit = await test_db.audit_logs.find_one(
        {"tenant_id": tenant_id, "action": "subscription.invoice_paid"}
    )
    assert audit is not None
    assert (audit.get("after") or {}).get("subscription_id") == sub_id
    assert (audit.get("after") or {}).get("amount") == 12900

    # Webhook event recorded for idempotency
    evt = await test_db.billing_webhook_events.find_one({"provider_event_id": raw_event["id"]})
    assert evt is not None


@pytest.mark.anyio
async def test_invoice_payment_failed_webhook_sets_past_due_and_audits(
    async_client, test_db, monkeypatch
):
    org_id, tenant_id = await _seed_org_tenant(test_db, slug="webhook_failed")
    sub_id = "sub_smoke_failed"
    await _seed_subscription(test_db, tenant_id=tenant_id, org_id=org_id, sub_id=sub_id)

    raw_event = {
        "id": "evt_smoke_invoice_failed",
        "type": "invoice.payment_failed",
        "data": {
            "object": {
                "subscription": sub_id,
                "amount_due": 24900,
                "hosted_invoice_url": "https://billing.example.test/invoice/hosted",
                "invoice_pdf": "https://billing.example.test/invoice.pdf",
                "status_transitions": {"finalized_at": 1_700_000_500},
            }
        },
    }
    _patch_webhook_pipeline(
        monkeypatch,
        event_id=raw_event["id"],
        event_type=raw_event["type"],
        raw_event=raw_event,
    )

    resp = await async_client.post(
        "/api/webhook/stripe",
        content=json.dumps(raw_event).encode("utf-8"),
        headers={"Stripe-Signature": "t=0,v1=stub"},
    )
    assert resp.status_code == 200, resp.text

    sub_doc = await test_db.billing_subscriptions.find_one({"tenant_id": tenant_id})
    assert sub_doc is not None
    assert sub_doc["status"] == "past_due"
    assert sub_doc["last_payment_failed_amount"] == 24900
    assert sub_doc.get("grace_period_until")
    assert sub_doc.get("invoice_hosted_url") == "https://billing.example.test/invoice/hosted"
    assert sub_doc.get("invoice_pdf_url") == "https://billing.example.test/invoice.pdf"

    audit = await test_db.audit_logs.find_one(
        {"tenant_id": tenant_id, "action": "subscription.payment_failed"}
    )
    assert audit is not None
    after = audit.get("after") or {}
    assert after.get("status") == "past_due"
    assert after.get("amount") == 24900
    assert after.get("invoice_hosted_url") == "https://billing.example.test/invoice/hosted"


@pytest.mark.anyio
async def test_subscription_deleted_webhook_marks_canceled_and_audits(
    async_client, test_db, monkeypatch
):
    org_id, tenant_id = await _seed_org_tenant(test_db, slug="webhook_canceled")
    sub_id = "sub_smoke_cancel"
    await _seed_subscription(test_db, tenant_id=tenant_id, org_id=org_id, sub_id=sub_id)

    raw_event = {
        "id": "evt_smoke_sub_deleted",
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": sub_id,
                "canceled_at": 1_700_001_000,
            }
        },
    }
    _patch_webhook_pipeline(
        monkeypatch,
        event_id=raw_event["id"],
        event_type=raw_event["type"],
        raw_event=raw_event,
    )

    resp = await async_client.post(
        "/api/webhook/stripe",
        content=json.dumps(raw_event).encode("utf-8"),
        headers={"Stripe-Signature": "t=0,v1=stub"},
    )
    assert resp.status_code == 200, resp.text

    sub_doc = await test_db.billing_subscriptions.find_one({"tenant_id": tenant_id})
    assert sub_doc is not None
    assert sub_doc["status"] == "canceled"
    assert sub_doc.get("cancel_at_period_end") is False
    assert sub_doc.get("canceled_at")

    audit = await test_db.audit_logs.find_one(
        {"tenant_id": tenant_id, "action": "subscription.canceled"}
    )
    assert audit is not None
    assert (audit.get("after") or {}).get("subscription_id") == sub_id
    assert (audit.get("after") or {}).get("status") == "canceled"


@pytest.mark.anyio
async def test_duplicate_webhook_event_is_idempotent(
    async_client, test_db, monkeypatch
):
    """Re-posting the same event_id must short-circuit on the dedup check."""

    org_id, tenant_id = await _seed_org_tenant(test_db, slug="webhook_dupe")
    sub_id = "sub_smoke_dupe"
    await _seed_subscription(test_db, tenant_id=tenant_id, org_id=org_id, sub_id=sub_id)

    raw_event = {
        "id": "evt_smoke_dupe",
        "type": "invoice.paid",
        "data": {
            "object": {
                "subscription": sub_id,
                "amount_paid": 9900,
                "status_transitions": {"paid_at": 1_700_002_000},
            }
        },
    }
    _patch_webhook_pipeline(
        monkeypatch,
        event_id=raw_event["id"],
        event_type=raw_event["type"],
        raw_event=raw_event,
    )

    first = await async_client.post(
        "/api/webhook/stripe",
        content=json.dumps(raw_event).encode("utf-8"),
        headers={"Stripe-Signature": "t=0,v1=stub"},
    )
    assert first.status_code == 200, first.text

    second = await async_client.post(
        "/api/webhook/stripe",
        content=json.dumps(raw_event).encode("utf-8"),
        headers={"Stripe-Signature": "t=0,v1=stub"},
    )
    assert second.status_code == 200, second.text
    body = second.json()
    payload = body.get("data", body) if isinstance(body, dict) and "ok" in body else body
    assert payload.get("status") == "already_processed"

    audits = await test_db.audit_logs.count_documents(
        {"tenant_id": tenant_id, "action": "subscription.invoice_paid"}
    )
    assert audits == 1, "duplicate webhook delivery must not double-write audit log"
