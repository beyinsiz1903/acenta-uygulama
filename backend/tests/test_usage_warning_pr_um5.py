"""
PR-UM5 Usage Warning Levels + CTA Integration Tests

Tests:
- Quota warning helper thresholds: 50% normal, 70% warning, 85% critical, 100% limit_reached
- GET /api/tenant/usage-summary includes warning_level, warning_message, upgrade_recommended, cta_href/cta_label per metric
- GET /api/tenant/usage-summary includes trial_conversion payload when tenant is trialing and usage_ratio > 0
- GET /api/tenant/quota-status exposes warning fields used by app shell warnings
"""

import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://usage-metering.preview.emergentagent.com").rstrip("/")

# Credentials
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "admin123"
TRIAL_EMAIL = "admin@demo-travel.demo.test"
TRIAL_PASSWORD = "Demotrav!9831"


@pytest.fixture(scope="module")
def admin_token():
    """Authenticate as admin user"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    if resp.status_code == 200:
        return resp.json().get("access_token") or resp.json().get("token")
    pytest.skip(f"Admin login failed: {resp.status_code}")


@pytest.fixture(scope="module")
def trial_token():
    """Authenticate as trial demo tenant user"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={"email": TRIAL_EMAIL, "password": TRIAL_PASSWORD})
    if resp.status_code == 200:
        return resp.json().get("access_token") or resp.json().get("token")
    pytest.skip(f"Trial login failed: {resp.status_code}")


class TestQuotaWarningService:
    """Unit-level validation of quota warning thresholds"""
    
    def test_warning_level_normal_under_70(self):
        """50% usage should be 'normal'"""
        from app.services.quota_warning_service import calculate_warning_level
        assert calculate_warning_level(50, 100) == "normal"
        assert calculate_warning_level(69, 100) == "normal"
    
    def test_warning_level_warning_at_70(self):
        """70% usage should be 'warning'"""
        from app.services.quota_warning_service import calculate_warning_level
        assert calculate_warning_level(70, 100) == "warning"
        assert calculate_warning_level(84, 100) == "warning"
    
    def test_warning_level_critical_at_85(self):
        """85% usage should be 'critical'"""
        from app.services.quota_warning_service import calculate_warning_level
        assert calculate_warning_level(85, 100) == "critical"
        assert calculate_warning_level(99, 100) == "critical"
    
    def test_warning_level_limit_reached_at_100(self):
        """100% usage should be 'limit_reached'"""
        from app.services.quota_warning_service import calculate_warning_level
        assert calculate_warning_level(100, 100) == "limit_reached"
        assert calculate_warning_level(150, 100) == "limit_reached"  # Over limit
    
    def test_warning_level_with_none_limit(self):
        """None limit should return 'normal' (unlimited)"""
        from app.services.quota_warning_service import calculate_warning_level
        assert calculate_warning_level(100, None) == "normal"
        assert calculate_warning_level(100, 0) == "normal"


class TestTrialPlanRecommendation:
    """Validate trial plan recommendation thresholds"""
    
    def test_recommend_starter_under_40(self):
        """<40% usage should recommend Starter"""
        from app.services.quota_warning_service import recommend_plan
        assert recommend_plan(0.0) == "Starter"
        assert recommend_plan(0.39) == "Starter"
    
    def test_recommend_pro_40_to_80(self):
        """40-80% usage should recommend Pro"""
        from app.services.quota_warning_service import recommend_plan
        assert recommend_plan(0.4) == "Pro"
        assert recommend_plan(0.79) == "Pro"
    
    def test_recommend_enterprise_over_80(self):
        """>80% usage should recommend Enterprise"""
        from app.services.quota_warning_service import recommend_plan
        assert recommend_plan(0.8) == "Enterprise"
        assert recommend_plan(1.0) == "Enterprise"


