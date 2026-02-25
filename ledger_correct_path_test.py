#!/usr/bin/env python3
"""
Ledger Reversal Net Zero Correct Path Test

Testing the correct path /api/api/ops/finance/_test/posting
"""

import asyncio
import httpx
import json
import time
from typing import Dict, Any


class LedgerReversalCorrectPathTest:
    def __init__(self):
        self.backend_url = "https://redis-cache-upgrade.preview.emergentagent.com"
        self.admin_token = None
        
    async def get_admin_token(self) -> str:
        """Get admin authentication token"""
        if self.admin_token:
            return self.admin_token
            
        login_url = f"{self.backend_url}/api/auth/login"
        login_data = {
            "email": "admin@acenta.test",
            "password": "admin123"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(login_url, json=login_data)
                if response.status_code == 200:
                    data = response.json()
                    self.admin_token = data.get("access_token")
                    return self.admin_token
                else:
                    print(f"❌ Login failed: {response.text}")
                    return None
            except Exception as e:
                print(f"❌ Login error: {e}")
                return None

    async def test_correct_path_smoke(self):
        """Test the correct path with smoke data"""
        print("🔍 TESTING CORRECT PATH: /api/api/ops/finance/_test/posting")
        print("=" * 70)
        
        token = await self.get_admin_token()
        if not token:
            return {"error": "Failed to get admin token"}
            
        # Correct URL with double API prefix
        url = f"{self.backend_url}/api/api/ops/finance/_test/posting"
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test payload as specified in review request
        payload = {
            "source_type": "booking",
            "source_id": "TEST_SMOKE",
            "event": "BOOKING_CONFIRMED",
            "agency_account_id": "AG_TEST",
            "platform_account_id": "PL_TEST",
            "amount": 100.0
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                print(f"📡 POST {url}")
                print(f"📋 Payload: {json.dumps(payload, indent=2)}")
                
                response = await client.post(url, headers=headers, json=payload)
                
                print(f"📊 Status Code: {response.status_code}")
                print(f"📄 Response Headers: {dict(response.headers)}")
                
                try:
                    response_data = response.json()
                    print(f"📦 Response Body: {json.dumps(response_data, indent=2)}")
                except:
                    print(f"📦 Response Text: {response.text}")
                
                return {
                    "status_code": response.status_code,
                    "response": response.text,
                    "headers": dict(response.headers)
                }
                
            except Exception as e:
                print(f"❌ Request error: {e}")
                return {"error": str(e)}

    async def test_with_test_payload(self):
        """Test with the exact payload from test_ledger_reversal_net_zero.py"""
        print("\n🔍 TESTING WITH EXACT TEST PAYLOAD")
        print("=" * 70)
        
        token = await self.get_admin_token()
        if not token:
            return {"error": "Failed to get admin token"}
            
        # Correct URL with double API prefix
        url = f"{self.backend_url}/api/api/ops/finance/_test/posting"
        headers = {"Authorization": f"Bearer {token}"}
        
        # Exact payload from the test file
        source_id = f"TEST_BKG_{int(time.time())}"
        payload = {
            "source_type": "booking",
            "source_id": source_id,
            "event": "BOOKING_CONFIRMED",
            "agency_account_id": "AGENCY_TEST",
            "platform_account_id": "PLATFORM_TEST",
            "amount": 100.0
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                print(f"📡 POST {url}")
                print(f"📋 Payload: {json.dumps(payload, indent=2)}")
                
                response = await client.post(url, headers=headers, json=payload)
                
                print(f"📊 Status Code: {response.status_code}")
                
                try:
                    response_data = response.json()
                    print(f"📦 Response Body: {json.dumps(response_data, indent=2)}")
                    
                    if response.status_code == 200:
                        print(f"\n✅ SUCCESS! Endpoint is working correctly")
                        print(f"   - posting_id: {response_data.get('posting_id')}")
                        print(f"   - organization_id: {response_data.get('organization_id')}")
                        print(f"   - event: {response_data.get('event')}")
                        print(f"   - lines_count: {response_data.get('lines_count')}")
                        
                        return {
                            "status_code": response.status_code,
                            "response_data": response_data,
                            "source_id": source_id
                        }
                    else:
                        print(f"❌ Unexpected status code: {response.status_code}")
                        return {
                            "status_code": response.status_code,
                            "response": response.text
                        }
                        
                except Exception as json_error:
                    print(f"📦 Response Text: {response.text}")
                    print(f"❌ JSON parse error: {json_error}")
                    return {
                        "status_code": response.status_code,
                        "response": response.text
                    }
                
            except Exception as e:
                print(f"❌ Request error: {e}")
                return {"error": str(e)}

    async def test_refund_approved_event(self, source_id: str):
        """Test REFUND_APPROVED event with the same source_id"""
        print(f"\n🔍 TESTING REFUND_APPROVED EVENT (source_id: {source_id})")
        print("=" * 70)
        
        token = await self.get_admin_token()
        if not token:
            return {"error": "Failed to get admin token"}
            
        url = f"{self.backend_url}/api/api/ops/finance/_test/posting"
        headers = {"Authorization": f"Bearer {token}"}
        
        payload = {
            "source_type": "booking",
            "source_id": source_id,
            "event": "REFUND_APPROVED",
            "agency_account_id": "AGENCY_TEST",
            "platform_account_id": "PLATFORM_TEST",
            "amount": 100.0
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                print(f"📡 POST {url}")
                print(f"📋 Payload: {json.dumps(payload, indent=2)}")
                
                response = await client.post(url, headers=headers, json=payload)
                
                print(f"📊 Status Code: {response.status_code}")
                
                try:
                    response_data = response.json()
                    print(f"📦 Response Body: {json.dumps(response_data, indent=2)}")
                    
                    if response.status_code == 200:
                        print(f"✅ REFUND_APPROVED event successful!")
                        return {
                            "status_code": response.status_code,
                            "response_data": response_data
                        }
                    else:
                        print(f"❌ Unexpected status code: {response.status_code}")
                        return {
                            "status_code": response.status_code,
                            "response": response.text
                        }
                        
                except Exception as json_error:
                    print(f"📦 Response Text: {response.text}")
                    return {
                        "status_code": response.status_code,
                        "response": response.text
                    }
                
            except Exception as e:
                print(f"❌ Request error: {e}")
                return {"error": str(e)}

    async def run_complete_test(self):
        """Run complete test sequence"""
        print("🎯 LEDGER REVERSAL NET ZERO - CORRECT PATH TEST")
        print("=" * 80)
        
        # Step 1: Test smoke payload
        result1 = await self.test_correct_path_smoke()
        
        # Step 2: Test with exact test payload
        result2 = await self.test_with_test_payload()
        
        # Step 3: If successful, test REFUND_APPROVED
        result3 = None
        if result2.get("status_code") == 200:
            source_id = result2.get("source_id")
            if source_id:
                result3 = await self.test_refund_approved_event(source_id)
        
        # Summary
        print("\n" + "=" * 80)
        print("🎯 TEST RESULTS SUMMARY")
        print("=" * 80)
        
        print(f"\n1️⃣ Smoke test result: {result1.get('status_code', 'ERROR')}")
        print(f"2️⃣ Exact test payload result: {result2.get('status_code', 'ERROR')}")
        if result3:
            print(f"3️⃣ REFUND_APPROVED test result: {result3.get('status_code', 'ERROR')}")
        
        # Conclusion
        if result2.get("status_code") == 200:
            print(f"\n✅ CONCLUSION: ENDPOINT IS WORKING!")
            print(f"   - Correct URL: /api/api/ops/finance/_test/posting (double API prefix)")
            print(f"   - The test file needs to be updated to use the correct path")
            print(f"   - Original test was using: /api/ops/finance/_test/posting (single API prefix)")
            print(f"   - This explains the 404 error in the test")
            
            if result3 and result3.get("status_code") == 200:
                print(f"   - Both BOOKING_CONFIRMED and REFUND_APPROVED events work correctly")
        else:
            print(f"\n❌ CONCLUSION: ENDPOINT STILL NOT WORKING")
            print(f"   - Even with correct path, getting {result2.get('status_code', 'ERROR')}")
            print(f"   - May be authentication, role, or other dependency issue")


async def main():
    """Main test execution"""
    tester = LedgerReversalCorrectPathTest()
    await tester.run_complete_test()


if __name__ == "__main__":
    asyncio.run(main())