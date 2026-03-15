#!/usr/bin/env python3
"""
Debug the admin tenants response structure
"""

import requests
import json

# Configuration
BACKEND_URL = "https://frontend-standardize.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "admin123"

def main():
    print("Debugging admin tenants response...")
    
    session = requests.Session()
    
    # Login
    login_response = session.post(
        f"{BACKEND_URL}/auth/login",
        json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }
    )
    
    if login_response.status_code == 200:
        login_data = login_response.json()
        admin_token = login_data.get('access_token')
        session.headers.update({'Authorization': f'Bearer {admin_token}'})
        print("✅ Login successful")
        
        # Get tenants
        tenants_response = session.get(f"{BACKEND_URL}/admin/tenants?limit=5")
        print(f"Response status: {tenants_response.status_code}")
        print(f"Response headers: {dict(tenants_response.headers)}")
        print("Response body:")
        print(json.dumps(tenants_response.json(), indent=2))
        
    else:
        print(f"❌ Login failed: {login_response.status_code}")

if __name__ == "__main__":
    main()