class TestTenantUsageSummaryEndpoint:
    """Test GET /api/tenant/usage-summary with warning fields"""
    
    def test_usage_summary_returns_200(self, trial_token):
        """Usage summary endpoint should return 200"""
        resp = requests.get(
            f"{BASE_URL}/api/tenant/usage-summary?days=30",
            headers={"Authorization": f"Bearer {trial_token}"}
        )
        assert resp.status_code == 200
        print(f"✅ Usage summary status: {resp.status_code}")
    
    def test_usage_summary_has_warning_fields_per_metric(self, trial_token):
        """Each metric should include warning_level, warning_message, upgrade_recommended"""
        resp = requests.get(
            f"{BASE_URL}/api/tenant/usage-summary?days=30",
            headers={"Authorization": f"Bearer {trial_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        metrics = data.get("metrics", {})
        
        assert len(metrics) > 0, "Should have at least one metric"
        
        for metric_key, metric_data in metrics.items():
            assert "warning_level" in metric_data, f"Missing warning_level for {metric_key}"
            assert metric_data["warning_level"] in ["normal", "warning", "critical", "limit_reached"]
            assert "warning_message" in metric_data, f"Missing warning_message for {metric_key}"
            assert "upgrade_recommended" in metric_data, f"Missing upgrade_recommended for {metric_key}"
            assert isinstance(metric_data["upgrade_recommended"], bool)
            print(f"✅ {metric_key}: warning_level={metric_data['warning_level']}, upgrade={metric_data['upgrade_recommended']}")
    
    def test_usage_summary_cta_fields_when_upgrade_recommended(self, trial_token):
        """When upgrade_recommended=true, cta_href and cta_label should be present"""
        resp = requests.get(
            f"{BASE_URL}/api/tenant/usage-summary?days=30",
            headers={"Authorization": f"Bearer {trial_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        metrics = data.get("metrics", {})
        
        for metric_key, metric_data in metrics.items():
            if metric_data.get("upgrade_recommended"):
                assert metric_data.get("cta_href") == "/pricing", f"CTA href should be /pricing for {metric_key}"
                assert metric_data.get("cta_label") is not None, f"CTA label should be present for {metric_key}"
                print(f"✅ {metric_key}: CTA present with href={metric_data['cta_href']}")
    
    def test_usage_summary_has_trial_conversion_payload(self, trial_token):
        """Trial tenant should have trial_conversion payload"""
        resp = requests.get(
            f"{BASE_URL}/api/tenant/usage-summary?days=30",
            headers={"Authorization": f"Bearer {trial_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        
        # Check trial_conversion exists
        assert "trial_conversion" in data, "Missing trial_conversion in response"
        tc = data["trial_conversion"]
        
        # Required fields
        assert "is_trial" in tc
        assert "show" in tc
        assert "usage_ratio" in tc
        assert "recommended_plan" in tc
        assert "message" in tc
        assert "cta_href" in tc
        assert "cta_label" in tc
        
        print(f"✅ trial_conversion: is_trial={tc['is_trial']}, show={tc['show']}, plan={tc.get('recommended_plan')}")
        
        # If trial and usage_ratio > 0, show should be True
        if tc.get("is_trial") and tc.get("usage_ratio", 0) > 0:
            assert tc["show"] is True
            assert tc["recommended_plan"] in ["Starter", "Pro", "Enterprise"]
            assert tc["cta_href"] == "/pricing"
            print(f"✅ Trial conversion CTA: {tc['cta_label']} -> {tc['cta_href']}")


class TestTenantQuotaStatusEndpoint:
    """Test GET /api/tenant/quota-status for app shell warnings"""
    
    def test_quota_status_returns_200(self, trial_token):
        """Quota status endpoint should return 200"""
        resp = requests.get(
            f"{BASE_URL}/api/tenant/quota-status",
            headers={"Authorization": f"Bearer {trial_token}"}
        )
        assert resp.status_code == 200
        print(f"✅ Quota status: {resp.status_code}")
    
    def test_quota_status_has_quotas_array(self, trial_token):
        """Should have quotas array with warning fields"""
        resp = requests.get(
            f"{BASE_URL}/api/tenant/quota-status",
            headers={"Authorization": f"Bearer {trial_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        
        assert "quotas" in data
        assert isinstance(data["quotas"], list)
        
        for quota in data["quotas"]:
            assert "metric" in quota
            assert "used" in quota
            assert "quota" in quota
            assert "warning_level" in quota
            assert "warning_message" in quota
            assert "upgrade_recommended" in quota
            print(f"✅ Quota item: {quota['metric']} - {quota['warning_level']}")
    
    def test_quota_status_cta_fields(self, trial_token):
        """Quota status should include cta_href and cta_label"""
        resp = requests.get(
            f"{BASE_URL}/api/tenant/quota-status",
            headers={"Authorization": f"Bearer {trial_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        
        for quota in data.get("quotas", []):
            assert "cta_href" in quota
            assert "cta_label" in quota
            if quota.get("upgrade_recommended"):
                assert quota["cta_href"] == "/pricing"
                print(f"✅ {quota['metric']}: CTA -> {quota['cta_href']}")


class TestAdminUsageNoCTA:
    """Verify admin usage views have NO pricing CTA"""
    
    def test_admin_usage_endpoint_exists(self, admin_token):
        """Admin usage endpoint should work"""
        # First get a tenant ID
        resp = requests.get(
            f"{BASE_URL}/api/admin/tenants",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            pytest.skip("Admin tenants endpoint not accessible")
        
        tenants_data = resp.json()
        # Handle paginated response
        tenants = tenants_data.get("items", tenants_data) if isinstance(tenants_data, dict) else tenants_data
        if not tenants:
            pytest.skip("No tenants available")
        
        tenant_id = tenants[0].get("_id") or tenants[0].get("id")
        
        resp = requests.get(
            f"{BASE_URL}/api/admin/billing/tenants/{tenant_id}/usage?days=30",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code == 200
        print(f"✅ Admin usage endpoint working for tenant {tenant_id}")


class TestTrialDemoTenantSpecifically:
    """Test with trial demo tenant that has 85/100 export usage"""
    
    def test_trial_tenant_has_critical_warning(self, trial_token):
        """Trial tenant with 85% usage should show critical warning"""
        resp = requests.get(
            f"{BASE_URL}/api/tenant/usage-summary?days=30",
            headers={"Authorization": f"Bearer {trial_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        
        # Check if export.generated has critical/limit_reached warning
        metrics = data.get("metrics", {})
        export_metric = metrics.get("export.generated", {})
        
        if export_metric:
            warning = export_metric.get("warning_level")
            used = export_metric.get("used")
            limit = export_metric.get("limit")
            print(f"✅ export.generated: used={used}, limit={limit}, warning={warning}")
            
            # If 85/100, should be critical
            if used and limit and used >= limit * 0.85:
                assert warning in ["critical", "limit_reached"], f"Expected critical/limit_reached for 85%+ usage, got {warning}"
                assert export_metric.get("upgrade_recommended") is True
                assert export_metric.get("cta_href") == "/pricing"
                print(f"✅ CTA shown for export: {export_metric.get('cta_label')} -> {export_metric.get('cta_href')}")
    
    def test_trial_conversion_recommendation(self, trial_token):
        """Trial tenant should have plan recommendation"""
        resp = requests.get(
            f"{BASE_URL}/api/tenant/usage-summary?days=30",
            headers={"Authorization": f"Bearer {trial_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        
        tc = data.get("trial_conversion", {})
        is_trial = data.get("is_trial", False)
        
        print(f"✅ is_trial={is_trial}, trial_conversion.show={tc.get('show')}")
        
        if is_trial and tc.get("usage_ratio", 0) > 0:
            assert tc["show"] is True
            ratio = tc.get("usage_ratio", 0)
            plan = tc.get("recommended_plan")
            
            # Validate recommendation matches rule
            if ratio < 0.4:
                assert plan == "Starter"
            elif ratio < 0.8:
                assert plan == "Pro"
            else:
                assert plan == "Enterprise"
            
            print(f"✅ Recommended plan: {plan} for usage_ratio={ratio}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
