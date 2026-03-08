#!/usr/bin/env python3
"""
Backend API validation test for PR-6 Runtime Composition Refactor
Turkish context: PR-6 runtime composition refactor tamamlandı. server.py artık ince wrapper; 
API composition backend/app/bootstrap/api_app.py'ye taşındı. Auth/session/tenant ve Mobile BFF davranış değişmeden kalması hedefi.

Testing:
1. POST /api/auth/login
2. GET /api/auth/me
3. GET /api/v1/mobile/auth/me
4. GET /api/v1/mobile/bookings
5. GET /api/v1/mobile/reports/summary
6. Unauthorized guard kontrolü
7. Root API smoke test (/health)
8. Auth/session/tenant/Mobile BFF regresyonu check
"""

import asyncio
import json
import sys
from typing import Any, Dict, Optional

import httpx


class PR6BackendValidator:
    def __init__(self):
        self.base_url = "https://acenta-billing.preview.emergentagent.com"
        self.admin_email = "admin@acenta.test"
        self.admin_password = "admin123"
        self.session = httpx.AsyncClient(timeout=30.0)
        self.access_token: Optional[str] = None
        self.test_results: list[Dict[str, Any]] = []
    
    def log_test(self, test_name: str, passed: bool, details: str = "", response_data: Any = None):
        """Log test result with details"""
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "details": details,
            "response_data": response_data
        })
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if details:
            print(f"   Details: {details}")
        if response_data and not passed:
            print(f"   Response: {json.dumps(response_data, indent=2)}")
    
    async def test_1_auth_login(self) -> bool:
        """Test 1: POST /api/auth/login"""
        try:
            response = await self.session.post(
                f"{self.base_url}/api/auth/login",
                json={
                    "email": self.admin_email,
                    "password": self.admin_password
                },
                headers={
                    "Content-Type": "application/json",
                    "X-Tenant-Id": "9c5c1079-9dea-49bf-82c0-74838b146160"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if "access_token" in data and "refresh_token" in data:
                    self.access_token = data["access_token"]
                    self.log_test(
                        "1. POST /api/auth/login",
                        True,
                        f"Login successful, access_token: {len(self.access_token)} chars, refresh_token: {len(data['refresh_token'])} chars"
                    )
                    return True
                else:
                    self.log_test(
                        "1. POST /api/auth/login",
                        False,
                        "Missing access_token or refresh_token in response",
                        data
                    )
                    return False
            else:
                self.log_test(
                    "1. POST /api/auth/login",
                    False,
                    f"Login failed with status {response.status_code}",
                    response.text
                )
                return False
        
        except Exception as e:
            self.log_test(
                "1. POST /api/auth/login",
                False,
                f"Exception during login: {str(e)}"
            )
            return False
    
    async def test_2_auth_me(self) -> bool:
        """Test 2: GET /api/auth/me"""
        if not self.access_token:
            self.log_test(
                "2. GET /api/auth/me",
                False,
                "No access token available for testing"
            )
            return False
        
        try:
            response = await self.session.get(
                f"{self.base_url}/api/auth/me",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "X-Tenant-Id": "9c5c1079-9dea-49bf-82c0-74838b146160"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if "email" in data and data["email"] == self.admin_email:
                    self.log_test(
                        "2. GET /api/auth/me",
                        True,
                        f"Auth/me working correctly. Email: {data['email']}, roles: {data.get('roles', [])}"
                    )
                    return True
                else:
                    self.log_test(
                        "2. GET /api/auth/me",
                        False,
                        f"Email mismatch or missing. Expected: {self.admin_email}, got: {data.get('email')}",
                        data
                    )
                    return False
            else:
                self.log_test(
                    "2. GET /api/auth/me",
                    False,
                    f"Auth/me failed with status {response.status_code}",
                    response.text
                )
                return False
                
        except Exception as e:
            self.log_test(
                "2. GET /api/auth/me",
                False,
                f"Exception: {str(e)}"
            )
            return False
    
    async def test_3_mobile_auth_me(self) -> bool:
        """Test 3: GET /api/v1/mobile/auth/me"""
        if not self.access_token:
            self.log_test(
                "3. GET /api/v1/mobile/auth/me",
                False,
                "No access token available for testing"
            )
            return False
        
        try:
            response = await self.session.get(
                f"{self.base_url}/api/v1/mobile/auth/me",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "X-Tenant-Id": "9c5c1079-9dea-49bf-82c0-74838b146160"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["id", "email", "roles", "organization_id"]
                has_required = all(field in data for field in required_fields)
                
                # Check for Mongo _id leak
                has_mongo_leak = "_id" in data
                
                # Check for sensitive fields
                sensitive_fields = ["password_hash", "totp_secret", "recovery_codes"]
                has_sensitive_leak = any(field in data for field in sensitive_fields)
                
                if has_required and not has_mongo_leak and not has_sensitive_leak:
                    self.log_test(
                        "3. GET /api/v1/mobile/auth/me",
                        True,
                        f"Mobile auth/me working correctly. Email: {data['email']}, no leaks detected"
                    )
                    return True
                else:
                    issues = []
                    if not has_required:
                        missing = [f for f in required_fields if f not in data]
                        issues.append(f"missing fields: {missing}")
                    if has_mongo_leak:
                        issues.append("contains raw Mongo _id leak")
                    if has_sensitive_leak:
                        issues.append("contains sensitive field leak")
                    
                    self.log_test(
                        "3. GET /api/v1/mobile/auth/me",
                        False,
                        f"Mobile auth/me issues: {', '.join(issues)}",
                        data
                    )
                    return False
            else:
                self.log_test(
                    "3. GET /api/v1/mobile/auth/me",
                    False,
                    f"Mobile auth/me failed with status {response.status_code}",
                    response.text
                )
                return False
                
        except Exception as e:
            self.log_test(
                "3. GET /api/v1/mobile/auth/me",
                False,
                f"Exception: {str(e)}"
            )
            return False
    
    async def test_4_mobile_bookings(self) -> bool:
        """Test 4: GET /api/v1/mobile/bookings"""
        if not self.access_token:
            self.log_test(
                "4. GET /api/v1/mobile/bookings",
                False,
                "No access token available for testing"
            )
            return False
        
        try:
            response = await self.session.get(
                f"{self.base_url}/api/v1/mobile/bookings",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "X-Tenant-Id": "9c5c1079-9dea-49bf-82c0-74838b146160"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check list wrapper structure
                has_wrapper = "total" in data and "items" in data
                
                # Check for Mongo _id leaks
                has_mongo_leak = "_id" in data
                
                # Check booking IDs are strings
                items = data.get("items", [])
                invalid_ids = [item for item in items if not isinstance(item.get("id"), str)]
                
                if has_wrapper and not has_mongo_leak and not invalid_ids:
                    self.log_test(
                        "4. GET /api/v1/mobile/bookings",
                        True,
                        f"Mobile bookings working correctly. Total: {data['total']}, items: {len(items)}, no leaks"
                    )
                    return True
                else:
                    issues = []
                    if not has_wrapper:
                        issues.append("missing list wrapper (total, items)")
                    if has_mongo_leak:
                        issues.append("contains raw Mongo _id leak")
                    if invalid_ids:
                        issues.append(f"{len(invalid_ids)} bookings with non-string IDs")
                    
                    self.log_test(
                        "4. GET /api/v1/mobile/bookings",
                        False,
                        f"Mobile bookings issues: {', '.join(issues)}",
                        data
                    )
                    return False
            else:
                self.log_test(
                    "4. GET /api/v1/mobile/bookings",
                    False,
                    f"Mobile bookings failed with status {response.status_code}",
                    response.text
                )
                return False
                
        except Exception as e:
            self.log_test(
                "4. GET /api/v1/mobile/bookings",
                False,
                f"Exception: {str(e)}"
            )
            return False
    
    async def test_5_mobile_reports_summary(self) -> bool:
        """Test 5: GET /api/v1/mobile/reports/summary"""
        if not self.access_token:
            self.log_test(
                "5. GET /api/v1/mobile/reports/summary",
                False,
                "No access token available for testing"
            )
            return False
        
        try:
            response = await self.session.get(
                f"{self.base_url}/api/v1/mobile/reports/summary",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "X-Tenant-Id": "9c5c1079-9dea-49bf-82c0-74838b146160"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check required summary fields
                required_fields = ["total_bookings", "total_revenue", "currency", "status_breakdown", "daily_sales"]
                has_required = all(field in data for field in required_fields)
                
                # Check data types
                types_correct = (
                    isinstance(data.get("total_bookings"), int) and
                    isinstance(data.get("total_revenue"), (int, float)) and
                    isinstance(data.get("currency"), str) and
                    isinstance(data.get("status_breakdown"), list) and
                    isinstance(data.get("daily_sales"), list)
                )
                
                if has_required and types_correct:
                    self.log_test(
                        "5. GET /api/v1/mobile/reports/summary",
                        True,
                        f"Mobile reports working correctly. Bookings: {data['total_bookings']}, "
                        f"revenue: {data['total_revenue']} {data['currency']}, "
                        f"breakdowns: {len(data['status_breakdown'])} status, {len(data['daily_sales'])} daily"
                    )
                    return True
                else:
                    issues = []
                    if not has_required:
                        missing = [f for f in required_fields if f not in data]
                        issues.append(f"missing fields: {missing}")
                    if not types_correct:
                        issues.append("incorrect data types")
                    
                    self.log_test(
                        "5. GET /api/v1/mobile/reports/summary",
                        False,
                        f"Mobile reports issues: {', '.join(issues)}",
                        data
                    )
                    return False
            else:
                self.log_test(
                    "5. GET /api/v1/mobile/reports/summary",
                    False,
                    f"Mobile reports failed with status {response.status_code}",
                    response.text
                )
                return False
                
        except Exception as e:
            self.log_test(
                "5. GET /api/v1/mobile/reports/summary",
                False,
                f"Exception: {str(e)}"
            )
            return False
    
    async def test_6_unauthorized_guards(self) -> bool:
        """Test 6: Unauthorized guard kontrolü"""
        try:
            # Test auth/me without token
            response1 = await self.session.get(f"{self.base_url}/api/auth/me")
            auth_me_guard = response1.status_code == 401
            
            # Test mobile auth/me without token
            response2 = await self.session.get(f"{self.base_url}/api/v1/mobile/auth/me")
            mobile_auth_me_guard = response2.status_code == 401
            
            if auth_me_guard and mobile_auth_me_guard:
                self.log_test(
                    "6. Unauthorized guard kontrolü",
                    True,
                    "Auth guards working correctly. /api/auth/me: 401, /api/v1/mobile/auth/me: 401"
                )
                return True
            else:
                issues = []
                if not auth_me_guard:
                    issues.append(f"/api/auth/me returned {response1.status_code} (expected 401)")
                if not mobile_auth_me_guard:
                    issues.append(f"/api/v1/mobile/auth/me returned {response2.status_code} (expected 401)")
                
                self.log_test(
                    "6. Unauthorized guard kontrolü",
                    False,
                    f"Auth guard issues: {', '.join(issues)}"
                )
                return False
                
        except Exception as e:
            self.log_test(
                "6. Unauthorized guard kontrolü",
                False,
                f"Exception: {str(e)}"
            )
            return False
    
    async def test_7_root_api_smoke(self) -> bool:
        """Test 7: Root API smoke test (/health)"""
        try:
            # Test health endpoint
            response = await self.session.get(f"{self.base_url}/api/health")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ok":
                    self.log_test(
                        "7. Root API smoke test (/health)",
                        True,
                        f"Health endpoint working correctly. Status: {data['status']}"
                    )
                    return True
                else:
                    self.log_test(
                        "7. Root API smoke test (/health)",
                        False,
                        f"Health endpoint returned unexpected status: {data}",
                        data
                    )
                    return False
            else:
                self.log_test(
                    "7. Root API smoke test (/health)",
                    False,
                    f"Health endpoint failed with status {response.status_code}",
                    response.text
                )
                return False
                
        except Exception as e:
            self.log_test(
                "7. Root API smoke test (/health)",
                False,
                f"Exception: {str(e)}"
            )
            return False
    
    async def test_8_regression_check(self) -> bool:
        """Test 8: Auth/session/tenant/Mobile BFF regresyonu check"""
        if not self.access_token:
            self.log_test(
                "8. Auth/session/tenant/Mobile BFF regresyonu check",
                False,
                "No access token available for regression testing"
            )
            return False
        
        try:
            # Test auth regression - GET /api/auth/me should work
            auth_response = await self.session.get(
                f"{self.base_url}/api/auth/me",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "X-Tenant-Id": "9c5c1079-9dea-49bf-82c0-74838b146160"
                }
            )
            auth_working = auth_response.status_code == 200
            
            # Test mobile BFF regression - GET /api/v1/mobile/auth/me should work
            mobile_response = await self.session.get(
                f"{self.base_url}/api/v1/mobile/auth/me",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "X-Tenant-Id": "9c5c1079-9dea-49bf-82c0-74838b146160"
                }
            )
            mobile_working = mobile_response.status_code == 200
            
            # Test admin endpoint (tenant context)
            admin_response = await self.session.get(
                f"{self.base_url}/api/admin/agencies",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "X-Tenant-Id": "9c5c1079-9dea-49bf-82c0-74838b146160"
                }
            )
            admin_working = admin_response.status_code == 200
            
            if auth_working and mobile_working and admin_working:
                agencies_count = len(admin_response.json()) if admin_working else 0
                self.log_test(
                    "8. Auth/session/tenant/Mobile BFF regresyonu check",
                    True,
                    f"No regression detected. Auth: ✅, Mobile BFF: ✅, Tenant context: ✅ ({agencies_count} agencies)"
                )
                return True
            else:
                issues = []
                if not auth_working:
                    issues.append(f"Auth regression: /api/auth/me returned {auth_response.status_code}")
                if not mobile_working:
                    issues.append(f"Mobile BFF regression: /api/v1/mobile/auth/me returned {mobile_response.status_code}")
                if not admin_working:
                    issues.append(f"Tenant regression: /api/admin/agencies returned {admin_response.status_code}")
                
                self.log_test(
                    "8. Auth/session/tenant/Mobile BFF regresyonu check",
                    False,
                    f"Regression detected: {', '.join(issues)}"
                )
                return False
                
        except Exception as e:
            self.log_test(
                "8. Auth/session/tenant/Mobile BFF regresyonu check",
                False,
                f"Exception: {str(e)}"
            )
            return False
    
    async def run_all_tests(self):
        """Run all PR-6 backend validation tests in sequence"""
        print("🚀 Starting PR-6 Runtime Composition Refactor Backend Validation")
        print(f"📡 Preview URL: {self.base_url}")
        print(f"👤 Admin Account: {self.admin_email}")
        print("🔧 PR-6 Context: server.py → bootstrap/api_app.py composition refactor")
        print("=" * 80)
        
        tests = [
            self.test_1_auth_login,
            self.test_2_auth_me,
            self.test_3_mobile_auth_me,
            self.test_4_mobile_bookings,
            self.test_5_mobile_reports_summary,
            self.test_6_unauthorized_guards,
            self.test_7_root_api_smoke,
            self.test_8_regression_check,
        ]
        
        passed_count = 0
        total_count = len(tests)
        
        for test_func in tests:
            try:
                result = await test_func()
                if result:
                    passed_count += 1
                print()  # Empty line between tests for readability
            except Exception as e:
                print(f"❌ FAIL: {test_func.__name__} - Exception: {str(e)}")
                print()
        
        print("=" * 80)
        print(f"📊 PR-6 TEST SUMMARY: {passed_count}/{total_count} PASSED")
        
        if passed_count == total_count:
            print("🎉 ALL TESTS PASSED - PR-6 runtime composition refactor successful!")
            print("✅ Auth/session/tenant ve Mobile BFF davranış değişmeden kaldı")
            print("✅ server.py → bootstrap/api_app.py refactor working correctly")
        else:
            print("⚠️  SOME TESTS FAILED - PR-6 regression detected")
            failed_tests = [r for r in self.test_results if not r["passed"]]
            print(f"   Failed tests: {len(failed_tests)}")
            for failed in failed_tests:
                print(f"   - {failed['test']}: {failed['details']}")
        
        return passed_count == total_count
    
    async def close(self):
        """Clean up HTTP client"""
        await self.session.aclose()


async def main():
    """Main test runner"""
    validator = PR6BackendValidator()
    try:
        success = await validator.run_all_tests()
        sys.exit(0 if success else 1)
    finally:
        await validator.close()


if __name__ == "__main__":
    asyncio.run(main())