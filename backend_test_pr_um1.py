#!/usr/bin/env python3

"""
PR-UM1 Usage Metering Foundation Backend Regression Test

This test validates the specific backend APIs requested for PR-UM1 Usage Metering foundation:
1. POST /api/auth/login
2. GET /api/admin/tenants  
3. GET /api/admin/billing/tenants/{tenant_id}/usage - should return 200 and stable payload shape including billing_period, metrics, totals_source

Test credentials: admin@acenta.test / admin123
Base URL: https://acenta-billing.preview.emergentagent.com
"""

import asyncio
import json
import sys
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

import httpx

# Configuration
BASE_URL = "https://acenta-billing.preview.emergentagent.com"
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "admin123"

@dataclass
class TestResult:
    name: str
    passed: bool
    message: str
    response_data: Optional[Dict] = None
    error: Optional[str] = None

class PRUsageMeteringTester:
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

    async def test_1_auth_login(self) -> TestResult:
        """Test 1: POST /api/auth/login - Admin authentication"""
        try:
            response = await self.client.post(f"{BASE_URL}/api/auth/login", json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            })
            
            if response.status_code != 200:
                return self.log_test(
                    "1. POST /api/auth/login", False, 
                    f"Login failed with status {response.status_code}",
                    error=response.text
                )
            
            data = response.json()
            
            # Validate required fields
            required_fields = ["access_token"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                return self.log_test(
                    "1. POST /api/auth/login", False,
                    f"Missing required fields: {missing_fields}",
                    response_data=data
                )
            
            self.admin_token = data["access_token"]
            
            return self.log_test(
                "1. POST /api/auth/login", True,
                f"Login successful, token length: {len(self.admin_token)} chars",
                response_data={"has_token": bool(self.admin_token), "email_returned": data.get("user", {}).get("email")}
            )
            
        except Exception as e:
            return self.log_test("1. POST /api/auth/login", False, "Login request failed", error=str(e))

    async def test_2_admin_tenants(self) -> TestResult:
        """Test 2: GET /api/admin/tenants - Fetch tenant list"""
        try:
            if not self.admin_token:
                return self.log_test("2. GET /api/admin/tenants", False, "No admin token available")
            
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = await self.client.get(f"{BASE_URL}/api/admin/tenants", headers=headers)
            
            if response.status_code != 200:
                return self.log_test(
                    "2. GET /api/admin/tenants", False,
                    f"Tenants endpoint failed with status {response.status_code}",
                    error=response.text
                )
            
            data = response.json()
            
            # Validate response structure - it could be a list directly or an object with items
            tenants = data
            if isinstance(data, dict) and "items" in data:
                tenants = data["items"]
            elif isinstance(data, dict) and "tenants" in data:
                tenants = data["tenants"]
            elif not isinstance(data, list):
                return self.log_test(
                    "2. GET /api/admin/tenants", False,
                    "Response is not a list or object with tenant items",
                    response_data=data
                )
            
            if not tenants:
                return self.log_test(
                    "2. GET /api/admin/tenants", False,
                    "No tenants found in response",
                    response_data=data
                )
            
            # Get the first tenant ID
            first_tenant = tenants[0]
            tenant_id_field = None
            for field in ["id", "_id", "tenant_id"]:
                if field in first_tenant:
                    tenant_id_field = field
                    break
            
            if not tenant_id_field:
                return self.log_test(
                    "2. GET /api/admin/tenants", False,
                    "First tenant missing ID field (tried 'id', '_id', 'tenant_id')",
                    response_data=first_tenant
                )
            
            self.tenant_id = first_tenant[tenant_id_field]
            
            return self.log_test(
                "2. GET /api/admin/tenants", True,
                f"Found {len(tenants)} tenants, selected tenant ID: {self.tenant_id}",
                response_data={"tenant_count": len(tenants), "selected_tenant_id": self.tenant_id}
            )
            
        except Exception as e:
            return self.log_test("2. GET /api/admin/tenants", False, "Tenants request failed", error=str(e))

    async def test_3_tenant_billing_usage(self) -> TestResult:
        """Test 3: GET /api/admin/billing/tenants/{tenant_id}/usage - Usage metering endpoint with stable payload shape"""
        try:
            if not self.admin_token or not self.tenant_id:
                return self.log_test("3. GET /api/admin/billing/tenants/{tenant_id}/usage", False, "Missing admin token or tenant ID")
            
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = await self.client.get(
                f"{BASE_URL}/api/admin/billing/tenants/{self.tenant_id}/usage", 
                headers=headers
            )
            
            if response.status_code != 200:
                return self.log_test(
                    "3. GET /api/admin/billing/tenants/{tenant_id}/usage", False,
                    f"Usage endpoint failed with status {response.status_code}",
                    error=response.text
                )
            
            data = response.json()
            
            # Check required stable payload shape fields
            required_fields = ["billing_period", "metrics", "totals_source"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                return self.log_test(
                    "3. GET /api/admin/billing/tenants/{tenant_id}/usage", False,
                    f"Missing required payload shape fields: {missing_fields}",
                    response_data=data
                )
            
            # Validate field types and structure
            validation_issues = []
            
            # billing_period should be a string (e.g., "2026-03" or similar)
            if not isinstance(data.get("billing_period"), str):
                validation_issues.append("billing_period should be string")
            
            # metrics should be a dict/object
            if not isinstance(data.get("metrics"), dict):
                validation_issues.append("metrics should be dict")
            
            # totals_source should be a string indicating source of data
            if not isinstance(data.get("totals_source"), str):
                validation_issues.append("totals_source should be string")
            
            if validation_issues:
                return self.log_test(
                    "3. GET /api/admin/billing/tenants/{tenant_id}/usage", False,
                    f"Payload shape validation issues: {', '.join(validation_issues)}",
                    response_data=data
                )
            
            # Additional structure validation
            billing_period = data.get("billing_period", "")
            metrics = data.get("metrics", {})
            totals_source = data.get("totals_source", "")
            
            return self.log_test(
                "3. GET /api/admin/billing/tenants/{tenant_id}/usage", True,
                f"Usage endpoint returns 200 with stable payload shape (period: {billing_period}, source: {totals_source}, {len(metrics)} metrics)",
                response_data={
                    "billing_period": billing_period,
                    "metrics_count": len(metrics),
                    "totals_source": totals_source,
                    "metrics_keys": list(metrics.keys()) if isinstance(metrics, dict) else None,
                    "payload_shape_valid": True
                }
            )
            
        except Exception as e:
            return self.log_test("3. GET /api/admin/billing/tenants/{tenant_id}/usage", False, "Usage request failed", error=str(e))

    async def run_all_tests(self):
        """Run all PR-UM1 usage metering regression tests"""
        print("🚀 Starting PR-UM1 Usage Metering Foundation Backend Regression Test")
        print(f"Base URL: {BASE_URL}")
        print(f"Admin Credentials: {ADMIN_EMAIL}")
        print("=" * 80)
        
        # Run tests sequentially
        await self.test_1_auth_login()
        await self.test_2_admin_tenants()
        await self.test_3_tenant_billing_usage()
        
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
        else:
            print(f"\n✅ ALL TESTS PASSED - No regressions detected in Usage Metering foundation")
        
        return summary

async def main():
    """Main test execution"""
    async with PRUsageMeteringTester() as tester:
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
        
        with open("/app/pr_um1_test_results.json", "w") as f:
            json.dump({
                "pr": "PR-UM1",
                "test_type": "Usage Metering Foundation Backend Regression",
                "summary": {
                    "total_tests": summary["total_tests"],
                    "passed": summary["passed"],
                    "failed": summary["failed"],
                    "success_rate": summary["success_rate"]
                },
                "detailed_results": results_data
            }, f, indent=2)
        
        print(f"\n📝 Detailed results saved to: /app/pr_um1_test_results.json")
        
        # Exit with error code if any tests failed
        if summary["failed"] > 0:
            sys.exit(1)
        else:
            print("\n🎉 All PR-UM1 usage metering foundation tests passed!")
            sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())