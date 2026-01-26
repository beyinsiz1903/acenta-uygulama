#!/usr/bin/env python3
"""
Test ops/bookings endpoint directly
"""

import requests


def test_ops_bookings():
    """Test ops/bookings endpoint with authentication"""
    try:
        # Login
        login_data = {"email": "admin@acenta.test", "password": "admin123"}
        response = requests.post("https://agentisplus.preview.emergentagent.com/api/auth/login", json=login_data, timeout=10)
        
        if response.status_code != 200:
            print(f"Login failed: {response.status_code} - {response.text}")
            return
        
        token = response.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test different ops endpoints
        endpoints = [
            "/api/ops/bookings",
            "/api/ops/bookings?page_size=5",
            "/api/ops/bookings?limit=5",
        ]
        
        for endpoint in endpoints:
            print(f"\nTesting {endpoint}...")
            full_url = f"https://agentisplus.preview.emergentagent.com{endpoint}"
            response = requests.get(full_url, headers=headers, timeout=10)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    print(f"Response: List with {len(data)} items")
                    for i, item in enumerate(data[:2]):  # Show first 2 items
                        booking_id = item.get('booking_id', 'No booking_id')
                        print(f"  {i+1}. {booking_id}")
                elif isinstance(data, dict):
                    print(f"Response: Dict with keys: {list(data.keys())}")
                    if 'items' in data:
                        items = data['items']
                        print(f"  Items: {len(items)}")
                        for i, item in enumerate(items[:2]):
                            booking_id = item.get('booking_id', 'No booking_id')
                            print(f"    {i+1}. {booking_id}")
                else:
                    print(f"Response: {data}")
            else:
                print(f"Error: {response.text}")
                
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    test_ops_bookings()