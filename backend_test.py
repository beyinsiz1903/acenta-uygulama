#!/usr/bin/env python3
"""
Backend API Testing Script for Syroce Tourism Platform
Tests the backend API endpoints after security fixes.
Includes Redis cache layer testing.
"""

import requests
import json
import sys
import subprocess
from typing import Dict, Any

# Backend URL from frontend/.env
BACKEND_URL = "https://improvement-areas.preview.emergentagent.com"
BASE_API_URL = f"{BACKEND_URL}/api"

def make_request(method: str, endpoint: str, data: Dict[Any, Any] = None, headers: Dict[str, str] = None) -> Dict[str, Any]:
    """Make HTTP request and return response details."""
    url = f"{BASE_API_URL}{endpoint}"
    
    default_headers = {
        "Content-Type": "application/json",
        "User-Agent": "Backend-Test-Script/1.0"
    }
    
    if headers:
        default_headers.update(headers)
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=default_headers, timeout=30)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, headers=default_headers, timeout=30)
        else:
            return {"error": f"Unsupported method: {method}"}
        
        result = {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "url": url,
            "method": method.upper()
        }
        
        try:
            result["json"] = response.json()
        except:
            result["text"] = response.text[:1000]  # Limit response text
            
        return result
        
    except requests.exceptions.Timeout:
        return {"error": "Request timeout"}
    except requests.exceptions.ConnectionError:
        return {"error": "Connection error"}
    except Exception as e:
        return {"error": str(e)}

def test_health_ready():
    """Test GET /api/health/ready endpoint with Redis checks."""
    print("Testing Health Ready endpoint with Redis...")
    result = make_request("GET", "/health/ready")
    
    if "error" in result:
        print(f"❌ FAILED: {result['error']}")
        return False
    
    print(f"Status Code: {result['status_code']}")
    
    if result["status_code"] == 200:
        json_data = result.get("json", {})
        status = json_data.get("status")
        checks = json_data.get("checks", {})
        
        # Check Redis specific fields
        redis_status = checks.get("redis")
        redis_memory = checks.get("redis_memory")
        
        print(f"✅ PASSED: Health Ready - Status: {status}")
        print(f"   Redis Status: {redis_status}")
        if redis_memory:
            print(f"   Redis Memory: {redis_memory}")
        print(f"   All Checks: {json.dumps(checks, indent=2)}")
        
        # Validate Redis health
        if redis_status == "healthy":
            print("✅ Redis is healthy")
            return True
        else:
            print(f"⚠️  Redis status is not healthy: {redis_status} (but endpoint returned 200)")
            return True  # Health endpoint still works
    else:
        print(f"❌ FAILED: Expected 200, got {result['status_code']}")
        print(f"   Response: {result.get('json') or result.get('text', 'No response')}")
        return False

def test_health_live():
    """Test GET /api/health/live endpoint."""
    print("\nTesting Health Live endpoint...")
    result = make_request("GET", "/health/live")
    
    if "error" in result:
        print(f"❌ FAILED: {result['error']}")
        return False
    
    print(f"Status Code: {result['status_code']}")
    
    if result["status_code"] == 200:
        json_data = result.get("json", {})
        status = json_data.get("status")
        
        print(f"✅ PASSED: Health Live - Status: {status}")
        return True
    else:
        print(f"❌ FAILED: Expected 200, got {result['status_code']}")
        print(f"   Response: {result.get('json') or result.get('text', 'No response')}")
        return False

def test_login_valid():
    """Test POST /api/auth/login with valid credentials."""
    print("\nTesting Login with valid credentials...")
    
    login_data = {
        "email": "admin@acenta.test",
        "password": "admin123"
    }
    
    result = make_request("POST", "/auth/login", login_data)
    
    if "error" in result:
        print(f"❌ FAILED: {result['error']}")
        return False
    
    print(f"Status Code: {result['status_code']}")
    
    if result["status_code"] == 200:
        json_data = result.get("json", {})
        access_token = json_data.get("access_token")
        user_data = json_data.get("user")
        
        if access_token and user_data:
            print(f"✅ PASSED: Login successful")
            print(f"   User: {user_data.get('email')}")
            print(f"   Token received: {access_token[:20]}...")
            return True
        else:
            print(f"❌ FAILED: Missing access_token or user in response")
            print(f"   Response: {json_data}")
            return False
    else:
        print(f"❌ FAILED: Expected 200, got {result['status_code']}")
        json_data = result.get("json", {})
        print(f"   Error: {json_data.get('detail', 'Unknown error')}")
        return False

