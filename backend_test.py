#!/usr/bin/env python3
"""
Travel Agency Operating System - Admin Tenant Cleanup Validation Test

Tests the admin tenant cleanup functionality per Turkish review request:
- Admin authentication
- Tenant list endpoint with new enrichment fields
- Response structure validation
- Features endpoint no-regression
- Authorization guardrails
- Mongo _id leakage prevention
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
BACKEND_URL = "https://travel-agency-os-2.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "admin123"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

def log_test(test_name, status, details=""):
    """Log test results with colors"""
    color = Colors.GREEN if status == "PASS" else Colors.RED if status == "FAIL" else Colors.YELLOW
    print(f"{color}{status}{Colors.END} - {test_name}")
    if details:
        print(f"       {details}")

def log_info(message):
    """Log informational message"""
    print(f"{Colors.BLUE}INFO{Colors.END} - {message}")

def log_error(message):
    """Log error message"""
    print(f"{Colors.RED}ERROR{Colors.END} - {message}")

def check_mongo_id_leakage(data, path=""):
    """Check for MongoDB _id fields in response data"""
    leakage_found = []
    
    if isinstance(data, dict):
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key
            if key == "_id":
                leakage_found.append(current_path)
            elif isinstance(value, (dict, list)):
                leakage_found.extend(check_mongo_id_leakage(value, current_path))
    elif isinstance(data, list):
        for i, item in enumerate(data):
            current_path = f"{path}[{i}]" if path else f"[{i}]"
            if isinstance(item, (dict, list)):
                leakage_found.extend(check_mongo_id_leakage(item, current_path))
    
    return leakage_found

def validate_summary_structure(summary):
    """Validate the top-level summary object structure"""
    required_fields = [
        'total', 'payment_issue_count', 'trial_count', 
        'canceling_count', 'active_count', 'by_plan', 'lifecycle'
    ]
    
    missing_fields = []
    for field in required_fields:
        if field not in summary:
            missing_fields.append(field)
    
    return missing_fields

def validate_tenant_item_structure(tenant):
    """Validate tenant item structure"""
    required_fields = [
        'id', 'name', 'slug', 'status', 'organization_id', 'plan', 
        'plan_label', 'subscription_status', 'cancel_at_period_end', 
        'grace_period_until', 'current_period_end', 'lifecycle_stage', 
        'has_payment_issue'
    ]
    
    missing_fields = []
    for field in required_fields:
        if field not in tenant:
            missing_fields.append(field)
    
    return missing_fields

def main():
    print(f"{Colors.BOLD}Travel Agency Operating System - Admin Tenant Cleanup Validation{Colors.END}")
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    session = requests.Session()
    admin_token = None
    test_results = []
    
    # Test 1: Admin Login
    try:
        log_info("Testing admin login...")
        login_response = session.post(
            f"{BACKEND_URL}/auth/login",
            json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            },
            timeout=30
        )
        
        if login_response.status_code == 200:
            login_data = login_response.json()
            admin_token = login_data.get('access_token')
            
            if admin_token:
                log_test("POST /api/auth/login admin authentication", "PASS", 
                        f"Status: {login_response.status_code}, Token length: {len(admin_token)} chars")
                session.headers.update({'Authorization': f'Bearer {admin_token}'})
                test_results.append(("Admin Login", True, ""))
            else:
                log_test("POST /api/auth/login admin authentication", "FAIL", 
                        "No access_token in response")
                test_results.append(("Admin Login", False, "No access_token"))
        else:
            log_test("POST /api/auth/login admin authentication", "FAIL", 
                    f"Status: {login_response.status_code}, Response: {login_response.text[:200]}")
            test_results.append(("Admin Login", False, f"HTTP {login_response.status_code}"))
            
    except Exception as e:
        log_test("POST /api/auth/login admin authentication", "FAIL", f"Exception: {str(e)}")
        test_results.append(("Admin Login", False, str(e)))
        
    if not admin_token:
        log_error("Admin authentication failed - cannot proceed with other tests")
        print_summary(test_results)
        return
    
    # Test 2: GET /api/admin/tenants?limit=5
    try:
        log_info("Testing admin tenants endpoint...")
        tenants_response = session.get(
            f"{BACKEND_URL}/admin/tenants?limit=5",
            timeout=30
        )
        
        if tenants_response.status_code == 200:
            log_test("GET /api/admin/tenants?limit=5 endpoint", "PASS", 
                    f"Status: {tenants_response.status_code}")
            test_results.append(("Admin Tenants Endpoint", True, ""))
            
            try:
                tenants_data = tenants_response.json()
                log_info(f"Response size: {len(tenants_response.text)} chars")
                
                # Test 3: Response structure validation
                structure_issues = []
                
                # Check top-level summary object
                if 'summary' in tenants_data:
                    missing_summary_fields = validate_summary_structure(tenants_data['summary'])
                    if missing_summary_fields:
                        structure_issues.append(f"Missing summary fields: {missing_summary_fields}")
                    else:
                        log_test("Summary object structure", "PASS", 
                               f"All required fields present: total={tenants_data['summary'].get('total', 'N/A')}")
                else:
                    structure_issues.append("Missing top-level 'summary' object")
                
                # Check tenant items structure
                tenant_items = tenants_data.get('items', [])
                if tenant_items:
                    first_tenant = tenant_items[0]
                    missing_tenant_fields = validate_tenant_item_structure(first_tenant)
                    if missing_tenant_fields:
                        structure_issues.append(f"Missing tenant fields: {missing_tenant_fields}")
                    else:
                        log_test("Tenant item structure", "PASS", 
                               f"All required fields present in tenant items (checked first of {len(tenant_items)})")
                else:
                    structure_issues.append("No tenant items in response")
                
                if structure_issues:
                    log_test("Response structure validation", "FAIL", "; ".join(structure_issues))
                    test_results.append(("Response Structure", False, "; ".join(structure_issues)))
                else:
                    log_test("Response structure validation", "PASS", "All required fields present")
                    test_results.append(("Response Structure", True, ""))
                
                # Test 4: Mongo _id leakage check
                mongo_leaks = check_mongo_id_leakage(tenants_data)
                if mongo_leaks:
                    log_test("Mongo _id leakage prevention", "FAIL", 
                           f"Found _id fields at: {', '.join(mongo_leaks)}")
                    test_results.append(("Mongo ID Leakage", False, f"Found at: {', '.join(mongo_leaks)}"))
                else:
                    log_test("Mongo _id leakage prevention", "PASS", "No _id fields found in response")
                    test_results.append(("Mongo ID Leakage", True, ""))
                    
            except json.JSONDecodeError as e:
                log_test("Response structure validation", "FAIL", f"Invalid JSON: {str(e)}")
                test_results.append(("Response Structure", False, "Invalid JSON"))
                
        else:
            log_test("GET /api/admin/tenants?limit=5 endpoint", "FAIL", 
                    f"Status: {tenants_response.status_code}, Response: {tenants_response.text[:200]}")
            test_results.append(("Admin Tenants Endpoint", False, f"HTTP {tenants_response.status_code}"))
            
    except Exception as e:
        log_test("GET /api/admin/tenants?limit=5 endpoint", "FAIL", f"Exception: {str(e)}")
        test_results.append(("Admin Tenants Endpoint", False, str(e)))
    
    # Test 5: GET /api/admin/tenants/{tenant_id}/features no-regression
    try:
        log_info("Testing tenant features endpoint no-regression...")
        
        # Get first tenant ID from previous response
        tenant_id = None
        try:
            tenants_response = session.get(f"{BACKEND_URL}/admin/tenants?limit=1", timeout=30)
            if tenants_response.status_code == 200:
                tenants_data = tenants_response.json()
                tenant_items = tenants_data.get('items', [])
                if tenant_items:
                    tenant_id = tenant_items[0].get('id')
        except:
            pass
            
        if tenant_id:
            features_response = session.get(
                f"{BACKEND_URL}/admin/tenants/{tenant_id}/features",
                timeout=30
            )
            
            if features_response.status_code in [200, 404]:
                log_test("GET /api/admin/tenants/{tenant_id}/features no-regression", "PASS", 
                        f"Status: {features_response.status_code} (expected 200 or 404)")
                test_results.append(("Features No-regression", True, ""))
            else:
                log_test("GET /api/admin/tenants/{tenant_id}/features no-regression", "FAIL", 
                        f"Status: {features_response.status_code}, Response: {features_response.text[:200]}")
                test_results.append(("Features No-regression", False, f"HTTP {features_response.status_code}"))
        else:
            log_test("GET /api/admin/tenants/{tenant_id}/features no-regression", "FAIL", 
                    "Could not get tenant ID for testing")
            test_results.append(("Features No-regression", False, "No tenant ID available"))
            
    except Exception as e:
        log_test("GET /api/admin/tenants/{tenant_id}/features no-regression", "FAIL", f"Exception: {str(e)}")
        test_results.append(("Features No-regression", False, str(e)))
    
    # Test 6: Authorization guardrails
    try:
        log_info("Testing authorization guardrails...")
        
        # Test with no authorization header
        session_no_auth = requests.Session()
        no_auth_response = session_no_auth.get(
            f"{BACKEND_URL}/admin/tenants?limit=5",
            timeout=30
        )
        
        if no_auth_response.status_code in [401, 403]:
            log_test("Authorization guardrails", "PASS", 
                    f"Properly rejects unauthorized requests (HTTP {no_auth_response.status_code})")
            test_results.append(("Auth Guardrails", True, ""))
        elif no_auth_response.status_code == 500:
            log_test("Authorization guardrails", "FAIL", 
                    f"Returns 500 instead of 401/403 for unauthorized requests")
            test_results.append(("Auth Guardrails", False, "500 error instead of 401/403"))
        else:
            log_test("Authorization guardrails", "FAIL", 
                    f"Unexpected status for unauthorized request: {no_auth_response.status_code}")
            test_results.append(("Auth Guardrails", False, f"Unexpected status {no_auth_response.status_code}"))
            
    except Exception as e:
        log_test("Authorization guardrails", "FAIL", f"Exception: {str(e)}")
        test_results.append(("Auth Guardrails", False, str(e)))
    
    print_summary(test_results)

def print_summary(test_results):
    """Print test summary"""
    print("\n" + "=" * 80)
    print(f"{Colors.BOLD}TEST SUMMARY{Colors.END}")
    print("=" * 80)
    
    passed = sum(1 for _, status, _ in test_results if status)
    total = len(test_results)
    
    print(f"Total Tests: {total}")
    print(f"Passed: {Colors.GREEN}{passed}{Colors.END}")
    print(f"Failed: {Colors.RED}{total - passed}{Colors.END}")
    print(f"Success Rate: {(passed/total)*100:.1f}%" if total > 0 else "N/A")
    
    print(f"\n{Colors.BOLD}Detailed Results:{Colors.END}")
    for test_name, status, details in test_results:
        status_text = f"{Colors.GREEN}✅ PASS{Colors.END}" if status else f"{Colors.RED}❌ FAIL{Colors.END}"
        print(f"{status_text} - {test_name}")
        if details:
            print(f"         {details}")

if __name__ == "__main__":
    main()