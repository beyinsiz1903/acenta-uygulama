#!/usr/bin/env python3
"""
CORS Validation Test - Turkish Review Request
Backend CORS middleware validation for https://agency.syroce.com origin.

Tests:
1. OPTIONS http://127.0.0.1:8001/api/auth/me with Origin: https://agency.syroce.com + preflight headers
2. OPTIONS http://127.0.0.1:8001/api/public/theme with same origin
3. Response header validation: access-control-allow-origin and access-control-allow-credentials
4. Existing login endpoint smoke: POST external preview /api/auth/login admin@acenta.test / admin123
"""

import requests
import json
import sys


def test_cors_preflight():
    """Test CORS preflight requests to local backend with agency.syroce.com origin"""
    
    print("=" * 80)
    print("SYROCE BACKEND CORS VALIDATION - Turkish Review Request")
    print("=" * 80)
    
    local_backend = "http://127.0.0.1:8001"
    external_backend = "https://cache-health-check.preview.emergentagent.com"
    origin = "https://agency.syroce.com"
    
    results = {}
    
    # Test 1: OPTIONS /api/auth/me with Origin
    print("\n1. Testing OPTIONS /api/auth/me with Origin: https://agency.syroce.com")
    print("-" * 60)
    
    headers = {
        "Origin": origin,
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "authorization,content-type"
    }
    
    try:
        response = requests.options(f"{local_backend}/api/auth/me", headers=headers, timeout=10)
        print(f"   Status: {response.status_code}")
        print(f"   Response Headers:")
        
        cors_headers = {}
        for key, value in response.headers.items():
            if key.lower().startswith('access-control'):
                cors_headers[key.lower()] = value
                print(f"     {key}: {value}")
        
        # Check specific CORS headers
        allow_origin = cors_headers.get('access-control-allow-origin', '')
        allow_credentials = cors_headers.get('access-control-allow-credentials', '')
        
        results['auth_me_preflight'] = {
            'status': response.status_code,
            'allow_origin': allow_origin,
            'allow_credentials': allow_credentials,
            'cors_headers': cors_headers
        }
        
        print(f"   ✅ access-control-allow-origin: {allow_origin}")
        print(f"   ✅ access-control-allow-credentials: {allow_credentials}")
        
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        results['auth_me_preflight'] = {'error': str(e)}
    
    # Test 2: OPTIONS /api/public/theme with Origin
    print("\n2. Testing OPTIONS /api/public/theme with Origin: https://agency.syroce.com")
    print("-" * 60)
    
    try:
        response = requests.options(f"{local_backend}/api/public/theme", headers=headers, timeout=10)
        print(f"   Status: {response.status_code}")
        print(f"   Response Headers:")
        
        cors_headers = {}
        for key, value in response.headers.items():
            if key.lower().startswith('access-control'):
                cors_headers[key.lower()] = value
                print(f"     {key}: {value}")
        
        allow_origin = cors_headers.get('access-control-allow-origin', '')
        allow_credentials = cors_headers.get('access-control-allow-credentials', '')
        
        results['public_theme_preflight'] = {
            'status': response.status_code,
            'allow_origin': allow_origin,
            'allow_credentials': allow_credentials,
            'cors_headers': cors_headers
        }
        
        print(f"   ✅ access-control-allow-origin: {allow_origin}")
        print(f"   ✅ access-control-allow-credentials: {allow_credentials}")
        
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        results['public_theme_preflight'] = {'error': str(e)}
    
    # Test 3: Validate expected CORS headers
    print("\n3. CORS Header Validation")
    print("-" * 60)
    
    cors_validation = True
    issues = []
    
    # Check auth/me endpoint
    if 'auth_me_preflight' in results and 'error' not in results['auth_me_preflight']:
        auth_data = results['auth_me_preflight']
        
        # With allow-all-regex mode, we should see the requesting origin echoed back
        if auth_data['allow_origin'] != origin:
            issues.append(f"auth/me: Expected allow-origin '{origin}', got '{auth_data['allow_origin']}'")
            cors_validation = False
        
        if auth_data['allow_credentials'].lower() != 'true':
            issues.append(f"auth/me: Expected allow-credentials 'true', got '{auth_data['allow_credentials']}'")
            cors_validation = False
    
    # Check public/theme endpoint  
    if 'public_theme_preflight' in results and 'error' not in results['public_theme_preflight']:
        theme_data = results['public_theme_preflight']
        
        if theme_data['allow_origin'] != origin:
            issues.append(f"public/theme: Expected allow-origin '{origin}', got '{theme_data['allow_origin']}'")
            cors_validation = False
        
        if theme_data['allow_credentials'].lower() != 'true':
            issues.append(f"public/theme: Expected allow-credentials 'true', got '{theme_data['allow_credentials']}'")
            cors_validation = False
    
    if cors_validation:
        print("   ✅ All CORS headers correct!")
        print(f"   ✅ access-control-allow-origin: {origin}")
        print(f"   ✅ access-control-allow-credentials: true")
    else:
        for issue in issues:
            print(f"   ❌ {issue}")
    
    # Test 4: Login endpoint smoke test on external preview
    print("\n4. Login Endpoint Smoke Test (External Preview)")
    print("-" * 60)
    
    login_payload = {
        "email": "admin@acenta.test",
        "password": "admin123"
    }
    
    try:
        response = requests.post(
            f"{external_backend}/api/auth/login", 
            json=login_payload,
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            token_length = len(data.get('access_token', '')) if 'access_token' in data else 0
            print(f"   ✅ Login successful")
            print(f"   ✅ Access token received: {token_length} chars")
            results['login_smoke'] = {'status': 200, 'token_length': token_length}
        else:
            print(f"   ❌ Login failed: {response.text}")
            results['login_smoke'] = {'status': response.status_code, 'error': response.text}
            
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        results['login_smoke'] = {'error': str(e)}
    
    # Final Summary
    print("\n" + "=" * 80)
    print("CORS VALIDATION SUMMARY")
    print("=" * 80)
    
    all_passed = True
    
    print(f"1. OPTIONS /api/auth/me + Origin check:", end=" ")
    if 'auth_me_preflight' in results and 'error' not in results['auth_me_preflight']:
        auth_result = results['auth_me_preflight']
        if auth_result['allow_origin'] == origin and auth_result['allow_credentials'].lower() == 'true':
            print("✅ PASS")
        else:
            print("❌ FAIL")
            all_passed = False
    else:
        print("❌ FAIL (Error)")
        all_passed = False
    
    print(f"2. OPTIONS /api/public/theme + Origin check:", end=" ")
    if 'public_theme_preflight' in results and 'error' not in results['public_theme_preflight']:
        theme_result = results['public_theme_preflight']
        if theme_result['allow_origin'] == origin and theme_result['allow_credentials'].lower() == 'true':
            print("✅ PASS")
        else:
            print("❌ FAIL")
            all_passed = False
    else:
        print("❌ FAIL (Error)")
        all_passed = False
    
    print(f"3. CORS headers validation:", end=" ")
    if cors_validation:
        print("✅ PASS")
    else:
        print("❌ FAIL")
        all_passed = False
    
    print(f"4. Login smoke test:", end=" ")
    if 'login_smoke' in results and results['login_smoke'].get('status') == 200:
        print("✅ PASS")
    else:
        print("❌ FAIL")
        all_passed = False
    
    print("\n" + "=" * 80)
    if all_passed:
        print("🎉 LOCAL BACKEND CORS OK ✅")
        print("Backend CORS middleware correctly configured for https://agency.syroce.com")
    else:
        print("⚠️  CORS Issues Detected ❌")
        print("Some CORS configurations need attention")
    
    print("=" * 80)
    
    return all_passed, results


if __name__ == "__main__":
    success, test_results = test_cors_preflight()
    
    # Print test results as JSON for debugging
    print(f"\nTest Results JSON:")
    print(json.dumps(test_results, indent=2))
    
    sys.exit(0 if success else 1)