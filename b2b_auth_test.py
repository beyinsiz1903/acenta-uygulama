#!/usr/bin/env python3
"""Quick test to verify B2B authentication issue and fix."""

import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from app.auth import create_access_token, decode_token


async def test_b2b_auth_issue():
    """Test the B2B authentication issue."""
    
    # Simulate the issue: ObjectId vs string mismatch
    from bson import ObjectId
    
    org_id_objectid = ObjectId()
    org_id_string = str(org_id_objectid)
    
    print(f"ObjectId: {org_id_objectid} (type: {type(org_id_objectid)})")
    print(f"String: {org_id_string} (type: {type(org_id_string)})")
    print(f"Are they equal? {org_id_objectid == org_id_string}")
    
    # Create token with string org_id (as done in fixtures)
    token = create_access_token(
        subject="test@example.com",
        organization_id=org_id_string,
        roles=["agency_admin"]
    )
    
    # Decode token to see what's stored
    payload = decode_token(token)
    print(f"JWT payload org: {payload['org']} (type: {type(payload['org'])})")
    
    # This is the issue: database lookup will fail if user.organization_id is ObjectId
    # but JWT payload.org is string
    print(f"Database lookup would fail: ObjectId({org_id_objectid}) != '{payload['org']}'")
    
    return True


if __name__ == "__main__":
    asyncio.run(test_b2b_auth_issue())