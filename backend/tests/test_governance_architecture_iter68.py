"""
Enterprise Governance Architecture (10-Part) - Backend API Tests (Iteration 68)

Tests all 10 parts of the governance layer:
  P1 - RBAC System (6 roles, hierarchy)
  P2 - Permission Model (46 permissions, wildcards)
  P3 - Audit Logging (who/what/when/before/after)
  P4 - Secret Management (store/rotate/access log)
  P5 - Tenant Security (cross-tenant isolation)
  P6 - Compliance Logging (hash-chain integrity)
  P7 - Data Access Policies
  P8 - Security Alerting (suspicious activity detection)
  P9 - Admin Governance Panel (aggregated dashboard)
  P10 - Governance Roadmap (top 25 improvements + maturity score)

Test User: agent@acenta.test / agent123 (super_admin role)
API Base: /api/governance/*
"""

import os
import pytest
import requests
import uuid

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


@pytest.fixture(scope="module")
def auth_token():
    """Authenticate and get access token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "agent@acenta.test", "password": "agent123"},
    )
    if response.status_code == 200:
        data = response.json()
        # Token key is 'access_token' per main agent note
        return data.get("access_token") or data.get("token")
    pytest.fail(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def headers(auth_token):
    """Request headers with auth token"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json",
    }


@pytest.fixture(scope="module")
def no_auth_headers():
    """Headers without authentication"""
    return {"Content-Type": "application/json"}


