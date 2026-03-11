#!/usr/bin/env python3
"""
Emergent Native Deployment Backend Readiness Fix Test
Test the health endpoints to verify deployment blocker fix.
"""

import requests
import json
import sys
from datetime import datetime

def test_health_endpoints():
    """Test health endpoints for Emergent native deployment readiness"""
    
    base_url = "https://syroce-staging-2.preview.emergentagent.com"
    
    results = {
        "test_time": datetime.now().isoformat(),
        "base_url": base_url,
        "tests": []
    }
    
    # Test cases for health endpoints
    test_cases = [
        {
            "name": "GET /api/healthz",
            "url": f"{base_url}/api/healthz",
            "method": "GET",
            "expected_status": 200,
            "description": "Main health check endpoint - was returning 404 (deployment blocker)"
        },
        {
            "name": "GET /api/health/ready", 
            "url": f"{base_url}/api/health/ready",
            "method": "GET",
            "expected_status": 200,
            "description": "Readiness probe endpoint"
        },
        {
            "name": "GET /api/health",
            "url": f"{base_url}/api/health", 
            "method": "GET",
            "expected_status": 200,
            "description": "General health endpoint"
        },
        {
            "name": "GET /api/auth/me (no auth)",
            "url": f"{base_url}/api/auth/me",
            "method": "GET", 
            "expected_status": 401,
            "description": "Auth endpoint without credentials - should return 401 (normal, not deployment blocker)"
        }
    ]
    
    print("=" * 70)
    print("🏥 EMERGENT NATIVE DEPLOYMENT HEALTH ENDPOINT VALIDATION")
    print("=" * 70)
    print(f"Base URL: {base_url}")
    print(f"Test Time: {results['test_time']}")
    print()
    
    passed_tests = 0
    total_tests = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test {i}/{total_tests}: {test_case['name']}")
        print(f"URL: {test_case['url']}")
        print(f"Expected Status: {test_case['expected_status']}")
        print(f"Description: {test_case['description']}")
        
        test_result = {
            "test_number": i,
            "name": test_case['name'],
            "url": test_case['url'],
            "expected_status": test_case['expected_status'],
            "description": test_case['description']
        }
        
        try:
            # Make request with timeout
            response = requests.get(test_case['url'], timeout=10)
            
            test_result.update({
                "actual_status": response.status_code,
                "response_time_ms": int(response.elapsed.total_seconds() * 1000),
                "response_size": len(response.content),
                "content_type": response.headers.get('content-type', 'unknown'),
                "success": response.status_code == test_case['expected_status']
            })
            
            # Try to parse JSON response if possible
            try:
                if 'application/json' in response.headers.get('content-type', ''):
                    test_result['response_json'] = response.json()
                else:
                    test_result['response_text'] = response.text[:200]  # First 200 chars
            except:
                test_result['response_text'] = response.text[:200] if response.text else "Empty response"
            
            # Display result
            status_symbol = "✅" if test_result['success'] else "❌"
            print(f"Result: {status_symbol} Status {response.status_code} (Expected: {test_case['expected_status']})")
            print(f"Response Time: {test_result['response_time_ms']}ms")
            print(f"Response Size: {test_result['response_size']} bytes")
            
            if test_result['success']:
                passed_tests += 1
                print("✅ PASS")
            else:
                print("❌ FAIL")
                
        except requests.exceptions.RequestException as e:
            test_result.update({
                "error": str(e),
                "success": False,
                "actual_status": "ERROR"
            })
            print(f"❌ ERROR: {e}")
            
        results['tests'].append(test_result)
        print("-" * 50)
    
    # Summary
    print("📊 TEST SUMMARY")
    print("=" * 70)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    print()
    
    # Key findings for deployment
    print("🎯 DEPLOYMENT BLOCKER ANALYSIS")
    print("=" * 70)
    
    healthz_test = next((t for t in results['tests'] if 'healthz' in t['name']), None)
    if healthz_test:
        if healthz_test['success']:
            print("✅ CRITICAL: /api/healthz now returns 200 OK")
            print("✅ DEPLOYMENT BLOCKER RESOLVED: Main health check working")
        else:
            print("❌ CRITICAL: /api/healthz still failing")
            print("❌ DEPLOYMENT BLOCKER PERSISTS: Health check not working")
    
    auth_test = next((t for t in results['tests'] if 'auth/me' in t['name']), None)
    if auth_test:
        if auth_test['success']:
            print("✅ AUTH ENDPOINT: /api/auth/me correctly returns 401 (normal behavior)")
            print("✅ NOT A DEPLOYMENT BLOCKER: Auth without credentials properly rejected")
        else:
            print("⚠️ AUTH ENDPOINT: /api/auth/me unexpected response (but not deployment blocker)")
    
    print()
    
    # Final verdict
    deployment_ready = healthz_test and healthz_test['success']
    if deployment_ready:
        print("🚀 VERDICT: DEPLOYMENT READY")
        print("✅ Main blocker (/api/healthz 404) has been RESOLVED")
        print("✅ Health endpoints are functional")
    else:
        print("🚫 VERDICT: DEPLOYMENT BLOCKED") 
        print("❌ /api/healthz still not working - deployment blocker persists")
    
    return results, passed_tests, total_tests

if __name__ == "__main__":
    try:
        results, passed, total = test_health_endpoints()
        
        # Write detailed results to file
        with open('/app/health_test_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n📄 Detailed results saved to: /app/health_test_results.json")
        
        # Exit with appropriate code
        sys.exit(0 if passed == total else 1)
        
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        sys.exit(2)