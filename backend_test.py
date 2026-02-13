#!/usr/bin/env python3
"""Backend Test Script for Bug Fixes"""

import requests
import json
import os
from datetime import datetime

# Get backend URL from frontend .env
BACKEND_URL = "https://tour-reserve.preview.emergentagent.com"
API_PREFIX = "/api"

class BackendTester:
    def __init__(self):
        self.results = {
            "olaylar_404_fix": {"status": "unknown", "details": []},
            "voucher_auth_fix": {"status": "unknown", "details": []}, 
            "general_health": {"status": "unknown", "details": []}
        }
        
    def test_olaylar_incidents_404_fix(self):
        """Test that GET /api/admin/ops/incidents returns 401 (not 404) without auth"""
        print("\n=== Testing Olaylar (Incidents) 404 Fix ===")
        
        try:
            # Test without auth token - should get 401, not 404
            url = f"{BACKEND_URL}{API_PREFIX}/admin/ops/incidents"
            print(f"Testing: GET {url}")
            
            response = requests.get(url, timeout=30)
            print(f"Response Status: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            
            if response.status_code == 401:
                self.results["olaylar_404_fix"]["status"] = "✅ FIXED"
                self.results["olaylar_404_fix"]["details"].append(
                    "✅ FIXED: GET /api/admin/ops/incidents returns 401 (not 404) without auth. Endpoint exists and requires authentication as expected."
                )
                print("✅ SUCCESS: Returns 401 without auth (endpoint exists)")
            elif response.status_code == 404:
                self.results["olaylar_404_fix"]["status"] = "❌ FAILED"
                self.results["olaylar_404_fix"]["details"].append(
                    "❌ FAILED: Still returning 404 - the get_current_org dependency issue may not be fully resolved."
                )
                print("❌ FAILED: Still returns 404")
            else:
                self.results["olaylar_404_fix"]["status"] = "⚠️ UNEXPECTED"
                self.results["olaylar_404_fix"]["details"].append(
                    f"⚠️ UNEXPECTED: Got {response.status_code} instead of expected 401. Response: {response.text[:200]}"
                )
                print(f"⚠️ UNEXPECTED: Got {response.status_code}")
                
        except Exception as e:
            self.results["olaylar_404_fix"]["status"] = "❌ ERROR"
            self.results["olaylar_404_fix"]["details"].append(f"❌ ERROR: {str(e)}")
            print(f"❌ ERROR: {e}")
    
    def test_voucher_auth_fix(self):
        """Test that GET /api/reservations/{id}/voucher requires auth (returns 401 without token)"""
        print("\n=== Testing Voucher Auth Fix ===")
        
        try:
            # Test with a dummy reservation ID
            test_id = "test_reservation_id"
            url = f"{BACKEND_URL}{API_PREFIX}/reservations/{test_id}/voucher"
            print(f"Testing: GET {url}")
            
            response = requests.get(url, timeout=30)
            print(f"Response Status: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            
            if response.status_code == 401:
                self.results["voucher_auth_fix"]["status"] = "✅ WORKING"
                self.results["voucher_auth_fix"]["details"].append(
                    "✅ WORKING: GET /api/reservations/{id}/voucher returns 401 without auth. Backend endpoint exists and requires authentication as expected."
                )
                print("✅ SUCCESS: Voucher endpoint requires auth (returns 401)")
            elif response.status_code == 404:
                self.results["voucher_auth_fix"]["status"] = "⚠️ INFO"
                self.results["voucher_auth_fix"]["details"].append(
                    "⚠️ INFO: Returns 404 - endpoint may not exist at this URL or routing issue."
                )
                print("⚠️ INFO: Returns 404 - endpoint may not exist")
            else:
                self.results["voucher_auth_fix"]["status"] = "⚠️ UNEXPECTED"
                self.results["voucher_auth_fix"]["details"].append(
                    f"⚠️ UNEXPECTED: Got {response.status_code}. Response: {response.text[:200]}"
                )
                print(f"⚠️ UNEXPECTED: Got {response.status_code}")
                
        except Exception as e:
            self.results["voucher_auth_fix"]["status"] = "❌ ERROR"
            self.results["voucher_auth_fix"]["details"].append(f"❌ ERROR: {str(e)}")
            print(f"❌ ERROR: {e}")
    
    def test_general_health(self):
        """Test that backend server is running and responding"""
        print("\n=== Testing General Backend Health ===")
        
        try:
            # Test root endpoint
            print(f"Testing: GET {BACKEND_URL}/")
            response = requests.get(f"{BACKEND_URL}/", timeout=30)
            print(f"Root Status: {response.status_code}")
            
            if response.status_code == 200:
                self.results["general_health"]["details"].append("✅ Root endpoint responding correctly")
            
            # Test health endpoint  
            print(f"Testing: GET {BACKEND_URL}/health")
            health_response = requests.get(f"{BACKEND_URL}/health", timeout=30)
            print(f"Health Status: {health_response.status_code}")
            
            if health_response.status_code == 200:
                self.results["general_health"]["details"].append("✅ Health endpoint responding correctly")
                
            # Test API prefix
            print(f"Testing: GET {BACKEND_URL}{API_PREFIX}/")
            api_response = requests.get(f"{BACKEND_URL}{API_PREFIX}/", timeout=30)
            print(f"API Status: {api_response.status_code}")
            
            # Overall health assessment
            if response.status_code == 200 and health_response.status_code == 200:
                self.results["general_health"]["status"] = "✅ HEALTHY"
                self.results["general_health"]["details"].append(
                    f"✅ HEALTHY: Backend server running properly on {BACKEND_URL}"
                )
                print("✅ SUCCESS: Backend is healthy and responding")
            else:
                self.results["general_health"]["status"] = "⚠️ PARTIAL"
                self.results["general_health"]["details"].append(
                    "⚠️ PARTIAL: Some endpoints not responding as expected"
                )
                print("⚠️ PARTIAL: Some issues detected")
                
        except Exception as e:
            self.results["general_health"]["status"] = "❌ ERROR"
            self.results["general_health"]["details"].append(f"❌ ERROR: {str(e)}")
            print(f"❌ ERROR: {e}")
    
    def run_all_tests(self):
        """Run all bug fix tests"""
        print(f"Backend Bug Fix Testing")
        print(f"Target URL: {BACKEND_URL}")
        print(f"Time: {datetime.now().isoformat()}")
        print("="*60)
        
        # Run individual tests
        self.test_olaylar_incidents_404_fix()
        self.test_voucher_auth_fix() 
        self.test_general_health()
        
        # Print summary
        print("\n" + "="*60)
        print("TEST RESULTS SUMMARY")
        print("="*60)
        
        for test_name, result in self.results.items():
            print(f"{test_name}: {result['status']}")
            for detail in result['details']:
                print(f"  {detail}")
        
        return self.results

if __name__ == "__main__":
    tester = BackendTester()
    results = tester.run_all_tests()