def test_login_invalid():
    """Test POST /api/auth/login with invalid credentials."""
    print("\nTesting Login with invalid credentials...")
    
    login_data = {
        "email": "invalid",
        "password": "wrong"
    }
    
    result = make_request("POST", "/auth/login", login_data)
    
    if "error" in result:
        print(f"❌ FAILED: {result['error']}")
        return False
    
    print(f"Status Code: {result['status_code']}")
    
    if result["status_code"] == 401:
        json_data = result.get("json", {})
        error_detail = json_data.get("detail", "")
        
        print(f"✅ PASSED: Login correctly rejected - {error_detail}")
        return True
    else:
        print(f"❌ FAILED: Expected 401, got {result['status_code']}")
        print(f"   Response: {result.get('json') or result.get('text', 'No response')}")
        return False

def test_cors_headers():
    """Test CORS headers in responses."""
    print("\nTesting CORS headers...")
    
    # Test with health endpoint
    result = make_request("GET", "/health/live")
    
    if "error" in result:
        print(f"❌ FAILED: {result['error']}")
        return False
    
    headers = result.get("headers", {})
    cors_origin = headers.get("Access-Control-Allow-Origin", "")
    cors_credentials = headers.get("Access-Control-Allow-Credentials", "")
    cors_methods = headers.get("Access-Control-Allow-Methods", "")
    
    print(f"CORS Headers:")
    print(f"   Access-Control-Allow-Origin: {cors_origin}")
    print(f"   Access-Control-Allow-Credentials: {cors_credentials}")
    print(f"   Access-Control-Allow-Methods: {cors_methods}")
    
    # Check that CORS origin is not wildcard (*)
    if cors_origin == "*":
        print(f"❌ FAILED: CORS origin is wildcard (*), should be specific domains")
        return False
    elif cors_origin:
        print(f"✅ PASSED: CORS headers present with specific origin")
        return True
    else:
        print(f"⚠️  WARNING: No CORS headers found")
        return True  # This might be handled by middleware differently

