#!/usr/bin/env python3
"""
Backend test for pricing + trial onboarding validation

Tests for Turkish review request:
1. GET /api/onboarding/plans
   - trial plan with is_public=false
   - starter pricing monthly 990, users.active 3, reservations.monthly 100
   - pro pricing monthly 2490, users.active 10, reservations.monthly 500
   - enterprise pricing monthly 6990, limits unlimited

2. POST /api/onboarding/signup
   - trial plan signup acceptance
   - response includes plan: trial
   - trial_end 14 days from now
"""

import json
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

# Use environment variable for backend URL
import os
backend_url = os.environ.get('REACT_APP_BACKEND_URL', 'https://usage-metering.preview.emergentagent.com')
base_url = f"{backend_url}/api"

def log_test(test_name: str, passed: bool, details: str = ""):
    """Log test results with consistent formatting"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {test_name}")
    if details:
        print(f"     {details}")

def test_get_plans():
    """Test GET /api/onboarding/plans endpoint"""
    print("\n=== Testing GET /api/onboarding/plans ===")
    
    try:
        response = requests.get(f"{base_url}/onboarding/plans", timeout=30)
        print(f"Status: {response.status_code}")
        
        if response.status_code != 200:
            log_test("GET /api/onboarding/plans status", False, f"Expected 200, got {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        data = response.json()
        plans = data.get('plans', [])
        
        if not plans:
            log_test("Plans array exists", False, "No plans found in response")
            return False
        
        log_test("GET /api/onboarding/plans status", True, f"Returned {len(plans)} plans")
        
        # Create plans lookup
        plans_dict = {plan.get('key') or plan.get('name'): plan for plan in plans}
        
        # Test trial plan requirements
        trial_plan = plans_dict.get('trial')
        if not trial_plan:
            log_test("Trial plan exists", False, "Trial plan not found")
        else:
            # Check is_public=false for trial
            is_public = trial_plan.get('is_public', True)
            log_test("Trial plan is_public=false", is_public is False, f"is_public={is_public}")
        
        # Test starter plan requirements
        starter_plan = plans_dict.get('starter')
        if not starter_plan:
            log_test("Starter plan exists", False, "Starter plan not found")
        else:
            pricing = starter_plan.get('pricing', {})
            limits = starter_plan.get('limits', {})
            
            # Check pricing monthly 990
            monthly_price = pricing.get('monthly')
            log_test("Starter pricing monthly 990", monthly_price == 990, f"monthly={monthly_price}")
            
            # Check users.active 3
            users_active = limits.get('users.active')
            log_test("Starter users.active 3", users_active == 3, f"users.active={users_active}")
            
            # Check reservations.monthly 100
            reservations_monthly = limits.get('reservations.monthly')
            log_test("Starter reservations.monthly 100", reservations_monthly == 100, f"reservations.monthly={reservations_monthly}")
        
        # Test pro plan requirements
        pro_plan = plans_dict.get('pro')
        if not pro_plan:
            log_test("Pro plan exists", False, "Pro plan not found")
        else:
            pricing = pro_plan.get('pricing', {})
            limits = pro_plan.get('limits', {})
            
            # Check pricing monthly 2490
            monthly_price = pricing.get('monthly')
            log_test("Pro pricing monthly 2490", monthly_price == 2490, f"monthly={monthly_price}")
            
            # Check users.active 10
            users_active = limits.get('users.active')
            log_test("Pro users.active 10", users_active == 10, f"users.active={users_active}")
            
            # Check reservations.monthly 500
            reservations_monthly = limits.get('reservations.monthly')
            log_test("Pro reservations.monthly 500", reservations_monthly == 500, f"reservations.monthly={reservations_monthly}")
        
        # Test enterprise plan requirements
        enterprise_plan = plans_dict.get('enterprise')
        if not enterprise_plan:
            log_test("Enterprise plan exists", False, "Enterprise plan not found")
        else:
            pricing = enterprise_plan.get('pricing', {})
            limits = enterprise_plan.get('limits', {})
            
            # Check pricing monthly 6990
            monthly_price = pricing.get('monthly')
            log_test("Enterprise pricing monthly 6990", monthly_price == 6990, f"monthly={monthly_price}")
            
            # Check unlimited limits (None values)
            users_active = limits.get('users.active')
            reservations_monthly = limits.get('reservations.monthly')
            log_test("Enterprise unlimited users", users_active is None, f"users.active={users_active}")
            log_test("Enterprise unlimited reservations", reservations_monthly is None, f"reservations.monthly={reservations_monthly}")
        
        # Print plans summary for debugging
        print("\n--- Plans Summary ---")
        for plan in plans:
            plan_name = plan.get('key') or plan.get('name')
            pricing = plan.get('pricing', {})
            limits = plan.get('limits', {})
            is_public = plan.get('is_public', True)
            print(f"{plan_name}: monthly={pricing.get('monthly')}, is_public={is_public}")
            print(f"  users.active={limits.get('users.active')}, reservations.monthly={limits.get('reservations.monthly')}")
        
        return True
        
    except requests.exceptions.RequestException as e:
        log_test("GET /api/onboarding/plans request", False, f"Request failed: {e}")
        return False
    except Exception as e:
        log_test("GET /api/onboarding/plans parsing", False, f"Error parsing response: {e}")
        return False

def test_signup_trial():
    """Test POST /api/onboarding/signup with trial plan"""
    print("\n=== Testing POST /api/onboarding/signup ===")
    
    # Generate unique email for signup test
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    test_email = f"test-{unique_id}@demo.test"
    
    signup_data = {
        "company_name": f"Test Acenta {unique_id}",
        "admin_name": f"Test Admin {unique_id}",
        "email": test_email,
        "password": "TestPassword123!",
        "plan": "trial",
        "billing_cycle": "monthly"
    }
    
    try:
        print(f"Signing up with email: {test_email}")
        response = requests.post(
            f"{base_url}/onboarding/signup", 
            json=signup_data,
            timeout=30
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code not in [200, 201]:
            log_test("POST /api/onboarding/signup status", False, f"Expected 200/201, got {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        data = response.json()
        log_test("POST /api/onboarding/signup status", True, f"Status {response.status_code}")
        
        # Check required fields in response
        required_fields = ['access_token', 'user_id', 'org_id', 'tenant_id', 'plan', 'trial_end']
        for field in required_fields:
            field_exists = field in data
            log_test(f"Response contains {field}", field_exists, f"Value: {data.get(field, 'MISSING')}")
        
        # Check plan is trial
        plan = data.get('plan')
        log_test("Response plan=trial", plan == "trial", f"plan={plan}")
        
        # Check trial_end is approximately 14 days from now
        trial_end_str = data.get('trial_end')
        if trial_end_str:
            try:
                # Parse trial_end datetime
                if trial_end_str.endswith('Z'):
                    trial_end_str = trial_end_str[:-1] + '+00:00'
                elif '+' not in trial_end_str and trial_end_str.count('T') == 1:
                    trial_end_str += '+00:00'
                
                trial_end = datetime.fromisoformat(trial_end_str)
                now = datetime.now(timezone.utc)
                
                # Calculate days difference
                days_diff = (trial_end - now).total_seconds() / (24 * 3600)
                
                # Should be approximately 14 days (allow 13-15 days range)
                valid_trial_period = 13 <= days_diff <= 15
                log_test("trial_end ~14 days from now", valid_trial_period, f"Days: {days_diff:.1f}")
                
            except Exception as e:
                log_test("trial_end parsing", False, f"Error parsing trial_end: {e}")
        else:
            log_test("trial_end exists", False, "trial_end field missing")
        
        # Print response summary
        print("\n--- Signup Response Summary ---")
        print(f"plan: {data.get('plan')}")
        print(f"trial_end: {data.get('trial_end')}")
        print(f"access_token length: {len(data.get('access_token', ''))}")
        print(f"user_id: {data.get('user_id')}")
        print(f"tenant_id: {data.get('tenant_id')}")
        
        return True
        
    except requests.exceptions.RequestException as e:
        log_test("POST /api/onboarding/signup request", False, f"Request failed: {e}")
        return False
    except Exception as e:
        log_test("POST /api/onboarding/signup parsing", False, f"Error parsing response: {e}")
        return False

def main():
    """Run all pricing + trial onboarding backend tests"""
    print("=" * 60)
    print("PRICING + TRIAL ONBOARDING BACKEND VALIDATION")
    print(f"Testing against: {backend_url}")
    print("=" * 60)
    
    tests = [
        test_get_plans,
        test_signup_trial
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ FAIL: {test_func.__name__} - Unexpected error: {e}")
            results.append(False)
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    total_tests = len(results)
    passed_tests = sum(results)
    failed_tests = total_tests - passed_tests
    
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Success rate: {(passed_tests/total_tests)*100:.1f}%")
    
    if failed_tests == 0:
        print("\n🎉 ALL TESTS PASSED - Pricing + trial onboarding backend working correctly!")
    else:
        print(f"\n⚠️  {failed_tests} test(s) failed - Review issues above")
    
    return failed_tests == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)