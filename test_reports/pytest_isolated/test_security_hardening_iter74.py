"""
Security Hardening Sprint - Iteration 74 Backend Tests

Tests for the 10-part security hardening sprint:
1. GET /api/hardening/security/secrets - Enhanced v2 secret audit
2. GET /api/hardening/security/jwt - JWT security verification (8 checks)
3. GET /api/hardening/security/tenant-isolation - Tenant isolation for 20 collections
4. GET /api/hardening/security/rbac - RBAC permission audit
5. GET /api/hardening/security/api-keys - API key management audit
6. GET /api/hardening/security/monitoring - Security monitoring with detection rules
7. GET /api/hardening/security/tests - 10 automated security tests
8. GET /api/hardening/security/metrics - Security metrics summary
9. GET /api/hardening/security/readiness - Security readiness score >=8.5
10. GET /api/hardening/activation/certification - GO decision with >=8.5 production readiness
11. Verify JWT_SECRET is strong (not 'please_rotate')
12. Verify CORS is whitelisted (not '*')
13. Verify STRIPE_WEBHOOK_SECRET is strong (not 'whsec_test')
"""
import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    BASE_URL = "https://syroce-query.preview.emergentagent.com"


class TestAuth:
    """Get auth token for testing"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Login as super_admin and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "agent@acenta.test",
            "password": "agent123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        return data["access_token"]


class TestSecuritySecretsEndpoint(TestAuth):
    """Part 1 & 2: Secret rotation & storage hardening audit"""
    
    def test_secrets_audit_returns_v2_format(self, auth_token):
        """GET /api/hardening/security/secrets returns enhanced v2 audit"""
        response = requests.get(
            f"{BASE_URL}/api/hardening/security/secrets",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Status {response.status_code}: {response.text}"
        data = response.json()
        
        # v2 format includes secrets array with strength_check
        assert "secrets" in data, "Missing secrets array"
        assert "summary" in data, "Missing summary"
        assert "storage" in data, "Missing storage (v2 includes storage hardening)"
        
        # Check summary has v2 fields
        summary = data["summary"]
        assert "production_ready_pct" in summary, "Missing production_ready_pct"
        assert "total" in summary
        assert "configured" in summary
        
        print(f"PASS: Secrets audit v2 - {summary['configured']}/{summary['total']} secrets configured, {summary['production_ready_pct']}% production ready")
    
    def test_secrets_have_strength_checks(self, auth_token):
        """Each secret has strength_check in v2 format"""
        response = requests.get(
            f"{BASE_URL}/api/hardening/security/secrets",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        for secret in data["secrets"]:
            assert "strength_check" in secret, f"Secret {secret['name']} missing strength_check"
            sc = secret["strength_check"]
            assert "min_length" in sc, f"Secret {secret['name']} missing min_length"
            assert "actual_length" in sc, f"Secret {secret['name']} missing actual_length"
            assert "meets_length" in sc, f"Secret {secret['name']} missing meets_length"
        
        print(f"PASS: All {len(data['secrets'])} secrets have strength_check")
    
    def test_jwt_secret_is_strong(self, auth_token):
        """JWT_SECRET should be strong (not default 'please_rotate')"""
        response = requests.get(
            f"{BASE_URL}/api/hardening/security/secrets",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        jwt_secret = next((s for s in data["secrets"] if s["name"] == "JWT_SECRET"), None)
        assert jwt_secret is not None, "JWT_SECRET not found in audit"
        
        # Should be strong and production ready
        assert jwt_secret["status"] == "strong", f"JWT_SECRET status is {jwt_secret['status']}, expected 'strong'"
        assert jwt_secret["is_production_ready"] == True, "JWT_SECRET should be production ready"
        assert jwt_secret["risk"] == "low", f"JWT_SECRET risk is {jwt_secret['risk']}, expected 'low'"
        
        # Strength check should pass
        sc = jwt_secret["strength_check"]
        assert sc["meets_length"] == True, "JWT_SECRET doesn't meet minimum length"
        assert sc["actual_length"] >= 32, f"JWT_SECRET length {sc['actual_length']} < 32"
        assert sc["has_entropy"] == True, "JWT_SECRET lacks entropy"
        
        print(f"PASS: JWT_SECRET is strong - length {sc['actual_length']}, meets_length=True, has_entropy=True")
    
    def test_cors_is_whitelisted(self, auth_token):
        """CORS_ORIGINS should be whitelisted (not wildcard '*')"""
        response = requests.get(
            f"{BASE_URL}/api/hardening/security/secrets",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        cors = next((s for s in data["secrets"] if s["name"] == "CORS_ORIGINS"), None)
        assert cors is not None, "CORS_ORIGINS not found in audit"
        
        # Should be configured (not wildcard)
        assert cors["status"] == "configured", f"CORS_ORIGINS status is {cors['status']}, expected 'configured'"
        assert cors["is_production_ready"] == True, "CORS_ORIGINS should be production ready"
        assert cors["status"] != "wildcard_cors", "CORS_ORIGINS should not be wildcard"
        
        print(f"PASS: CORS_ORIGINS is whitelisted - status={cors['status']}, production_ready=True")
    
    def test_stripe_webhook_secret_is_strong(self, auth_token):
        """STRIPE_WEBHOOK_SECRET should be strong (not 'whsec_test')"""
        response = requests.get(
            f"{BASE_URL}/api/hardening/security/secrets",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        webhook = next((s for s in data["secrets"] if s["name"] == "STRIPE_WEBHOOK_SECRET"), None)
        assert webhook is not None, "STRIPE_WEBHOOK_SECRET not found in audit"
        
        # Should be strong and production ready
        assert webhook["status"] == "strong", f"STRIPE_WEBHOOK_SECRET status is {webhook['status']}, expected 'strong'"
        assert webhook["is_production_ready"] == True, "STRIPE_WEBHOOK_SECRET should be production ready"
        
        print(f"PASS: STRIPE_WEBHOOK_SECRET is strong - status={webhook['status']}, production_ready=True")


class TestJWTSecurityEndpoint(TestAuth):
    """Part 3: JWT Security Verification"""
    
    def test_jwt_security_returns_8_checks(self, auth_token):
        """GET /api/hardening/security/jwt returns 8 security checks"""
        response = requests.get(
            f"{BASE_URL}/api/hardening/security/jwt",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Status {response.status_code}: {response.text}"
        data = response.json()
        
        assert "checks" in data, "Missing checks array"
        assert "summary" in data, "Missing summary"
        assert "configuration" in data, "Missing configuration"
        
        # Should have 8 checks
        assert len(data["checks"]) == 8, f"Expected 8 JWT checks, got {len(data['checks'])}"
        
        # Check summary
        summary = data["summary"]
        assert "total_checks" in summary
        assert summary["total_checks"] == 8
        
        print(f"PASS: JWT security has {len(data['checks'])} checks, {summary['passing']}/{summary['total_checks']} passing")
    
    def test_jwt_key_strength_check_passes(self, auth_token):
        """JWT Key Strength check should pass with strong secret"""
        response = requests.get(
            f"{BASE_URL}/api/hardening/security/jwt",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        key_strength = next((c for c in data["checks"] if c["check"] == "Key Strength"), None)
        assert key_strength is not None, "Key Strength check not found"
        assert key_strength["status"] == "pass", f"Key Strength check failed: {key_strength.get('details')}"
        
        print(f"PASS: JWT Key Strength check passes - {key_strength['details']}")
    
    def test_jwt_no_default_keys_check_passes(self, auth_token):
        """No Default Keys check should pass"""
        response = requests.get(
            f"{BASE_URL}/api/hardening/security/jwt",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        no_defaults = next((c for c in data["checks"] if c["check"] == "No Default Keys"), None)
        assert no_defaults is not None, "No Default Keys check not found"
        assert no_defaults["status"] == "pass", f"No Default Keys check failed: {no_defaults.get('details')}"
        
        print(f"PASS: No Default Keys check passes - {no_defaults['details']}")
    
    def test_jwt_score_is_100_percent(self, auth_token):
        """JWT security score should be 100% with strong secret"""
        response = requests.get(
            f"{BASE_URL}/api/hardening/security/jwt",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        summary = data["summary"]
        assert summary["passing"] == summary["total_checks"], f"Not all checks passing: {summary['passing']}/{summary['total_checks']}"
        assert summary["score_pct"] == 100.0, f"JWT score {summary['score_pct']}% is not 100%"
        
        print(f"PASS: JWT security score is {summary['score_pct']}% ({summary['passing']}/{summary['total_checks']} checks passing)")


class TestTenantIsolationEndpoint(TestAuth):
    """Part 4: Tenant Isolation Enforcement"""
    
    def test_tenant_isolation_returns_20_collections(self, auth_token):
        """GET /api/hardening/security/tenant-isolation returns 20 collections"""
        response = requests.get(
            f"{BASE_URL}/api/hardening/security/tenant-isolation",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Status {response.status_code}: {response.text}"
        data = response.json()
        
        assert "results" in data, "Missing results array"
        assert "summary" in data, "Missing summary"
        
        # Should have 20 collections
        assert data["summary"]["total_collections"] == 20, f"Expected 20 collections, got {data['summary']['total_collections']}"
        
        print(f"PASS: Tenant isolation audits {data['summary']['total_collections']} collections")
    
    def test_tenant_isolation_has_proper_fields(self, auth_token):
        """Each collection result has required fields"""
        response = requests.get(
            f"{BASE_URL}/api/hardening/security/tenant-isolation",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        for result in data["results"]:
            assert "collection" in result, "Missing collection name"
            assert "status" in result, f"Missing status for {result.get('collection')}"
            assert "expected_field" in result, f"Missing expected_field for {result.get('collection')}"
            assert "compliant" in result, f"Missing compliant flag for {result.get('collection')}"
            assert "risk" in result, f"Missing risk for {result.get('collection')}"
        
        print(f"PASS: All {len(data['results'])} collection results have required fields")


class TestRBACEndpoint(TestAuth):
    """Part 5: RBAC Permission Audit"""
    
    def test_rbac_audit_returns_checks(self, auth_token):
        """GET /api/hardening/security/rbac returns RBAC checks"""
        response = requests.get(
            f"{BASE_URL}/api/hardening/security/rbac",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Status {response.status_code}: {response.text}"
        data = response.json()
        
        assert "checks" in data, "Missing checks array"
        assert "summary" in data, "Missing summary"
        
        # Should have multiple checks
        assert len(data["checks"]) >= 8, f"Expected at least 8 RBAC checks, got {len(data['checks'])}"
        
        summary = data["summary"]
        assert "total_checks" in summary
        assert "passing" in summary
        assert "score_pct" in summary
        
        print(f"PASS: RBAC audit has {len(data['checks'])} checks, {summary['passing']}/{summary['total_checks']} passing ({summary['score_pct']}%)")


class TestAPIKeysEndpoint(TestAuth):
    """Part 6: API Key Management"""
    
    def test_api_keys_audit_returns_keys(self, auth_token):
        """GET /api/hardening/security/api-keys returns API key audit"""
        response = requests.get(
            f"{BASE_URL}/api/hardening/security/api-keys",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Status {response.status_code}: {response.text}"
        data = response.json()
        
        assert "api_keys" in data, "Missing api_keys array"
        assert "practices" in data, "Missing practices"
        
        # Should have at least 3 API keys (Stripe, AviationStack, Emergent LLM)
        assert len(data["api_keys"]) >= 3, f"Expected at least 3 API keys, got {len(data['api_keys'])}"
        
        # Check practices
        practices = data["practices"]
        assert practices["keys_hashed_at_rest"] == True, "Keys should be hashed at rest"
        
        print(f"PASS: API keys audit has {len(data['api_keys'])} keys with good practices")


class TestSecurityMonitoringEndpoint(TestAuth):
    """Part 7: Security Monitoring"""
    
    def test_monitoring_returns_detection_rules(self, auth_token):
        """GET /api/hardening/security/monitoring returns detection rules"""
        response = requests.get(
            f"{BASE_URL}/api/hardening/security/monitoring",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Status {response.status_code}: {response.text}"
        data = response.json()
        
        assert "monitoring" in data, "Missing monitoring"
        assert "detection_rules" in data, "Missing detection_rules"
        
        # Should have multiple detection rules
        assert len(data["detection_rules"]) >= 4, f"Expected at least 4 detection rules, got {len(data['detection_rules'])}"
        
        # Check detection rules have required fields
        for rule in data["detection_rules"]:
            assert "rule" in rule, "Missing rule name"
            assert "status" in rule, "Missing status"
            assert "description" in rule, "Missing description"
        
        print(f"PASS: Security monitoring has {len(data['detection_rules'])} detection rules")


class TestSecurityTestsEndpoint(TestAuth):
    """Part 8: Automated Security Tests"""
    
    def test_security_tests_returns_10_tests(self, auth_token):
        """GET /api/hardening/security/tests returns 10 automated tests"""
        response = requests.get(
            f"{BASE_URL}/api/hardening/security/tests",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Status {response.status_code}: {response.text}"
        data = response.json()
        
        assert "tests" in data, "Missing tests array"
        assert "summary" in data, "Missing summary"
        
        # Should have 10 tests
        assert len(data["tests"]) == 10, f"Expected 10 security tests, got {len(data['tests'])}"
        
        summary = data["summary"]
        assert summary["total_tests"] == 10, f"Expected 10 total tests, got {summary['total_tests']}"
        
        print(f"PASS: Security tests has {len(data['tests'])} tests, {summary['passing']}/{summary['total_tests']} passing ({summary['pass_rate_pct']}%)")
    
    def test_cors_policy_test_passes(self, auth_token):
        """CORS Policy Enforcement test should pass with whitelisted origins"""
        response = requests.get(
            f"{BASE_URL}/api/hardening/security/tests",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        cors_test = next((t for t in data["tests"] if t["test"] == "CORS Policy Enforcement"), None)
        assert cors_test is not None, "CORS Policy Enforcement test not found"
        assert cors_test["status"] == "pass", f"CORS test failed: {cors_test.get('details')}"
        
        print(f"PASS: CORS Policy Enforcement test passes - {cors_test['details']}")


class TestSecurityMetricsEndpoint(TestAuth):
    """Part 9: Security Metrics"""
    
    def test_security_metrics_returns_summary(self, auth_token):
        """GET /api/hardening/security/metrics returns metrics summary"""
        response = requests.get(
            f"{BASE_URL}/api/hardening/security/metrics",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Status {response.status_code}: {response.text}"
        data = response.json()
        
        assert "metrics" in data, "Missing metrics"
        
        metrics = data["metrics"]
        assert "secrets_production_ready_pct" in metrics, "Missing secrets_production_ready_pct"
        assert "jwt_security_score_pct" in metrics, "Missing jwt_security_score_pct"
        assert "api_keys_present" in metrics, "Missing api_keys_present"
        assert "cors_whitelisted" in metrics, "Missing cors_whitelisted"
        
        # CORS should be whitelisted
        assert metrics["cors_whitelisted"] == True, "CORS should be whitelisted"
        
        print(f"PASS: Security metrics - secrets {metrics['secrets_production_ready_pct']}% ready, JWT {metrics['jwt_security_score_pct']}% secure, CORS whitelisted={metrics['cors_whitelisted']}")


class TestSecurityReadinessEndpoint(TestAuth):
    """Part 10: Security Readiness Score"""
    
    def test_security_readiness_returns_score(self, auth_token):
        """GET /api/hardening/security/readiness returns comprehensive score"""
        response = requests.get(
            f"{BASE_URL}/api/hardening/security/readiness",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Status {response.status_code}: {response.text}"
        data = response.json()
        
        assert "security_readiness_score" in data, "Missing security_readiness_score"
        assert "dimensions" in data, "Missing dimensions"
        assert "target" in data, "Missing target"
        assert "meets_target" in data, "Missing meets_target"
        
        print(f"PASS: Security readiness score is {data['security_readiness_score']}/10 (target: {data['target']})")
    
    def test_security_readiness_has_6_dimensions(self, auth_token):
        """Security readiness should have 6 dimension scores"""
        response = requests.get(
            f"{BASE_URL}/api/hardening/security/readiness",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        dimensions = data["dimensions"]
        expected_dims = ["secret_management", "jwt_security", "tenant_isolation", "rbac", "security_testing", "monitoring"]
        
        for dim in expected_dims:
            assert dim in dimensions, f"Missing dimension: {dim}"
            assert "score" in dimensions[dim], f"Missing score in {dim}"
            assert "weight" in dimensions[dim], f"Missing weight in {dim}"
        
        print(f"PASS: Security readiness has all 6 dimensions: {list(dimensions.keys())}")
    
    def test_security_readiness_score_meets_target(self, auth_token):
        """Security readiness score should be >=8.5 after hardening"""
        response = requests.get(
            f"{BASE_URL}/api/hardening/security/readiness",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        score = data["security_readiness_score"]
        target = data["target"]
        meets_target = data["meets_target"]
        
        assert score >= 8.5, f"Security readiness score {score} < 8.5 target"
        assert meets_target == True, f"meets_target is {meets_target}, expected True"
        
        # Print dimension breakdown
        for dim, info in data["dimensions"].items():
            print(f"  {dim}: {info['score']}/10 (weight: {info['weight']*100}%)")
        
        print(f"PASS: Security readiness score {score}/10 meets target {target}")


class TestGoLiveCertification(TestAuth):
    """Go-Live Certification should show GO decision"""
    
    def test_certification_returns_go_decision(self, auth_token):
        """GET /api/hardening/activation/certification returns GO decision"""
        response = requests.get(
            f"{BASE_URL}/api/hardening/activation/certification",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Status {response.status_code}: {response.text}"
        data = response.json()
        
        assert "certification" in data, "Missing certification"
        cert = data["certification"]
        
        assert "production_readiness_score" in cert, "Missing production_readiness_score"
        assert "decision" in cert, "Missing decision"
        assert "certified" in cert, "Missing certified"
        
        print(f"PASS: Certification - decision: {cert['decision']}, score: {cert['production_readiness_score']}/10, certified: {cert['certified']}")
    
    def test_certification_production_readiness_at_least_8_5(self, auth_token):
        """Production readiness score should be >=8.5"""
        response = requests.get(
            f"{BASE_URL}/api/hardening/activation/certification",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        cert = data["certification"]
        score = cert["production_readiness_score"]
        
        assert score >= 8.5, f"Production readiness {score} < 8.5 target"
        
        # Print dimension scores
        if "dimension_scores" in data:
            print(f"Dimension scores:")
            for dim, s in data["dimension_scores"].items():
                print(f"  {dim}: {s}/10")
        
        print(f"PASS: Production readiness score {score}/10 >= 8.5 target")
    
    def test_certification_is_go(self, auth_token):
        """Certification decision should be GO"""
        response = requests.get(
            f"{BASE_URL}/api/hardening/activation/certification",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        cert = data["certification"]
        
        assert cert["decision"] == "GO", f"Decision is {cert['decision']}, expected GO"
        assert cert["certified"] == True, f"certified is {cert['certified']}, expected True"
        
        print(f"PASS: Go-Live certification is GO with score {cert['production_readiness_score']}/10")
    
    def test_certification_security_dimension_uses_v2_engine(self, auth_token):
        """Certification should use security engine v2 for security score"""
        response = requests.get(
            f"{BASE_URL}/api/hardening/activation/certification",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Security score in certification should match security readiness endpoint
        assert "security" in data, "Missing security section"
        security = data["security"]
        
        assert "security_score" in security, "Missing security_score"
        
        # Also check dimension scores include security
        if "dimension_scores" in data:
            assert "security" in data["dimension_scores"], "Security missing from dimension_scores"
        
        print(f"PASS: Certification uses v2 security engine - security score: {security['security_score']}/10")


class TestActivationSecretsUsesV2(TestAuth):
    """Activation secrets endpoint should use v2 engine"""
    
    def test_activation_secrets_uses_v2(self, auth_token):
        """GET /api/hardening/activation/secrets should use audit_secrets_v2"""
        response = requests.get(
            f"{BASE_URL}/api/hardening/activation/secrets",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Status {response.status_code}: {response.text}"
        data = response.json()
        
        # v2 has strength_check on each secret
        assert "secrets" in data, "Missing secrets"
        for secret in data["secrets"]:
            assert "strength_check" in secret, f"Secret {secret['name']} missing strength_check (not v2)"
        
        print(f"PASS: /api/hardening/activation/secrets uses v2 engine with strength_check")


class TestActivationTenantIsolationUsesV2(TestAuth):
    """Activation tenant-isolation endpoint should use v2 engine"""
    
    def test_activation_tenant_isolation_uses_v2(self, auth_token):
        """GET /api/hardening/activation/tenant-isolation should use v2 audit"""
        response = requests.get(
            f"{BASE_URL}/api/hardening/activation/tenant-isolation",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Status {response.status_code}: {response.text}"
        data = response.json()
        
        # v2 has expected_field and actual_field in results
        assert "results" in data, "Missing results"
        assert "summary" in data, "Missing summary"
        
        # Check v2 fields
        for result in data["results"]:
            assert "expected_field" in result, f"Collection {result.get('collection')} missing expected_field (not v2)"
            assert "compliant" in result, f"Collection {result.get('collection')} missing compliant flag (not v2)"
        
        # v2 summary has isolation_score_pct
        assert "isolation_score_pct" in data["summary"], "Missing isolation_score_pct (not v2)"
        
        print(f"PASS: /api/hardening/activation/tenant-isolation uses v2 engine - isolation score {data['summary']['isolation_score_pct']}%")


class TestAuthRequired(TestAuth):
    """All security endpoints require authentication"""
    
    def test_security_secrets_requires_auth(self):
        """GET /api/hardening/security/secrets requires auth"""
        response = requests.get(f"{BASE_URL}/api/hardening/security/secrets")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print("PASS: /api/hardening/security/secrets requires auth")
    
    def test_security_jwt_requires_auth(self):
        """GET /api/hardening/security/jwt requires auth"""
        response = requests.get(f"{BASE_URL}/api/hardening/security/jwt")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print("PASS: /api/hardening/security/jwt requires auth")
    
    def test_security_readiness_requires_auth(self):
        """GET /api/hardening/security/readiness requires auth"""
        response = requests.get(f"{BASE_URL}/api/hardening/security/readiness")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print("PASS: /api/hardening/security/readiness requires auth")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
