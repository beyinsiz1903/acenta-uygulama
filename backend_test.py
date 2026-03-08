#!/usr/bin/env python3
"""
Backend validation for Stripe billing functionality.
Tests all required endpoints and user account states per review request.
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
BASE_URL = "https://escape-excel.preview.emergentagent.com"
API_BASE = f"{BASE_URL}/api"

def main():
    """Main test execution with comprehensive Stripe billing validation."""
    print("=== STRIPE BILLING BACKEND VALIDATION ===")
    print(f"Base URL: {BASE_URL}")
    print(f"Test Start: {datetime.now().isoformat()}")
    print()
    
    test_results = []
    
    # Test 1: POST /api/billing/create-checkout functionality
    print("1. Testing POST /api/billing/create-checkout...")
    checkout_result = test_create_checkout()
    test_results.append(checkout_result)
    
    # Test 2: GET /api/billing/checkout-status/{session_id}
    print("\n2. Testing GET /api/billing/checkout-status/{session_id}...")
    status_result = test_checkout_status()
    test_results.append(status_result)
    
    # Test 3: POST /api/webhook/stripe endpoint existence
    print("\n3. Testing POST /api/webhook/stripe endpoint...")
    webhook_result = test_stripe_webhook()
    test_results.append(webhook_result)
    
    # Test 4: Paid account trial.db3ef59b76@example.com status
    print("\n4. Testing paid account trial status (trial.db3ef59b76@example.com)...")
    paid_account_result = test_paid_account_status()
    test_results.append(paid_account_result)
    
    # Test 5: Expired test account status
    print("\n5. Testing expired account status (expired.checkout.cdc8caf5@trial.test)...")
    expired_account_result = test_expired_account_status()
    test_results.append(expired_account_result)
    
    # Summary
    print("\n=== TEST SUMMARY ===")
    passed = sum(1 for result in test_results if result['status'] == 'PASS')
    total = len(test_results)
    print(f"Tests Passed: {passed}/{total}")
    
    for i, result in enumerate(test_results, 1):
        status_icon = "✅" if result['status'] == 'PASS' else "❌"
        print(f"{status_icon} Test {i}: {result['name']} - {result['status']}")
        if result.get('details'):
            for detail in result['details']:
                print(f"   • {detail}")
    
    print(f"\nTest End: {datetime.now().isoformat()}")
    return passed == total

def authenticate_user(email: str, password: str) -> dict:
    """Authenticate user and return token and user info."""
    login_url = f"{API_BASE}/auth/login"
    
    payload = {
        "email": email,
        "password": password
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-Client-Platform": "web"
    }
    
    try:
        response = requests.post(login_url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "token": data.get("access_token"),
                "user": data,
                "cookies": response.cookies
            }
        else:
            return {
                "success": False,
                "error": f"Login failed with status {response.status_code}: {response.text}",
                "status_code": response.status_code
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"Login request failed: {str(e)}"
        }

def test_create_checkout():
    """Test POST /api/billing/create-checkout with different plans and intervals."""
    result = {
        "name": "POST /api/billing/create-checkout functionality",
        "status": "FAIL",
        "details": []
    }
    
    # First authenticate to get a token
    auth = authenticate_user("admin@acenta.test", "admin123")
    if not auth["success"]:
        result["details"].append(f"Authentication failed: {auth['error']}")
        return result
    
    token = auth["token"]
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    test_cases = [
        {
            "name": "Starter Monthly",
            "plan": "starter",
            "interval": "monthly",
            "should_work": True
        },
        {
            "name": "Starter Yearly", 
            "plan": "starter",
            "interval": "yearly",
            "should_work": True
        },
        {
            "name": "Pro Monthly",
            "plan": "pro",
            "interval": "monthly", 
            "should_work": True
        },
        {
            "name": "Pro Yearly",
            "plan": "pro",
            "interval": "yearly",
            "should_work": True
        },
        {
            "name": "Enterprise Monthly (should reject)",
            "plan": "enterprise",
            "interval": "monthly",
            "should_work": False
        },
        {
            "name": "Enterprise Yearly (should reject)",
            "plan": "enterprise", 
            "interval": "yearly",
            "should_work": False
        }
    ]
    
    checkout_url = f"{API_BASE}/billing/create-checkout"
    passed_tests = 0
    
    for test_case in test_cases:
        payload = {
            "plan": test_case["plan"],
            "interval": test_case["interval"],
            "origin_url": BASE_URL,
            "cancel_path": "/pricing"
        }
        
        try:
            response = requests.post(checkout_url, json=payload, headers=headers, timeout=30)
            
            if test_case["should_work"]:
                if response.status_code == 200:
                    data = response.json()
                    if "checkout_url" in data or "session_id" in data:
                        result["details"].append(f"✅ {test_case['name']}: Created checkout session")
                        passed_tests += 1
                    else:
                        result["details"].append(f"❌ {test_case['name']}: Response missing checkout_url/session_id")
                else:
                    result["details"].append(f"❌ {test_case['name']}: Expected 200, got {response.status_code}")
            else:
                # Enterprise should be rejected
                if response.status_code in [400, 403, 422]:
                    result["details"].append(f"✅ {test_case['name']}: Correctly rejected with {response.status_code}")
                    passed_tests += 1
                else:
                    result["details"].append(f"❌ {test_case['name']}: Expected rejection, got {response.status_code}")
                    
        except Exception as e:
            result["details"].append(f"❌ {test_case['name']}: Request failed - {str(e)}")
    
    if passed_tests == len(test_cases):
        result["status"] = "PASS"
        result["details"].insert(0, f"All {len(test_cases)} checkout creation tests passed")
    
    return result

def test_checkout_status():
    """Test GET /api/billing/checkout-status/{session_id} endpoint."""
    result = {
        "name": "GET /api/billing/checkout-status/{session_id}",
        "status": "FAIL", 
        "details": []
    }
    
    # Authenticate
    auth = authenticate_user("admin@acenta.test", "admin123")
    if not auth["success"]:
        result["details"].append(f"Authentication failed: {auth['error']}")
        return result
    
    token = auth["token"]
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    # Test with a dummy session ID to check endpoint exists and response structure
    test_session_id = "cs_test_dummy_session_id_123"
    status_url = f"{API_BASE}/billing/checkout-status/{test_session_id}"
    
    try:
        response = requests.get(status_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            expected_fields = ["status", "session_id"]
            
            has_required_fields = all(field in data for field in expected_fields)
            if has_required_fields:
                result["status"] = "PASS"
                result["details"].append("✅ Endpoint exists and returns expected schema")
                result["details"].append(f"Response fields: {list(data.keys())}")
            else:
                result["details"].append(f"❌ Missing expected fields. Got: {list(data.keys())}")
                
        elif response.status_code == 404:
            # Session not found is acceptable for a dummy ID
            result["status"] = "PASS"
            result["details"].append("✅ Endpoint exists (404 expected for dummy session ID)")
            
        elif response.status_code == 400:
            # Bad request might be expected for invalid session format
            result["status"] = "PASS"
            result["details"].append("✅ Endpoint exists (400 expected for invalid session format)")
            
        else:
            result["details"].append(f"❌ Unexpected status code: {response.status_code}")
            result["details"].append(f"Response: {response.text[:200]}")
            
    except Exception as e:
        result["details"].append(f"❌ Request failed: {str(e)}")
    
    return result

def test_stripe_webhook():
    """Test POST /api/webhook/stripe endpoint existence."""
    result = {
        "name": "POST /api/webhook/stripe endpoint existence",
        "status": "FAIL",
        "details": []
    }
    
    webhook_url = f"{API_BASE}/webhook/stripe"
    
    # Test with minimal payload to check endpoint exists
    payload = {}
    headers = {
        "Content-Type": "application/json",
        "Stripe-Signature": "dummy_signature"
    }
    
    try:
        response = requests.post(webhook_url, json=payload, headers=headers, timeout=30)
        
        # Any response (even 400/401/500) indicates endpoint exists
        if response.status_code in [200, 400, 401, 403, 500, 503]:
            result["status"] = "PASS"
            result["details"].append(f"✅ Endpoint exists at exact path /api/webhook/stripe")
            result["details"].append(f"Response status: {response.status_code}")
            
            if response.status_code == 503:
                result["details"].append("✅ Returns 503 when webhook secret not configured (expected)")
            elif response.status_code == 400:
                result["details"].append("✅ Returns 400 for invalid signature (expected)")
        else:
            result["details"].append(f"❌ Unexpected status code: {response.status_code}")
            
    except requests.exceptions.ConnectionError as e:
        if "404" in str(e):
            result["details"].append("❌ Endpoint not found (404)")
        else:
            result["details"].append(f"❌ Connection error: {str(e)}")
    except Exception as e:
        result["details"].append(f"❌ Request failed: {str(e)}")
    
    return result

def test_paid_account_status():
    """Test that trial.db3ef59b76@example.com reports active/non-expired status."""
    result = {
        "name": "Paid account trial status (trial.db3ef59b76@example.com)",
        "status": "FAIL",
        "details": []
    }
    
    # Authenticate with the paid account
    auth = authenticate_user("trial.db3ef59b76@example.com", "Test1234!")
    if not auth["success"]:
        result["details"].append(f"❌ Authentication failed: {auth['error']}")
        return result
    
    result["details"].append("✅ Login successful")
    
    token = auth["token"]
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    # Test /api/onboarding/trial endpoint
    trial_url = f"{API_BASE}/onboarding/trial"
    
    try:
        response = requests.get(trial_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            result["details"].append(f"Trial status response: {json.dumps(data, indent=2)}")
            
            # Check if account reports as active/non-expired
            expired = data.get("expired", True)
            status = data.get("status", "unknown")
            
            if not expired and status != "expired":
                result["status"] = "PASS"
                result["details"].append("✅ Account reports as active/non-expired")
                result["details"].append(f"Status: {status}, Expired: {expired}")
                
                # Check if it reflects upgraded plan state
                plan = data.get("plan")
                if plan and plan != "trial":
                    result["details"].append(f"✅ Shows upgraded plan: {plan}")
                
            else:
                result["details"].append(f"❌ Account still reports as expired. Status: {status}, Expired: {expired}")
                
        else:
            result["details"].append(f"❌ Trial status check failed: {response.status_code}")
            result["details"].append(f"Response: {response.text[:200]}")
            
    except Exception as e:
        result["details"].append(f"❌ Trial status request failed: {str(e)}")
    
    return result

def test_expired_account_status():
    """Test that expired.checkout.cdc8caf5@trial.test still reports expired state."""
    result = {
        "name": "Expired account status (expired.checkout.cdc8caf5@trial.test)", 
        "status": "FAIL",
        "details": []
    }
    
    # Authenticate with the expired test account
    auth = authenticate_user("expired.checkout.cdc8caf5@trial.test", "Test1234!")
    if not auth["success"]:
        result["details"].append(f"❌ Authentication failed: {auth['error']}")
        return result
    
    result["details"].append("✅ Login successful")
    
    token = auth["token"]
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    # Test /api/onboarding/trial endpoint
    trial_url = f"{API_BASE}/onboarding/trial"
    
    try:
        response = requests.get(trial_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            result["details"].append(f"Trial status response: {json.dumps(data, indent=2)}")
            
            # Check if account still reports as expired
            expired = data.get("expired", False)
            status = data.get("status", "unknown")
            
            if expired or status == "expired":
                result["status"] = "PASS"
                result["details"].append("✅ Account correctly reports as expired")
                result["details"].append(f"Status: {status}, Expired: {expired}")
            else:
                result["details"].append(f"❌ Account should be expired but reports: Status: {status}, Expired: {expired}")
                
        else:
            result["details"].append(f"❌ Trial status check failed: {response.status_code}")
            result["details"].append(f"Response: {response.text[:200]}")
            
    except Exception as e:
        result["details"].append(f"❌ Trial status request failed: {str(e)}")
    
    return result

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)