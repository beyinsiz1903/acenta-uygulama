"""
PR-UM5 Soft Quota Warnings & Upgrade CTAs - Integration Tests

Tests:
- Cookie-compat login with agent@acenta.test / agent123
- GET /api/auth/me returns tenant_id for cookie-auth frontend bootstrap
- GET /api/tenant/usage-summary returns Trial plan with warning/critical/limit_reached states
- Warning colors: normal=gray, warning=sarı (amber), critical=turuncu (orange), limit_reached=kırmızı (red)
- CTA label: 'Planları Görüntüle', CTA target: /pricing
- Trial recommendation: 'Trial kullanımınız devam ediyor.' with recommended plan 'Pro Plan'
"""

import os
import pytest
import requests

from tests.preview_auth_helper import get_preview_base_url_or_skip

BASE_URL = get_preview_base_url_or_skip(os.environ.get("REACT_APP_BACKEND_URL", ""))

# PR-UM5 specific credentials
AGENT_EMAIL = "agent@acenta.test"
AGENT_PASSWORD = "agent123"


@pytest.fixture(scope="module")
def agent_session():
    """Authenticate as agent user and return session with cookies"""
    session = requests.Session()
    resp = session.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": AGENT_EMAIL, "password": AGENT_PASSWORD},
        headers={"X-Acenta-Web-Auth": "browser"}  # Cookie compat header
    )
    if resp.status_code != 200:
        pytest.skip(f"Agent login failed: {resp.status_code} - {resp.text}")
    
    data = resp.json()
    token = data.get("access_token") or data.get("token")
    session.headers.update({"Authorization": f"Bearer {token}"})
    return {
        "session": session,
        "token": token,
        "login_response": data
    }


class TestCookieCompatLogin:
    """Test cookie-compat login flow"""
    
    def test_login_returns_200(self):
        """Login with agent credentials should succeed"""
        resp = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": AGENT_EMAIL, "password": AGENT_PASSWORD}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data or "token" in data
        print(f"✅ Login successful for {AGENT_EMAIL}")
    
    def test_login_returns_tenant_id(self):
        """Login should return tenant_id"""
        resp = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": AGENT_EMAIL, "password": AGENT_PASSWORD}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "tenant_id" in data, "tenant_id should be in login response"
        assert data["tenant_id"], "tenant_id should not be empty"
        print(f"✅ tenant_id: {data['tenant_id']}")


