#!/usr/bin/env python3
"""
Comprehensive Load Testing for Hotel PMS
Tests system under realistic load: 550 rooms, 300+ daily transactions
"""

import asyncio
import aiohttp
import time
import random
import json
from datetime import datetime, timedelta
from typing import List, Dict
import statistics

BACKEND_URL = "http://localhost:8001/api"
TOKEN = None

class LoadTester:
    """Comprehensive load testing suite"""
    
    def __init__(self):
        self.results = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'response_times': [],
            'errors': [],
            'endpoint_stats': {}
        }
        
    async def authenticate(self, session):
        """Get authentication token"""
        global TOKEN
        login_data = {"email": "admin@hotel.com", "password": "admin123"}
        
        async with session.post(f"{BACKEND_URL}/auth/login", json=login_data) as response:
            if response.status == 200:
                data = await response.json()
                TOKEN = data.get("access_token")
                return True
            return False
    
    async def make_request(self, session, method, endpoint, data=None):
        """Make HTTP request and track metrics"""
        headers = {"Authorization": f"Bearer {TOKEN}"}
        url = f"{BACKEND_URL}{endpoint}"
        
        start = time.time()
        try:
            if method == "GET":
                async with session.get(url, headers=headers) as response:
                    response_time = (time.time() - start) * 1000
                    status = response.status
                    result = await response.json() if response.status == 200 else {}
            elif method == "POST":
                async with session.post(url, json=data, headers=headers) as response:
                    response_time = (time.time() - start) * 1000
                    status = response.status
                    result = await response.json() if response.status == 200 else {}
            
            # Track metrics
            self.results['total_requests'] += 1
            self.results['response_times'].append(response_time)
            
            if status == 200:
                self.results['successful_requests'] += 1
            else:
                self.results['failed_requests'] += 1
                self.results['errors'].append({
                    'endpoint': endpoint,
                    'status': status,
                    'time': datetime.now().isoformat()
                })
            
            # Track per-endpoint stats
            if endpoint not in self.results['endpoint_stats']:
                self.results['endpoint_stats'][endpoint] = {
                    'count': 0,
                    'success': 0,
                    'failed': 0,
                    'response_times': []
                }
            
            self.results['endpoint_stats'][endpoint]['count'] += 1
            self.results['endpoint_stats'][endpoint]['response_times'].append(response_time)
            
            if status == 200:
                self.results['endpoint_stats'][endpoint]['success'] += 1
            else:
                self.results['endpoint_stats'][endpoint]['failed'] += 1
            
            return status, response_time, result
            
        except Exception as e:
            response_time = (time.time() - start) * 1000
            self.results['total_requests'] += 1
            self.results['failed_requests'] += 1
            self.results['errors'].append({
                'endpoint': endpoint,
                'error': str(e),
                'time': datetime.now().isoformat()
            })
            return 500, response_time, {}
    
    async def simulate_dashboard_load(self, session, duration=60):
        """Simulate multiple users accessing dashboards"""
        print(f"\n📊 Simulating Dashboard Load ({duration}s)...")
        
        dashboards = [
            "/pms/dashboard",
            "/housekeeping/room-status",
            "/dashboard/role-based",
            "/dashboard/employee-performance",
            "/dashboard/guest-satisfaction-trends",
            "/dashboard/ota-cancellation-rate"
        ]
        
        end_time = time.time() + duration
        request_count = 0
        
        while time.time() < end_time:
            # Random dashboard
            endpoint = random.choice(dashboards)
            status, response_time, _ = await self.make_request(session, "GET", endpoint)
            request_count += 1
            
            if request_count % 10 == 0:
                print(f"  📈 {request_count} requests sent...")
            
            # Small delay to simulate real user behavior
            await asyncio.sleep(random.uniform(0.1, 0.5))
        
        print(f"  ✅ Dashboard load test complete: {request_count} requests")
    
    async def simulate_concurrent_users(self, session, num_users=20, duration=30):
        """Simulate multiple concurrent users"""
        print(f"\n👥 Simulating {num_users} Concurrent Users ({duration}s)...")
        
        endpoints = [
            "/pms/dashboard",
            "/housekeeping/room-status",
            "/dashboard/role-based",
            "/monitoring/health",
            "/monitoring/system"
        ]
        
        async def user_session(user_id):
            """Simulate one user's activity"""
            end_time = time.time() + duration
            user_requests = 0
            
            while time.time() < end_time:
                endpoint = random.choice(endpoints)
                await self.make_request(session, "GET", endpoint)
                user_requests += 1
                await asyncio.sleep(random.uniform(0.2, 1.0))
            
            return user_requests
        
        # Run all users concurrently
        tasks = [user_session(i) for i in range(num_users)]
        user_results = await asyncio.gather(*tasks)
        
        total_requests = sum(user_results)
        print(f"  ✅ {num_users} users completed: {total_requests} total requests")
    
    async def stress_test_critical_endpoints(self, session, requests_per_endpoint=100):
        """Stress test critical endpoints with rapid requests"""
        print(f"\n🔥 Stress Testing Critical Endpoints ({requests_per_endpoint} requests each)...")
        
        critical_endpoints = [
            "/pms/dashboard",
            "/housekeeping/room-status",
            "/dashboard/role-based",
            "/monitoring/health"
        ]
        
        for endpoint in critical_endpoints:
            print(f"  🎯 Testing {endpoint}...")
            
            start_time = time.time()
            
            # Fire rapid requests
            tasks = [
                self.make_request(session, "GET", endpoint)
                for _ in range(requests_per_endpoint)
            ]
            
            results = await asyncio.gather(*tasks)
            
            duration = time.time() - start_time
            requests_per_second = requests_per_endpoint / duration
            
            success_count = sum(1 for r in results if r[0] == 200)
            avg_response_time = statistics.mean([r[1] for r in results])
            
            print(f"     ✅ {success_count}/{requests_per_endpoint} successful")
            print(f"     ⚡ {requests_per_second:.1f} req/s")
            print(f"     ⏱️  Avg response: {avg_response_time:.1f}ms")
    
    async def test_database_load(self, session, duration=30):
        """Test database-heavy operations"""
        print(f"\n🗄️  Testing Database Load ({duration}s)...")
        
        # These endpoints hit the database heavily
        db_endpoints = [
            "/pms/dashboard",
            "/housekeeping/room-status",
            "/dashboard/employee-performance",
            "/dashboard/guest-satisfaction-trends"
        ]
        
        end_time = time.time() + duration
        request_count = 0
        
        while time.time() < end_time:
            # Fire multiple concurrent requests
            tasks = [
                self.make_request(session, "GET", random.choice(db_endpoints))
                for _ in range(10)
            ]
            
            await asyncio.gather(*tasks)
            request_count += 10
            
            if request_count % 50 == 0:
                print(f"  📊 {request_count} DB requests sent...")
            
            await asyncio.sleep(0.1)
        
        print(f"  ✅ Database load test complete: {request_count} requests")
    
    async def run_comprehensive_load_test(self):
        """Run all load tests"""
        print("=" * 70)
        print("🚀 COMPREHENSIVE LOAD TESTING - Hotel PMS")
        print("=" * 70)
        print(f"Target: 550 rooms, 300+ daily transactions")
        print(f"Test Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        async with aiohttp.ClientSession() as session:
            # Authenticate
            print("🔐 Authenticating...")
            if not await self.authenticate(session):
                print("❌ Authentication failed!")
                return
            print("✅ Authentication successful")
            
            # Test 1: Dashboard Load (Simulates normal usage)
            await self.simulate_dashboard_load(session, duration=30)
            
            # Test 2: Concurrent Users (Simulates peak hours)
            await self.simulate_concurrent_users(session, num_users=20, duration=20)
            
            # Test 3: Stress Test Critical Endpoints
            await self.stress_test_critical_endpoints(session, requests_per_endpoint=50)
            
            # Test 4: Database Load
            await self.test_database_load(session, duration=20)
            
            # Test 5: Extreme Concurrent Load
            print(f"\n⚡ EXTREME LOAD TEST: 50 Concurrent Users (15s)...")
            await self.simulate_concurrent_users(session, num_users=50, duration=15)
        
        # Print results
        self.print_results()
    
    def print_results(self):
        """Print comprehensive test results"""
        print("\n" + "=" * 70)
        print("📊 LOAD TEST RESULTS")
        print("=" * 70)
        
        # Overall stats
        print(f"\n📈 OVERALL STATISTICS:")
        print(f"  Total Requests: {self.results['total_requests']}")
        print(f"  Successful: {self.results['successful_requests']} ({self.results['successful_requests']/self.results['total_requests']*100:.1f}%)")
        print(f"  Failed: {self.results['failed_requests']} ({self.results['failed_requests']/self.results['total_requests']*100:.1f}%)")
        
        # Response time stats
        if self.results['response_times']:
            print(f"\n⏱️  RESPONSE TIME STATISTICS:")
            print(f"  Average: {statistics.mean(self.results['response_times']):.1f}ms")
            print(f"  Median: {statistics.median(self.results['response_times']):.1f}ms")
            print(f"  Min: {min(self.results['response_times']):.1f}ms")
            print(f"  Max: {max(self.results['response_times']):.1f}ms")
            print(f"  95th Percentile: {self.percentile(self.results['response_times'], 95):.1f}ms")
            print(f"  99th Percentile: {self.percentile(self.results['response_times'], 99):.1f}ms")
        
        # Per-endpoint stats
        print(f"\n🎯 PER-ENDPOINT STATISTICS:")
        for endpoint, stats in sorted(self.results['endpoint_stats'].items(), 
                                      key=lambda x: x[1]['count'], 
                                      reverse=True)[:10]:
            success_rate = (stats['success'] / stats['count'] * 100) if stats['count'] > 0 else 0
            avg_time = statistics.mean(stats['response_times']) if stats['response_times'] else 0
            
            print(f"\n  {endpoint}")
            print(f"    Requests: {stats['count']}")
            print(f"    Success Rate: {success_rate:.1f}%")
            print(f"    Avg Response: {avg_time:.1f}ms")
        
        # Errors
        if self.results['errors']:
            print(f"\n❌ ERRORS ({len(self.results['errors'])}):")
            error_summary = {}
            for error in self.results['errors']:
                key = f"{error.get('endpoint', 'unknown')}: {error.get('status', error.get('error', 'unknown'))}"
                error_summary[key] = error_summary.get(key, 0) + 1
            
            for error, count in sorted(error_summary.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"  • {error}: {count} times")
        
        # Performance assessment
        print(f"\n🎯 PERFORMANCE ASSESSMENT:")
        
        if self.results['response_times']:
            avg_time = statistics.mean(self.results['response_times'])
            success_rate = self.results['successful_requests'] / self.results['total_requests'] * 100
            
            if avg_time < 100 and success_rate > 99:
                rating = "🌟 EXCELLENT"
            elif avg_time < 200 and success_rate > 95:
                rating = "✅ GOOD"
            elif avg_time < 500 and success_rate > 90:
                rating = "⚠️  ACCEPTABLE"
            else:
                rating = "❌ NEEDS IMPROVEMENT"
            
            print(f"  Overall Rating: {rating}")
            print(f"  Average Response Time: {avg_time:.1f}ms")
            print(f"  Success Rate: {success_rate:.1f}%")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        
        if self.results['response_times']:
            p95 = self.percentile(self.results['response_times'], 95)
            
            if p95 > 1000:
                print("  ⚠️  95th percentile > 1000ms - Consider additional optimization")
            elif p95 > 500:
                print("  ℹ️  95th percentile > 500ms - Monitor under production load")
            else:
                print("  ✅ Response times are excellent")
        
        if self.results['failed_requests'] > 0:
            failure_rate = self.results['failed_requests'] / self.results['total_requests'] * 100
            if failure_rate > 5:
                print("  ⚠️  High failure rate - Investigate error causes")
            elif failure_rate > 1:
                print("  ℹ️  Some failures detected - Review error logs")
        else:
            print("  ✅ No failures detected")
        
        print("\n" + "=" * 70)
        print(f"Test End: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
    
    @staticmethod
    def percentile(data, p):
        """Calculate percentile"""
        sorted_data = sorted(data)
        index = int(len(sorted_data) * p / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]

async def main():
    """Run load tests"""
    tester = LoadTester()
    await tester.run_comprehensive_load_test()

if __name__ == "__main__":
    asyncio.run(main())
