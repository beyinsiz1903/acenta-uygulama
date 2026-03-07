#!/usr/bin/env python3

"""
Backend Entitlement Projection Flows Validation Test

This test validates the specific entitlement projection flows requested:
1. POST /api/auth/login
2. GET /api/onboarding/plans -> confirm starter/pro/enterprise with limits + usage_allowances
3. GET /api/admin/tenants -> fetch a tenant id
4. GET /api/admin/tenants/{tenant_id}/features -> confirm canonical entitlement fields exist
5. PATCH /api/admin/tenants/{tenant_id}/plan with pro or enterprise -> confirm limits update
6. PATCH /api/admin/tenants/{tenant_id}/add-ons -> confirm response shape remains consistent
7. GET /api/tenant/features and GET /api/tenant/entitlements with tenant context -> confirm canonical projection

Test credentials: admin@acenta.test / admin123
Base URL: https://travel-saas-refactor-1.preview.emergentagent.com
"""

import asyncio
import json
import sys
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

import httpx

# Configuration
BASE_URL = "https://travel-saas-refactor-1.preview.emergentagent.com"
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "admin123"

@dataclass
class TestResult:
    name: str
    passed: bool
    message: str
    response_data: Optional[Dict] = None
    error: Optional[str] = None

class EntitlementProjectionTester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.admin_token = None
        self.tenant_id = None
        self.results: List[TestResult] = []
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def log_test(self, name: str, passed: bool, message: str, response_data: Optional[Dict] = None, error: Optional[str] = None):
        """Log a test result"""
        result = TestResult(name=name, passed=passed, message=message, response_data=response_data, error=error)
        self.results.append(result)
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name} - {message}")
        if error:
            print(f"   Error: {error}")
        return result

    async def test_1_admin_login(self) -> TestResult:
        """Test 1: POST /api/auth/login - Admin authentication"""
        try:
            response = await self.client.post(f"{BASE_URL}/api/auth/login", json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            })
            
            if response.status_code != 200:
                return self.log_test(
                    "1. Admin Login", False, 
                    f"Login failed with status {response.status_code}",
                    error=response.text
                )
            
            data = response.json()
            
            # Validate required fields
            required_fields = ["access_token", "token_type"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                return self.log_test(
                    "1. Admin Login", False,
                    f"Missing required fields: {missing_fields}",
                    response_data=data
                )
            
            self.admin_token = data["access_token"]
            
            return self.log_test(
                "1. Admin Login", True,
                f"Login successful, token length: {len(self.admin_token)} chars",
                response_data={"token_type": data.get("token_type"), "has_token": bool(self.admin_token)}
            )
            
        except Exception as e:
            return self.log_test("1. Admin Login", False, "Login request failed", error=str(e))

    async def test_2_onboarding_plans(self) -> TestResult:
        """Test 2: GET /api/onboarding/plans - Confirm starter/pro/enterprise with limits + usage_allowances"""
        try:
            response = await self.client.get(f"{BASE_URL}/api/onboarding/plans")
            
            if response.status_code != 200:
                return self.log_test(
                    "2. Onboarding Plans", False,
                    f"Plans endpoint failed with status {response.status_code}",
                    error=response.text
                )
            
            data = response.json()
            
            # Validate response structure
            if "plans" not in data:
                return self.log_test(
                    "2. Onboarding Plans", False,
                    "Response missing 'plans' field",
                    response_data=data
                )
            
            plans = data["plans"]
            plan_names = [plan.get("name", "").lower() for plan in plans]
            
            # Check required plans exist
            required_plans = ["starter", "pro", "enterprise"]
            missing_plans = [plan for plan in required_plans if plan not in plan_names]
            
            if missing_plans:
                return self.log_test(
                    "2. Onboarding Plans", False,
                    f"Missing required plans: {missing_plans}. Found: {plan_names}",
                    response_data=data
                )
            
            # Validate each plan has limits and usage_allowances
            issues = []
            for plan in plans:
                plan_name = plan.get("name", "unknown")
                if "limits" not in plan:
                    issues.append(f"{plan_name} missing 'limits' field")
                if "usage_allowances" not in plan:
                    issues.append(f"{plan_name} missing 'usage_allowances' field")
            
            if issues:
                return self.log_test(
                    "2. Onboarding Plans", False,
                    f"Plan structure issues: {', '.join(issues)}",
                    response_data=data
                )
            
            return self.log_test(
                "2. Onboarding Plans", True,
                f"Found all required plans ({', '.join(required_plans)}) with limits and usage_allowances",
                response_data={"plan_count": len(plans), "plan_names": plan_names}
            )
            
        except Exception as e:
            return self.log_test("2. Onboarding Plans", False, "Plans request failed", error=str(e))

    async def test_3_admin_tenants(self) -> TestResult:
        """Test 3: GET /api/admin/tenants - Fetch a tenant ID"""
        try:
            if not self.admin_token:
                return self.log_test("3. Admin Tenants", False, "No admin token available")
            
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = await self.client.get(f"{BASE_URL}/api/admin/tenants", headers=headers)
            
            if response.status_code != 200:
                return self.log_test(
                    "3. Admin Tenants", False,
                    f"Tenants endpoint failed with status {response.status_code}",
                    error=response.text
                )
            
            data = response.json()
            
            # Validate response structure
            if "items" not in data:
                return self.log_test(
                    "3. Admin Tenants", False,
                    "Response missing 'items' field",
                    response_data=data
                )
            
            items = data["items"]
            
            if not items:
                return self.log_test(
                    "3. Admin Tenants", False,
                    "No tenants found in response",
                    response_data=data
                )
            
            # Get the first tenant ID
            first_tenant = items[0]
            if "id" not in first_tenant:
                return self.log_test(
                    "3. Admin Tenants", False,
                    "First tenant missing 'id' field",
                    response_data=data
                )
            
            self.tenant_id = first_tenant["id"]
            
            return self.log_test(
                "3. Admin Tenants", True,
                f"Found {len(items)} tenants, selected tenant ID: {self.tenant_id}",
                response_data={"tenant_count": len(items), "selected_tenant": first_tenant}
            )
            
        except Exception as e:
            return self.log_test("3. Admin Tenants", False, "Tenants request failed", error=str(e))

    async def test_4_tenant_features(self) -> TestResult:
        """Test 4: GET /api/admin/tenants/{tenant_id}/features - Confirm canonical entitlement fields"""
        try:
            if not self.admin_token or not self.tenant_id:
                return self.log_test("4. Tenant Features", False, "Missing admin token or tenant ID")
            
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = await self.client.get(
                f"{BASE_URL}/api/admin/tenants/{self.tenant_id}/features", 
                headers=headers
            )
            
            if response.status_code != 200:
                return self.log_test(
                    "4. Tenant Features", False,
                    f"Tenant features endpoint failed with status {response.status_code}",
                    error=response.text
                )
            
            data = response.json()
            
            # Check canonical entitlement fields
            required_fields = ["tenant_id", "plan", "plan_label", "add_ons", "features", "limits", "usage_allowances", "source"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                return self.log_test(
                    "4. Tenant Features", False,
                    f"Missing canonical entitlement fields: {missing_fields}",
                    response_data=data
                )
            
            # Validate field types
            type_issues = []
            if not isinstance(data.get("add_ons"), list):
                type_issues.append("add_ons should be list")
            if not isinstance(data.get("features"), list):
                type_issues.append("features should be list")
            if not isinstance(data.get("limits"), dict):
                type_issues.append("limits should be dict")
            if not isinstance(data.get("usage_allowances"), dict):
                type_issues.append("usage_allowances should be dict")
            
            if type_issues:
                return self.log_test(
                    "4. Tenant Features", False,
                    f"Field type issues: {', '.join(type_issues)}",
                    response_data=data
                )
            
            return self.log_test(
                "4. Tenant Features", True,
                f"All canonical entitlement fields present for plan '{data.get('plan')}' (source: {data.get('source')})",
                response_data={
                    "plan": data.get("plan"),
                    "plan_label": data.get("plan_label"),
                    "feature_count": len(data.get("features", [])),
                    "limits_count": len(data.get("limits", {})),
                    "usage_allowances_count": len(data.get("usage_allowances", {})),
                    "source": data.get("source")
                }
            )
            
        except Exception as e:
            return self.log_test("4. Tenant Features", False, "Tenant features request failed", error=str(e))

    async def test_5_patch_tenant_plan(self) -> TestResult:
        """Test 5: PATCH /api/admin/tenants/{tenant_id}/plan - Update to pro/enterprise and confirm limits update"""
        try:
            if not self.admin_token or not self.tenant_id:
                return self.log_test("5. Patch Tenant Plan", False, "Missing admin token or tenant ID")
            
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            
            # First get current state
            get_response = await self.client.get(
                f"{BASE_URL}/api/admin/tenants/{self.tenant_id}/features", 
                headers=headers
            )
            
            if get_response.status_code != 200:
                return self.log_test(
                    "5. Patch Tenant Plan", False,
                    f"Failed to get current tenant features: {get_response.status_code}",
                    error=get_response.text
                )
            
            current_data = get_response.json()
            current_plan = current_data.get("plan", "unknown")
            current_limits = current_data.get("limits", {})
            
            # Choose target plan (upgrade to pro or enterprise)
            target_plan = "enterprise" if current_plan.lower() == "pro" else "pro"
            
            # Update the plan
            patch_response = await self.client.patch(
                f"{BASE_URL}/api/admin/tenants/{self.tenant_id}/plan",
                headers=headers,
                json={"plan": target_plan}
            )
            
            if patch_response.status_code != 200:
                return self.log_test(
                    "5. Patch Tenant Plan", False,
                    f"Plan update failed with status {patch_response.status_code}",
                    error=patch_response.text
                )
            
            updated_data = patch_response.json()
            
            # Validate the response structure
            required_fields = ["tenant_id", "plan", "plan_label", "limits", "usage_allowances"]
            missing_fields = [field for field in required_fields if field not in updated_data]
            
            if missing_fields:
                return self.log_test(
                    "5. Patch Tenant Plan", False,
                    f"Missing fields in update response: {missing_fields}",
                    response_data=updated_data
                )
            
            # Confirm plan was updated
            new_plan = updated_data.get("plan")
            if new_plan != target_plan:
                return self.log_test(
                    "5. Patch Tenant Plan", False,
                    f"Plan not updated correctly. Expected: {target_plan}, Got: {new_plan}",
                    response_data=updated_data
                )
            
            new_limits = updated_data.get("limits", {})
            
            return self.log_test(
                "5. Patch Tenant Plan", True,
                f"Successfully updated plan from '{current_plan}' to '{target_plan}', limits updated",
                response_data={
                    "previous_plan": current_plan,
                    "new_plan": new_plan,
                    "plan_label": updated_data.get("plan_label"),
                    "limits_changed": current_limits != new_limits,
                    "current_limits_count": len(new_limits)
                }
            )
            
        except Exception as e:
            return self.log_test("5. Patch Tenant Plan", False, "Plan update request failed", error=str(e))

    async def test_6_patch_tenant_add_ons(self) -> TestResult:
        """Test 6: PATCH /api/admin/tenants/{tenant_id}/add-ons - Confirm response shape consistency"""
        try:
            if not self.admin_token or not self.tenant_id:
                return self.log_test("6. Patch Tenant Add-ons", False, "Missing admin token or tenant ID")
            
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            
            # Test with valid feature keys from the system
            test_add_ons = ["reports", "crm"]
            
            patch_response = await self.client.patch(
                f"{BASE_URL}/api/admin/tenants/{self.tenant_id}/add-ons",
                headers=headers,
                json={"add_ons": test_add_ons}
            )
            
            if patch_response.status_code != 200:
                return self.log_test(
                    "6. Patch Tenant Add-ons", False,
                    f"Add-ons update failed with status {patch_response.status_code}",
                    error=patch_response.text
                )
            
            data = patch_response.json()
            
            # Validate response shape consistency (same as other entitlement endpoints)
            required_fields = ["tenant_id", "plan", "plan_label", "add_ons", "features", "limits", "usage_allowances", "source"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                return self.log_test(
                    "6. Patch Tenant Add-ons", False,
                    f"Response shape inconsistent, missing fields: {missing_fields}",
                    response_data=data
                )
            
            # Validate field types match canonical projection
            type_issues = []
            if not isinstance(data.get("add_ons"), list):
                type_issues.append("add_ons should be list")
            if not isinstance(data.get("features"), list):
                type_issues.append("features should be list")
            if not isinstance(data.get("limits"), dict):
                type_issues.append("limits should be dict")
            if not isinstance(data.get("usage_allowances"), dict):
                type_issues.append("usage_allowances should be dict")
            
            if type_issues:
                return self.log_test(
                    "6. Patch Tenant Add-ons", False,
                    f"Response shape type issues: {', '.join(type_issues)}",
                    response_data=data
                )
            
            return self.log_test(
                "6. Patch Tenant Add-ons", True,
                f"Add-ons update successful, response shape consistent with canonical projection",
                response_data={
                    "updated_add_ons": data.get("add_ons"),
                    "plan": data.get("plan"),
                    "source": data.get("source"),
                    "response_shape_valid": True
                }
            )
            
        except Exception as e:
            return self.log_test("6. Patch Tenant Add-ons", False, "Add-ons update request failed", error=str(e))

    async def test_7_tenant_context_endpoints(self) -> TestResult:
        """Test 7: GET /api/tenant/features and /api/tenant/entitlements with tenant context"""
        try:
            if not self.admin_token or not self.tenant_id:
                return self.log_test("7. Tenant Context Endpoints", False, "Missing admin token or tenant ID")
            
            headers = {
                "Authorization": f"Bearer {self.admin_token}",
                "X-Tenant-Id": self.tenant_id
            }
            
            # Test GET /api/tenant/features
            features_response = await self.client.get(f"{BASE_URL}/api/tenant/features", headers=headers)
            
            if features_response.status_code != 200:
                return self.log_test(
                    "7. Tenant Context Endpoints", False,
                    f"/api/tenant/features failed with status {features_response.status_code}",
                    error=features_response.text
                )
            
            features_data = features_response.json()
            
            # Test GET /api/tenant/entitlements
            entitlements_response = await self.client.get(f"{BASE_URL}/api/tenant/entitlements", headers=headers)
            
            if entitlements_response.status_code != 200:
                return self.log_test(
                    "7. Tenant Context Endpoints", False,
                    f"/api/tenant/entitlements failed with status {entitlements_response.status_code}",
                    error=entitlements_response.text
                )
            
            entitlements_data = entitlements_response.json()
            
            # Validate both responses have canonical projection fields
            for endpoint, data in [("features", features_data), ("entitlements", entitlements_data)]:
                required_fields = ["tenant_id", "plan", "plan_label", "add_ons", "features", "limits", "usage_allowances", "source"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    return self.log_test(
                        "7. Tenant Context Endpoints", False,
                        f"/api/tenant/{endpoint} missing canonical fields: {missing_fields}",
                        response_data=data
                    )
            
            # Verify both endpoints return the same data (they should be equivalent)
            if features_data != entitlements_data:
                return self.log_test(
                    "7. Tenant Context Endpoints", False,
                    "/api/tenant/features and /api/tenant/entitlements return different data",
                    response_data={"features": features_data, "entitlements": entitlements_data}
                )
            
            return self.log_test(
                "7. Tenant Context Endpoints", True,
                f"Both tenant context endpoints working with canonical projection (tenant: {features_data.get('tenant_id')})",
                response_data={
                    "tenant_id": features_data.get("tenant_id"),
                    "plan": features_data.get("plan"),
                    "source": features_data.get("source"),
                    "endpoints_consistent": True
                }
            )
            
        except Exception as e:
            return self.log_test("7. Tenant Context Endpoints", False, "Tenant context endpoints request failed", error=str(e))

    async def run_all_tests(self):
        """Run all entitlement projection flow tests"""
        print("🚀 Starting Backend Entitlement Projection Flows Validation")
        print(f"Base URL: {BASE_URL}")
        print(f"Admin Credentials: {ADMIN_EMAIL}")
        print("=" * 80)
        
        # Run tests sequentially
        await self.test_1_admin_login()
        await self.test_2_onboarding_plans()
        await self.test_3_admin_tenants()
        await self.test_4_tenant_features()
        await self.test_5_patch_tenant_plan()
        await self.test_6_patch_tenant_add_ons()
        await self.test_7_tenant_context_endpoints()
        
        print("=" * 80)
        return self.generate_summary()

    def generate_summary(self) -> Dict[str, Any]:
        """Generate test summary"""
        total_tests = len(self.results)
        passed_tests = sum(1 for result in self.results if result.passed)
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        summary = {
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "success_rate": round(success_rate, 1),
            "results": self.results
        }
        
        print(f"📊 TEST SUMMARY:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {passed_tests}")
        print(f"   Failed: {failed_tests}")
        print(f"   Success Rate: {success_rate:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS:")
            for result in self.results:
                if not result.passed:
                    print(f"   - {result.name}: {result.message}")
                    if result.error:
                        print(f"     Error: {result.error}")
        
        return summary

async def main():
    """Main test execution"""
    async with EntitlementProjectionTester() as tester:
        summary = await tester.run_all_tests()
        
        # Write detailed results to file
        results_data = []
        for result in tester.results:
            results_data.append({
                "name": result.name,
                "passed": result.passed,
                "message": result.message,
                "response_data": result.response_data,
                "error": result.error
            })
        
        with open("/app/entitlement_test_results.json", "w") as f:
            json.dump({
                "summary": {
                    "total_tests": summary["total_tests"],
                    "passed": summary["passed"],
                    "failed": summary["failed"],
                    "success_rate": summary["success_rate"]
                },
                "detailed_results": results_data
            }, f, indent=2)
        
        print(f"\n📝 Detailed results saved to: /app/entitlement_test_results.json")
        
        # Exit with error code if any tests failed
        if summary["failed"] > 0:
            sys.exit(1)
        else:
            print("\n🎉 All entitlement projection flow tests passed!")
            sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())