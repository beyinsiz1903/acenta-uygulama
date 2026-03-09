#!/usr/bin/env python3
"""
Backend API Validation Test for Turkish Review Request
Validates recent backend fixes for dashboard endpoints and ObjectId serialization
"""

import requests
import json
import sys
from typing import Dict, Any, Optional

class BackendTester:
    def __init__(self):
        self.base_url = "https://syroce-preview-1.preview.emergentagent.com/api"
        self.session = requests.Session()
        self.admin_token = None
        self.agency_token = None
        
    def log(self, message: str):
        print(f"[TEST] {message}")
        
    def test_login(self, email: str, password: str) -> Optional[str]:
        """Test login endpoint and return access token"""
        url = f"{self.base_url}/auth/login"
        payload = {
            "email": email,
            "password": password
        }
        
        try:
            response = self.session.post(url, json=payload)
            self.log(f"POST /auth/login ({email}): Status {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if 'access_token' in data:
                    token = data['access_token']
                    self.log(f"✅ Login successful - Token length: {len(token)} chars")
                    return token
                else:
                    self.log(f"❌ Login failed - Missing access_token in response")
                    return None
            else:
                self.log(f"❌ Login failed - Status: {response.status_code}, Response: {response.text}")
                return None
                
        except Exception as e:
            self.log(f"❌ Login error - Exception: {str(e)}")
            return None
    
    def test_authenticated_endpoint_with_payload(self, endpoint: str, token: str, method: str = "POST", payload: dict = None) -> Dict[str, Any]:
        """Test an authenticated endpoint with JSON payload"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        try:
            if method.upper() == "POST":
                response = self.session.post(url, headers=headers, json=payload)
            else:
                raise ValueError(f"Unsupported method for payload: {method}")
                
            self.log(f"{method} /{endpoint}: Status {response.status_code}")
            
            result = {
                'status_code': response.status_code,
                'success': response.status_code in [200, 201],
                'response_size': len(response.text) if response.text else 0,
                'endpoint': endpoint
            }
            
            # Try to parse JSON
            try:
                result['json'] = response.json()
            except:
                result['json'] = None
                result['text'] = response.text[:500]  # First 500 chars
                
            return result
            
        except Exception as e:
            self.log(f"❌ {method} /{endpoint} error - Exception: {str(e)}")
            return {
                'status_code': 0,
                'success': False,
                'error': str(e),
                'endpoint': endpoint
            }
    
    def test_authenticated_endpoint(self, endpoint: str, token: str, method: str = "GET") -> Dict[str, Any]:
        """Test an authenticated endpoint"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url, headers=headers)
            elif method.upper() == "POST":
                response = self.session.post(url, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            self.log(f"{method} /{endpoint}: Status {response.status_code}")
            
            result = {
                'status_code': response.status_code,
                'success': response.status_code in [200, 201],
                'response_size': len(response.text) if response.text else 0,
                'endpoint': endpoint
            }
            
            # Try to parse JSON
            try:
                result['json'] = response.json()
            except:
                result['json'] = None
                result['text'] = response.text[:500]  # First 500 chars
                
            return result
            
        except Exception as e:
            self.log(f"❌ {method} /{endpoint} error - Exception: {str(e)}")
            return {
                'status_code': 0,
                'success': False,
                'error': str(e),
                'endpoint': endpoint
            }
    
    def run_validation(self):
        """Run complete validation as per Turkish review request"""
        self.log("=== BACKEND VALIDATION STARTING ===")
        self.log("Base URL: https://syroce-preview-1.preview.emergentagent.com/api")
        
        results = {}
        
        # 1. Test admin login
        self.log("\n--- 1. Testing POST /api/auth/login (admin) ---")
        self.admin_token = self.test_login("admin@acenta.test", "admin123")
        results['admin_login'] = {
            'success': self.admin_token is not None,
            'token_length': len(self.admin_token) if self.admin_token else 0
        }
        
        # 2. Test agency login  
        self.log("\n--- 2. Testing POST /api/auth/login (agency) ---")
        self.agency_token = self.test_login("agent@acenta.test", "agent123")
        results['agency_login'] = {
            'success': self.agency_token is not None,
            'token_length': len(self.agency_token) if self.agency_token else 0
        }
        
        if not self.admin_token or not self.agency_token:
            self.log("❌ CRITICAL: Login failed, cannot continue with endpoint tests")
            return results
        
        # 3. Test GET /api/dashboard/popular-products (CRITICAL - was failing before)
        self.log("\n--- 3. Testing GET /api/dashboard/popular-products (ObjectId fix) ---")
        results['popular_products'] = self.test_authenticated_endpoint(
            "dashboard/popular-products", self.agency_token
        )
        
        if results['popular_products']['success']:
            self.log("✅ /dashboard/popular-products: 200 OK - ObjectId serialization FIXED")
        else:
            self.log(f"❌ /dashboard/popular-products: {results['popular_products']['status_code']} - Still broken")
        
        # 4. Test dashboard endpoint set
        self.log("\n--- 4. Testing Dashboard Endpoint Set ---")
        dashboard_endpoints = [
            "dashboard/kpi-stats",
            "dashboard/reservation-widgets", 
            "dashboard/weekly-summary",
            "dashboard/recent-customers"
        ]
        
        results['dashboard_set'] = {}
        for endpoint in dashboard_endpoints:
            result = self.test_authenticated_endpoint(endpoint, self.agency_token)
            results['dashboard_set'][endpoint] = result
            
            if result['success']:
                self.log(f"✅ /{endpoint}: 200 OK")
            else:
                self.log(f"❌ /{endpoint}: {result['status_code']}")
        
        # 5. No-regression tests
        self.log("\n--- 5. Testing No-Regression Endpoints ---")
        
        # Test /api/reports/generate with proper payload
        results['reports_generate'] = self.test_authenticated_endpoint_with_payload(
            "reports/generate", self.agency_token, "POST", {"report_type": "sales", "format": "json"}
        )
        
        # Test /api/search with query parameter
        results['search'] = self.test_authenticated_endpoint(
            "search?q=test", self.agency_token
        )
        
        if results['reports_generate']['success']:
            self.log("✅ /reports/generate: No regression")
        else:
            self.log(f"❌ /reports/generate: {results['reports_generate']['status_code']}")
            
        if results['search']['success']:
            self.log("✅ /search: No regression") 
        else:
            self.log(f"❌ /search: {results['search']['status_code']}")
        
        # Summary
        self.log("\n=== VALIDATION SUMMARY ===")
        
        # Critical tests
        critical_passed = 0
        critical_total = 0
        
        # Login tests
        if results['admin_login']['success'] and results['agency_login']['success']:
            self.log("✅ 1. POST /api/auth/login: PASS (both admin and agency)")
            critical_passed += 1
        else:
            self.log("❌ 1. POST /api/auth/login: FAIL")
        critical_total += 1
        
        # Popular products (the main fix being validated)
        if results['popular_products']['success']:
            self.log("✅ 2. GET /api/dashboard/popular-products: PASS (ObjectId serialization FIXED)")
            critical_passed += 1
        else:
            self.log("❌ 2. GET /api/dashboard/popular-products: FAIL (ObjectId issue still present)")
        critical_total += 1
        
        # Dashboard endpoint set
        dashboard_success_count = sum(1 for r in results['dashboard_set'].values() if r['success'])
        dashboard_total = len(dashboard_endpoints)
        
        if dashboard_success_count == dashboard_total:
            self.log(f"✅ 3. Dashboard endpoint set: PASS ({dashboard_success_count}/{dashboard_total})")
            critical_passed += 1
        else:
            self.log(f"❌ 3. Dashboard endpoint set: PARTIAL ({dashboard_success_count}/{dashboard_total})")
        critical_total += 1
        
        # No-regression
        regression_passed = (results['reports_generate']['success'] and 
                           results['search']['success'])
        if regression_passed:
            self.log("✅ 4. No-regression (/reports/generate, /search): PASS")
            critical_passed += 1
        else:
            self.log("❌ 4. No-regression: FAIL")
        critical_total += 1
        
        self.log(f"\nOVERALL RESULT: {critical_passed}/{critical_total} critical tests passed")
        
        if critical_passed == critical_total:
            self.log("✅ ALL TESTS PASSED - Backend fixes validated successfully")
        else:
            self.log("❌ SOME TESTS FAILED - Backend issues still present")
            
        return results

if __name__ == "__main__":
    tester = BackendTester()
    tester.run_validation()