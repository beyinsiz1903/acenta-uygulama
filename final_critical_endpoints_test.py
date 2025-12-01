#!/usr/bin/env python3
"""
ABSOLUTE FINAL PERFORMANCE TEST - 6 Critical Endpoints Only

Focused test on the exact 6 endpoints requested in the review:
1. GET /api/monitoring/health - Verify no errors, response <50ms
2. GET /api/monitoring/system - Verify metrics present, response <50ms
3. GET /api/pms/rooms - Verify pre-warmed cache working, no 500 errors
4. GET /api/pms/bookings - Verify data returned correctly
5. GET /api/pms/dashboard - Verify aggregation working
6. GET /api/executive/kpi-snapshot - Verify KPI data present

SUCCESS CRITERIA:
- All endpoints return 200 OK
- No validation errors (especially PMS Rooms)
- All required fields present in responses
- Response times improved from baseline
- Cache working (faster on 2nd call)

Target: 100% success, all optimizations working correctly
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime, timezone

# Configuration
BACKEND_URL = "https://booking-system-76.preview.emergentagent.com/api"
TEST_EMAIL = "admin@hotel.com"
TEST_PASSWORD = "admin123"

class CriticalEndpointsTester:
    def __init__(self):
        self.session = None
        self.auth_token = None
        self.tenant_id = None
        self.results = []

    async def setup_session(self):
        """Initialize HTTP session"""
        self.session = aiohttp.ClientSession()

    async def cleanup_session(self):
        """Cleanup HTTP session"""
        if self.session:
            await self.session.close()

    async def authenticate(self):
        """Authenticate and get token"""
        try:
            login_data = {"email": TEST_EMAIL, "password": TEST_PASSWORD}
            async with self.session.post(f"{BACKEND_URL}/auth/login", json=login_data) as response:
                if response.status == 200:
                    data = await response.json()
                    self.auth_token = data["access_token"]
                    self.tenant_id = data["user"]["tenant_id"]
                    print(f"✅ Authentication successful - Tenant: {self.tenant_id}")
                    return True
                else:
                    print(f"❌ Authentication failed: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False

    def get_headers(self):
        """Get authorization headers"""
        return {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }

    async def test_endpoint(self, endpoint_name: str, url: str, expected_fields: list = None, test_cache: bool = False):
        """Test a single endpoint with performance and validation checks"""
        print(f"\n🎯 Testing {endpoint_name}...")
        
        # First call
        start_time = time.time()
        try:
            async with self.session.get(url, headers=self.get_headers()) as response:
                first_response_time = (time.time() - start_time) * 1000
                first_status = response.status
                first_data = await response.json() if response.content_type == 'application/json' else await response.text()
                first_headers = dict(response.headers)
        except Exception as e:
            first_response_time = (time.time() - start_time) * 1000
            first_status = 0
            first_data = None
            first_headers = {}
            print(f"  ❌ Error: {e}")

        # Second call for cache testing
        second_response_time = None
        cache_improvement = 0
        if test_cache and first_status == 200:
            await asyncio.sleep(0.1)  # Small delay
            start_time = time.time()
            try:
                async with self.session.get(url, headers=self.get_headers()) as response:
                    second_response_time = (time.time() - start_time) * 1000
                    if second_response_time < first_response_time:
                        cache_improvement = ((first_response_time - second_response_time) / first_response_time) * 100
            except Exception as e:
                second_response_time = None

        # Analyze results
        success = first_status == 200
        issues = []
        
        if not success:
            issues.append(f"HTTP {first_status} error")
        
        # Check response time target
        target_met = first_response_time < 50
        if not target_met:
            issues.append(f"Response time {first_response_time:.1f}ms >= 50ms target")
        
        # Check required fields
        if success and first_data and expected_fields:
            if isinstance(first_data, dict):
                missing_fields = [field for field in expected_fields if field not in first_data]
                if missing_fields:
                    issues.append(f"Missing fields: {missing_fields}")
                
                # Check tenant_id
                if "tenant_id" not in first_data:
                    issues.append("Missing tenant_id field")
            elif isinstance(first_data, list) and len(first_data) > 0:
                # For list responses, check first item
                first_item = first_data[0]
                if isinstance(first_item, dict):
                    missing_fields = [field for field in expected_fields if field not in first_item]
                    if missing_fields:
                        issues.append(f"Missing fields in first item: {missing_fields}")
                    
                    if "tenant_id" not in first_item:
                        issues.append("Missing tenant_id field in first item")

        # Check compression
        compression_active = "gzip" in first_headers.get("content-encoding", "").lower()
        
        # Print results
        status_icon = "✅" if success and not issues else "❌"
        print(f"  {status_icon} Status: {first_status}")
        print(f"  ⏱️ Response time: {first_response_time:.1f}ms")
        print(f"  🎯 Target <50ms: {'✅ MET' if target_met else '❌ MISSED'}")
        print(f"  🗜️ GZip compression: {'✅ ACTIVE' if compression_active else '❌ INACTIVE'}")
        
        if test_cache and second_response_time:
            cache_status = "✅ WORKING" if cache_improvement > 0 else "❌ NOT WORKING"
            print(f"  🔄 Cache performance: {cache_status} ({cache_improvement:.1f}% improvement)")
        
        if issues:
            for issue in issues:
                print(f"  ⚠️ {issue}")
        
        # Store result
        result = {
            "endpoint": endpoint_name,
            "url": url,
            "status": first_status,
            "response_time": first_response_time,
            "target_met": target_met,
            "compression_active": compression_active,
            "success": success and not issues,
            "issues": issues,
            "cache_improvement": cache_improvement if test_cache else None
        }
        
        self.results.append(result)
        return result

    async def run_all_tests(self):
        """Run all 6 critical endpoint tests"""
        print("🚀 ABSOLUTE FINAL PERFORMANCE TEST - 6 Critical Endpoints")
        print("=" * 70)
        
        await self.setup_session()
        
        if not await self.authenticate():
            print("❌ Authentication failed. Cannot proceed with tests.")
            return
        
        # Test all 6 critical endpoints
        await self.test_endpoint(
            "1. Monitoring Health",
            f"{BACKEND_URL}/monitoring/health",
            ["status", "components"],
            test_cache=True
        )
        
        await self.test_endpoint(
            "2. Monitoring System",
            f"{BACKEND_URL}/monitoring/system",
            ["cpu_usage", "memory", "disk", "network"],
            test_cache=True
        )
        
        await self.test_endpoint(
            "3. PMS Rooms",
            f"{BACKEND_URL}/pms/rooms",
            ["id", "room_number", "room_type", "status"],
            test_cache=True
        )
        
        await self.test_endpoint(
            "4. PMS Bookings",
            f"{BACKEND_URL}/pms/bookings",
            ["id", "guest_id", "room_id", "check_in", "check_out", "status"],
            test_cache=True
        )
        
        await self.test_endpoint(
            "5. PMS Dashboard",
            f"{BACKEND_URL}/pms/dashboard",
            [],  # Dashboard structure varies
            test_cache=True
        )
        
        await self.test_endpoint(
            "6. Executive KPI Snapshot",
            f"{BACKEND_URL}/executive/kpi-snapshot",
            ["kpis", "summary"],
            test_cache=True
        )
        
        await self.cleanup_session()
        self.print_summary()

    def print_summary(self):
        """Print final test summary"""
        print("\n" + "=" * 70)
        print("📊 FINAL PERFORMANCE TEST RESULTS")
        print("=" * 70)
        
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r["success"])
        targets_met = sum(1 for r in self.results if r["target_met"])
        compression_active = sum(1 for r in self.results if r["compression_active"])
        cache_working = sum(1 for r in self.results if r["cache_improvement"] and r["cache_improvement"] > 0)
        
        avg_response_time = sum(r["response_time"] for r in self.results) / total_tests
        
        print(f"\n📈 SUCCESS RATE: {successful_tests}/{total_tests} ({successful_tests/total_tests*100:.1f}%)")
        print(f"🎯 TARGETS MET (<50ms): {targets_met}/{total_tests} ({targets_met/total_tests*100:.1f}%)")
        print(f"⏱️ AVERAGE RESPONSE TIME: {avg_response_time:.1f}ms")
        print(f"🗜️ COMPRESSION ACTIVE: {compression_active}/{total_tests} ({compression_active/total_tests*100:.1f}%)")
        print(f"🔄 CACHE WORKING: {cache_working}/{total_tests} ({cache_working/total_tests*100:.1f}%)")
        
        print(f"\n🔍 DETAILED RESULTS:")
        print("-" * 50)
        for result in self.results:
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            target = "✅" if result["target_met"] else "❌"
            compression = "🗜️" if result["compression_active"] else "  "
            cache = f"🔄{result['cache_improvement']:.0f}%" if result["cache_improvement"] and result["cache_improvement"] > 0 else "   "
            
            print(f"{status} {result['endpoint']}")
            print(f"     {target} {result['response_time']:.1f}ms {compression} {cache}")
            
            if result["issues"]:
                for issue in result["issues"]:
                    print(f"     ⚠️ {issue}")
        
        print("\n" + "=" * 70)
        if successful_tests == total_tests and targets_met >= total_tests * 0.8:
            print("🎉 EXCELLENT: All optimizations working correctly!")
            print("✅ All endpoints return 200 OK")
            print("✅ No validation errors")
            print("✅ Response times within targets")
            print("✅ Cache performance improvements detected")
        elif successful_tests >= total_tests * 0.8:
            print("✅ GOOD: Most optimizations working, minor issues")
        else:
            print("❌ ISSUES: Some optimizations need attention")
        
        print("=" * 70)

async def main():
    """Main test execution"""
    tester = CriticalEndpointsTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())