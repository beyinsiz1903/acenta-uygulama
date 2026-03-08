#!/usr/bin/env python3
"""
Backend Billing Lifecycle Smoke Test + API Validation
Turkish Review Request: Backend billing lifecycle smoke + API validation yap.

Test endpoints:
1. POST /api/auth/login 
2. GET /api/billing/subscription
3. POST /api/billing/cancel-subscription
4. POST /api/billing/reactivate-subscription  
5. POST /api/billing/customer-portal

Validation Requirements:
- billing/subscription shouldn't return 500 and should return managed subscription state
- cancel-subscription should produce cancel_at_period_end=true state
- reactivation should return to active state
- customer-portal should return valid Stripe portal URL
- Responses should contain Turkish user messages
- Note any stale Stripe reference guardrails backend issues
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
BASE_URL = "https://saas-billing-13.preview.emergentagent.com"
TEST_CREDENTIALS = {
    "email": "agent@acenta.test",
    "password": "agent123"
}

class BillingLifecycleTest:
    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'BillingLifecycleTest/1.0'
        })
        self.access_token = None
        self.test_results = []
        
    def log_result(self, test_name, status, details, expected=None, actual=None):
        """Log test result with timestamp"""
        result = {
            'test': test_name,
            'status': status,  # PASS, FAIL, WARN
            'details': details,
            'timestamp': datetime.now().isoformat(),
            'expected': expected,
            'actual': actual
        }
        self.test_results.append(result)
        
        status_symbol = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_symbol} {test_name}: {details}")
        
        if expected and actual:
            print(f"   Expected: {expected}")
            print(f"   Actual: {actual}")
        print()
    
    def make_request(self, method, endpoint, **kwargs):
        """Make HTTP request with proper error handling"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            # Add auth header if we have a token
            if self.access_token:
                self.session.headers['Authorization'] = f"Bearer {self.access_token}"
                
            response = self.session.request(method, url, **kwargs)
            
            # Log request details
            print(f"🔍 {method} {endpoint}")
            print(f"   Status: {response.status_code}")
            if response.headers.get('content-type', '').startswith('application/json'):
                try:
                    response_json = response.json()
                    print(f"   Response: {json.dumps(response_json, indent=2, ensure_ascii=False)[:500]}...")
                except:
                    print(f"   Response: {response.text[:200]}...")
            print()
            
            return response
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            return None

    def test_1_auth_login(self):
        """Test 1: POST /api/auth/login authentication"""
        test_name = "POST /api/auth/login authentication"
        
        try:
            response = self.make_request(
                'POST', 
                '/api/auth/login',
                json=TEST_CREDENTIALS
            )
            
            if not response:
                self.log_result(test_name, "FAIL", "Request failed - no response")
                return False
                
            if response.status_code != 200:
                self.log_result(
                    test_name, 
                    "FAIL", 
                    f"Authentication failed with status {response.status_code}",
                    "200 OK",
                    f"{response.status_code} {response.text[:100]}"
                )
                return False
                
            try:
                data = response.json()
                
                # Check for required fields
                required_fields = ['access_token']
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_result(
                        test_name,
                        "FAIL", 
                        f"Missing required fields: {missing_fields}",
                        "access_token field present",
                        f"Missing: {missing_fields}"
                    )
                    return False
                    
                self.access_token = data['access_token']
                
                self.log_result(
                    test_name,
                    "PASS",
                    f"Authentication successful. Token length: {len(self.access_token)} chars"
                )
                return True
                
            except json.JSONDecodeError:
                self.log_result(test_name, "FAIL", "Invalid JSON response")
                return False
                
        except Exception as e:
            self.log_result(test_name, "FAIL", f"Test exception: {str(e)}")
            return False

    def test_2_billing_subscription(self):
        """Test 2: GET /api/billing/subscription - should return managed subscription state, not 500"""
        test_name = "GET /api/billing/subscription"
        
        try:
            response = self.make_request('GET', '/api/billing/subscription')
            
            if not response:
                self.log_result(test_name, "FAIL", "Request failed - no response")
                return False
            
            # Critical: Should NOT return 500
            if response.status_code == 500:
                self.log_result(
                    test_name,
                    "FAIL",
                    "❌ CRITICAL: Endpoint returns 500 - This violates review requirement",
                    "Non-500 status code",
                    f"500 Server Error: {response.text[:200]}"
                )
                return False
                
            if response.status_code != 200:
                self.log_result(
                    test_name,
                    "FAIL",
                    f"Unexpected status code: {response.status_code}",
                    "200 OK",
                    f"{response.status_code}: {response.text[:200]}"
                )
                return False
                
            try:
                data = response.json()
                
                # Check for managed subscription state indicators
                expected_fields = ['managed_subscription', 'legacy_subscription', 'portal_available']
                present_fields = [field for field in expected_fields if field in data]
                
                if not present_fields:
                    self.log_result(
                        test_name,
                        "WARN",
                        f"No managed subscription state fields found. Available fields: {list(data.keys())}"
                    )
                else:
                    # Validate managed subscription state
                    managed = data.get('managed_subscription', False)
                    legacy = data.get('legacy_subscription', True)
                    portal_available = data.get('portal_available', False)
                    
                    state_details = f"managed_subscription={managed}, legacy_subscription={legacy}, portal_available={portal_available}"
                    
                    if managed and not legacy and portal_available:
                        self.log_result(
                            test_name,
                            "PASS",
                            f"✅ Managed subscription state returned correctly. {state_details}"
                        )
                    else:
                        self.log_result(
                            test_name,
                            "WARN",
                            f"Subscription state may not be fully managed. {state_details}"
                        )
                
                # Store subscription data for other tests
                self.subscription_data = data
                return True
                
            except json.JSONDecodeError:
                self.log_result(test_name, "FAIL", "Invalid JSON response")
                return False
                
        except Exception as e:
            self.log_result(test_name, "FAIL", f"Test exception: {str(e)}")
            return False

    def test_3_cancel_subscription(self):
        """Test 3: POST /api/billing/cancel-subscription - should produce cancel_at_period_end=true"""
        test_name = "POST /api/billing/cancel-subscription"
        
        try:
            response = self.make_request('POST', '/api/billing/cancel-subscription', json={})
            
            if not response:
                self.log_result(test_name, "FAIL", "Request failed - no response")
                return False
            
            if response.status_code not in [200, 409]:  # 409 might be expected if already cancelled
                self.log_result(
                    test_name,
                    "FAIL",
                    f"Cancel failed with status {response.status_code}",
                    "200 or 409 status",
                    f"{response.status_code}: {response.text[:200]}"
                )
                return False
                
            try:
                data = response.json()
                
                if response.status_code == 409:
                    # Check if it's already cancelled
                    if "already" in str(data).lower() or "zaten" in str(data).lower():
                        self.log_result(
                            test_name,
                            "PASS",
                            "Subscription already cancelled (409 conflict as expected)"
                        )
                        return True
                
                # Check for Turkish user messages
                message_text = str(data)
                has_turkish = any(word in message_text.lower() for word in ['abonelik', 'iptal', 'dönem', 'sona'])
                
                if has_turkish:
                    self.log_result(
                        test_name,
                        "PASS",
                        f"✅ Cancel request processed with Turkish messages. Response: {json.dumps(data, ensure_ascii=False)[:200]}"
                    )
                else:
                    self.log_result(
                        test_name,
                        "PASS",
                        f"Cancel request processed. Response: {json.dumps(data)[:200]}"
                    )
                
                # Store cancel response for validation
                self.cancel_response = data
                return True
                
            except json.JSONDecodeError:
                self.log_result(test_name, "FAIL", "Invalid JSON response")
                return False
                
        except Exception as e:
            self.log_result(test_name, "FAIL", f"Test exception: {str(e)}")
            return False

    def test_4_verify_cancel_state(self):
        """Test 4: Verify cancel_at_period_end=true state after cancellation"""
        test_name = "Verify cancel_at_period_end=true state"
        
        try:
            # Re-fetch subscription to check cancel state
            response = self.make_request('GET', '/api/billing/subscription')
            
            if not response or response.status_code != 200:
                self.log_result(test_name, "FAIL", "Could not fetch subscription after cancel")
                return False
                
            try:
                data = response.json()
                
                # Look for cancellation indicators
                cancel_indicators = [
                    'cancel_at_period_end', 'canceled_at_period_end', 
                    'scheduled_cancel', 'will_cancel', 'pending_cancel'
                ]
                
                found_indicators = {}
                for indicator in cancel_indicators:
                    if indicator in data:
                        found_indicators[indicator] = data[indicator]
                
                if found_indicators:
                    # Check if any indicator shows pending cancellation
                    has_pending_cancel = any(
                        str(value).lower() in ['true', '1'] 
                        for value in found_indicators.values()
                    )
                    
                    if has_pending_cancel:
                        self.log_result(
                            test_name,
                            "PASS", 
                            f"✅ Cancel_at_period_end state confirmed. Indicators: {found_indicators}"
                        )
                    else:
                        self.log_result(
                            test_name,
                            "WARN",
                            f"Cancellation indicators present but not showing pending state: {found_indicators}"
                        )
                else:
                    self.log_result(
                        test_name,
                        "WARN",
                        f"No explicit cancel_at_period_end indicators found. Response keys: {list(data.keys())}"
                    )
                
                return True
                
            except json.JSONDecodeError:
                self.log_result(test_name, "FAIL", "Invalid JSON response")
                return False
                
        except Exception as e:
            self.log_result(test_name, "FAIL", f"Test exception: {str(e)}")
            return False

    def test_5_reactivate_subscription(self):
        """Test 5: POST /api/billing/reactivate-subscription - should return to active state"""
        test_name = "POST /api/billing/reactivate-subscription"
        
        try:
            response = self.make_request('POST', '/api/billing/reactivate-subscription', json={})
            
            if not response:
                self.log_result(test_name, "FAIL", "Request failed - no response")
                return False
            
            if response.status_code not in [200, 409]:  # 409 might be expected if already active
                self.log_result(
                    test_name,
                    "FAIL",
                    f"Reactivate failed with status {response.status_code}",
                    "200 or 409 status",
                    f"{response.status_code}: {response.text[:200]}"
                )
                return False
                
            try:
                data = response.json()
                
                if response.status_code == 409:
                    # Check if it's already active
                    if "already" in str(data).lower() or "zaten" in str(data).lower():
                        self.log_result(
                            test_name,
                            "PASS",
                            "Subscription already active (409 conflict as expected)"
                        )
                        return True
                
                # Check for Turkish user messages
                message_text = str(data)
                has_turkish = any(word in message_text.lower() for word in ['abonelik', 'yeniden', 'aktif', 'başlat'])
                
                if has_turkish:
                    self.log_result(
                        test_name,
                        "PASS",
                        f"✅ Reactivate request processed with Turkish messages. Response: {json.dumps(data, ensure_ascii=False)[:200]}"
                    )
                else:
                    self.log_result(
                        test_name,
                        "PASS", 
                        f"Reactivate request processed. Response: {json.dumps(data)[:200]}"
                    )
                
                return True
                
            except json.JSONDecodeError:
                self.log_result(test_name, "FAIL", "Invalid JSON response")
                return False
                
        except Exception as e:
            self.log_result(test_name, "FAIL", f"Test exception: {str(e)}")
            return False

    def test_6_verify_active_state(self):
        """Test 6: Verify subscription returned to active state after reactivation"""
        test_name = "Verify active state after reactivation"
        
        try:
            # Re-fetch subscription to check active state
            response = self.make_request('GET', '/api/billing/subscription')
            
            if not response or response.status_code != 200:
                self.log_result(test_name, "FAIL", "Could not fetch subscription after reactivate")
                return False
                
            try:
                data = response.json()
                
                # Look for active state indicators
                active_indicators = [
                    'cancel_at_period_end', 'canceled_at_period_end',
                    'status', 'state', 'active'
                ]
                
                found_indicators = {}
                for indicator in active_indicators:
                    if indicator in data:
                        found_indicators[indicator] = data[indicator]
                
                # Check if subscription is now active (cancel_at_period_end should be false)
                cancel_at_period_end = data.get('cancel_at_period_end', data.get('canceled_at_period_end'))
                
                if cancel_at_period_end is False:
                    self.log_result(
                        test_name,
                        "PASS",
                        f"✅ Subscription returned to active state. cancel_at_period_end=false"
                    )
                elif cancel_at_period_end is None:
                    # Check other status indicators
                    status = data.get('status', data.get('state', 'unknown'))
                    if str(status).lower() in ['active', 'aktif']:
                        self.log_result(
                            test_name,
                            "PASS",
                            f"✅ Subscription active state confirmed via status: {status}"
                        )
                    else:
                        self.log_result(
                            test_name,
                            "WARN",
                            f"Active state unclear. Status indicators: {found_indicators}"
                        )
                else:
                    self.log_result(
                        test_name,
                        "WARN",
                        f"Subscription may still be pending cancellation: cancel_at_period_end={cancel_at_period_end}"
                    )
                
                return True
                
            except json.JSONDecodeError:
                self.log_result(test_name, "FAIL", "Invalid JSON response")
                return False
                
        except Exception as e:
            self.log_result(test_name, "FAIL", f"Test exception: {str(e)}")
            return False

    def test_7_customer_portal(self):
        """Test 7: POST /api/billing/customer-portal - should return valid Stripe portal URL"""
        test_name = "POST /api/billing/customer-portal"
        
        try:
            # Customer portal needs both return_path and origin_url
            payload = {
                "return_path": "/app/settings/billing",
                "origin_url": self.base_url
            }
            
            response = self.make_request('POST', '/api/billing/customer-portal', json=payload)
            
            if not response:
                self.log_result(test_name, "FAIL", "Request failed - no response")
                return False
            
            if response.status_code != 200:
                self.log_result(
                    test_name,
                    "FAIL",
                    f"Customer portal failed with status {response.status_code}",
                    "200 OK",
                    f"{response.status_code}: {response.text[:200]}"
                )
                return False
                
            try:
                data = response.json()
                
                # Look for portal URL
                portal_url = data.get('url', data.get('portal_url', data.get('redirect_url')))
                
                if not portal_url:
                    self.log_result(
                        test_name,
                        "FAIL",
                        f"No portal URL found in response. Available keys: {list(data.keys())}"
                    )
                    return False
                
                # Validate it's a proper Stripe portal URL
                if 'billing.stripe.com' in portal_url or 'stripe.com' in portal_url:
                    self.log_result(
                        test_name,
                        "PASS",
                        f"✅ Valid Stripe portal URL returned: {portal_url[:80]}..."
                    )
                else:
                    self.log_result(
                        test_name,
                        "WARN",
                        f"Portal URL doesn't appear to be Stripe domain: {portal_url}"
                    )
                
                return True
                
            except json.JSONDecodeError:
                self.log_result(test_name, "FAIL", "Invalid JSON response")
                return False
                
        except Exception as e:
            self.log_result(test_name, "FAIL", f"Test exception: {str(e)}")
            return False

    def test_8_stale_stripe_references(self):
        """Test 8: Check for stale Stripe reference guardrails backend issues"""
        test_name = "Check for stale Stripe reference guardrails"
        
        # This test will look for common indicators of stale Stripe references
        # by analyzing response patterns and error messages
        
        try:
            issues_found = []
            
            # Check subscription response for stale reference indicators
            if hasattr(self, 'subscription_data'):
                subscription_str = str(self.subscription_data)
                
                # Look for common stale reference patterns
                stale_patterns = [
                    'subscription_not_found', 'invalid_subscription_id',
                    'customer_not_found', 'invalid_customer_id',
                    'payment_method_not_found', 'setup_intent_failed'
                ]
                
                found_patterns = [pattern for pattern in stale_patterns if pattern in subscription_str.lower()]
                if found_patterns:
                    issues_found.extend(found_patterns)
            
            # Check for error responses that might indicate stale references
            for result in self.test_results:
                if result['status'] == 'FAIL' and result.get('actual'):
                    error_text = str(result['actual']).lower()
                    if any(word in error_text for word in ['not_found', 'invalid', 'expired', 'stale']):
                        issues_found.append(f"Potential stale reference in {result['test']}: {error_text[:100]}")
            
            if issues_found:
                self.log_result(
                    test_name,
                    "WARN",
                    f"⚠️ Potential stale Stripe reference issues detected: {issues_found}"
                )
            else:
                self.log_result(
                    test_name,
                    "PASS",
                    "No obvious stale Stripe reference guardrail issues detected"
                )
            
            return True
            
        except Exception as e:
            self.log_result(test_name, "FAIL", f"Test exception: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all billing lifecycle tests"""
        print("🚀 Starting Backend Billing Lifecycle Smoke Test + API Validation")
        print(f"📍 Base URL: {self.base_url}")
        print(f"👤 Test Account: {TEST_CREDENTIALS['email']}")
        print("=" * 80)
        print()
        
        # Test sequence
        tests = [
            self.test_1_auth_login,
            self.test_2_billing_subscription,
            self.test_3_cancel_subscription,
            self.test_4_verify_cancel_state,
            self.test_5_reactivate_subscription,
            self.test_6_verify_active_state,
            self.test_7_customer_portal,
            self.test_8_stale_stripe_references
        ]
        
        passed = 0
        failed = 0
        warnings = 0
        
        for test in tests:
            try:
                result = test()
                # Don't count failed auth as blocking other tests
                if not result and test == self.test_1_auth_login:
                    print("❌ Authentication failed - aborting remaining tests")
                    break
            except Exception as e:
                print(f"❌ Test {test.__name__} crashed: {e}")
                failed += 1
        
        # Count results
        for result in self.test_results:
            if result['status'] == 'PASS':
                passed += 1
            elif result['status'] == 'FAIL':
                failed += 1
            elif result['status'] == 'WARN':
                warnings += 1
        
        # Print summary
        print("=" * 80)
        print("📊 BACKEND BILLING LIFECYCLE TEST SUMMARY")
        print("=" * 80)
        print(f"✅ PASSED: {passed}")
        print(f"❌ FAILED: {failed}")
        print(f"⚠️  WARNINGS: {warnings}")
        print(f"📈 SUCCESS RATE: {(passed / (passed + failed + warnings) * 100):.1f}% (if warnings count as passes: {((passed + warnings) / (passed + failed + warnings) * 100):.1f}%)")
        print()
        
        # Critical validations from review request
        print("🎯 REVIEW REQUEST CRITICAL VALIDATIONS:")
        
        critical_checks = [
            ("billing/subscription 500 vermesin", not any(r['test'] == 'GET /api/billing/subscription' and '500' in str(r.get('actual', '')) for r in self.test_results)),
            ("managed subscription state dönsün", any(r['test'] == 'GET /api/billing/subscription' and r['status'] == 'PASS' for r in self.test_results)),
            ("cancel-subscription cancel_at_period_end=true durumu", any(r['test'] == 'Verify cancel_at_period_end=true state' and r['status'] == 'PASS' for r in self.test_results)),
            ("reactivation sonrası aktif state", any(r['test'] == 'Verify active state after reactivation' and r['status'] == 'PASS' for r in self.test_results)),
            ("customer-portal Stripe portal URL dönsün", any(r['test'] == 'POST /api/billing/customer-portal' and r['status'] == 'PASS' for r in self.test_results))
        ]
        
        for check_name, check_result in critical_checks:
            status_symbol = "✅" if check_result else "❌"
            print(f"{status_symbol} {check_name}: {'VALIDATED' if check_result else 'FAILED'}")
        
        print()
        
        if failed == 0:
            print("🎉 All backend billing lifecycle endpoints are working correctly!")
            return True
        else:
            print(f"⚠️ {failed} critical issues found that need attention.")
            return False

if __name__ == "__main__":
    tester = BillingLifecycleTest()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)