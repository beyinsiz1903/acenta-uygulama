#!/usr/bin/env python3
"""
Focused Backend Billing/Auth Regression Test
==========================================

Review Request Context:
- Base URL: https://worker-pool-dash.preview.emergentagent.com
- Credentials: agent@acenta.test / agent123
- Account State: pro / yearly / active (as verified manually)
- Recent Change: Frontend-only fix to stop agency users from calling admin-only whitelabel endpoint
- Goal: Backend regression confidence around auth + billing endpoints after this session

Test Requirements:
1. POST /api/auth/login with the agency account
2. GET /api/auth/me with the returned bearer token  
3. GET /api/billing/subscription and confirm it returns a valid billing payload in current account state
4. GET /api/billing/history and confirm timeline structure is valid
5. Check that unauthenticated access to billing endpoints is rejected correctly
6. Sanity-check that billing endpoints still behave consistently for the current yearly managed subscription state
"""

import json
import requests
import sys
from datetime import datetime
from typing import Any, Dict, Optional

# Configuration  
BASE_URL = "https://worker-pool-dash.preview.emergentagent.com"
TEST_CREDENTIALS = {
    "email": "agent@acenta.test",
    "password": "agent123" 
}

class FocusedBillingAuthRegressionRunner:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.auth_token = None
        self.subscription_data = None
        
    def log(self, message: str, success: bool = True):
        """Log test messages with status indicators"""
        status = "✅" if success else "❌"
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {status} {message}")
        
    def make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request with proper error handling"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.request(method, url, timeout=30, **kwargs)
            return response
        except Exception as e:
            self.log(f"Request failed: {method} {endpoint} - {str(e)}", False)
            raise
            
    def test_agency_login(self) -> bool:
        """
        Requirement 1: POST /api/auth/login with the agency account
        """
        try:
            self.log("Testing POST /api/auth/login with agency account...")
            response = self.make_request(
                'POST',
                '/api/auth/login',
                json=TEST_CREDENTIALS
            )
            
            if response.status_code != 200:
                self.log(f"Agency login failed: HTTP {response.status_code} - {response.text}", False)
                return False
                
            data = response.json()
            self.auth_token = data.get('access_token')
            
            if not self.auth_token:
                self.log("Login successful but no access_token received", False)
                return False
                
            # Update session headers for subsequent requests
            self.session.headers.update({
                'Authorization': f'Bearer {self.auth_token}'
            })
            
            # Validate login response structure
            required_fields = ['access_token', 'refresh_token']
            for field in required_fields:
                if field not in data:
                    self.log(f"Missing required field in login response: {field}", False)
                    return False
            
            self.log(f"Agency login successful - Token length: {len(self.auth_token)} chars")
            
            # Additional validation: confirm this is the expected agency user
            email = data.get('user', {}).get('email', 'unknown')
            if email != TEST_CREDENTIALS['email']:
                self.log(f"Login returned unexpected email: {email} (expected: {TEST_CREDENTIALS['email']})", False)
                return False
                
            return True
            
        except Exception as e:
            self.log(f"Agency login test error: {str(e)}", False)
            return False
    
    def test_auth_me_with_bearer_token(self) -> bool:
        """
        Requirement 2: GET /api/auth/me with the returned bearer token
        """
        if not self.auth_token:
            self.log("No auth token available for /api/auth/me test", False)
            return False
            
        try:
            self.log("Testing GET /api/auth/me with returned bearer token...")
            response = self.make_request('GET', '/api/auth/me')
            
            if response.status_code != 200:
                self.log(f"Auth/me failed: HTTP {response.status_code} - {response.text}", False)
                return False
                
            data = response.json()
            
            # Validate response structure
            required_fields = ['id', 'email', 'roles']
            for field in required_fields:
                if field not in data:
                    self.log(f"Missing required field in auth/me response: {field}", False)
                    return False
            
            email = data.get('email')
            roles = data.get('roles', [])
            
            if email != TEST_CREDENTIALS['email']:
                self.log(f"Email mismatch: expected {TEST_CREDENTIALS['email']}, got {email}", False)
                return False
                
            # Validate this is an agency user (not admin)
            if 'agency' not in str(roles).lower() and 'agent' not in str(roles).lower():
                self.log(f"User roles validation: {roles} - should contain agency/agent role", False)
                return False
            
            self.log(f"Auth/me successful - User: {email}, Roles: {roles}")
            return True
            
        except Exception as e:
            self.log(f"Auth/me test error: {str(e)}", False)
            return False
    
    def test_billing_subscription_valid_payload(self) -> bool:
        """
        Requirement 3: GET /api/billing/subscription and confirm valid billing payload in current state
        """
        if not self.auth_token:
            self.log("No auth token available for billing subscription test", False)
            return False
            
        try:
            self.log("Testing GET /api/billing/subscription for valid billing payload...")
            response = self.make_request('GET', '/api/billing/subscription')
            
            if response.status_code != 200:
                self.log(f"Billing subscription failed: HTTP {response.status_code} - {response.text}", False)
                return False
                
            data = response.json()
            self.subscription_data = data  # Store for later validation
            
            # Validate core billing payload structure
            required_fields = [
                'plan', 'status', 'managed_subscription', 'legacy_subscription',
                'can_cancel', 'portal_available', 'interval'
            ]
            for field in required_fields:
                if field not in data:
                    self.log(f"Missing required field in billing subscription response: {field}", False)
                    return False
            
            # Validate current account state (pro / yearly / active)
            plan = data.get('plan')
            status = data.get('status')
            interval = data.get('interval')
            managed = data.get('managed_subscription')
            
            # Check expected values per review request
            if plan != 'pro':
                self.log(f"Unexpected plan: expected 'pro', got '{plan}'", False)
                return False
                
            if status != 'active':
                self.log(f"Unexpected status: expected 'active', got '{status}'", False)
                return False
                
            if interval != 'yearly':
                self.log(f"Unexpected interval: expected 'yearly', got '{interval}'", False)
                return False
                
            if not managed:
                self.log(f"Unexpected managed subscription state: expected True, got {managed}", False)
                return False
            
            # Validate additional payload fields for consistency
            portal_available = data.get('portal_available')
            can_cancel = data.get('can_cancel')
            
            self.log(f"Billing subscription valid payload confirmed:")
            self.log(f"  Plan: {plan} (✓ pro)")
            self.log(f"  Status: {status} (✓ active)")
            self.log(f"  Interval: {interval} (✓ yearly)")
            self.log(f"  Managed: {managed} (✓ True)")
            self.log(f"  Portal Available: {portal_available}")
            self.log(f"  Can Cancel: {can_cancel}")
            
            return True
            
        except Exception as e:
            self.log(f"Billing subscription test error: {str(e)}", False)
            return False
    
    def test_billing_history_timeline_structure(self) -> bool:
        """
        Requirement 4: GET /api/billing/history and confirm timeline structure is valid
        """
        if not self.auth_token:
            self.log("No auth token available for billing history test", False)
            return False
            
        try:
            self.log("Testing GET /api/billing/history for valid timeline structure...")
            response = self.make_request('GET', '/api/billing/history')
            
            if response.status_code != 200:
                self.log(f"Billing history failed: HTTP {response.status_code} - {response.text}", False)
                return False
                
            data = response.json()
            
            # Validate timeline structure
            if 'items' not in data:
                self.log("Missing 'items' field in billing history response", False)
                return False
                
            items = data['items']
            if not isinstance(items, list):
                self.log("Billing history 'items' should be a list", False)
                return False
                
            # Validate timeline item structure (if items exist)
            if len(items) > 0:
                sample_item = items[0]
                required_item_fields = ['id', 'action', 'title', 'description', 'occurred_at']
                
                for field in required_item_fields:
                    if field not in sample_item:
                        self.log(f"Missing required field '{field}' in billing history timeline item", False)
                        return False
                
                # Validate date format (occurred_at field)
                try:
                    datetime.fromisoformat(sample_item['occurred_at'].replace('Z', '+00:00'))
                except ValueError:
                    self.log(f"Invalid date format in timeline item: {sample_item['occurred_at']}", False)
                    return False
                    
                self.log(f"Timeline structure validation:")
                self.log(f"  Sample item action: {sample_item.get('action')}")
                self.log(f"  Sample item occurred_at: {sample_item.get('occurred_at')}")
                self.log(f"  Sample item title: {sample_item.get('title')}")
                self.log(f"  Sample item description: {sample_item.get('description')[:50]}...")
                
            self.log(f"Billing history timeline structure valid - {len(items)} items returned")
            return True
            
        except Exception as e:
            self.log(f"Billing history test error: {str(e)}", False)
            return False
    
    def test_unauthenticated_access_rejection(self) -> bool:
        """
        Requirement 5: Check that unauthenticated access to billing endpoints is rejected correctly
        """
        try:
            self.log("Testing unauthenticated access rejection to billing endpoints...")
            
            # Create session without auth headers
            unauth_session = requests.Session()
            unauth_session.headers.update({
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            })
            
            billing_endpoints = [
                '/api/billing/subscription',
                '/api/billing/history'
            ]
            
            rejection_success = True
            
            for endpoint in billing_endpoints:
                url = f"{self.base_url}{endpoint}"
                response = unauth_session.get(url, timeout=30)
                
                if response.status_code != 401:
                    self.log(f"Improper auth protection: GET {endpoint} returned {response.status_code} (expected 401)", False)
                    rejection_success = False
                else:
                    self.log(f"✅ Proper auth protection: GET {endpoint} correctly returned 401")
            
            return rejection_success
            
        except Exception as e:
            self.log(f"Unauthenticated access test error: {str(e)}", False)
            return False
    
    def test_yearly_managed_subscription_consistency(self) -> bool:
        """
        Requirement 6: Sanity-check billing endpoints behave consistently for yearly managed subscription
        """
        if not self.subscription_data:
            self.log("No subscription data available for consistency test", False)
            return False
            
        try:
            self.log("Testing yearly managed subscription consistency...")
            
            # Re-fetch subscription to ensure consistency
            response = self.make_request('GET', '/api/billing/subscription')
            if response.status_code != 200:
                self.log("Failed to re-fetch subscription for consistency check", False)
                return False
                
            fresh_data = response.json()
            
            # Compare key fields for consistency
            consistency_fields = ['plan', 'status', 'interval', 'managed_subscription']
            
            for field in consistency_fields:
                original_value = self.subscription_data.get(field)
                fresh_value = fresh_data.get(field)
                
                if original_value != fresh_value:
                    self.log(f"Consistency error: {field} changed from {original_value} to {fresh_value}", False)
                    return False
                    
            # Validate yearly subscription specific behaviors
            if fresh_data.get('interval') == 'yearly':
                # For yearly subscriptions, certain fields should behave consistently
                managed = fresh_data.get('managed_subscription')
                portal_available = fresh_data.get('portal_available')
                
                if not managed:
                    self.log("Yearly subscription should be managed", False)
                    return False
                    
                if not portal_available:
                    self.log("Yearly managed subscription should have portal available", False)
                    return False
            
            # Test billing operations consistency for yearly subscription
            # Note: We won't actually cancel/modify to avoid disrupting the account state
            response = self.make_request('GET', '/api/billing/history')
            if response.status_code != 200:
                self.log("Billing history consistency check failed", False)
                return False
            
            self.log("Yearly managed subscription consistency validated:")
            self.log(f"  Subscription state remains: {fresh_data.get('plan')} / {fresh_data.get('interval')} / {fresh_data.get('status')}")
            self.log(f"  Managed subscription: {fresh_data.get('managed_subscription')}")
            self.log(f"  Portal available: {fresh_data.get('portal_available')}")
            
            return True
            
        except Exception as e:
            self.log(f"Consistency test error: {str(e)}", False)
            return False
    
    def run_focused_regression_test(self) -> bool:
        """Run the focused billing/auth regression test per review request"""
        self.log("=" * 90)
        self.log("FOCUSED BACKEND BILLING/AUTH REGRESSION TEST")
        self.log("Review Context: Frontend-only whitelabel endpoint fix - backend regression confidence")
        self.log("=" * 90)
        self.log(f"Base URL: {self.base_url}")
        self.log(f"Test Account: {TEST_CREDENTIALS['email']}")
        self.log(f"Expected State: pro / yearly / active")
        
        # Define test sequence per requirements
        tests = [
            ("1. POST /api/auth/login with agency account", self.test_agency_login),
            ("2. GET /api/auth/me with returned bearer token", self.test_auth_me_with_bearer_token),
            ("3. GET /api/billing/subscription valid payload (pro/yearly/active)", self.test_billing_subscription_valid_payload),
            ("4. GET /api/billing/history timeline structure validation", self.test_billing_history_timeline_structure),
            ("5. Unauthenticated access to billing endpoints rejection", self.test_unauthenticated_access_rejection),
            ("6. Yearly managed subscription consistency sanity check", self.test_yearly_managed_subscription_consistency)
        ]
        
        results = []
        for test_name, test_func in tests:
            self.log("-" * 80)
            self.log(f"Running: {test_name}")
            
            try:
                result = test_func()
                results.append((test_name, result))
                
                # If login fails, skip remaining authenticated tests
                if not result and "login" in test_name.lower():
                    self.log("Login failed, skipping remaining authenticated tests", False)
                    break
                    
            except Exception as e:
                self.log(f"Test execution error: {str(e)}", False)
                results.append((test_name, False))
        
        # Generate summary
        self.log("=" * 90)
        self.log("FOCUSED REGRESSION TEST RESULTS")
        self.log("=" * 90)
        
        passed = 0
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            self.log(f"{status} - {test_name}")
            if result:
                passed += 1
                
        self.log("-" * 90)
        self.log(f"Success Rate: {passed}/{total} tests passed ({100 * passed // total if total > 0 else 0}%)")
        
        if passed == total:
            self.log("🎉 ALL REGRESSION TESTS PASSED - No action required!")
            self.log("Backend auth + billing endpoints working correctly for yearly managed subscription")
            return True
        else:
            self.log("⚠️ REGRESSION ISSUES DETECTED - Review failures above", False)
            return False

def main():
    """Main test execution"""
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = BASE_URL
        
    test_runner = FocusedBillingAuthRegressionRunner(base_url)
    success = test_runner.run_focused_regression_test()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()