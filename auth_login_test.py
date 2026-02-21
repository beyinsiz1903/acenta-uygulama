#!/usr/bin/env python3
"""
Auth Login Endpoint Testing Script
Tests the POST /api/auth/login endpoint with valid and invalid credentials
"""
import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "https://booking-lifecycle-2.preview.emergentagent.com"
VALID_CREDENTIALS = {
    "email": "admin@acenta.test",
    "password": "admin123"
}
INVALID_CREDENTIALS = {
    "email": "admin@acenta.test", 
    "password": "wrongpassword"
}

class AuthLoginTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.test_results = []

    def log_result(self, test_name, success, message, curl_command=None, response_data=None):
        """Log test result with curl command"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "curl_command": curl_command,
            "timestamp": datetime.now().isoformat(),
            "response_data": response_data
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}: {message}")
        if curl_command:
            print(f"   CURL: {curl_command}")
        return success

    def test_valid_login(self):
        """Test POST /api/auth/login with valid credentials"""
        try:
            print("\n🔐 Testing valid login credentials...")
            login_url = f"{self.base_url}/api/auth/login"
            
            # Prepare curl command for logging
            curl_command = f'curl -X POST "{login_url}" -H "Content-Type: application/json" -d \'{json.dumps(VALID_CREDENTIALS)}\''
            
            response = requests.post(login_url, json=VALID_CREDENTIALS)
            
            print(f"   Status Code: {response.status_code}")
            print(f"   Response Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"   Response Body: {json.dumps(data, indent=2)}")
                    
                    if "access_token" in data:
                        return self.log_result(
                            "Valid Login", 
                            True, 
                            f"Successfully logged in with status 200, received access_token",
                            curl_command,
                            data
                        )
                    else:
                        return self.log_result(
                            "Valid Login", 
                            False, 
                            f"Status 200 but no access_token in response: {data}",
                            curl_command,
                            data
                        )
                except json.JSONDecodeError as e:
                    return self.log_result(
                        "Valid Login", 
                        False, 
                        f"Status 200 but invalid JSON response: {response.text}",
                        curl_command,
                        {"raw_response": response.text}
                    )
            else:
                try:
                    error_data = response.json()
                    print(f"   Error Response: {json.dumps(error_data, indent=2)}")
                except:
                    error_data = {"raw_response": response.text}
                    print(f"   Raw Error Response: {response.text}")
                
                return self.log_result(
                    "Valid Login", 
                    False, 
                    f"Expected 200 but got {response.status_code}",
                    curl_command,
                    error_data
                )
        except Exception as e:
            return self.log_result(
                "Valid Login", 
                False, 
                f"Exception occurred: {str(e)}",
                curl_command
            )

    def test_invalid_login(self):
        """Test POST /api/auth/login with invalid credentials"""
        try:
            print("\n🚫 Testing invalid login credentials...")
            login_url = f"{self.base_url}/api/auth/login"
            
            # Prepare curl command for logging
            curl_command = f'curl -X POST "{login_url}" -H "Content-Type: application/json" -d \'{json.dumps(INVALID_CREDENTIALS)}\''
            
            response = requests.post(login_url, json=INVALID_CREDENTIALS)
            
            print(f"   Status Code: {response.status_code}")
            print(f"   Response Headers: {dict(response.headers)}")
            
            if response.status_code == 401:
                try:
                    data = response.json()
                    print(f"   Response Body: {json.dumps(data, indent=2)}")
                    
                    return self.log_result(
                        "Invalid Login", 
                        True, 
                        f"Correctly returned 401 for invalid credentials",
                        curl_command,
                        data
                    )
                except json.JSONDecodeError as e:
                    print(f"   Raw Response: {response.text}")
                    return self.log_result(
                        "Invalid Login", 
                        True, 
                        f"Correctly returned 401 for invalid credentials (non-JSON response)",
                        curl_command,
                        {"raw_response": response.text}
                    )
            else:
                try:
                    error_data = response.json()
                    print(f"   Unexpected Response: {json.dumps(error_data, indent=2)}")
                except:
                    error_data = {"raw_response": response.text}
                    print(f"   Raw Unexpected Response: {response.text}")
                
                return self.log_result(
                    "Invalid Login", 
                    False, 
                    f"Expected 401 but got {response.status_code}",
                    curl_command,
                    error_data
                )
        except Exception as e:
            return self.log_result(
                "Invalid Login", 
                False, 
                f"Exception occurred: {str(e)}",
                curl_command
            )

    def test_cors_and_headers(self):
        """Test CORS and response headers"""
        try:
            print("\n🌐 Testing CORS and headers...")
            login_url = f"{self.base_url}/api/auth/login"
            
            # Test OPTIONS request for CORS preflight
            curl_command = f'curl -X OPTIONS "{login_url}" -H "Origin: https://example.com" -H "Access-Control-Request-Method: POST" -H "Access-Control-Request-Headers: Content-Type"'
            
            response = requests.options(
                login_url,
                headers={
                    "Origin": "https://example.com",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "Content-Type"
                }
            )
            
            print(f"   OPTIONS Status Code: {response.status_code}")
            print(f"   CORS Headers: {dict(response.headers)}")
            
            cors_headers = {
                "access-control-allow-origin": response.headers.get("access-control-allow-origin"),
                "access-control-allow-methods": response.headers.get("access-control-allow-methods"),
                "access-control-allow-headers": response.headers.get("access-control-allow-headers"),
                "access-control-allow-credentials": response.headers.get("access-control-allow-credentials")
            }
            
            if response.status_code in [200, 204]:
                return self.log_result(
                    "CORS Headers", 
                    True, 
                    f"CORS preflight successful with status {response.status_code}",
                    curl_command,
                    cors_headers
                )
            else:
                return self.log_result(
                    "CORS Headers", 
                    False, 
                    f"CORS preflight failed with status {response.status_code}",
                    curl_command,
                    cors_headers
                )
        except Exception as e:
            return self.log_result(
                "CORS Headers", 
                False, 
                f"Exception occurred: {str(e)}",
                curl_command
            )

    def run_all_tests(self):
        """Run all auth login tests"""
        print("🚀 Starting Auth Login Endpoint Tests")
        print("=" * 60)
        print(f"Target URL: {BASE_URL}/api/auth/login")
        print(f"Valid Credentials: {VALID_CREDENTIALS}")
        print(f"Invalid Credentials: {INVALID_CREDENTIALS}")
        print("=" * 60)
        
        # Run all tests
        tests = [
            self.test_valid_login,
            self.test_invalid_login,
            self.test_cors_and_headers
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            if test():
                passed += 1
        
        # Print detailed summary
        print("\n" + "=" * 60)
        print(f"📋 AUTH LOGIN TEST SUMMARY: {passed}/{total} tests passed")
        print("=" * 60)
        
        for result in self.test_results:
            status = "✅" if result["success"] else "❌"
            print(f"\n{status} {result['test']}")
            print(f"   Result: {result['message']}")
            if result.get('curl_command'):
                print(f"   CURL: {result['curl_command']}")
            if result.get('response_data'):
                print(f"   Data: {json.dumps(result['response_data'], indent=4)}")
        
        # Summary for main agent
        print("\n" + "=" * 60)
        print("🎯 SUMMARY FOR MAIN AGENT:")
        
        if passed == total:
            print("✅ All auth login tests PASSED")
            print("✅ Valid admin credentials (admin@acenta.test / admin123) work correctly")
            print("✅ Invalid credentials properly return 401")
            print("✅ CORS headers are configured correctly")
        else:
            print("❌ Some auth login tests FAILED")
            failed_tests = [r for r in self.test_results if not r["success"]]
            for failed in failed_tests:
                print(f"   ❌ {failed['test']}: {failed['message']}")
        
        return passed == total

if __name__ == "__main__":
    tester = AuthLoginTester()
    success = tester.run_all_tests()
    exit(0 if success else 1)