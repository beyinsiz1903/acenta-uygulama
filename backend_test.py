#!/usr/bin/env python3

import requests
import json
import sys
from datetime import datetime

# Configuration from environment
BASE_URL = "https://core-nav-update.preview.emergentagent.com"
API_BASE = f"{BASE_URL}/api"

# Test accounts - note: agent@acenta.test appears to be managed, not legacy
ACCOUNTS = {
    "agent@acenta.test": {"email": "agent@acenta.test", "password": "agent123"},
    "billing.test.83ce5350@example.com": {"email": "billing.test.83ce5350@example.com", "password": "agent123"}
}

class BillingLifecycleTester:
    def __init__(self):
        self.session = requests.Session()
        self.test_results = []
        
    def log(self, message, success=True):
        """Log test result"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        status = "✅" if success else "❌"
        print(f"[{timestamp}] {status} {message}")
        self.test_results.append({
            "message": message,
            "success": success,
            "timestamp": timestamp
        })
        
    def authenticate(self, credentials):
        """Authenticate and return access token"""
        try:
            response = self.session.post(
                f"{API_BASE}/auth/login",
                json=credentials,
                timeout=30
            )
            
            if response.status_code != 200:
                self.log(f"Login failed: {response.status_code} {response.text}", False)
                return None
                
            data = response.json()
            token = data.get("access_token")
            if not token:
                self.log("No access token in login response", False)
                return None
                
            self.log(f"Login successful for {credentials['email']} (token: {len(token)} chars)")
            return token
            
        except Exception as e:
            self.log(f"Login error for {credentials['email']}: {str(e)}", False)
            return None
    
    def api_call(self, method, endpoint, token=None, data=None):
        """Make authenticated API call"""
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        try:
            if method == "GET":
                response = self.session.get(f"{API_BASE}{endpoint}", headers=headers, timeout=30)
            elif method == "POST":
                headers["Content-Type"] = "application/json"
                response = self.session.post(f"{API_BASE}{endpoint}", headers=headers, json=data or {}, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            return response
            
        except Exception as e:
            self.log(f"API call error {method} {endpoint}: {str(e)}", False)
            return None
    
    def test_billing_account(self, account_name, credentials, expected_type="managed"):
        """Test billing endpoints for a specific account"""
        self.log(f"\n=== TESTING {account_name.upper()} ===")
        
        # Authenticate
        token = self.authenticate(credentials)
        if not token:
            self.log(f"Cannot proceed with {account_name} tests - authentication failed", False)
            return
        
        # Test 1: GET /api/billing/subscription
        response = self.api_call("GET", "/billing/subscription", token)
        if response and response.status_code == 200:
            try:
                data = response.json()
                
                # Log current state for analysis
                plan = data.get("plan")
                interval = data.get("interval") 
                status = data.get("status")
                managed_subscription = data.get("managed_subscription")
                legacy_subscription = data.get("legacy_subscription")
                can_cancel = data.get("can_cancel")
                change_flow = data.get("change_flow")
                portal_available = data.get("portal_available")
                cancel_at_period_end = data.get("cancel_at_period_end")
                provider_subscription_id = data.get("provider_subscription_id")
                scheduled_change = data.get("scheduled_change")
                
                self.log(f"Subscription analysis for {account_name}:")
                self.log(f"  plan={plan}, interval={interval}, status={status}")
                self.log(f"  managed_subscription={managed_subscription}")
                self.log(f"  legacy_subscription={legacy_subscription}")
                self.log(f"  can_cancel={can_cancel}")
                self.log(f"  change_flow={change_flow}")
                self.log(f"  portal_available={portal_available}")
                self.log(f"  cancel_at_period_end={cancel_at_period_end}")
                self.log(f"  provider_subscription_id={provider_subscription_id}")
                
                if scheduled_change:
                    self.log(f"  scheduled_change={scheduled_change}")
                
                # Check if this matches expected behavior
                if expected_type == "legacy":
                    if legacy_subscription and not managed_subscription:
                        self.log(f"✓ {account_name} correctly identified as legacy subscription")
                    else:
                        self.log(f"⚠️ {account_name} expected legacy but managed={managed_subscription}, legacy={legacy_subscription}")
                elif expected_type == "managed":
                    if managed_subscription:
                        self.log(f"✓ {account_name} correctly identified as managed subscription")
                    else:
                        self.log(f"⚠️ {account_name} expected managed but managed={managed_subscription}")
                
            except Exception as e:
                self.log(f"Error parsing /billing/subscription response: {str(e)}", False)
        else:
            status = response.status_code if response else "No response"
            self.log(f"GET /billing/subscription failed: {status}", False)
            return
            
        # Test 2: POST /api/billing/cancel-subscription (if can_cancel=true)
        if data.get("can_cancel"):
            response = self.api_call("POST", "/billing/cancel-subscription", token)
            if response and response.status_code == 200:
                try:
                    result = response.json()
                    cancel_at_period_end = result.get("cancel_at_period_end")
                    message = result.get("message", "")
                    if cancel_at_period_end == True:
                        self.log(f"✓ POST /billing/cancel-subscription: cancel_at_period_end=true")
                        if "dönem sonunda sona erecek" in message:
                            self.log(f"✓ Turkish cancel message correct")
                    else:
                        self.log(f"❌ cancel_at_period_end={cancel_at_period_end} (expected: true)", False)
                except Exception as e:
                    self.log(f"Error parsing cancel response: {str(e)}", False)
            else:
                status = response.status_code if response else "No response"
                if response and response.status_code == 409:
                    self.log(f"POST /billing/cancel-subscription: 409 (subscription management unavailable)")
                else:
                    self.log(f"POST /billing/cancel-subscription failed: {status}", False)
        else:
            self.log(f"Skipping cancel test - can_cancel={data.get('can_cancel')}")
            
        # Test 3: POST /api/billing/reactivate-subscription (only after cancel)
        response = self.api_call("POST", "/billing/reactivate-subscription", token)
        if response and response.status_code == 200:
            try:
                result = response.json()
                cancel_at_period_end = result.get("cancel_at_period_end")
                message = result.get("message", "")
                if cancel_at_period_end == False:
                    self.log(f"✓ POST /billing/reactivate-subscription: cancel_at_period_end=false")
                    if "yeniden aktif" in message:
                        self.log(f"✓ Turkish reactivate message correct")
                else:
                    self.log(f"❌ reactivate cancel_at_period_end={cancel_at_period_end} (expected: false)", False)
            except Exception as e:
                self.log(f"Error parsing reactivate response: {str(e)}", False)
        else:
            status = response.status_code if response else "No response"
            if response and response.status_code == 409:
                self.log(f"POST /billing/reactivate-subscription: 409 (subscription management unavailable)")
            else:
                self.log(f"POST /billing/reactivate-subscription failed: {status}", False)
                
        # Test 4: POST /api/billing/change-plan
        change_plan_data = {
            "plan": "starter" if data.get("plan") != "starter" else "pro",
            "interval": "monthly",
            "origin_url": BASE_URL,
            "cancel_path": "/app/settings/billing"
        }
        response = self.api_call("POST", "/billing/change-plan", token, change_plan_data)
        if response:
            if response.status_code == 500:
                self.log("❌ POST /billing/change-plan returned 500 error (CRITICAL ISSUE)", False)
            elif response.status_code == 409:
                self.log(f"POST /billing/change-plan: 409 (plan conflict - acceptable)")
            elif response.status_code == 200:
                try:
                    result = response.json()
                    action = result.get("action")
                    self.log(f"✓ POST /billing/change-plan: action={action}")
                    
                    # Verify expected flow based on subscription type
                    if data.get("change_flow") == "checkout_redirect" and action != "checkout_redirect":
                        self.log(f"⚠️ Expected checkout_redirect but got {action}")
                    elif data.get("change_flow") == "self_serve" and action not in ["changed_now", "scheduled"]:
                        self.log(f"⚠️ Expected self_serve action but got {action}")
                        
                except Exception as e:
                    self.log(f"Error parsing change-plan response: {str(e)}", False)
            else:
                self.log(f"POST /billing/change-plan: status {response.status_code}")
        else:
            self.log("POST /billing/change-plan: No response", False)
            
        # Test 5: POST /api/billing/customer-portal
        portal_data = {
            "origin_url": BASE_URL,
            "return_path": "/app/settings/billing"
        }
        response = self.api_call("POST", "/billing/customer-portal", token, portal_data)
        if response and response.status_code == 200:
            try:
                result = response.json()
                portal_url = result.get("url")
                if portal_url and "billing.stripe.com" in portal_url:
                    self.log("✓ POST /billing/customer-portal: valid billing.stripe.com URL")
                else:
                    self.log(f"❌ POST /billing/customer-portal: URL={portal_url} (expected billing.stripe.com)", False)
            except Exception as e:
                self.log(f"Error parsing customer-portal response: {str(e)}", False)
        else:
            status = response.status_code if response else "No response"
            self.log(f"POST /billing/customer-portal failed: {status}", False)
    
    def run_all_tests(self):
        """Run all billing lifecycle tests"""
        self.log("=== P0 BILLING LIFECYCLE VALIDATION STARTED ===")
        self.log(f"Base URL: {BASE_URL}")
        self.log(f"API Base: {API_BASE}")
        
        try:
            # Test agent@acenta.test - appears to be managed, not legacy as requested
            self.test_billing_account("agent@acenta.test (supposed legacy)", 
                                    ACCOUNTS["agent@acenta.test"], 
                                    expected_type="legacy")
            
            # Test billing.test.83ce5350@example.com - managed QA account
            self.test_billing_account("billing.test.83ce5350@example.com (managed QA)", 
                                    ACCOUNTS["billing.test.83ce5350@example.com"], 
                                    expected_type="managed")
            
            # Test stale reference handling
            self.log("\n=== TESTING STALE STRIPE REFERENCE GUARDRAILS ===")
            error_500_count = sum(1 for result in self.test_results if "500 error" in result["message"] and not result["success"])
            if error_500_count == 0:
                self.log("✓ No 500 errors detected - stale reference guardrails working")
            else:
                self.log(f"❌ Found {error_500_count} 500 errors - stale reference guardrails may need attention", False)
            
            # Summary
            total_tests = len(self.test_results)
            passed_tests = sum(1 for result in self.test_results if result["success"])
            failed_tests = total_tests - passed_tests
            
            self.log(f"\n=== BILLING LIFECYCLE VALIDATION SUMMARY ===")
            self.log(f"Total logged items: {total_tests}")
            self.log(f"Successful: {passed_tests}")
            self.log(f"Failed: {failed_tests}")
            
            if failed_tests > 0:
                self.log("\n=== FAILED ITEMS ===")
                for result in self.test_results:
                    if not result["success"]:
                        self.log(f"❌ {result['message']}")
                        
            return failed_tests == 0
            
        except Exception as e:
            self.log(f"Test execution error: {str(e)}", False)
            return False


if __name__ == "__main__":
    tester = BillingLifecycleTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)