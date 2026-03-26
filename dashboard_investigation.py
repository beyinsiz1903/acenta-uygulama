#!/usr/bin/env python3
"""
Detailed investigation of /dashboard/popular-products 500 error
"""

import requests
import json

BASE_URL = "https://test-stability-core.preview.emergentagent.com/api"

def test_dashboard_endpoints_detailed():
    """Test various dashboard endpoints to identify the scope of issues."""
    
    # First login as admin
    login_data = {"email": "admin@acenta.test", "password": "admin123"}
    login_response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    
    if login_response.status_code != 200:
        print("❌ Login failed")
        return
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test various dashboard/admin endpoints
    endpoints_to_test = [
        "/dashboard/popular-products",
        "/admin/agencies", 
        "/admin/tenants?limit=3",
        "/admin/all-users?limit=3",
        "/reports/reservations-summary",
        "/reports/sales-summary"
    ]
    
    print("🔍 DETAILED ENDPOINT TESTING")
    print("=" * 60)
    
    for endpoint in endpoints_to_test:
        print(f"\nTesting: {endpoint}")
        
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, timeout=10)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, list):
                        print(f"✅ Returns list with {len(data)} items")
                    elif isinstance(data, dict):
                        print(f"✅ Returns dict with keys: {list(data.keys())}")
                    else:
                        print(f"✅ Returns data type: {type(data)}")
                except:
                    print(f"✅ Response length: {len(response.text)} chars")
            elif response.status_code == 500:
                print(f"❌ Server error. Response: {response.text[:200]}...")
            else:
                print(f"⚠️ Status {response.status_code}: {response.text[:100]}...")
                
        except Exception as e:
            print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    test_dashboard_endpoints_detailed()