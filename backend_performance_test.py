#!/usr/bin/env python3
"""
Syroce Backend Performance Validation Test
Turkish Review Request: Performance validation after endpoint optimization
Focus: Cache effectiveness and latency measurement for specific endpoints
"""

import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "https://hook-platform.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "admin123"

# Test endpoints as specified in Turkish review
TEST_ENDPOINTS = [
    "/billing/subscription",
    "/dashboard/weekly-summary", 
    "/tenant/features",
    "/dashboard/kpi-stats",
    "/dashboard/reservation-widgets"
]

def log_test_result(test_name, status, details=""):
    """Log test results with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    status_symbol = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
    print(f"{status_symbol} [{timestamp}] {test_name}: {status}")
    if details:
        print(f"    {details}")

def make_request_with_timing(url, headers=None, method="GET", data=None):
    """Make HTTP request and measure timing"""
    start_time = time.time()
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=30)
        
        end_time = time.time()
        latency_ms = round((end_time - start_time) * 1000, 2)
        
        return response, latency_ms
    except Exception as e:
        end_time = time.time()
        latency_ms = round((end_time - start_time) * 1000, 2)
        return None, latency_ms

def test_admin_login():
    """Test admin login and return auth token"""
    print("\n=== ADMIN LOGIN TEST ===")
    
    login_url = f"{BASE_URL}/auth/login"
    login_data = {
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    }
    
    response, latency = make_request_with_timing(login_url, method="POST", data=login_data)
    
    if response and response.status_code == 200:
        try:
            data = response.json()
            access_token = data.get("access_token")
            if access_token:
                log_test_result(f"Admin login ({ADMIN_EMAIL})", "PASS", 
                               f"Status: {response.status_code}, Token: {len(access_token)} chars, Latency: {latency}ms")
                return access_token
            else:
                log_test_result("Admin login", "FAIL", "No access_token in response")
                return None
        except json.JSONDecodeError:
            log_test_result("Admin login", "FAIL", f"Invalid JSON response, Status: {response.status_code}")
            return None
    else:
        error_msg = f"Status: {response.status_code if response else 'Connection Error'}, Latency: {latency}ms"
        log_test_result("Admin login", "FAIL", error_msg)
        return None

def test_endpoint_performance(endpoint, auth_headers, test_round):
    """Test endpoint performance with multiple requests to measure cache effectiveness"""
    print(f"\n--- Endpoint: {endpoint} (Round {test_round}) ---")
    
    endpoint_url = f"{BASE_URL}{endpoint}"
    latencies = []
    
    # Make 3 requests to measure cache effectiveness
    for i in range(1, 4):
        response, latency = make_request_with_timing(endpoint_url, headers=auth_headers)
        
        if response:
            status_code = response.status_code
            if status_code == 200:
                try:
                    data = response.json()
                    response_size = len(json.dumps(data))
                    latencies.append(latency)
                    
                    cache_indicator = ""
                    if i > 1 and latency < latencies[0] * 0.7:  # Significant improvement
                        cache_indicator = " (CACHE HIT LIKELY)"
                    
                    log_test_result(f"Request {i}", "PASS", 
                                   f"Status: {status_code}, Response: {response_size} chars, Latency: {latency}ms{cache_indicator}")
                except json.JSONDecodeError:
                    log_test_result(f"Request {i}", "FAIL", f"Invalid JSON, Status: {status_code}, Latency: {latency}ms")
            else:
                log_test_result(f"Request {i}", "FAIL", f"Status: {status_code}, Latency: {latency}ms")
        else:
            log_test_result(f"Request {i}", "FAIL", f"Connection error, Latency: {latency}ms")
    
    # Calculate performance metrics
    if latencies:
        avg_latency = round(sum(latencies) / len(latencies), 2)
        min_latency = min(latencies)
        max_latency = max(latencies)
        
        # Cache effectiveness analysis
        if len(latencies) >= 2:
            improvement = round(((latencies[0] - latencies[-1]) / latencies[0]) * 100, 1)
            cache_effectiveness = "EXCELLENT" if improvement > 30 else "GOOD" if improvement > 10 else "MODERATE" if improvement > 0 else "NONE"
            
            print(f"    📊 Performance Summary:")
            print(f"       First request: {latencies[0]}ms")
            print(f"       Last request: {latencies[-1]}ms") 
            print(f"       Average: {avg_latency}ms, Range: {min_latency}-{max_latency}ms")
            print(f"       Cache improvement: {improvement}% ({cache_effectiveness})")
            
            return True, avg_latency, improvement
    
    return False, 0, 0

def main():
    """Main performance validation test"""
    print("🚀 SYROCE BACKEND PERFORMANCE VALIDATION")
    print("=" * 60)
    print(f"Target: {BASE_URL}")
    print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Scope: Performance validation after endpoint cache optimization")
    print("")
    
    # Step 1: Admin login
    access_token = test_admin_login()
    if not access_token:
        print("\n❌ CRITICAL: Admin login failed, cannot proceed with endpoint tests")
        return False
    
    # Setup auth headers
    auth_headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # Step 2: Test each endpoint for performance
    print(f"\n=== ENDPOINT PERFORMANCE TESTS ===")
    print(f"Testing {len(TEST_ENDPOINTS)} endpoints with cache effectiveness measurement")
    
    test_results = []
    
    for i, endpoint in enumerate(TEST_ENDPOINTS, 1):
        success, avg_latency, cache_improvement = test_endpoint_performance(endpoint, auth_headers, i)
        test_results.append({
            'endpoint': endpoint,
            'success': success,
            'avg_latency': avg_latency,
            'cache_improvement': cache_improvement
        })
        
        # Small delay between endpoint tests
        time.sleep(0.5)
    
    # Step 3: Summary and Analysis
    print(f"\n{'=' * 60}")
    print("📋 PERFORMANCE VALIDATION SUMMARY")
    print(f"{'=' * 60}")
    
    successful_tests = sum(1 for result in test_results if result['success'])
    total_tests = len(test_results)
    
    print(f"Endpoints tested: {total_tests}")
    print(f"Successful tests: {successful_tests}")
    print(f"Success rate: {round((successful_tests/total_tests)*100, 1)}%")
    print("")
    
    if successful_tests > 0:
        print("📊 ENDPOINT PERFORMANCE ANALYSIS:")
        print("-" * 40)
        
        for result in test_results:
            if result['success']:
                endpoint = result['endpoint']
                latency = result['avg_latency']
                improvement = result['cache_improvement']
                
                # Performance rating
                perf_rating = "🟢 EXCELLENT" if latency < 200 else "🟡 GOOD" if latency < 500 else "🔴 SLOW"
                cache_rating = "🚀 HIGH" if improvement > 30 else "✅ MODERATE" if improvement > 10 else "⚪ LOW"
                
                print(f"  {endpoint}")
                print(f"    Latency: {latency}ms ({perf_rating})")
                print(f"    Cache effectiveness: {improvement}% ({cache_rating})")
                
                # Special analysis for billing/subscription (mentioned as key focus)
                if "/billing/subscription" in endpoint and latency < 300:
                    print(f"    ⭐ BILLING ENDPOINT: Cache optimization successful (< 300ms)")
                elif "/billing/subscription" in endpoint:
                    print(f"    ⚠️  BILLING ENDPOINT: May need further optimization")
    
    print("")
    
    # Step 4: Turkish Review Requirements Check
    print("🎯 TURKISH REVIEW REQUIREMENTS CHECK:")
    print("-" * 40)
    
    critical_issues = []
    
    # Check if billing/subscription is working with acceptable performance
    billing_result = next((r for r in test_results if "/billing/subscription" in r['endpoint']), None)
    if billing_result and billing_result['success']:
        if billing_result['avg_latency'] < 500:
            print("✅ /api/billing/subscription: Working with acceptable latency")
        else:
            print("⚠️  /api/billing/subscription: Working but high latency")
            critical_issues.append("Billing subscription endpoint has high latency")
    else:
        print("❌ /api/billing/subscription: FAILED")
        critical_issues.append("Billing subscription endpoint failed")
    
    # Check overall endpoint functionality
    if successful_tests == total_tests:
        print("✅ All dashboard/billing endpoints: Functional")
    else:
        print(f"⚠️  {total_tests - successful_tests} endpoint(s) failed")
        critical_issues.append(f"{total_tests - successful_tests} endpoints failed")
    
    # Check cache optimization effectiveness
    cache_effective_count = sum(1 for r in test_results if r['success'] and r['cache_improvement'] > 10)
    if cache_effective_count >= len(test_results) // 2:
        print("✅ Cache optimization: Effective (multiple endpoints show improvement)")
    else:
        print("⚠️  Cache optimization: Limited effectiveness detected")
    
    print("")
    
    # Final assessment
    if not critical_issues:
        print("🎉 PERFORMANCE VALIDATION: ✅ PASSED")
        print("   All endpoints functional with acceptable performance")
        print("   Cache optimization appears to be working effectively")
        return True
    else:
        print("⚠️  PERFORMANCE VALIDATION: ISSUES DETECTED")
        for issue in critical_issues:
            print(f"   - {issue}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)