"""
Tests for Entitlement Projection Engine (V1)
  - GET /api/onboarding/plans
  - GET /api/admin/tenants/{tenant_id}/features
  - PATCH /api/admin/tenants/{tenant_id}/plan
  - PATCH /api/admin/tenants/{tenant_id}/add-ons
  - GET /api/tenant/features
  - GET /api/tenant/entitlements
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "admin123"
AGENT_EMAIL = "agent@acenta.test"
AGENT_PASSWORD = "agent123"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def admin_token(api_client):
    """Authenticate as admin and get token."""
    resp = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if resp.status_code == 200:
        data = resp.json()
        return data.get("access_token") or data.get("token")
    pytest.skip(f"Admin login failed: {resp.status_code} - {resp.text}")


@pytest.fixture(scope="module")
def admin_client(api_client, admin_token):
    """Session with admin auth header."""
    api_client.headers.update({"Authorization": f"Bearer {admin_token}"})
    return api_client


@pytest.fixture(scope="module")
def agent_token(api_client):
    """Authenticate as agent and get token."""
    # Create new session for agent
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    resp = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": AGENT_EMAIL,
        "password": AGENT_PASSWORD
    })
    if resp.status_code == 200:
        data = resp.json()
        return data.get("access_token") or data.get("token")
    pytest.skip(f"Agent login failed: {resp.status_code} - {resp.text}")


@pytest.fixture(scope="module")
def agent_client(agent_token):
    """Session with agent auth header."""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {agent_token}"
    })
    return session


class TestOnboardingPlans:
    """Tests for GET /api/onboarding/plans - Plan catalog endpoint."""

    def test_plans_returns_200(self, api_client):
        """GET /api/onboarding/plans should return 200."""
        resp = api_client.get(f"{BASE_URL}/api/onboarding/plans")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    def test_plans_contains_plans_array(self, api_client):
        """Response should contain 'plans' array."""
        resp = api_client.get(f"{BASE_URL}/api/onboarding/plans")
        data = resp.json()
        assert "plans" in data, "Response should contain 'plans' key"
        assert isinstance(data["plans"], list), "'plans' should be a list"

    def test_plans_has_starter_pro_enterprise(self, api_client):
        """Plan catalog should include starter, pro, enterprise."""
        resp = api_client.get(f"{BASE_URL}/api/onboarding/plans")
        data = resp.json()
        plan_keys = [p.get("key") or p.get("name") for p in data["plans"]]
        assert "starter" in plan_keys, "Should include 'starter' plan"
        assert "pro" in plan_keys, "Should include 'pro' plan"
        assert "enterprise" in plan_keys, "Should include 'enterprise' plan"

    def test_plan_has_limits_and_usage_allowances(self, api_client):
        """Each plan should have limits and usage_allowances."""
        resp = api_client.get(f"{BASE_URL}/api/onboarding/plans")
        data = resp.json()
        
        for plan in data["plans"]:
            plan_name = plan.get("key") or plan.get("name")
            assert "limits" in plan, f"Plan '{plan_name}' should have 'limits'"
            assert "usage_allowances" in plan, f"Plan '{plan_name}' should have 'usage_allowances'"
            assert isinstance(plan["limits"], dict), f"Plan '{plan_name}' limits should be dict"
            assert isinstance(plan["usage_allowances"], dict), f"Plan '{plan_name}' usage_allowances should be dict"

    def test_starter_plan_has_correct_limits(self, api_client):
        """Starter plan should have expected limit values."""
        resp = api_client.get(f"{BASE_URL}/api/onboarding/plans")
        data = resp.json()
        
        starter = next((p for p in data["plans"] if (p.get("key") or p.get("name")) == "starter"), None)
        assert starter is not None, "Starter plan should exist"
        
        limits = starter.get("limits", {})
        assert "users.active" in limits, "Starter should have 'users.active' limit"
        assert limits["users.active"] == 2, f"Starter users.active should be 2, got {limits['users.active']}"

    def test_pro_plan_has_correct_limits(self, api_client):
        """Pro plan should have expected limit values."""
        resp = api_client.get(f"{BASE_URL}/api/onboarding/plans")
        data = resp.json()
        
        pro = next((p for p in data["plans"] if (p.get("key") or p.get("name")) == "pro"), None)
        assert pro is not None, "Pro plan should exist"
        
        limits = pro.get("limits", {})
        assert "users.active" in limits, "Pro should have 'users.active' limit"
        assert limits["users.active"] == 10, f"Pro users.active should be 10, got {limits['users.active']}"

    def test_plans_have_features_array(self, api_client):
        """Each plan should have features array."""
        resp = api_client.get(f"{BASE_URL}/api/onboarding/plans")
        data = resp.json()
        
        for plan in data["plans"]:
            plan_name = plan.get("key") or plan.get("name")
            assert "features" in plan, f"Plan '{plan_name}' should have 'features'"
            assert isinstance(plan["features"], list), f"Plan '{plan_name}' features should be list"
            assert len(plan["features"]) > 0, f"Plan '{plan_name}' should have at least one feature"


class TestAdminTenantFeatures:
    """Tests for admin tenant entitlement endpoints."""

    def test_admin_list_tenants(self, admin_client):
        """GET /api/admin/tenants should return list of tenants."""
        resp = admin_client.get(f"{BASE_URL}/api/admin/tenants")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "items" in data, "Response should have 'items'"
        assert isinstance(data["items"], list), "'items' should be a list"

    def test_get_tenant_features_returns_entitlement_projection(self, admin_client):
        """GET /api/admin/tenants/{tenant_id}/features should return entitlement projection."""
        # First get a tenant
        tenants_resp = admin_client.get(f"{BASE_URL}/api/admin/tenants")
        data = tenants_resp.json()
        if not data.get("items"):
            pytest.skip("No tenants available for testing")
        
        tenant_id = data["items"][0]["id"]
        
        resp = admin_client.get(f"{BASE_URL}/api/admin/tenants/{tenant_id}/features")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        feat_data = resp.json()
        # Verify projection fields exist
        assert "tenant_id" in feat_data, "Should have 'tenant_id'"
        assert "plan" in feat_data, "Should have 'plan'"
        assert "plan_label" in feat_data, "Should have 'plan_label'"
        assert "limits" in feat_data, "Should have 'limits'"
        assert "usage_allowances" in feat_data, "Should have 'usage_allowances'"
        assert "plan_catalog" in feat_data, "Should have 'plan_catalog'"

    def test_patch_tenant_plan_updates_entitlement(self, admin_client):
        """PATCH /api/admin/tenants/{tenant_id}/plan should update entitlement projection."""
        # First get a tenant
        tenants_resp = admin_client.get(f"{BASE_URL}/api/admin/tenants")
        data = tenants_resp.json()
        if not data.get("items"):
            pytest.skip("No tenants available for testing")
        
        tenant_id = data["items"][0]["id"]
        
        # Get current plan
        feat_resp = admin_client.get(f"{BASE_URL}/api/admin/tenants/{tenant_id}/features")
        current_plan = feat_resp.json().get("plan") or "starter"
        
        # Determine new plan to switch to
        new_plan = "pro" if current_plan != "pro" else "starter"
        
        # Patch plan
        patch_resp = admin_client.patch(
            f"{BASE_URL}/api/admin/tenants/{tenant_id}/plan",
            json={"plan": new_plan}
        )
        assert patch_resp.status_code == 200, f"Expected 200, got {patch_resp.status_code}: {patch_resp.text}"
        
        patch_data = patch_resp.json()
        assert patch_data.get("plan") == new_plan, f"Plan should be '{new_plan}', got {patch_data.get('plan')}"
        assert "limits" in patch_data, "Response should include 'limits'"
        assert "usage_allowances" in patch_data, "Response should include 'usage_allowances'"
        
        # Verify limits match expected for new plan
        limits = patch_data.get("limits", {})
        if new_plan == "pro":
            assert limits.get("users.active") == 10, f"Pro should have users.active=10, got {limits.get('users.active')}"
        elif new_plan == "starter":
            assert limits.get("users.active") == 2, f"Starter should have users.active=2, got {limits.get('users.active')}"
        
        # Restore original plan
        admin_client.patch(
            f"{BASE_URL}/api/admin/tenants/{tenant_id}/plan",
            json={"plan": current_plan}
        )

    def test_patch_tenant_add_ons_preserves_entitlement_shape(self, admin_client):
        """PATCH /api/admin/tenants/{tenant_id}/add-ons should preserve effective features and entitlement shape."""
        # First get a tenant
        tenants_resp = admin_client.get(f"{BASE_URL}/api/admin/tenants")
        data = tenants_resp.json()
        if not data.get("items"):
            pytest.skip("No tenants available for testing")
        
        tenant_id = data["items"][0]["id"]
        
        # Get current add-ons
        feat_resp = admin_client.get(f"{BASE_URL}/api/admin/tenants/{tenant_id}/features")
        current_add_ons = feat_resp.json().get("add_ons", [])
        
        # Add a test add-on (e.g., 'b2b' if not already present)
        test_addon = "b2b" if "b2b" not in current_add_ons else "ops"
        new_add_ons = list(set(current_add_ons + [test_addon]))
        
        # Patch add-ons
        patch_resp = admin_client.patch(
            f"{BASE_URL}/api/admin/tenants/{tenant_id}/add-ons",
            json={"add_ons": new_add_ons}
        )
        assert patch_resp.status_code == 200, f"Expected 200, got {patch_resp.status_code}: {patch_resp.text}"
        
        patch_data = patch_resp.json()
        # Verify entitlement shape is preserved
        assert "tenant_id" in patch_data, "Response should have 'tenant_id'"
        assert "plan" in patch_data, "Response should have 'plan'"
        assert "plan_label" in patch_data, "Response should have 'plan_label'"
        assert "add_ons" in patch_data, "Response should have 'add_ons'"
        assert "features" in patch_data, "Response should have 'features'"
        assert "limits" in patch_data, "Response should have 'limits'"
        assert "usage_allowances" in patch_data, "Response should have 'usage_allowances'"
        assert "source" in patch_data, "Response should have 'source'"
        
        # Verify add-on is in add_ons list
        assert test_addon in patch_data.get("add_ons", []), f"'{test_addon}' should be in add_ons"
        
        # Verify add-on is in effective features
        assert test_addon in patch_data.get("features", []), f"'{test_addon}' should be in features"
        
        # Restore original add-ons
        admin_client.patch(
            f"{BASE_URL}/api/admin/tenants/{tenant_id}/add-ons",
            json={"add_ons": current_add_ons}
        )


class TestTenantSelfServiceEntitlements:
    """Tests for tenant self-service entitlement endpoints."""

    def test_tenant_features_returns_projection(self, agent_client):
        """GET /api/tenant/features should return canonical projection for current tenant."""
        resp = agent_client.get(f"{BASE_URL}/api/tenant/features")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert "tenant_id" in data, "Should have 'tenant_id'"
        assert "plan" in data, "Should have 'plan'"
        assert "limits" in data, "Should have 'limits'"
        assert "usage_allowances" in data, "Should have 'usage_allowances'"
        assert "features" in data, "Should have 'features'"
        assert "source" in data, "Should have 'source'"

    def test_tenant_entitlements_alias(self, agent_client):
        """GET /api/tenant/entitlements should be alias for /api/tenant/features."""
        feat_resp = agent_client.get(f"{BASE_URL}/api/tenant/features")
        ent_resp = agent_client.get(f"{BASE_URL}/api/tenant/entitlements")
        
        assert ent_resp.status_code == 200, f"Expected 200, got {ent_resp.status_code}: {ent_resp.text}"
        
        feat_data = feat_resp.json()
        ent_data = ent_resp.json()
        
        # Both should have same structure
        assert feat_data.get("tenant_id") == ent_data.get("tenant_id")
        assert feat_data.get("plan") == ent_data.get("plan")
        assert feat_data.get("limits") == ent_data.get("limits")

    def test_tenant_features_has_valid_plan(self, agent_client):
        """Tenant features should have a valid plan (starter, pro, or enterprise)."""
        resp = agent_client.get(f"{BASE_URL}/api/tenant/features")
        data = resp.json()
        
        plan = data.get("plan")
        if plan is not None:
            assert plan in ["starter", "pro", "enterprise"], f"Plan '{plan}' is not valid"


class TestInvalidPlanHandling:
    """Tests for error handling on invalid plan/add-on operations."""

    def test_patch_invalid_plan_returns_422(self, admin_client):
        """PATCH /api/admin/tenants/{tenant_id}/plan with invalid plan should return 422."""
        # First get a tenant
        tenants_resp = admin_client.get(f"{BASE_URL}/api/admin/tenants")
        data = tenants_resp.json()
        if not data.get("items"):
            pytest.skip("No tenants available for testing")
        
        tenant_id = data["items"][0]["id"]
        
        resp = admin_client.patch(
            f"{BASE_URL}/api/admin/tenants/{tenant_id}/plan",
            json={"plan": "invalid_plan_xyz"}
        )
        assert resp.status_code == 422, f"Expected 422 for invalid plan, got {resp.status_code}"

    def test_patch_invalid_addon_returns_422(self, admin_client):
        """PATCH /api/admin/tenants/{tenant_id}/add-ons with invalid add-on should return 422."""
        # First get a tenant
        tenants_resp = admin_client.get(f"{BASE_URL}/api/admin/tenants")
        data = tenants_resp.json()
        if not data.get("items"):
            pytest.skip("No tenants available for testing")
        
        tenant_id = data["items"][0]["id"]
        
        resp = admin_client.patch(
            f"{BASE_URL}/api/admin/tenants/{tenant_id}/add-ons",
            json={"add_ons": ["invalid_addon_xyz_123"]}
        )
        assert resp.status_code == 422, f"Expected 422 for invalid add-on, got {resp.status_code}"
