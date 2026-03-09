#!/usr/bin/env python3
"""
Backend No-Regression Test for Billing/Payment Failure Improvements
==================================================================

Test Requirements:
1) GET /api/billing/subscription returns 200 and includes new payment_issue shape fields
2) GET /api/billing/history works with no regression
3) Auth guardrail: unauthenticated calls return 401/403
4) Code reference: /api/webhook/stripe main flow should handle invoice.paid, invoice.payment_failed, customer.subscription.deleted with proper helpers

Test Account: agent@acenta.test / agent123

Referência dos arquivos:
- /app/backend/app/services/stripe_checkout_service.py
- /app/backend/app/routers/billing_webhooks.py
"""

import json
import os
import requests
import sys
from datetime import datetime
from typing import Any, Dict, Optional

# Configuration
BASE_URL = "https://agency-platform-18.preview.emergentagent.com"
TEST_CREDENTIALS = {
    "email": "agent@acenta.test", 
    "password": "agent123"
}

class BillingPaymentTestRunner:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-Client-Platform': 'web'  # For cookie auth compatibility
        })
        self.auth_token = None
        self.tenant_id = None
        
    def log(self, message: str, success: bool = True):
        """Log test messages with status indicators"""
        status = "✅" if success else "❌"
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {status} {message}")
        
    def make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request with proper error handling"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.request(method, url, **kwargs)
            return response
        except Exception as e:
            self.log(f"Request failed: {method} {endpoint} - {str(e)}", False)
            raise
            
    def authenticate(self) -> bool:
        """Authenticate with the test account"""
        try:
            self.log("Attempting login with agent@acenta.test...")
            response = self.make_request(
                'POST',
                '/api/auth/login',
                json=TEST_CREDENTIALS
            )
            
            if response.status_code != 200:
                self.log(f"Login failed: HTTP {response.status_code} - {response.text}", False)
                return False
                
            data = response.json()
            self.auth_token = data.get('access_token')
            
            if not self.auth_token:
                self.log("Login successful but no access_token received", False)
                return False
                
            # Update session headers with auth token
            self.session.headers.update({
                'Authorization': f'Bearer {self.auth_token}'
            })
            
            self.log(f"Login successful - Token length: {len(self.auth_token)} chars")
            return True
            
        except Exception as e:
            self.log(f"Authentication error: {str(e)}", False)
            return False
    
    def test_billing_subscription_endpoint(self) -> bool:
        """
        Test 1: GET /api/billing/subscription returns 200 and includes new payment_issue shape fields
        
        Expected payment_issue shape:
        {
            "has_issue": bool,
            "severity": "critical" | "warning" | None,
            "title": str | None,
            "message": str | None,
            "cta_label": str | None,
            "grace_period_until": str | None,
            "last_failed_at": str | None,
            "last_failed_amount": int | None,
            "last_failed_amount_label": str | None,
            "invoice_hosted_url": str | None,
            "invoice_pdf_url": str | None
        }
        """
        try:
            self.log("Testing GET /api/billing/subscription endpoint...")
            response = self.make_request('GET', '/api/billing/subscription')
            
            if response.status_code != 200:
                self.log(f"Billing subscription endpoint failed: HTTP {response.status_code} - {response.text}", False)
                return False
                
            data = response.json()
            self.log(f"Billing subscription endpoint returned 200 OK")
            
            # Extract tenant_id for other tests
            self.tenant_id = data.get('tenant_id')
            
            # Validate payment_issue shape
            payment_issue = data.get('payment_issue', {})
            if not isinstance(payment_issue, dict):
                self.log("Missing or invalid payment_issue object in response", False)
                return False
                
            # Check required payment_issue fields
            required_fields = [
                'has_issue', 'severity', 'title', 'message', 'cta_label',
                'grace_period_until', 'last_failed_at', 'last_failed_amount', 
                'last_failed_amount_label', 'invoice_hosted_url', 'invoice_pdf_url'
            ]
            
            missing_fields = []
            for field in required_fields:
                if field not in payment_issue:
                    missing_fields.append(field)
                    
            if missing_fields:
                self.log(f"Missing payment_issue fields: {', '.join(missing_fields)}", False)
                return False
                
            self.log("All required payment_issue fields present in response")
            
            # Validate field types
            has_issue = payment_issue.get('has_issue')
            if not isinstance(has_issue, bool):
                self.log(f"payment_issue.has_issue should be boolean, got: {type(has_issue)}", False)
                return False
                
            severity = payment_issue.get('severity')
            if severity is not None and severity not in ['critical', 'warning']:
                self.log(f"payment_issue.severity should be 'critical'/'warning'/null, got: {severity}", False)
                return False
                
            self.log(f"Payment issue status: has_issue={has_issue}, severity={severity}")
            
            # Validate other billing subscription fields
            expected_fields = [
                'plan', 'interval', 'interval_label', 'status', 'current_period_end',
                'cancel_at_period_end', 'portal_available', 'managed_subscription',
                'legacy_subscription', 'can_cancel', 'can_change_plan'
            ]
            
            for field in expected_fields:
                if field not in data:
                    self.log(f"Missing billing subscription field: {field}", False)
                    return False
                    
            self.log("All core billing subscription fields present")
            
            # Log key subscription details
            plan = data.get('plan')
            status = data.get('status')
            managed = data.get('managed_subscription')
            self.log(f"Subscription details: plan={plan}, status={status}, managed={managed}")
            
            return True
            
        except Exception as e:
            self.log(f"Billing subscription test error: {str(e)}", False)
            return False
    
    def test_billing_history_endpoint(self) -> bool:
        """
        Test 2: GET /api/billing/history works with no regression
        """
        try:
            self.log("Testing GET /api/billing/history endpoint...")
            response = self.make_request('GET', '/api/billing/history')
            
            if response.status_code != 200:
                self.log(f"Billing history endpoint failed: HTTP {response.status_code} - {response.text}", False)
                return False
                
            data = response.json()
            self.log(f"Billing history endpoint returned 200 OK")
            
            # Validate response structure
            if 'items' not in data:
                self.log("Missing 'items' field in billing history response", False)
                return False
                
            items = data['items']
            if not isinstance(items, list):
                self.log("billing history 'items' should be a list", False)
                return False
                
            self.log(f"Billing history contains {len(items)} items")
            
            # If there are items, validate their structure
            if len(items) > 0:
                first_item = items[0]
                required_item_fields = ['id', 'action', 'title', 'description', 'occurred_at', 'actor_label', 'actor_type', 'tone']
                
                for field in required_item_fields:
                    if field not in first_item:
                        self.log(f"Missing field '{field}' in billing history item", False)
                        return False
                        
                self.log(f"Sample history item: {first_item['title']} - {first_item['actor_label']}")
                
            # Test with limit parameter
            response_limit = self.make_request('GET', '/api/billing/history?limit=5')
            if response_limit.status_code != 200:
                self.log("Billing history with limit parameter failed", False)
                return False
                
            limited_data = response_limit.json()
            limited_items = limited_data.get('items', [])
            self.log(f"Billing history with limit=5: {len(limited_items)} items returned")
            
            return True
            
        except Exception as e:
            self.log(f"Billing history test error: {str(e)}", False)
            return False
    
    def test_auth_guardrails(self) -> bool:
        """
        Test 3: Auth guardrail - unauthenticated calls return 401/403
        """
        try:
            self.log("Testing auth guardrails for billing endpoints...")
            
            # Create a session without auth token
            unauth_session = requests.Session()
            unauth_session.headers.update({
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            })
            
            endpoints_to_test = [
                '/api/billing/subscription',
                '/api/billing/history',
                '/api/billing/customer-portal',
                '/api/billing/cancel-subscription',
                '/api/billing/reactivate-subscription'
            ]
            
            success_count = 0
            
            for endpoint in endpoints_to_test:
                url = f"{self.base_url}{endpoint}"
                
                # Test GET endpoints
                if endpoint in ['/api/billing/subscription', '/api/billing/history']:
                    response = unauth_session.get(url)
                else:
                    # Test POST endpoints 
                    test_body = {}
                    if 'portal' in endpoint:
                        test_body = {"origin_url": "https://example.com"}
                    response = unauth_session.post(url, json=test_body)
                
                if response.status_code in [401, 403]:
                    self.log(f"Auth guardrail working for {endpoint}: HTTP {response.status_code}")
                    success_count += 1
                else:
                    self.log(f"Auth guardrail FAILED for {endpoint}: HTTP {response.status_code} (expected 401/403)", False)
                    
            if success_count == len(endpoints_to_test):
                self.log(f"All {len(endpoints_to_test)} auth guardrails working correctly")
                return True
            else:
                self.log(f"Auth guardrails failed: {success_count}/{len(endpoints_to_test)} endpoints protected", False)
                return False
                
        except Exception as e:
            self.log(f"Auth guardrails test error: {str(e)}", False)
            return False
    
    def test_webhook_stripe_code_reference(self) -> bool:
        """
        Test 4: Code reference validation of /api/webhook/stripe handlers
        
        Verify that the webhook handler supports:
        - invoice.paid
        - invoice.payment_failed  
        - customer.subscription.deleted
        
        And uses proper helper methods from stripe_checkout_service.py
        """
        try:
            self.log("Validating webhook code references...")
            
            # Read the webhook file
            webhook_file = "/app/backend/app/routers/billing_webhooks.py"
            if not os.path.exists(webhook_file):
                self.log(f"Webhook file not found: {webhook_file}", False)
                return False
                
            with open(webhook_file, 'r') as f:
                webhook_code = f.read()
                
            # Check for required event handlers
            required_events = [
                'invoice.paid',
                'invoice.payment_failed', 
                'customer.subscription.deleted'
            ]
            
            events_found = []
            for event in required_events:
                if event in webhook_code:
                    events_found.append(event)
                    self.log(f"Webhook handler found for: {event}")
                else:
                    self.log(f"Missing webhook handler for: {event}", False)
                    
            if len(events_found) != len(required_events):
                self.log(f"Missing webhook handlers: {set(required_events) - set(events_found)}", False)
                return False
                
            # Check for helper method usage
            helper_methods = [
                'mark_invoice_paid',
                'mark_payment_failed',
                'mark_subscription_canceled'
            ]
            
            helpers_found = []
            for helper in helper_methods:
                if helper in webhook_code:
                    helpers_found.append(helper)
                    self.log(f"Webhook uses helper: {helper}")
                else:
                    self.log(f"Missing helper usage: {helper}", False)
                    
            if len(helpers_found) != len(helper_methods):
                self.log(f"Missing helper methods: {set(helper_methods) - set(helpers_found)}", False)
                return False
                
            # Check for idempotency protection
            idempotency_checks = [
                'webhook_event_exists',
                'record_webhook_event'
            ]
            
            for check in idempotency_checks:
                if check in webhook_code:
                    self.log(f"Idempotency protection found: {check}")
                else:
                    self.log(f"Missing idempotency protection: {check}", False)
                    return False
                    
            # Test webhook endpoint existence (should return error without proper Stripe signature)
            self.log("Testing webhook endpoint existence...")
            response = self.make_request('POST', '/api/webhook/stripe', json={"test": "data"})
            
            # Expect 400 (bad signature), 500 (webhook processing error), or 503 (missing secret) - all indicate endpoint exists
            if response.status_code in [400, 500, 503]:
                self.log(f"Webhook endpoint exists and rejects test requests: HTTP {response.status_code}")
            else:
                self.log(f"Webhook endpoint behavior unexpected: HTTP {response.status_code}", False)
                return False
                
            return True
            
        except Exception as e:
            self.log(f"Webhook code reference test error: {str(e)}", False)
            return False
    
    def run_all_tests(self) -> bool:
        """Run all billing/payment failure improvement tests"""
        self.log("=" * 80)
        self.log("BILLING/PAYMENT FAILURE IMPROVEMENTS - BACKEND NO-REGRESSION TEST")
        self.log("=" * 80)
        self.log(f"Base URL: {self.base_url}")
        self.log(f"Test Account: {TEST_CREDENTIALS['email']}")
        
        # Step 1: Authenticate
        if not self.authenticate():
            return False
            
        # Step 2: Run individual tests
        tests = [
            ("GET /api/billing/subscription with payment_issue fields", self.test_billing_subscription_endpoint),
            ("GET /api/billing/history no-regression", self.test_billing_history_endpoint),
            ("Auth guardrails (401/403 for unauthenticated)", self.test_auth_guardrails),
            ("Webhook code reference validation", self.test_webhook_stripe_code_reference)
        ]
        
        results = []
        for test_name, test_func in tests:
            self.log("-" * 60)
            self.log(f"Running: {test_name}")
            result = test_func()
            results.append((test_name, result))
            
        # Summary
        self.log("=" * 80)
        self.log("TEST RESULTS SUMMARY")
        self.log("=" * 80)
        
        passed = 0
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            self.log(f"{status} - {test_name}")
            if result:
                passed += 1
                
        self.log("-" * 80)
        self.log(f"Success Rate: {passed}/{total} tests passed ({100 * passed // total}%)")
        
        if passed == total:
            self.log("🎉 ALL TESTS PASSED - Billing/payment failure improvements validated successfully!")
            return True
        else:
            self.log("⚠️  SOME TESTS FAILED - Review failures above", False)
            return False

def main():
    """Main test execution"""
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = BASE_URL
        
    test_runner = BillingPaymentTestRunner(base_url)
    success = test_runner.run_all_tests()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()