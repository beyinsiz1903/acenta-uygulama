#!/usr/bin/env python3
"""
Debug specific failing tests to see response structure
"""

import asyncio
import tempfile
import httpx

BACKEND_URL = "https://unified-control-4.preview.emergentagent.com"
API_BASE = f"{BACKEND_URL}/api"
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "admin123"

async def debug_tests():
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Login
        login_resp = await client.post(f"{API_BASE}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        if login_resp.status_code != 200:
            print(f"Login failed: {login_resp.status_code}")
            return
        
        token = login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test sheet connect to see response structure
        print("=== Testing Sheet Connect ===")
        sheet_resp = await client.post(
            f"{API_BASE}/admin/import/sheet/connect",
            headers=headers,
            json={
                "sheet_id": "debug_test",
                "worksheet_name": "Sheet1",
                "sync_enabled": False
            }
        )
        print(f"Status: {sheet_resp.status_code}")
        print(f"Response: {sheet_resp.json()}")
        print()
        
        # Get list of jobs to see if any exist
        print("=== Testing Job List ===")
        jobs_resp = await client.get(f"{API_BASE}/admin/import/jobs", headers=headers)
        print(f"Status: {jobs_resp.status_code}")
        jobs_data = jobs_resp.json()
        print(f"Jobs count: {len(jobs_data)}")
        if jobs_data:
            print(f"First job structure: {jobs_data[0]}")
            
            # Test job detail
            job_id = jobs_data[0].get("id") or jobs_data[0].get("_id")
            if job_id:
                print(f"\n=== Testing Job Detail for {job_id} ===")
                job_detail_resp = await client.get(f"{API_BASE}/admin/import/jobs/{job_id}", headers=headers)
                print(f"Status: {job_detail_resp.status_code}")
                print(f"Response: {job_detail_resp.json()}")

if __name__ == "__main__":
    asyncio.run(debug_tests())