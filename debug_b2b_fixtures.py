#!/usr/bin/env python3
"""Debug script to understand B2B test fixture issues."""

import asyncio
import sys
import os
sys.path.append('/app/backend')

from app.db import connect_mongo, get_db
from bson import ObjectId
from datetime import datetime, timezone

async def debug_b2b_fixtures():
    await connect_mongo()
    db = await get_db()
    
    # Find the default org
    org = await db.organizations.find_one({"slug": "default"})
    if not org:
        print("❌ No default org found")
        return
    
    print(f"✅ Found org: {org['_id']} (type: {type(org['_id'])})")
    
    # Check for B2B test users
    provider_user = await db.users.find_one({"email": "provider-b2b@test.local"})
    seller_user = await db.users.find_one({"email": "seller-b2b@test.local"})
    
    if provider_user:
        print(f"✅ Found provider user: org_id={provider_user.get('organization_id')} (type: {type(provider_user.get('organization_id'))})")
    else:
        print("❌ No provider user found")
    
    if seller_user:
        print(f"✅ Found seller user: org_id={seller_user.get('organization_id')} (type: {type(seller_user.get('organization_id'))})")
    else:
        print("❌ No seller user found")
    
    # Check for B2B tenants
    provider_tenant = await db.tenants.find_one({"slug": "b2b-provider-tenant"})
    seller_tenant = await db.tenants.find_one({"slug": "b2b-seller-tenant"})
    
    if provider_tenant:
        print(f"✅ Found provider tenant: {provider_tenant['_id']}, org_id={provider_tenant.get('organization_id')}")
    else:
        print("❌ No provider tenant found")
    
    if seller_tenant:
        print(f"✅ Found seller tenant: {seller_tenant['_id']}, org_id={seller_tenant.get('organization_id')}")
    else:
        print("❌ No seller tenant found")
    
    # Check memberships
    if provider_user and provider_tenant:
        membership = await db.memberships.find_one({
            "user_id": str(provider_user["_id"]),
            "tenant_id": str(provider_tenant["_id"])
        })
        if membership:
            print(f"✅ Found provider membership: status={membership.get('status')}")
        else:
            print("❌ No provider membership found")
    
    if seller_user and seller_tenant:
        membership = await db.memberships.find_one({
            "user_id": str(seller_user["_id"]),
            "tenant_id": str(seller_tenant["_id"])
        })
        if membership:
            print(f"✅ Found seller membership: status={membership.get('status')}")
        else:
            print("❌ No seller membership found")
    
    # Check partner relationships
    if provider_tenant and seller_tenant:
        rel = await db.partner_relationships.find_one({
            "seller_tenant_id": str(provider_tenant["_id"]),
            "buyer_tenant_id": str(seller_tenant["_id"]),
            "status": "active"
        })
        if rel:
            print(f"✅ Found active partner relationship")
        else:
            print("❌ No active partner relationship found")
            # Check for any relationships
            all_rels = await db.partner_relationships.find({}).to_list(length=10)
            print(f"Found {len(all_rels)} total partner relationships:")
            for r in all_rels:
                print(f"  - seller: {r.get('seller_tenant_id')}, buyer: {r.get('buyer_tenant_id')}, status: {r.get('status')}")

if __name__ == "__main__":
    asyncio.run(debug_b2b_fixtures())