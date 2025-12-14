#!/usr/bin/env python3
"""
REDIS CACHE AND CONNECTION POOL TESTING
Testing Redis cache functionality and MongoDB connection pool optimization
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime

# Configuration
BACKEND_URL = "https://canli-problem.preview.emergentagent.com/api"
TEST_EMAIL = "admin@hotel.com"
TEST_PASSWORD = "admin123"

class RedisCacheConnectionTester:
    def __init__(self):
        self.session = None
        self.auth_token = None
        self.test_results = []

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
            login_data = {
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            }
            
            async with self.session.post(f"{BACKEND_URL}/auth/login", json=login_data) as response:
                if response.status == 200:
                    data = await response.json()
                    self.auth_token = data["access_token"]
                    print(f"✅ Authentication successful")
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

    async def measure_response_time(self, url: str, method: str = "GET", data: dict = None) -> tuple:
        """Measure response time for an endpoint"""
        start_time = time.time()
        try:
            if method == "GET":
                async with self.session.get(url, headers=self.get_headers()) as response:
                    response_data = await response.json() if response.content_type == 'application/json' else await response.text()
                    end_time = time.time()
                    response_time = (end_time - start_time) * 1000
                    return response.status, response_data, response_time
            elif method == "POST":
                async with self.session.post(url, json=data, headers=self.get_headers()) as response:
                    response_data = await response.json() if response.content_type == 'application/json' else await response.text()
                    end_time = time.time()
                    response_time = (end_time - start_time) * 1000
                    return response.status, response_data, response_time
        except Exception as e:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            return 500, {"error": str(e)}, response_time

    async def test_redis_cache_functionality(self):
        """Test Redis cache by making repeated requests"""
        print("\n🗄️ Testing Redis Cache Functionality...")
        
        # Test endpoints that should be cached
        cache_test_endpoints = [
            "/pms/rooms",
            "/pms/guests", 
            "/pms/bookings?limit=10"
        ]
        
        for endpoint in cache_test_endpoints:
            print(f"\n  Testing cache for {endpoint}:")
            url = f"{BACKEND_URL}{endpoint}"
            
            # Make 3 requests to test caching
            response_times = []
            for i in range(3):
                status, data, response_time = await self.measure_response_time(url)
                response_times.append(response_time)
                print(f"    Request {i+1}: {response_time:.1f}ms (HTTP {status})")
                
                # Small delay between requests
                await asyncio.sleep(0.1)
            
            # Analyze cache performance
            if len(response_times) >= 2:
                first_request = response_times[0]
                subsequent_avg = sum(response_times[1:]) / len(response_times[1:])
                
                if subsequent_avg < first_request * 0.8:  # 20% improvement indicates caching
                    print(f"    ✅ Cache working: First: {first_request:.1f}ms, Avg subsequent: {subsequent_avg:.1f}ms")
                    cache_working = True
                else:
                    print(f"    ⚠️ No cache benefit: First: {first_request:.1f}ms, Avg subsequent: {subsequent_avg:.1f}ms")
                    cache_working = False
                
                self.test_results.append({
                    "endpoint": f"Cache Test: {endpoint}",
                    "first_request_ms": first_request,
                    "subsequent_avg_ms": subsequent_avg,
                    "cache_working": cache_working,
                    "improvement_pct": ((first_request - subsequent_avg) / first_request * 100) if first_request > 0 else 0
                })

    async def test_connection_pool_stress(self):
        """Test connection pool under concurrent load"""
        print("\n🔗 Testing MongoDB Connection Pool Under Load...")
        
        # Create multiple concurrent requests to test connection pool
        concurrent_requests = 20
        endpoint = "/pms/rooms"
        url = f"{BACKEND_URL}{endpoint}"
        
        print(f"  Making {concurrent_requests} concurrent requests to test connection pool...")
        
        async def make_request(request_id):
            status, data, response_time = await self.measure_response_time(url)
            return {
                "request_id": request_id,
                "status": status,
                "response_time": response_time
            }
        
        # Execute concurrent requests
        start_time = time.time()
        tasks = [make_request(i) for i in range(concurrent_requests)]
        results = await asyncio.gather(*tasks)
        total_time = (time.time() - start_time) * 1000
        
        # Analyze results
        successful_requests = [r for r in results if r["status"] == 200]
        failed_requests = [r for r in results if r["status"] != 200]
        
        if successful_requests:
            response_times = [r["response_time"] for r in successful_requests]
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            min_response_time = min(response_times)
            
            print(f"  ✅ Connection Pool Test Results:")
            print(f"    • Successful requests: {len(successful_requests)}/{concurrent_requests}")
            print(f"    • Failed requests: {len(failed_requests)}")
            print(f"    • Total time: {total_time:.1f}ms")
            print(f"    • Average response time: {avg_response_time:.1f}ms")
            print(f"    • Min response time: {min_response_time:.1f}ms")
            print(f"    • Max response time: {max_response_time:.1f}ms")
            
            # Check if connection pool is handling load well
            if len(successful_requests) == concurrent_requests and avg_response_time < 1000:
                print(f"    ✅ Connection pool handling load well")
                pool_performance = "excellent"
            elif len(successful_requests) >= concurrent_requests * 0.9 and avg_response_time < 2000:
                print(f"    ✅ Connection pool handling load adequately")
                pool_performance = "good"
            else:
                print(f"    ⚠️ Connection pool may be under stress")
                pool_performance = "stressed"
            
            self.test_results.append({
                "test": "Connection Pool Stress Test",
                "concurrent_requests": concurrent_requests,
                "successful_requests": len(successful_requests),
                "failed_requests": len(failed_requests),
                "avg_response_time_ms": avg_response_time,
                "max_response_time_ms": max_response_time,
                "min_response_time_ms": min_response_time,
                "total_time_ms": total_time,
                "performance": pool_performance
            })
        else:
            print(f"  ❌ All requests failed - connection pool may be misconfigured")

    async def test_database_connection_info(self):
        """Test database connection information"""
        print("\n🗄️ Testing Database Connection Information...")
        
        url = f"{BACKEND_URL}/monitoring/database"
        status, data, response_time = await self.measure_response_time(url)
        
        if status == 200 and isinstance(data, dict):
            print(f"  ✅ Database monitoring endpoint working: {response_time:.1f}ms")
            
            # Check connection information
            if "connections" in data:
                conn_info = data["connections"]
                if "connections" in conn_info:
                    current_conn = conn_info["connections"].get("current", 0)
                    available_conn = conn_info["connections"].get("available", 0)
                    total_created = conn_info["connections"].get("total_created", 0)
                    
                    print(f"    • Current connections: {current_conn}")
                    print(f"    • Available connections: {available_conn}")
                    print(f"    • Total created: {total_created}")
                    
                    # Check if connection pool is optimized
                    total_pool = current_conn + available_conn
                    if total_pool >= 200:  # Expected maxPoolSize=200
                        print(f"    ✅ Connection pool size optimized: {total_pool} (target: 200)")
                    else:
                        print(f"    ⚠️ Connection pool size: {total_pool} (expected: ~200)")
                
                # Check network stats
                if "network" in conn_info:
                    network = conn_info["network"]
                    bytes_in = network.get("bytes_in", 0)
                    bytes_out = network.get("bytes_out", 0)
                    requests = network.get("num_requests", 0)
                    
                    print(f"    • Network bytes in: {bytes_in}")
                    print(f"    • Network bytes out: {bytes_out}")
                    print(f"    • Total requests: {requests}")
            
            # Check collections info
            if "collections" in data:
                collections = data["collections"]
                collection_count = len(collections)
                print(f"    • Collections monitored: {collection_count}")
                
                # Show collection sizes
                for coll_name, coll_info in collections.items():
                    count = coll_info.get("count", 0)
                    size_mb = coll_info.get("estimated_size_mb", 0)
                    if count > 0:
                        print(f"      - {coll_name}: {count} documents, {size_mb:.2f} MB")
            
            self.test_results.append({
                "test": "Database Connection Info",
                "status": "success",
                "response_time_ms": response_time,
                "data": data
            })
        else:
            print(f"  ❌ Database monitoring endpoint failed: HTTP {status}")
            self.test_results.append({
                "test": "Database Connection Info",
                "status": "failed",
                "http_status": status
            })

    async def run_all_tests(self):
        """Run all Redis cache and connection pool tests"""
        print("🚀 REDIS CACHE AND CONNECTION POOL TESTING")
        print("Testing Redis cache functionality and MongoDB connection pool optimization")
        print("=" * 70)
        
        await self.setup_session()
        
        if not await self.authenticate():
            print("❌ Authentication failed. Cannot proceed with tests.")
            return
        
        await self.test_redis_cache_functionality()
        await self.test_connection_pool_stress()
        await self.test_database_connection_info()
        
        await self.cleanup_session()
        
        self.print_summary()

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 70)
        print("📊 REDIS CACHE AND CONNECTION POOL TEST RESULTS")
        print("=" * 70)
        
        # Cache test results
        cache_tests = [r for r in self.test_results if "Cache Test" in r.get("endpoint", "")]
        if cache_tests:
            print("\n🗄️ CACHE TEST RESULTS:")
            working_cache = sum(1 for t in cache_tests if t.get("cache_working", False))
            total_cache = len(cache_tests)
            
            for test in cache_tests:
                status = "✅" if test.get("cache_working", False) else "⚠️"
                improvement = test.get("improvement_pct", 0)
                print(f"  {status} {test['endpoint']}: {improvement:.1f}% improvement")
            
            print(f"\n  Cache Success Rate: {working_cache}/{total_cache} ({working_cache/total_cache*100:.1f}%)")
        
        # Connection pool test results
        pool_tests = [r for r in self.test_results if r.get("test") == "Connection Pool Stress Test"]
        if pool_tests:
            print("\n🔗 CONNECTION POOL TEST RESULTS:")
            for test in pool_tests:
                performance = test.get("performance", "unknown")
                status = "✅" if performance in ["excellent", "good"] else "⚠️"
                print(f"  {status} Concurrent Load Test: {performance}")
                print(f"    • Success Rate: {test['successful_requests']}/{test['concurrent_requests']}")
                print(f"    • Avg Response Time: {test['avg_response_time_ms']:.1f}ms")
                print(f"    • Max Response Time: {test['max_response_time_ms']:.1f}ms")
        
        # Database connection info
        db_tests = [r for r in self.test_results if r.get("test") == "Database Connection Info"]
        if db_tests:
            print("\n🗄️ DATABASE CONNECTION INFO:")
            for test in db_tests:
                if test.get("status") == "success":
                    print(f"  ✅ Database monitoring working: {test['response_time_ms']:.1f}ms")
                else:
                    print(f"  ❌ Database monitoring failed")
        
        print("\n🎯 OPTIMIZATION SUMMARY:")
        print("• Redis Cache: Tested for performance improvements")
        print("• Connection Pool: Tested under concurrent load")
        print("• MongoDB Monitoring: Connection stats verified")
        print("• Performance Target: < 500ms average response time")
        
        print("\n" + "=" * 70)

async def main():
    """Main test execution"""
    tester = RedisCacheConnectionTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())