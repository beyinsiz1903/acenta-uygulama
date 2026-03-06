#!/usr/bin/env python3
"""
Backend Smoke Test for Web SaaS Application
Target: https://dashboard-stabilize.preview.emergentagent.com
"""

import requests
import json
import sys
from typing import Dict, Any, Optional

class BackendSmokeTest:
    def __init__(self, base_url: str, email: str, password: str):
        self.base_url = base_url.rstrip('/')
        self.email = email
        self.password = password
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.session = requests.Session()
        self.session.timeout = 30
        
    def log(self, message: str, level: str = "INFO"):
        """Log test messages"""
        print(f"[{level}] {message}")
        
    def test_login(self) -> bool:
        """Test POST /api/auth/login"""
        self.log("Testing POST /api/auth/login...")
        
        login_url = f"{self.base_url}/api/auth/login"
        payload = {
            "email": self.email,
            "password": self.password
        }
        
        try:
            response = self.session.post(login_url, json=payload)
            self.log(f"Login response status: {response.status_code}")
            
            if response.status_code >= 500:
                self.log(f"🚨 5XX ERROR: {response.status_code} - {response.text}", "ERROR")
                return False
                
            if response.status_code != 200:
                self.log(f"❌ Login failed with status: {response.status_code}", "ERROR")
                self.log(f"Response: {response.text}", "ERROR")
                return False
                
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                self.log(f"🚨 JSON DECODE ERROR: {e}", "ERROR")
                self.log(f"Raw response: {response.text}", "ERROR")
                return False
                
            # Check for tokens
            if 'access_token' not in data:
                self.log("❌ Missing access_token in login response", "ERROR")
                return False
                
            if 'refresh_token' not in data:
                self.log("❌ Missing refresh_token in login response", "ERROR")
                return False
                
            self.access_token = data['access_token']
            self.refresh_token = data['refresh_token']
            
            self.log("✅ Login successful - tokens received")
            return True
            
        except requests.exceptions.RequestException as e:
            self.log(f"🚨 LOGIN REQUEST ERROR: {e}", "ERROR")
            return False
            
    def test_auth_me(self) -> bool:
        """Test GET /api/auth/me with token"""
        if not self.access_token:
            self.log("❌ No access token available for /auth/me test", "ERROR")
            return False
            
        self.log("Testing GET /api/auth/me...")
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        me_url = f"{self.base_url}/api/auth/me"
        
        try:
            response = self.session.get(me_url, headers=headers)
            self.log(f"/auth/me response status: {response.status_code}")
            
            if response.status_code >= 500:
                self.log(f"🚨 5XX ERROR: {response.status_code} - {response.text}", "ERROR")
                return False
                
            if response.status_code == 401:
                self.log("🚨 AUTH BROKEN: 401 Unauthorized on /auth/me", "ERROR")
                return False
                
            if response.status_code != 200:
                self.log(f"❌ /auth/me failed with status: {response.status_code}", "ERROR")
                return False
                
            try:
                data = response.json()
                self.log("✅ /auth/me working - user data received")
                return True
            except json.JSONDecodeError as e:
                self.log(f"🚨 JSON DECODE ERROR in /auth/me: {e}", "ERROR")
                return False
                
        except requests.exceptions.RequestException as e:
            self.log(f"🚨 AUTH/ME REQUEST ERROR: {e}", "ERROR")
            return False
            
    def test_admin_agencies(self) -> bool:
        """Test GET /api/admin/agencies with token"""
        if not self.access_token:
            self.log("❌ No access token available for /admin/agencies test", "ERROR")
            return False
            
        self.log("Testing GET /api/admin/agencies...")
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        agencies_url = f"{self.base_url}/api/admin/agencies"
        
        try:
            response = self.session.get(agencies_url, headers=headers)
            self.log(f"/admin/agencies response status: {response.status_code}")
            
            if response.status_code >= 500:
                self.log(f"🚨 5XX ERROR: {response.status_code} - {response.text}", "ERROR")
                return False
                
            if response.status_code == 401:
                self.log("🚨 AUTH BROKEN: 401 Unauthorized on /admin/agencies", "ERROR")
                return False
                
            if response.status_code != 200:
                self.log(f"❌ /admin/agencies failed with status: {response.status_code}", "ERROR")
                return False
                
            try:
                data = response.json()
                self.log("✅ /admin/agencies working - data received")
                return True
            except json.JSONDecodeError as e:
                self.log(f"🚨 JSON DECODE ERROR in /admin/agencies: {e}", "ERROR")
                return False
                
        except requests.exceptions.RequestException as e:
            self.log(f"🚨 ADMIN/AGENCIES REQUEST ERROR: {e}", "ERROR")
            return False
            
    def test_dashboard_endpoint(self) -> bool:
        """Test critical dashboard endpoint"""
        if not self.access_token:
            self.log("❌ No access token available for dashboard test", "ERROR")
            return False
            
        self.log("Testing dashboard endpoints...")
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        # Try multiple potential dashboard endpoints
        endpoints = [
            "/api/dashboard/popular-products",
            "/api/dashboard/stats",
            "/api/dashboard/summary"
        ]
        
        for endpoint in endpoints:
            url = f"{self.base_url}{endpoint}"
            try:
                response = self.session.get(url, headers=headers)
                self.log(f"{endpoint} response status: {response.status_code}")
                
                if response.status_code >= 500:
                    self.log(f"🚨 5XX ERROR on {endpoint}: {response.status_code} - {response.text}", "ERROR")
                    continue
                    
                if response.status_code == 401:
                    self.log(f"🚨 AUTH BROKEN on {endpoint}: 401 Unauthorized", "ERROR")
                    continue
                    
                if response.status_code == 200:
                    try:
                        data = response.json()
                        self.log(f"✅ {endpoint} working - data received")
                        return True
                    except json.JSONDecodeError as e:
                        self.log(f"🚨 JSON DECODE ERROR in {endpoint}: {e}", "ERROR")
                        continue
                        
                elif response.status_code == 404:
                    self.log(f"ℹ️  {endpoint} not found (404) - endpoint may not exist")
                else:
                    self.log(f"⚠️  {endpoint} returned {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                self.log(f"🚨 REQUEST ERROR for {endpoint}: {e}", "ERROR")
                continue
                
        self.log("⚠️  No working dashboard endpoints found - may be WAF/preview restrictions")
        return False
        
    def run_smoke_test(self) -> Dict[str, bool]:
        """Run complete smoke test suite"""
        self.log("🚀 Starting Backend Smoke Test")
        self.log(f"Target: {self.base_url}")
        self.log(f"Admin: {self.email}")
        
        results = {
            "login": False,
            "auth_me": False, 
            "admin_agencies": False,
            "dashboard": False
        }
        
        # Test 1: Login
        results["login"] = self.test_login()
        
        # Test 2: Auth me (requires login success)
        if results["login"]:
            results["auth_me"] = self.test_auth_me()
        else:
            self.log("⏭️  Skipping /auth/me test - login failed")
            
        # Test 3: Admin agencies (requires login success)
        if results["login"]:
            results["admin_agencies"] = self.test_admin_agencies()
        else:
            self.log("⏭️  Skipping /admin/agencies test - login failed")
            
        # Test 4: Dashboard endpoint (requires login success)
        if results["login"]:
            results["dashboard"] = self.test_dashboard_endpoint()
        else:
            self.log("⏭️  Skipping dashboard test - login failed")
            
        return results
        
    def print_summary(self, results: Dict[str, bool]):
        """Print test summary"""
        self.log("=" * 50)
        self.log("📋 SMOKE TEST SUMMARY")
        self.log("=" * 50)
        
        total_tests = len(results)
        passed_tests = sum(results.values())
        
        for test_name, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            self.log(f"{test_name.upper()}: {status}")
            
        self.log("-" * 50)
        self.log(f"OVERALL: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            self.log("🎉 ALL TESTS PASSED - Backend is healthy")
        elif passed_tests == 0:
            self.log("🚨 ALL TESTS FAILED - Critical backend issues")
        else:
            self.log("⚠️  PARTIAL SUCCESS - Some endpoints failing")


def main():
    """Main test execution"""
    base_url = "https://dashboard-stabilize.preview.emergentagent.com"
    email = "admin@acenta.test"
    password = "admin123"
    
    tester = BackendSmokeTest(base_url, email, password)
    results = tester.run_smoke_test()
    tester.print_summary(results)
    
    # Exit with appropriate code
    if all(results.values()):
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Failure


if __name__ == "__main__":
    main()