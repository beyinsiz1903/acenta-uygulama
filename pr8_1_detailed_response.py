#!/usr/bin/env python3
"""
PR#8.1 Detailed Response Structure Verification
Show detailed field examples to confirm proper serialization
"""

import requests
import json

BASE_URL = "https://availability-perms.preview.emergentagent.com"

def login_admin():
    """Login as admin user and return token"""
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
    )
    assert r.status_code == 200, f"Admin login failed: {r.text}"
    data = r.json()
    return data["access_token"]

def show_detailed_response_structure():
    """Show detailed response structure with field examples"""
    print("PR#8.1 DETAILED RESPONSE STRUCTURE VERIFICATION")
    print("=" * 60)
    
    admin_token = login_admin()
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Test cust_seed_linked
    r = requests.get(
        f"{BASE_URL}/api/crm/customers/cust_seed_linked",
        headers=admin_headers,
    )
    
    if r.status_code == 200:
        data = r.json()
        
        print("\n📋 RESPONSE STRUCTURE FOR cust_seed_linked:")
        print(f"Status Code: {r.status_code}")
        print(f"Content-Type: {r.headers.get('content-type', 'N/A')}")
        
        print("\n📋 TOP-LEVEL FIELDS:")
        for key, value in data.items():
            print(f"  {key}: {type(value).__name__} (length: {len(value) if isinstance(value, (list, dict, str)) else 'N/A'})")
        
        print("\n📋 CUSTOMER FIELD DETAILS:")
        customer = data.get("customer", {})
        for key, value in customer.items():
            print(f"  customer.{key}: {type(value).__name__} = {repr(value)}")
        
        print("\n📋 RECENT_BOOKINGS FIELD DETAILS:")
        recent_bookings = data.get("recent_bookings", [])
        print(f"  Count: {len(recent_bookings)}")
        if recent_bookings:
            booking = recent_bookings[0]
            print(f"  Sample booking fields:")
            for key, value in booking.items():
                print(f"    {key}: {type(value).__name__} = {repr(value)}")
        
        print("\n📋 OPEN_DEALS FIELD DETAILS:")
        open_deals = data.get("open_deals", [])
        print(f"  Count: {len(open_deals)}")
        if open_deals:
            deal = open_deals[0]
            print(f"  Sample deal fields:")
            for key, value in deal.items():
                print(f"    {key}: {type(value).__name__} = {repr(value)}")
        
        print("\n📋 OPEN_TASKS FIELD DETAILS:")
        open_tasks = data.get("open_tasks", [])
        print(f"  Count: {len(open_tasks)}")
        if open_tasks:
            task = open_tasks[0]
            print(f"  Sample task fields:")
            for key, value in task.items():
                print(f"    {key}: {type(value).__name__} = {repr(value)}")
        
        print("\n📋 FULL JSON RESPONSE (formatted):")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
    else:
        print(f"❌ Request failed: {r.status_code} - {r.text}")

if __name__ == "__main__":
    show_detailed_response_structure()