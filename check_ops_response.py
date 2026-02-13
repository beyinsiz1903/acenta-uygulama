#!/usr/bin/env python3
"""
Check the actual structure of the ops/bookings API response
"""

import requests
import json


def check_ops_bookings_response():
    """Check the structure of ops/bookings API response"""
    try:
        # Login
        login_data = {"email": "admin@acenta.test", "password": "admin123"}
        response = requests.post("https://test-data-populator.preview.emergentagent.com/api/auth/login", json=login_data, timeout=10)
        
        if response.status_code != 200:
            print(f"Login failed: {response.status_code} - {response.text}")
            return
        
        token = response.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get bookings
        response = requests.get("https://test-data-populator.preview.emergentagent.com/api/api/ops/bookings", headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response structure: {json.dumps(data, indent=2)}")
        else:
            print(f"Error: {response.status_code} - {response.text}")
                
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    check_ops_bookings_response()