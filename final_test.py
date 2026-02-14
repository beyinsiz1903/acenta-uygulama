#!/usr/bin/env python3
"""
Final comprehensive test - core flow only to avoid rate limits
"""

import asyncio
import tempfile
import time
import httpx

BACKEND_URL = "https://booking-suite-pro.preview.emergentagent.com"
API_BASE = f"{BACKEND_URL}/api"
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "admin123"

async def test_core_flow():
    """Test the main import flow without hitting rate limits"""
    
    print("🚀 Testing Zero Migration Friction Engine - Core Import Flow\n")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # 1. Authentication
        print("1️⃣ Testing Authentication...")
        login_resp = await client.post(f"{API_BASE}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        if login_resp.status_code == 200:
            print("✅ Authentication successful")
            token = login_resp.json().get("access_token")
            headers = {"Authorization": f"Bearer {token}"}
        else:
            print(f"❌ Authentication failed: {login_resp.status_code}")
            return
        
        await asyncio.sleep(1)  # Rate limit protection
        
        # 2. CSV Upload
        print("\n2️⃣ Testing CSV Upload...")
        timestamp = str(int(time.time()))
        csv_content = f"""Otel Adı,Şehir,Ülke,Açıklama,Fiyat,Yıldız
Final Test Hotel {timestamp}_1,İstanbul,TR,Test hotel,1500,5
Final Test Hotel {timestamp}_2,Antalya,TR,Beach hotel,2000,4
Final Test Hotel {timestamp}_3,Bodrum,TR,Marina view,3000,5
Final Test Hotel {timestamp}_4,,TR,Missing city,,3
Final Test Hotel {timestamp}_5,İzmir,TR,Good hotel,abc,4"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            temp_path = f.name
        
        with open(temp_path, 'rb') as f:
            files = {"file": ("final_test.csv", f, "text/csv")}
            upload_resp = await client.post(
                f"{API_BASE}/admin/import/hotels/upload",
                headers=headers,
                files=files
            )
        
        if upload_resp.status_code == 200:
            upload_data = upload_resp.json()
            job_id = upload_data["job_id"]
            print(f"✅ CSV Upload successful - Job ID: {job_id}")
            print(f"   Total rows: {upload_data['total_rows']}")
        else:
            print(f"❌ CSV Upload failed: {upload_resp.status_code}")
            return
            
        await asyncio.sleep(1)  # Rate limit protection
        
        # 3. Validation
        print("\n3️⃣ Testing Validation...")
        mapping = {
            "0": "name", "1": "city", "2": "country",
            "3": "description", "4": "price", "5": "stars"
        }
        
        validate_resp = await client.post(
            f"{API_BASE}/admin/import/hotels/validate",
            headers=headers,
            json={"job_id": job_id, "mapping": mapping}
        )
        
        if validate_resp.status_code == 200:
            validate_data = validate_resp.json()
            print(f"✅ Validation successful")
            print(f"   Valid rows: {validate_data['valid_count']}")
            print(f"   Error rows: {validate_data['error_count']}")
        else:
            print(f"❌ Validation failed: {validate_resp.status_code}")
            return
            
        await asyncio.sleep(1)  # Rate limit protection
        
        # 4. Execution
        print("\n4️⃣ Testing Execution...")
        execute_resp = await client.post(
            f"{API_BASE}/admin/import/hotels/execute",
            headers=headers,
            json={"job_id": job_id}
        )
        
        if execute_resp.status_code == 200:
            execute_data = execute_resp.json()
            print(f"✅ Execution started: {execute_data['status']}")
        else:
            print(f"❌ Execution failed: {execute_resp.status_code}")
            print(f"   Response: {execute_resp.json()}")
            return
            
        await asyncio.sleep(1)  # Rate limit protection
        
        # 5. Check job status after execution
        print("\n5️⃣ Checking job status...")
        await asyncio.sleep(3)  # Wait for background processing
        
        job_resp = await client.get(f"{API_BASE}/admin/import/jobs/{job_id}", headers=headers)
        if job_resp.status_code == 200:
            job_data = job_resp.json()
            print(f"✅ Job status: {job_data['status']}")
            print(f"   Success count: {job_data.get('success_count', 0)}")
            print(f"   Error count: {job_data.get('error_count', 0)}")
            if job_data.get('errors'):
                print(f"   Errors found: {len(job_data['errors'])}")
        else:
            print(f"❌ Job status check failed: {job_resp.status_code}")
            
        await asyncio.sleep(1)  # Rate limit protection
        
        # 6. Test Export Template
        print("\n6️⃣ Testing Template Export...")
        template_resp = await client.get(f"{API_BASE}/admin/import/export-template", headers=headers)
        if template_resp.status_code == 200:
            content_type = template_resp.headers.get("content-type", "")
            if "spreadsheet" in content_type:
                print("✅ Template export successful")
            else:
                print(f"❌ Template export wrong content type: {content_type}")
        else:
            print(f"❌ Template export failed: {template_resp.status_code}")
            
        await asyncio.sleep(1)  # Rate limit protection
        
        # 7. Test Google Sheets (MOCKED)
        print("\n7️⃣ Testing Google Sheets (MOCKED)...")
        sheet_resp = await client.post(
            f"{API_BASE}/admin/import/sheet/connect",
            headers=headers,
            json={
                "sheet_id": f"test_{timestamp}",
                "worksheet_name": "Sheet1",
                "sync_enabled": False
            }
        )
        
        if sheet_resp.status_code == 200:
            print("✅ Google Sheets connection (MOCKED) successful")
        else:
            print(f"❌ Google Sheets connection failed: {sheet_resp.status_code}")
        
        print("\n🎉 Core import flow testing complete!")

if __name__ == "__main__":
    asyncio.run(test_core_flow())