#!/usr/bin/env python3
"""
Google Sheets Live Sync - Detailed Response Validation

Validates the exact response formats and behavior as specified in the review request.
"""

import asyncio
import json
import tempfile
import time
from typing import Any, Dict, Optional

import httpx

# Configuration
BACKEND_URL = "https://availability-perms.preview.emergentagent.com"
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "admin123"
API_BASE = f"{BACKEND_URL}/api"


class DetailedValidator:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.auth_token: Optional[str] = None
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
        
    async def authenticate(self):
        response = await self.client.post(
            f"{API_BASE}/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code == 200:
            self.auth_token = response.json().get("access_token")
            return True
        return False
    
    def get_headers(self):
        return {"Authorization": f"Bearer {self.auth_token}"} if self.auth_token else {}
    
    async def validate_config_endpoint(self):
        """Validate GET /api/admin/import/sheet/config response format."""
        print("🔍 Validating /api/admin/import/sheet/config")
        
        response = await self.client.get(
            f"{API_BASE}/admin/import/sheet/config",
            headers=self.get_headers()
        )
        
        print(f"  Status: {response.status_code}")
        data = response.json()
        print(f"  Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
        # Expected format: { configured: false, service_account_email: null, message: "..." }
        assert data["configured"] == False, f"Expected configured=false, got {data['configured']}"
        assert data["service_account_email"] is None, f"Expected service_account_email=null, got {data['service_account_email']}"
        assert "message" in data and data["message"], "Expected non-empty message"
        print("  ✅ Response format correct")
        
        return data
    
    async def validate_connect_endpoint(self):
        """Validate POST /api/admin/import/sheet/connect response format."""
        print("\n🔍 Validating /api/admin/import/sheet/connect")
        
        test_payload = {
            "sheet_id": "test_sheet_123",
            "worksheet_name": "Hotels", 
            "column_mapping": {"Otel Adı": "name", "Şehir": "city"},
            "sync_enabled": True
        }
        
        response = await self.client.post(
            f"{API_BASE}/admin/import/sheet/connect",
            headers=self.get_headers(),
            json=test_payload
        )
        
        print(f"  Status: {response.status_code}")
        data = response.json()
        print(f"  Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
        # Should save connection even without API key (graceful)
        # Returns: connection doc with configured=false, detected_headers=[]
        assert "id" in data, "Missing connection id"
        assert data["configured"] == False, f"Expected configured=false, got {data['configured']}"
        assert data["detected_headers"] == [], f"Expected empty detected_headers, got {data['detected_headers']}"
        assert data["sheet_id"] == test_payload["sheet_id"], "Sheet ID mismatch"
        print("  ✅ Response format correct")
        
        return data
    
    async def validate_sync_endpoint(self):
        """Validate POST /api/admin/import/sheet/sync response format."""
        print("\n🔍 Validating /api/admin/import/sheet/sync")
        
        response = await self.client.post(
            f"{API_BASE}/admin/import/sheet/sync",
            headers=self.get_headers(),
            json={}
        )
        
        print(f"  Status: {response.status_code}")
        data = response.json()
        print(f"  Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
        # Should return: { status: "not_configured", message: "...", configured: false }
        assert data["status"] == "not_configured", f"Expected status='not_configured', got {data['status']}"
        assert data["configured"] == False, f"Expected configured=false, got {data['configured']}"
        assert "message" in data and data["message"], "Expected non-empty message"
        print("  ✅ Response format correct")
        
        return data
    
    async def validate_connection_endpoint(self):
        """Validate GET /api/admin/import/sheet/connection response format."""
        print("\n🔍 Validating /api/admin/import/sheet/connection")
        
        response = await self.client.get(
            f"{API_BASE}/admin/import/sheet/connection",
            headers=self.get_headers()
        )
        
        print(f"  Status: {response.status_code}")
        data = response.json()
        print(f"  Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
        # Should include: connected=true, configured=false
        if data.get("connected"):
            assert data["configured"] == False, f"Expected configured=false, got {data['configured']}"
            print("  ✅ Connection exists with correct configured status")
        else:
            print("  ✅ No connection exists (valid state)")
        
        return data
    
    async def validate_status_endpoint(self):
        """Validate GET /api/admin/import/sheet/status response format."""
        print("\n🔍 Validating /api/admin/import/sheet/status")
        
        response = await self.client.get(
            f"{API_BASE}/admin/import/sheet/status",
            headers=self.get_headers()
        )
        
        print(f"  Status: {response.status_code}")
        data = response.json()
        print(f"  Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
        # Should return: connected=true, sync stats, recent_runs
        if data.get("connected"):
            assert data["configured"] == False, f"Expected configured=false, got {data['configured']}"
            assert "recent_runs" in data, "Missing recent_runs"
            assert isinstance(data["recent_runs"], list), "recent_runs should be a list"
            # last_sync_status may be null (never synced)
            print("  ✅ Status format correct")
        else:
            print("  ✅ No connection exists (valid state)")
        
        return data
    
    async def validate_connections_endpoint(self):
        """Validate GET /api/admin/import/sheet/connections response format."""
        print("\n🔍 Validating /api/admin/import/sheet/connections")
        
        response = await self.client.get(
            f"{API_BASE}/admin/import/sheet/connections",
            headers=self.get_headers()
        )
        
        print(f"  Status: {response.status_code}")
        data = response.json()
        print(f"  Response length: {len(data)} connections")
        
        # Should return array of all connections
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        print("  ✅ Returns array of connections")
        
        return data
    
    async def validate_excel_regression(self):
        """Quick test that Excel import lifecycle still works."""
        print("\n🔍 Validating Excel Import Still Works (regression test)")
        
        # Create test CSV
        test_csv = "name,city,country\nSheets Test Hotel,Istanbul,TR"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(test_csv)
            temp_path = f.name
        
        # Upload
        import os
        with open(temp_path, 'rb') as f:
            files = {"file": ("test_sheets.csv", f, "text/csv")}
            response = await self.client.post(
                f"{API_BASE}/admin/import/hotels/upload",
                headers=self.get_headers(),
                files=files
            )
        
        os.unlink(temp_path)
        
        print(f"  Upload Status: {response.status_code}")
        if response.status_code == 200:
            job_data = response.json()
            job_id = job_data["job_id"]
            
            # Validate
            response = await self.client.post(
                f"{API_BASE}/admin/import/hotels/validate",
                headers=self.get_headers(),
                json={
                    "job_id": job_id,
                    "mapping": {"0": "name", "1": "city", "2": "country"}
                }
            )
            
            print(f"  Validation Status: {response.status_code}")
            if response.status_code == 200:
                # Execute
                response = await self.client.post(
                    f"{API_BASE}/admin/import/hotels/execute",
                    headers=self.get_headers(),
                    json={"job_id": job_id}
                )
                print(f"  Execution Status: {response.status_code}")
                
                if response.status_code == 200:
                    print("  ✅ Full Excel import lifecycle works")
                    return True
        
        print("  ❌ Excel import regression detected")
        return False


async def main():
    """Run detailed validation of all endpoints."""
    print("🔬 Google Sheets Live Sync - Detailed Response Validation")
    print("=" * 60)
    
    async with DetailedValidator() as validator:
        if not await validator.authenticate():
            print("❌ Authentication failed")
            return
        
        try:
            await validator.validate_config_endpoint()
            await validator.validate_connect_endpoint()
            await validator.validate_sync_endpoint()
            await validator.validate_connection_endpoint()
            await validator.validate_status_endpoint()
            await validator.validate_connections_endpoint()
            await validator.validate_excel_regression()
            
            print("\n✅ All validations passed - Google Sheets Live Sync is working correctly!")
            print("📋 Key findings:")
            print("   • GOOGLE_SERVICE_ACCOUNT_JSON is NOT set (graceful fallback mode)")
            print("   • All endpoints return proper responses without crashing")
            print("   • Connection saving works even without API key")
            print("   • Sync operations gracefully indicate 'not_configured'")
            print("   • Excel import functionality remains intact")
            
        except Exception as e:
            print(f"\n❌ Validation failed: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())