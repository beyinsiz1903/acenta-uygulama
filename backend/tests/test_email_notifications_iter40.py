from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.constants.usage_metrics import UsageMetric
from app.services.email_outbox import dispatch_pending_emails, enqueue_generic_email
from app.services.stripe_checkout_service import stripe_checkout_service
from app.services.usage_service import track_usage_event


@pytest.mark.anyio
async def test_track_usage_event_enqueues_quota_warning_email(test_db, monkeypatch):
    org = await test_db.organizations.find_one({"slug": "default"}, {"_id": 1})
    assert org is not None
    org_id = str(org.get("_id"))
    tenant_id = "tenant_default"

    await test_db.users.insert_one(
        {
            "organization_id": org_id,
            "tenant_id": tenant_id,
            "email": "quota-owner@acenta.test",
            "name": "Quota Owner",
            "roles": ["agency_admin"],
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
    )
    await test_db.usage_daily.insert_one(
        {
            "tenant_id": tenant_id,
            "organization_id": org_id,
            "metric": UsageMetric.REPORT_GENERATED,
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "count": 6,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
    )

    async def _fake_entitlements(_tenant_id: str, refresh: bool = False):
        return {
            "plan": "starter",
            "plan_label": "Starter",
            "usage_allowances": {UsageMetric.REPORT_GENERATED: 10},
        }

    monkeypatch.setattr(
        "app.services.usage_service.entitlement_service.get_tenant_entitlements",
        _fake_entitlements,
    )

    inserted = await track_usage_event(
        tenant_id=tenant_id,
        organization_id=org_id,
        metric=UsageMetric.REPORT_GENERATED,
        quantity=1,
        source="reports.generate",
        source_event_id="iter40-report-threshold",
        metadata={"report_type": "operations_overview"},
    )

    assert inserted is True
    outbox_job = await test_db.email_outbox.find_one(
        {"tenant_id": tenant_id, "event_type": "usage.quota_warning"},
        {"_id": 0, "subject": 1, "to": 1, "metadata": 1},
    )
    assert outbox_job is not None
    assert "quota-owner@acenta.test" in outbox_job["to"]
    assert "Kota Uyarısı" in outbox_job["subject"]
    assert outbox_job["metadata"]["warning_level"] == "warning"


@pytest.mark.anyio
async def test_mark_payment_failed_enqueues_email_outbox(test_db, monkeypatch):
    org = await test_db.organizations.find_one({"slug": "default"}, {"_id": 1})
    assert org is not None
    org_id = str(org.get("_id"))
    tenant_id = "tenant_default"
    now = datetime.now(timezone.utc)

    await test_db.users.insert_one(
        {
            "organization_id": org_id,
            "tenant_id": tenant_id,
            "email": "billing-owner@acenta.test",
            "name": "Billing Owner",
            "roles": ["agency_admin"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    await test_db.billing_subscriptions.insert_one(
        {
            "tenant_id": tenant_id,
            "provider": "stripe",
            "provider_subscription_id": "sub_iter40",
            "plan": "pro",
            "interval": "monthly",
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
    )
    await test_db.subscriptions.insert_one(
        {
            "org_id": org_id,
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
    )

    async def _fake_sync(_tenant_id: str, _subscription_id: str):
        return {"status": "past_due"}

    monkeypatch.setattr(stripe_checkout_service, "sync_provider_subscription_record", _fake_sync)

    result = await stripe_checkout_service.mark_payment_failed(
        tenant_id,
        subscription_id="sub_iter40",
        amount_due=249000,
        invoice_hosted_url="https://billing.example.test/invoice/hosted",
        invoice_pdf_url="https://billing.example.test/invoice.pdf",
        failed_at="2026-03-09T10:00:00+00:00",
    )

    assert result["status"] == "past_due"
    outbox_job = await test_db.email_outbox.find_one(
        {"tenant_id": tenant_id, "event_type": "billing.payment_failed"},
        {"_id": 0, "subject": 1, "to": 1, "metadata": 1},
    )
    assert outbox_job is not None
    assert "billing-owner@acenta.test" in outbox_job["to"]
    assert "Ödeme Başarısız" in outbox_job["subject"]
    assert outbox_job["metadata"]["invoice_hosted_url"] == "https://billing.example.test/invoice/hosted"


@pytest.mark.anyio
async def test_dispatch_pending_emails_marks_job_skipped_when_provider_missing(test_db, monkeypatch):
    async_job_id = await enqueue_generic_email(
        test_db,
        organization_id="org_demo",
        tenant_id="tenant_demo",
        to_addresses=["ops@acenta.test"],
        subject="Test email",
        html_body="<p>Merhaba</p>",
        text_body="Merhaba",
        event_type="generic",
        dedupe_key="iter40-email-skip",
    )
    assert async_job_id is not None

    monkeypatch.setattr(
        "app.services.email_outbox.send_email_ses",
        lambda **_: {"ok": False, "skipped": True, "reason": "ses_not_configured"},
    )

    processed = await dispatch_pending_emails(test_db, limit=10)
    assert processed == 1

    job = await test_db.email_outbox.find_one({"dedupe_key": "iter40-email-skip"}, {"_id": 0, "status": 1, "last_error": 1})
    assert job is not None
    assert job["status"] == "skipped"
    assert job["last_error"] == "ses_not_configured"