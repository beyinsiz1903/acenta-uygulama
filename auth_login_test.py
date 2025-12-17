#!/usr/bin/env python3
"""
AUTH LOGIN FLOW TESTING
Test the auth login flow on the running backend for preview environment.

OBJECTIVE: Test authentication endpoints with specific credentials:
1) POST /api/auth/login with email muratsutay@hotmail.com and password murat1903. 
   Expect 200 and response contains access_token, user.role == "super_admin".
2) Then call GET /api/auth/me with Bearer token. Expect 200 and user.email matches.
3) Also test existing demo login still works: POST /api/auth/login with demo@hotel.com / demo123 should return 200.

Report any errors and the response bodies (redact token).
"""

import asyncio
import aiohttp
import json
import sys
import os
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

# Configuration
BACKEND_URL = "https://code-review-helper-12.preview.emergentagent.com/api"

class AuthLoginTester:
    def __init__(self):
        self.session = None
        self.test_results = []

    async def setup_session(self):
        """Initialize HTTP session"""
        self.session = aiohttp.ClientSession()

    async def cleanup_session(self):
        """Cleanup HTTP session"""
        if self.session:
            await self.session.close()

    def redact_token(self, response_data):
        """Redact sensitive token information from response"""
        if isinstance(response_data, dict):
            redacted = response_data.copy()
            if 'access_token' in redacted:
                token = redacted['access_token']
                if len(token) > 20:
                    redacted['access_token'] = f"{token[:10]}...{token[-10:]}"
                else:
                    redacted['access_token'] = "***REDACTED***"
            return redacted
        return response_data

    async def test_super_admin_login(self):
        """Test login with muratsutay@hotmail.com / murat1903 - expect super_admin role"""
        print("\n🔐 Testing Super Admin Login (muratsutay@hotmail.com / murat1903)...")
        
        login_data = {
            "email": "muratsutay@hotmail.com",
            "password": "murat1903"
        }
        
        try:
            start_time = datetime.now()
            async with self.session.post(f"{BACKEND_URL}/auth/login", json=login_data) as response:
                end_time = datetime.now()
                response_time = (end_time - start_time).total_seconds() * 1000
                
                print(f"  📊 Response Status: {response.status}")
                print(f"  ⏱️ Response Time: {response_time:.1f}ms")
                
                if response.status == 200:
                    data = await response.json()
                    redacted_data = self.redact_token(data)
                    
                    print(f"  📄 Response Body (redacted): {json.dumps(redacted_data, indent=2)}")
                    
                    # Verify required fields
                    if 'access_token' in data:
                        print("  ✅ access_token present in response")
                        
                        if 'user' in data and 'role' in data['user']:
                            user_role = data['user']['role']
                            print(f"  📊 User Role: {user_role}")
                            
                            if user_role == "super_admin":
                                print("  ✅ User role is super_admin as expected")
                                
                                # Store token for /auth/me test
                                self.super_admin_token = data['access_token']
                                self.super_admin_email = data['user'].get('email', 'N/A')
                                
                                self.test_results.append({
                                    "test": "Super Admin Login",
                                    "status": "PASSED",
                                    "response_time": f"{response_time:.1f}ms",
                                    "details": f"Login successful, role: {user_role}"
                                })
                                return True
                            else:
                                print(f"  ❌ Expected role 'super_admin', got '{user_role}'")
                                self.test_results.append({
                                    "test": "Super Admin Login",
                                    "status": "FAILED",
                                    "response_time": f"{response_time:.1f}ms",
                                    "details": f"Wrong role: expected 'super_admin', got '{user_role}'"
                                })
                        else:
                            print("  ❌ User or role field missing in response")
                            self.test_results.append({
                                "test": "Super Admin Login",
                                "status": "FAILED",
                                "response_time": f"{response_time:.1f}ms",
                                "details": "User or role field missing in response"
                            })
                    else:
                        print("  ❌ access_token missing in response")
                        self.test_results.append({
                            "test": "Super Admin Login",
                            "status": "FAILED",
                            "response_time": f"{response_time:.1f}ms",
                            "details": "access_token missing in response"
                        })
                else:
                    error_text = await response.text()
                    print(f"  ❌ Login failed with status {response.status}")
                    print(f"  📄 Error Response: {error_text}")
                    
                    self.test_results.append({
                        "test": "Super Admin Login",
                        "status": "FAILED",
                        "response_time": f"{response_time:.1f}ms",
                        "details": f"HTTP {response.status}: {error_text[:200]}"
                    })
                    
        except Exception as e:
            print(f"  ❌ Exception during super admin login: {e}")
            self.test_results.append({
                "test": "Super Admin Login",
                "status": "ERROR",
                "response_time": "N/A",
                "details": f"Exception: {str(e)}"
            })
            
        return False

    async def test_super_admin_me_endpoint(self):
        """Test GET /auth/me with super admin token"""
        print("\n👤 Testing /auth/me with Super Admin Token...")
        
        if not hasattr(self, 'super_admin_token'):
            print("  ⚠️ No super admin token available, skipping /auth/me test")
            self.test_results.append({
                "test": "Super Admin /auth/me",
                "status": "SKIPPED",
                "response_time": "N/A",
                "details": "No token available from login test"
            })
            return False
        
        headers = {
            "Authorization": f"Bearer {self.super_admin_token}",
            "Content-Type": "application/json"
        }
        
        try:
            start_time = datetime.now()
            async with self.session.get(f"{BACKEND_URL}/auth/me", headers=headers) as response:
                end_time = datetime.now()
                response_time = (end_time - start_time).total_seconds() * 1000
                
                print(f"  📊 Response Status: {response.status}")
                print(f"  ⏱️ Response Time: {response_time:.1f}ms")
                
                if response.status == 200:
                    data = await response.json()
                    print(f"  📄 Response Body: {json.dumps(data, indent=2)}")
                    
                    # Verify email matches
                    if 'email' in data:
                        response_email = data['email']
                        expected_email = "muratsutay@hotmail.com"
                        
                        print(f"  📊 Response Email: {response_email}")
                        print(f"  📊 Expected Email: {expected_email}")
                        
                        if response_email == expected_email:
                            print("  ✅ Email matches expected value")
                            
                            self.test_results.append({
                                "test": "Super Admin /auth/me",
                                "status": "PASSED",
                                "response_time": f"{response_time:.1f}ms",
                                "details": f"Email verified: {response_email}"
                            })
                            return True
                        else:
                            print(f"  ❌ Email mismatch: expected '{expected_email}', got '{response_email}'")
                            self.test_results.append({
                                "test": "Super Admin /auth/me",
                                "status": "FAILED",
                                "response_time": f"{response_time:.1f}ms",
                                "details": f"Email mismatch: expected '{expected_email}', got '{response_email}'"
                            })
                    else:
                        print("  ❌ Email field missing in response")
                        self.test_results.append({
                            "test": "Super Admin /auth/me",
                            "status": "FAILED",
                            "response_time": f"{response_time:.1f}ms",
                            "details": "Email field missing in response"
                        })
                else:
                    error_text = await response.text()
                    print(f"  ❌ /auth/me failed with status {response.status}")
                    print(f"  📄 Error Response: {error_text}")
                    
                    self.test_results.append({
                        "test": "Super Admin /auth/me",
                        "status": "FAILED",
                        "response_time": f"{response_time:.1f}ms",
                        "details": f"HTTP {response.status}: {error_text[:200]}"
                    })
                    
        except Exception as e:
            print(f"  ❌ Exception during /auth/me test: {e}")
            self.test_results.append({
                "test": "Super Admin /auth/me",
                "status": "ERROR",
                "response_time": "N/A",
                "details": f"Exception: {str(e)}"
            })
            
        return False

    async def test_demo_login(self):
        """Test existing demo login still works: demo@hotel.com / demo123"""
        print("\n🏨 Testing Demo Login (demo@hotel.com / demo123)...")
        
        login_data = {
            "email": "demo@hotel.com",
            "password": "demo123"
        }
        
        try:
            start_time = datetime.now()
            async with self.session.post(f"{BACKEND_URL}/auth/login", json=login_data) as response:
                end_time = datetime.now()
                response_time = (end_time - start_time).total_seconds() * 1000
                
                print(f"  📊 Response Status: {response.status}")
                print(f"  ⏱️ Response Time: {response_time:.1f}ms")
                
                if response.status == 200:
                    data = await response.json()
                    redacted_data = self.redact_token(data)
                    
                    print(f"  📄 Response Body (redacted): {json.dumps(redacted_data, indent=2)}")
                    
                    # Verify required fields
                    if 'access_token' in data:
                        print("  ✅ access_token present in response")
                        
                        if 'user' in data:
                            user_email = data['user'].get('email', 'N/A')
                            user_role = data['user'].get('role', 'N/A')
                            user_name = data['user'].get('name', 'N/A')
                            
                            print(f"  📊 User Email: {user_email}")
                            print(f"  📊 User Role: {user_role}")
                            print(f"  📊 User Name: {user_name}")
                            
                            if user_email == "demo@hotel.com":
                                print("  ✅ Demo login successful")
                                
                                self.test_results.append({
                                    "test": "Demo Login",
                                    "status": "PASSED",
                                    "response_time": f"{response_time:.1f}ms",
                                    "details": f"Login successful, user: {user_name}, role: {user_role}"
                                })
                                return True
                            else:
                                print(f"  ❌ Email mismatch: expected 'demo@hotel.com', got '{user_email}'")
                                self.test_results.append({
                                    "test": "Demo Login",
                                    "status": "FAILED",
                                    "response_time": f"{response_time:.1f}ms",
                                    "details": f"Email mismatch: expected 'demo@hotel.com', got '{user_email}'"
                                })
                        else:
                            print("  ❌ User field missing in response")
                            self.test_results.append({
                                "test": "Demo Login",
                                "status": "FAILED",
                                "response_time": f"{response_time:.1f}ms",
                                "details": "User field missing in response"
                            })
                    else:
                        print("  ❌ access_token missing in response")
                        self.test_results.append({
                            "test": "Demo Login",
                            "status": "FAILED",
                            "response_time": f"{response_time:.1f}ms",
                            "details": "access_token missing in response"
                        })
                else:
                    error_text = await response.text()
                    print(f"  ❌ Demo login failed with status {response.status}")
                    print(f"  📄 Error Response: {error_text}")
                    
                    self.test_results.append({
                        "test": "Demo Login",
                        "status": "FAILED",
                        "response_time": f"{response_time:.1f}ms",
                        "details": f"HTTP {response.status}: {error_text[:200]}"
                    })
                    
        except Exception as e:
            print(f"  ❌ Exception during demo login: {e}")
            self.test_results.append({
                "test": "Demo Login",
                "status": "ERROR",
                "response_time": "N/A",
                "details": f"Exception: {str(e)}"
            })
            
        return False

    async def run_all_tests(self):
        """Run all authentication tests"""
        print("🚀 AUTH LOGIN FLOW TESTING")
        print("Testing authentication endpoints for preview environment")
        print("Base URL: https://code-review-helper-12.preview.emergentagent.com/api")
        print("=" * 80)
        
        # Setup
        await self.setup_session()
        
        # Run all authentication tests
        print("\n" + "="*60)
        print("🔐 AUTHENTICATION ENDPOINT TESTING")
        print("="*60)
        
        await self.test_super_admin_login()
        await self.test_super_admin_me_endpoint()
        await self.test_demo_login()
        
        # Cleanup
        await self.cleanup_session()
        
        # Print results
        self.print_test_summary()

    def print_test_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "=" * 80)
        print("📊 AUTH LOGIN FLOW TEST RESULTS")
        print("=" * 80)
        
        total_passed = 0
        total_tests = len(self.test_results)
        
        print("\n🔐 AUTHENTICATION TEST RESULTS:")
        print("-" * 70)
        
        for result in self.test_results:
            test_name = result["test"]
            status = result["status"]
            response_time = result.get("response_time", "N/A")
            details = result.get("details", "")
            
            if status == "PASSED":
                status_icon = "✅"
            elif status == "FAILED":
                status_icon = "❌"
            elif status == "ERROR":
                status_icon = "💥"
            else:  # SKIPPED
                status_icon = "⚠️"
            
            print(f"{status_icon} {test_name}: {status} ({response_time})")
            if details:
                print(f"    📝 {details}")
            
            if status == "PASSED":
                total_passed += 1
        
        print("\n" + "=" * 80)
        overall_success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        print(f"📈 OVERALL SUCCESS RATE: {total_passed}/{total_tests} ({overall_success_rate:.1f}%)")
        
        # Final assessment
        if overall_success_rate >= 90:
            print("🎉 RESULT: Authentication system working perfectly ✅")
            print("   All login flows functional and secure")
        elif overall_success_rate >= 75:
            print("✅ RESULT: Authentication system mostly working")
            print("   Most login flows functional, minor issues present")
        elif overall_success_rate >= 50:
            print("⚠️ RESULT: Authentication system has issues")
            print("   Some login flows working, significant problems detected")
        else:
            print("❌ RESULT: Authentication system has critical issues")
            print("   Major authentication problems, immediate attention required")
        
        print("\n🔍 TESTED SCENARIOS:")
        print("• Super Admin Login (muratsutay@hotmail.com / murat1903)")
        print("• Super Admin Token Validation (/auth/me)")
        print("• Demo User Login (demo@hotel.com / demo123)")
        print("• Response structure validation")
        print("• Token security (redacted in logs)")
        print("• Performance metrics")
        
        print("\n" + "=" * 80)

async def main():
    """Main test execution"""
    tester = AuthLoginTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())