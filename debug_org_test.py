#!/usr/bin/env python3
"""
Quick test to check user organization and debug API issues
"""

import asyncio
import sys
import requests

# Add backend to path for imports
sys.path.append('/app/backend')
from app.db import get_db


async def check_user_org():
    """Check what organization the admin user belongs to"""
    db = await get_db()
    
    # Find admin user
    admin_user = await db.users.find_one({"email": "admin@acenta.test"})
    if admin_user:
        print(f"Admin user organization_id: {admin_user.get('organization_id')}")
        print(f"Admin user id: {admin_user.get('id') or admin_user.get('_id')}")
    else:
        print("Admin user not found")
    
    # Check all organizations
    orgs = await db.organizations.find({}).to_list(length=10)
    print(f"\nFound {len(orgs)} organizations:")
    for org in orgs:
        org_id = org.get('id') or org.get('_id')
        print(f"  - {org_id}: {org.get('name', 'No name')}")
    
    # Check customers in different orgs
    customers_by_org = {}
    async for customer in db.customers.find({}):
        org_id = customer.get('organization_id')
        if org_id not in customers_by_org:
            customers_by_org[org_id] = []
        customers_by_org[org_id].append(customer.get('id') or customer.get('name'))
    
    print(f"\nCustomers by organization:")
    for org_id, customers in customers_by_org.items():
        print(f"  {org_id}: {len(customers)} customers - {customers[:3]}...")


def test_api_with_debug():
    """Test API with debug info"""
    try:
        # Login
        login_data = {"email": "admin@acenta.test", "password": "admin123"}
        response = requests.post("https://risk-aware-b2b.preview.emergentagent.com/api/auth/login", json=login_data, timeout=10)
        
        if response.status_code != 200:
            print(f"Login failed: {response.status_code} - {response.text}")
            return
        
        token = response.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test customers API with debug
        print("\nTesting customers API...")
        response = requests.get("https://risk-aware-b2b.preview.emergentagent.com/api/crm/customers", headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {data}")
        else:
            print(f"Error: {response.text}")
        
        # Test with search
        print("\nTesting customers API with search=seed...")
        response = requests.get("https://risk-aware-b2b.preview.emergentagent.com/api/crm/customers?search=seed", headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {data}")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"API test error: {e}")


async def main():
    await check_user_org()
    test_api_with_debug()


if __name__ == "__main__":
    asyncio.run(main())