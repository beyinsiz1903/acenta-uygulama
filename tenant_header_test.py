#!/usr/bin/env python3
"""
Additional validation test with tenant header variations for PR-5A Mobile BFF
"""

import asyncio
import json
import httpx


async def test_with_tenant_header():
    """Test mobile endpoints with X-Tenant-Id header as requested in Turkish review"""
    
    base_url = "https://tenant-audit-preview.preview.emergentagent.com"
    admin_email = "admin@acenta.test"
    admin_password = "admin123"
    
    async with httpx.AsyncClient(timeout=30.0) as session:
        # Login first
        response = await session.post(
            f"{base_url}/api/auth/login",
            json={"email": admin_email, "password": admin_password},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code != 200:
            print(f"❌ Login failed: {response.status_code}")
            return
        
        access_token = response.json().get("access_token")
        if not access_token:
            print("❌ No access token received")
            return
        
        print("✅ Login successful")
        
        # Test mobile endpoints with tenant header
        tenant_id = "9c5c1079-9dea-49bf-82c0-74838b146160"
        
        endpoints_to_test = [
            ("/api/v1/mobile/auth/me", "Mobile Auth Me"),
            ("/api/v1/mobile/dashboard/summary", "Mobile Dashboard"), 
            ("/api/v1/mobile/bookings", "Mobile Bookings List"),
            ("/api/v1/mobile/reports/summary", "Mobile Reports"),
        ]
        
        for endpoint, name in endpoints_to_test:
            # Test with tenant header
            response = await session.get(
                f"{base_url}{endpoint}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "X-Tenant-Id": tenant_id
                }
            )
            
            if response.status_code == 200:
                print(f"✅ {name} with tenant header: OK ({response.status_code})")
            else:
                print(f"❌ {name} with tenant header: FAILED ({response.status_code})")
                
            # Test without tenant header (should still work for backwards compatibility)
            response_no_tenant = await session.get(
                f"{base_url}{endpoint}",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if response_no_tenant.status_code == 200:
                print(f"✅ {name} without tenant header: OK ({response_no_tenant.status_code})")
            else:
                print(f"⚠️  {name} without tenant header: {response_no_tenant.status_code} (may be expected)")


async def main():
    print("🔍 Additional Mobile BFF Tenant Header Testing")
    print("=" * 50)
    await test_with_tenant_header()
    print("=" * 50)
    print("✅ Tenant header testing completed")


if __name__ == "__main__":
    asyncio.run(main())