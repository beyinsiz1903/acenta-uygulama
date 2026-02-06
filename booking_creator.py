#!/usr/bin/env python3
"""
Create a test booking for voucher testing
"""
import requests
import sys
import uuid
from datetime import datetime, timedelta

class BookingCreator:
    def __init__(self, base_url="https://enterprise-ops-8.preview.emergentagent.com"):
        self.base_url = base_url
        self.agency_token = None
        self.hotel_token = None
        self.booking_id = None

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def run_test(self, name, method, endpoint, expected_status, data=None, headers_override=None, token=None):
        """Run a single API test with specific token"""
        url = f"{self.base_url}/{endpoint}"
        headers = headers_override or {'Content-Type': 'application/json'}
        
        if token:
            headers['Authorization'] = f'Bearer {token}'

        self.log(f"🔍 {name}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=15)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=15)
            else:
                raise ValueError(f"Unsupported method: {method}")

            if isinstance(expected_status, list):
                status_ok = response.status_code in expected_status
            else:
                status_ok = response.status_code == expected_status

            if status_ok:
                self.log(f"✅ PASSED - Status: {response.status_code}")
                
                if 'application/json' in response.headers.get('content-type', ''):
                    return True, response.json()
                else:
                    return True, response.text
            else:
                self.log(f"❌ FAILED - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json()
                    self.log(f"   Response: {error_detail}")
                except:
                    self.log(f"   Response: {response.text[:200]}")
                return False, None
                
        except Exception as e:
            self.log(f"❌ FAILED - Exception: {str(e)}")
            return False, None

    def login_agency(self):
        """Login as agency admin"""
        login_data = {
            "email": "agency1@demo.test",
            "password": "agency123"
        }
        
        success, response = self.run_test(
            "Agency Login",
            "POST",
            "api/auth/login",
            200,
            data=login_data
        )
        
        if success:
            self.agency_token = response.get('access_token')
            return True
        return False

    def login_hotel(self):
        """Login as hotel admin"""
        login_data = {
            "email": "hoteladmin@acenta.test",
            "password": "admin123"
        }
        
        success, response = self.run_test(
            "Hotel Login",
            "POST",
            "api/auth/login",
            200,
            data=login_data
        )
        
        if success:
            self.hotel_token = response.get('access_token')
            return True
        return False

    def check_existing_bookings(self):
        """Check for existing bookings"""
        # Check agency bookings
        success, response = self.run_test(
            "Get Agency Bookings",
            "GET",
            "api/agency/bookings",
            200,
            token=self.agency_token
        )
        
        if success and isinstance(response, list) and len(response) > 0:
            self.booking_id = response[0].get('id')
            self.log(f"✅ Found existing agency booking: {self.booking_id}")
            return True
        
        # Check hotel bookings
        success, response = self.run_test(
            "Get Hotel Bookings",
            "GET",
            "api/hotel/bookings",
            200,
            token=self.hotel_token
        )
        
        if success and isinstance(response, list) and len(response) > 0:
            self.booking_id = response[0].get('id')
            self.log(f"✅ Found existing hotel booking: {self.booking_id}")
            return True
        
        return False

    def create_booking_via_seed(self):
        """Try to create a booking by directly inserting into database via API"""
        # This is a workaround - we'll create a mock booking entry
        # Since we can't directly access the database, we'll use a known booking ID pattern
        
        # Let's try to use the admin API to see if we can create test data
        admin_login_data = {
            "email": "admin@acenta.test",
            "password": "admin123"
        }
        
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "api/auth/login",
            200,
            data=admin_login_data
        )
        
        if success:
            admin_token = response.get('access_token')
            self.log(f"✅ Admin login successful")
            
            # Check if there are any agencies and hotels
            success, agencies = self.run_test(
                "Get Agencies",
                "GET",
                "api/admin/agencies",
                200,
                token=admin_token
            )
            
            success, hotels = self.run_test(
                "Get Hotels",
                "GET",
                "api/admin/hotels",
                200,
                token=admin_token
            )
            
            if success:
                self.log(f"Found {len(agencies)} agencies and {len(hotels)} hotels")
                return False
        
        return False

    def run(self):
        """Main execution"""
        self.log("🚀 Checking for existing bookings or creating test booking")
        
        # Login to both accounts
        if not self.login_agency():
            self.log("❌ Agency login failed")
            return None
        
        if not self.login_hotel():
            self.log("❌ Hotel login failed")
            return None
        
        # Check for existing bookings
        if self.check_existing_bookings():
            return self.booking_id
        
        # Try to create via admin
        self.create_booking_via_seed()
        
        return None

if __name__ == "__main__":
    creator = BookingCreator()
    booking_id = creator.run()
    if booking_id:
        print(f"BOOKING_ID={booking_id}")
    else:
        print("NO_BOOKING_FOUND")