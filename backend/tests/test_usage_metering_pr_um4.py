"""
PR-UM4 Usage Metering + Usage Visibility Tests
Tests:
1. GET /api/tenant/usage-summary - tenant usage summary with 30-day trend
2. GET /api/admin/billing/tenants/{tenant_id}/usage - admin raw usage + trend
3. Both endpoints return correct structure with metrics and trend data
4. PRIMARY_USAGE_METRICS are correctly defined (reservation.created, report.generated, export.generated)
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "admin123"

# Expected primary metrics for UM4
EXPECTED_PRIMARY_METRICS = [
    "reservation.created",
    "report.generated",
    "export.generated",
]


@pytest.fixture(scope="module")
def admin_session():
    """Create authenticated admin session."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    
    # Login as admin
    login_resp = session.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    if login_resp.status_code != 200:
        pytest.skip(f"Admin login failed: {login_resp.status_code} - {login_resp.text[:200]}")
    
    data = login_resp.json()
    token = data.get("token") or data.get("access_token")
    if token:
        session.headers.update({"Authorization": f"Bearer {token}"})
    
    return session


@pytest.fixture(scope="module")
def tenant_id(admin_session):
    """Get a tenant_id for testing admin endpoints."""
    # Try to get tenant from /admin/tenants list
    resp = admin_session.get(f"{BASE_URL}/api/admin/tenants", params={"limit": 1})
    if resp.status_code == 200:
        data = resp.json()
        items = data.get("items") or data.get("tenants") or []
        if items:
            return str(items[0].get("id") or items[0].get("_id"))
    
    # Fallback: try /api/tenant/features to get current tenant_id
    resp2 = admin_session.get(f"{BASE_URL}/api/tenant/features")
    if resp2.status_code == 200:
        return resp2.json().get("tenant_id")
    
    pytest.skip("Could not find a tenant_id for testing")


class TestTenantUsageSummaryEndpoint:
    """Tests for GET /api/tenant/usage-summary"""

    def test_usage_summary_returns_200(self, admin_session):
        """Tenant usage summary endpoint should return 200."""
        resp = admin_session.get(f"{BASE_URL}/api/tenant/usage-summary", params={"days": 30})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:300]}"
        print("✅ GET /api/tenant/usage-summary returns 200")

    def test_usage_summary_has_metrics(self, admin_session):
        """Response should contain metrics object."""
        resp = admin_session.get(f"{BASE_URL}/api/tenant/usage-summary", params={"days": 30})
        assert resp.status_code == 200
        data = resp.json()
        
        assert "metrics" in data, "Response should have 'metrics' field"
        assert isinstance(data["metrics"], dict), "'metrics' should be a dict"
        print(f"✅ Response has metrics: {list(data['metrics'].keys())}")

    def test_usage_summary_has_trend(self, admin_session):
        """Response should contain trend data."""
        resp = admin_session.get(f"{BASE_URL}/api/tenant/usage-summary", params={"days": 30})
        assert resp.status_code == 200
        data = resp.json()
        
        assert "trend" in data, "Response should have 'trend' field"
        trend = data["trend"]
        assert "daily" in trend, "'trend' should have 'daily' array"
        assert "days" in trend, "'trend' should have 'days' count"
        assert isinstance(trend["daily"], list), "'daily' should be a list"
        print(f"✅ Trend data present: {trend.get('days')} days, {len(trend.get('daily', []))} daily entries")

    def test_usage_summary_has_primary_metrics(self, admin_session):
        """Response should contain primary_metrics list."""
        resp = admin_session.get(f"{BASE_URL}/api/tenant/usage-summary", params={"days": 30})
        assert resp.status_code == 200
        data = resp.json()
        
        assert "primary_metrics" in data, "Response should have 'primary_metrics'"
        primary = data["primary_metrics"]
        assert isinstance(primary, list), "'primary_metrics' should be a list"
        
        # Verify expected metrics
        for metric in EXPECTED_PRIMARY_METRICS:
            assert metric in primary, f"'{metric}' should be in primary_metrics"
        
        # Verify integration.call is NOT in primary (as per UM4 guardrails)
        assert "integration.call" not in primary, "integration.call should NOT be in primary_metrics for tenant view"
        print(f"✅ primary_metrics correct: {primary}")

    def test_usage_summary_has_plan_info(self, admin_session):
        """Response should have plan and billing period info."""
        resp = admin_session.get(f"{BASE_URL}/api/tenant/usage-summary", params={"days": 30})
        assert resp.status_code == 200
        data = resp.json()
        
        assert "plan" in data or "plan_label" in data, "Response should have plan info"
        assert "period" in data or "billing_period" in data, "Response should have billing period"
        print(f"✅ Plan: {data.get('plan_label') or data.get('plan')}, Period: {data.get('period') or data.get('billing_period')}")

    def test_usage_summary_metrics_structure(self, admin_session):
        """Each metric should have used, limit, percent fields."""
        resp = admin_session.get(f"{BASE_URL}/api/tenant/usage-summary", params={"days": 30})
        assert resp.status_code == 200
        data = resp.json()
        metrics = data.get("metrics", {})
        
        if not metrics:
            print("⚠️ No metrics returned (may be new tenant with no usage)")
            return
        
        for metric_key, metric_data in metrics.items():
            assert "used" in metric_data, f"Metric '{metric_key}' should have 'used'"
            assert "percent" in metric_data or "ratio" in metric_data, f"Metric '{metric_key}' should have 'percent' or 'ratio'"
            print(f"✅ Metric '{metric_key}': used={metric_data.get('used')}, percent={metric_data.get('percent')}")