class TestAuthMe:
    """Test GET /api/auth/me returns tenant_id"""
    
    def test_auth_me_returns_200(self, agent_session):
        """/api/auth/me should return 200"""
        session = agent_session["session"]
        resp = session.get(f"{BASE_URL}/api/auth/me")
        assert resp.status_code == 200
        print(f"✅ /api/auth/me status: {resp.status_code}")
    
    def test_auth_me_returns_tenant_id(self, agent_session):
        """GET /api/auth/me should return tenant_id for frontend bootstrap"""
        session = agent_session["session"]
        resp = session.get(f"{BASE_URL}/api/auth/me")
        assert resp.status_code == 200
        data = resp.json()
        assert "tenant_id" in data, "tenant_id should be in /api/auth/me response"
        assert data["tenant_id"], "tenant_id should not be empty"
        print(f"✅ tenant_id from /api/auth/me: {data['tenant_id']}")
    
    def test_auth_me_returns_user_info(self, agent_session):
        """GET /api/auth/me should return user email and roles"""
        session = agent_session["session"]
        resp = session.get(f"{BASE_URL}/api/auth/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("email") == AGENT_EMAIL
        assert "roles" in data
        print(f"✅ User: {data['email']}, roles: {data['roles']}")


class TestUsageSummaryEndpoint:
    """Test GET /api/tenant/usage-summary?days=30"""
    
    def test_usage_summary_returns_200(self, agent_session):
        """Usage summary endpoint should return 200"""
        session = agent_session["session"]
        resp = session.get(f"{BASE_URL}/api/tenant/usage-summary?days=30")
        assert resp.status_code == 200
        print(f"✅ /api/tenant/usage-summary status: {resp.status_code}")
    
    def test_usage_summary_returns_trial_plan(self, agent_session):
        """Demo tenant should have Trial plan"""
        session = agent_session["session"]
        resp = session.get(f"{BASE_URL}/api/tenant/usage-summary?days=30")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("plan") == "trial", f"Expected 'trial' plan, got {data.get('plan')}"
        assert data.get("is_trial") is True, "is_trial should be True"
        print(f"✅ Plan: {data['plan']}, is_trial: {data['is_trial']}")
    
    def test_usage_summary_has_metrics_with_warning_levels(self, agent_session):
        """Each metric should have warning_level field"""
        session = agent_session["session"]
        resp = session.get(f"{BASE_URL}/api/tenant/usage-summary?days=30")
        assert resp.status_code == 200
        data = resp.json()
        
        metrics = data.get("metrics", {})
        assert len(metrics) > 0, "Should have at least one metric"
        
        for metric_key, metric_data in metrics.items():
            assert "warning_level" in metric_data, f"Missing warning_level for {metric_key}"
            assert metric_data["warning_level"] in ["normal", "warning", "critical", "limit_reached"]
            print(f"✅ {metric_key}: warning_level={metric_data['warning_level']}")
    
    def test_reservation_created_warning_state(self, agent_session):
        """reservation.created 70/100 should be 'warning' (70%)"""
        session = agent_session["session"]
        resp = session.get(f"{BASE_URL}/api/tenant/usage-summary?days=30")
        assert resp.status_code == 200
        data = resp.json()
        
        metric = data.get("metrics", {}).get("reservation.created", {})
        assert metric.get("used") == 70, f"Expected 70, got {metric.get('used')}"
        assert metric.get("limit") == 100, f"Expected limit 100, got {metric.get('limit')}"
        assert metric.get("warning_level") == "warning", f"Expected 'warning', got {metric.get('warning_level')}"
        print(f"✅ reservation.created: {metric['used']}/{metric['limit']} = {metric['warning_level']}")
    
    def test_report_generated_critical_state(self, agent_session):
        """report.generated 17/20 should be 'critical' (85%)"""
        session = agent_session["session"]
        resp = session.get(f"{BASE_URL}/api/tenant/usage-summary?days=30")
        assert resp.status_code == 200
        data = resp.json()
        
        metric = data.get("metrics", {}).get("report.generated", {})
        assert metric.get("used") == 17, f"Expected 17, got {metric.get('used')}"
        assert metric.get("limit") == 20, f"Expected limit 20, got {metric.get('limit')}"
        assert metric.get("warning_level") == "critical", f"Expected 'critical', got {metric.get('warning_level')}"
        # Critical should have upgrade CTA
        assert metric.get("upgrade_recommended") is True
        assert metric.get("cta_href") == "/pricing"
        assert metric.get("cta_label") == "Planları Görüntüle"
        print(f"✅ report.generated: {metric['used']}/{metric['limit']} = {metric['warning_level']} + CTA")
    
    def test_export_generated_limit_reached_state(self, agent_session):
        """export.generated 10/10 should be 'limit_reached' (100%)"""
        session = agent_session["session"]
        resp = session.get(f"{BASE_URL}/api/tenant/usage-summary?days=30")
        assert resp.status_code == 200
        data = resp.json()
        
        metric = data.get("metrics", {}).get("export.generated", {})
        assert metric.get("used") == 10, f"Expected 10, got {metric.get('used')}"
        assert metric.get("limit") == 10, f"Expected limit 10, got {metric.get('limit')}"
        assert metric.get("warning_level") == "limit_reached", f"Expected 'limit_reached', got {metric.get('warning_level')}"
        # Limit reached should have upgrade CTA
        assert metric.get("upgrade_recommended") is True
        assert metric.get("cta_href") == "/pricing"
        assert metric.get("cta_label") == "Planları Görüntüle"
        print(f"✅ export.generated: {metric['used']}/{metric['limit']} = {metric['warning_level']} + CTA")


class TestCTAConfiguration:
    """Test CTA labels and targets match PR-UM5 spec"""
    
    def test_cta_target_is_pricing(self, agent_session):
        """CTA href should be /pricing"""
        session = agent_session["session"]
        resp = session.get(f"{BASE_URL}/api/tenant/usage-summary?days=30")
        assert resp.status_code == 200
        data = resp.json()
        
        metrics = data.get("metrics", {})
        for metric_key, metric_data in metrics.items():
            if metric_data.get("upgrade_recommended"):
                assert metric_data.get("cta_href") == "/pricing", f"CTA href should be /pricing for {metric_key}"
                print(f"✅ {metric_key} CTA href: {metric_data['cta_href']}")
    
    def test_cta_label_is_turkish(self, agent_session):
        """CTA label should be 'Planları Görüntüle'"""
        session = agent_session["session"]
        resp = session.get(f"{BASE_URL}/api/tenant/usage-summary?days=30")
        assert resp.status_code == 200
        data = resp.json()
        
        metrics = data.get("metrics", {})
        for metric_key, metric_data in metrics.items():
            if metric_data.get("upgrade_recommended"):
                assert metric_data.get("cta_label") == "Planları Görüntüle", f"CTA label should be 'Planları Görüntüle' for {metric_key}"
                print(f"✅ {metric_key} CTA label: {metric_data['cta_label']}")


class TestTrialConversion:
    """Test trial_conversion payload with Pro Plan recommendation"""
    
    def test_trial_conversion_is_present(self, agent_session):
        """trial_conversion should be in response"""
        session = agent_session["session"]
        resp = session.get(f"{BASE_URL}/api/tenant/usage-summary?days=30")
        assert resp.status_code == 200
        data = resp.json()
        
        assert "trial_conversion" in data, "trial_conversion should be in response"
        tc = data["trial_conversion"]
        assert "is_trial" in tc
        assert "show" in tc
        assert "usage_ratio" in tc
        assert "recommended_plan" in tc
        assert "message" in tc
        print(f"✅ trial_conversion present: is_trial={tc['is_trial']}, show={tc['show']}")
    
    def test_trial_conversion_shows_for_trial_tenant(self, agent_session):
        """Trial tenant should have show=True"""
        session = agent_session["session"]
        resp = session.get(f"{BASE_URL}/api/tenant/usage-summary?days=30")
        assert resp.status_code == 200
        data = resp.json()
        
        tc = data["trial_conversion"]
        assert tc.get("is_trial") is True
        assert tc.get("show") is True
        print(f"✅ Trial conversion showing for trial tenant")
    
    def test_trial_message_is_correct(self, agent_session):
        """Trial message should be 'Trial kullanımınız devam ediyor.'"""
        session = agent_session["session"]
        resp = session.get(f"{BASE_URL}/api/tenant/usage-summary?days=30")
        assert resp.status_code == 200
        data = resp.json()
        
        tc = data["trial_conversion"]
        assert tc.get("message") == "Trial kullanımınız devam ediyor.", f"Expected Turkish message, got {tc.get('message')}"
        print(f"✅ Trial message: {tc['message']}")
    
    def test_recommended_plan_is_pro(self, agent_session):
        """With 70% usage ratio, recommended plan should be 'Pro'"""
        session = agent_session["session"]
        resp = session.get(f"{BASE_URL}/api/tenant/usage-summary?days=30")
        assert resp.status_code == 200
        data = resp.json()
        
        tc = data["trial_conversion"]
        # 40-80% usage recommends Pro
        assert tc.get("recommended_plan") == "Pro", f"Expected 'Pro', got {tc.get('recommended_plan')}"
        assert tc.get("recommended_plan_label") == "Pro Plan", f"Expected 'Pro Plan', got {tc.get('recommended_plan_label')}"
        print(f"✅ Recommended plan: {tc['recommended_plan']} ({tc['recommended_plan_label']})")
    
    def test_trial_conversion_cta(self, agent_session):
        """Trial conversion CTA should point to /pricing with correct label"""
        session = agent_session["session"]
        resp = session.get(f"{BASE_URL}/api/tenant/usage-summary?days=30")
        assert resp.status_code == 200
        data = resp.json()
        
        tc = data["trial_conversion"]
        assert tc.get("cta_href") == "/pricing"
        assert tc.get("cta_label") == "Planları Görüntüle"
        print(f"✅ Trial CTA: {tc['cta_label']} -> {tc['cta_href']}")


class TestTrendData:
    """Test trend chart data is present"""
    
    def test_trend_data_present(self, agent_session):
        """Response should have 30-day trend data"""
        session = agent_session["session"]
        resp = session.get(f"{BASE_URL}/api/tenant/usage-summary?days=30")
        assert resp.status_code == 200
        data = resp.json()
        
        assert "trend" in data, "trend should be in response"
        trend = data["trend"]
        assert trend.get("days") == 30
        assert "daily" in trend
        assert len(trend["daily"]) == 30
        print(f"✅ Trend data: {trend['days']} days")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
