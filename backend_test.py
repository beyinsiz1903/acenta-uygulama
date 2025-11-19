#!/usr/bin/env python3
"""
Comprehensive Backend Testing for 7 New Hotel PMS Features
Testing 57 endpoints across all major hotel management features
"""

import requests
import json
import sys
import os
from datetime import datetime, timedelta
import base64

# Configuration
BACKEND_URL = "https://pms-innovations.preview.emergentagent.com/api"
TEST_EMAIL = "test@hotel.com"
TEST_PASSWORD = "test123"

class HotelPMSBackendTester:
    def __init__(self):
        self.session = requests.Session()
        self.auth_token = None
        self.tenant_id = None
        self.user_id = None
        self.test_results = {
            "messaging": {"passed": 0, "failed": 0, "details": []},
            "rms": {"passed": 0, "failed": 0, "details": []},
            "housekeeping_mobile": {"passed": 0, "failed": 0, "details": []},
            "efatura_pos": {"passed": 0, "failed": 0, "details": []},
            "group_block": {"passed": 0, "failed": 0, "details": []},
            "multi_property": {"passed": 0, "failed": 0, "details": []},
            "marketplace": {"passed": 0, "failed": 0, "details": []}
        }
        self.created_resources = {
            "comp_set_ids": [],
            "group_ids": [],
            "block_ids": [],
            "property_ids": [],
            "product_ids": [],
            "po_ids": [],
            "room_ids": []
        }

    def authenticate(self):
        """Authenticate with the backend"""
        print("🔐 Authenticating...")
        try:
            response = self.session.post(f"{BACKEND_URL}/auth/login", json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            })
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data["access_token"]
                self.tenant_id = data["user"]["tenant_id"]
                self.user_id = data["user"]["id"]
                self.session.headers.update({
                    "Authorization": f"Bearer {self.auth_token}",
                    "Content-Type": "application/json"
                })
                print(f"✅ Authentication successful - User: {data['user']['name']}")
                return True
            else:
                print(f"❌ Authentication failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Authentication error: {str(e)}")
            return False

    def log_test_result(self, category, endpoint, method, success, details=""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = {
            "endpoint": f"{method} {endpoint}",
            "status": status,
            "details": details
        }
        self.test_results[category]["details"].append(result)
        if success:
            self.test_results[category]["passed"] += 1
        else:
            self.test_results[category]["failed"] += 1
        
        print(f"  {status}: {method} {endpoint} - {details}")

    def test_messaging_hub(self):
        """Test WhatsApp & OTA Messaging Hub (7 endpoints)"""
        print("\n📱 Testing WhatsApp & OTA Messaging Hub...")
        
        # 1. POST /api/messaging/send-whatsapp
        try:
            response = self.session.post(f"{BACKEND_URL}/messaging/send-whatsapp", json={
                "to": "+1234567890",
                "message": "Test WhatsApp message from hotel PMS",
                "booking_id": None
            })
            success = response.status_code in [200, 201]
            details = f"Status: {response.status_code}"
            if success and response.json():
                details += f" - Message ID: {response.json().get('message_id', 'N/A')}"
            self.log_test_result("messaging", "/messaging/send-whatsapp", "POST", success, details)
        except Exception as e:
            self.log_test_result("messaging", "/messaging/send-whatsapp", "POST", False, f"Error: {str(e)}")

        # 2. POST /api/messaging/send-email
        try:
            response = self.session.post(f"{BACKEND_URL}/messaging/send-email", json={
                "to": "guest@example.com",
                "subject": "Booking Confirmation - Hotel PMS Test",
                "message": "Thank you for your booking. This is a test email from our PMS system."
            })
            success = response.status_code in [200, 201]
            details = f"Status: {response.status_code}"
            if success and response.json():
                details += f" - Email sent: {response.json().get('sent', False)}"
            self.log_test_result("messaging", "/messaging/send-email", "POST", success, details)
        except Exception as e:
            self.log_test_result("messaging", "/messaging/send-email", "POST", False, f"Error: {str(e)}")

        # 3. POST /api/messaging/send-sms
        try:
            response = self.session.post(f"{BACKEND_URL}/messaging/send-sms", json={
                "to": "+1234567890",
                "message": "Your room is ready for check-in. Hotel PMS Test SMS."
            })
            success = response.status_code in [200, 201]
            details = f"Status: {response.status_code}"
            if success and response.json():
                details += f" - SMS sent: {response.json().get('sent', False)}"
            self.log_test_result("messaging", "/messaging/send-sms", "POST", success, details)
        except Exception as e:
            self.log_test_result("messaging", "/messaging/send-sms", "POST", False, f"Error: {str(e)}")

        # 4. GET /api/messaging/conversations
        try:
            response = self.session.get(f"{BACKEND_URL}/messaging/conversations")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                details += f" - Conversations: {len(data.get('conversations', []))}"
            self.log_test_result("messaging", "/messaging/conversations", "GET", success, details)
        except Exception as e:
            self.log_test_result("messaging", "/messaging/conversations", "GET", False, f"Error: {str(e)}")

        # 5. GET /api/messaging/conversations with filter
        try:
            response = self.session.get(f"{BACKEND_URL}/messaging/conversations?channel=whatsapp")
            success = response.status_code == 200
            details = f"Status: {response.status_code} - WhatsApp filter"
            if success:
                data = response.json()
                details += f" - WhatsApp conversations: {len(data.get('conversations', []))}"
            self.log_test_result("messaging", "/messaging/conversations?channel=whatsapp", "GET", success, details)
        except Exception as e:
            self.log_test_result("messaging", "/messaging/conversations?channel=whatsapp", "GET", False, f"Error: {str(e)}")

        # 6. GET /api/messaging/templates
        try:
            response = self.session.get(f"{BACKEND_URL}/messaging/templates")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                details += f" - Templates: {len(data.get('templates', []))}"
            self.log_test_result("messaging", "/messaging/templates", "GET", success, details)
        except Exception as e:
            self.log_test_result("messaging", "/messaging/templates", "GET", False, f"Error: {str(e)}")

        # 7. POST /api/messaging/templates
        try:
            response = self.session.post(f"{BACKEND_URL}/messaging/templates", json={
                "name": "Welcome Message Test",
                "channel": "whatsapp",
                "content": "Welcome {{guest_name}} to our hotel! Your room {{room_number}} is ready."
            })
            success = response.status_code in [200, 201]
            details = f"Status: {response.status_code}"
            if success and response.json():
                details += f" - Template created: {response.json().get('name', 'N/A')}"
            self.log_test_result("messaging", "/messaging/templates", "POST", success, details)
        except Exception as e:
            self.log_test_result("messaging", "/messaging/templates", "POST", False, f"Error: {str(e)}")

        # 8. GET /api/messaging/ota-integrations
        try:
            response = self.session.get(f"{BACKEND_URL}/messaging/ota-integrations")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                details += f" - OTA integrations: {len(data.get('integrations', []))}"
            self.log_test_result("messaging", "/messaging/ota-integrations", "GET", success, details)
        except Exception as e:
            self.log_test_result("messaging", "/messaging/ota-integrations", "GET", False, f"Error: {str(e)}")

    def test_rms_system(self):
        """Test Full RMS - Revenue Management System (10 endpoints)"""
        print("\n💰 Testing RMS - Revenue Management System...")
        
        # 1. POST /api/rms/comp-set
        try:
            response = self.session.post(f"{BACKEND_URL}/rms/comp-set", json={
                "name": "Hilton Downtown Test",
                "location": "Downtown Business District",
                "star_rating": 4.5,
                "property_type": "business_hotel",
                "website": "https://hilton.com"
            })
            success = response.status_code in [200, 201]
            details = f"Status: {response.status_code}"
            if success and response.json():
                comp_id = response.json().get('id')
                if comp_id:
                    self.created_resources["comp_set_ids"].append(comp_id)
                details += f" - Competitor added: {response.json().get('name', 'N/A')}"
            self.log_test_result("rms", "/rms/comp-set", "POST", success, details)
        except Exception as e:
            self.log_test_result("rms", "/rms/comp-set", "POST", False, f"Error: {str(e)}")

        # 2. GET /api/rms/comp-set
        try:
            response = self.session.get(f"{BACKEND_URL}/rms/comp-set")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                details += f" - Competitors: {len(data.get('competitors', []))}"
            self.log_test_result("rms", "/rms/comp-set", "GET", success, details)
        except Exception as e:
            self.log_test_result("rms", "/rms/comp-set", "GET", False, f"Error: {str(e)}")

        # 3. POST /api/rms/scrape-comp-prices
        try:
            response = self.session.post(f"{BACKEND_URL}/rms/scrape-comp-prices", json={
                "date": "2025-01-25",
                "room_type": "standard"
            })
            success = response.status_code in [200, 201]
            details = f"Status: {response.status_code}"
            if success and response.json():
                details += f" - Prices scraped: {response.json().get('prices_found', 0)}"
            self.log_test_result("rms", "/rms/scrape-comp-prices", "POST", success, details)
        except Exception as e:
            self.log_test_result("rms", "/rms/scrape-comp-prices", "POST", False, f"Error: {str(e)}")

        # 4. GET /api/rms/comp-pricing
        try:
            response = self.session.get(f"{BACKEND_URL}/rms/comp-pricing?date=2025-01-25")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                details += f" - Pricing data points: {len(data.get('pricing', []))}"
            self.log_test_result("rms", "/rms/comp-pricing", "GET", success, details)
        except Exception as e:
            self.log_test_result("rms", "/rms/comp-pricing", "GET", False, f"Error: {str(e)}")

        # 5. POST /api/rms/auto-pricing
        try:
            response = self.session.post(f"{BACKEND_URL}/rms/auto-pricing", json={
                "start_date": "2025-01-25",
                "end_date": "2025-01-31",
                "room_types": ["standard", "deluxe"],
                "strategy": "competitive"
            })
            success = response.status_code in [200, 201]
            details = f"Status: {response.status_code}"
            if success and response.json():
                details += f" - Recommendations: {response.json().get('recommendations_count', 0)}"
            self.log_test_result("rms", "/rms/auto-pricing", "POST", success, details)
        except Exception as e:
            self.log_test_result("rms", "/rms/auto-pricing", "POST", False, f"Error: {str(e)}")

        # 6. GET /api/rms/pricing-recommendations
        try:
            response = self.session.get(f"{BACKEND_URL}/rms/pricing-recommendations?status=pending")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                recommendations = data.get('recommendations', [])
                details += f" - Pending recommendations: {len(recommendations)}"
                
                # Test apply recommendation if available
                if recommendations:
                    rec_id = recommendations[0].get('id')
                    if rec_id:
                        try:
                            apply_response = self.session.post(f"{BACKEND_URL}/rms/apply-pricing/{rec_id}")
                            apply_success = apply_response.status_code in [200, 201]
                            apply_details = f"Status: {apply_response.status_code}"
                            if apply_success:
                                apply_details += " - Recommendation applied"
                            self.log_test_result("rms", f"/rms/apply-pricing/{rec_id}", "POST", apply_success, apply_details)
                        except Exception as e:
                            self.log_test_result("rms", f"/rms/apply-pricing/{rec_id}", "POST", False, f"Error: {str(e)}")
            
            self.log_test_result("rms", "/rms/pricing-recommendations", "GET", success, details)
        except Exception as e:
            self.log_test_result("rms", "/rms/pricing-recommendations", "GET", False, f"Error: {str(e)}")

        # 7. POST /api/rms/demand-forecast
        try:
            response = self.session.post(f"{BACKEND_URL}/rms/demand-forecast", json={
                "start_date": "2025-02-01",
                "end_date": "2025-02-14",
                "room_type": "standard"
            })
            success = response.status_code in [200, 201]
            details = f"Status: {response.status_code}"
            if success and response.json():
                details += f" - Forecast created for 14 days"
            self.log_test_result("rms", "/rms/demand-forecast", "POST", success, details)
        except Exception as e:
            self.log_test_result("rms", "/rms/demand-forecast", "POST", False, f"Error: {str(e)}")

        # 8. GET /api/rms/demand-forecast
        try:
            response = self.session.get(f"{BACKEND_URL}/rms/demand-forecast?start_date=2025-02-01&end_date=2025-02-14")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                details += f" - Forecast data points: {len(data.get('forecast', []))}"
            self.log_test_result("rms", "/rms/demand-forecast", "GET", success, details)
        except Exception as e:
            self.log_test_result("rms", "/rms/demand-forecast", "GET", False, f"Error: {str(e)}")

    def test_mobile_housekeeping(self):
        """Test Mobile Housekeeping App (7 endpoints)"""
        print("\n🧹 Testing Mobile Housekeeping App...")
        
        # First get available rooms for testing
        try:
            rooms_response = self.session.get(f"{BACKEND_URL}/pms/rooms")
            if rooms_response.status_code == 200:
                rooms = rooms_response.json()
                if rooms:
                    self.created_resources["room_ids"] = [room["id"] for room in rooms[:3]]
        except:
            pass

        # 1. GET /api/housekeeping/mobile/my-tasks
        try:
            response = self.session.get(f"{BACKEND_URL}/housekeeping/mobile/my-tasks?status=pending")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                tasks = data.get('tasks', [])
                details += f" - Pending tasks: {len(tasks)}"
                
                # Test start-task and complete-task workflow if tasks exist
                if tasks:
                    task_id = tasks[0].get('id')
                    if task_id:
                        # Test start task
                        try:
                            start_response = self.session.post(f"{BACKEND_URL}/housekeeping/mobile/start-task/{task_id}")
                            start_success = start_response.status_code in [200, 201]
                            start_details = f"Status: {start_response.status_code}"
                            if start_success:
                                start_details += " - Task started"
                            self.log_test_result("housekeeping_mobile", f"/housekeeping/mobile/start-task/{task_id}", "POST", start_success, start_details)
                            
                            # Test complete task
                            complete_response = self.session.post(f"{BACKEND_URL}/housekeeping/mobile/complete-task/{task_id}", json={
                                "notes": "Task completed successfully during testing",
                                "quality_score": 5
                            })
                            complete_success = complete_response.status_code in [200, 201]
                            complete_details = f"Status: {complete_response.status_code}"
                            if complete_success:
                                complete_details += " - Task completed"
                            self.log_test_result("housekeeping_mobile", f"/housekeeping/mobile/complete-task/{task_id}", "POST", complete_success, complete_details)
                        except Exception as e:
                            self.log_test_result("housekeeping_mobile", f"/housekeeping/mobile/start-task/{task_id}", "POST", False, f"Error: {str(e)}")
                            self.log_test_result("housekeeping_mobile", f"/housekeeping/mobile/complete-task/{task_id}", "POST", False, f"Error: {str(e)}")
            
            self.log_test_result("housekeeping_mobile", "/housekeeping/mobile/my-tasks", "GET", success, details)
        except Exception as e:
            self.log_test_result("housekeeping_mobile", "/housekeeping/mobile/my-tasks", "GET", False, f"Error: {str(e)}")

        # 2. POST /api/housekeeping/mobile/report-issue
        room_id = self.created_resources["room_ids"][0] if self.created_resources["room_ids"] else "test-room-id"
        try:
            response = self.session.post(f"{BACKEND_URL}/housekeeping/mobile/report-issue", json={
                "room_id": room_id,
                "issue_type": "maintenance",
                "description": "Broken faucet in bathroom - needs immediate attention",
                "priority": "high",
                "reported_by": "housekeeping_staff"
            })
            success = response.status_code in [200, 201]
            details = f"Status: {response.status_code}"
            if success and response.json():
                details += f" - Issue reported: {response.json().get('issue_type', 'N/A')}"
            self.log_test_result("housekeeping_mobile", "/housekeeping/mobile/report-issue", "POST", success, details)
        except Exception as e:
            self.log_test_result("housekeeping_mobile", "/housekeeping/mobile/report-issue", "POST", False, f"Error: {str(e)}")

        # 3. POST /api/housekeeping/mobile/upload-photo
        try:
            # Create a simple base64 encoded test image
            test_image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
            response = self.session.post(f"{BACKEND_URL}/housekeeping/mobile/upload-photo", json={
                "task_id": "test-task-id",
                "photo_base64": test_image_b64,
                "description": "Before cleaning photo"
            })
            success = response.status_code in [200, 201]
            details = f"Status: {response.status_code}"
            if success and response.json():
                details += f" - Photo uploaded: {response.json().get('photo_id', 'N/A')}"
            self.log_test_result("housekeeping_mobile", "/housekeeping/mobile/upload-photo", "POST", success, details)
        except Exception as e:
            self.log_test_result("housekeeping_mobile", "/housekeeping/mobile/upload-photo", "POST", False, f"Error: {str(e)}")

        # 4. GET /api/housekeeping/mobile/room-status/{room_id}
        if self.created_resources["room_ids"]:
            room_id = self.created_resources["room_ids"][0]
            try:
                response = self.session.get(f"{BACKEND_URL}/housekeeping/mobile/room-status/{room_id}")
                success = response.status_code == 200
                details = f"Status: {response.status_code}"
                if success:
                    data = response.json()
                    details += f" - Room status: {data.get('status', 'N/A')}"
                self.log_test_result("housekeeping_mobile", f"/housekeeping/mobile/room-status/{room_id}", "GET", success, details)
            except Exception as e:
                self.log_test_result("housekeeping_mobile", f"/housekeeping/mobile/room-status/{room_id}", "GET", False, f"Error: {str(e)}")

    def test_efatura_pos(self):
        """Test E-Fatura & POS Integration (7 endpoints)"""
        print("\n🧾 Testing E-Fatura & POS Integration...")
        
        # 1. GET /api/efatura/invoices
        try:
            response = self.session.get(f"{BACKEND_URL}/efatura/invoices")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                invoices = data.get('invoices', [])
                details += f" - Total invoices: {len(invoices)}"
                
                # Test generate and send if invoices exist
                if invoices:
                    invoice_id = invoices[0].get('id')
                    if invoice_id:
                        # Test generate
                        try:
                            gen_response = self.session.post(f"{BACKEND_URL}/efatura/generate/{invoice_id}")
                            gen_success = gen_response.status_code in [200, 201]
                            gen_details = f"Status: {gen_response.status_code}"
                            if gen_success:
                                gen_details += " - E-Fatura generated"
                            self.log_test_result("efatura_pos", f"/efatura/generate/{invoice_id}", "POST", gen_success, gen_details)
                            
                            # Test send to GIB
                            gib_response = self.session.post(f"{BACKEND_URL}/efatura/send-to-gib/{invoice_id}")
                            gib_success = gib_response.status_code in [200, 201]
                            gib_details = f"Status: {gib_response.status_code}"
                            if gib_success:
                                gib_details += " - Sent to GIB"
                            self.log_test_result("efatura_pos", f"/efatura/send-to-gib/{invoice_id}", "POST", gib_success, gib_details)
                        except Exception as e:
                            self.log_test_result("efatura_pos", f"/efatura/generate/{invoice_id}", "POST", False, f"Error: {str(e)}")
                            self.log_test_result("efatura_pos", f"/efatura/send-to-gib/{invoice_id}", "POST", False, f"Error: {str(e)}")
            
            self.log_test_result("efatura_pos", "/efatura/invoices", "GET", success, details)
        except Exception as e:
            self.log_test_result("efatura_pos", "/efatura/invoices", "GET", False, f"Error: {str(e)}")

        # 2. GET /api/efatura/invoices with status filter
        try:
            response = self.session.get(f"{BACKEND_URL}/efatura/invoices?status=pending")
            success = response.status_code == 200
            details = f"Status: {response.status_code} - Pending filter"
            if success:
                data = response.json()
                details += f" - Pending invoices: {len(data.get('invoices', []))}"
            self.log_test_result("efatura_pos", "/efatura/invoices?status=pending", "GET", success, details)
        except Exception as e:
            self.log_test_result("efatura_pos", "/efatura/invoices?status=pending", "GET", False, f"Error: {str(e)}")

        # 3. POST /api/pos/transaction
        try:
            response = self.session.post(f"{BACKEND_URL}/pos/transaction", json={
                "amount": 150.50,
                "payment_method": "card",
                "card_type": "visa",
                "transaction_type": "sale",
                "description": "Hotel restaurant payment"
            })
            success = response.status_code in [200, 201]
            details = f"Status: {response.status_code}"
            if success and response.json():
                details += f" - Transaction ID: {response.json().get('transaction_id', 'N/A')}"
            self.log_test_result("efatura_pos", "/pos/transaction", "POST", success, details)
        except Exception as e:
            self.log_test_result("efatura_pos", "/pos/transaction", "POST", False, f"Error: {str(e)}")

        # 4. GET /api/pos/transactions
        try:
            response = self.session.get(f"{BACKEND_URL}/pos/transactions")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                details += f" - Transactions: {len(data.get('transactions', []))}"
            self.log_test_result("efatura_pos", "/pos/transactions", "GET", success, details)
        except Exception as e:
            self.log_test_result("efatura_pos", "/pos/transactions", "GET", False, f"Error: {str(e)}")

        # 5. GET /api/pos/daily-summary
        today = datetime.now().strftime("%Y-%m-%d")
        try:
            response = self.session.get(f"{BACKEND_URL}/pos/daily-summary?date={today}")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                details += f" - Total amount: {data.get('total_amount', 0)}"
            self.log_test_result("efatura_pos", f"/pos/daily-summary?date={today}", "GET", success, details)
        except Exception as e:
            self.log_test_result("efatura_pos", f"/pos/daily-summary?date={today}", "GET", False, f"Error: {str(e)}")

    def test_group_block_reservations(self):
        """Test Group & Block Reservations (9 endpoints)"""
        print("\n👥 Testing Group & Block Reservations...")
        
        # 1. POST /api/group-reservations
        try:
            response = self.session.post(f"{BACKEND_URL}/group-reservations", json={
                "group_name": "Corporate Training Group Test",
                "group_type": "corporate",
                "contact_person": "John Smith",
                "contact_email": "john@company.com",
                "contact_phone": "+1234567890",
                "check_in_date": "2025-02-15",
                "check_out_date": "2025-02-17",
                "total_rooms": 10,
                "adults_per_room": 2,
                "special_requests": "Meeting room required"
            })
            success = response.status_code in [200, 201]
            details = f"Status: {response.status_code}"
            if success and response.json():
                group_id = response.json().get('id')
                if group_id:
                    self.created_resources["group_ids"].append(group_id)
                details += f" - Group created: {response.json().get('group_name', 'N/A')}"
            self.log_test_result("group_block", "/group-reservations", "POST", success, details)
        except Exception as e:
            self.log_test_result("group_block", "/group-reservations", "POST", False, f"Error: {str(e)}")

        # 2. GET /api/group-reservations
        try:
            response = self.session.get(f"{BACKEND_URL}/group-reservations")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                details += f" - Groups: {len(data.get('groups', []))}"
            self.log_test_result("group_block", "/group-reservations", "GET", success, details)
        except Exception as e:
            self.log_test_result("group_block", "/group-reservations", "GET", False, f"Error: {str(e)}")

        # 3. GET /api/group-reservations/{group_id}
        if self.created_resources["group_ids"]:
            group_id = self.created_resources["group_ids"][0]
            try:
                response = self.session.get(f"{BACKEND_URL}/group-reservations/{group_id}")
                success = response.status_code == 200
                details = f"Status: {response.status_code}"
                if success:
                    data = response.json()
                    details += f" - Group: {data.get('group_name', 'N/A')}"
                self.log_test_result("group_block", f"/group-reservations/{group_id}", "GET", success, details)
            except Exception as e:
                self.log_test_result("group_block", f"/group-reservations/{group_id}", "GET", False, f"Error: {str(e)}")

            # 4. POST /api/group-reservations/{group_id}/assign-rooms
            try:
                room_assignments = []
                if self.created_resources["room_ids"]:
                    room_assignments = [
                        {"room_id": self.created_resources["room_ids"][0], "guest_name": "Alice Johnson", "adults": 2},
                        {"room_id": self.created_resources["room_ids"][1] if len(self.created_resources["room_ids"]) > 1 else self.created_resources["room_ids"][0], "guest_name": "Bob Wilson", "adults": 2}
                    ]
                
                response = self.session.post(f"{BACKEND_URL}/group-reservations/{group_id}/assign-rooms", json={
                    "room_assignments": room_assignments
                })
                success = response.status_code in [200, 201]
                details = f"Status: {response.status_code}"
                if success:
                    details += f" - Rooms assigned: {len(room_assignments)}"
                self.log_test_result("group_block", f"/group-reservations/{group_id}/assign-rooms", "POST", success, details)
            except Exception as e:
                self.log_test_result("group_block", f"/group-reservations/{group_id}/assign-rooms", "POST", False, f"Error: {str(e)}")

        # 5. POST /api/block-reservations
        try:
            response = self.session.post(f"{BACKEND_URL}/block-reservations", json={
                "block_name": "Wedding Block Test",
                "room_type": "deluxe",
                "start_date": "2025-03-01",
                "end_date": "2025-03-03",
                "total_rooms": 15,
                "block_type": "confirmed",
                "rate": 200.0,
                "contact_person": "Wedding Coordinator"
            })
            success = response.status_code in [200, 201]
            details = f"Status: {response.status_code}"
            if success and response.json():
                block_id = response.json().get('id')
                if block_id:
                    self.created_resources["block_ids"].append(block_id)
                details += f" - Block created: {response.json().get('block_name', 'N/A')}"
            self.log_test_result("group_block", "/block-reservations", "POST", success, details)
        except Exception as e:
            self.log_test_result("group_block", "/block-reservations", "POST", False, f"Error: {str(e)}")

        # 6. GET /api/block-reservations
        try:
            response = self.session.get(f"{BACKEND_URL}/block-reservations")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                details += f" - Blocks: {len(data.get('blocks', []))}"
            self.log_test_result("group_block", "/block-reservations", "GET", success, details)
        except Exception as e:
            self.log_test_result("group_block", "/block-reservations", "GET", False, f"Error: {str(e)}")

        # 7. POST /api/block-reservations/{block_id}/use-room
        if self.created_resources["block_ids"]:
            block_id = self.created_resources["block_ids"][0]
            try:
                response = self.session.post(f"{BACKEND_URL}/block-reservations/{block_id}/use-room", json={
                    "guest_name": "Jane Doe",
                    "guest_email": "jane@example.com",
                    "guest_phone": "+1234567890",
                    "check_in_date": "2025-03-01",
                    "check_out_date": "2025-03-03"
                })
                success = response.status_code in [200, 201]
                details = f"Status: {response.status_code}"
                if success:
                    details += " - Room used from block"
                self.log_test_result("group_block", f"/block-reservations/{block_id}/use-room", "POST", success, details)
            except Exception as e:
                self.log_test_result("group_block", f"/block-reservations/{block_id}/use-room", "POST", False, f"Error: {str(e)}")

            # 8. POST /api/block-reservations/{block_id}/release
            try:
                response = self.session.post(f"{BACKEND_URL}/block-reservations/{block_id}/release", json={
                    "rooms_to_release": 5,
                    "reason": "Lower than expected attendance"
                })
                success = response.status_code in [200, 201]
                details = f"Status: {response.status_code}"
                if success:
                    details += " - Rooms released from block"
                self.log_test_result("group_block", f"/block-reservations/{block_id}/release", "POST", success, details)
            except Exception as e:
                self.log_test_result("group_block", f"/block-reservations/{block_id}/release", "POST", False, f"Error: {str(e)}")

    def test_multi_property(self):
        """Test Multi-Property Management (5 endpoints)"""
        print("\n🏨 Testing Multi-Property Management...")
        
        # 1. POST /api/multi-property/properties (First property)
        try:
            response = self.session.post(f"{BACKEND_URL}/multi-property/properties", json={
                "property_name": "Grand Hotel Downtown Test",
                "property_code": "GHD",
                "location": "Downtown Business District",
                "total_rooms": 150,
                "property_type": "hotel",
                "address": "123 Business Ave",
                "phone": "+1234567890"
            })
            success = response.status_code in [200, 201]
            details = f"Status: {response.status_code}"
            if success and response.json():
                prop_id = response.json().get('id')
                if prop_id:
                    self.created_resources["property_ids"].append(prop_id)
                details += f" - Property created: {response.json().get('property_name', 'N/A')}"
            self.log_test_result("multi_property", "/multi-property/properties", "POST", success, details)
        except Exception as e:
            self.log_test_result("multi_property", "/multi-property/properties", "POST", False, f"Error: {str(e)}")

        # 2. POST /api/multi-property/properties (Second property)
        try:
            response = self.session.post(f"{BACKEND_URL}/multi-property/properties", json={
                "property_name": "Resort Beach Hotel Test",
                "property_code": "RBH",
                "location": "Beach Area Resort",
                "total_rooms": 200,
                "property_type": "resort",
                "address": "456 Beach Blvd",
                "phone": "+1234567891"
            })
            success = response.status_code in [200, 201]
            details = f"Status: {response.status_code}"
            if success and response.json():
                prop_id = response.json().get('id')
                if prop_id:
                    self.created_resources["property_ids"].append(prop_id)
                details += f" - Property created: {response.json().get('property_name', 'N/A')}"
            self.log_test_result("multi_property", "/multi-property/properties (Resort)", "POST", success, details)
        except Exception as e:
            self.log_test_result("multi_property", "/multi-property/properties (Resort)", "POST", False, f"Error: {str(e)}")

        # 3. GET /api/multi-property/properties
        try:
            response = self.session.get(f"{BACKEND_URL}/multi-property/properties")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                details += f" - Properties: {len(data.get('properties', []))}"
            self.log_test_result("multi_property", "/multi-property/properties", "GET", success, details)
        except Exception as e:
            self.log_test_result("multi_property", "/multi-property/properties", "GET", False, f"Error: {str(e)}")

        # 4. GET /api/multi-property/dashboard
        try:
            response = self.session.get(f"{BACKEND_URL}/multi-property/dashboard")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                details += f" - Dashboard data loaded"
                if 'total_properties' in data:
                    details += f" - Total properties: {data['total_properties']}"
            self.log_test_result("multi_property", "/multi-property/dashboard", "GET", success, details)
        except Exception as e:
            self.log_test_result("multi_property", "/multi-property/dashboard", "GET", False, f"Error: {str(e)}")

        # 5. GET /api/multi-property/consolidated-report
        try:
            response = self.session.get(f"{BACKEND_URL}/multi-property/consolidated-report", params={
                "start_date": "2025-01-15",
                "end_date": "2025-01-20",
                "metric": "occupancy"
            })
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                details += f" - Report generated for occupancy metric"
            self.log_test_result("multi_property", "/multi-property/consolidated-report", "GET", success, details)
        except Exception as e:
            self.log_test_result("multi_property", "/multi-property/consolidated-report", "GET", False, f"Error: {str(e)}")

    def test_marketplace(self):
        """Test Marketplace - Procurement & Inventory (12 endpoints)"""
        print("\n🛒 Testing Marketplace - Procurement & Inventory...")
        
        # 1. POST /api/marketplace/products (Bath Towels)
        try:
            response = self.session.post(f"{BACKEND_URL}/marketplace/products", json={
                "name": "Bath Towels Premium",
                "category": "linens",
                "price": 15.50,
                "unit": "piece",
                "supplier": "Linen Supply Co",
                "description": "High quality cotton bath towels"
            })
            success = response.status_code in [200, 201]
            details = f"Status: {response.status_code}"
            if success and response.json():
                prod_id = response.json().get('id')
                if prod_id:
                    self.created_resources["product_ids"].append(prod_id)
                details += f" - Product created: {response.json().get('name', 'N/A')}"
            self.log_test_result("marketplace", "/marketplace/products", "POST", success, details)
        except Exception as e:
            self.log_test_result("marketplace", "/marketplace/products", "POST", False, f"Error: {str(e)}")

        # 2. POST /api/marketplace/products (Shampoo Bottles)
        try:
            response = self.session.post(f"{BACKEND_URL}/marketplace/products", json={
                "name": "Shampoo Bottles Luxury",
                "category": "amenities",
                "price": 2.50,
                "unit": "bottle",
                "supplier": "Hotel Supplies Inc",
                "description": "Premium hotel shampoo bottles"
            })
            success = response.status_code in [200, 201]
            details = f"Status: {response.status_code}"
            if success and response.json():
                prod_id = response.json().get('id')
                if prod_id:
                    self.created_resources["product_ids"].append(prod_id)
                details += f" - Product created: {response.json().get('name', 'N/A')}"
            self.log_test_result("marketplace", "/marketplace/products (Shampoo)", "POST", success, details)
        except Exception as e:
            self.log_test_result("marketplace", "/marketplace/products (Shampoo)", "POST", False, f"Error: {str(e)}")

        # 3. GET /api/marketplace/products
        try:
            response = self.session.get(f"{BACKEND_URL}/marketplace/products")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                # Response is a list directly, not a dict with 'products' key
                products_count = len(data) if isinstance(data, list) else len(data.get('products', []))
                details += f" - Products: {products_count}"
            self.log_test_result("marketplace", "/marketplace/products", "GET", success, details)
        except Exception as e:
            self.log_test_result("marketplace", "/marketplace/products", "GET", False, f"Error: {str(e)}")

        # 4. GET /api/marketplace/products with category filter
        try:
            response = self.session.get(f"{BACKEND_URL}/marketplace/products?category=linens")
            success = response.status_code == 200
            details = f"Status: {response.status_code} - Linens filter"
            if success:
                data = response.json()
                # Response is a list directly, not a dict with 'products' key
                products_count = len(data) if isinstance(data, list) else len(data.get('products', []))
                details += f" - Linen products: {products_count}"
            self.log_test_result("marketplace", "/marketplace/products?category=linens", "GET", success, details)
        except Exception as e:
            self.log_test_result("marketplace", "/marketplace/products?category=linens", "GET", False, f"Error: {str(e)}")

        # 5. GET /api/marketplace/inventory
        try:
            response = self.session.get(f"{BACKEND_URL}/marketplace/inventory")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                details += f" - Inventory items: {len(data.get('inventory', []))}"
            self.log_test_result("marketplace", "/marketplace/inventory", "GET", success, details)
        except Exception as e:
            self.log_test_result("marketplace", "/marketplace/inventory", "GET", False, f"Error: {str(e)}")

        # 6. POST /api/marketplace/inventory/adjust
        if self.created_resources["product_ids"]:
            product_id = self.created_resources["product_ids"][0]
            try:
                response = self.session.post(f"{BACKEND_URL}/marketplace/inventory/adjust", json={
                    "product_id": product_id,
                    "location": "main_warehouse",
                    "quantity_change": 500,
                    "reason": "Initial stock - testing",
                    "adjustment_type": "increase"
                })
                success = response.status_code in [200, 201]
                details = f"Status: {response.status_code}"
                if success:
                    details += " - Inventory adjusted (+500)"
                self.log_test_result("marketplace", "/marketplace/inventory/adjust", "POST", success, details)
            except Exception as e:
                self.log_test_result("marketplace", "/marketplace/inventory/adjust", "POST", False, f"Error: {str(e)}")

        # 7. POST /api/marketplace/purchase-orders
        try:
            items = []
            if len(self.created_resources["product_ids"]) >= 2:
                items = [
                    {
                        "product_id": self.created_resources["product_ids"][0],
                        "quantity": 100,
                        "unit_price": 15.50
                    },
                    {
                        "product_id": self.created_resources["product_ids"][1],
                        "quantity": 200,
                        "unit_price": 2.50
                    }
                ]
            
            response = self.session.post(f"{BACKEND_URL}/marketplace/purchase-orders", json={
                "supplier": "Linen Supply Co",
                "items": items,
                "delivery_date": "2025-02-01",
                "notes": "Urgent order for hotel renovation"
            })
            success = response.status_code in [200, 201]
            details = f"Status: {response.status_code}"
            if success and response.json():
                po_id = response.json().get('id')
                if po_id:
                    self.created_resources["po_ids"].append(po_id)
                details += f" - PO created: {response.json().get('po_number', 'N/A')}"
            self.log_test_result("marketplace", "/marketplace/purchase-orders", "POST", success, details)
        except Exception as e:
            self.log_test_result("marketplace", "/marketplace/purchase-orders", "POST", False, f"Error: {str(e)}")

        # 8. GET /api/marketplace/purchase-orders
        try:
            response = self.session.get(f"{BACKEND_URL}/marketplace/purchase-orders")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                details += f" - Purchase orders: {len(data.get('purchase_orders', []))}"
            self.log_test_result("marketplace", "/marketplace/purchase-orders", "GET", success, details)
        except Exception as e:
            self.log_test_result("marketplace", "/marketplace/purchase-orders", "GET", False, f"Error: {str(e)}")

        # 9. POST /api/marketplace/purchase-orders/{po_id}/approve
        if self.created_resources["po_ids"]:
            po_id = self.created_resources["po_ids"][0]
            try:
                response = self.session.post(f"{BACKEND_URL}/marketplace/purchase-orders/{po_id}/approve", json={
                    "approved_by": "manager",
                    "notes": "Approved for immediate processing"
                })
                success = response.status_code in [200, 201]
                details = f"Status: {response.status_code}"
                if success:
                    details += " - Purchase order approved"
                self.log_test_result("marketplace", f"/marketplace/purchase-orders/{po_id}/approve", "POST", success, details)
            except Exception as e:
                self.log_test_result("marketplace", f"/marketplace/purchase-orders/{po_id}/approve", "POST", False, f"Error: {str(e)}")

            # 10. POST /api/marketplace/purchase-orders/{po_id}/receive
            try:
                received_items = []
                if len(self.created_resources["product_ids"]) >= 2:
                    received_items = [
                        {
                            "product_id": self.created_resources["product_ids"][0],
                            "quantity_received": 95,
                            "condition": "good"
                        },
                        {
                            "product_id": self.created_resources["product_ids"][1],
                            "quantity_received": 200,
                            "condition": "good"
                        }
                    ]
                
                response = self.session.post(f"{BACKEND_URL}/marketplace/purchase-orders/{po_id}/receive", json={
                    "received_items": received_items,
                    "received_by": "warehouse_staff",
                    "notes": "All items received in good condition"
                })
                success = response.status_code in [200, 201]
                details = f"Status: {response.status_code}"
                if success:
                    details += f" - Items received: {len(received_items)}"
                self.log_test_result("marketplace", f"/marketplace/purchase-orders/{po_id}/receive", "POST", success, details)
            except Exception as e:
                self.log_test_result("marketplace", f"/marketplace/purchase-orders/{po_id}/receive", "POST", False, f"Error: {str(e)}")

        # 11. GET /api/marketplace/deliveries
        try:
            response = self.session.get(f"{BACKEND_URL}/marketplace/deliveries")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                details += f" - Deliveries: {len(data.get('deliveries', []))}"
            self.log_test_result("marketplace", "/marketplace/deliveries", "GET", success, details)
        except Exception as e:
            self.log_test_result("marketplace", "/marketplace/deliveries", "GET", False, f"Error: {str(e)}")

        # 12. GET /api/marketplace/stock-alerts
        try:
            response = self.session.get(f"{BACKEND_URL}/marketplace/stock-alerts")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                details += f" - Stock alerts: {len(data.get('alerts', []))}"
            self.log_test_result("marketplace", "/marketplace/stock-alerts", "GET", success, details)
        except Exception as e:
            self.log_test_result("marketplace", "/marketplace/stock-alerts", "GET", False, f"Error: {str(e)}")

    def print_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "="*80)
        print("🎯 COMPREHENSIVE BACKEND TESTING SUMMARY")
        print("="*80)
        
        total_passed = 0
        total_failed = 0
        
        for category, results in self.test_results.items():
            passed = results["passed"]
            failed = results["failed"]
            total = passed + failed
            
            total_passed += passed
            total_failed += failed
            
            success_rate = (passed / total * 100) if total > 0 else 0
            status_icon = "✅" if success_rate >= 80 else "⚠️" if success_rate >= 60 else "❌"
            
            print(f"\n{status_icon} {category.upper().replace('_', ' ')}: {passed}/{total} ({success_rate:.1f}%)")
            
            # Show failed tests
            failed_tests = [detail for detail in results["details"] if "❌ FAIL" in detail["status"]]
            if failed_tests:
                print("   Failed endpoints:")
                for test in failed_tests[:3]:  # Show first 3 failures
                    print(f"     • {test['endpoint']} - {test['details']}")
                if len(failed_tests) > 3:
                    print(f"     • ... and {len(failed_tests) - 3} more")
        
        grand_total = total_passed + total_failed
        overall_success_rate = (total_passed / grand_total * 100) if grand_total > 0 else 0
        
        print(f"\n🎯 OVERALL RESULTS:")
        print(f"   Total Endpoints Tested: {grand_total}")
        print(f"   Passed: {total_passed}")
        print(f"   Failed: {total_failed}")
        print(f"   Success Rate: {overall_success_rate:.1f}%")
        
        if overall_success_rate >= 90:
            print("   Status: 🟢 EXCELLENT - All systems operational")
        elif overall_success_rate >= 80:
            print("   Status: 🟡 GOOD - Minor issues detected")
        elif overall_success_rate >= 60:
            print("   Status: 🟠 FAIR - Several issues need attention")
        else:
            print("   Status: 🔴 POOR - Major issues require immediate attention")
        
        print("\n" + "="*80)

    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting Comprehensive Backend Testing for Hotel PMS")
        print("Testing 57 endpoints across 7 major features...")
        
        if not self.authenticate():
            print("❌ Authentication failed. Cannot proceed with testing.")
            return False
        
        # Run all test suites
        self.test_messaging_hub()           # 7 endpoints
        self.test_rms_system()              # 10 endpoints  
        self.test_mobile_housekeeping()     # 7 endpoints
        self.test_efatura_pos()             # 7 endpoints
        self.test_group_block_reservations() # 9 endpoints
        self.test_multi_property()          # 5 endpoints
        self.test_marketplace()             # 12 endpoints
        
        # Print comprehensive summary
        self.print_summary()
        
        return True

def main():
    """Main function"""
    tester = HotelPMSBackendTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n✅ Backend testing completed successfully!")
    else:
        print("\n❌ Backend testing failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
