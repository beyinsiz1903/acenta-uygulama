#!/usr/bin/env python3
"""
Debug JWT token and organization context
"""

import base64
import json
import requests


def decode_jwt_payload(token):
    """Decode JWT payload without verification (for debugging)"""
    try:
        # JWT has 3 parts separated by dots
        parts = token.split('.')
        if len(parts) != 3:
            return None
        
        # Decode the payload (second part)
        payload = parts[1]
        # Add padding if needed
        payload += '=' * (4 - len(payload) % 4)
        decoded = base64.b64decode(payload)
        return json.loads(decoded)
    except Exception as e:
        print(f"Error decoding JWT: {e}")
        return None


def test_auth_debug():
    """Test authentication with detailed debugging"""
    try:
        # Login
        login_data = {"email": "admin@acenta.test", "password": "admin123"}
        response = requests.post("https://enterprise-ops-8.preview.emergentagent.com/api/auth/login", json=login_data, timeout=10)
        
        print(f"Login status: {response.status_code}")
        if response.status_code != 200:
            print(f"Login failed: {response.text}")
            return
        
        login_response = response.json()
        token = login_response.get("access_token")
        print(f"Token received: {token[:50]}...")
        
        # Decode JWT payload
        payload = decode_jwt_payload(token)
        if payload:
            print(f"JWT payload: {json.dumps(payload, indent=2)}")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test a simple endpoint first
        print("\nTesting /api/auth/me...")
        response = requests.get("https://enterprise-ops-8.preview.emergentagent.com/api/auth/me", headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            me_data = response.json()
            print(f"User data: {json.dumps(me_data, indent=2)}")
        else:
            print(f"Error: {response.text}")
        
        # Test customers API with full URL
        print("\nTesting full customers API URL...")
        full_url = "https://enterprise-ops-8.preview.emergentagent.com/api/crm/customers"
        print(f"URL: {full_url}")
        response = requests.get(full_url, headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        if response.status_code != 200:
            print(f"Error response: {response.text}")
        else:
            data = response.json()
            print(f"Success - got {len(data.get('items', []))} customers")
            
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    test_auth_debug()