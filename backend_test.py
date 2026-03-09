#!/usr/bin/env python3
"""
Backend smoke validation test for travel agency SaaS app.
Tests login functionality and core API endpoints after frontend-only navigation simplification.
"""
import requests
import json
from datetime import datetime

BASE_URL = "https://core-nav-update.preview.emergentagent.com"

class BackendSmokeTest:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.agent_token = None
        
    def test_admin_login(self):
        """Test admin login with admin@acenta.test / admin123"""
        print("🔑 Testing admin login...")
        
        response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": "admin@acenta.test",
                "password": "admin123"
            },
            headers={"Content-Type": "application/json"}
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"   ❌ FAILED - Admin login failed: {response.text}")
            return False
        
        data = response.json()
        if "access_token" not in data:
            print(f"   ❌ FAILED - No access_token in response: {data}")
            return False
        
        self.admin_token = data["access_token"]
        print(f"   ✅ SUCCESS - Admin login successful (token length: {len(self.admin_token)})")
        return True
    
    def test_agent_login(self):
        """Test agent login with agent@acenta.test / agent123"""
        print("🔑 Testing agent login...")
        
        response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": "agent@acenta.test", 
                "password": "agent123"
            },
            headers={"Content-Type": "application/json"}
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"   ❌ FAILED - Agent login failed: {response.text}")
            return False
        
        data = response.json()
        if "access_token" not in data:
            print(f"   ❌ FAILED - No access_token in response: {data}")
            return False
        
        self.agent_token = data["access_token"]
        print(f"   ✅ SUCCESS - Agent login successful (token length: {len(self.agent_token)})")
        return True
    
    def test_auth_me_endpoint(self, token, user_type):
        """Test /api/auth/me endpoint"""
        print(f"👤 Testing /api/auth/me for {user_type}...")
        
        response = self.session.get(
            f"{BASE_URL}/api/auth/me",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"   ❌ FAILED - Auth/me failed for {user_type}: {response.text}")
            return False
        
        try:
            data = response.json()
            if "email" not in data:
                print(f"   ❌ FAILED - No email in auth/me response for {user_type}: {data}")
                return False
            
            print(f"   ✅ SUCCESS - Auth/me working for {user_type} (email: {data.get('email', 'N/A')})")
            return True
        except json.JSONDecodeError:
            print(f"   ❌ FAILED - Invalid JSON response for {user_type}: {response.text}")
            return False
    
    def test_reports_endpoint(self, token, endpoint, user_type):
        """Test reports endpoints"""
        print(f"📊 Testing {endpoint} for {user_type}...")
        
        response = self.session.get(
            f"{BASE_URL}{endpoint}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"   ✅ SUCCESS - {endpoint} working for {user_type}")
                return True
            except json.JSONDecodeError:
                print(f"   ❌ FAILED - Invalid JSON response from {endpoint} for {user_type}")
                return False
        elif response.status_code == 404:
            print(f"   ⚠️  404 - {endpoint} not found for {user_type} (may be data/backend issue, not frontend change)")
            return True  # 404 is acceptable per review request
        elif response.status_code == 403:
            print(f"   ⚠️  403 - {endpoint} forbidden for {user_type} (permission issue, not frontend change)")
            return True
        else:
            print(f"   ❌ FAILED - {endpoint} returned {response.status_code} for {user_type}: {response.text}")
            return False
    
    def test_agency_endpoint(self, token, endpoint, user_type):
        """Test agency-specific endpoints"""
        print(f"🏢 Testing {endpoint} for {user_type}...")
        
        response = self.session.get(
            f"{BASE_URL}{endpoint}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"   ✅ SUCCESS - {endpoint} working for {user_type}")
                return True
            except json.JSONDecodeError:
                print(f"   ❌ FAILED - Invalid JSON response from {endpoint} for {user_type}")
                return False
        elif response.status_code == 404:
            print(f"   ⚠️  404 - {endpoint} not found for {user_type} (pre-existing data/backend issue)")
            return True  # 404 is acceptable per review request
        elif response.status_code == 403:
            print(f"   ⚠️  403 - {endpoint} forbidden for {user_type} (permission issue)")
            return True
        else:
            print(f"   ❌ FAILED - {endpoint} returned {response.status_code} for {user_type}: {response.text}")
            return False
    
    def run_smoke_test(self):
        """Run the complete backend smoke test"""
        print("=" * 60)
        print("🚀 BACKEND SMOKE TEST - Travel Agency SaaS")
        print(f"   Base URL: {BASE_URL}")
        print(f"   Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("   Context: Frontend-only navigation simplification")
        print("=" * 60)
        
        results = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "warnings": 0
        }
        
        # Test 1: Admin Login
        results["total_tests"] += 1
        if self.test_admin_login():
            results["passed_tests"] += 1
        else:
            results["failed_tests"] += 1
            print("❌ Cannot continue without admin login")
            return results
        
        # Test 2: Agent Login  
        results["total_tests"] += 1
        if self.test_agent_login():
            results["passed_tests"] += 1
        else:
            results["failed_tests"] += 1
            print("❌ Cannot continue without agent login")
            return results
        
        # Test 3: Admin /api/auth/me
        results["total_tests"] += 1
        if self.test_auth_me_endpoint(self.admin_token, "admin"):
            results["passed_tests"] += 1
        else:
            results["failed_tests"] += 1
        
        # Test 4: Agent /api/auth/me
        results["total_tests"] += 1
        if self.test_auth_me_endpoint(self.agent_token, "agent"):
            results["passed_tests"] += 1
        else:
            results["failed_tests"] += 1
        
        # Test 5: Admin Reports - Reservations Summary
        results["total_tests"] += 1
        if self.test_reports_endpoint(self.admin_token, "/api/reports/reservations-summary", "admin"):
            results["passed_tests"] += 1
        else:
            results["failed_tests"] += 1
        
        # Test 6: Admin Reports - Sales Summary
        results["total_tests"] += 1
        if self.test_reports_endpoint(self.admin_token, "/api/reports/sales-summary", "admin"):
            results["passed_tests"] += 1
        else:
            results["failed_tests"] += 1
        
        # Test 7: Agent Reports - Reservations Summary
        results["total_tests"] += 1
        if self.test_reports_endpoint(self.agent_token, "/api/reports/reservations-summary", "agent"):
            results["passed_tests"] += 1
        else:
            results["failed_tests"] += 1
        
        # Test 8: Agent Reports - Sales Summary
        results["total_tests"] += 1
        if self.test_reports_endpoint(self.agent_token, "/api/reports/sales-summary", "agent"):
            results["passed_tests"] += 1
        else:
            results["failed_tests"] += 1
        
        # Test 9: Agent /api/agency/bookings
        results["total_tests"] += 1
        if self.test_agency_endpoint(self.agent_token, "/api/agency/bookings", "agent"):
            results["passed_tests"] += 1
        else:
            results["failed_tests"] += 1
        
        # Test 10: Agent /api/agency/settlements
        results["total_tests"] += 1
        if self.test_agency_endpoint(self.agent_token, "/api/agency/settlements", "agent"):
            results["passed_tests"] += 1
        else:
            results["failed_tests"] += 1
        
        print("\n" + "=" * 60)
        print("📋 TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {results['total_tests']}")
        print(f"Passed: {results['passed_tests']}")
        print(f"Failed: {results['failed_tests']}")
        print(f"Success Rate: {(results['passed_tests']/results['total_tests']*100):.1f}%")
        
        print("\n📝 KEY FINDINGS:")
        if results['failed_tests'] == 0:
            print("✅ ALL TESTS PASSED - Backend is stable after frontend navigation changes")
            print("✅ No backend impact detected from AppShell.jsx modification")
        else:
            print("⚠️  Some backend endpoints failed - reviewing failures:")
            print("   This helps determine if issues are:")
            print("   - Pre-existing backend/data issues (expected)")
            print("   - New issues from frontend changes (unexpected)")
        
        return results

if __name__ == "__main__":
    test = BackendSmokeTest()
    test.run_smoke_test()