#!/usr/bin/env python3
"""Debug script to understand B2B authentication issues."""

import asyncio
import sys
import os
sys.path.append('/app/backend')

from app.db import connect_mongo, get_db
from app.auth import create_access_token, decode_token, get_current_user
from fastapi.security import HTTPAuthorizationCredentials

async def debug_auth():
    await connect_mongo()
    db = await get_db()
    
    # Find the default org
    org = await db.organizations.find_one({"slug": "default"})
    if not org:
        print("❌ No default org found")
        return
    
    print(f"✅ Found org: {org['_id']} (type: {type(org['_id'])})")
    
    # Find users with organization_id matching the org
    users = await db.users.find({"organization_id": str(org["_id"])}).to_list(length=10)
    print(f"✅ Found {len(users)} users with organization_id as string")
    
    for user in users:
        print(f"  - {user['email']}: org_id={user['organization_id']} (type: {type(user['organization_id'])})")
    
    # Test token creation and decoding
    if users:
        test_user = users[0]
        token = create_access_token(
            subject=test_user["email"],
            organization_id=str(org["_id"]),
            roles=test_user.get("roles", [])
        )
        print(f"✅ Created token for {test_user['email']}")
        
        # Decode token
        payload = decode_token(token)
        print(f"✅ Token payload: sub={payload.get('sub')}, org={payload.get('org')} (type: {type(payload.get('org'))})")
        
        # Test user lookup
        lookup_user = await db.users.find_one({
            "email": payload.get("sub"), 
            "organization_id": payload.get("org")
        })
        if lookup_user:
            print(f"✅ User lookup successful: {lookup_user['email']}")
        else:
            print(f"❌ User lookup failed for email={payload.get('sub')}, org_id={payload.get('org')}")
            
            # Try alternative lookups
            by_email = await db.users.find_one({"email": payload.get("sub")})
            if by_email:
                print(f"  - Found by email only: org_id={by_email.get('organization_id')} (type: {type(by_email.get('organization_id'))})")
            
            by_org = await db.users.find({"organization_id": payload.get("org")}).to_list(length=5)
            print(f"  - Found {len(by_org)} users with matching org_id")

if __name__ == "__main__":
    asyncio.run(debug_auth())