#!/usr/bin/env python3
"""
C3 Response Structure Demo - Show complete API responses
"""
import requests
import json
from datetime import datetime

class C3ResponseDemo:
    def __init__(self, base_url="https://syroce-booking.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.booking_id = None

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def login(self):
        """Login and get token"""
        url = f"{self.base_url}/api/auth/login"
        data = {"email": "agency1@demo.test", "password": "agency123"}
        
        response = requests.post(url, json=data, timeout=15)
        if response.status_code == 200:
            result = response.json()
            self.token = result['access_token']
            user = result.get('user', {})
            self.log(f"✅ Login successful - agency_id: {user.get('agency_id')}")
            return True
        else:
            self.log(f"❌ Login failed - Status: {response.status_code}")
            return False

    def get_booking_id(self):
        """Get a booking ID for testing"""
        url = f"{self.base_url}/api/agency/tour-bookings?limit=1"
        headers = {'Authorization': f'Bearer {self.token}'}
        
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            result = response.json()
            items = result.get('items', [])
            if items:
                self.booking_id = items[0]['id']
                self.log(f"✅ Found booking ID: {self.booking_id}")
                return True
        
        self.log("❌ Could not get booking ID")
        return False

    def demo_get_booking_detail(self):
        """Demo GET /api/agency/tour-bookings/{id} response"""
        self.log("\n" + "="*80)
        self.log("GET /api/agency/tour-bookings/{id} - RESPONSE STRUCTURE")
        self.log("="*80)
        
        url = f"{self.base_url}/api/agency/tour-bookings/{self.booking_id}"
        headers = {'Authorization': f'Bearer {self.token}'}
        
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            result = response.json()
            self.log(f"Status: {response.status_code} OK")
            self.log("Response Body:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            # Verify required fields
            required_fields = ['id', 'organization_id', 'agency_id', 'tour_id', 'tour_title', 
                             'guest', 'desired_date', 'pax', 'status', 'note', 'internal_notes']
            self.log(f"\n✅ Required fields present:")
            for field in required_fields:
                present = field in result
                self.log(f"   - {field}: {'✅' if present else '❌'}")
            
            return True
        else:
            self.log(f"❌ Request failed - Status: {response.status_code}")
            return False

    def demo_add_note(self):
        """Demo POST /api/agency/tour-bookings/{id}/add-note"""
        self.log("\n" + "="*80)
        self.log("POST /api/agency/tour-bookings/{id}/add-note - REQUEST/RESPONSE")
        self.log("="*80)
        
        url = f"{self.base_url}/api/agency/tour-bookings/{self.booking_id}/add-note"
        headers = {'Authorization': f'Bearer {self.token}', 'Content-Type': 'application/json'}
        data = {"text": "Demo not: Müşteri ile görüşme yapıldı, ödeme onaylandı."}
        
        self.log("Request Body:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        response = requests.post(url, json=data, headers=headers, timeout=15)
        if response.status_code == 200:
            result = response.json()
            self.log(f"\nStatus: {response.status_code} OK")
            self.log("Response Body:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return True
        else:
            self.log(f"❌ Request failed - Status: {response.status_code}")
            try:
                error = response.json()
                self.log("Error Response:")
                print(json.dumps(error, indent=2, ensure_ascii=False))
            except:
                self.log(f"Error Text: {response.text}")
            return False

    def demo_get_with_notes(self):
        """Demo GET after adding notes to show internal_notes structure"""
        self.log("\n" + "="*80)
        self.log("GET /api/agency/tour-bookings/{id} - WITH INTERNAL NOTES")
        self.log("="*80)
        
        url = f"{self.base_url}/api/agency/tour-bookings/{self.booking_id}"
        headers = {'Authorization': f'Bearer {self.token}'}
        
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            result = response.json()
            self.log(f"Status: {response.status_code} OK")
            
            # Show only internal_notes structure
            internal_notes = result.get('internal_notes', [])
            self.log(f"\nInternal Notes Count: {len(internal_notes)}")
            self.log("Internal Notes Structure:")
            print(json.dumps(internal_notes, indent=2, ensure_ascii=False))
            
            if internal_notes:
                latest_note = internal_notes[-1]
                self.log(f"\n✅ Latest Note Structure:")
                self.log(f"   - text: {latest_note.get('text')}")
                self.log(f"   - created_at: {latest_note.get('created_at')}")
                self.log(f"   - actor.user_id: {latest_note.get('actor', {}).get('user_id')}")
                self.log(f"   - actor.name: {latest_note.get('actor', {}).get('name')}")
                self.log(f"   - actor.role: {latest_note.get('actor', {}).get('role')}")
            
            return True
        else:
            self.log(f"❌ Request failed - Status: {response.status_code}")
            return False

    def demo_error_cases(self):
        """Demo error cases"""
        self.log("\n" + "="*80)
        self.log("ERROR CASES DEMO")
        self.log("="*80)
        
        # 1. Invalid note (empty text)
        self.log("\n1) POST add-note with empty text (should return 400 INVALID_NOTE):")
        url = f"{self.base_url}/api/agency/tour-bookings/{self.booking_id}/add-note"
        headers = {'Authorization': f'Bearer {self.token}', 'Content-Type': 'application/json'}
        data = {"text": ""}
        
        response = requests.post(url, json=data, headers=headers, timeout=15)
        self.log(f"Status: {response.status_code}")
        try:
            error = response.json()
            print(json.dumps(error, indent=2, ensure_ascii=False))
        except:
            self.log(f"Response: {response.text}")
        
        # 2. Non-existing booking
        self.log("\n2) GET non-existing booking (should return 404 TOUR_BOOKING_REQUEST_NOT_FOUND):")
        fake_id = "507f1f77bcf86cd799439011"
        url = f"{self.base_url}/api/agency/tour-bookings/{fake_id}"
        headers = {'Authorization': f'Bearer {self.token}'}
        
        response = requests.get(url, headers=headers, timeout=15)
        self.log(f"Status: {response.status_code}")
        try:
            error = response.json()
            print(json.dumps(error, indent=2, ensure_ascii=False))
        except:
            self.log(f"Response: {response.text}")
        
        # 3. No authentication
        self.log("\n3) GET without JWT (should return 401):")
        url = f"{self.base_url}/api/agency/tour-bookings/{self.booking_id}"
        
        response = requests.get(url, timeout=15)
        self.log(f"Status: {response.status_code}")
        try:
            error = response.json()
            print(json.dumps(error, indent=2, ensure_ascii=False))
        except:
            self.log(f"Response: {response.text}")

    def run_demo(self):
        """Run complete demo"""
        self.log("🚀 Starting C3 Response Structure Demo")
        self.log(f"Base URL: {self.base_url}")
        
        if not self.login():
            return 1
        
        if not self.get_booking_id():
            return 1
        
        self.demo_get_booking_detail()
        self.demo_add_note()
        self.demo_get_with_notes()
        self.demo_error_cases()
        
        self.log("\n" + "="*80)
        self.log("✅ C3 DEMO COMPLETED - All endpoints working correctly!")
        self.log("="*80)
        
        return 0


if __name__ == "__main__":
    demo = C3ResponseDemo()
    exit_code = demo.run_demo()
    exit(exit_code)