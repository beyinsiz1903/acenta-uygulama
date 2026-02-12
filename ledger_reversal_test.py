#!/usr/bin/env python3
"""
Ledger Reversal Net Zero Legacy Test Investigation

This test investigates the 404 issue with /api/ops/finance/_test/posting endpoint
as reported in the review request.
"""

import asyncio
import httpx
import json
import os
from typing import Dict, Any


class LedgerReversalTestInvestigator:
    def __init__(self):
        # Get backend URL from frontend env
        self.backend_url = "https://conversational-ai-5.preview.emergentagent.com"
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
                print(f"🔐 Admin login: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    self.admin_token = data.get("access_token")
                    print(f"✅ Admin token obtained: {self.admin_token[:20]}...")
                    return self.admin_token
                else:
                    print(f"❌ Login failed: {response.text}")
                    return None
                    
            except Exception as e:
                print(f"❌ Login error: {e}")
                return None

    async def test_smoke_post_direct(self) -> Dict[str, Any]:
        """Step 1: Direct smoke POST to /api/ops/finance/_test/posting"""
        print("\n" + "="*60)
        print("STEP 1: Direct smoke POST to /api/ops/finance/_test/posting")
        print("="*60)
        
        token = await self.get_admin_token()
        if not token:
            return {"error": "Failed to get admin token"}
            
        url = f"{self.backend_url}/api/ops/finance/_test/posting"
        headers = {"Authorization": f"Bearer {token}"}
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

    async def test_with_admin_token_from_test(self) -> Dict[str, Any]:
        """Step 2: Test with admin token like the test does"""
        print("\n" + "="*60)
        print("STEP 2: Test with admin token (same as test_ledger_reversal_net_zero.py)")
        print("="*60)
        
        token = await self.get_admin_token()
        if not token:
            return {"error": "Failed to get admin token"}
            
        # Same payload as in the test
        url = f"{self.backend_url}/api/ops/finance/_test/posting"
        headers = {"Authorization": f"Bearer {token}"}
        
        import time
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
                print(f"📄 Response Headers: {dict(response.headers)}")
                
                try:
                    response_data = response.json()
                    print(f"📦 Response Body: {json.dumps(response_data, indent=2)}")
                except:
                    print(f"📦 Response Text: {response.text}")
                
                return {
                    "status_code": response.status_code,
                    "response": response.text,
                    "headers": dict(response.headers),
                    "source_id": source_id
                }
                
            except Exception as e:
                print(f"❌ Request error: {e}")
                return {"error": str(e)}

    async def test_alternative_paths(self) -> Dict[str, Any]:
        """Step 3: Test alternative URL paths to identify correct endpoint"""
        print("\n" + "="*60)
        print("STEP 3: Testing alternative URL paths")
        print("="*60)
        
        token = await self.get_admin_token()
        if not token:
            return {"error": "Failed to get admin token"}
            
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "source_type": "booking",
            "source_id": "TEST_PATH_CHECK",
            "event": "BOOKING_CONFIRMED",
            "agency_account_id": "AG_TEST",
            "platform_account_id": "PL_TEST",
            "amount": 100.0
        }
        
        # Test different possible paths
        test_paths = [
            "/api/ops/finance/_test/posting",  # Expected path
            "/api/api/ops/finance/_test/posting",  # Double prefix
            "/ops/finance/_test/posting",  # No API prefix
            "/api/ops-finance/_test/posting",  # Hyphenated
        ]
        
        results = {}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for path in test_paths:
                url = f"{self.backend_url}{path}"
                try:
                    print(f"\n🔍 Testing: {url}")
                    response = await client.post(url, headers=headers, json=payload)
                    
                    print(f"   📊 Status: {response.status_code}")
                    if response.status_code != 404:
                        try:
                            response_data = response.json()
                            print(f"   📦 Response: {json.dumps(response_data, indent=6)}")
                        except:
                            print(f"   📦 Response: {response.text}")
                    
                    results[path] = {
                        "status_code": response.status_code,
                        "response": response.text[:200] if response.text else ""
                    }
                    
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                    results[path] = {"error": str(e)}
        
        return results

    async def check_server_routes(self) -> Dict[str, Any]:
        """Step 4: Check available routes and server status"""
        print("\n" + "="*60)
        print("STEP 4: Checking server routes and status")
        print("="*60)
        
        results = {}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Check root endpoint
            try:
                response = await client.get(f"{self.backend_url}/")
                print(f"🏠 Root endpoint: {response.status_code}")
                if response.status_code == 200:
                    print(f"   📦 {response.json()}")
                results["root"] = {"status_code": response.status_code, "response": response.text}
            except Exception as e:
                print(f"❌ Root endpoint error: {e}")
                results["root"] = {"error": str(e)}
            
            # Check health endpoint
            try:
                response = await client.get(f"{self.backend_url}/health")
                print(f"🏥 Health endpoint: {response.status_code}")
                if response.status_code == 200:
                    print(f"   📦 {response.json()}")
                results["health"] = {"status_code": response.status_code, "response": response.text}
            except Exception as e:
                print(f"❌ Health endpoint error: {e}")
                results["health"] = {"error": str(e)}
            
            # Check OpenAPI docs
            try:
                response = await client.get(f"{self.backend_url}/api/openapi.json")
                print(f"📚 OpenAPI docs: {response.status_code}")
                results["openapi"] = {"status_code": response.status_code}
                
                if response.status_code == 200:
                    openapi_data = response.json()
                    # Look for ops/finance paths
                    paths = openapi_data.get("paths", {})
                    finance_paths = [path for path in paths.keys() if "finance" in path]
                    print(f"   🔍 Finance-related paths found: {len(finance_paths)}")
                    for path in finance_paths[:5]:  # Show first 5
                        print(f"      - {path}")
                    results["finance_paths"] = finance_paths
                    
            except Exception as e:
                print(f"❌ OpenAPI docs error: {e}")
                results["openapi"] = {"error": str(e)}
        
        return results

    async def run_investigation(self):
        """Run complete investigation"""
        print("🔍 LEDGER REVERSAL NET ZERO ENDPOINT INVESTIGATION")
        print("=" * 80)
        
        # Step 1: Direct smoke test
        result1 = await self.test_smoke_post_direct()
        
        # Step 2: Test with admin token like the test
        result2 = await self.test_with_admin_token_from_test()
        
        # Step 3: Test alternative paths
        result3 = await self.test_alternative_paths()
        
        # Step 4: Check server routes
        result4 = await self.check_server_routes()
        
        # Summary
        print("\n" + "="*80)
        print("🎯 INVESTIGATION SUMMARY")
        print("="*80)
        
        print(f"\n1️⃣ Direct smoke POST result: {result1.get('status_code', 'ERROR')}")
        print(f"2️⃣ Admin token test result: {result2.get('status_code', 'ERROR')}")
        
        print(f"\n3️⃣ Alternative paths results:")
        for path, result in result3.items():
            status = result.get('status_code', 'ERROR')
            print(f"   {path}: {status}")
        
        print(f"\n4️⃣ Server status:")
        print(f"   Root: {result4.get('root', {}).get('status_code', 'ERROR')}")
        print(f"   Health: {result4.get('health', {}).get('status_code', 'ERROR')}")
        print(f"   OpenAPI: {result4.get('openapi', {}).get('status_code', 'ERROR')}")
        
        # Find working endpoint
        working_endpoints = []
        for path, result in result3.items():
            if result.get('status_code') == 200:
                working_endpoints.append(path)
        
        if working_endpoints:
            print(f"\n✅ WORKING ENDPOINTS FOUND:")
            for endpoint in working_endpoints:
                print(f"   - {endpoint}")
        else:
            print(f"\n❌ NO WORKING ENDPOINTS FOUND")
            print(f"   All tested paths returned 404 or errors")
            
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        if result4.get('openapi', {}).get('status_code') == 200:
            finance_paths = result4.get('finance_paths', [])
            if finance_paths:
                print(f"   - Check OpenAPI docs for correct finance endpoints")
                print(f"   - Found {len(finance_paths)} finance-related paths")
            else:
                print(f"   - No finance paths found in OpenAPI - router may not be included")
        
        if all(r.get('status_code') == 404 for r in [result1, result2]):
            print(f"   - Endpoint may not be available in this environment")
            print(f"   - Check if ops_finance_router is properly included in server.py")
            print(f"   - Verify API_PREFIX configuration")


async def main():
    """Main test execution"""
    investigator = LedgerReversalTestInvestigator()
    await investigator.run_investigation()


if __name__ == "__main__":
    asyncio.run(main())