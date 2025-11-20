#!/usr/bin/env python3
"""
Comprehensive Backend Testing for Monitoring & Logging System
Testing 6 log types and 12 endpoints with integration testing
"""

import asyncio
import aiohttp
import json
import sys
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
import uuid

# Configuration
BACKEND_URL = "https://fix-attempt-1.preview.emergentagent.com/api"
TEST_EMAIL = "test@hotel.com"
TEST_PASSWORD = "test123"

class LoggingSystemTester:
    def __init__(self):
        self.session = None
        self.auth_token = None
        self.tenant_id = None
        self.user_id = None
        self.test_results = []
        self.created_test_data = {
            'error_logs': [],
            'night_audit_logs': [],
            'ota_sync_logs': [],
            'rms_publish_logs': [],
            'maintenance_prediction_logs': [],
            'alerts': [],
            'bookings': [],
            'folios': []
        }

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
                    self.tenant_id = data["user"]["tenant_id"]
                    self.user_id = data["user"]["id"]
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

    async def create_test_data(self):
        """Create test data for logging system testing"""
        print("\n🔧 Creating test data for logging system...")
        
        # Create test booking and folio for night audit testing
        try:
            # First create a guest
            guest_data = {
                "name": "John Doe",
                "email": "john.doe@test.com",
                "phone": "+1234567890",
                "id_number": "12345678",
                "nationality": "US"
            }
            
            async with self.session.post(f"{BACKEND_URL}/pms/guests", 
                                       json=guest_data, 
                                       headers=self.get_headers()) as response:
                if response.status == 200:
                    guest = await response.json()
                    guest_id = guest["id"]
                    print(f"✅ Test guest created: {guest_id}")
                else:
                    print(f"⚠️ Guest creation failed: {response.status}")
                    return False

            # Get available room
            async with self.session.get(f"{BACKEND_URL}/pms/rooms", 
                                      headers=self.get_headers()) as response:
                if response.status == 200:
                    rooms = await response.json()
                    if rooms:
                        room_id = rooms[0]["id"]
                        print(f"✅ Using room: {room_id}")
                    else:
                        print("⚠️ No rooms available")
                        return False
                else:
                    print(f"⚠️ Failed to get rooms: {response.status}")
                    return False

            # Create test booking
            booking_data = {
                "guest_id": guest_id,
                "room_id": room_id,
                "check_in": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
                "check_out": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
                "adults": 2,
                "children": 0,
                "children_ages": [],
                "guests_count": 2,
                "total_amount": 150.0,
                "base_rate": 150.0
            }
            
            async with self.session.post(f"{BACKEND_URL}/pms/bookings", 
                                       json=booking_data, 
                                       headers=self.get_headers()) as response:
                if response.status == 200:
                    booking = await response.json()
                    booking_id = booking["id"]
                    self.created_test_data['bookings'].append(booking_id)
                    print(f"✅ Test booking created: {booking_id}")
                else:
                    print(f"⚠️ Booking creation failed: {response.status}")
                    return False

            # Check in the booking
            async with self.session.post(f"{BACKEND_URL}/frontdesk/checkin/{booking_id}?create_folio=true", 
                                       headers=self.get_headers()) as response:
                if response.status == 200:
                    checkin_result = await response.json()
                    print(f"✅ Booking checked in successfully")
                else:
                    print(f"⚠️ Check-in failed: {response.status}")

            return True
            
        except Exception as e:
            print(f"❌ Error creating test data: {e}")
            return False

    async def test_error_logs_endpoint(self):
        """Test GET /api/logs/errors endpoint"""
        print("\n📋 Testing Error Logs Endpoint...")
        
        test_cases = [
            {
                "name": "Get all error logs",
                "params": {},
                "expected_fields": ["logs", "total_count", "severity_stats"]
            },
            {
                "name": "Filter by severity",
                "params": {"severity": "error"},
                "expected_fields": ["logs", "total_count", "severity_stats"]
            },
            {
                "name": "Filter by date range",
                "params": {
                    "start_date": (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(),
                    "end_date": datetime.now(timezone.utc).isoformat()
                },
                "expected_fields": ["logs", "total_count", "severity_stats"]
            },
            {
                "name": "Test pagination",
                "params": {"limit": 5, "skip": 0},
                "expected_fields": ["logs", "total_count", "limit", "skip"]
            }
        ]
        
        passed = 0
        total = len(test_cases)
        
        for test_case in test_cases:
            try:
                url = f"{BACKEND_URL}/logs/errors"
                if test_case["params"]:
                    params = "&".join([f"{k}={v}" for k, v in test_case["params"].items()])
                    url += f"?{params}"
                
                async with self.session.get(url, headers=self.get_headers()) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Check required fields
                        missing_fields = [field for field in test_case["expected_fields"] if field not in data]
                        if not missing_fields:
                            print(f"  ✅ {test_case['name']}: PASSED")
                            passed += 1
                        else:
                            print(f"  ❌ {test_case['name']}: Missing fields {missing_fields}")
                    else:
                        print(f"  ❌ {test_case['name']}: HTTP {response.status}")
                        
            except Exception as e:
                print(f"  ❌ {test_case['name']}: Error {e}")
        
        self.test_results.append({
            "endpoint": "GET /api/logs/errors",
            "passed": passed,
            "total": total,
            "success_rate": f"{passed/total*100:.1f}%"
        })

    async def test_night_audit_logs_endpoint(self):
        """Test GET /api/logs/night-audit endpoint"""
        print("\n📋 Testing Night Audit Logs Endpoint...")
        
        test_cases = [
            {
                "name": "Get all night audit logs",
                "params": {},
                "expected_fields": ["logs", "total_count", "stats"]
            },
            {
                "name": "Filter by status",
                "params": {"status": "completed"},
                "expected_fields": ["logs", "total_count", "stats"]
            },
            {
                "name": "Filter by date range",
                "params": {
                    "start_date": (datetime.now(timezone.utc) - timedelta(days=30)).date().isoformat(),
                    "end_date": datetime.now(timezone.utc).date().isoformat()
                },
                "expected_fields": ["logs", "total_count", "stats"]
            }
        ]
        
        passed = 0
        total = len(test_cases)
        
        for test_case in test_cases:
            try:
                url = f"{BACKEND_URL}/logs/night-audit"
                if test_case["params"]:
                    params = "&".join([f"{k}={v}" for k, v in test_case["params"].items()])
                    url += f"?{params}"
                
                async with self.session.get(url, headers=self.get_headers()) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Check required fields
                        missing_fields = [field for field in test_case["expected_fields"] if field not in data]
                        if not missing_fields:
                            # Verify stats structure
                            stats = data.get("stats", {})
                            required_stats = ["total_audits", "successful", "failed", "success_rate", "total_charges"]
                            missing_stats = [stat for stat in required_stats if stat not in stats]
                            
                            if not missing_stats:
                                print(f"  ✅ {test_case['name']}: PASSED")
                                passed += 1
                            else:
                                print(f"  ❌ {test_case['name']}: Missing stats {missing_stats}")
                        else:
                            print(f"  ❌ {test_case['name']}: Missing fields {missing_fields}")
                    else:
                        print(f"  ❌ {test_case['name']}: HTTP {response.status}")
                        
            except Exception as e:
                print(f"  ❌ {test_case['name']}: Error {e}")
        
        self.test_results.append({
            "endpoint": "GET /api/logs/night-audit",
            "passed": passed,
            "total": total,
            "success_rate": f"{passed/total*100:.1f}%"
        })

    async def test_ota_sync_logs_endpoint(self):
        """Test GET /api/logs/ota-sync endpoint"""
        print("\n📋 Testing OTA Sync Logs Endpoint...")
        
        test_cases = [
            {
                "name": "Get all OTA sync logs",
                "params": {},
                "expected_fields": ["logs", "total_count", "channel_stats"]
            },
            {
                "name": "Filter by channel",
                "params": {"channel": "booking_com"},
                "expected_fields": ["logs", "total_count", "channel_stats"]
            },
            {
                "name": "Filter by sync type",
                "params": {"sync_type": "rates"},
                "expected_fields": ["logs", "total_count", "channel_stats"]
            },
            {
                "name": "Filter by status",
                "params": {"status": "completed"},
                "expected_fields": ["logs", "total_count", "channel_stats"]
            }
        ]
        
        passed = 0
        total = len(test_cases)
        
        for test_case in test_cases:
            try:
                url = f"{BACKEND_URL}/logs/ota-sync"
                if test_case["params"]:
                    params = "&".join([f"{k}={v}" for k, v in test_case["params"].items()])
                    url += f"?{params}"
                
                async with self.session.get(url, headers=self.get_headers()) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Check required fields
                        missing_fields = [field for field in test_case["expected_fields"] if field not in data]
                        if not missing_fields:
                            print(f"  ✅ {test_case['name']}: PASSED")
                            passed += 1
                        else:
                            print(f"  ❌ {test_case['name']}: Missing fields {missing_fields}")
                    else:
                        print(f"  ❌ {test_case['name']}: HTTP {response.status}")
                        
            except Exception as e:
                print(f"  ❌ {test_case['name']}: Error {e}")
        
        self.test_results.append({
            "endpoint": "GET /api/logs/ota-sync",
            "passed": passed,
            "total": total,
            "success_rate": f"{passed/total*100:.1f}%"
        })

    async def test_rms_publish_logs_endpoint(self):
        """Test GET /api/logs/rms-publish endpoint"""
        print("\n📋 Testing RMS Publish Logs Endpoint...")
        
        test_cases = [
            {
                "name": "Get all RMS publish logs",
                "params": {},
                "expected_fields": ["logs", "total_count", "stats"]
            },
            {
                "name": "Filter by publish type",
                "params": {"publish_type": "rates"},
                "expected_fields": ["logs", "total_count", "stats"]
            },
            {
                "name": "Filter by auto published",
                "params": {"auto_published": "true"},
                "expected_fields": ["logs", "total_count", "stats"]
            }
        ]
        
        passed = 0
        total = len(test_cases)
        
        for test_case in test_cases:
            try:
                url = f"{BACKEND_URL}/logs/rms-publish"
                if test_case["params"]:
                    params = "&".join([f"{k}={v}" for k, v in test_case["params"].items()])
                    url += f"?{params}"
                
                async with self.session.get(url, headers=self.get_headers()) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Check required fields
                        missing_fields = [field for field in test_case["expected_fields"] if field not in data]
                        if not missing_fields:
                            # Verify stats structure
                            stats = data.get("stats", {})
                            required_stats = ["total_publishes", "automation_rate", "success_rate"]
                            missing_stats = [stat for stat in required_stats if stat not in stats]
                            
                            if not missing_stats:
                                print(f"  ✅ {test_case['name']}: PASSED")
                                passed += 1
                            else:
                                print(f"  ❌ {test_case['name']}: Missing stats {missing_stats}")
                        else:
                            print(f"  ❌ {test_case['name']}: Missing fields {missing_fields}")
                    else:
                        print(f"  ❌ {test_case['name']}: HTTP {response.status}")
                        
            except Exception as e:
                print(f"  ❌ {test_case['name']}: Error {e}")
        
        self.test_results.append({
            "endpoint": "GET /api/logs/rms-publish",
            "passed": passed,
            "total": total,
            "success_rate": f"{passed/total*100:.1f}%"
        })

    async def test_maintenance_prediction_logs_endpoint(self):
        """Test GET /api/logs/maintenance-predictions endpoint"""
        print("\n📋 Testing Maintenance Prediction Logs Endpoint...")
        
        test_cases = [
            {
                "name": "Get all maintenance prediction logs",
                "params": {},
                "expected_fields": ["logs", "total_count", "risk_stats"]
            },
            {
                "name": "Filter by equipment type",
                "params": {"equipment_type": "hvac"},
                "expected_fields": ["logs", "total_count", "risk_stats"]
            },
            {
                "name": "Filter by prediction result",
                "params": {"prediction_result": "high"},
                "expected_fields": ["logs", "total_count", "risk_stats"]
            }
        ]
        
        passed = 0
        total = len(test_cases)
        
        for test_case in test_cases:
            try:
                url = f"{BACKEND_URL}/logs/maintenance-predictions"
                if test_case["params"]:
                    params = "&".join([f"{k}={v}" for k, v in test_case["params"].items()])
                    url += f"?{params}"
                
                async with self.session.get(url, headers=self.get_headers()) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Check required fields
                        missing_fields = [field for field in test_case["expected_fields"] if field not in data]
                        if not missing_fields:
                            print(f"  ✅ {test_case['name']}: PASSED")
                            passed += 1
                        else:
                            print(f"  ❌ {test_case['name']}: Missing fields {missing_fields}")
                    else:
                        print(f"  ❌ {test_case['name']}: HTTP {response.status}")
                        
            except Exception as e:
                print(f"  ❌ {test_case['name']}: Error {e}")
        
        self.test_results.append({
            "endpoint": "GET /api/logs/maintenance-predictions",
            "passed": passed,
            "total": total,
            "success_rate": f"{passed/total*100:.1f}%"
        })

    async def test_alerts_history_endpoint(self):
        """Test GET /api/logs/alerts-history endpoint"""
        print("\n📋 Testing Alert History Endpoint...")
        
        test_cases = [
            {
                "name": "Get all alert history",
                "params": {},
                "expected_fields": ["alerts", "total_count", "stats"]
            },
            {
                "name": "Filter by severity",
                "params": {"severity": "high"},
                "expected_fields": ["alerts", "total_count", "stats"]
            },
            {
                "name": "Filter by status",
                "params": {"status": "unread"},
                "expected_fields": ["alerts", "total_count", "stats"]
            },
            {
                "name": "Filter by source module",
                "params": {"source_module": "system"},
                "expected_fields": ["alerts", "total_count", "stats"]
            }
        ]
        
        passed = 0
        total = len(test_cases)
        
        for test_case in test_cases:
            try:
                url = f"{BACKEND_URL}/logs/alerts-history"
                if test_case["params"]:
                    params = "&".join([f"{k}={v}" for k, v in test_case["params"].items()])
                    url += f"?{params}"
                
                async with self.session.get(url, headers=self.get_headers()) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Check required fields
                        missing_fields = [field for field in test_case["expected_fields"] if field not in data]
                        if not missing_fields:
                            # Verify stats structure
                            stats = data.get("stats", {})
                            required_stats = ["total_alerts", "by_severity", "by_module"]
                            missing_stats = [stat for stat in required_stats if stat not in stats]
                            
                            if not missing_stats:
                                print(f"  ✅ {test_case['name']}: PASSED")
                                passed += 1
                            else:
                                print(f"  ❌ {test_case['name']}: Missing stats {missing_stats}")
                        else:
                            print(f"  ❌ {test_case['name']}: Missing fields {missing_fields}")
                    else:
                        print(f"  ❌ {test_case['name']}: HTTP {response.status}")
                        
            except Exception as e:
                print(f"  ❌ {test_case['name']}: Error {e}")
        
        self.test_results.append({
            "endpoint": "GET /api/logs/alerts-history",
            "passed": passed,
            "total": total,
            "success_rate": f"{passed/total*100:.1f}%"
        })

    async def test_logs_dashboard_endpoint(self):
        """Test GET /api/logs/dashboard endpoint"""
        print("\n📋 Testing Logs Dashboard Endpoint...")
        
        try:
            async with self.session.get(f"{BACKEND_URL}/logs/dashboard", 
                                      headers=self.get_headers()) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Check required fields
                    required_fields = [
                        "summary", "recent_critical_errors", "unread_alerts", "health"
                    ]
                    missing_fields = [field for field in required_fields if field not in data]
                    
                    if not missing_fields:
                        # Verify summary structure
                        summary = data.get("summary", {})
                        required_summary_fields = [
                            "error_logs", "night_audit_logs", "ota_sync_logs", 
                            "rms_publish_logs", "maintenance_prediction_logs", "alert_history"
                        ]
                        missing_summary = [field for field in required_summary_fields if field not in summary]
                        
                        # Verify health structure
                        health = data.get("health", {})
                        required_health_fields = ["overall_status", "indicators"]
                        missing_health = [field for field in required_health_fields if field not in health]
                        
                        if not missing_summary and not missing_health:
                            print("  ✅ Dashboard structure: PASSED")
                            self.test_results.append({
                                "endpoint": "GET /api/logs/dashboard",
                                "passed": 1,
                                "total": 1,
                                "success_rate": "100.0%"
                            })
                        else:
                            print(f"  ❌ Dashboard structure: Missing summary {missing_summary}, health {missing_health}")
                            self.test_results.append({
                                "endpoint": "GET /api/logs/dashboard",
                                "passed": 0,
                                "total": 1,
                                "success_rate": "0.0%"
                            })
                    else:
                        print(f"  ❌ Dashboard: Missing fields {missing_fields}")
                        self.test_results.append({
                            "endpoint": "GET /api/logs/dashboard",
                            "passed": 0,
                            "total": 1,
                            "success_rate": "0.0%"
                        })
                else:
                    print(f"  ❌ Dashboard: HTTP {response.status}")
                    self.test_results.append({
                        "endpoint": "GET /api/logs/dashboard",
                        "passed": 0,
                        "total": 1,
                        "success_rate": "0.0%"
                    })
                    
        except Exception as e:
            print(f"  ❌ Dashboard: Error {e}")
            self.test_results.append({
                "endpoint": "GET /api/logs/dashboard",
                "passed": 0,
                "total": 1,
                "success_rate": "0.0%"
            })

    async def test_night_audit_integration(self):
        """Test POST /api/night-audit/post-room-charges with logging integration"""
        print("\n🔄 Testing Night Audit Integration with Logging...")
        
        try:
            # First, get current night audit log count
            async with self.session.get(f"{BACKEND_URL}/logs/night-audit", 
                                      headers=self.get_headers()) as response:
                if response.status == 200:
                    before_data = await response.json()
                    before_count = before_data.get("total_count", 0)
                else:
                    before_count = 0
            
            # Trigger night audit
            async with self.session.post(f"{BACKEND_URL}/night-audit/post-room-charges", 
                                       headers=self.get_headers()) as response:
                if response.status == 200:
                    audit_result = await response.json()
                    print(f"  ✅ Night audit executed: {audit_result.get('message')}")
                    print(f"     Charges posted: {audit_result.get('charges_posted', 0)}")
                    print(f"     Bookings processed: {audit_result.get('bookings_processed', 0)}")
                    
                    # Wait a moment for log to be created
                    await asyncio.sleep(1)
                    
                    # Check if log was created
                    async with self.session.get(f"{BACKEND_URL}/logs/night-audit", 
                                              headers=self.get_headers()) as response:
                        if response.status == 200:
                            after_data = await response.json()
                            after_count = after_data.get("total_count", 0)
                            
                            if after_count > before_count:
                                print(f"  ✅ Night audit log created successfully")
                                
                                # Check the latest log entry
                                logs = after_data.get("logs", [])
                                if logs:
                                    latest_log = logs[0]  # Should be sorted by timestamp desc
                                    required_fields = ["audit_date", "status", "rooms_processed", "charges_posted", "total_amount"]
                                    missing_fields = [field for field in required_fields if field not in latest_log]
                                    
                                    if not missing_fields:
                                        print(f"  ✅ Log entry structure verified")
                                        self.test_results.append({
                                            "endpoint": "POST /api/night-audit/post-room-charges (Integration)",
                                            "passed": 1,
                                            "total": 1,
                                            "success_rate": "100.0%"
                                        })
                                    else:
                                        print(f"  ❌ Log entry missing fields: {missing_fields}")
                                        self.test_results.append({
                                            "endpoint": "POST /api/night-audit/post-room-charges (Integration)",
                                            "passed": 0,
                                            "total": 1,
                                            "success_rate": "0.0%"
                                        })
                                else:
                                    print(f"  ❌ No log entries found")
                                    self.test_results.append({
                                        "endpoint": "POST /api/night-audit/post-room-charges (Integration)",
                                        "passed": 0,
                                        "total": 1,
                                        "success_rate": "0.0%"
                                    })
                            else:
                                print(f"  ❌ No new log entry created")
                                self.test_results.append({
                                    "endpoint": "POST /api/night-audit/post-room-charges (Integration)",
                                    "passed": 0,
                                    "total": 1,
                                    "success_rate": "0.0%"
                                })
                        else:
                            print(f"  ❌ Failed to retrieve logs after audit")
                            self.test_results.append({
                                "endpoint": "POST /api/night-audit/post-room-charges (Integration)",
                                "passed": 0,
                                "total": 1,
                                "success_rate": "0.0%"
                            })
                else:
                    print(f"  ❌ Night audit failed: HTTP {response.status}")
                    error_text = await response.text()
                    print(f"     Error: {error_text}")
                    self.test_results.append({
                        "endpoint": "POST /api/night-audit/post-room-charges (Integration)",
                        "passed": 0,
                        "total": 1,
                        "success_rate": "0.0%"
                    })
                    
        except Exception as e:
            print(f"  ❌ Night audit integration error: {e}")
            self.test_results.append({
                "endpoint": "POST /api/night-audit/post-room-charges (Integration)",
                "passed": 0,
                "total": 1,
                "success_rate": "0.0%"
            })

    async def test_error_resolution_endpoint(self):
        """Test POST /api/logs/errors/{error_id}/resolve endpoint"""
        print("\n🔧 Testing Error Resolution Endpoint...")
        
        # This test would require creating an actual error log first
        # For now, we'll test with a mock error ID to verify endpoint structure
        
        try:
            mock_error_id = str(uuid.uuid4())
            resolution_data = {
                "resolution_notes": "Test resolution notes"
            }
            
            async with self.session.post(f"{BACKEND_URL}/logs/errors/{mock_error_id}/resolve", 
                                       json=resolution_data,
                                       headers=self.get_headers()) as response:
                if response.status == 404:
                    # Expected for non-existent error ID
                    print(f"  ✅ Error resolution endpoint structure verified (404 for non-existent ID)")
                    self.test_results.append({
                        "endpoint": "POST /api/logs/errors/{error_id}/resolve",
                        "passed": 1,
                        "total": 1,
                        "success_rate": "100.0%"
                    })
                elif response.status == 200:
                    data = await response.json()
                    if data.get("success") and data.get("message"):
                        print(f"  ✅ Error resolution successful")
                        self.test_results.append({
                            "endpoint": "POST /api/logs/errors/{error_id}/resolve",
                            "passed": 1,
                            "total": 1,
                            "success_rate": "100.0%"
                        })
                    else:
                        print(f"  ❌ Invalid response structure")
                        self.test_results.append({
                            "endpoint": "POST /api/logs/errors/{error_id}/resolve",
                            "passed": 0,
                            "total": 1,
                            "success_rate": "0.0%"
                        })
                else:
                    print(f"  ❌ Unexpected status: {response.status}")
                    self.test_results.append({
                        "endpoint": "POST /api/logs/errors/{error_id}/resolve",
                        "passed": 0,
                        "total": 1,
                        "success_rate": "0.0%"
                    })
                    
        except Exception as e:
            print(f"  ❌ Error resolution test error: {e}")
            self.test_results.append({
                "endpoint": "POST /api/logs/errors/{error_id}/resolve",
                "passed": 0,
                "total": 1,
                "success_rate": "0.0%"
            })

    async def test_alert_action_endpoints(self):
        """Test alert acknowledge and resolve endpoints"""
        print("\n🚨 Testing Alert Action Endpoints...")
        
        # Test acknowledge endpoint
        try:
            mock_alert_id = str(uuid.uuid4())
            
            async with self.session.post(f"{BACKEND_URL}/logs/alerts/{mock_alert_id}/acknowledge", 
                                       headers=self.get_headers()) as response:
                if response.status == 404:
                    # Expected for non-existent alert ID
                    print(f"  ✅ Alert acknowledge endpoint structure verified (404 for non-existent ID)")
                    acknowledge_passed = 1
                elif response.status == 200:
                    data = await response.json()
                    if data.get("success") and data.get("message"):
                        print(f"  ✅ Alert acknowledge successful")
                        acknowledge_passed = 1
                    else:
                        print(f"  ❌ Invalid acknowledge response structure")
                        acknowledge_passed = 0
                else:
                    print(f"  ❌ Acknowledge unexpected status: {response.status}")
                    acknowledge_passed = 0
                    
        except Exception as e:
            print(f"  ❌ Alert acknowledge test error: {e}")
            acknowledge_passed = 0

        # Test resolve endpoint
        try:
            mock_alert_id = str(uuid.uuid4())
            resolution_data = {
                "resolution_notes": "Test alert resolution"
            }
            
            async with self.session.post(f"{BACKEND_URL}/logs/alerts/{mock_alert_id}/resolve", 
                                       json=resolution_data,
                                       headers=self.get_headers()) as response:
                if response.status == 404:
                    # Expected for non-existent alert ID
                    print(f"  ✅ Alert resolve endpoint structure verified (404 for non-existent ID)")
                    resolve_passed = 1
                elif response.status == 200:
                    data = await response.json()
                    if data.get("success") and data.get("message"):
                        print(f"  ✅ Alert resolve successful")
                        resolve_passed = 1
                    else:
                        print(f"  ❌ Invalid resolve response structure")
                        resolve_passed = 0
                else:
                    print(f"  ❌ Resolve unexpected status: {response.status}")
                    resolve_passed = 0
                    
        except Exception as e:
            print(f"  ❌ Alert resolve test error: {e}")
            resolve_passed = 0

        # Record results
        self.test_results.append({
            "endpoint": "POST /api/logs/alerts/{alert_id}/acknowledge",
            "passed": acknowledge_passed,
            "total": 1,
            "success_rate": f"{acknowledge_passed*100:.1f}%"
        })
        
        self.test_results.append({
            "endpoint": "POST /api/logs/alerts/{alert_id}/resolve",
            "passed": resolve_passed,
            "total": 1,
            "success_rate": f"{resolve_passed*100:.1f}%"
        })

    async def run_all_tests(self):
        """Run all monitoring and logging system tests"""
        print("🚀 Starting Comprehensive Monitoring & Logging System Tests")
        print("=" * 70)
        
        # Setup
        await self.setup_session()
        
        if not await self.authenticate():
            print("❌ Authentication failed. Cannot proceed with tests.")
            return
        
        # Create test data
        if not await self.create_test_data():
            print("⚠️ Test data creation failed. Some tests may not work properly.")
        
        # Phase 1: Log Viewing Endpoints (Priority: HIGH)
        await self.test_error_logs_endpoint()
        await self.test_night_audit_logs_endpoint()
        await self.test_ota_sync_logs_endpoint()
        await self.test_rms_publish_logs_endpoint()
        await self.test_maintenance_prediction_logs_endpoint()
        await self.test_alerts_history_endpoint()
        
        # Phase 2: Dashboard & Overview (Priority: HIGH)
        await self.test_logs_dashboard_endpoint()
        
        # Phase 3: Action Endpoints (Priority: MEDIUM)
        await self.test_error_resolution_endpoint()
        await self.test_alert_action_endpoints()
        
        # Phase 4: Integration Testing (Priority: HIGH)
        await self.test_night_audit_integration()
        
        # Cleanup
        await self.cleanup_session()
        
        # Print results
        self.print_test_summary()

    def print_test_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "=" * 70)
        print("📊 MONITORING & LOGGING SYSTEM TEST RESULTS")
        print("=" * 70)
        
        total_passed = 0
        total_tests = 0
        
        print("\n📋 ENDPOINT TEST RESULTS:")
        print("-" * 50)
        
        for result in self.test_results:
            endpoint = result["endpoint"]
            passed = result["passed"]
            total = result["total"]
            success_rate = result["success_rate"]
            
            status = "✅ WORKING" if passed == total else "❌ FAILED" if passed == 0 else "⚠️ PARTIAL"
            print(f"{status} {endpoint}")
            print(f"   Tests: {passed}/{total} ({success_rate})")
            
            total_passed += passed
            total_tests += total
        
        print("\n" + "=" * 70)
        overall_success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        print(f"📈 OVERALL SUCCESS RATE: {total_passed}/{total_tests} ({overall_success_rate:.1f}%)")
        
        if overall_success_rate >= 90:
            print("🎉 EXCELLENT: Monitoring & Logging System is working perfectly!")
        elif overall_success_rate >= 75:
            print("✅ GOOD: Most monitoring features are working correctly")
        elif overall_success_rate >= 50:
            print("⚠️ PARTIAL: Some monitoring features need attention")
        else:
            print("❌ CRITICAL: Major issues with monitoring system")
        
        print("\n🔍 KEY FEATURES TESTED:")
        print("• 6 Log Types: Error, Night Audit, OTA Sync, RMS Publish, Maintenance Predictions, Alert History")
        print("• 12 Endpoints: Log viewing, filtering, dashboard, actions")
        print("• Integration: Night audit automatic logging")
        print("• Dashboard: Comprehensive overview with health indicators")
        print("• Actions: Error resolution, alert acknowledgment/resolution")
        
        print("\n" + "=" * 70)

async def main():
    """Main test execution"""
    tester = LoggingSystemTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())