#!/usr/bin/env python3
"""
Backend smoke/regression test for hard quota enforcement implementation.

Tests all endpoints mentioned in the review request to ensure they return
200 or 403 (when quota exceeded) but NOT 500 server errors.

Review Request: Backend smoke/regression testing for hard quota enforcement:
- New service: backend/app/services/quota_enforcement_service.py
- Reservation/report/export flows have quota guards added
- Frontend only had error parsing changes; backend needs live regression testing

Required Tests:
1. Login with agent@acenta.test / agent123 and auth flow
2. GET /api/tenant/usage-summary?days=30 returns 200
3. GET /api/billing/subscription returns 200 
4. GET /api/reports/sales-summary.csv returns 200 OR 403 (not 500)
5. Admin endpoints: POST /api/admin/tenant/export and GET /api/admin/audit/export return 200 OR 403 (not 500)
6. Check for regressions/import errors/serialization issues in hard quota implementation
"""
import os
import sys
import json
import requests
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://agency-billing-ui.preview.emergentagent.com"
AGENT_EMAIL = "agent@acenta.test"
AGENT_PASSWORD = "agent123"
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "admin123"

class BackendQuotaSmokeTester:
    def __init__(self):
        self.base_url = BASE_URL.rstrip("/")
        self.agent_session = None
        self.admin_session = None
        self.test_results = []
        
    def log_result(self, test_name: str, passed: bool, message: str, details: Optional[Dict] = None):
        """Log test result with details."""
        result = {
            "test": test_name,
            "passed": passed,
            "message": message,
            "details": details or {}
        }
        self.test_results.append(result)
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        print(f"   {message}")
        if details:
            print(f"   Details: {json.dumps(details, indent=2)[:200]}...")
        print()

    def create_session(self, email: str, password: str) -> requests.Session:
        """Create authenticated session for user."""
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
        
        # Login
        login_response = session.post(
            f"{self.base_url}/api/auth/login",
            json={"email": email, "password": password},
            timeout=10
        )
        
        if login_response.status_code != 200:
            raise Exception(f"Login failed for {email}: {login_response.status_code} - {login_response.text}")
        
        # Handle token auth if present
        try:
            login_data = login_response.json()
            if "access_token" in login_data:
                session.headers.update({
                    "Authorization": f"Bearer {login_data['access_token']}"
                })
        except:
            pass  # Cookie-based auth, session cookies should be set automatically
        
        return session

    def test_1_agent_login_auth_flow(self):
        """Test 1: Login with agent@acenta.test / agent123 and auth flow"""
        try:
            # Create agent session
            self.agent_session = self.create_session(AGENT_EMAIL, AGENT_PASSWORD)
            
            # Verify auth flow with /api/auth/me
            me_response = self.agent_session.get(f"{self.base_url}/api/auth/me", timeout=10)
            
            if me_response.status_code == 200:
                user_data = me_response.json()
                if user_data.get("email") == AGENT_EMAIL:
                    self.log_result(
                        "1. Agent Login & Auth Flow",
                        True,
                        f"Successfully authenticated as {AGENT_EMAIL}",
                        {"email": user_data.get("email"), "tenant_id": user_data.get("tenant_id")}
                    )
                else:
                    self.log_result(
                        "1. Agent Login & Auth Flow",
                        False,
                        f"Email mismatch: expected {AGENT_EMAIL}, got {user_data.get('email')}",
                        user_data
                    )
            else:
                self.log_result(
                    "1. Agent Login & Auth Flow",
                    False,
                    f"/api/auth/me failed: {me_response.status_code} - {me_response.text[:100]}",
                    {"status_code": me_response.status_code}
                )
        except Exception as e:
            self.log_result(
                "1. Agent Login & Auth Flow",
                False,
                f"Exception during agent login: {str(e)[:100]}",
                {"exception": str(e)}
            )

    def test_2_usage_summary_endpoint(self):
        """Test 2: GET /api/tenant/usage-summary?days=30 returns 200"""
        if not self.agent_session:
            self.log_result("2. Usage Summary Endpoint", False, "No agent session available", {})
            return
            
        try:
            response = self.agent_session.get(
                f"{self.base_url}/api/tenant/usage-summary?days=30",
                timeout=10
            )
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    self.log_result(
                        "2. Usage Summary Endpoint",
                        True,
                        "GET /api/tenant/usage-summary?days=30 returned 200 OK",
                        {
                            "status_code": 200,
                            "has_metrics": "metrics" in data,
                            "has_plan": "plan" in data,
                            "response_keys": list(data.keys())[:10]
                        }
                    )
                except json.JSONDecodeError:
                    self.log_result(
                        "2. Usage Summary Endpoint",
                        False,
                        "GET /api/tenant/usage-summary returned 200 but invalid JSON",
                        {"status_code": 200, "content": response.text[:100]}
                    )
            else:
                self.log_result(
                    "2. Usage Summary Endpoint", 
                    False,
                    f"GET /api/tenant/usage-summary failed: {response.status_code}",
                    {"status_code": response.status_code, "error": response.text[:100]}
                )
        except Exception as e:
            self.log_result(
                "2. Usage Summary Endpoint",
                False,
                f"Exception: {str(e)[:100]}",
                {"exception": str(e)}
            )

    def test_3_billing_subscription_endpoint(self):
        """Test 3: GET /api/billing/subscription returns 200"""
        if not self.agent_session:
            self.log_result("3. Billing Subscription Endpoint", False, "No agent session available", {})
            return
            
        try:
            response = self.agent_session.get(
                f"{self.base_url}/api/billing/subscription",
                timeout=10
            )
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    self.log_result(
                        "3. Billing Subscription Endpoint",
                        True,
                        "GET /api/billing/subscription returned 200 OK",
                        {
                            "status_code": 200,
                            "plan": data.get("plan"),
                            "status": data.get("status"),
                            "has_subscription": "subscription_id" in data or "provider_subscription_id" in data
                        }
                    )
                except json.JSONDecodeError:
                    self.log_result(
                        "3. Billing Subscription Endpoint",
                        False,
                        "GET /api/billing/subscription returned 200 but invalid JSON",
                        {"status_code": 200, "content": response.text[:100]}
                    )
            else:
                self.log_result(
                    "3. Billing Subscription Endpoint",
                    False,
                    f"GET /api/billing/subscription failed: {response.status_code}",
                    {"status_code": response.status_code, "error": response.text[:100]}
                )
        except Exception as e:
            self.log_result(
                "3. Billing Subscription Endpoint",
                False,
                f"Exception: {str(e)[:100]}",
                {"exception": str(e)}
            )

    def test_4_sales_summary_csv_endpoint(self):
        """Test 4: GET /api/reports/sales-summary.csv returns 200 OR 403 (quota exceeded) but NOT 500"""
        if not self.agent_session:
            self.log_result("4. Sales Summary CSV Endpoint", False, "No agent session available", {})
            return
            
        try:
            response = self.agent_session.get(
                f"{self.base_url}/api/reports/sales-summary.csv",
                timeout=15  # CSV generation may take longer
            )
            
            if response.status_code == 200:
                # Success - verify it's CSV
                content_type = response.headers.get("content-type", "")
                is_csv = "csv" in content_type.lower() or "text/plain" in content_type.lower()
                self.log_result(
                    "4. Sales Summary CSV Endpoint",
                    True,
                    "GET /api/reports/sales-summary.csv returned 200 OK (CSV generated)",
                    {
                        "status_code": 200,
                        "content_type": content_type,
                        "is_csv": is_csv,
                        "content_length": len(response.content)
                    }
                )
            elif response.status_code == 403:
                # Quota exceeded - verify error structure
                try:
                    error_data = response.json()
                    quota_error = (
                        "error" in error_data and 
                        error_data["error"].get("code") == "quota_exceeded"
                    )
                    self.log_result(
                        "4. Sales Summary CSV Endpoint",
                        True,
                        "GET /api/reports/sales-summary.csv returned 403 (quota exceeded) - correct behavior",
                        {
                            "status_code": 403,
                            "has_quota_error": quota_error,
                            "error_code": error_data.get("error", {}).get("code"),
                            "metric": error_data.get("error", {}).get("details", {}).get("metric")
                        }
                    )
                except:
                    self.log_result(
                        "4. Sales Summary CSV Endpoint",
                        True,
                        "GET /api/reports/sales-summary.csv returned 403 (likely quota exceeded)",
                        {"status_code": 403, "response": response.text[:100]}
                    )
            elif response.status_code == 500:
                # Server error - this is BAD
                self.log_result(
                    "4. Sales Summary CSV Endpoint",
                    False,
                    "GET /api/reports/sales-summary.csv returned 500 - SERVER ERROR (hard quota implementation issue!)",
                    {"status_code": 500, "error": response.text[:200]}
                )
            else:
                self.log_result(
                    "4. Sales Summary CSV Endpoint",
                    False,
                    f"GET /api/reports/sales-summary.csv returned unexpected status: {response.status_code}",
                    {"status_code": response.status_code, "error": response.text[:100]}
                )
        except Exception as e:
            self.log_result(
                "4. Sales Summary CSV Endpoint",
                False,
                f"Exception: {str(e)[:100]}",
                {"exception": str(e)}
            )

    def test_5_admin_endpoints(self):
        """Test 5: Admin endpoints POST /api/admin/tenant/export and GET /api/admin/audit/export return 200 OR 403 (not 500)"""
        try:
            # Create admin session
            self.admin_session = self.create_session(ADMIN_EMAIL, ADMIN_PASSWORD)
            
            # Verify admin session with /api/auth/me
            me_response = self.admin_session.get(f"{self.base_url}/api/auth/me", timeout=10)
            if me_response.status_code != 200:
                self.log_result(
                    "5a. Admin Session Setup",
                    False,
                    f"Admin auth failed: {me_response.status_code}",
                    {"status_code": me_response.status_code}
                )
                return
            
            admin_data = me_response.json()
            self.log_result(
                "5a. Admin Session Setup",
                True,
                f"Successfully authenticated as admin: {admin_data.get('email')}",
                {"email": admin_data.get("email"), "roles": admin_data.get("roles", [])}
            )
            
        except Exception as e:
            self.log_result(
                "5a. Admin Session Setup",
                False,
                f"Exception during admin login: {str(e)[:100]}",
                {"exception": str(e)}
            )
            return

        # Test POST /api/admin/tenant/export
        try:
            response = self.admin_session.post(
                f"{self.base_url}/api/admin/tenant/export",
                timeout=20  # Export may take longer
            )
            
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")
                is_zip = "zip" in content_type.lower()
                self.log_result(
                    "5b. Admin Tenant Export",
                    True,
                    "POST /api/admin/tenant/export returned 200 OK",
                    {
                        "status_code": 200,
                        "content_type": content_type,
                        "is_zip": is_zip,
                        "content_length": len(response.content)
                    }
                )
            elif response.status_code == 403:
                try:
                    error_data = response.json()
                    quota_error = (
                        "error" in error_data and 
                        error_data["error"].get("code") == "quota_exceeded"
                    )
                    self.log_result(
                        "5b. Admin Tenant Export",
                        True,
                        "POST /api/admin/tenant/export returned 403 (quota exceeded) - correct behavior",
                        {
                            "status_code": 403,
                            "has_quota_error": quota_error,
                            "error_code": error_data.get("error", {}).get("code")
                        }
                    )
                except:
                    self.log_result(
                        "5b. Admin Tenant Export",
                        True,
                        "POST /api/admin/tenant/export returned 403 (likely quota exceeded)",
                        {"status_code": 403}
                    )
            elif response.status_code == 500:
                self.log_result(
                    "5b. Admin Tenant Export",
                    False,
                    "POST /api/admin/tenant/export returned 500 - SERVER ERROR (hard quota implementation issue!)",
                    {"status_code": 500, "error": response.text[:200]}
                )
            else:
                self.log_result(
                    "5b. Admin Tenant Export",
                    False,
                    f"POST /api/admin/tenant/export returned unexpected status: {response.status_code}",
                    {"status_code": response.status_code, "error": response.text[:100]}
                )
        except Exception as e:
            self.log_result(
                "5b. Admin Tenant Export",
                False,
                f"Exception: {str(e)[:100]}",
                {"exception": str(e)}
            )

        # Test GET /api/admin/audit/export
        try:
            response = self.admin_session.get(
                f"{self.base_url}/api/admin/audit/export",
                timeout=20  # Export may take longer
            )
            
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")
                is_csv = "csv" in content_type.lower() or "text" in content_type.lower()
                self.log_result(
                    "5c. Admin Audit Export",
                    True,
                    "GET /api/admin/audit/export returned 200 OK",
                    {
                        "status_code": 200,
                        "content_type": content_type,
                        "is_csv": is_csv,
                        "content_length": len(response.content)
                    }
                )
            elif response.status_code == 403:
                try:
                    error_data = response.json()
                    quota_error = (
                        "error" in error_data and 
                        error_data["error"].get("code") == "quota_exceeded"
                    )
                    self.log_result(
                        "5c. Admin Audit Export",
                        True,
                        "GET /api/admin/audit/export returned 403 (quota exceeded) - correct behavior",
                        {
                            "status_code": 403,
                            "has_quota_error": quota_error,
                            "error_code": error_data.get("error", {}).get("code")
                        }
                    )
                except:
                    self.log_result(
                        "5c. Admin Audit Export",
                        True,
                        "GET /api/admin/audit/export returned 403 (likely quota exceeded)",
                        {"status_code": 403}
                    )
            elif response.status_code == 500:
                self.log_result(
                    "5c. Admin Audit Export",
                    False,
                    "GET /api/admin/audit/export returned 500 - SERVER ERROR (hard quota implementation issue!)",
                    {"status_code": 500, "error": response.text[:200]}
                )
            else:
                self.log_result(
                    "5c. Admin Audit Export",
                    False,
                    f"GET /api/admin/audit/export returned unexpected status: {response.status_code}",
                    {"status_code": response.status_code, "error": response.text[:100]}
                )
        except Exception as e:
            self.log_result(
                "5c. Admin Audit Export",
                False,
                f"Exception: {str(e)[:100]}",
                {"exception": str(e)}
            )

    def test_6_quota_service_regression_check(self):
        """Test 6: Check for regressions/import errors/serialization issues in hard quota implementation"""
        
        # Check if quota service endpoints are accessible (basic smoke test)
        service_checks = []
        
        if self.agent_session:
            try:
                # Test quota service integration via usage endpoint
                response = self.agent_session.get(
                    f"{self.base_url}/api/tenant/usage-summary?days=30",
                    timeout=10
                )
                service_checks.append({
                    "endpoint": "/api/tenant/usage-summary",
                    "accessible": response.status_code in [200, 403],
                    "status_code": response.status_code
                })
            except Exception as e:
                service_checks.append({
                    "endpoint": "/api/tenant/usage-summary",
                    "accessible": False,
                    "error": str(e)[:100]
                })
        
        # Check auth endpoint is still working
        try:
            test_session = requests.Session()
            test_session.headers.update({"Content-Type": "application/json"})
            
            response = test_session.post(
                f"{self.base_url}/api/auth/login",
                json={"email": AGENT_EMAIL, "password": AGENT_PASSWORD},
                timeout=10
            )
            service_checks.append({
                "endpoint": "/api/auth/login",
                "accessible": response.status_code == 200,
                "status_code": response.status_code
            })
        except Exception as e:
            service_checks.append({
                "endpoint": "/api/auth/login",
                "accessible": False,
                "error": str(e)[:100]
            })
        
        # Evaluate results
        all_accessible = all(check.get("accessible", False) for check in service_checks)
        
        if all_accessible:
            self.log_result(
                "6. Quota Service Regression Check",
                True,
                "All tested endpoints accessible - no obvious import/serialization regressions detected",
                {"service_checks": service_checks}
            )
        else:
            failed_services = [
                check for check in service_checks 
                if not check.get("accessible", False)
            ]
            self.log_result(
                "6. Quota Service Regression Check",
                False,
                f"Potential regression detected - {len(failed_services)} endpoints failed",
                {"failed_services": failed_services, "all_checks": service_checks}
            )

    def run_all_tests(self):
        """Run all smoke tests in order."""
        print("🚀 BACKEND SMOKE/REGRESSION TEST FOR HARD QUOTA ENFORCEMENT")
        print(f"Testing against: {self.base_url}")
        print("=" * 80)
        print()
        
        self.test_1_agent_login_auth_flow()
        self.test_2_usage_summary_endpoint()
        self.test_3_billing_subscription_endpoint()
        self.test_4_sales_summary_csv_endpoint()
        self.test_5_admin_endpoints()
        self.test_6_quota_service_regression_check()
        
        return self.generate_summary()

    def generate_summary(self) -> Dict[str, Any]:
        """Generate test summary."""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["passed"]])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print("=" * 80)
        print("📊 HARD QUOTA ENFORCEMENT SMOKE TEST SUMMARY")
        print("=" * 80)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {success_rate:.1f}%")
        print()
        
        # Show failed tests
        failed_tests_list = [r for r in self.test_results if not r["passed"]]
        if failed_tests_list:
            print("❌ FAILED TESTS:")
            for test in failed_tests_list:
                print(f"  - {test['test']}: {test['message']}")
            print()
        
        # Show passed tests
        passed_tests_list = [r for r in self.test_results if r["passed"]]
        if passed_tests_list:
            print("✅ PASSED TESTS:")
            for test in passed_tests_list:
                print(f"  - {test['test']}")
            print()
        
        # Check for critical issues
        critical_issues = []
        for test in self.test_results:
            if not test["passed"]:
                if "500" in test["message"] or "SERVER ERROR" in test["message"]:
                    critical_issues.append(f"{test['test']}: {test['message']}")
        
        if critical_issues:
            print("🚨 CRITICAL ISSUES DETECTED:")
            for issue in critical_issues:
                print(f"  - {issue}")
            print()
        
        print("=" * 80)
        
        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": success_rate,
            "critical_issues": critical_issues,
            "all_results": self.test_results
        }

def main():
    """Main test execution."""
    tester = BackendQuotaSmokeTester()
    summary = tester.run_all_tests()
    
    # Exit with error code if critical issues found
    if summary["critical_issues"]:
        print(f"❌ Exiting with error due to {len(summary['critical_issues'])} critical issues")
        sys.exit(1)
    elif summary["failed_tests"] > 0:
        print(f"⚠️ Tests completed with {summary['failed_tests']} non-critical failures")
        sys.exit(0)
    else:
        print("✅ All tests passed successfully")
        sys.exit(0)

if __name__ == "__main__":
    main()