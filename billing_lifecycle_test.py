#!/usr/bin/env python3

import requests
import json
import sys
from typing import Dict, Any, Tuple

# Configuration
BASE_URL = "https://saas-payments-2.preview.emergentagent.com"

# Test users from review request
MANAGED_USER = {
    "email": "expired.checkout.cdc8caf5@trial.test", 
    "password": "Test1234!"
}

LEGACY_USER = {
    "email": "trial.db3ef59b76@example.com", 
    "password": "Test1234!"
}

class BillingTester:
    def __init__(self):
        self.session = requests.Session()
        self.test_results = []

    def log_test(self, test_name: str, success: bool, details: str, response_data: Any = None):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL" 
        print(f"{status} {test_name}")
        if not success or response_data:
            print(f"   Details: {details}")
        if response_data:
            print(f"   Response: {json.dumps(response_data, indent=2)}")
        print()
        
        self.test_results.append({
            "test_name": test_name,
            "success": success,
            "details": details,
            "response_data": response_data
        })

    def login_user(self, email: str, password: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Login user and return success, token, user_data"""
        try:
            response = self.session.post(
                f"{BASE_URL}/api/auth/login",
                json={"email": email, "password": password},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                token = data.get('access_token', '')
                return True, token, data
            else:
                return False, "", {"error": f"Status {response.status_code}: {response.text}"}
                
        except Exception as e:
            return False, "", {"error": f"Exception: {str(e)}"}

    def make_authenticated_request(self, method: str, endpoint: str, token: str, json_data: Dict = None) -> Tuple[int, Dict[str, Any]]:
        """Make authenticated request and return status_code, response_data"""
        try:
            headers = {"Authorization": f"Bearer {token}"}
            url = f"{BASE_URL}{endpoint}"
            
            if method.upper() == "GET":
                response = self.session.get(url, headers=headers, timeout=30)
            elif method.upper() == "POST":
                response = self.session.post(url, headers=headers, json=json_data, timeout=30)
            else:
                return 400, {"error": f"Unsupported method: {method}"}
                
            try:
                response_data = response.json()
            except:
                response_data = {"text": response.text, "content_type": response.headers.get('content-type', '')}
                
            return response.status_code, response_data
            
        except Exception as e:
            return 500, {"error": f"Request exception: {str(e)}"}

    def test_managed_user_subscription_endpoint(self):
        """Test 1: GET /api/billing/subscription for managed user"""
        success, token, user_data = self.login_user(MANAGED_USER["email"], MANAGED_USER["password"])
        
        if not success:
            self.log_test("Managed User Login", False, f"Login failed: {user_data}")
            return False, None
            
        self.log_test("Managed User Login", True, f"Login successful for {MANAGED_USER['email']}")
        
        # Test GET /api/billing/subscription
        status_code, response_data = self.make_authenticated_request("GET", "/api/billing/subscription", token)
        
        expected_fields = ["managed_subscription", "legacy_subscription", "portal_available"]
        
        if status_code == 200:
            # Check for expected fields and values
            has_managed = response_data.get("managed_subscription") is True
            legacy_subscription = response_data.get("legacy_subscription")
            has_portal = response_data.get("portal_available") is True
            
            print(f"DEBUG: managed_subscription={response_data.get('managed_subscription')}")
            print(f"DEBUG: legacy_subscription={legacy_subscription}") 
            print(f"DEBUG: portal_available={response_data.get('portal_available')}")
            print(f"DEBUG: has_managed={has_managed}, legacy_subscription={legacy_subscription}, has_portal={has_portal}")
            
            if has_managed and legacy_subscription is False and has_portal:
                self.log_test(
                    "GET /api/billing/subscription (managed user)", 
                    True, 
                    f"Correct flags: managed_subscription={has_managed}, legacy_subscription={legacy_subscription}, portal_available={has_portal}",
                    response_data
                )
                return True, token
            else:
                self.log_test(
                    "GET /api/billing/subscription (managed user)", 
                    False, 
                    f"Incorrect flags: managed_subscription={response_data.get('managed_subscription')}, legacy_subscription={response_data.get('legacy_subscription')}, portal_available={response_data.get('portal_available')}",
                    response_data
                )
        else:
            self.log_test(
                "GET /api/billing/subscription (managed user)", 
                False, 
                f"HTTP {status_code} error",
                response_data
            )
        
        return False, token

    def test_customer_portal_endpoint(self, token: str):
        """Test 2: POST /api/billing/customer-portal"""
        portal_data = {
            "origin_url": "https://saas-payments-2.preview.emergentagent.com/app/settings/billing",
            "return_path": "/app/settings/billing"
        }
        
        status_code, response_data = self.make_authenticated_request(
            "POST", "/api/billing/customer-portal", token, portal_data
        )
        
        if status_code == 200:
            portal_url = response_data.get("portal_url", "") or response_data.get("url", "")
            if portal_url and ("stripe.com" in portal_url or "billing.stripe.com" in portal_url):
                self.log_test(
                    "POST /api/billing/customer-portal", 
                    True, 
                    f"Stripe portal URL returned: {portal_url[:50]}...",
                    {"portal_url_domain": portal_url.split('/')[2] if '/' in portal_url else portal_url}
                )
                return True
            else:
                self.log_test(
                    "POST /api/billing/customer-portal", 
                    False, 
                    f"Invalid portal URL: {portal_url}",
                    response_data
                )
        else:
            self.log_test(
                "POST /api/billing/customer-portal", 
                False, 
                f"HTTP {status_code} error",
                response_data
            )
        
        return False

    def test_change_plan_managed_user(self, token: str):
        """Test 3: POST /api/billing/change-plan for managed user (upgrade/downgrade)"""
        
        # Test upgrade (immediate)
        upgrade_data = {
            "plan": "pro",
            "interval": "monthly", 
            "origin_url": "https://saas-payments-2.preview.emergentagent.com/app/settings/billing",
            "cancel_path": "/app/settings/billing"
        }
        
        status_code, response_data = self.make_authenticated_request(
            "POST", "/api/billing/change-plan", token, upgrade_data
        )
        
        upgrade_success = False
        if status_code == 200:
            message = response_data.get("message", "").lower()
            if "immediate" in message or "upgraded" in message:
                self.log_test(
                    "POST /api/billing/change-plan (upgrade)", 
                    True, 
                    f"Immediate upgrade message: {response_data.get('message', '')}",
                    response_data
                )
                upgrade_success = True
            else:
                self.log_test(
                    "POST /api/billing/change-plan (upgrade)", 
                    False, 
                    f"Missing immediate upgrade message: {response_data.get('message', '')}",
                    response_data
                )
        else:
            self.log_test(
                "POST /api/billing/change-plan (upgrade)", 
                False, 
                f"HTTP {status_code} error",
                response_data
            )
        
        # Test downgrade (scheduled)
        downgrade_data = {
            "plan": "starter",
            "interval": "monthly",
            "origin_url": "https://saas-payments-2.preview.emergentagent.com/app/settings/billing",
            "cancel_path": "/app/settings/billing"  
        }
        
        status_code, response_data = self.make_authenticated_request(
            "POST", "/api/billing/change-plan", token, downgrade_data
        )
        
        downgrade_success = False
        if status_code == 200:
            message = response_data.get("message", "").lower()
            if "scheduled" in message or "period" in message:
                self.log_test(
                    "POST /api/billing/change-plan (downgrade)", 
                    True, 
                    f"Scheduled downgrade message: {response_data.get('message', '')}",
                    response_data
                )
                downgrade_success = True
            else:
                self.log_test(
                    "POST /api/billing/change-plan (downgrade)", 
                    False, 
                    f"Missing scheduled downgrade message: {response_data.get('message', '')}",
                    response_data
                )
        else:
            self.log_test(
                "POST /api/billing/change-plan (downgrade)", 
                False, 
                f"HTTP {status_code} error",
                response_data
            )
        
        return upgrade_success and downgrade_success

    def test_cancel_subscription_managed_user(self, token: str):
        """Test 4: POST /api/billing/cancel-subscription for managed user"""
        status_code, response_data = self.make_authenticated_request(
            "POST", "/api/billing/cancel-subscription", token
        )
        
        if status_code == 200:
            message = response_data.get("message", "").lower()
            if "period" in message or "end" in message:
                self.log_test(
                    "POST /api/billing/cancel-subscription (managed user)", 
                    True, 
                    f"Period-end cancel message: {response_data.get('message', '')}",
                    response_data
                )
                return True
            else:
                self.log_test(
                    "POST /api/billing/cancel-subscription (managed user)", 
                    False, 
                    f"Missing period-end cancel message: {response_data.get('message', '')}",
                    response_data
                )
        else:
            self.log_test(
                "POST /api/billing/cancel-subscription (managed user)", 
                False, 
                f"HTTP {status_code} error",
                response_data
            )
        
        return False

    def test_legacy_user_guardrails(self):
        """Test 5: Legacy user guardrails"""
        success, token, user_data = self.login_user(LEGACY_USER["email"], LEGACY_USER["password"])
        
        if not success:
            self.log_test("Legacy User Login", False, f"Login failed: {user_data}")
            return False
            
        self.log_test("Legacy User Login", True, f"Login successful for {LEGACY_USER['email']}")
        
        # Test portal URL (should work)
        portal_data = {
            "origin_url": "https://saas-payments-2.preview.emergentagent.com/app/settings/billing",
            "return_path": "/app/settings/billing"
        }
        
        status_code, response_data = self.make_authenticated_request(
            "POST", "/api/billing/customer-portal", token, portal_data
        )
        
        portal_success = False
        if status_code == 200:
            portal_url = response_data.get("portal_url", "") or response_data.get("url", "")
            if portal_url and ("stripe.com" in portal_url or "billing.stripe.com" in portal_url):
                self.log_test(
                    "Legacy user portal access", 
                    True, 
                    "Portal URL returned for legacy user",
                    {"has_portal_url": bool(response_data.get("portal_url"))}
                )
                portal_success = True
            else:
                self.log_test(
                    "Legacy user portal access", 
                    False, 
                    f"Invalid portal URL: {portal_url}",
                    response_data
                )
        else:
            self.log_test(
                "Legacy user portal access", 
                False, 
                f"Portal access failed: HTTP {status_code}",
                response_data
            )
        
        # Test change-plan (should return legacy checkout_redirect)
        change_plan_data = {
            "plan": "pro",
            "interval": "monthly",
            "origin_url": "https://saas-payments-2.preview.emergentagent.com/app/settings/billing",
            "cancel_path": "/app/settings/billing"
        }
        
        status_code, response_data = self.make_authenticated_request(
            "POST", "/api/billing/change-plan", token, change_plan_data
        )
        
        change_plan_success = False
        if status_code == 200:
            if ("checkout_redirect" in response_data.get("action", "") or 
                "checkout_url" in response_data or 
                "url" in response_data and "checkout.stripe.com" in response_data.get("url", "")):
                self.log_test(
                    "Legacy user change-plan", 
                    True, 
                    "Legacy checkout redirect returned",
                    response_data
                )
                change_plan_success = True
            else:
                self.log_test(
                    "Legacy user change-plan", 
                    False, 
                    "Missing checkout redirect for legacy user",
                    response_data
                )
        else:
            self.log_test(
                "Legacy user change-plan", 
                False, 
                f"Change plan failed: HTTP {status_code}",
                response_data
            )
        
        # Test cancel (should return 409)
        status_code, response_data = self.make_authenticated_request(
            "POST", "/api/billing/cancel-subscription", token
        )
        
        cancel_success = False
        if status_code == 409:
            self.log_test(
                "Legacy user cancel subscription", 
                True, 
                "Correct 409 response for legacy user cancel",
                response_data
            )
            cancel_success = True
        else:
            self.log_test(
                "Legacy user cancel subscription", 
                False, 
                f"Expected 409, got {status_code}",
                response_data
            )
        
        return portal_success and change_plan_success and cancel_success

    def test_enterprise_change_plan(self):
        """Test 6: Enterprise change-plan returns 422"""
        # Use managed user token
        success, token, user_data = self.login_user(MANAGED_USER["email"], MANAGED_USER["password"])
        
        if not success:
            self.log_test("Enterprise test login", False, f"Login failed: {user_data}")
            return False
        
        enterprise_data = {
            "plan": "enterprise",
            "interval": "monthly",
            "origin_url": "https://saas-payments-2.preview.emergentagent.com/app/settings/billing",
            "cancel_path": "/app/settings/billing"
        }
        
        status_code, response_data = self.make_authenticated_request(
            "POST", "/api/billing/change-plan", token, enterprise_data
        )
        
        if status_code == 422:
            self.log_test(
                "Enterprise change-plan returns 422", 
                True, 
                "Correct 422 response for enterprise plan",
                response_data
            )
            return True
        else:
            self.log_test(
                "Enterprise change-plan returns 422", 
                False, 
                f"Expected 422, got {status_code}",
                response_data
            )
        
        return False

    def test_create_checkout_subscription_mode(self):
        """Test 7: /api/billing/create-checkout subscription mode"""
        # Use managed user
        success, token, user_data = self.login_user(MANAGED_USER["email"], MANAGED_USER["password"])
        
        if not success:
            self.log_test("Checkout test login", False, f"Login failed: {user_data}")
            return False
        
        checkout_data = {
            "plan": "pro",
            "interval": "monthly",
            "origin_url": "https://saas-payments-2.preview.emergentagent.com/app/settings/billing",
            "cancel_path": "/pricing"
        }
        
        status_code, response_data = self.make_authenticated_request(
            "POST", "/api/billing/create-checkout", token, checkout_data
        )
        
        if status_code == 200:
            checkout_url = response_data.get("checkout_url", "") or response_data.get("url", "")
            if checkout_url and ("stripe.com" in checkout_url or "checkout.stripe.com" in checkout_url):
                self.log_test(
                    "/api/billing/create-checkout subscription mode", 
                    True, 
                    f"Subscription checkout URL created: {checkout_url[:50]}...",
                    {"has_checkout_url": bool(checkout_url), "domain": checkout_url.split('/')[2] if '/' in checkout_url else ""}
                )
                return True
            else:
                self.log_test(
                    "/api/billing/create-checkout subscription mode", 
                    False, 
                    f"Invalid checkout URL: {checkout_url}",
                    response_data
                )
        else:
            self.log_test(
                "/api/billing/create-checkout subscription mode", 
                False, 
                f"HTTP {status_code} error", 
                response_data
            )
        
        return False

    def run_all_tests(self):
        """Run all billing lifecycle tests"""
        print("🧪 STRIPE SUBSCRIPTION LIFECYCLE BACKEND VALIDATION")
        print("=" * 60)
        print(f"Base URL: {BASE_URL}")
        print(f"Managed User: {MANAGED_USER['email']}")
        print(f"Legacy User: {LEGACY_USER['email']}")
        print()
        
        # Test 1: Managed user subscription endpoint
        print("Testing managed user endpoints...")
        managed_success, managed_token = self.test_managed_user_subscription_endpoint()
        
        # Test 2-4: Other managed user tests (if login succeeded)
        if managed_token:  # Run even if subscription test failed, as long as login worked
            import time
            time.sleep(2)  # Rate limiting protection
            self.test_customer_portal_endpoint(managed_token)
            time.sleep(2)
            self.test_change_plan_managed_user(managed_token)  
            time.sleep(2)
            self.test_cancel_subscription_managed_user(managed_token)
        
        # Test 5: Legacy user guardrails  
        print("\nTesting legacy user endpoints...")
        time.sleep(5)  # Extra delay for rate limiting
        self.test_legacy_user_guardrails()
        
        # Test 6: Enterprise change-plan 422
        print("\nTesting enterprise restrictions...")
        time.sleep(5)  # Extra delay for rate limiting 
        self.test_enterprise_change_plan()
        
        # Test 7: Create checkout subscription mode
        print("\nTesting checkout creation...")
        time.sleep(3)  # Extra delay for rate limiting
        self.test_create_checkout_subscription_mode()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total*100):.1f}%" if total > 0 else "N/A")
        print()
        
        # Detailed results by category
        managed_tests = [r for r in self.test_results if "managed" in r["test_name"].lower()]
        legacy_tests = [r for r in self.test_results if "legacy" in r["test_name"].lower()]
        
        managed_passed = sum(1 for r in managed_tests if r["success"])
        legacy_passed = sum(1 for r in legacy_tests if r["success"])
        
        print("📈 RESULTS BY CATEGORY:")
        print(f"  Managed User Tests: {managed_passed}/{len(managed_tests)} passed")
        print(f"  Legacy User Tests: {legacy_passed}/{len(legacy_tests)} passed")
        print()
        
        # Failed tests details
        failed_tests = [r for r in self.test_results if not r["success"]]
        if failed_tests:
            print("❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"  - {test['test_name']}: {test['details']}")
        else:
            print("✅ ALL TESTS PASSED!")


if __name__ == "__main__":
    tester = BillingTester()
    tester.run_all_tests()