class TestUnauthorizedAccess:
    """Test that endpoints return 401 without auth"""

    def test_rbac_roles_requires_auth(self, no_auth_headers):
        """GET /api/governance/rbac/roles requires authentication"""
        response = requests.get(
            f"{BASE_URL}/api/governance/rbac/roles", headers=no_auth_headers
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ RBAC roles endpoint requires authentication (401)")

    def test_audit_logs_requires_auth(self, no_auth_headers):
        """GET /api/governance/audit/logs requires authentication"""
        response = requests.get(
            f"{BASE_URL}/api/governance/audit/logs", headers=no_auth_headers
        )
        assert response.status_code == 401
        print("✓ Audit logs endpoint requires authentication (401)")

    def test_secrets_requires_auth(self, no_auth_headers):
        """GET /api/governance/secrets requires authentication"""
        response = requests.get(
            f"{BASE_URL}/api/governance/secrets", headers=no_auth_headers
        )
        assert response.status_code == 401
        print("✓ Secrets endpoint requires authentication (401)")


class TestPart1RBACSystem:
    """PART 1 — RBAC System with 6 hierarchical roles"""

    def test_seed_rbac(self, headers):
        """POST /api/governance/rbac/seed - Seeds 6 roles and 46 permissions"""
        response = requests.post(f"{BASE_URL}/api/governance/rbac/seed", headers=headers)
        assert response.status_code == 200, f"Seed RBAC failed: {response.text}"
        data = response.json()
        assert "roles_seeded" in data
        assert len(data["roles_seeded"]) == 6, f"Expected 6 roles, got {len(data['roles_seeded'])}"
        expected_roles = {"super_admin", "ops_admin", "finance_admin", "agency_admin", "agent", "support"}
        assert set(data["roles_seeded"]) == expected_roles
        assert data["permissions_seeded"] == 46, f"Expected 46 permissions, got {data['permissions_seeded']}"
        print(f"✓ RBAC seeded: 6 roles, 46 permissions - {data['roles_seeded']}")

    def test_list_roles(self, headers):
        """GET /api/governance/rbac/roles - Returns all 6 roles with hierarchy"""
        response = requests.get(f"{BASE_URL}/api/governance/rbac/roles", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 6, f"Expected at least 6 roles, got {len(data)}"

        # Verify hierarchy levels
        role_levels = {r["role"]: r.get("level", 0) for r in data}
        assert role_levels.get("super_admin", 0) >= role_levels.get("ops_admin", 0)
        assert role_levels.get("ops_admin", 0) >= role_levels.get("agent", 0)
        print(f"✓ Listed {len(data)} roles with hierarchy levels")

    def test_get_role_hierarchy(self, headers):
        """GET /api/governance/rbac/hierarchy - Returns role hierarchy tree sorted by level"""
        response = requests.get(f"{BASE_URL}/api/governance/rbac/hierarchy", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # Verify sorted by level descending
        levels = [r.get("level", 0) for r in data]
        assert levels == sorted(levels, reverse=True), "Hierarchy should be sorted by level descending"
        print(f"✓ Role hierarchy returned - {[r['role'] for r in data]}")


class TestPart2PermissionModel:
    """PART 2 — Fine-grained Permission Model (46 permissions with wildcard matching)"""

    def test_list_permissions(self, headers):
        """GET /api/governance/rbac/permissions - Returns all 46 permissions"""
        response = requests.get(f"{BASE_URL}/api/governance/rbac/permissions", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 46, f"Expected at least 46 permissions, got {len(data)}"

        # Verify permission structure
        sample = data[0]
        assert "code" in sample
        print(f"✓ Listed {len(data)} permissions")

    def test_update_role_permissions(self, headers):
        """PUT /api/governance/rbac/roles - Update role permissions"""
        response = requests.put(
            f"{BASE_URL}/api/governance/rbac/roles",
            headers=headers,
            json={
                "role": "support",
                "permissions": ["booking.view", "finance.view", "reports.view"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("role") == "support"
        assert "permissions" in data
        print("✓ Updated support role permissions")

    def test_resolve_user_permissions(self, headers):
        """GET /api/governance/rbac/user-permissions - Resolve effective permissions with inheritance"""
        response = requests.get(
            f"{BASE_URL}/api/governance/rbac/user-permissions",
            headers=headers,
            params={"user_email": "agent@acenta.test"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "direct_roles" in data
        assert "effective_roles" in data
        assert "permissions" in data
        # super_admin should have wildcard permission
        assert data.get("has_wildcard", False), "super_admin should have wildcard permission"
        print(f"✓ Resolved permissions - direct roles: {data['direct_roles']}, has_wildcard: {data['has_wildcard']}")

    def test_check_permission(self, headers):
        """GET /api/governance/rbac/check-permission - Check specific permission for user"""
        response = requests.get(
            f"{BASE_URL}/api/governance/rbac/check-permission",
            headers=headers,
            params={"user_email": "agent@acenta.test", "permission": "governance.rbac.manage"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "granted" in data
        assert data["granted"] is True, "super_admin should have all permissions"
        print(f"✓ Permission check - governance.rbac.manage: {data['granted']}")


class TestPart3AuditLogging:
    """PART 3 — Audit Logging (who/what/when/before/after)"""

    def test_search_audit_logs(self, headers):
        """GET /api/governance/audit/logs - Search audit logs"""
        response = requests.get(
            f"{BASE_URL}/api/governance/audit/logs",
            headers=headers,
            params={"limit": 10},
        )
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data
        print(f"✓ Audit logs retrieved - total: {data['total']}, items: {len(data['items'])}")

    def test_get_audit_stats(self, headers):
        """GET /api/governance/audit/stats - Get audit statistics"""
        response = requests.get(
            f"{BASE_URL}/api/governance/audit/stats",
            headers=headers,
            params={"days": 30},
        )
        assert response.status_code == 200
        data = response.json()
        assert "period_days" in data
        assert "total_events" in data
        assert "by_category" in data
        print(f"✓ Audit stats - {data['total_events']} events in {data['period_days']} days")


class TestPart4SecretManagement:
    """PART 4 — Secret Management (store/rotate/access log)"""

    def test_store_secret(self, headers):
        """POST /api/governance/secrets - Store a new secret"""
        secret_name = f"TEST_api_key_{uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{BASE_URL}/api/governance/secrets",
            headers=headers,
            json={
                "name": secret_name,
                "value": "sk_test_secret_value_12345",
                "secret_type": "api_key",
                "description": "Test API key for governance testing",
                "rotation_days": 30,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("name") == secret_name
        assert data.get("action") == "created"
        assert data.get("version") == 1
        print(f"✓ Secret stored: {secret_name}, version: {data['version']}")
        return secret_name

    def test_rotate_secret(self, headers):
        """POST /api/governance/secrets - Rotate existing secret (version increments)"""
        secret_name = f"TEST_rotate_{uuid.uuid4().hex[:8]}"

        # Create initial secret
        requests.post(
            f"{BASE_URL}/api/governance/secrets",
            headers=headers,
            json={
                "name": secret_name,
                "value": "initial_value",
                "secret_type": "api_key",
            },
        )

        # Rotate the secret
        response = requests.post(
            f"{BASE_URL}/api/governance/secrets",
            headers=headers,
            json={
                "name": secret_name,
                "value": "rotated_value_new",
                "secret_type": "api_key",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("action") == "rotated"
        assert data.get("version") >= 2
        print(f"✓ Secret rotated: {secret_name}, new version: {data['version']}")

    def test_list_secrets(self, headers):
        """GET /api/governance/secrets - List secrets (values masked)"""
        response = requests.get(f"{BASE_URL}/api/governance/secrets", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # Verify values are not exposed in list
        for secret in data:
            assert "encrypted_value" not in secret, "Encrypted value should not be exposed"
        print(f"✓ Listed {len(data)} secrets (values masked)")

    def test_get_secret_value(self, headers):
        """GET /api/governance/secrets/{name}/value - Retrieve secret value"""
        # Create a test secret first
        secret_name = f"TEST_retrieve_{uuid.uuid4().hex[:8]}"
        secret_value = "my_secret_test_value_xyz"

        requests.post(
            f"{BASE_URL}/api/governance/secrets",
            headers=headers,
            json={"name": secret_name, "value": secret_value, "secret_type": "api_key"},
        )

        # Retrieve the value
        response = requests.get(
            f"{BASE_URL}/api/governance/secrets/{secret_name}/value",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("name") == secret_name
        assert data.get("value") == secret_value
        print(f"✓ Secret value retrieved: {secret_name}")

    def test_delete_secret(self, headers):
        """DELETE /api/governance/secrets/{name} - Soft delete a secret"""
        secret_name = f"TEST_delete_{uuid.uuid4().hex[:8]}"

        # Create secret
        requests.post(
            f"{BASE_URL}/api/governance/secrets",
            headers=headers,
            json={"name": secret_name, "value": "to_be_deleted", "secret_type": "api_key"},
        )

        # Delete it
        response = requests.delete(
            f"{BASE_URL}/api/governance/secrets/{secret_name}",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("deleted") is True
        print(f"✓ Secret soft-deleted: {secret_name}")

    def test_check_rotation_status(self, headers):
        """GET /api/governance/secrets/rotation/status - Check rotation status"""
        response = requests.get(
            f"{BASE_URL}/api/governance/secrets/rotation/status",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # Verify rotation status structure
        for item in data:
            assert "name" in item
            assert "needs_rotation" in item
            assert "status" in item
        print(f"✓ Rotation status checked for {len(data)} secrets")


class TestPart5TenantSecurity:
    """PART 5 — Tenant Security (cross-tenant isolation)"""

    def test_tenant_isolation_report(self, headers):
        """GET /api/governance/tenant/isolation-report - Tenant isolation health report"""
        response = requests.get(
            f"{BASE_URL}/api/governance/tenant/isolation-report",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "isolation_score" in data
        assert "violations_detected" in data
        assert "collection_isolation" in data
        print(f"✓ Tenant isolation report - score: {data['isolation_score']}%, violations: {data['violations_detected']}")

    def test_list_violations(self, headers):
        """GET /api/governance/tenant/violations - List violations"""
        response = requests.get(
            f"{BASE_URL}/api/governance/tenant/violations",
            headers=headers,
            params={"limit": 10},
        )
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data
        print(f"✓ Tenant violations - total: {data['total']}")

    def test_validate_access_same_org(self, headers):
        """POST /api/governance/tenant/validate-access - Same org access allowed"""
        # Get current user's org_id by checking profile or using test org
        response = requests.post(
            f"{BASE_URL}/api/governance/tenant/validate-access",
            headers=headers,
            json={
                "target_org_id": "test_org_id",  # Will compare with requesting user's org
                "resource_type": "bookings",
                "action": "read",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "allowed" in data
        print(f"✓ Tenant access validation - allowed: {data['allowed']}")

    def test_validate_access_cross_org_blocked(self, headers):
        """POST /api/governance/tenant/validate-access - Cross-org access blocked"""
        response = requests.post(
            f"{BASE_URL}/api/governance/tenant/validate-access",
            headers=headers,
            json={
                "target_org_id": "DIFFERENT_ORG_ID_12345",
                "resource_type": "payments",
                "action": "read",
            },
        )
        assert response.status_code == 200
        data = response.json()
        # Cross-org should be blocked
        assert data.get("allowed") is False, "Cross-org access should be blocked"
        print("✓ Cross-org access correctly blocked")


class TestPart6ComplianceLogging:
    """PART 6 — Compliance Logging (hash-chain integrity)"""

    def test_log_financial_operation(self, headers):
        """POST /api/governance/compliance/log - Log financial operation with hash chain"""
        response = requests.post(
            f"{BASE_URL}/api/governance/compliance/log",
            headers=headers,
            json={
                "operation_type": "payment_received",
                "amount": 1250.50,
                "currency": "EUR",
                "booking_id": f"BK_{uuid.uuid4().hex[:8]}",
                "payment_id": f"PAY_{uuid.uuid4().hex[:8]}",
                "counterparty": "Test Customer",
                "tax_details": {"vat_rate": 0.19, "vat_amount": 199.58},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "compliance_id" in data
        assert "sequence" in data
        assert "entry_hash" in data
        print(f"✓ Compliance log created - sequence: {data['sequence']}, hash: {data['entry_hash'][:16]}...")

    def test_search_compliance_logs(self, headers):
        """GET /api/governance/compliance/logs - Search compliance logs"""
        response = requests.get(
            f"{BASE_URL}/api/governance/compliance/logs",
            headers=headers,
            params={"limit": 20},
        )
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data
        print(f"✓ Compliance logs - total: {data['total']}, items: {len(data['items'])}")

    def test_verify_chain_integrity(self, headers):
        """GET /api/governance/compliance/verify-chain - Verify hash chain integrity"""
        response = requests.get(
            f"{BASE_URL}/api/governance/compliance/verify-chain",
            headers=headers,
            params={"last_n": 100},
        )
        assert response.status_code == 200
        data = response.json()
        assert "verified" in data
        assert "status" in data
        assert "entries_checked" in data
        print(f"✓ Chain integrity - verified: {data['verified']}, status: {data['status']}, entries: {data['entries_checked']}")

    def test_compliance_summary(self, headers):
        """GET /api/governance/compliance/summary - Get compliance summary"""
        response = requests.get(
            f"{BASE_URL}/api/governance/compliance/summary",
            headers=headers,
            params={"days": 90},
        )
        assert response.status_code == 200
        data = response.json()
        assert "period_days" in data
        assert "total_entries" in data
        assert "chain_integrity" in data
        print(f"✓ Compliance summary - {data['total_entries']} entries in {data['period_days']} days, chain: {data['chain_integrity']}")


class TestPart7DataAccessPolicies:
    """PART 7 — Data Access Policies"""

    def test_seed_default_policies(self, headers):
        """POST /api/governance/data-policies/seed - Seed 4 default policies"""
        response = requests.post(
            f"{BASE_URL}/api/governance/data-policies/seed",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "policies_seeded" in data
        print(f"✓ Data policies seeded: {data['policies_seeded']}")

    def test_list_data_policies(self, headers):
        """GET /api/governance/data-policies - List data access policies"""
        response = requests.get(
            f"{BASE_URL}/api/governance/data-policies",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Listed {len(data)} data access policies")

    def test_evaluate_data_access(self, headers):
        """POST /api/governance/data-policies/evaluate - Evaluate data access"""
        response = requests.post(
            f"{BASE_URL}/api/governance/data-policies/evaluate",
            headers=headers,
            json={
                "resource": "bookings",
                "action": "read",
                "context": {"user_roles": ["super_admin"]},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "allowed" in data
        assert "reason" in data
        print(f"✓ Data access evaluated - allowed: {data['allowed']}, reason: {data['reason']}")


class TestPart8SecurityAlerting:
    """PART 8 — Security Alerting (suspicious activity detection)"""

    def test_create_security_alert(self, headers):
        """POST /api/governance/security/alerts - Create security alert"""
        response = requests.post(
            f"{BASE_URL}/api/governance/security/alerts",
            headers=headers,
            json={
                "alert_type": "suspicious_login",
                "severity": "medium",
                "title": "TEST: Suspicious login detected",
                "description": "Multiple login attempts from new IP",
                "actor_email": "test@example.com",
                "source_ip": "192.168.1.100",
                "evidence": {"attempts": 5, "timeframe": "1h"},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "alert_id" in data
        assert data.get("status") == "open"
        print(f"✓ Security alert created - ID: {data['alert_id']}, status: {data['status']}")
        return data["alert_id"]

    def test_list_security_alerts(self, headers):
        """GET /api/governance/security/alerts - List security alerts"""
        response = requests.get(
            f"{BASE_URL}/api/governance/security/alerts",
            headers=headers,
            params={"limit": 10},
        )
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data
        print(f"✓ Security alerts - total: {data['total']}")
        return data["items"][0]["alert_id"] if data["items"] else None

    def test_acknowledge_alert(self, headers):
        """POST /api/governance/security/alerts/{id}/acknowledge - Acknowledge alert"""
        # Create an alert first
        create_resp = requests.post(
            f"{BASE_URL}/api/governance/security/alerts",
            headers=headers,
            json={
                "alert_type": "brute_force_attempt",
                "severity": "high",
                "title": "TEST: Brute force detected",
                "actor_email": "attacker@test.com",
            },
        )
        alert_id = create_resp.json().get("alert_id")

        # Acknowledge it
        response = requests.post(
            f"{BASE_URL}/api/governance/security/alerts/{alert_id}/acknowledge",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("acknowledged") is True
        print(f"✓ Alert acknowledged - ID: {alert_id}")

    def test_resolve_alert(self, headers):
        """POST /api/governance/security/alerts/{id}/resolve - Resolve alert"""
        # Create an alert
        create_resp = requests.post(
            f"{BASE_URL}/api/governance/security/alerts",
            headers=headers,
            json={
                "alert_type": "privilege_escalation",
                "severity": "critical",
                "title": "TEST: Privilege escalation",
            },
        )
        alert_id = create_resp.json().get("alert_id")

        # Resolve it
        response = requests.post(
            f"{BASE_URL}/api/governance/security/alerts/{alert_id}/resolve",
            headers=headers,
            params={"resolution": "False positive - authorized admin action"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("resolved") is True
        print(f"✓ Alert resolved - ID: {alert_id}")

    def test_security_dashboard(self, headers):
        """GET /api/governance/security/dashboard - Security dashboard"""
        response = requests.get(
            f"{BASE_URL}/api/governance/security/dashboard",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "open_alerts" in data
        assert "total_alerts_this_week" in data
        assert "alert_types" in data
        print(f"✓ Security dashboard - open: {data['open_alerts']}, this week: {data['total_alerts_this_week']}")


class TestPart9AdminGovernancePanel:
    """PART 9 — Admin Governance Panel (aggregated dashboard)"""

    def test_governance_overview(self, headers):
        """GET /api/governance/panel/overview - Governance overview panel"""
        response = requests.get(
            f"{BASE_URL}/api/governance/panel/overview",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()

        # Verify all sections present
        assert "rbac" in data
        assert "audit" in data
        assert "security" in data
        assert "secrets" in data
        assert "tenant_isolation" in data
        assert "compliance" in data

        print(f"✓ Governance overview - roles: {data['rbac']['total_roles']}, "
              f"open alerts: {data['security']['open_alerts']}, "
              f"secrets: {data['secrets']['total_secrets']}")

    def test_inspect_user_profile(self, headers):
        """GET /api/governance/panel/user/{email} - Inspect user governance profile"""
        response = requests.get(
            f"{BASE_URL}/api/governance/panel/user/agent@acenta.test",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert "permissions" in data
        assert "recent_activity" in data

        user = data["user"]
        assert user.get("email") == "agent@acenta.test"
        print(f"✓ User profile inspected - roles: {user.get('roles')}, permissions count: {len(data['permissions'].get('permissions', []))}")


class TestPart10GovernanceRoadmap:
    """PART 10 — Governance Roadmap (top 25 improvements + maturity score)"""

    def test_governance_roadmap(self, headers):
        """GET /api/governance/roadmap - Top 25 improvements and maturity score"""
        response = requests.get(f"{BASE_URL}/api/governance/roadmap", headers=headers)
        assert response.status_code == 200
        data = response.json()

        # Verify maturity score
        assert "security_maturity_score" in data
        score = data["security_maturity_score"]
        assert "score" in score
        assert "max_score" in score
        assert "percentage" in score
        assert "grade" in score

        # Verify roadmap
        assert "top_25_improvements" in data
        improvements = data["top_25_improvements"]
        assert len(improvements) == 25, f"Expected 25 improvements, got {len(improvements)}"

        # Verify improvement structure
        first = improvements[0]
        assert "rank" in first
        assert "category" in first
        assert "title" in first
        assert "impact" in first
        assert "effort" in first
        assert "status" in first

        # Verify risk analysis
        assert "risk_analysis" in data
        risks = data["risk_analysis"]
        assert "critical_risks" in risks
        assert "high_risks" in risks
        assert "medium_risks" in risks

        print(f"✓ Governance roadmap - maturity score: {score['percentage']}% (Grade {score['grade']}), "
              f"improvements: {len(improvements)}, critical risks: {len(risks['critical_risks'])}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
