#!/usr/bin/env python3
"""
Check admin user roles and test with correct role requirements
"""

import requests
import json


def check_admin_roles():
    """Check admin user roles"""
    try:
        # Login
        login_data = {"email": "admin@acenta.test", "password": "admin123"}
        response = requests.post("https://ui-bug-fixes-13.preview.emergentagent.com/api/auth/login", json=login_data, timeout=10)
        
        if response.status_code != 200:
            print(f"Login failed: {response.status_code} - {response.text}")
            return
        
        token = response.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Check user info
        print("Checking user info...")
        response = requests.get("https://ui-bug-fixes-13.preview.emergentagent.com/api/auth/me", headers=headers, timeout=10)
        if response.status_code == 200:
            user_data = response.json()
            print(f"User roles: {user_data.get('roles')}")
            print(f"User organization: {user_data.get('organization_id')}")
        else:
            print(f"Failed to get user info: {response.status_code}")
        
        # Test ops endpoint with different parameters
        print("\nTesting ops/bookings with different parameters...")
        
        test_params = [
            "",
            "?limit=10",
            "?status=CONFIRMED",
            "?limit=5&status=CONFIRMED",
        ]
        
        for params in test_params:
            url = f"https://ui-bug-fixes-13.preview.emergentagent.com/api/ops/bookings{params}"
            print(f"\nTesting: {url}")
            response = requests.get(url, headers=headers, timeout=10)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Success: {json.dumps(data, indent=2)[:200]}...")
            else:
                print(f"Error: {response.text}")
                
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    check_admin_roles()