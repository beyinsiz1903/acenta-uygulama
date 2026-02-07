#!/usr/bin/env python3
"""
Debug validation issues
"""

import asyncio
import tempfile
import httpx

BACKEND_URL = "https://unified-control-4.preview.emergentagent.com"
API_BASE = f"{BACKEND_URL}/api"
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "admin123"

# Use different hotel names to avoid duplicates
TEST_CSV_CONTENT = """Otel Adı,Şehir,Ülke,Açıklama,Fiyat,Yıldız
Unique Hotel 1,İstanbul,TR,Test hotel,1500,5
Unique Hotel 2,Antalya,TR,Beach hotel,2000,4
Unique Hotel 3,Bodrum,TR,Marina view,3000,5
Unique Hotel 4,,TR,Missing city,,3
Unique Hotel 5,İzmir,TR,Good hotel,abc,4"""

async def debug_validation():
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Login
        login_resp = await client.post(f"{API_BASE}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        if login_resp.status_code != 200:
            print(f"Login failed: {login_resp.status_code}")
            return
        
        token = login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Upload CSV
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(TEST_CSV_CONTENT)
            temp_path = f.name
        
        with open(temp_path, 'rb') as f:
            files = {"file": ("debug_test.csv", f, "text/csv")}
            upload_resp = await client.post(
                f"{API_BASE}/admin/import/hotels/upload",
                headers=headers,
                files=files
            )
        
        print(f"Upload Status: {upload_resp.status_code}")
        upload_data = upload_resp.json()
        print(f"Upload Response: {upload_data}")
        
        if upload_resp.status_code != 200:
            return
            
        job_id = upload_data["job_id"]
        
        # Test validation
        mapping = {
            "0": "name",
            "1": "city", 
            "2": "country",
            "3": "description",
            "4": "price",
            "5": "stars"
        }
        
        validate_resp = await client.post(
            f"{API_BASE}/admin/import/hotels/validate",
            headers=headers,
            json={
                "job_id": job_id,
                "mapping": mapping
            }
        )
        
        print(f"\nValidation Status: {validate_resp.status_code}")
        validate_data = validate_resp.json()
        print(f"Validation Response: {validate_data}")
        
        # Check job detail with errors
        await asyncio.sleep(1)
        job_detail_resp = await client.get(f"{API_BASE}/admin/import/jobs/{job_id}", headers=headers)
        print(f"\nJob Detail Status: {job_detail_resp.status_code}")
        print(f"Job Detail: {job_detail_resp.json()}")

if __name__ == "__main__":
    asyncio.run(debug_validation())