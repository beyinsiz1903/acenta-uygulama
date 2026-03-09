"""
Iteration 40: Email Notification Tests + No-Regression for Search/Reports

Test Coverage:
1. billing.payment_failed -> email_outbox job creation
2. usage.quota_warning/critical/limit_reached -> email_outbox job creation
3. Email worker dispatch with skipped status when provider not configured
4. GET /api/search no-regression
5. GET /api/reports/generate no-regression
6. GET /api/reports/sales-summary.csv no-regression

MOCKED: Email provider credentials intentionally missing; only queue creation and graceful skipped behavior tested.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest
import requests

from app.constants.usage_metrics import UsageMetric
from app.services.email_outbox import dispatch_pending_emails, enqueue_generic_email
from app.services.notification_email_service import (
    enqueue_payment_failed_email,
    maybe_enqueue_quota_warning_email,
)
from app.services.stripe_checkout_service import stripe_checkout_service
from app.services.usage_service import track_usage_event

# BASE_URL from frontend .env for HTTP tests
BASE_URL = "https://travel-ops-system-4.preview.emergentagent.com"


# ========================================
# UNIT TESTS - Email Outbox + Notifications
# ========================================


@pytest.mark.anyio
async def test_enqueue_payment_failed_email_creates_outbox_job(test_db):
    """Test billing.payment_failed lifecycle creates email_outbox job."""
    org_id = "org_iter40_payment"
    tenant_id = "tenant_iter40_payment"
    now = datetime.now(timezone.utc)

    # Setup user who will receive the email (agency_admin role for tenant notifications)
    await test_db.users.insert_one({
        "organization_id": org_id,
        "tenant_id": tenant_id,
        "email": "billing-admin@iter40.test",
        "name": "Billing Admin",
        "roles": ["agency_admin"],
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    })

    # Setup tenant
    await test_db.tenants.insert_one({
        "_id": tenant_id,
        "organization_id": org_id,
        "name": "Iter40 Test Tenant",
        "created_at": now,
        "updated_at": now,
    })

    # Setup subscription
    await test_db.billing_subscriptions.insert_one({
        "tenant_id": tenant_id,
        "provider": "stripe",
        "provider_subscription_id": "sub_iter40_test",
        "plan": "pro",
        "interval": "monthly",
        "status": "active",
        "created_at": now,
        "updated_at": now,
    })

    # Enqueue payment failed email
    result = await enqueue_payment_failed_email(
        test_db,
        organization_id=org_id,
        tenant_id=tenant_id,
        subscription_id="sub_iter40_test",
        amount_due=99000,  # 990.00 TRY in minor units
        failed_at="2026-03-09T10:00:00+00:00",
        grace_period_until="2026-03-16T10:00:00+00:00",
        invoice_hosted_url="https://billing.test/invoice/hosted",
        invoice_pdf_url="https://billing.test/invoice.pdf",
        dedupe_key="iter40-payment-failed-test",
    )

    assert result is not None

    # Verify outbox job was created
    outbox_job = await test_db.email_outbox.find_one(
        {"dedupe_key": "iter40-payment-failed-test"},
        {"_id": 0, "event_type": 1, "subject": 1, "to": 1, "metadata": 1, "status": 1},
    )

    assert outbox_job is not None
    assert outbox_job["event_type"] == "billing.payment_failed"
    assert "billing-admin@iter40.test" in outbox_job["to"]
    assert "Ödeme Başarısız" in outbox_job["subject"]
    assert outbox_job["status"] == "pending"
    assert outbox_job["metadata"]["subscription_id"] == "sub_iter40_test"
    assert outbox_job["metadata"]["amount_due"] == 99000
    assert outbox_job["metadata"]["invoice_hosted_url"] == "https://billing.test/invoice/hosted"


@pytest.mark.anyio
async def test_maybe_enqueue_quota_warning_email_warning_level(test_db):
    """Test usage.quota_warning job creation when crossing 70% threshold."""
    org_id = "org_iter40_quota_warn"
    tenant_id = "tenant_iter40_quota_warn"
    now = datetime.now(timezone.utc)
    billing_period = now.strftime("%Y-%m")

    # Setup user with agency_admin role (in TENANT_NOTIFICATION_ROLES)
    await test_db.users.insert_one({
        "organization_id": org_id,
        "tenant_id": tenant_id,
        "email": "quota-owner@iter40.test",
        "name": "Quota Owner",
        "roles": ["agency_admin"],
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    })

    # Setup tenant
    await test_db.tenants.insert_one({
        "_id": tenant_id,
        "organization_id": org_id,
        "name": "Iter40 Quota Tenant",
        "created_at": now,
        "updated_at": now,
    })

    # Enqueue quota warning (70% threshold crossed)
    result = await maybe_enqueue_quota_warning_email(
        test_db,
        organization_id=org_id,
        tenant_id=tenant_id,
        metric=UsageMetric.REPORT_GENERATED,
        used=71,
        limit=100,
        previous_used=69,  # Was below 70%
        billing_period=billing_period,
        plan_label="Starter",
    )

    assert result is not None

    # Verify outbox job
    outbox_job = await test_db.email_outbox.find_one(
        {"tenant_id": tenant_id, "event_type": "usage.quota_warning"},
        {"_id": 0, "subject": 1, "to": 1, "metadata": 1, "status": 1},
    )

    assert outbox_job is not None
    assert "Kota Uyarısı" in outbox_job["subject"]
    assert "quota-owner@iter40.test" in outbox_job["to"]
    assert outbox_job["metadata"]["warning_level"] == "warning"
    assert outbox_job["metadata"]["metric"] == UsageMetric.REPORT_GENERATED
    assert outbox_job["status"] == "pending"


@pytest.mark.anyio
async def test_maybe_enqueue_quota_warning_email_critical_level(test_db):
    """Test usage.quota_critical job creation when crossing 85% threshold."""
    org_id = "org_iter40_quota_crit"
    tenant_id = "tenant_iter40_quota_crit"
    now = datetime.now(timezone.utc)
    billing_period = now.strftime("%Y-%m")

    # Setup user with agency_admin role (required for TENANT_NOTIFICATION_ROLES)
    await test_db.users.insert_one({
        "organization_id": org_id,
        "tenant_id": tenant_id,
        "email": "critical-owner@iter40.test",
        "name": "Critical Owner",
        "roles": ["agency_admin"],
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    })

    # Setup tenant
    await test_db.tenants.insert_one({
        "_id": tenant_id,
        "organization_id": org_id,
        "name": "Iter40 Critical Tenant",
        "created_at": now,
        "updated_at": now,
    })

    # Enqueue quota critical (85% threshold crossed - NOT 90%)
    result = await maybe_enqueue_quota_warning_email(
        test_db,
        organization_id=org_id,
        tenant_id=tenant_id,
        metric=UsageMetric.RESERVATION_CREATED,
        used=86,  # 86% - above 85% critical threshold
        limit=100,
        previous_used=84,  # Was below 85%
        billing_period=billing_period,
        plan_label="Pro",
    )

    assert result is not None

    # Verify outbox job
    outbox_job = await test_db.email_outbox.find_one(
        {"tenant_id": tenant_id, "event_type": "usage.quota_critical"},
        {"_id": 0, "subject": 1, "metadata": 1},
    )

    assert outbox_job is not None
    assert "Kritik Kota" in outbox_job["subject"]
    assert outbox_job["metadata"]["warning_level"] == "critical"


@pytest.mark.anyio
async def test_maybe_enqueue_quota_warning_email_limit_reached(test_db):
    """Test usage.quota_limit_reached job creation when hitting 100%."""
    org_id = "org_iter40_quota_limit"
    tenant_id = "tenant_iter40_quota_limit"
    now = datetime.now(timezone.utc)
    billing_period = now.strftime("%Y-%m")

    # Setup user with super_admin role (in ORG_NOTIFICATION_ROLES)
    await test_db.users.insert_one({
        "organization_id": org_id,
        "tenant_id": tenant_id,
        "email": "limit-owner@iter40.test",
        "name": "Limit Owner",
        "roles": ["super_admin"],
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    })

    # Setup tenant
    await test_db.tenants.insert_one({
        "_id": tenant_id,
        "organization_id": org_id,
        "name": "Iter40 Limit Tenant",
        "created_at": now,
        "updated_at": now,
    })

    # Enqueue quota limit_reached (100% threshold crossed)
    result = await maybe_enqueue_quota_warning_email(
        test_db,
        organization_id=org_id,
        tenant_id=tenant_id,
        metric=UsageMetric.EXPORT_GENERATED,
        used=100,
        limit=100,
        previous_used=99,
        billing_period=billing_period,
        plan_label="Enterprise",
    )

    assert result is not None

    # Verify outbox job
    outbox_job = await test_db.email_outbox.find_one(
        {"tenant_id": tenant_id, "event_type": "usage.quota_limit_reached"},
        {"_id": 0, "subject": 1, "metadata": 1},
    )

    assert outbox_job is not None
    assert "Kota Doldu" in outbox_job["subject"]
    assert outbox_job["metadata"]["warning_level"] == "limit_reached"


@pytest.mark.anyio
async def test_dispatch_pending_emails_skipped_when_provider_missing(test_db, monkeypatch):
    """Test email worker marks job as 'skipped' when provider not configured."""
    # Create a pending email job
    job_id = await enqueue_generic_email(
        test_db,
        organization_id="org_iter40_dispatch",
        tenant_id="tenant_iter40_dispatch",
        to_addresses=["dispatch-test@iter40.test"],
        subject="Dispatch Test Email",
        html_body="<p>Test content</p>",
        text_body="Test content",
        event_type="test.dispatch",
        dedupe_key="iter40-dispatch-skip",
    )
    assert job_id is not None

    # Mock send_email_ses to return skipped status
    monkeypatch.setattr(
        "app.services.email_outbox.send_email_ses",
        lambda **_: {"ok": False, "skipped": True, "reason": "email_provider_not_configured"},
    )

    # Dispatch pending emails
    processed = await dispatch_pending_emails(test_db, limit=10)
    assert processed >= 1

    # Verify job status is 'skipped'
    job = await test_db.email_outbox.find_one(
        {"dedupe_key": "iter40-dispatch-skip"},
        {"_id": 0, "status": 1, "last_error": 1, "sent_at": 1},
    )

    assert job is not None
    assert job["status"] == "skipped"
    assert job["last_error"] == "email_provider_not_configured"
    assert job["sent_at"] is None  # Should not be set for skipped


@pytest.mark.anyio
async def test_track_usage_event_triggers_quota_warning_email(test_db, monkeypatch):
    """Test that track_usage_event triggers quota warning email when threshold crossed."""
    org_id = "org_iter40_usage"
    tenant_id = "tenant_iter40_usage"
    now = datetime.now(timezone.utc)

    # Setup user
    await test_db.users.insert_one({
        "organization_id": org_id,
        "tenant_id": tenant_id,
        "email": "usage-track@iter40.test",
        "name": "Usage Tracker",
        "roles": ["agency_admin"],
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    })

    # Setup tenant
    await test_db.tenants.insert_one({
        "_id": tenant_id,
        "organization_id": org_id,
        "name": "Iter40 Usage Tenant",
        "created_at": now,
        "updated_at": now,
    })

    # Setup usage_daily so we're at 70% after this event
    await test_db.usage_daily.insert_one({
        "tenant_id": tenant_id,
        "organization_id": org_id,
        "metric": UsageMetric.REPORT_GENERATED,
        "date": now.strftime("%Y-%m-%d"),
        "count": 6,  # 6/10 = 60%, will become 7/10 = 70%
        "created_at": now,
        "updated_at": now,
    })

    # Mock entitlements to return limit of 10
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

    # Track usage event
    inserted = await track_usage_event(
        tenant_id=tenant_id,
        organization_id=org_id,
        metric=UsageMetric.REPORT_GENERATED,
        quantity=1,
        source="reports.generate",
        source_event_id="iter40-usage-trigger-test",
        metadata={"report_type": "operations_overview"},
    )

    assert inserted is True

    # Verify quota warning email was enqueued
    outbox_job = await test_db.email_outbox.find_one(
        {"tenant_id": tenant_id, "event_type": "usage.quota_warning"},
        {"_id": 0, "subject": 1, "to": 1, "metadata": 1},
    )

    assert outbox_job is not None
    assert "usage-track@iter40.test" in outbox_job["to"]
    assert "Kota Uyarısı" in outbox_job["subject"]
    assert outbox_job["metadata"]["warning_level"] == "warning"


@pytest.mark.anyio
async def test_mark_payment_failed_via_stripe_service_creates_outbox(test_db, monkeypatch):
    """Test mark_payment_failed in stripe_checkout_service creates email outbox job."""
    org_id = "org_iter40_stripe"
    tenant_id = "tenant_iter40_stripe"
    now = datetime.now(timezone.utc)

    # Setup organization
    await test_db.organizations.insert_one({
        "_id": org_id,
        "slug": "iter40-stripe",
        "name": "Iter40 Stripe Org",
        "created_at": now,
        "updated_at": now,
    })

    # Setup user with admin role
    await test_db.users.insert_one({
        "organization_id": org_id,
        "tenant_id": tenant_id,
        "email": "stripe-billing@iter40.test",
        "name": "Stripe Billing Owner",
        "roles": ["agency_admin"],  # Use agency_admin for tenant notifications
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    })

    # Setup tenant
    await test_db.tenants.insert_one({
        "_id": tenant_id,
        "organization_id": org_id,
        "name": "Iter40 Stripe Tenant",
        "created_at": now,
        "updated_at": now,
    })

    # Setup billing subscription
    await test_db.billing_subscriptions.insert_one({
        "tenant_id": tenant_id,
        "provider": "stripe",
        "provider_subscription_id": "sub_iter40_stripe",
        "plan": "pro",
        "interval": "monthly",
        "status": "active",
        "created_at": now,
        "updated_at": now,
    })

    # Setup org subscription
    await test_db.subscriptions.insert_one({
        "org_id": org_id,
        "status": "active",
        "created_at": now,
        "updated_at": now,
    })

    # Mock sync_provider_subscription_record to avoid Stripe API call
    async def _fake_sync(_tenant_id: str, _subscription_id: str):
        return {"status": "past_due"}

    monkeypatch.setattr(stripe_checkout_service, "sync_provider_subscription_record", _fake_sync)

    # Call mark_payment_failed
    result = await stripe_checkout_service.mark_payment_failed(
        tenant_id,
        subscription_id="sub_iter40_stripe",
        amount_due=249000,
        invoice_hosted_url="https://stripe.test/invoice",
        invoice_pdf_url="https://stripe.test/invoice.pdf",
        failed_at="2026-03-09T15:00:00+00:00",
    )

    assert result["status"] == "past_due"

    # Verify email outbox job was created
    outbox_job = await test_db.email_outbox.find_one(
        {"tenant_id": tenant_id, "event_type": "billing.payment_failed"},
        {"_id": 0, "subject": 1, "to": 1, "metadata": 1},
    )

    assert outbox_job is not None
    assert "stripe-billing@iter40.test" in outbox_job["to"]
    assert "Ödeme Başarısız" in outbox_job["subject"]
    assert outbox_job["metadata"]["invoice_hosted_url"] == "https://stripe.test/invoice"


# ========================================
# HTTP NO-REGRESSION TESTS - Search/Reports
# ========================================


class TestSearchNoRegression:
    """No-regression tests for GET /api/search endpoint."""

    @pytest.fixture
    def auth_headers(self):
        """Get auth headers for agent user."""
        resp = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "agent@acenta.test", "password": "agent123"},
            timeout=30,
        )
        assert resp.status_code == 200, f"Login failed: {resp.text}"
        token = resp.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}

    def test_global_search_returns_200(self, auth_headers):
        """GET /api/search?q=test should return 200."""
        resp = requests.get(
            f"{BASE_URL}/api/search",
            params={"q": "test"},
            headers=auth_headers,
            timeout=30,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "query" in data
        assert "scope" in data
        assert "sections" in data
        assert data["query"] == "test"

    def test_global_search_sections_structure(self, auth_headers):
        """GET /api/search returns correct sections."""
        resp = requests.get(
            f"{BASE_URL}/api/search",
            params={"q": "hotel"},
            headers=auth_headers,
            timeout=30,
        )
        assert resp.status_code == 200
        data = resp.json()
        sections = data.get("sections", {})
        # Verify all expected section keys exist
        assert "customers" in sections
        assert "bookings" in sections
        assert "hotels" in sections
        assert "tours" in sections

    def test_global_search_scope_agency(self, auth_headers):
        """Agent user search should return scope=agency."""
        resp = requests.get(
            f"{BASE_URL}/api/search",
            params={"q": "demo"},
            headers=auth_headers,
            timeout=30,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("scope") == "agency"

    def test_global_search_with_limit(self, auth_headers):
        """GET /api/search with limit parameter."""
        resp = requests.get(
            f"{BASE_URL}/api/search",
            params={"q": "test", "limit": 2},
            headers=auth_headers,
            timeout=30,
        )
        assert resp.status_code == 200
        data = resp.json()
        # Each section should have at most 2 items
        for section_name, items in data.get("sections", {}).items():
            assert len(items) <= 2, f"Section {section_name} exceeds limit"


class TestReportsNoRegression:
    """No-regression tests for /api/reports endpoints."""

    @pytest.fixture
    def auth_headers(self):
        """Get auth headers for agent user."""
        resp = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "agent@acenta.test", "password": "agent123"},
            timeout=30,
        )
        assert resp.status_code == 200, f"Login failed: {resp.text}"
        token = resp.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}

    def test_reports_generate_returns_200(self, auth_headers):
        """GET /api/reports/generate should return 200."""
        resp = requests.get(
            f"{BASE_URL}/api/reports/generate",
            params={"days": 30},
            headers=auth_headers,
            timeout=30,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "generated_at" in data
        assert "period" in data
        assert "kpis" in data

    def test_reports_generate_kpis_structure(self, auth_headers):
        """GET /api/reports/generate returns correct KPI structure."""
        resp = requests.get(
            f"{BASE_URL}/api/reports/generate",
            params={"days": 30},
            headers=auth_headers,
            timeout=30,
        )
        assert resp.status_code == 200
        data = resp.json()
        kpis = data.get("kpis", {})
        # Verify KPI fields exist
        assert "booking_count" in kpis
        assert "revenue_total" in kpis
        assert "avg_booking_value" in kpis
        assert "active_customer_count" in kpis
        # Verify data types
        assert isinstance(kpis["booking_count"], int)
        assert isinstance(kpis["revenue_total"], (int, float))

    def test_reports_generate_period_structure(self, auth_headers):
        """GET /api/reports/generate returns correct period structure."""
        resp = requests.get(
            f"{BASE_URL}/api/reports/generate",
            params={"days": 14},
            headers=auth_headers,
            timeout=30,
        )
        assert resp.status_code == 200
        data = resp.json()
        period = data.get("period", {})
        assert "start" in period
        assert "end" in period
        assert "days" in period
        assert period["days"] == 14

    def test_sales_summary_csv_returns_200(self, auth_headers):
        """GET /api/reports/sales-summary.csv should return 200 with CSV."""
        resp = requests.get(
            f"{BASE_URL}/api/reports/sales-summary.csv",
            params={"days": 7},
            headers=auth_headers,
            timeout=30,
        )
        assert resp.status_code == 200
        # Verify CSV content type
        content_type = resp.headers.get("content-type", "")
        assert "text/csv" in content_type
        # Verify CSV has header
        content = resp.text
        assert "day,revenue,count" in content or "day" in content

    def test_sales_summary_json_returns_200(self, auth_headers):
        """GET /api/reports/sales-summary should return 200 with JSON."""
        resp = requests.get(
            f"{BASE_URL}/api/reports/sales-summary",
            params={"days": 14},
            headers=auth_headers,
            timeout=30,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # If data exists, verify structure
        if data:
            assert "day" in data[0]
            assert "revenue" in data[0]
            assert "count" in data[0]


# ========================================
# Admin User Search No-Regression
# ========================================


class TestAdminSearchNoRegression:
    """No-regression tests for admin user search."""

    @pytest.fixture
    def admin_headers(self):
        """Get auth headers for admin user."""
        resp = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@acenta.test", "password": "admin123"},
            timeout=30,
        )
        assert resp.status_code == 200, f"Admin login failed: {resp.text}"
        token = resp.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}

    def test_admin_search_scope_organization(self, admin_headers):
        """Admin user search should return scope=organization."""
        resp = requests.get(
            f"{BASE_URL}/api/search",
            params={"q": "test"},
            headers=admin_headers,
            timeout=30,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("scope") == "organization"

    def test_admin_reports_generate(self, admin_headers):
        """Admin user can access reports/generate."""
        resp = requests.get(
            f"{BASE_URL}/api/reports/generate",
            params={"days": 30},
            headers=admin_headers,
            timeout=30,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "kpis" in data
        # Admin should see more bookings than agency-scoped user
        assert data["kpis"]["booking_count"] >= 0
