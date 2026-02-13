#!/usr/bin/env python3
"""
Debug test for Partner Graph endpoints
"""

import requests
import json

BASE_URL = "https://tour-reserve.preview.emergentagent.com"

def test_partner_graph_debug():
    # Login
    r = requests.post(f"{BASE_URL}/api/auth/login", 
                     json={"email": "muratsutay@hotmail.com", "password": "murat1903"})
    assert r.status_code == 200, f"Login failed: {r.text}"
    
    data = r.json()
    token = data["access_token"]
    org_id = data["user"]["organization_id"]
    
    print(f"✅ Logged in as: {data['user']['email']}")
    print(f"✅ Org ID: {org_id}")
    
    # Use existing tenant IDs
    seller_tenant_id = "6981c6ff113e0acfa72d24ec"
    buyer_tenant_id = "6981c6ff113e0acfa72d24ef"
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test 1: Try partner graph invite without X-Tenant-Id
    print("\n1️⃣ Testing partner graph invite without X-Tenant-Id...")
    r = requests.post(f"{BASE_URL}/api/partner-graph/invite", 
                     json={"buyer_tenant_id": buyer_tenant_id}, 
                     headers=headers)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text}")
    
    # Test 2: Try partner graph invite with X-Tenant-Id
    print("\n2️⃣ Testing partner graph invite with X-Tenant-Id...")
    headers_with_tenant = {**headers, "X-Tenant-Id": seller_tenant_id}
    r = requests.post(f"{BASE_URL}/api/partner-graph/invite", 
                     json={"buyer_tenant_id": buyer_tenant_id}, 
                     headers=headers_with_tenant)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text}")
    
    # Test 3: Try inventory shares list
    print("\n3️⃣ Testing inventory shares list...")
    r = requests.get(f"{BASE_URL}/api/inventory-shares", 
                    headers=headers_with_tenant)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text}")

if __name__ == "__main__":
    test_partner_graph_debug()