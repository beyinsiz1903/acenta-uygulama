#!/usr/bin/env python3
"""
Test various booking endpoints to find the right one
"""

import requests


def test_booking_endpoints():
    """Test various booking endpoints"""
    try:
        # Login
        login_data = {"email": "admin@acenta.test", "password": "admin123"}
        response = requests.post("https://ui-consistency-50.preview.emergentagent.com/api/auth/login", json=login_data, timeout=10)
        
        if response.status_code != 200:
            print(f"Login failed: {response.status_code} - {response.text}")
            return
        
        token = response.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test different booking endpoints
        endpoints = [
            "/api/bookings",
            "/api/ops/bookings",
            "/api/b2b/bookings",
            "/api/admin/bookings",
            "/api/ops/b2b/bookings",
        ]
        
        for endpoint in endpoints:
            print(f"\nTesting {endpoint}...")
            full_url = f"https://ui-consistency-50.preview.emergentagent.com{endpoint}"
            response = requests.get(full_url, headers=headers, timeout=10)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    print(f"Success: List with {len(data)} items")
                elif isinstance(data, dict):
                    print(f"Success: Dict with keys: {list(data.keys())}")
                    if 'items' in data:
                        print(f"  Items count: {len(data.get('items', []))}")
            elif response.status_code == 404:
                print("Not Found")
            elif response.status_code == 403:
                print("Forbidden")
            elif response.status_code == 401:
                print("Unauthorized")
            else:
                print(f"Error {response.status_code}: {response.text[:100]}")
                
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    test_booking_endpoints()