#!/usr/bin/env python3
"""
Test the double API prefix issue
"""

import requests


def test_double_api_prefix():
    """Test if the issue is double API prefix"""
    try:
        # Login
        login_data = {"email": "admin@acenta.test", "password": "admin123"}
        response = requests.post("https://ui-consistency-50.preview.emergentagent.com/api/auth/login", json=login_data, timeout=10)
        
        if response.status_code != 200:
            print(f"Login failed: {response.status_code} - {response.text}")
            return
        
        token = response.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test double API prefix
        endpoints = [
            "/api/ops/bookings",
            "/api/api/ops/bookings",
            "/ops/bookings",
        ]
        
        for endpoint in endpoints:
            print(f"\nTesting {endpoint}...")
            full_url = f"https://ui-consistency-50.preview.emergentagent.com{endpoint}"
            response = requests.get(full_url, headers=headers, timeout=10)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Success: {data}")
            elif response.status_code != 404:
                print(f"Error: {response.text}")
                
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    test_double_api_prefix()