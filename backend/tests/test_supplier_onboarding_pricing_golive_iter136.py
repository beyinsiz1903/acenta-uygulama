"""Supplier Onboarding Pricing & Go-Live Tests — Iteration 136

Tests the NEW Pricing Setup and Go-Live features for Supplier Self-Serve Onboarding:
- GET /api/supplier-onboarding/dashboard - returns 6 suppliers with status
- GET /api/supplier-onboarding/detail/{supplier_code} - returns supplier detail including pricing_config
- GET /api/supplier-onboarding/pricing-setup/{supplier_code} - returns pricing config defaults for unconfigured, actual for configured
- POST /api/supplier-onboarding/pricing-setup/{supplier_code} - saves pricing config and updates status to pricing_configured
- POST /api/supplier-onboarding/go-live/{supplier_code} - toggles go-live and logs activity timeline event
- POST /api/supplier-onboarding/credentials - saves credentials
- POST /api/supplier-onboarding/validate/{supplier_code} - runs health check
- POST /api/supplier-onboarding/certify/{supplier_code} - runs certification
- Activity Timeline: Go-live action logs an event to /api/activity-timeline

Mocked APIs: Health check and certification tests use simulated results (always pass in sandbox mode).
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
TEST_EMAIL = "agent@acenta.test"
TEST_PASSWORD = "agent123"

# Expected suppliers
EXPECTED_SUPPLIERS = ["ratehawk", "paximum", "tbo", "wtatil", "hotelbeds", "juniper"]

# Test supplier for pricing/go-live flow
TEST_SUPPLIER_PRICING = "hotelbeds"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for super admin"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if resp.status_code == 200:
        data = resp.json()
        return data.get("access_token") or data.get("token")
    pytest.skip(f"Auth failed: {resp.status_code} — {resp.text[:200]}")


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Authenticated requests session"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


# ============================================================
# DASHBOARD & DETAIL TESTS
# ============================================================

class TestDashboardReturns6Suppliers:
    """Test GET /api/supplier-onboarding/dashboard returns 6 suppliers with status"""
    
    def test_dashboard_returns_6_suppliers(self, api_client):
        """Dashboard should return status for all 6 suppliers"""
        resp = api_client.get(f"{BASE_URL}/api/supplier-onboarding/dashboard")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        
        data = resp.json()
        assert "suppliers" in data
        assert len(data["suppliers"]) == 6, f"Expected 6 suppliers, got {len(data['suppliers'])}"
        
        # Check each supplier has required fields
        for supplier in data["suppliers"]:
            assert "supplier_code" in supplier
            assert "status" in supplier
            
    def test_dashboard_has_go_live_threshold(self, api_client):
        """Dashboard should include go_live_threshold of 80"""
        resp = api_client.get(f"{BASE_URL}/api/supplier-onboarding/dashboard")
        assert resp.status_code == 200
        
        data = resp.json()
        assert "go_live_threshold" in data
        assert data["go_live_threshold"] == 80


class TestSupplierDetailIncludesPricingConfig:
    """Test GET /api/supplier-onboarding/detail/{supplier_code} returns pricing_config"""
    
    def test_supplier_detail_includes_pricing_config_field(self, api_client):
        """Supplier detail should include pricing_config field (null if not configured)"""
        resp = api_client.get(f"{BASE_URL}/api/supplier-onboarding/detail/ratehawk")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        
        data = resp.json()
        assert "pricing_config" in data, "pricing_config field missing from supplier detail"
        # pricing_config can be null or an object
        
    def test_supplier_detail_has_all_required_fields(self, api_client):
        """Supplier detail should have all required fields"""
        resp = api_client.get(f"{BASE_URL}/api/supplier-onboarding/detail/paximum")
        assert resp.status_code == 200
        
        data = resp.json()
        required_fields = ["code", "name", "status", "credential_fields", "go_live"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"


# ============================================================
# PRICING SETUP TESTS
# ============================================================

class TestPricingSetupGetDefaults:
    """Test GET /api/supplier-onboarding/pricing-setup/{supplier_code}"""
    
    def test_pricing_setup_returns_defaults_for_unconfigured(self, api_client):
        """Pricing setup should return default config for unconfigured suppliers"""
        # Reset supplier first to ensure clean state
        api_client.post(f"{BASE_URL}/api/supplier-onboarding/reset/tbo")
        
        resp = api_client.get(f"{BASE_URL}/api/supplier-onboarding/pricing-setup/tbo")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        
        data = resp.json()
        assert "supplier_code" in data
        assert "pricing_config" in data
        assert data.get("is_default") is True, "Expected is_default=True for unconfigured supplier"
        
        # Check default values
        config = data["pricing_config"]
        assert config.get("base_markup_pct") == 10, "Default base_markup_pct should be 10"
        
    def test_pricing_setup_has_channel_rules(self, api_client):
        """Pricing config should include channel rules (B2B, B2C, Corporate, Whitelabel)"""
        resp = api_client.get(f"{BASE_URL}/api/supplier-onboarding/pricing-setup/wtatil")
        assert resp.status_code == 200
        
        data = resp.json()
        config = data.get("pricing_config", {})
        channels = config.get("channels", {})
        
        expected_channels = ["b2b", "b2c", "corporate", "whitelabel"]
        for ch in expected_channels:
            assert ch in channels, f"Missing channel: {ch}"
            assert "adjustment_pct" in channels[ch], f"Missing adjustment_pct for {ch}"
            assert "active" in channels[ch], f"Missing active flag for {ch}"
            
    def test_pricing_setup_has_agency_tiers(self, api_client):
        """Pricing config should include agency tier discounts"""
        resp = api_client.get(f"{BASE_URL}/api/supplier-onboarding/pricing-setup/juniper")
        assert resp.status_code == 200
        
        data = resp.json()
        config = data.get("pricing_config", {})
        tiers = config.get("agency_tiers", {})
        
        expected_tiers = ["starter", "standard", "premium", "enterprise"]
        for tier in expected_tiers:
            assert tier in tiers, f"Missing tier: {tier}"
            assert "discount_pct" in tiers[tier], f"Missing discount_pct for {tier}"
            
    def test_pricing_setup_has_guardrails(self, api_client):
        """Pricing config should include guardrails (min_margin_pct, max_discount_pct)"""
        resp = api_client.get(f"{BASE_URL}/api/supplier-onboarding/pricing-setup/ratehawk")
        assert resp.status_code == 200
        
        data = resp.json()
        config = data.get("pricing_config", {})
        guardrails = config.get("guardrails", {})
        
        assert "min_margin_pct" in guardrails, "Missing min_margin_pct in guardrails"
        assert "max_discount_pct" in guardrails, "Missing max_discount_pct in guardrails"


class TestPricingSetupSave:
    """Test POST /api/supplier-onboarding/pricing-setup/{supplier_code}"""
    
    def test_save_pricing_setup_for_certified_supplier(self, api_client):
        """Save pricing config should update status to pricing_configured for certified supplier"""
        # First, go through the full onboarding flow to get to certified state
        api_client.post(f"{BASE_URL}/api/supplier-onboarding/reset/{TEST_SUPPLIER_PRICING}")
        
        # Save credentials for hotelbeds
        cred_resp = api_client.post(f"{BASE_URL}/api/supplier-onboarding/credentials", json={
            "supplier_code": TEST_SUPPLIER_PRICING,
            "credentials": {
                "base_url": "https://api.test.hotelbeds.com",
                "api_key": "test_api_key_1234",
                "secret": "test_secret_5678"
            }
        })
        assert cred_resp.status_code == 200
        
        # Run health check
        health_resp = api_client.post(f"{BASE_URL}/api/supplier-onboarding/validate/{TEST_SUPPLIER_PRICING}")
        assert health_resp.status_code == 200
        
        # Run certification
        cert_resp = api_client.post(f"{BASE_URL}/api/supplier-onboarding/certify/{TEST_SUPPLIER_PRICING}")
        assert cert_resp.status_code == 200
        
        # Now save pricing config
        pricing_payload = {
            "base_markup_pct": 12,
            "channels": {
                "b2b": {"adjustment_pct": -6, "active": True},
                "b2c": {"adjustment_pct": 4, "active": True},
                "corporate": {"adjustment_pct": -10, "active": True},
                "whitelabel": {"adjustment_pct": -4, "active": False}
            },
            "agency_tiers": {
                "starter": {"discount_pct": 0},
                "standard": {"discount_pct": 3},
                "premium": {"discount_pct": 6},
                "enterprise": {"discount_pct": 10}
            },
            "min_margin_pct": 4,
            "max_discount_pct": 30
        }
        
        resp = api_client.post(f"{BASE_URL}/api/supplier-onboarding/pricing-setup/{TEST_SUPPLIER_PRICING}", json=pricing_payload)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        
        data = resp.json()
        assert data.get("status") == "pricing_configured", f"Expected status pricing_configured, got {data.get('status')}"
        assert "pricing_config" in data
        
    def test_pricing_config_persists_after_save(self, api_client):
        """GET pricing-setup should return saved config, not defaults"""
        resp = api_client.get(f"{BASE_URL}/api/supplier-onboarding/pricing-setup/{TEST_SUPPLIER_PRICING}")
        assert resp.status_code == 200
        
        data = resp.json()
        assert data.get("is_default") is False, "Expected is_default=False after saving"
        
        config = data.get("pricing_config", {})
        assert config.get("base_markup_pct") == 12, f"Expected base_markup_pct=12, got {config.get('base_markup_pct')}"
        
    def test_pricing_config_in_supplier_detail(self, api_client):
        """Supplier detail should show pricing_config after saving"""
        resp = api_client.get(f"{BASE_URL}/api/supplier-onboarding/detail/{TEST_SUPPLIER_PRICING}")
        assert resp.status_code == 200
        
        data = resp.json()
        assert data.get("status") == "pricing_configured"
        assert data.get("pricing_config") is not None
        assert data["pricing_config"].get("base_markup_pct") == 12


# ============================================================
# GO-LIVE TESTS
# ============================================================

class TestGoLiveToggle:
    """Test POST /api/supplier-onboarding/go-live/{supplier_code}"""
    
    def test_go_live_enable_for_pricing_configured_supplier(self, api_client):
        """Go-live toggle should activate supplier for production traffic"""
        resp = api_client.post(f"{BASE_URL}/api/supplier-onboarding/go-live/{TEST_SUPPLIER_PRICING}", json={
            "enabled": True
        })
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        
        data = resp.json()
        assert data.get("status") == "live", f"Expected status 'live', got {data.get('status')}"
        assert data.get("go_live") is True
        assert "message" in data
        
    def test_go_live_disable(self, api_client):
        """Go-live toggle off should deactivate supplier"""
        resp = api_client.post(f"{BASE_URL}/api/supplier-onboarding/go-live/{TEST_SUPPLIER_PRICING}", json={
            "enabled": False
        })
        assert resp.status_code == 200
        
        data = resp.json()
        # Should return to pricing_configured since pricing was set
        assert data.get("status") == "pricing_configured", f"Expected status 'pricing_configured', got {data.get('status')}"
        assert data.get("go_live") is False
        
    def test_go_live_requires_certification(self, api_client):
        """Go-live without certification should fail"""
        # Reset and only save credentials (no certification)
        api_client.post(f"{BASE_URL}/api/supplier-onboarding/reset/wtatil")
        api_client.post(f"{BASE_URL}/api/supplier-onboarding/credentials", json={
            "supplier_code": "wtatil",
            "credentials": {
                "base_url": "https://b2b-api-test.wtatil.com",
                "application_secret_key": "test_secret",
                "username": "test_user",
                "password": "test_pass",
                "agency_id": "12345"
            }
        })
        
        resp = api_client.post(f"{BASE_URL}/api/supplier-onboarding/go-live/wtatil", json={
            "enabled": True
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data, "Expected error when trying to go-live without certification"


class TestActivityTimelineLogging:
    """Test that go-live action logs an event to activity timeline"""
    
    def test_go_live_logs_timeline_event(self, api_client):
        """Go-live should log an event to activity timeline"""
        # Re-enable go-live for the supplier
        resp = api_client.post(f"{BASE_URL}/api/supplier-onboarding/go-live/{TEST_SUPPLIER_PRICING}", json={
            "enabled": True
        })
        assert resp.status_code == 200
        
        # Wait a moment for event to be logged
        time.sleep(0.5)
        
        # Check activity timeline for the go-live event
        timeline_resp = api_client.get(f"{BASE_URL}/api/activity-timeline", params={
            "entity_type": "supplier",
            "entity_id": TEST_SUPPLIER_PRICING,
            "limit": 5
        })
        assert timeline_resp.status_code == 200, f"Expected 200 for timeline, got {timeline_resp.status_code}"
        
        timeline_data = timeline_resp.json()
        events = timeline_data.get("events", [])
        
        # Find the go-live event
        go_live_events = [e for e in events if e.get("action") == "supplier_go_live"]
        assert len(go_live_events) > 0, "Expected at least one supplier_go_live event in timeline"
        
        # Verify event details
        event = go_live_events[0]
        assert event.get("entity_type") == "supplier"
        assert event.get("entity_id") == TEST_SUPPLIER_PRICING
        
    def test_deactivate_logs_timeline_event(self, api_client):
        """Deactivating go-live should also log a timeline event"""
        # Disable go-live
        resp = api_client.post(f"{BASE_URL}/api/supplier-onboarding/go-live/{TEST_SUPPLIER_PRICING}", json={
            "enabled": False
        })
        assert resp.status_code == 200
        
        time.sleep(0.5)
        
        # Check for deactivation event
        timeline_resp = api_client.get(f"{BASE_URL}/api/activity-timeline", params={
            "entity_type": "supplier",
            "limit": 10
        })
        assert timeline_resp.status_code == 200
        
        timeline_data = timeline_resp.json()
        events = timeline_data.get("events", [])
        
        deactivate_events = [e for e in events if e.get("action") == "supplier_deactivated"]
        assert len(deactivate_events) > 0, "Expected supplier_deactivated event in timeline"


# ============================================================
# FULL WORKFLOW TESTS
# ============================================================

class TestFullOnboardingWorkflow:
    """Test complete onboarding workflow: credentials → validate → certify → pricing → go-live"""
    
    def test_full_workflow_for_juniper(self, api_client):
        """Run through the complete onboarding workflow for juniper supplier"""
        supplier = "juniper"
        
        # Step 0: Reset
        reset_resp = api_client.post(f"{BASE_URL}/api/supplier-onboarding/reset/{supplier}")
        assert reset_resp.status_code == 200
        
        # Step 1: Save credentials
        cred_resp = api_client.post(f"{BASE_URL}/api/supplier-onboarding/credentials", json={
            "supplier_code": supplier,
            "credentials": {
                "base_url": "https://xml-uat.bookingengine.es",
                "username": "juniper_test",
                "password": "juniper_pass_1234"
            }
        })
        assert cred_resp.status_code == 200
        cred_data = cred_resp.json()
        assert cred_data.get("status") == "credentials_saved"
        
        # Step 2: Health check
        health_resp = api_client.post(f"{BASE_URL}/api/supplier-onboarding/validate/{supplier}")
        assert health_resp.status_code == 200
        health_data = health_resp.json()
        assert health_data.get("overall") == "pass"
        assert len(health_data.get("checks", [])) == 4
        
        # Step 3: Certification
        cert_resp = api_client.post(f"{BASE_URL}/api/supplier-onboarding/certify/{supplier}")
        assert cert_resp.status_code == 200
        cert_data = cert_resp.json()
        assert cert_data.get("go_live_eligible") is True
        assert len(cert_data.get("results", [])) == 6
        
        # Verify status is certified
        detail_resp = api_client.get(f"{BASE_URL}/api/supplier-onboarding/detail/{supplier}")
        assert detail_resp.status_code == 200
        detail_data = detail_resp.json()
        assert detail_data.get("status") == "certified"
        
        # Step 4: Configure pricing
        pricing_resp = api_client.post(f"{BASE_URL}/api/supplier-onboarding/pricing-setup/{supplier}", json={
            "base_markup_pct": 15,
            "min_margin_pct": 6,
            "max_discount_pct": 20
        })
        assert pricing_resp.status_code == 200
        pricing_data = pricing_resp.json()
        assert pricing_data.get("status") == "pricing_configured"
        
        # Step 5: Go-live
        golive_resp = api_client.post(f"{BASE_URL}/api/supplier-onboarding/go-live/{supplier}", json={
            "enabled": True
        })
        assert golive_resp.status_code == 200
        golive_data = golive_resp.json()
        assert golive_data.get("status") == "live"
        assert golive_data.get("go_live") is True
        
        # Final verification
        final_detail = api_client.get(f"{BASE_URL}/api/supplier-onboarding/detail/{supplier}")
        assert final_detail.status_code == 200
        final_data = final_detail.json()
        assert final_data.get("status") == "live"
        assert final_data.get("go_live") is True
        assert final_data.get("pricing_config") is not None
        assert final_data["pricing_config"].get("base_markup_pct") == 15


# ============================================================
# ERROR HANDLING TESTS
# ============================================================

class TestPricingSetupErrors:
    """Test error handling for pricing setup endpoints"""
    
    def test_pricing_setup_unknown_supplier(self, api_client):
        """Pricing setup for unknown supplier should return error"""
        resp = api_client.get(f"{BASE_URL}/api/supplier-onboarding/pricing-setup/unknown_supplier")
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data
        
    def test_pricing_setup_save_unknown_supplier(self, api_client):
        """Save pricing for unknown supplier should return error"""
        resp = api_client.post(f"{BASE_URL}/api/supplier-onboarding/pricing-setup/unknown_supplier", json={
            "base_markup_pct": 10
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data


class TestAuthRequired:
    """Test authentication requirements"""
    
    def test_pricing_setup_requires_auth(self):
        """Pricing setup endpoint requires authentication"""
        resp = requests.get(f"{BASE_URL}/api/supplier-onboarding/pricing-setup/ratehawk")
        assert resp.status_code in [401, 403, 422]
        
    def test_go_live_requires_auth(self):
        """Go-live endpoint requires authentication"""
        resp = requests.post(f"{BASE_URL}/api/supplier-onboarding/go-live/ratehawk", json={"enabled": True})
        assert resp.status_code in [401, 403, 422]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
