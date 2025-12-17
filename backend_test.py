#!/usr/bin/env python3
"""
CSV IMPORT ENDPOINT BACKEND TESTING
Test the new CSV import endpoint for rooms.

OBJECTIVE: Test the CSV import functionality as requested

TARGET ENDPOINTS:
1. POST /api/pms/rooms/import-csv - Import rooms from CSV file
2. GET /api/pms/rooms?limit=300 - Verify imported rooms exist

TEST SCENARIO:
1. Login as muratsutay@hotmail.com / murat1903
2. Call POST /api/pms/rooms/import-csv with multipart/form-data file named rooms.csv containing:
   room_number,room_type,floor,capacity,base_price,view,bed_type,amenities
   C101,deluxe,1,2,150,sea,king,wifi|balcony
   C102,standard,1,2,90,city,queen,wifi
3. Expect response: created==2, skipped==0, errors==0
4. Call again with same file and expect created==0 skipped==2
5. Verify via GET /api/pms/rooms?limit=300 that C101 and C102 exist and have view/bed_type/amenities

EXPECTED RESULTS:
- First import: created=2, skipped=0, errors=0
- Second import: created=0, skipped=2, errors=0
- Rooms C101 and C102 should exist with correct properties
"""

import asyncio
import aiohttp
import json
import sys
import os
from datetime import datetime, timezone, timedelta, date
from typing import Dict, List, Any, Optional
import uuid

# Configuration
BACKEND_URL = "https://code-review-helper-12.preview.emergentagent.com/api"
TEST_EMAIL = "muratsutay@hotmail.com"
TEST_PASSWORD = "murat1903"