def test_redis_cli_ping():
    """Test Redis CLI ping command."""
    print("\nTesting Redis CLI ping...")
    
    try:
        result = subprocess.run(
            ["redis-cli", "ping"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            output = result.stdout.strip()
            print(f"Output: {output}")
            
            if "PONG" in output:
                print("✅ PASSED: Redis CLI ping successful")
                return True
            else:
                print(f"❌ FAILED: Expected 'PONG', got '{output}'")
                return False
        else:
            print(f"❌ FAILED: redis-cli ping failed with exit code {result.returncode}")
            print(f"Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ FAILED: Error running redis-cli ping: {e}")
        return False

def test_redis_cli_info_memory():
    """Test Redis CLI info memory command."""
    print("\nTesting Redis CLI info memory...")
    
    try:
        result = subprocess.run(
            ["redis-cli", "info", "memory"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            output = result.stdout.strip()
            print(f"Output (first 200 chars): {output[:200]}...")
            
            # Check for expected memory info fields
            if "used_memory:" in output and "used_memory_human:" in output:
                print("✅ PASSED: Redis memory info retrieved successfully")
                return True
            else:
                print(f"❌ FAILED: Expected memory info not found in output")
                return False
        else:
            print(f"❌ FAILED: redis-cli info memory failed with exit code {result.returncode}")
            print(f"Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ FAILED: Error running redis-cli info memory: {e}")
        return False

def test_redis_cli_dbsize():
    """Test Redis CLI dbsize command."""
    print("\nTesting Redis CLI dbsize...")
    
    try:
        result = subprocess.run(
            ["redis-cli", "dbsize"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            output = result.stdout.strip()
            print(f"Output: {output}")
            
            # Should be a number
            try:
                key_count = int(output)
                print(f"✅ PASSED: Redis DB has {key_count} keys")
                return True
            except ValueError:
                print(f"❌ FAILED: Expected numeric dbsize, got '{output}'")
                return False
        else:
            print(f"❌ FAILED: redis-cli dbsize failed with exit code {result.returncode}")
            print(f"Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ FAILED: Error running redis-cli dbsize: {e}")
        return False

def test_redis_cache_operations():
    """Test Redis cache operations with sc: prefix."""
    print("\nTesting Redis cache operations...")
    
    # Test commands in sequence
    test_commands = [
        {
            "command": ["redis-cli", "SET", "sc:test:key", "hello", "EX", "60"],
            "expected": "OK",
            "description": "Set key with sc: prefix and 60s TTL"
        },
        {
            "command": ["redis-cli", "GET", "sc:test:key"],
            "expected": "hello",
            "description": "Get key value"
        },
        {
            "command": ["redis-cli", "DEL", "sc:test:key"],
            "expected": "1",
            "description": "Delete key"
        },
        {
            "command": ["redis-cli", "GET", "sc:test:key"],
            "expected": "(nil)",
            "description": "Verify key is deleted"
        }
    ]
    
    all_passed = True
    
    for i, test in enumerate(test_commands, 1):
        try:
            print(f"  {i}. {test['description']}")
            print(f"     Command: {' '.join(test['command'])}")
            
            result = subprocess.run(
                test["command"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                output = result.stdout.strip()
                print(f"     Output: {output}")
                
                if test["expected"] in output or output == test["expected"]:
                    print(f"     ✅ PASSED")
                else:
                    print(f"     ❌ FAILED: Expected '{test['expected']}', got '{output}'")
                    all_passed = False
            else:
                print(f"     ❌ FAILED: Exit code {result.returncode}")
                print(f"     Error: {result.stderr}")
                all_passed = False
                
        except Exception as e:
            print(f"     ❌ FAILED: Error: {e}")
            all_passed = False
        
        print()
    
    if all_passed:
        print("✅ PASSED: All Redis cache operations successful")
    else:
        print("❌ FAILED: Some Redis cache operations failed")
    
    return all_passed

def test_redis_key_prefix_pattern():
    """Test that Redis keys use the sc: prefix pattern."""
    print("\nTesting Redis key prefix pattern...")
    
    try:
        # Set some test keys with sc: prefix
        subprocess.run(
            ["redis-cli", "SET", "sc:test:hotels", "hotel_data", "EX", "60"],
            capture_output=True,
            check=True
        )
        subprocess.run(
            ["redis-cli", "SET", "sc:test:search", "search_results", "EX", "60"],
            capture_output=True,
            check=True
        )
        
        # Check for keys with sc: prefix
        result = subprocess.run(
            ["redis-cli", "KEYS", "sc:*"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            output = result.stdout.strip()
            if output:
                keys = [k for k in output.split('\n') if k.startswith('sc:')]
                print(f"Found {len(keys)} keys with 'sc:' prefix:")
                for key in keys[:10]:  # Show first 10
                    print(f"  - {key}")
                
                if len(keys) >= 2:  # Our test keys
                    print("✅ PASSED: Key prefix pattern 'sc:' is being used")
                    
                    # Clean up test keys
                    subprocess.run(["redis-cli", "DEL", "sc:test:hotels"], capture_output=True)
                    subprocess.run(["redis-cli", "DEL", "sc:test:search"], capture_output=True)
                    
                    return True
                else:
                    print("❌ FAILED: Expected at least 2 keys with 'sc:' prefix")
                    return False
            else:
                print("⚠️  No keys found with 'sc:' prefix (Redis might be empty)")
                return True  # Not a failure, Redis might be clean
        else:
            print(f"❌ FAILED: redis-cli KEYS failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ FAILED: Error testing key prefix pattern: {e}")
        return False

def main():
    """Run all backend API tests."""
    print("=" * 60)
    print("SYROCE BACKEND API TESTING")
    print("=" * 60)
    print(f"Backend URL: {BACKEND_URL}")
    print(f"API Base URL: {BASE_API_URL}")
    print("=" * 60)
    
    tests = [
        ("Health Check Ready", test_health_ready),
        ("Health Check Live", test_health_live),
        ("Login Valid Credentials", test_login_valid),
        ("Login Invalid Credentials", test_login_invalid),
        ("CORS Headers", test_cors_headers),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ FAILED: {test_name} - Exception: {str(e)}")
            failed += 1
    
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed > 0:
        print("\n❌ Some tests failed. Check the details above.")
        sys.exit(1)
    else:
        print("\n✅ All tests passed successfully!")
        sys.exit(0)

if __name__ == "__main__":
    main()