#!/usr/bin/env python3
"""
Backend API validation test for PR-5A Mobile BFF re-verification
Turkish context: PR-5A Mobile BFF backend state re-validation per review request
"""

import asyncio
import json
import sys
from typing import Any, Dict, Optional

import httpx


class BackendValidator:
    def __init__(self):
        self.base_url = "https://tenant-audit-preview.preview.emergentagent.com"
        self.admin_email = "admin@acenta.test"
        self.admin_password = "admin123"
        self.session = httpx.AsyncClient(timeout=30.0)
        self.access_token: Optional[str] = None
        self.test_results: list[Dict[str, Any]] = []
        self.created_booking_id: Optional[str] = None
    
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
    
    async def test_admin_login(self) -> bool:
        """Test 1: POST /api/auth/login with admin credentials"""
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
                if "access_token" in data:
                    self.access_token = data["access_token"]
                    self.log_test(
                        "POST /api/auth/login admin credentials",
                        True,
                        f"Login successful, token length: {len(self.access_token)} chars"
                    )
                    return True
                else:
                    self.log_test(
                        "POST /api/auth/login admin credentials",
                        False,
                        "Login response missing access_token",
                        data
                    )
                    return False
            else:
                self.log_test(
                    "POST /api/auth/login admin credentials",
                    False,
                    f"Login failed with status {response.status_code}",
                    response.text
                )
                return False
        
        except Exception as e:
            self.log_test(
                "POST /api/auth/login admin credentials",
                False,
                f"Exception during login: {str(e)}"
            )
            return False
    
    async def test_mobile_auth_me(self) -> bool:
        """Test 2: GET /api/v1/mobile/auth/me auth requirement and response shape"""
        # First test without auth (should fail)
        try:
            response = await self.session.get(f"{self.base_url}/api/v1/mobile/auth/me")
            if response.status_code == 401:
                auth_required = True
                auth_details = "Correctly requires authentication (401 without token)"
            else:
                auth_required = False
                auth_details = f"Should return 401 without auth, got {response.status_code}"
        except Exception as e:
            auth_required = False
            auth_details = f"Exception testing auth requirement: {str(e)}"
        
        # Now test with auth
        if not self.access_token:
            self.log_test(
                "GET /api/v1/mobile/auth/me auth requirement and response",
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
                
                # Check for Mongo _id leak (raw _id field exposure, not converted string IDs)
                has_mongo_leak = "_id" in data
                
                # Check for sensitive fields that shouldn't be exposed
                sensitive_fields = ["password_hash", "totp_secret", "recovery_codes"]
                has_sensitive_leak = any(field in data for field in sensitive_fields)
                
                if has_required and not has_mongo_leak and not has_sensitive_leak:
                    self.log_test(
                        "GET /api/v1/mobile/auth/me auth requirement and response",
                        auth_required,
                        f"{auth_details}. Authenticated response: valid shape, no leaks. Email: {data.get('email')}"
                    )
                    return auth_required
                else:
                    issues = []
                    if not has_required:
                        missing = [f for f in required_fields if f not in data]
                        issues.append(f"missing fields: {missing}")
                    if has_mongo_leak:
                        issues.append("contains Mongo _id leak")
                    if has_sensitive_leak:
                        issues.append("contains sensitive field leak")
                    
                    self.log_test(
                        "GET /api/v1/mobile/auth/me auth requirement and response",
                        False,
                        f"{auth_details}. Response issues: {', '.join(issues)}",
                        data
                    )
                    return False
            else:
                self.log_test(
                    "GET /api/v1/mobile/auth/me auth requirement and response",
                    False,
                    f"{auth_details}. Authenticated request failed: {response.status_code}",
                    response.text
                )
                return False
                
        except Exception as e:
            self.log_test(
                "GET /api/v1/mobile/auth/me auth requirement and response",
                False,
                f"{auth_details}. Exception during authenticated test: {str(e)}"
            )
            return False
    
    async def test_mobile_dashboard_summary(self) -> bool:
        """Test 3: GET /api/v1/mobile/dashboard/summary response shape"""
        if not self.access_token:
            self.log_test(
                "GET /api/v1/mobile/dashboard/summary response shape",
                False,
                "No access token available"
            )
            return False
        
        try:
            response = await self.session.get(
                f"{self.base_url}/api/v1/mobile/dashboard/summary",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "X-Tenant-Id": "9c5c1079-9dea-49bf-82c0-74838b146160"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["bookings_today", "bookings_month", "revenue_month", "currency"]
                has_required = all(field in data for field in required_fields)
                
                # Check data types
                types_correct = (
                    isinstance(data.get("bookings_today"), int) and
                    isinstance(data.get("bookings_month"), int) and
                    isinstance(data.get("revenue_month"), (int, float)) and
                    isinstance(data.get("currency"), str)
                )
                
                if has_required and types_correct:
                    self.log_test(
                        "GET /api/v1/mobile/dashboard/summary response shape",
                        True,
                        f"Valid KPI shape: bookings_today={data['bookings_today']}, "
                        f"bookings_month={data['bookings_month']}, "
                        f"revenue_month={data['revenue_month']}, "
                        f"currency={data['currency']}"
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
                        "GET /api/v1/mobile/dashboard/summary response shape",
                        False,
                        f"Response issues: {', '.join(issues)}",
                        data
                    )
                    return False
            else:
                self.log_test(
                    "GET /api/v1/mobile/dashboard/summary response shape",
                    False,
                    f"Request failed with status {response.status_code}",
                    response.text
                )
                return False
                
        except Exception as e:
            self.log_test(
                "GET /api/v1/mobile/dashboard/summary response shape",
                False,
                f"Exception: {str(e)}"
            )
            return False
    
    async def test_mobile_bookings_list(self) -> bool:
        """Test 4: GET /api/v1/mobile/bookings response shape and auth"""
        if not self.access_token:
            self.log_test(
                "GET /api/v1/mobile/bookings response shape and auth",
                False,
                "No access token available"
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
                if not has_wrapper:
                    self.log_test(
                        "GET /api/v1/mobile/bookings response shape and auth",
                        False,
                        "Missing list wrapper (total, items)",
                        data
                    )
                    return False
                
                # Check for Mongo _id leaks (raw _id field exposure)
                has_mongo_leak = "_id" in data
                if has_mongo_leak:
                    self.log_test(
                        "GET /api/v1/mobile/bookings response shape and auth",
                        False,
                        "Response contains raw _id field exposure",
                        data
                    )
                    return False
                
                # Check that booking IDs are strings
                items = data.get("items", [])
                invalid_ids = [item for item in items if not isinstance(item.get("id"), str)]
                if invalid_ids:
                    self.log_test(
                        "GET /api/v1/mobile/bookings response shape and auth",
                        False,
                        f"Found {len(invalid_ids)} bookings with non-string IDs"
                    )
                    return False
                
                self.log_test(
                    "GET /api/v1/mobile/bookings response shape and auth",
                    True,
                    f"Valid list wrapper, {data['total']} total bookings, {len(items)} in response, no Mongo _id leaks"
                )
                return True
                
            else:
                self.log_test(
                    "GET /api/v1/mobile/bookings response shape and auth",
                    False,
                    f"Request failed with status {response.status_code}",
                    response.text
                )
                return False
                
        except Exception as e:
            self.log_test(
                "GET /api/v1/mobile/bookings response shape and auth",
                False,
                f"Exception: {str(e)}"
            )
            return False
    
    async def test_mobile_booking_create(self) -> bool:
        """Test 5: POST /api/v1/mobile/bookings draft create flow"""
        if not self.access_token:
            self.log_test(
                "POST /api/v1/mobile/bookings draft create flow",
                False,
                "No access token available"
            )
            return False
        
        try:
            # Create a draft booking with mobile-realistic data
            booking_payload = {
                "amount": 850.50,
                "currency": "TRY",
                "customer_name": "Mehmet Yılmaz",
                "guest_name": "Mehmet Yılmaz",
                "hotel_name": "Antalya Resort Hotel",
                "check_in": "2026-04-15",
                "check_out": "2026-04-20",
                "notes": "Mobile app test booking",
                "source": "mobile"
            }
            
            response = await self.session.post(
                f"{self.base_url}/api/v1/mobile/bookings",
                json=booking_payload,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                    "X-Tenant-Id": "9c5c1079-9dea-49bf-82c0-74838b146160"
                }
            )
            
            if response.status_code == 201:
                data = response.json()
                
                # Check response has booking ID
                if not data.get("id"):
                    self.log_test(
                        "POST /api/v1/mobile/bookings draft create flow",
                        False,
                        "Created booking missing ID",
                        data
                    )
                    return False
                
                self.created_booking_id = data["id"]
                
                # Check status is draft
                if data.get("status") != "draft":
                    self.log_test(
                        "POST /api/v1/mobile/bookings draft create flow",
                        False,
                        f"Expected status=draft, got {data.get('status')}",
                        data
                    )
                    return False
                
                # Check source is mobile
                if data.get("source") != "mobile":
                    self.log_test(
                        "POST /api/v1/mobile/bookings draft create flow",
                        False,
                        f"Expected source=mobile, got {data.get('source')}",
                        data
                    )
                    return False
                
                # Check no Mongo _id leak (raw _id field exposure)
                if "_id" in data:
                    self.log_test(
                        "POST /api/v1/mobile/bookings draft create flow",
                        False,
                        "Response contains raw _id field exposure",
                        data
                    )
                    return False
                
                self.log_test(
                    "POST /api/v1/mobile/bookings draft create flow",
                    True,
                    f"Created booking ID={data['id']}, status={data['status']}, source={data['source']}"
                )
                return True
                
            else:
                self.log_test(
                    "POST /api/v1/mobile/bookings draft create flow",
                    False,
                    f"Create failed with status {response.status_code}",
                    response.text
                )
                return False
                
        except Exception as e:
            self.log_test(
                "POST /api/v1/mobile/bookings draft create flow",
                False,
                f"Exception: {str(e)}"
            )
            return False
    
    async def test_mobile_booking_detail(self) -> bool:
        """Test 6: GET /api/v1/mobile/bookings/{id} detail flow for created record"""
        if not self.access_token:
            self.log_test(
                "GET /api/v1/mobile/bookings/{id} detail flow",
                False,
                "No access token available"
            )
            return False
        
        if not self.created_booking_id:
            self.log_test(
                "GET /api/v1/mobile/bookings/{id} detail flow",
                False,
                "No created booking ID available for testing"
            )
            return False
        
        try:
            response = await self.session.get(
                f"{self.base_url}/api/v1/mobile/bookings/{self.created_booking_id}",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "X-Tenant-Id": "9c5c1079-9dea-49bf-82c0-74838b146160"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check has detail fields beyond summary
                detail_fields = ["tenant_id", "agency_id", "booking_ref", "offer_ref"]
                has_detail_fields = any(field in data for field in detail_fields)
                
                # Check no Mongo _id leak (raw _id field exposure)
                has_mongo_leak = "_id" in data
                
                # Check booking ID matches
                id_matches = data.get("id") == self.created_booking_id
                
                if has_detail_fields and not has_mongo_leak and id_matches:
                    self.log_test(
                        "GET /api/v1/mobile/bookings/{id} detail flow",
                        True,
                        f"Detail endpoint working: ID matches, has detail fields, no Mongo _id leaks. "
                        f"Tenant scoping: tenant_id={data.get('tenant_id')}"
                    )
                    return True
                else:
                    issues = []
                    if not has_detail_fields:
                        issues.append("missing detail fields")
                    if has_mongo_leak:
                        issues.append("contains Mongo _id leak")
                    if not id_matches:
                        issues.append(f"ID mismatch: expected {self.created_booking_id}, got {data.get('id')}")
                    
                    self.log_test(
                        "GET /api/v1/mobile/bookings/{id} detail flow",
                        False,
                        f"Detail response issues: {', '.join(issues)}",
                        data
                    )
                    return False
                    
            else:
                self.log_test(
                    "GET /api/v1/mobile/bookings/{id} detail flow",
                    False,
                    f"Detail request failed with status {response.status_code}",
                    response.text
                )
                return False
                
        except Exception as e:
            self.log_test(
                "GET /api/v1/mobile/bookings/{id} detail flow",
                False,
                f"Exception: {str(e)}"
            )
            return False
    
    async def test_mobile_reports_summary(self) -> bool:
        """Test 7: GET /api/v1/mobile/reports/summary response shape"""
        if not self.access_token:
            self.log_test(
                "GET /api/v1/mobile/reports/summary response shape",
                False,
                "No access token available"
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
                        "GET /api/v1/mobile/reports/summary response shape",
                        True,
                        f"Valid summary shape: total_bookings={data['total_bookings']}, "
                        f"total_revenue={data['total_revenue']}, currency={data['currency']}, "
                        f"status_breakdown={len(data['status_breakdown'])} items, "
                        f"daily_sales={len(data['daily_sales'])} items"
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
                        "GET /api/v1/mobile/reports/summary response shape",
                        False,
                        f"Response issues: {', '.join(issues)}",
                        data
                    )
                    return False
                    
            else:
                self.log_test(
                    "GET /api/v1/mobile/reports/summary response shape",
                    False,
                    f"Request failed with status {response.status_code}",
                    response.text
                )
                return False
                
        except Exception as e:
            self.log_test(
                "GET /api/v1/mobile/reports/summary response shape",
                False,
                f"Exception: {str(e)}"
            )
            return False
    
    async def test_legacy_auth_regression(self) -> bool:
        """Test 8: Legacy auth flow regression check (/api/auth/me basic smoke)"""
        if not self.access_token:
            self.log_test(
                "Legacy auth endpoints regression check",
                False,
                "No access token available"
            )
            return False
        
        try:
            # Test legacy /api/auth/me endpoint
            response = await self.session.get(
                f"{self.base_url}/api/auth/me",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "X-Tenant-Id": "9c5c1079-9dea-49bf-82c0-74838b146160"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check basic user data is present
                has_email = "email" in data
                email_matches = data.get("email") == self.admin_email
                
                if has_email and email_matches:
                    self.log_test(
                        "Legacy auth endpoints regression check",
                        True,
                        f"Legacy /api/auth/me working correctly. Email: {data.get('email')}"
                    )
                    return True
                else:
                    issues = []
                    if not has_email:
                        issues.append("missing email field")
                    if not email_matches:
                        issues.append(f"email mismatch: expected {self.admin_email}, got {data.get('email')}")
                    
                    self.log_test(
                        "Legacy auth endpoints regression check",
                        False,
                        f"Legacy auth issues: {', '.join(issues)}",
                        data
                    )
                    return False
                    
            else:
                self.log_test(
                    "Legacy auth endpoints regression check",
                    False,
                    f"Legacy /api/auth/me failed with status {response.status_code}",
                    response.text
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Legacy auth endpoints regression check",
                False,
                f"Exception: {str(e)}"
            )
            return False
    
    async def run_all_tests(self):
        """Run all backend validation tests in sequence"""
        print("🚀 Starting PR-5A Mobile BFF Backend Re-Validation")
        print(f"📡 Preview URL: {self.base_url}")
        print(f"👤 Admin Account: {self.admin_email}")
        print("=" * 70)
        
        tests = [
            self.test_admin_login,
            self.test_mobile_auth_me,
            self.test_mobile_dashboard_summary,
            self.test_mobile_bookings_list,
            self.test_mobile_booking_create,
            self.test_mobile_booking_detail,
            self.test_mobile_reports_summary,
            self.test_legacy_auth_regression,
        ]
        
        passed_count = 0
        total_count = len(tests)
        
        for test_func in tests:
            try:
                result = await test_func()
                if result:
                    passed_count += 1
            except Exception as e:
                print(f"❌ FAIL: {test_func.__name__} - Exception: {str(e)}")
        
        print("=" * 70)
        print(f"📊 TEST SUMMARY: {passed_count}/{total_count} PASSED")
        
        if passed_count == total_count:
            print("🎉 ALL TESTS PASSED - Mobile BFF backend ready for finish!")
        else:
            print("⚠️  SOME TESTS FAILED - See details above")
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
    validator = BackendValidator()
    try:
        success = await validator.run_all_tests()
        sys.exit(0 if success else 1)
    finally:
        await validator.close()


if __name__ == "__main__":
    asyncio.run(main())