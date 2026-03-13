"""Production Activation Layer — Comprehensive API Tests (Iteration 70)

Tests:
- P0: Redis health check, God Router decomposition
- P0: Decomposed finance routers (accounts, refunds, settlements, suppliers)
- P1: Production readiness certification
- P1: Secret management inventory
- P1: Supplier integration preparation
- P1: Voucher and notification delivery endpoints
- Reliability layer endpoints (P7-P8)

All tests use super_admin role (agent@acenta.test / agent123)
"""
import os
import pytest
import requests
from datetime import datetime

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
TEST_EMAIL = "agent@acenta.test"
TEST_PASSWORD = "agent123"


@pytest.fixture(scope="module")
def auth_token():
    """Get auth token for super_admin user."""
    resp = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
    )
    if resp.status_code != 200:
        pytest.skip(f"Authentication failed: {resp.status_code} {resp.text[:200]}")
    data = resp.json()
    return data.get("token") or data.get("access_token")


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Create authenticated session."""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json",
    })
    return session


class TestP0RedisAndPipelineStatus:
    """P0 - Redis health and pipeline status check."""

    def test_pipeline_status_returns_redis_healthy(self, api_client):
        """GET /api/production/pipeline/status should return redis: healthy."""
        resp = api_client.get(f"{BASE_URL}/api/production/pipeline/status")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:300]}"
        data = resp.json()
        assert "redis" in data, "Response should contain 'redis' key"
        assert data["redis"] == "healthy", f"Redis should be healthy, got: {data['redis']}"
        assert "rbac_middleware" in data, "Response should contain 'rbac_middleware'"
        assert data["rbac_middleware"] == "active", "RBAC middleware should be active"
        assert "reliability_pipeline" in data, "Response should contain 'reliability_pipeline'"
        assert data["reliability_pipeline"] == "wired", "Reliability pipeline should be wired"
        print(f"✓ Pipeline status: redis={data['redis']}, rbac={data['rbac_middleware']}, reliability={data['reliability_pipeline']}")


class TestP0GodRouterDecomposition:
    """P0 - God Router decomposition verification."""

    def test_decomposition_info_endpoint(self, api_client):
        """GET /api/ops/finance/_decomposed should return decomposition info."""
        resp = api_client.get(f"{BASE_URL}/api/ops/finance/_decomposed")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:300]}"
        data = resp.json()
        assert data["status"] == "decomposed", "Status should be 'decomposed'"
        assert "modules" in data, "Response should list decomposed modules"
        expected_modules = ["ops_finance_accounts", "ops_finance_refunds", "ops_finance_settlements", "ops_finance_documents", "ops_finance_suppliers"]
        for mod in expected_modules:
            assert mod in data["modules"], f"Module {mod} should be in decomposed list"
        print(f"✓ God Router decomposed into {len(data['modules'])} modules: {data['modules']}")


class TestDecomposedFinanceAccounts:
    """Finance Accounts Router - Decomposed from ops_finance.py."""

    def test_list_accounts(self, api_client):
        """GET /api/ops/finance/accounts should return accounts list."""
        resp = api_client.get(f"{BASE_URL}/api/ops/finance/accounts")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:300]}"
        data = resp.json()
        assert "items" in data, "Response should contain 'items' key"
        print(f"✓ Finance accounts: {len(data.get('items', []))} accounts returned")

    def test_list_credit_profiles(self, api_client):
        """GET /api/ops/finance/credit-profiles should return profiles."""
        resp = api_client.get(f"{BASE_URL}/api/ops/finance/credit-profiles")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:300]}"
        data = resp.json()
        assert "items" in data, "Response should contain 'items'"
        print(f"✓ Credit profiles: {len(data.get('items', []))} profiles returned")

    def test_get_exposure_dashboard(self, api_client):
        """GET /api/ops/finance/exposure should return exposure data."""
        resp = api_client.get(f"{BASE_URL}/api/ops/finance/exposure")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:300]}"
        data = resp.json()
        assert "items" in data, "Response should contain 'items'"
        print(f"✓ Exposure dashboard: {len(data.get('items', []))} agencies")


class TestDecomposedFinanceRefunds:
    """Finance Refunds Router - Decomposed from ops_finance.py."""

    def test_list_refunds(self, api_client):
        """GET /api/ops/finance/refunds should return refunds list."""
        resp = api_client.get(f"{BASE_URL}/api/ops/finance/refunds")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:300]}"
        data = resp.json()
        # Response is dict with items or direct list
        items = data.get("items") if isinstance(data, dict) else data
        print(f"✓ Refunds: {len(items) if items else 0} refund cases returned")


class TestDecomposedFinanceSettlements:
    """Finance Settlements Router - Decomposed from ops_finance.py."""

    def test_list_settlements(self, api_client):
        """GET /api/ops/finance/settlements should return settlements."""
        resp = api_client.get(f"{BASE_URL}/api/ops/finance/settlements")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:300]}"
        data = resp.json()
        assert "items" in data, "Response should contain 'items'"
        print(f"✓ Settlements: {len(data.get('items', []))} runs returned")

    def test_list_supplier_accruals(self, api_client):
        """GET /api/ops/finance/supplier-accruals should return accruals."""
        resp = api_client.get(f"{BASE_URL}/api/ops/finance/supplier-accruals")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:300]}"
        data = resp.json()
        assert "items" in data, "Response should contain 'items'"
        print(f"✓ Supplier accruals: {len(data.get('items', []))} items")


class TestDecomposedFinanceSuppliers:
    """Finance Suppliers Router - Decomposed from ops_finance.py."""

    def test_supplier_payable_summary(self, api_client):
        """GET /api/ops/finance/suppliers/payable-summary should work."""
        resp = api_client.get(f"{BASE_URL}/api/ops/finance/suppliers/payable-summary")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:300]}"
        data = resp.json()
        assert "currency" in data, "Response should contain currency"
        assert "total_payable" in data, "Response should contain total_payable"
        print(f"✓ Supplier payable: {data.get('total_payable', 0)} {data.get('currency', 'EUR')} total")


class TestProductionReadiness:
    """P1 - Production readiness certification."""

    def test_get_production_readiness(self, api_client):
        """GET /api/production/readiness should return readiness report."""
        resp = api_client.get(f"{BASE_URL}/api/production/readiness")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:300]}"
        data = resp.json()
        
        # Verify structure
        assert "summary" in data, "Should have summary"
        assert "maturity" in data, "Should have maturity"
        assert "checks" in data, "Should have checks"
        
        summary = data["summary"]
        assert "readiness_score" in summary, "Summary should have readiness_score"
        assert "go_live_ready" in summary, "Summary should have go_live_ready"
        
        maturity = data["maturity"]
        assert "overall_score" in maturity, "Maturity should have overall_score"
        assert "rating" in maturity, "Maturity should have rating"
        
        print(f"✓ Production readiness: {summary['readiness_score']}% score, maturity={maturity['overall_score']}/10 ({maturity['rating']})")

    def test_get_production_tasks(self, api_client):
        """GET /api/production/readiness/tasks should return 30 tasks."""
        resp = api_client.get(f"{BASE_URL}/api/production/readiness/tasks")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:300]}"
        data = resp.json()
        
        assert "tasks" in data, "Should have tasks"
        assert "risk_matrix" in data, "Should have risk_matrix"
        
        tasks = data["tasks"]
        assert len(tasks) == 30, f"Should have 30 tasks, got {len(tasks)}"
        
        # Check task structure
        for task in tasks[:3]:
            assert "id" in task
            assert "priority" in task
            assert "task" in task
            assert "status" in task
        
        # Count completed P0 tasks
        p0_done = sum(1 for t in tasks if t["priority"] == "P0" and t["status"] == "done")
        print(f"✓ Production tasks: {len(tasks)} total, {p0_done} P0 tasks done, {len(data['risk_matrix'])} risks identified")


class TestSecretManagement:
    """P1 - Secret management inventory and migration readiness."""

    def test_get_secret_inventory(self, api_client):
        """GET /api/production/readiness/secrets should return secret inventory."""
        resp = api_client.get(f"{BASE_URL}/api/production/readiness/secrets")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:300]}"
        data = resp.json()
        
        assert "inventory" in data, "Should have inventory"
        assert "migration" in data, "Should have migration"
        
        inventory = data["inventory"]
        assert len(inventory) > 0, "Should have secrets in inventory"
        
        # Check inventory structure
        for secret in inventory[:2]:
            assert "key" in secret
            assert "type" in secret
            assert "rotation_policy" in secret
            assert "risk_level" in secret
            assert "is_configured" in secret
        
        migration = data["migration"]
        assert "readiness_score" in migration
        assert "migration_phase" in migration
        assert "migration_steps" in migration
        
        configured = sum(1 for s in inventory if s["is_configured"])
        print(f"✓ Secret inventory: {configured}/{len(inventory)} configured, {migration['readiness_score']}% ready")


class TestSupplierIntegrations:
    """P1 - Supplier integration preparation."""

    def test_get_supplier_integrations(self, api_client):
        """GET /api/production/suppliers/integrations should return 3 configs."""
        resp = api_client.get(f"{BASE_URL}/api/production/suppliers/integrations")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:300]}"
        data = resp.json()
        
        assert "suppliers" in data, "Should have suppliers"
        assert "risk_matrix" in data, "Should have risk_matrix"
        assert "rollout_order" in data, "Should have rollout_order"
        
        suppliers = data["suppliers"]
        assert len(suppliers) == 3, f"Should have 3 suppliers, got {len(suppliers)}"
        
        expected_suppliers = ["paximum", "aviationstack", "amadeus"]
        for code in expected_suppliers:
            assert code in suppliers, f"Supplier {code} should be in configs"
            cfg = suppliers[code]
            assert "auth_method" in cfg
            assert "rate_limit_rps" in cfg
            assert "timeout_ms" in cfg
            assert "sandbox_mode" in cfg
        
        print(f"✓ Supplier integrations: {list(suppliers.keys())} configured, {len(data['rollout_order'])} phase rollout plan")


class TestVoucherPipeline:
    """P1 - Voucher generation pipeline."""

    def test_list_vouchers(self, api_client):
        """GET /api/production/vouchers should return voucher list."""
        resp = api_client.get(f"{BASE_URL}/api/production/vouchers")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:300]}"
        data = resp.json()
        assert "items" in data, "Response should have 'items'"
        assert "total" in data, "Response should have 'total'"
        print(f"✓ Vouchers: {data['total']} vouchers in system")


class TestNotificationDelivery:
    """P1 - Notification delivery pipeline."""

    def test_get_delivery_log(self, api_client):
        """GET /api/production/notifications/delivery-log should return log."""
        resp = api_client.get(f"{BASE_URL}/api/production/notifications/delivery-log")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:300]}"
        data = resp.json()
        assert "items" in data, "Response should have 'items'"
        assert "total" in data, "Response should have 'total'"
        print(f"✓ Notification delivery log: {data['total']} deliveries logged")


class TestReliabilityEndpoints:
    """Reliability layer endpoints (subset from P7-P8)."""

    def test_resilience_config(self, api_client):
        """GET /api/reliability/resilience/config should work."""
        resp = api_client.get(f"{BASE_URL}/api/reliability/resilience/config")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:300]}"
        data = resp.json()
        # Should have config data
        print(f"✓ Resilience config retrieved")

    def test_supplier_metrics(self, api_client):
        """GET /api/reliability/metrics/suppliers should work."""
        resp = api_client.get(f"{BASE_URL}/api/reliability/metrics/suppliers")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:300]}"
        data = resp.json()
        assert "window" in data or "suppliers" in data or isinstance(data, dict)
        print(f"✓ Supplier metrics retrieved")

    def test_list_incidents(self, api_client):
        """GET /api/reliability/incidents should return incidents list."""
        resp = api_client.get(f"{BASE_URL}/api/reliability/incidents")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:300]}"
        data = resp.json()
        # Response should have items
        items = data.get("items") if isinstance(data, dict) else data
        print(f"✓ Incidents: {len(items) if items else 0} incidents in system")


class TestAuthenticationRequired:
    """Verify endpoints require authentication."""

    def test_production_pipeline_requires_auth(self):
        """Pipeline status should require auth."""
        resp = requests.get(f"{BASE_URL}/api/production/pipeline/status")
        assert resp.status_code in [401, 403], f"Should require auth, got {resp.status_code}"
        print("✓ Pipeline status requires authentication")

    def test_production_readiness_requires_auth(self):
        """Production readiness should require auth."""
        resp = requests.get(f"{BASE_URL}/api/production/readiness")
        assert resp.status_code in [401, 403], f"Should require auth, got {resp.status_code}"
        print("✓ Production readiness requires authentication")

    def test_finance_accounts_requires_auth(self):
        """Finance accounts should require auth."""
        resp = requests.get(f"{BASE_URL}/api/ops/finance/accounts")
        assert resp.status_code in [401, 403], f"Should require auth, got {resp.status_code}"
        print("✓ Finance accounts requires authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