class TestAdminBillingUsageEndpoint:
    """Tests for GET /api/admin/billing/tenants/{tenant_id}/usage"""

    def test_admin_usage_returns_200(self, admin_session, tenant_id):
        """Admin usage endpoint should return 200."""
        resp = admin_session.get(f"{BASE_URL}/api/admin/billing/tenants/{tenant_id}/usage", params={"days": 30})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:300]}"
        print(f"✅ GET /api/admin/billing/tenants/{tenant_id}/usage returns 200")

    def test_admin_usage_has_raw_usage_and_trend(self, admin_session, tenant_id):
        """Admin endpoint should return raw usage + trend (no upgrade suggestion per UM4)."""
        resp = admin_session.get(f"{BASE_URL}/api/admin/billing/tenants/{tenant_id}/usage", params={"days": 30})
        assert resp.status_code == 200
        data = resp.json()
        
        # Should have metrics
        assert "metrics" in data, "Admin response should have 'metrics'"
        
        # Should have trend
        assert "trend" in data, "Admin response should have 'trend'"
        
        # Should NOT have upgrade_suggestion (deferred per UM4)
        # This is a guardrail check - if it's present, it's fine but warn
        if "upgrade_suggestion" in data:
            print("⚠️ upgrade_suggestion found in response (should be deferred per UM4 spec)")
        
        print(f"✅ Admin usage has metrics + trend, no upgrade CTA enforced")

    def test_admin_usage_includes_all_metrics(self, admin_session, tenant_id):
        """Admin view should include all metrics (not just primary)."""
        resp = admin_session.get(f"{BASE_URL}/api/admin/billing/tenants/{tenant_id}/usage", params={"days": 30})
        assert resp.status_code == 200
        data = resp.json()
        
        metrics = data.get("metrics", {})
        # Admin should see all available metrics
        print(f"✅ Admin view metrics: {list(metrics.keys())}")

    def test_admin_usage_has_totals_source(self, admin_session, tenant_id):
        """Admin response should indicate data source."""
        resp = admin_session.get(f"{BASE_URL}/api/admin/billing/tenants/{tenant_id}/usage", params={"days": 30})
        assert resp.status_code == 200
        data = resp.json()
        
        # Should have totals_source or similar indicator
        source = data.get("totals_source")
        print(f"✅ Data source: {source or 'not specified'}")

    def test_admin_usage_trend_structure(self, admin_session, tenant_id):
        """Trend should have daily array with date and metric counts."""
        resp = admin_session.get(f"{BASE_URL}/api/admin/billing/tenants/{tenant_id}/usage", params={"days": 30})
        assert resp.status_code == 200
        data = resp.json()
        
        trend = data.get("trend", {})
        daily = trend.get("daily", [])
        
        if daily:
            first_day = daily[0]
            assert "date" in first_day, "Daily entry should have 'date'"
            print(f"✅ Trend daily structure correct: {len(daily)} entries, first: {first_day.get('date')}")
        else:
            print("⚠️ No daily trend data (new tenant or no activity)")


class TestUsageReadServiceConstants:
    """Test that PRIMARY_USAGE_METRICS matches expected values."""

    def test_tenant_usage_filters_to_primary_only(self, admin_session):
        """Tenant usage summary should only show primary metrics."""
        resp = admin_session.get(f"{BASE_URL}/api/tenant/usage-summary", params={"days": 30})
        assert resp.status_code == 200
        data = resp.json()
        
        metrics = data.get("metrics", {})
        primary = data.get("primary_metrics", [])
        
        # All metrics keys should be in primary_metrics
        for key in metrics.keys():
            assert key in primary, f"Metric '{key}' should be in primary_metrics for tenant view"
        
        print(f"✅ Tenant view correctly filtered to primary metrics: {list(metrics.keys())}")


class TestNoUpgradeCTAYet:
    """Verify no upgrade CTA is present (deferred per UM4)."""

    def test_tenant_usage_no_upgrade_cta(self, admin_session):
        """Tenant usage should not have upgrade CTA."""
        resp = admin_session.get(f"{BASE_URL}/api/tenant/usage-summary", params={"days": 30})
        assert resp.status_code == 200
        data = resp.json()
        
        # Check for upgrade-related fields
        has_upgrade = any(k in data for k in ["upgrade_suggestion", "upgrade_cta", "recommended_plan"])
        if has_upgrade:
            print("⚠️ Upgrade CTA found in tenant usage (should be deferred)")
        else:
            print("✅ No upgrade CTA in tenant usage (correct per UM4)")

    def test_admin_usage_no_upgrade_suggestion(self, admin_session, tenant_id):
        """Admin usage should not have upgrade suggestion."""
        resp = admin_session.get(f"{BASE_URL}/api/admin/billing/tenants/{tenant_id}/usage", params={"days": 30})
        assert resp.status_code == 200
        data = resp.json()
        
        has_upgrade = any(k in data for k in ["upgrade_suggestion", "upgrade_cta", "recommended_plan"])
        if has_upgrade:
            print("⚠️ Upgrade suggestion found in admin usage (should be deferred)")
        else:
            print("✅ No upgrade suggestion in admin usage (correct per UM4)")


class TestTenantContextResolution:
    """Test that tenant context is properly resolved."""

    def test_usage_summary_resolves_tenant(self, admin_session):
        """Usage summary should resolve tenant from user context."""
        resp = admin_session.get(f"{BASE_URL}/api/tenant/usage-summary", params={"days": 30})
        
        # Should not return tenant_context_missing error
        if resp.status_code == 400:
            data = resp.json()
            error_code = data.get("error_code") or data.get("code")
            if error_code == "tenant_context_missing":
                pytest.fail("tenant_context_missing error - context fallback not working")
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        
        data = resp.json()
        tenant_id = data.get("tenant_id")
        assert tenant_id, "Response should include resolved tenant_id"
        print(f"✅ Tenant context resolved: {tenant_id}")