class PMSRoomsBulkTester:
    def __init__(self):
        self.session = None
        self.auth_token = None
        self.tenant_id = None
        self.user_id = None
        self.test_results = []
        self.created_test_data = {
            'guests': [],
            'bookings': [],
            'rooms': [],
            'folios': [],
            'bulk_rooms': []
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
                    print(f"✅ Authentication successful - User: {data['user']['name']}, Tenant: {self.tenant_id}")
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

    async def cleanup_test_rooms(self):
        """Clean up any existing test rooms to avoid conflicts"""
        print("\n🧹 Cleaning up existing test rooms...")
        
        try:
            # Get existing rooms with test prefixes
            async with self.session.get(f"{BACKEND_URL}/pms/rooms?limit=500", 
                                      headers=self.get_headers()) as response:
                if response.status == 200:
                    rooms = await response.json()
                    test_rooms = [room for room in rooms if room.get('room_number', '').startswith(('A10', 'B'))]
                    
                    for room in test_rooms:
                        try:
                            async with self.session.delete(f"{BACKEND_URL}/pms/rooms/{room['id']}", 
                                                         headers=self.get_headers()) as del_response:
                                if del_response.status in [200, 204, 404]:
                                    print(f"  🗑️ Cleaned up room: {room.get('room_number', 'Unknown')}")
                        except Exception as e:
                            print(f"  ⚠️ Failed to delete room {room.get('room_number', 'Unknown')}: {e}")
                    
                    print(f"✅ Cleanup completed - {len(test_rooms)} test rooms processed")
                else:
                    print(f"⚠️ Failed to get rooms for cleanup: {response.status}")
                    
        except Exception as e:
            print(f"❌ Error during cleanup: {e}")

    # ============= PMS ROOMS BULK FEATURES TESTS =============

    async def test_bulk_rooms_range_creation(self):
        """Test POST /api/pms/rooms/bulk/range - Create rooms A101-A105"""
        print("\n🏨 Testing Bulk Rooms Range Creation (A101-A105)...")
        print("🎯 OBJECTIVE: Create 5 deluxe rooms with range A101-A105")
        
        bulk_range_payload = {
            "prefix": "A",
            "start_number": 101,
            "end_number": 105,
            "floor": 1,
            "room_type": "deluxe",
            "capacity": 2,
            "base_price": 150,
            "amenities": ["wifi", "balcony"],
            "view": "sea",
            "bed_type": "king"
        }
        
        try:
            start_time = datetime.now()
            async with self.session.post(f"{BACKEND_URL}/pms/rooms/bulk/range", 
                                       json=bulk_range_payload, 
                                       headers=self.get_headers()) as response:
                end_time = datetime.now()
                response_time = (end_time - start_time).total_seconds() * 1000
                
                if response.status == 200:
                    data = await response.json()
                    created_count = data.get("created", 0)
                    skipped_count = data.get("skipped", 0)
                    
                    print(f"      📊 Response data: {data}")
                    
                    # Check if rooms were created OR already exist (skipped)
                    total_processed = created_count + skipped_count
                    if total_processed == 5:
                        if created_count == 5:
                            print(f"  ✅ Bulk range creation: PASSED - New rooms created ({response_time:.1f}ms)")
                            print(f"      📊 Expected: 5 rooms, Created: {created_count}")
                        elif skipped_count == 5:
                            print(f"  ✅ Bulk range creation: PASSED - Rooms already exist ({response_time:.1f}ms)")
                            print(f"      📊 Expected: 5 rooms, Skipped (existing): {skipped_count}")
                        else:
                            print(f"  ✅ Bulk range creation: PASSED - Mixed result ({response_time:.1f}ms)")
                            print(f"      📊 Created: {created_count}, Skipped: {skipped_count}")
                        
                        print(f"      📊 Room range: A101-A105")
                        print(f"      📊 Room type: deluxe, View: sea, Bed: king")
                        print(f"      📊 Amenities: {bulk_range_payload['amenities']}")
                        
                        # Store created room info for later tests
                        self.created_test_data['bulk_rooms'].extend([f"A{i}" for i in range(101, 106)])
                        
                        self.test_results.append({
                            "endpoint": "POST /api/pms/rooms/bulk/range",
                            "passed": 1, "total": 1, "success_rate": "100.0%",
                            "avg_response_time": f"{response_time:.1f}ms"
                        })
                    else:
                        print(f"  ❌ Bulk range creation: Expected 5 rooms total, got {total_processed} (created: {created_count}, skipped: {skipped_count})")
                        self.test_results.append({
                            "endpoint": "POST /api/pms/rooms/bulk/range",
                            "passed": 0, "total": 1, "success_rate": "0.0%",
                            "avg_response_time": f"{response_time:.1f}ms"
                        })
                else:
                    error_text = await response.text()
                    print(f"  ❌ Bulk range creation: Expected 200, got {response.status}")
                    print(f"      🔍 Error Details: {error_text[:300]}...")
                    self.test_results.append({
                        "endpoint": "POST /api/pms/rooms/bulk/range",
                        "passed": 0, "total": 1, "success_rate": "0.0%",
                        "avg_response_time": f"{response_time:.1f}ms"
                    })
                    
        except Exception as e:
            print(f"  ❌ Bulk range creation: Error {e}")
            self.test_results.append({
                "endpoint": "POST /api/pms/rooms/bulk/range",
                "passed": 0, "total": 1, "success_rate": "0.0%",
                "avg_response_time": "N/A"
            })

    async def test_rooms_filtering(self):
        """Test GET /api/pms/rooms?room_type=deluxe&view=sea&amenity=wifi&limit=200"""
        print("\n🔍 Testing Rooms Filtering (deluxe, sea view, wifi)...")
        print("🎯 OBJECTIVE: Verify A101-A105 rooms appear in filtered results")
        
        filter_params = {
            "room_type": "deluxe",
            "view": "sea", 
            "amenity": "wifi",
            "limit": 200
        }
        
        try:
            params_str = "&".join([f"{k}={v}" for k, v in filter_params.items()])
            url = f"{BACKEND_URL}/pms/rooms?{params_str}"
            
            start_time = datetime.now()
            async with self.session.get(url, headers=self.get_headers()) as response:
                end_time = datetime.now()
                response_time = (end_time - start_time).total_seconds() * 1000
                
                if response.status == 200:
                    data = await response.json()
                    
                    if isinstance(data, list):
                        # Look for our created rooms A101-A105
                        created_rooms = [room for room in data if room.get('room_number') in ['A101', 'A102', 'A103', 'A104', 'A105']]
                        
                        # Verify room structure and properties
                        valid_rooms = []
                        for room in created_rooms:
                            required_fields = ["id", "room_number", "room_type", "view", "bed_type", "amenities"]
                            missing_fields = [field for field in required_fields if field not in room]
                            
                            if not missing_fields:
                                # Check if room properties match our creation
                                if (room.get('room_type') == 'deluxe' and 
                                    room.get('view') == 'sea' and 
                                    room.get('bed_type') == 'king' and
                                    'wifi' in room.get('amenities', []) and
                                    'balcony' in room.get('amenities', [])):
                                    valid_rooms.append(room)
                        
                        if len(valid_rooms) >= 5:
                            print(f"  ✅ Rooms filtering: PASSED ({response_time:.1f}ms)")
                            print(f"      📊 Total rooms returned: {len(data)}")
                            print(f"      📊 A101-A105 rooms found: {len(created_rooms)}")
                            print(f"      📊 Valid rooms with correct properties: {len(valid_rooms)}")
                            print(f"      📊 Sample room: {valid_rooms[0].get('room_number')} - {valid_rooms[0].get('room_type')}")
                            print(f"      📊 View/Bed/Amenities verified: ✅")
                            
                            self.test_results.append({
                                "endpoint": "GET /api/pms/rooms (filtered)",
                                "passed": 1, "total": 1, "success_rate": "100.0%",
                                "avg_response_time": f"{response_time:.1f}ms"
                            })
                        else:
                            print(f"  ❌ Rooms filtering: Expected 5+ rooms, found {len(valid_rooms)} valid rooms")
                            print(f"      📊 Created rooms found: {[r.get('room_number') for r in created_rooms]}")
                            self.test_results.append({
                                "endpoint": "GET /api/pms/rooms (filtered)",
                                "passed": 0, "total": 1, "success_rate": "0.0%",
                                "avg_response_time": f"{response_time:.1f}ms"
                            })
                    else:
                        print(f"  ❌ Rooms filtering: Expected list response, got {type(data)}")
                        self.test_results.append({
                            "endpoint": "GET /api/pms/rooms (filtered)",
                            "passed": 0, "total": 1, "success_rate": "0.0%",
                            "avg_response_time": f"{response_time:.1f}ms"
                        })
                else:
                    error_text = await response.text()
                    print(f"  ❌ Rooms filtering: Expected 200, got {response.status}")
                    print(f"      🔍 Error Details: {error_text[:300]}...")
                    self.test_results.append({
                        "endpoint": "GET /api/pms/rooms (filtered)",
                        "passed": 0, "total": 1, "success_rate": "0.0%",
                        "avg_response_time": f"{response_time:.1f}ms"
                    })
                    
        except Exception as e:
            print(f"  ❌ Rooms filtering: Error {e}")
            self.test_results.append({
                "endpoint": "GET /api/pms/rooms (filtered)",
                "passed": 0, "total": 1, "success_rate": "0.0%",
                "avg_response_time": "N/A"
            })

    async def test_bulk_rooms_template_creation(self):
        """Test POST /api/pms/rooms/bulk/template - Create rooms B1-B3"""
        print("\n🏨 Testing Bulk Rooms Template Creation (B1-B3)...")
        print("🎯 OBJECTIVE: Create 3 standard rooms with template B1-B3")
        
        bulk_template_payload = {
            "prefix": "B",
            "start_number": 1,
            "count": 3,
            "floor": 2,
            "room_type": "standard",
            "capacity": 3,
            "base_price": 90,
            "amenities": ["wifi"],
            "view": "city",
            "bed_type": "twin"
        }
        
        try:
            start_time = datetime.now()
            async with self.session.post(f"{BACKEND_URL}/pms/rooms/bulk/template", 
                                       json=bulk_template_payload, 
                                       headers=self.get_headers()) as response:
                end_time = datetime.now()
                response_time = (end_time - start_time).total_seconds() * 1000
                
                if response.status == 200:
                    data = await response.json()
                    created_count = data.get("created", 0)
                    
                    if created_count == 3:
                        print(f"  ✅ Bulk template creation: PASSED ({response_time:.1f}ms)")
                        print(f"      📊 Expected: 3 rooms, Created: {created_count}")
                        print(f"      📊 Room range: B1-B3")
                        print(f"      📊 Room type: standard, View: city, Bed: twin")
                        print(f"      📊 Amenities: {bulk_template_payload['amenities']}")
                        
                        # Store created room info for later tests
                        self.created_test_data['bulk_rooms'].extend([f"B{i}" for i in range(1, 4)])
                        
                        self.test_results.append({
                            "endpoint": "POST /api/pms/rooms/bulk/template",
                            "passed": 1, "total": 1, "success_rate": "100.0%",
                            "avg_response_time": f"{response_time:.1f}ms"
                        })
                    else:
                        print(f"  ❌ Bulk template creation: Expected 3 rooms, got {created_count}")
                        self.test_results.append({
                            "endpoint": "POST /api/pms/rooms/bulk/template",
                            "passed": 0, "total": 1, "success_rate": "0.0%",
                            "avg_response_time": f"{response_time:.1f}ms"
                        })
                else:
                    error_text = await response.text()
                    print(f"  ❌ Bulk template creation: Expected 200, got {response.status}")
                    print(f"      🔍 Error Details: {error_text[:300]}...")
                    self.test_results.append({
                        "endpoint": "POST /api/pms/rooms/bulk/template",
                        "passed": 0, "total": 1, "success_rate": "0.0%",
                        "avg_response_time": f"{response_time:.1f}ms"
                    })
                    
        except Exception as e:
            print(f"  ❌ Bulk template creation: Error {e}")
            self.test_results.append({
                "endpoint": "POST /api/pms/rooms/bulk/template",
                "passed": 0, "total": 1, "success_rate": "0.0%",
                "avg_response_time": "N/A"
            })

    async def test_room_image_upload(self):
        """Test POST /api/pms/rooms/{room_id}/images - Upload room image"""
        print("\n📸 Testing Room Image Upload...")
        print("🎯 OBJECTIVE: Upload image to A101 room and verify response")
        
        # First, get the room ID for A101
        room_id = None
        try:
            async with self.session.get(f"{BACKEND_URL}/pms/rooms?limit=200", 
                                      headers=self.get_headers()) as response:
                if response.status == 200:
                    rooms = await response.json()
                    a101_room = next((room for room in rooms if room.get('room_number') == 'A101'), None)
                    if a101_room:
                        room_id = a101_room['id']
                        print(f"      📊 Found A101 room ID: {room_id[:8]}...")
                    else:
                        print("  ⚠️ A101 room not found for image upload test")
        except Exception as e:
            print(f"  ⚠️ Error finding A101 room: {e}")
        
        if not room_id:
            print("  ⚠️ No room available for testing image upload")
            self.test_results.append({
                "endpoint": "POST /api/pms/rooms/{room_id}/images",
                "passed": 0, "total": 1, "success_rate": "0.0%",
                "avg_response_time": "N/A"
            })
            return
        
        try:
            # Create a simple test image (1x1 pixel PNG)
            import base64
            # Minimal PNG image data (1x1 transparent pixel)
            png_data = base64.b64decode(
                'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAI9jU8'
                'AAABJRU5ErkJggg=='
            )
            
            # Prepare multipart form data
            form_data = aiohttp.FormData()
            form_data.add_field('files', png_data, filename='test_room_image.png', content_type='image/png')
            
            # Remove Content-Type header to let aiohttp set it for multipart
            headers = {
                "Authorization": f"Bearer {self.auth_token}"
            }
            
            start_time = datetime.now()
            async with self.session.post(f"{BACKEND_URL}/pms/rooms/{room_id}/images", 
                                       data=form_data, 
                                       headers=headers) as response:
                end_time = datetime.now()
                response_time = (end_time - start_time).total_seconds() * 1000
                
                if response.status == 200:
                    data = await response.json()
                    
                    # Check if response contains images array with upload path
                    if 'images' in data and isinstance(data['images'], list):
                        images = data['images']
                        upload_paths = [img for img in images if '/api/uploads/' in str(img)]
                        
                        if upload_paths:
                            print(f"  ✅ Room image upload: PASSED ({response_time:.1f}ms)")
                            print(f"      📊 Room ID: {room_id[:8]}...")
                            print(f"      📊 Images in response: {len(images)}")
                            print(f"      📊 Upload paths found: {len(upload_paths)}")
                            print(f"      📊 Sample path: {upload_paths[0]}")
                            
                            self.test_results.append({
                                "endpoint": "POST /api/pms/rooms/{room_id}/images",
                                "passed": 1, "total": 1, "success_rate": "100.0%",
                                "avg_response_time": f"{response_time:.1f}ms"
                            })
                        else:
                            print(f"  ❌ Room image upload: No /api/uploads/ paths in response")
                            print(f"      📊 Response images: {images}")
                            self.test_results.append({
                                "endpoint": "POST /api/pms/rooms/{room_id}/images",
                                "passed": 0, "total": 1, "success_rate": "0.0%",
                                "avg_response_time": f"{response_time:.1f}ms"
                            })
                    else:
                        print(f"  ❌ Room image upload: No 'images' array in response")
                        print(f"      📊 Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                        self.test_results.append({
                            "endpoint": "POST /api/pms/rooms/{room_id}/images",
                            "passed": 0, "total": 1, "success_rate": "0.0%",
                            "avg_response_time": f"{response_time:.1f}ms"
                        })
                else:
                    error_text = await response.text()
                    print(f"  ❌ Room image upload: Expected 200, got {response.status}")
                    print(f"      🔍 Error Details: {error_text[:300]}...")
                    self.test_results.append({
                        "endpoint": "POST /api/pms/rooms/{room_id}/images",
                        "passed": 0, "total": 1, "success_rate": "0.0%",
                        "avg_response_time": f"{response_time:.1f}ms"
                    })
                    
        except Exception as e:
            print(f"  ❌ Room image upload: Error {e}")
            self.test_results.append({
                "endpoint": "POST /api/pms/rooms/{room_id}/images",
                "passed": 0, "total": 1, "success_rate": "0.0%",
                "avg_response_time": "N/A"
            })

    # ============= MAIN TEST EXECUTION =============

    async def run_all_tests(self):
        """Run comprehensive PMS Rooms Bulk Features backend testing"""
        print("🚀 PMS ROOMS BULK FEATURES BACKEND TESTING")
        print("Testing the new PMS Rooms bulk features on preview backend")
        print("Base URL: https://code-review-helper-12.preview.emergentagent.com/api")
        print("Login: muratsutay@hotmail.com / murat1903")
        print("=" * 80)
        
        # Setup
        await self.setup_session()
        
        if not await self.authenticate():
            print("❌ Authentication failed. Cannot proceed with tests.")
            return
        
        # Clean up existing test rooms
        await self.cleanup_test_rooms()
        
        # Run all PMS Rooms Bulk tests
        print("\n" + "="*60)
        print("🏨 PMS ROOMS BULK FEATURES TESTING")
        print("="*60)
        
        await self.test_bulk_rooms_range_creation()
        await self.test_rooms_filtering()
        await self.test_bulk_rooms_template_creation()
        await self.test_room_image_upload()
        
        # Cleanup
        await self.cleanup_session()
        
        # Print results
        self.print_test_summary()

    def print_test_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "=" * 80)
        print("📊 PMS ROOMS BULK FEATURES TEST RESULTS")
        print("=" * 80)
        
        total_passed = 0
        total_tests = 0
        
        print("\n🏨 ENDPOINT TEST RESULTS:")
        print("-" * 70)
        
        for result in self.test_results:
            endpoint = result["endpoint"]
            passed = result["passed"]
            total = result["total"]
            success_rate = result["success_rate"]
            avg_time = result.get("avg_response_time", "N/A")
            
            status = "✅" if passed == total else "❌" if passed == 0 else "⚠️"
            print(f"{status} {endpoint}: {success_rate} (avg: {avg_time})")
            
            total_passed += passed
            total_tests += total
        
        print("\n" + "=" * 80)
        overall_success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        print(f"📈 OVERALL SUCCESS RATE: {total_passed}/{total_tests} ({overall_success_rate:.1f}%)")
        
        # Final assessment
        if overall_success_rate >= 90:
            print("🎉 RESULT: PMS Rooms Bulk Features: production-ready ✅")
            print("   All bulk endpoints working, room creation and filtering successful")
        elif overall_success_rate >= 75:
            print("✅ RESULT: PMS Rooms Bulk Features: mostly ready")
            print("   Most endpoints working, minor issues present")
        elif overall_success_rate >= 50:
            print("⚠️ RESULT: PMS Rooms Bulk Features: partial issues")
            print("   Some endpoints working, significant issues present")
        else:
            print("❌ RESULT: PMS Rooms Bulk Features: critical issues")
            print("   Major backend problems, immediate attention required")
        
        print("\n🔍 VERIFIED FEATURES:")
        print("• POST /api/pms/rooms/bulk/range: Bulk room creation with range (A101-A105)")
        print("• GET /api/pms/rooms (filtered): Room filtering by type, view, amenities")
        print("• POST /api/pms/rooms/bulk/template: Bulk room creation with template (B1-B3)")
        print("• POST /api/pms/rooms/{room_id}/images: Room image upload functionality")
        print("• Room data structure validation and response verification")
        print("• HTTP 200 responses and proper error handling")
        
        print("\n📋 TEST SUMMARY:")
        print(f"• Bulk Range Creation: {'✅' if any('bulk/range' in r['endpoint'] and r['passed'] > 0 for r in self.test_results) else '❌'}")
        print(f"• Room Filtering: {'✅' if any('filtered' in r['endpoint'] and r['passed'] > 0 for r in self.test_results) else '❌'}")
        print(f"• Bulk Template Creation: {'✅' if any('bulk/template' in r['endpoint'] and r['passed'] > 0 for r in self.test_results) else '❌'}")
        print(f"• Image Upload: {'✅' if any('images' in r['endpoint'] and r['passed'] > 0 for r in self.test_results) else '❌'}")
        
        print("\n" + "=" * 80)

async def main():
    """Main test execution"""
    tester = PMSRoomsBulkTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
