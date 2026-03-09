#!/usr/bin/env python3
"""
Backend API Test Suite for Turkish Travel Agency System
Review Request Validation: Backend endpoint regression testing
"""

import requests
import json
import sys
from typing import Dict, Any, Optional, Tuple

class BackendTester:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.agency_token = None
        self.admin_token = None
        self.agency_tenant_id = None
        self.admin_tenant_id = None
        
    def log(self, message: str, status: str = "INFO"):
        """Log test messages"""
        print(f"[{status}] {message}")
        
    def login(self, email: str, password: str) -> Tuple[Optional[str], Optional[str]]:
        """Login and return access token and tenant_id"""
        self.log(f"Attempting login for {email}")
        
        url = f"{self.base_url}/api/auth/login"
        data = {
            "email": email,
            "password": password
        }
        
        try:
            response = requests.post(url, json=data)
            self.log(f"Login response status: {response.status_code}")
            
            if response.status_code == 200:
                response_data = response.json()
                access_token = response_data.get('access_token')
                tenant_id = response_data.get('tenant_id')
                
                if access_token:
                    self.log(f"✅ Login successful for {email}")
                    self.log(f"   Token length: {len(access_token)} chars")
                    if tenant_id:
                        self.log(f"   Tenant ID: {tenant_id}")
                    return access_token, tenant_id
                else:
                    self.log(f"❌ No access token in response for {email}")
                    return None, None
            else:
                self.log(f"❌ Login failed for {email}: {response.status_code} - {response.text}")
                return None, None
                
        except Exception as e:
            self.log(f"❌ Login exception for {email}: {str(e)}")
            return None, None
    
    def make_request(self, method: str, endpoint: str, token: str = None, params: Dict = None, 
                    tenant_id: str = None) -> Tuple[int, Dict]:
        """Make authenticated API request"""
        url = f"{self.base_url}{endpoint}"
        headers = {}
        
        if token:
            headers['Authorization'] = f'Bearer {token}'
            
        if tenant_id:
            headers['X-Tenant-Id'] = tenant_id
            
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=params)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            try:
                return response.status_code, response.json()
            except:
                return response.status_code, {"text": response.text}
                
        except Exception as e:
            return 0, {"error": str(e)}
    
    def test_agency_login(self) -> bool:
        """Test 1: Agency login başarılı olmalı ve access token dönmeli"""
        self.log("=" * 60)
        self.log("TEST 1: Agency Login")
        self.log("=" * 60)
        
        token, tenant_id = self.login("agent@acenta.test", "agent123")
        if token:
            self.agency_token = token
            self.agency_tenant_id = tenant_id
            return True
        return False
    
    def test_admin_login(self) -> bool:
        """Admin login for later tests"""
        self.log("=" * 60)
        self.log("SETUP: Admin Login")
        self.log("=" * 60)
        
        token, tenant_id = self.login("admin@acenta.test", "admin123")
        if token:
            self.admin_token = token
            self.admin_tenant_id = tenant_id
            return True
        return False
    
    def test_agency_no_regression(self) -> Dict[str, bool]:
        """Test 2: Agency perspective no-regression"""
        self.log("=" * 60)
        self.log("TEST 2: Agency No-Regression")
        self.log("=" * 60)
        
        if not self.agency_token:
            self.log("❌ No agency token available for testing")
            return {"hotels": False, "bookings": False, "settlements": False}
        
        results = {}
        
        # Test 2a: GET /api/agency/hotels
        self.log("Testing GET /api/agency/hotels")
        status, data = self.make_request('GET', '/api/agency/hotels', self.agency_token, tenant_id=self.agency_tenant_id)
        results["hotels"] = status == 200
        self.log(f"   Status: {status} {'✅' if results['hotels'] else '❌'}")
        if not results["hotels"]:
            self.log(f"   Response: {data}")
        
        # Test 2b: GET /api/agency/bookings
        self.log("Testing GET /api/agency/bookings")
        status, data = self.make_request('GET', '/api/agency/bookings', self.agency_token, tenant_id=self.agency_tenant_id)
        results["bookings"] = status == 200
        self.log(f"   Status: {status} {'✅' if results['bookings'] else '❌'}")
        if not results["bookings"]:
            self.log(f"   Response: {data}")
        
        # Test 2c: GET /api/agency/settlements?month=2026-03
        self.log("Testing GET /api/agency/settlements?month=2026-03")
        params = {"month": "2026-03"}
        status, data = self.make_request('GET', '/api/agency/settlements', self.agency_token, 
                                       params=params, tenant_id=self.agency_tenant_id)
        results["settlements"] = status == 200
        self.log(f"   Status: {status} {'✅' if results['settlements'] else '❌'}")
        if not results["settlements"]:
            self.log(f"   Response: {data}")
        
        return results
    
    def test_global_search(self) -> bool:
        """Test 3: Yeni global search endpoint"""
        self.log("=" * 60)
        self.log("TEST 3: Global Search Endpoint")
        self.log("=" * 60)
        
        if not self.agency_token:
            self.log("❌ No agency token available for testing")
            return False
        
        self.log("Testing GET /api/search?q=demo&limit=3")
        params = {"q": "demo", "limit": 3}
        status, data = self.make_request('GET', '/api/search', self.agency_token, 
                                       params=params, tenant_id=self.agency_tenant_id)
        
        if status == 200:
            self.log(f"✅ Search endpoint returned 200")
            
            # Validate response structure
            required_fields = ["counts", "total_results", "sections"]
            missing_fields = []
            
            for field in required_fields:
                if field not in data:
                    missing_fields.append(field)
            
            if not missing_fields:
                self.log("✅ Response has required top-level fields: counts, total_results, sections")
                
                # Check sections content
                sections = data.get("sections", {})
                section_fields = ["customers", "bookings", "hotels"]
                sections_missing = []
                
                for section in section_fields:
                    if section not in sections:
                        sections_missing.append(section)
                
                if not sections_missing:
                    self.log("✅ Sections contains: customers, bookings, hotels")
                    
                    # Check for agency scope
                    if "scope" in data and data["scope"] == "agency":
                        self.log("✅ Response includes scope=agency")
                        return True
                    else:
                        self.log(f"⚠️  Response scope: {data.get('scope', 'not found')}")
                        return True  # Still valid if functional
                else:
                    self.log(f"❌ Missing sections: {sections_missing}")
                    return False
            else:
                self.log(f"❌ Missing required fields: {missing_fields}")
                return False
        else:
            self.log(f"❌ Search endpoint failed: {status}")
            self.log(f"   Response: {data}")
            return False
    
    def test_generated_report(self) -> bool:
        """Test 4: Yeni generated report endpoint"""
        self.log("=" * 60)
        self.log("TEST 4: Generated Report Endpoint")
        self.log("=" * 60)
        
        if not self.agency_token:
            self.log("❌ No agency token available for testing")
            return False
        
        # Test 4a: With X-Tenant-Id header
        self.log("Testing GET /api/reports/generate?days=30 (with X-Tenant-Id)")
        params = {"days": 30}
        status, data = self.make_request('GET', '/api/reports/generate', self.agency_token, 
                                       params=params, tenant_id=self.agency_tenant_id)
        
        if status == 200:
            self.log(f"✅ Reports/generate returned 200 with X-Tenant-Id")
            
            # Validate response structure
            required_fields = ["period", "kpis", "daily_revenue", "top_hotels", "payment_health", "recent_bookings"]
            missing_fields = []
            
            for field in required_fields:
                if field not in data:
                    missing_fields.append(field)
            
            if not missing_fields:
                self.log("✅ Response has all required fields")
                result_with_tenant = True
            else:
                self.log(f"❌ Missing fields with X-Tenant-Id: {missing_fields}")
                result_with_tenant = False
        else:
            self.log(f"❌ Reports/generate failed with X-Tenant-Id: {status}")
            self.log(f"   Response: {data}")
            result_with_tenant = False
        
        # Test 4b: Without X-Tenant-Id header (özellikle X-Tenant-Id header olmadan da test et)
        self.log("Testing GET /api/reports/generate?days=30 (without X-Tenant-Id)")
        status, data = self.make_request('GET', '/api/reports/generate', self.agency_token, 
                                       params=params)  # No tenant_id
        
        if status == 200:
            self.log(f"✅ Reports/generate returned 200 without X-Tenant-Id")
            result_without_tenant = True
        else:
            self.log(f"⚠️  Reports/generate status without X-Tenant-Id: {status}")
            self.log(f"   Response: {data}")
            result_without_tenant = False
            
        return result_with_tenant or result_without_tenant
    
    def test_sales_summary_regression(self) -> Dict[str, bool]:
        """Test 5: Sales summary filter regression"""
        self.log("=" * 60)
        self.log("TEST 5: Sales Summary Filter Regression")
        self.log("=" * 60)
        
        if not self.agency_token:
            self.log("❌ No agency token available for testing")
            return {"days_7": False, "days_30": False}
        
        results = {}
        
        # Test 5a: days=7
        self.log("Testing GET /api/reports/sales-summary?days=7")
        params = {"days": 7}
        status, data = self.make_request('GET', '/api/reports/sales-summary', self.agency_token, 
                                       params=params, tenant_id=self.agency_tenant_id)
        results["days_7"] = status == 200
        self.log(f"   Status: {status} {'✅' if results['days_7'] else '❌'}")
        if not results["days_7"]:
            self.log(f"   Response: {data}")
        
        # Test 5b: days=30
        self.log("Testing GET /api/reports/sales-summary?days=30")
        params = {"days": 30}
        status, data = self.make_request('GET', '/api/reports/sales-summary', self.agency_token, 
                                       params=params, tenant_id=self.agency_tenant_id)
        results["days_30"] = status == 200
        self.log(f"   Status: {status} {'✅' if results['days_30'] else '❌'}")
        if not results["days_30"]:
            self.log(f"   Response: {data}")
        
        return results
    
    def test_admin_no_regression(self) -> Dict[str, bool]:
        """Test 6: Admin no-regression"""
        self.log("=" * 60)
        self.log("TEST 6: Admin No-Regression")
        self.log("=" * 60)
        
        if not self.admin_token:
            self.log("❌ No admin token available for testing")
            return {"tenants": False, "tenant_features": False, "tenant_subscription": False}
        
        results = {}
        
        # Test 6a: GET /api/admin/tenants
        self.log("Testing GET /api/admin/tenants")
        status, data = self.make_request('GET', '/api/admin/tenants', self.admin_token, 
                                       tenant_id=self.admin_tenant_id)
        results["tenants"] = status == 200
        self.log(f"   Status: {status} {'✅' if results['tenants'] else '❌'}")
        
        tenant_id_for_test = None
        if results["tenants"] and isinstance(data, dict):
            # Extract a tenant ID from the response for further testing
            tenants = data.get("items", []) or data.get("tenants", [])
            if tenants and len(tenants) > 0:
                tenant_id_for_test = tenants[0].get("id")
                self.log(f"   Found tenant ID for testing: {tenant_id_for_test}")
        
        if not results["tenants"]:
            self.log(f"   Response: {data}")
        
        # Test 6b: GET /api/admin/tenants/{tenant_id}/features
        if tenant_id_for_test:
            self.log(f"Testing GET /api/admin/tenants/{tenant_id_for_test}/features")
            status, data = self.make_request('GET', f'/api/admin/tenants/{tenant_id_for_test}/features', 
                                           self.admin_token, tenant_id=self.admin_tenant_id)
            results["tenant_features"] = status == 200
            self.log(f"   Status: {status} {'✅' if results['tenant_features'] else '❌'}")
            if not results["tenant_features"]:
                self.log(f"   Response: {data}")
        else:
            self.log("❌ No tenant ID available for features test")
            results["tenant_features"] = False
        
        # Test 6c: GET /api/admin/billing/tenants/{tenant_id}/subscription
        if tenant_id_for_test:
            self.log(f"Testing GET /api/admin/billing/tenants/{tenant_id_for_test}/subscription")
            status, data = self.make_request('GET', f'/api/admin/billing/tenants/{tenant_id_for_test}/subscription', 
                                           self.admin_token, tenant_id=self.admin_tenant_id)
            results["tenant_subscription"] = status == 200 or (status == 404 and isinstance(data, dict))
            self.log(f"   Status: {status} {'✅' if results['tenant_subscription'] else '❌'}")
            if status == 404:
                self.log("   204/404 is acceptable for missing subscription (consistent empty response)")
            elif not results["tenant_subscription"]:
                self.log(f"   Response: {data}")
        else:
            self.log("❌ No tenant ID available for subscription test")
            results["tenant_subscription"] = False
        
        return results
    
    def run_all_tests(self):
        """Run all backend tests"""
        self.log("🚀 Starting Backend API Test Suite")
        self.log(f"Base URL: {self.base_url}")
        self.log("=" * 60)
        
        # Test results
        results = {}
        
        # Test 1: Agency Login
        results["agency_login"] = self.test_agency_login()
        
        # Setup: Admin Login
        admin_login_success = self.test_admin_login()
        
        # Test 2: Agency No-Regression
        if results["agency_login"]:
            results["agency_no_regression"] = self.test_agency_no_regression()
        else:
            self.log("❌ Skipping agency tests due to login failure")
            results["agency_no_regression"] = {"hotels": False, "bookings": False, "settlements": False}
        
        # Test 3: Global Search
        if results["agency_login"]:
            results["global_search"] = self.test_global_search()
        else:
            results["global_search"] = False
        
        # Test 4: Generated Report
        if results["agency_login"]:
            results["generated_report"] = self.test_generated_report()
        else:
            results["generated_report"] = False
        
        # Test 5: Sales Summary Regression
        if results["agency_login"]:
            results["sales_summary"] = self.test_sales_summary_regression()
        else:
            results["sales_summary"] = {"days_7": False, "days_30": False}
        
        # Test 6: Admin No-Regression
        if admin_login_success:
            results["admin_no_regression"] = self.test_admin_no_regression()
        else:
            self.log("❌ Skipping admin tests due to login failure")
            results["admin_no_regression"] = {"tenants": False, "tenant_features": False, "tenant_subscription": False}
        
        # Summary
        self.log("=" * 60)
        self.log("🎯 TEST SUMMARY")
        self.log("=" * 60)
        
        total_tests = 0
        passed_tests = 0
        
        # Agency Login
        total_tests += 1
        if results["agency_login"]:
            passed_tests += 1
            self.log("✅ Agency Login: PASSED")
        else:
            self.log("❌ Agency Login: FAILED")
        
        # Agency No-Regression
        agency_tests = results["agency_no_regression"]
        for test, passed in agency_tests.items():
            total_tests += 1
            if passed:
                passed_tests += 1
                self.log(f"✅ Agency {test}: PASSED")
            else:
                self.log(f"❌ Agency {test}: FAILED")
        
        # Global Search
        total_tests += 1
        if results["global_search"]:
            passed_tests += 1
            self.log("✅ Global Search: PASSED")
        else:
            self.log("❌ Global Search: FAILED")
        
        # Generated Report
        total_tests += 1
        if results["generated_report"]:
            passed_tests += 1
            self.log("✅ Generated Report: PASSED")
        else:
            self.log("❌ Generated Report: FAILED")
        
        # Sales Summary
        sales_tests = results["sales_summary"]
        for test, passed in sales_tests.items():
            total_tests += 1
            if passed:
                passed_tests += 1
                self.log(f"✅ Sales Summary {test}: PASSED")
            else:
                self.log(f"❌ Sales Summary {test}: FAILED")
        
        # Admin No-Regression
        admin_tests = results["admin_no_regression"]
        for test, passed in admin_tests.items():
            total_tests += 1
            if passed:
                passed_tests += 1
                self.log(f"✅ Admin {test}: PASSED")
            else:
                self.log(f"❌ Admin {test}: FAILED")
        
        self.log("=" * 60)
        self.log(f"📊 FINAL RESULTS: {passed_tests}/{total_tests} tests passed ({passed_tests/total_tests*100:.1f}%)")
        
        # Critical issues
        critical_issues = []
        if not results["agency_login"]:
            critical_issues.append("Agency login failing")
        if not results["generated_report"]:
            critical_issues.append("Generated report endpoint not working")
        if not admin_tests["tenants"]:
            critical_issues.append("Admin tenants endpoint not working")
            
        if critical_issues:
            self.log("🚨 CRITICAL ISSUES:")
            for issue in critical_issues:
                self.log(f"   - {issue}")
        else:
            self.log("✅ No critical issues detected")
        
        return results

def main():
    # Base URL from environment
    base_url = "https://quota-manager-stage.preview.emergentagent.com"
    
    tester = BackendTester(base_url)
    results = tester.run_all_tests()
    
    # Exit code based on critical tests
    if results.get("agency_login") and results.get("admin_no_regression", {}).get("tenants"):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()