#!/usr/bin/env python3
"""
Backend test script for auth JWT and org context CI fix validation
Based on Turkish review request requirements.
"""

import asyncio
import httpx
import json
from typing import Dict, Any

# Configuration
BASE_URL = "https://travel-saas-refactor.preview.emergentagent.com"
ADMIN_CREDENTIALS = {"email": "admin@acenta.test", "password": "admin123"}

class BackendTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.admin_token = None
        self.results = []

    def log_result(self, test_name: str, success: bool, details: str = ""):
        status = "✅ PASSED" if success else "❌ FAILED"
        self.results.append(f"{status} {test_name}: {details}")
        print(f"{status} {test_name}: {details}")

    async def test_health_endpoint(self):
        """Test GET /api/health"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/health")
                success = response.status_code == 200
                details = f"Status: {response.status_code}"
                if success:
                    data = response.json()
                    details += f", Response: {data}"
                self.log_result("GET /api/health", success, details)
                return success
        except Exception as e:
            self.log_result("GET /api/health", False, f"Exception: {str(e)}")
            return False

    async def test_login_endpoint(self):
        """Test POST /api/auth/login with admin@acenta.test"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/auth/login",
                    json=ADMIN_CREDENTIALS
                )
                success = response.status_code == 200
                details = f"Status: {response.status_code}"
                
                if success:
                    data = response.json()
                    self.admin_token = data.get("access_token")
                    token_length = len(self.admin_token) if self.admin_token else 0
                    details += f", Token length: {token_length}"
                else:
                    details += f", Error: {response.text}"
                
                self.log_result("POST /api/auth/login", success, details)
                return success
        except Exception as e:
            self.log_result("POST /api/auth/login", False, f"Exception: {str(e)}")
            return False

    async def test_auth_me_endpoint(self):
        """Test GET /api/auth/me with admin token"""
        if not self.admin_token:
            self.log_result("GET /api/auth/me", False, "No admin token available")
            return False

        try:
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {self.admin_token}"}
                response = await client.get(f"{self.base_url}/api/auth/me", headers=headers)
                success = response.status_code == 200
                details = f"Status: {response.status_code}"
                
                if success:
                    data = response.json()
                    email = data.get("email", "No email")
                    details += f", Email: {email}"
                else:
                    details += f", Error: {response.text}"
                
                self.log_result("GET /api/auth/me", success, details)
                return success
        except Exception as e:
            self.log_result("GET /api/auth/me", False, f"Exception: {str(e)}")
            return False

    async def test_mobile_auth_me_endpoint(self):
        """Test GET /api/v1/mobile/auth/me with admin token"""
        if not self.admin_token:
            self.log_result("GET /api/v1/mobile/auth/me", False, "No admin token available")
            return False

        try:
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {self.admin_token}"}
                response = await client.get(f"{self.base_url}/api/v1/mobile/auth/me", headers=headers)
                success = response.status_code == 200
                details = f"Status: {response.status_code}"
                
                if success:
                    data = response.json()
                    email = data.get("email", "No email")
                    # Check for no sensitive fields
                    sensitive_fields = ["password_hash", "totp_secret", "_id"]
                    has_sensitive = any(field in data for field in sensitive_fields)
                    details += f", Email: {email}, Sensitive fields: {'FOUND' if has_sensitive else 'NONE'}"
                else:
                    details += f", Error: {response.text}"
                
                self.log_result("GET /api/v1/mobile/auth/me", success, details)
                return success
        except Exception as e:
            self.log_result("GET /api/v1/mobile/auth/me", False, f"Exception: {str(e)}")
            return False

    async def run_all_tests(self):
        """Run all backend tests"""
        print("🔥 BACKEND AUTH JWT AND ORG CONTEXT CI FIX VALIDATION")
        print("=" * 60)
        
        test_methods = [
            self.test_health_endpoint,
            self.test_login_endpoint,
            self.test_auth_me_endpoint,
            self.test_mobile_auth_me_endpoint,
        ]
        
        passed_count = 0
        total_count = len(test_methods)
        
        for test_method in test_methods:
            success = await test_method()
            if success:
                passed_count += 1
        
        print("\n" + "=" * 60)
        print(f"SUMMARY: {passed_count}/{total_count} tests passed")
        
        if passed_count == total_count:
            print("🎉 ALL TESTS PASSED - CI fix validation successful!")
        else:
            print("⚠️  SOME TESTS FAILED - CI fix needs attention")
        
        return passed_count == total_count


async def main():
    tester = BackendTester()
    success = await tester.run_all_tests()
    return success

if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)