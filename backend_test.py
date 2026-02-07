#!/usr/bin/env python3
"""
Feature Modules Testing: E-Fatura Layer, SMS Notification Layer, QR Ticket + Check-in
Testing 3 new feature modules on backend with provider abstraction, mock providers, tenant isolation, RBAC, audit logging, idempotency
"""

import asyncio
import json
import time
import requests
from datetime import datetime
from typing import Dict, Any, Optional


class FeatureModulesTester:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.auth_token = None
        self.user_id = None
        self.org_id = None
        self.tenant_id = None
        self.admin_email = "admin@acenta.test"
        self.admin_password = "admin123"
        
    def log(self, message: str, level: str = "INFO"):
        """Log test messages with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    def login_admin(self) -> bool:
        """Login as admin@acenta.test with admin123"""
        try:
            self.log(f"🔐 Logging in as {self.admin_email}...")
            response = self.session.post(f"{self.base_url}/api/auth/login", json={
                "email": self.admin_email,
                "password": self.admin_password
            })
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                self.user_id = data.get("user_id")
                self.org_id = data.get("org_id") or data.get("organization_id")
                self.tenant_id = data.get("tenant_id") or self.org_id
                
                # Update session headers
                self.session.headers.update({
                    'Authorization': f'Bearer {self.auth_token}',
                    'X-Tenant-Id': self.tenant_id if self.tenant_id else '',
                    'Content-Type': 'application/json'
                })
                
                self.log(f"✅ Admin login successful - Token: {self.auth_token[:20]}...")
                self.log(f"   Org ID: {self.org_id}, Tenant ID: {self.tenant_id}")
                return True
            else:
                self.log(f"❌ Admin login failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Admin login error: {str(e)}", "ERROR")
            return False

    def test_efatura_profile_crud(self) -> Dict[str, Any]:
        """Test A) E-Fatura - Profile CRUD operations"""
        results = {"group": "A) E-Fatura - Profile CRUD", "tests": []}
        
        try:
            self.log("🧪 Testing E-Fatura Profile CRUD operations")
            
            # Test 1: PUT /api/efatura/profile - Create profile
            profile_data = {
                "legal_name": "Test Corp",
                "tax_number": "1234567890",
                "tax_office": "Istanbul",
                "city": "Istanbul",
                "default_currency": "TRY"
            }
            
            response = self.session.put(f"{self.base_url}/api/efatura/profile", json=profile_data)
            
            test_result = {
                "name": "PUT /api/efatura/profile - Create profile",
                "status": "pass" if response.status_code == 200 else "fail",
                "details": f"Status: {response.status_code}"
            }
            
            if response.status_code == 200:
                data = response.json()
                test_result["details"] += f" ✅ Profile created successfully: {data}"
            else:
                test_result["details"] += f" ❌ Response: {response.text[:200]}"
                
            results["tests"].append(test_result)
            
            # Test 2: GET /api/efatura/profile - Retrieve profile
            response2 = self.session.get(f"{self.base_url}/api/efatura/profile")
            
            test_result2 = {
                "name": "GET /api/efatura/profile - Retrieve profile",
                "status": "pass" if response2.status_code == 200 else "fail",
                "details": f"Status: {response2.status_code}"
            }
            
            if response2.status_code == 200:
                data2 = response2.json()
                if "legal_name" in data2 and data2.get("legal_name") == "Test Corp":
                    test_result2["details"] += f" ✅ Profile retrieved correctly: legal_name={data2.get('legal_name')}"
                else:
                    test_result2["status"] = "fail"
                    test_result2["details"] += f" ❌ Profile data invalid: {data2}"
            else:
                test_result2["details"] += f" ❌ Response: {response2.text[:200]}"
                
            results["tests"].append(test_result2)
            
        except Exception as e:
            results["tests"].append({
                "name": "E-Fatura Profile CRUD Exception",
                "status": "fail",
                "details": f"Exception: {str(e)}"
            })
            
        return results

    def test_efatura_invoice_operations(self) -> Dict[str, Any]:
        """Test A) E-Fatura - Invoice CRUD + Send + Cancel operations"""
        results = {"group": "A) E-Fatura - Invoice CRUD + Send + Cancel", "tests": []}
        
        try:
            self.log("🧪 Testing E-Fatura Invoice operations")
            
            # Test 1: POST /api/efatura/invoices - Create invoice (idempotent)
            invoice_data = {
                "source_type": "manual",
                "source_id": "test-1",
                "customer_id": "cust-1",
                "lines": [{
                    "description": "Otel konaklama",
                    "quantity": 2,
                    "unit_price": 500,
                    "tax_rate": 18,
                    "line_total": 1000
                }],
                "currency": "TRY"
            }
            
            response = self.session.post(f"{self.base_url}/api/efatura/invoices", json=invoice_data)
            
            test_result = {
                "name": "POST /api/efatura/invoices - Create invoice",
                "status": "pass" if response.status_code == 200 else "fail",
                "details": f"Status: {response.status_code}"
            }
            
            invoice_id = None
            if response.status_code == 200:
                data = response.json()
                invoice_id = data.get("invoice_id")
                if invoice_id and data.get("status") == "draft":
                    test_result["details"] += f" ✅ Invoice created: {invoice_id}, status={data.get('status')}"
                else:
                    test_result["status"] = "fail"
                    test_result["details"] += f" ❌ Invalid invoice response: {data}"
            else:
                test_result["details"] += f" ❌ Response: {response.text[:200]}"
                
            results["tests"].append(test_result)
            
            # Test 2: POST same data again - Test idempotency
            if invoice_id:
                response2 = self.session.post(f"{self.base_url}/api/efatura/invoices", json=invoice_data)
                
                test_result2 = {
                    "name": "POST /api/efatura/invoices - Test idempotency",
                    "status": "pass" if response2.status_code == 200 else "fail",
                    "details": f"Status: {response2.status_code}"
                }
                
                if response2.status_code == 200:
                    data2 = response2.json()
                    if data2.get("invoice_id") == invoice_id:
                        test_result2["details"] += f" ✅ Idempotency works - same invoice returned: {invoice_id}"
                    else:
                        test_result2["status"] = "fail"
                        test_result2["details"] += f" ❌ Different invoice returned: {data2.get('invoice_id')} vs {invoice_id}"
                else:
                    test_result2["details"] += f" ❌ Response: {response2.text[:200]}"
                    
                results["tests"].append(test_result2)
            
            # Test 3: POST /api/efatura/invoices/{invoice_id}/send
            if invoice_id:
                response3 = self.session.post(f"{self.base_url}/api/efatura/invoices/{invoice_id}/send")
                
                test_result3 = {
                    "name": f"POST /api/efatura/invoices/{invoice_id}/send - Send invoice",
                    "status": "pass" if response3.status_code == 200 else "fail",
                    "details": f"Status: {response3.status_code}"
                }
                
                if response3.status_code == 200:
                    data3 = response3.json()
                    test_result3["details"] += f" ✅ Invoice sent successfully: {data3}"
                else:
                    test_result3["details"] += f" ❌ Response: {response3.text[:200]}"
                    
                results["tests"].append(test_result3)
                
                # Test 4: GET /api/efatura/invoices/{invoice_id} - Check status
                time.sleep(1)  # Brief wait
                response4 = self.session.get(f"{self.base_url}/api/efatura/invoices/{invoice_id}")
                
                test_result4 = {
                    "name": f"GET /api/efatura/invoices/{invoice_id} - Check status",
                    "status": "pass" if response4.status_code == 200 else "fail",
                    "details": f"Status: {response4.status_code}"
                }
                
                if response4.status_code == 200:
                    data4 = response4.json()
                    status = data4.get("status")
                    if status in ["sent", "accepted"]:  # Mock auto-accepts
                        test_result4["details"] += f" ✅ Invoice status: {status}"
                    else:
                        test_result4["details"] += f" ⚠️ Invoice status: {status} (expected sent/accepted)"
                else:
                    test_result4["details"] += f" ❌ Response: {response4.text[:200]}"
                    
                results["tests"].append(test_result4)
            
            # Test 5: Create another invoice for cancellation test
            invoice_data_2 = {
                "source_type": "manual",
                "source_id": "test-2",
                "customer_id": "cust-2",
                "lines": [{
                    "description": "Test service",
                    "quantity": 1,
                    "unit_price": 100,
                    "tax_rate": 18,
                    "line_total": 100
                }],
                "currency": "TRY"
            }
            
            response5 = self.session.post(f"{self.base_url}/api/efatura/invoices", json=invoice_data_2)
            
            invoice_id_2 = None
            if response5.status_code == 200:
                data5 = response5.json()
                invoice_id_2 = data5.get("invoice_id")
            
            # Test 6: POST /api/efatura/invoices/{invoice_id}/cancel
            if invoice_id_2:
                response6 = self.session.post(f"{self.base_url}/api/efatura/invoices/{invoice_id_2}/cancel")
                
                test_result6 = {
                    "name": f"POST /api/efatura/invoices/{invoice_id_2}/cancel - Cancel invoice",
                    "status": "pass" if response6.status_code == 200 else "fail",
                    "details": f"Status: {response6.status_code}"
                }
                
                if response6.status_code == 200:
                    data6 = response6.json()
                    if data6.get("status") == "canceled":
                        test_result6["details"] += f" ✅ Invoice canceled successfully: {data6}"
                    else:
                        test_result6["details"] += f" ⚠️ Cancel response: {data6}"
                else:
                    test_result6["details"] += f" ❌ Response: {response6.text[:200]}"
                    
                results["tests"].append(test_result6)
            
            # Test 7: GET /api/efatura/invoices/{invoice_id}/events - Timeline
            if invoice_id:
                response7 = self.session.get(f"{self.base_url}/api/efatura/invoices/{invoice_id}/events")
                
                test_result7 = {
                    "name": f"GET /api/efatura/invoices/{invoice_id}/events - Timeline",
                    "status": "pass" if response7.status_code == 200 else "fail",
                    "details": f"Status: {response7.status_code}"
                }
                
                if response7.status_code == 200:
                    data7 = response7.json()
                    events = data7.get("events", [])
                    test_result7["details"] += f" ✅ Found {len(events)} events in timeline"
                else:
                    test_result7["details"] += f" ❌ Response: {response7.text[:200]}"
                    
                results["tests"].append(test_result7)
            
            # Test 8: GET /api/efatura/invoices - List invoices
            response8 = self.session.get(f"{self.base_url}/api/efatura/invoices")
            
            test_result8 = {
                "name": "GET /api/efatura/invoices - List invoices",
                "status": "pass" if response8.status_code == 200 else "fail",
                "details": f"Status: {response8.status_code}"
            }
            
            if response8.status_code == 200:
                data8 = response8.json()
                items = data8.get("items", [])
                test_result8["details"] += f" ✅ Found {len(items)} invoices in list"
            else:
                test_result8["details"] += f" ❌ Response: {response8.text[:200]}"
                
            results["tests"].append(test_result8)
            
        except Exception as e:
            results["tests"].append({
                "name": "E-Fatura Invoice Operations Exception",
                "status": "fail",
                "details": f"Exception: {str(e)}"
            })
            
        return results

    def test_sms_notifications(self) -> Dict[str, Any]:
        """Test B) SMS Notification - Send + Bulk + Logs operations"""
        results = {"group": "B) SMS Notification - Send + Bulk + Logs", "tests": []}
        
        try:
            self.log("🧪 Testing SMS Notification operations")
            
            # Test 1: GET /api/sms/templates - List templates
            response = self.session.get(f"{self.base_url}/api/sms/templates")
            
            test_result = {
                "name": "GET /api/sms/templates - List templates",
                "status": "pass" if response.status_code == 200 else "fail",
                "details": f"Status: {response.status_code}"
            }
            
            if response.status_code == 200:
                data = response.json()
                templates = data.get("templates", {})
                test_result["details"] += f" ✅ Found {len(templates)} templates: {list(templates.keys())}"
            else:
                test_result["details"] += f" ❌ Response: {response.text[:200]}"
                
            results["tests"].append(test_result)
            
            # Test 2: POST /api/sms/send - Send single SMS
            sms_data = {
                "to": "+905551234567",
                "template_key": "custom",
                "variables": {"message": "Test SMS mesaji"}
            }
            
            response2 = self.session.post(f"{self.base_url}/api/sms/send", json=sms_data)
            
            test_result2 = {
                "name": "POST /api/sms/send - Send single SMS",
                "status": "pass" if response2.status_code == 200 else "fail",
                "details": f"Status: {response2.status_code}"
            }
            
            if response2.status_code == 200:
                data2 = response2.json()
                message_id = data2.get("message_id")
                if message_id:
                    test_result2["details"] += f" ✅ SMS sent successfully: message_id={message_id}"
                else:
                    test_result2["details"] += f" ⚠️ SMS response: {data2}"
            else:
                test_result2["details"] += f" ❌ Response: {response2.text[:200]}"
                
            results["tests"].append(test_result2)
            
            # Test 3: POST /api/sms/send-bulk - Send bulk SMS
            bulk_data = {
                "recipients": ["+905551111111", "+905552222222"],
                "template_key": "reservation_confirmed",
                "variables": {
                    "customer_name": "Ali",
                    "product_name": "Kapadokya Turu",
                    "booking_code": "BK123"
                }
            }
            
            response3 = self.session.post(f"{self.base_url}/api/sms/send-bulk", json=bulk_data)
            
            test_result3 = {
                "name": "POST /api/sms/send-bulk - Send bulk SMS",
                "status": "pass" if response3.status_code == 200 else "fail",
                "details": f"Status: {response3.status_code}"
            }
            
            if response3.status_code == 200:
                data3 = response3.json()
                batch_id = data3.get("batch_id")
                if batch_id:
                    test_result3["details"] += f" ✅ Bulk SMS sent successfully: batch_id={batch_id}"
                else:
                    test_result3["details"] += f" ⚠️ Bulk SMS response: {data3}"
            else:
                test_result3["details"] += f" ❌ Response: {response3.text[:200]}"
                
            results["tests"].append(test_result3)
            
            # Test 4: GET /api/sms/logs - List SMS logs
            response4 = self.session.get(f"{self.base_url}/api/sms/logs")
            
            test_result4 = {
                "name": "GET /api/sms/logs - List SMS logs",
                "status": "pass" if response4.status_code == 200 else "fail",
                "details": f"Status: {response4.status_code}"
            }
            
            if response4.status_code == 200:
                data4 = response4.json()
                items = data4.get("items", [])
                test_result4["details"] += f" ✅ Found {len(items)} SMS logs"
            else:
                test_result4["details"] += f" ❌ Response: {response4.text[:200]}"
                
            results["tests"].append(test_result4)
            
        except Exception as e:
            results["tests"].append({
                "name": "SMS Notifications Exception",
                "status": "fail",
                "details": f"Exception: {str(e)}"
            })
            
        return results

    def test_qr_tickets(self) -> Dict[str, Any]:
        """Test C) QR Ticket - Create + Check-in + Cancel + Stats operations"""
        results = {"group": "C) QR Ticket - Create + Check-in + Cancel + Stats", "tests": []}
        
        try:
            self.log("🧪 Testing QR Ticket operations")
            
            # Test 1: POST /api/tickets - Create ticket
            ticket_data = {
                "reservation_id": "res-001",
                "product_name": "Kapadokya Balon Turu",
                "customer_name": "Ahmet Yilmaz",
                "customer_email": "ahmet@test.com",
                "event_date": "2026-03-01"
            }
            
            response = self.session.post(f"{self.base_url}/api/tickets", json=ticket_data)
            
            test_result = {
                "name": "POST /api/tickets - Create ticket",
                "status": "pass" if response.status_code == 200 else "fail",
                "details": f"Status: {response.status_code}"
            }
            
            ticket_code = None
            if response.status_code == 200:
                data = response.json()
                ticket_code = data.get("ticket_code")
                qr_data = data.get("qr_data")
                status = data.get("status")
                
                if ticket_code and qr_data and status == "active":
                    test_result["details"] += f" ✅ Ticket created: {ticket_code}, status={status}, has QR data"
                else:
                    test_result["status"] = "fail"
                    test_result["details"] += f" ❌ Invalid ticket response: {data}"
            else:
                test_result["details"] += f" ❌ Response: {response.text[:200]}"
                
            results["tests"].append(test_result)
            
            # Test 2: POST same data again - Test idempotency
            if ticket_code:
                response2 = self.session.post(f"{self.base_url}/api/tickets", json=ticket_data)
                
                test_result2 = {
                    "name": "POST /api/tickets - Test idempotency (same reservation_id)",
                    "status": "pass" if response2.status_code == 200 else "fail",
                    "details": f"Status: {response2.status_code}"
                }
                
                if response2.status_code == 200:
                    data2 = response2.json()
                    if data2.get("ticket_code") == ticket_code:
                        test_result2["details"] += f" ✅ Idempotency works - same ticket returned: {ticket_code}"
                    else:
                        test_result2["status"] = "fail"
                        test_result2["details"] += f" ❌ Different ticket returned: {data2.get('ticket_code')} vs {ticket_code}"
                else:
                    test_result2["details"] += f" ❌ Response: {response2.text[:200]}"
                    
                results["tests"].append(test_result2)
            
            # Test 3: POST /api/tickets/check-in - Check in ticket
            if ticket_code:
                checkin_data = {"ticket_code": ticket_code}
                response3 = self.session.post(f"{self.base_url}/api/tickets/check-in", json=checkin_data)
                
                test_result3 = {
                    "name": f"POST /api/tickets/check-in - Check in {ticket_code}",
                    "status": "pass" if response3.status_code == 200 else "fail",
                    "details": f"Status: {response3.status_code}"
                }
                
                if response3.status_code == 200:
                    data3 = response3.json()
                    test_result3["details"] += f" ✅ Check-in successful: {data3}"
                else:
                    test_result3["details"] += f" ❌ Response: {response3.text[:200]}"
                    
                results["tests"].append(test_result3)
                
                # Test 4: POST same check-in again - Should return 409
                response4 = self.session.post(f"{self.base_url}/api/tickets/check-in", json=checkin_data)
                
                test_result4 = {
                    "name": f"POST /api/tickets/check-in - Already checked in (should be 409)",
                    "status": "pass" if response4.status_code == 409 else "fail",
                    "details": f"Status: {response4.status_code}"
                }
                
                if response4.status_code == 409:
                    test_result4["details"] += " ✅ Correctly returned 409 - already checked in"
                else:
                    test_result4["details"] += f" ❌ Expected 409, got: {response4.text[:200]}"
                    
                results["tests"].append(test_result4)
            
            # Test 5: Create another ticket for cancellation test
            ticket_data_2 = {
                "reservation_id": "res-002",
                "product_name": "Istanbul City Tour",
                "customer_name": "Elif Demir",
                "customer_email": "elif@test.com",
                "event_date": "2026-03-02"
            }
            
            response5 = self.session.post(f"{self.base_url}/api/tickets", json=ticket_data_2)
            
            ticket_code_2 = None
            if response5.status_code == 200:
                data5 = response5.json()
                ticket_code_2 = data5.get("ticket_code")
            
            # Test 6: POST /api/tickets/{ticket_code}/cancel
            if ticket_code_2:
                response6 = self.session.post(f"{self.base_url}/api/tickets/{ticket_code_2}/cancel")
                
                test_result6 = {
                    "name": f"POST /api/tickets/{ticket_code_2}/cancel - Cancel ticket",
                    "status": "pass" if response6.status_code == 200 else "fail",
                    "details": f"Status: {response6.status_code}"
                }
                
                if response6.status_code == 200:
                    data6 = response6.json()
                    if data6.get("status") == "canceled":
                        test_result6["details"] += f" ✅ Ticket canceled successfully: {data6}"
                    else:
                        test_result6["details"] += f" ⚠️ Cancel response: {data6}"
                else:
                    test_result6["details"] += f" ❌ Response: {response6.text[:200]}"
                    
                results["tests"].append(test_result6)
                
                # Test 7: Try to check-in canceled ticket - Should return 410
                checkin_data_canceled = {"ticket_code": ticket_code_2}
                response7 = self.session.post(f"{self.base_url}/api/tickets/check-in", json=checkin_data_canceled)
                
                test_result7 = {
                    "name": f"POST /api/tickets/check-in - Canceled ticket (should be 410)",
                    "status": "pass" if response7.status_code == 410 else "fail",
                    "details": f"Status: {response7.status_code}"
                }
                
                if response7.status_code == 410:
                    test_result7["details"] += " ✅ Correctly returned 410 - ticket canceled"
                else:
                    test_result7["details"] += f" ❌ Expected 410, got: {response7.text[:200]}"
                    
                results["tests"].append(test_result7)
            
            # Test 8: GET /api/tickets - List tickets
            response8 = self.session.get(f"{self.base_url}/api/tickets")
            
            test_result8 = {
                "name": "GET /api/tickets - List tickets",
                "status": "pass" if response8.status_code == 200 else "fail",
                "details": f"Status: {response8.status_code}"
            }
            
            if response8.status_code == 200:
                data8 = response8.json()
                items = data8.get("items", [])
                test_result8["details"] += f" ✅ Found {len(items)} tickets in list"
            else:
                test_result8["details"] += f" ❌ Response: {response8.text[:200]}"
                
            results["tests"].append(test_result8)
            
            # Test 9: GET /api/tickets/stats - Statistics
            response9 = self.session.get(f"{self.base_url}/api/tickets/stats")
            
            test_result9 = {
                "name": "GET /api/tickets/stats - Statistics",
                "status": "pass" if response9.status_code == 200 else "fail",
                "details": f"Status: {response9.status_code}"
            }
            
            if response9.status_code == 200:
                data9 = response9.json()
                stats = ["total", "active", "checked_in", "canceled"]
                found_stats = [s for s in stats if s in data9]
                test_result9["details"] += f" ✅ Stats returned: {found_stats}, values: {data9}"
            else:
                test_result9["details"] += f" ❌ Response: {response9.text[:200]}"
                
            results["tests"].append(test_result9)
            
            # Test 10: GET /api/tickets/lookup/{ticket_code} - Lookup
            if ticket_code:
                response10 = self.session.get(f"{self.base_url}/api/tickets/lookup/{ticket_code}")
                
                test_result10 = {
                    "name": f"GET /api/tickets/lookup/{ticket_code} - Lookup ticket",
                    "status": "pass" if response10.status_code == 200 else "fail",
                    "details": f"Status: {response10.status_code}"
                }
                
                if response10.status_code == 200:
                    data10 = response10.json()
                    if data10.get("ticket_code") == ticket_code:
                        test_result10["details"] += f" ✅ Ticket lookup successful: {data10.get('product_name')}"
                    else:
                        test_result10["status"] = "fail"
                        test_result10["details"] += f" ❌ Wrong ticket data: {data10}"
                else:
                    test_result10["details"] += f" ❌ Response: {response10.text[:200]}"
                    
                results["tests"].append(test_result10)
            
        except Exception as e:
            results["tests"].append({
                "name": "QR Tickets Exception",
                "status": "fail",
                "details": f"Exception: {str(e)}"
            })
            
        return results

    def run_feature_modules_tests(self) -> Dict[str, Any]:
        """Run all feature modules tests"""
        self.log("🚀 Starting Feature Modules Testing")
        
        if not self.login_admin():
            return {"error": "Failed to login as admin"}
        
        all_results = []
        
        # Run tests in order
        test_groups = [
            self.test_efatura_profile_crud,
            self.test_efatura_invoice_operations,
            self.test_sms_notifications,
            self.test_qr_tickets,
        ]
        
        for test_group in test_groups:
            try:
                result = test_group()
                all_results.append(result)
            except Exception as e:
                all_results.append({
                    "group": test_group.__name__,
                    "tests": [{
                        "name": "Test group exception",
                        "status": "fail",
                        "details": f"Exception: {str(e)}"
                    }]
                })
        
        return {
            "summary": self.generate_summary(all_results),
            "details": all_results
        }

    def generate_summary(self, results: list) -> Dict[str, Any]:
        """Generate test summary"""
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        
        for group in results:
            for test in group.get("tests", []):
                total_tests += 1
                if test["status"] == "pass":
                    passed_tests += 1
                else:
                    failed_tests += 1
        
        return {
            "total_groups": len(results),
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "success_rate": f"{(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "0%"
        }


def main():
    """Main test execution"""
    # Backend URL from frontend env
    backend_url = "https://ops-excellence-10.preview.emergentagent.com"
    
    print(f"🎯 Testing Feature Modules at: {backend_url}")
    
    tester = FeatureModulesTester(backend_url)
    results = tester.run_feature_modules_tests()
    
    print("\n" + "="*80)
    print("📊 FEATURE MODULES TEST RESULTS")
    print("="*80)
    
    if "error" in results:
        print(f"❌ Test execution failed: {results['error']}")
        return False
    
    summary = results["summary"]
    print(f"📋 Total Groups: {summary['total_groups']}")
    print(f"📋 Total Tests: {summary['total_tests']}")
    print(f"✅ Passed: {summary['passed']}")
    print(f"❌ Failed: {summary['failed']}")
    print(f"📈 Success Rate: {summary['success_rate']}")
    
    print(f"\n📝 DETAILED RESULTS:")
    print("-" * 80)
    
    for group in results["details"]:
        group_name = group["group"]
        tests = group["tests"]
        group_passed = sum(1 for t in tests if t["status"] == "pass")
        group_total = len(tests)
        
        status_icon = "✅" if group_passed == group_total else "❌"
        print(f"{status_icon} {group_name} ({group_passed}/{group_total})")
        
        for test in tests:
            test_icon = "  ✅" if test["status"] == "pass" else "  ❌"
            print(f"{test_icon} {test['name']}: {test['details']}")
        print()

    return summary["failed"] == 0


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)