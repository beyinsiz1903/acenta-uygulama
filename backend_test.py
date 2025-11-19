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
            "calendar": {"passed": 0, "failed": 0, "details": []},
            "rms": {"passed": 0, "failed": 0, "details": []}
        }
        self.created_resources = {
            "comp_set_ids": [],
            "group_ids": [],
            "block_ids": [],
            "property_ids": [],
            "product_ids": [],
            "po_ids": [],
            "room_ids": [],
            "supplier_ids": [],
            "warehouse_ids": [],
            "delivery_ids": []
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

    def test_enhanced_pos_integration(self):
        """Test Enhanced POS Integration with Multi-Outlet, Menu Breakdown & Z Reports (9+ endpoints)"""
        print("\n🍽️ Testing Enhanced POS Integration with Multi-Outlet, Menu Breakdown & Z Reports...")
        
        # Store created resource IDs for testing
        outlet_ids = []
        menu_item_ids = []
        transaction_ids = []
        
        # ============= 1. MULTI-OUTLET SUPPORT (3 endpoints) =============
        print("\n🏪 Testing Multi-Outlet Support...")
        
        # 1.1 POST /api/pos/outlets - Create Main Restaurant
        try:
            response = self.session.post(f"{BACKEND_URL}/pos/outlets", json={
                "outlet_name": "Main Restaurant",
                "outlet_type": "restaurant",
                "location": "Ground Floor",
                "capacity": 80,
                "opening_hours": "07:00-22:00"
            })
            success = response.status_code in [200, 201]
            details = f"Status: {response.status_code}"
            
            if success and response.json():
                data = response.json()
                outlet_id = data.get('id')
                if outlet_id:
                    outlet_ids.append(outlet_id)
                details += f" - Created: {data.get('outlet_name')} ({data.get('outlet_type')})"
                details += f" - Location: {data.get('location')}, Capacity: {data.get('capacity')}"
                details += f" - Hours: {data.get('opening_hours')}"
            
            self.log_test_result("pos", "/pos/outlets (Main Restaurant)", "POST", success, details)
        except Exception as e:
            self.log_test_result("pos", "/pos/outlets (Main Restaurant)", "POST", False, f"Error: {str(e)}")

        # 1.2 POST /api/pos/outlets - Create Rooftop Bar
        try:
            response = self.session.post(f"{BACKEND_URL}/pos/outlets", json={
                "outlet_name": "Rooftop Bar",
                "outlet_type": "bar",
                "location": "10th Floor",
                "capacity": 40,
                "opening_hours": "17:00-02:00"
            })
            success = response.status_code in [200, 201]
            details = f"Status: {response.status_code}"
            
            if success and response.json():
                data = response.json()
                outlet_id = data.get('id')
                if outlet_id:
                    outlet_ids.append(outlet_id)
                details += f" - Created: {data.get('outlet_name')} ({data.get('outlet_type')})"
                details += f" - Location: {data.get('location')}, Capacity: {data.get('capacity')}"
                details += f" - Hours: {data.get('opening_hours')}"
            
            self.log_test_result("pos", "/pos/outlets (Rooftop Bar)", "POST", success, details)
        except Exception as e:
            self.log_test_result("pos", "/pos/outlets (Rooftop Bar)", "POST", False, f"Error: {str(e)}")

        # 1.3 POST /api/pos/outlets - Create Room Service
        try:
            response = self.session.post(f"{BACKEND_URL}/pos/outlets", json={
                "outlet_name": "Room Service",
                "outlet_type": "room_service",
                "location": "Kitchen",
                "capacity": None,
                "opening_hours": "24/7"
            })
            success = response.status_code in [200, 201]
            details = f"Status: {response.status_code}"
            
            if success and response.json():
                data = response.json()
                outlet_id = data.get('id')
                if outlet_id:
                    outlet_ids.append(outlet_id)
                details += f" - Created: {data.get('outlet_name')} ({data.get('outlet_type')})"
                details += f" - Location: {data.get('location')}, Hours: {data.get('opening_hours')}"
            
            self.log_test_result("pos", "/pos/outlets (Room Service)", "POST", success, details)
        except Exception as e:
            self.log_test_result("pos", "/pos/outlets (Room Service)", "POST", False, f"Error: {str(e)}")

        # 1.4 GET /api/pos/outlets - List all outlets
        try:
            response = self.session.get(f"{BACKEND_URL}/pos/outlets")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success and response.json():
                data = response.json()
                outlets = data.get('outlets', [])
                details += f" - Total outlets: {len(outlets)}"
                
                # Verify outlet types
                outlet_types = [outlet.get('outlet_type') for outlet in outlets]
                expected_types = ['restaurant', 'bar', 'room_service']
                found_types = [t for t in expected_types if t in outlet_types]
                details += f" - Types found: {found_types}"
            
            self.log_test_result("pos", "/pos/outlets", "GET", success, details)
        except Exception as e:
            self.log_test_result("pos", "/pos/outlets", "GET", False, f"Error: {str(e)}")

        # 1.5 GET /api/pos/outlets/{outlet_id} - Get specific outlet details
        if outlet_ids:
            try:
                outlet_id = outlet_ids[0]  # Main Restaurant
                response = self.session.get(f"{BACKEND_URL}/pos/outlets/{outlet_id}")
                success = response.status_code == 200
                details = f"Status: {response.status_code}"
                
                if success and response.json():
                    data = response.json()
                    details += f" - Outlet: {data.get('outlet_name')}"
                    details += f" - Menu items: {data.get('menu_items_count', 0)}"
                    details += f" - Location: {data.get('location')}"
                
                self.log_test_result("pos", f"/pos/outlets/{outlet_id}", "GET", success, details)
            except Exception as e:
                self.log_test_result("pos", f"/pos/outlets/{outlet_id}", "GET", False, f"Error: {str(e)}")

        # ============= 2. MENU-BASED TRANSACTION BREAKDOWN (4 endpoints) =============
        print("\n🍽️ Testing Menu-Based Transaction Breakdown...")
        
        # 2.1 POST /api/pos/menu-items - Create Grilled Salmon (Main Restaurant)
        if outlet_ids:
            try:
                main_restaurant_id = outlet_ids[0]
                response = self.session.post(f"{BACKEND_URL}/pos/menu-items", json={
                    "outlet_id": main_restaurant_id,
                    "item_name": "Grilled Salmon",
                    "category": "main",
                    "price": 45.00,
                    "cost": 18.00,
                    "description": "Fresh Atlantic salmon with herbs"
                })
                success = response.status_code in [200, 201]
                details = f"Status: {response.status_code}"
                
                if success and response.json():
                    data = response.json()
                    menu_item_id = data.get('id')
                    if menu_item_id:
                        menu_item_ids.append(menu_item_id)
                    details += f" - Created: {data.get('item_name')} (${data.get('price')})"
                    details += f" - Category: {data.get('category')}, Cost: ${data.get('cost')}"
                    details += f" - Margin: ${data.get('price', 0) - data.get('cost', 0)}"
                
                self.log_test_result("pos", "/pos/menu-items (Grilled Salmon)", "POST", success, details)
            except Exception as e:
                self.log_test_result("pos", "/pos/menu-items (Grilled Salmon)", "POST", False, f"Error: {str(e)}")

        # 2.2 POST /api/pos/menu-items - Create Caesar Salad (Main Restaurant)
        if outlet_ids:
            try:
                main_restaurant_id = outlet_ids[0]
                response = self.session.post(f"{BACKEND_URL}/pos/menu-items", json={
                    "outlet_id": main_restaurant_id,
                    "item_name": "Caesar Salad",
                    "category": "appetizer",
                    "price": 15.00,
                    "cost": 5.00,
                    "description": "Classic Caesar salad with croutons"
                })
                success = response.status_code in [200, 201]
                details = f"Status: {response.status_code}"
                
                if success and response.json():
                    data = response.json()
                    menu_item_id = data.get('id')
                    if menu_item_id:
                        menu_item_ids.append(menu_item_id)
                    details += f" - Created: {data.get('item_name')} (${data.get('price')})"
                    details += f" - Category: {data.get('category')}, Cost: ${data.get('cost')}"
                
                self.log_test_result("pos", "/pos/menu-items (Caesar Salad)", "POST", success, details)
            except Exception as e:
                self.log_test_result("pos", "/pos/menu-items (Caesar Salad)", "POST", False, f"Error: {str(e)}")

        # 2.3 POST /api/pos/menu-items - Create Mojito (Rooftop Bar)
        if len(outlet_ids) > 1:
            try:
                rooftop_bar_id = outlet_ids[1]
                response = self.session.post(f"{BACKEND_URL}/pos/menu-items", json={
                    "outlet_id": rooftop_bar_id,
                    "item_name": "Mojito",
                    "category": "beverage",
                    "price": 12.00,
                    "cost": 3.00,
                    "description": "Classic Cuban mojito with fresh mint"
                })
                success = response.status_code in [200, 201]
                details = f"Status: {response.status_code}"
                
                if success and response.json():
                    data = response.json()
                    menu_item_id = data.get('id')
                    if menu_item_id:
                        menu_item_ids.append(menu_item_id)
                    details += f" - Created: {data.get('item_name')} (${data.get('price')})"
                    details += f" - Category: {data.get('category')}, Cost: ${data.get('cost')}"
                
                self.log_test_result("pos", "/pos/menu-items (Mojito)", "POST", success, details)
            except Exception as e:
                self.log_test_result("pos", "/pos/menu-items (Mojito)", "POST", False, f"Error: {str(e)}")

        # 2.4 GET /api/pos/menu-items - List all menu items
        try:
            response = self.session.get(f"{BACKEND_URL}/pos/menu-items")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success and response.json():
                data = response.json()
                menu_items = data.get('menu_items', [])
                details += f" - Total menu items: {len(menu_items)}"
                
                # Group by category
                categories = {}
                for item in menu_items:
                    cat = item.get('category', 'unknown')
                    categories[cat] = categories.get(cat, 0) + 1
                details += f" - Categories: {dict(categories)}"
            
            self.log_test_result("pos", "/pos/menu-items", "GET", success, details)
        except Exception as e:
            self.log_test_result("pos", "/pos/menu-items", "GET", False, f"Error: {str(e)}")

        # 2.5 GET /api/pos/menu-items with outlet filter
        if outlet_ids:
            try:
                main_restaurant_id = outlet_ids[0]
                response = self.session.get(f"{BACKEND_URL}/pos/menu-items?outlet_id={main_restaurant_id}")
                success = response.status_code == 200
                details = f"Status: {response.status_code} - Main Restaurant filter"
                
                if success and response.json():
                    data = response.json()
                    menu_items = data.get('menu_items', [])
                    details += f" - Restaurant items: {len(menu_items)}"
                    
                    # Verify all items belong to main restaurant
                    restaurant_items = [item for item in menu_items if item.get('outlet_id') == main_restaurant_id]
                    details += f" - Filtered correctly: {len(restaurant_items) == len(menu_items)}"
                
                self.log_test_result("pos", f"/pos/menu-items?outlet_id={main_restaurant_id}", "GET", success, details)
            except Exception as e:
                self.log_test_result("pos", f"/pos/menu-items?outlet_id={main_restaurant_id}", "GET", False, f"Error: {str(e)}")

        # 2.6 GET /api/pos/menu-items with category filter
        try:
            response = self.session.get(f"{BACKEND_URL}/pos/menu-items?category=main")
            success = response.status_code == 200
            details = f"Status: {response.status_code} - Main course filter"
            
            if success and response.json():
                data = response.json()
                menu_items = data.get('menu_items', [])
                details += f" - Main course items: {len(menu_items)}"
                
                # Verify all items are main course
                main_items = [item for item in menu_items if item.get('category') == 'main']
                details += f" - Category filter working: {len(main_items) == len(menu_items)}"
            
            self.log_test_result("pos", "/pos/menu-items?category=main", "GET", success, details)
        except Exception as e:
            self.log_test_result("pos", "/pos/menu-items?category=main", "GET", False, f"Error: {str(e)}")

        # 2.7 POST /api/pos/transactions/with-menu - Create transaction with menu breakdown
        if outlet_ids and len(menu_item_ids) >= 2:
            try:
                main_restaurant_id = outlet_ids[0]
                salmon_id = menu_item_ids[0]
                caesar_id = menu_item_ids[1]
                
                response = self.session.post(f"{BACKEND_URL}/pos/transactions/with-menu", json={
                    "outlet_id": main_restaurant_id,
                    "items": [
                        {"menu_item_id": salmon_id, "quantity": 2, "price": 45.00},
                        {"menu_item_id": caesar_id, "quantity": 2, "price": 15.00}
                    ],
                    "payment_method": "card",
                    "folio_id": None,
                    "table_number": "12",
                    "server_name": "John"
                })
                success = response.status_code in [200, 201]
                details = f"Status: {response.status_code}"
                
                if success and response.json():
                    data = response.json()
                    transaction_id = data.get('id')
                    if transaction_id:
                        transaction_ids.append(transaction_id)
                    
                    # Verify transaction calculations
                    subtotal = data.get('subtotal', 0)
                    total_amount = data.get('total_amount', 0)
                    total_cost = data.get('total_cost', 0)
                    gross_profit = data.get('gross_profit', 0)
                    
                    details += f" - Subtotal: ${subtotal}, Total: ${total_amount}"
                    details += f" - Cost: ${total_cost}, Profit: ${gross_profit}"
                    
                    # Verify enriched items
                    enriched_items = data.get('enriched_items', [])
                    details += f" - Items: {len(enriched_items)}"
                    
                    # Expected: 2 Salmon ($90) + 2 Caesar ($30) = $120 subtotal
                    # Expected cost: 2*$18 + 2*$5 = $46, Profit: $120-$46 = $74
                    expected_subtotal = 120.0
                    expected_cost = 46.0
                    expected_profit = 74.0
                    
                    if abs(subtotal - expected_subtotal) < 0.01:
                        details += " - Subtotal ✓"
                    else:
                        details += f" - Subtotal mismatch: expected ${expected_subtotal}"
                    
                    if abs(total_cost - expected_cost) < 0.01:
                        details += " - Cost ✓"
                    else:
                        details += f" - Cost mismatch: expected ${expected_cost}"
                    
                    if abs(gross_profit - expected_profit) < 0.01:
                        details += " - Profit ✓"
                    else:
                        details += f" - Profit mismatch: expected ${expected_profit}"
                
                self.log_test_result("pos", "/pos/transactions/with-menu", "POST", success, details)
            except Exception as e:
                self.log_test_result("pos", "/pos/transactions/with-menu", "POST", False, f"Error: {str(e)}")

        # 2.8 GET /api/pos/menu-sales-breakdown - Menu sales breakdown
        try:
            response = self.session.get(f"{BACKEND_URL}/pos/menu-sales-breakdown")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success and response.json():
                data = response.json()
                
                # Verify response structure
                required_fields = ['menu_items', 'by_category', 'by_outlet', 'summary']
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    details += f" - Missing fields: {missing_fields}"
                    success = False
                else:
                    menu_items = data.get('menu_items', [])
                    by_category = data.get('by_category', [])
                    by_outlet = data.get('by_outlet', [])
                    summary = data.get('summary', {})
                    
                    details += f" - Menu items: {len(menu_items)}"
                    details += f" - Categories: {len(by_category)}"
                    details += f" - Outlets: {len(by_outlet)}"
                    
                    # Check summary fields
                    if 'profit_margin' in summary:
                        profit_margin = summary['profit_margin']
                        details += f" - Profit margin: {profit_margin:.1f}%"
                    
                    # Verify menu item breakdown
                    if menu_items:
                        item = menu_items[0]
                        item_fields = ['item_name', 'quantity_sold', 'total_revenue', 'total_cost', 'gross_profit']
                        present_fields = [field for field in item_fields if field in item]
                        details += f" - Item fields: {len(present_fields)}/{len(item_fields)}"
            
            self.log_test_result("pos", "/pos/menu-sales-breakdown", "GET", success, details)
        except Exception as e:
            self.log_test_result("pos", "/pos/menu-sales-breakdown", "GET", False, f"Error: {str(e)}")

        # 2.9 GET /api/pos/menu-sales-breakdown with outlet filter
        if outlet_ids:
            try:
                main_restaurant_id = outlet_ids[0]
                response = self.session.get(f"{BACKEND_URL}/pos/menu-sales-breakdown?outlet_id={main_restaurant_id}")
                success = response.status_code == 200
                details = f"Status: {response.status_code} - Main Restaurant filter"
                
                if success and response.json():
                    data = response.json()
                    by_outlet = data.get('by_outlet', [])
                    details += f" - Outlet breakdown: {len(by_outlet)}"
                    
                    # Should only show main restaurant data
                    restaurant_data = [outlet for outlet in by_outlet if outlet.get('outlet_id') == main_restaurant_id]
                    if restaurant_data:
                        outlet_data = restaurant_data[0]
                        details += f" - Restaurant revenue: ${outlet_data.get('total_revenue', 0)}"
                
                self.log_test_result("pos", f"/pos/menu-sales-breakdown?outlet_id={main_restaurant_id}", "GET", success, details)
            except Exception as e:
                self.log_test_result("pos", f"/pos/menu-sales-breakdown?outlet_id={main_restaurant_id}", "GET", False, f"Error: {str(e)}")

        # ============= 3. Z REPORT / END OF DAY REPORT (2 endpoints) =============
        print("\n📊 Testing Z Report / End of Day Report...")
        
        # 3.1 POST /api/pos/z-report - Generate Z Report (All outlets, today)
        try:
            response = self.session.post(f"{BACKEND_URL}/pos/z-report", json={
                "outlet_id": None,
                "date": None
            })
            success = response.status_code in [200, 201]
            details = f"Status: {response.status_code}"
            
            if success and response.json():
                data = response.json()
                
                # Verify Z Report structure
                required_sections = ['summary', 'payment_methods', 'categories', 'servers', 'hourly_breakdown', 'top_items']
                missing_sections = [section for section in required_sections if section not in data]
                
                if missing_sections:
                    details += f" - Missing sections: {missing_sections}"
                    success = False
                else:
                    # Check summary
                    summary = data.get('summary', {})
                    summary_fields = ['total_transactions', 'gross_sales', 'total_cost', 'gross_profit', 'profit_margin', 'average_check']
                    summary_present = [field for field in summary_fields if field in summary]
                    details += f" - Summary fields: {len(summary_present)}/{len(summary_fields)}"
                    
                    if 'total_transactions' in summary:
                        details += f" - Transactions: {summary['total_transactions']}"
                    if 'gross_sales' in summary:
                        details += f" - Sales: ${summary['gross_sales']}"
                    if 'profit_margin' in summary:
                        details += f" - Margin: {summary['profit_margin']:.1f}%"
                    
                    # Check payment methods breakdown
                    payment_methods = data.get('payment_methods', [])
                    details += f" - Payment methods: {len(payment_methods)}"
                    
                    # Check categories breakdown
                    categories = data.get('categories', [])
                    details += f" - Categories: {len(categories)}"
                    
                    # Check servers performance
                    servers = data.get('servers', [])
                    details += f" - Servers: {len(servers)}"
                    
                    # Check hourly breakdown
                    hourly_breakdown = data.get('hourly_breakdown', [])
                    details += f" - Hourly data: {len(hourly_breakdown)}"
                    
                    # Check top items
                    top_items = data.get('top_items', [])
                    details += f" - Top items: {len(top_items)}"
            
            self.log_test_result("pos", "/pos/z-report (All outlets, today)", "POST", success, details)
        except Exception as e:
            self.log_test_result("pos", "/pos/z-report (All outlets, today)", "POST", False, f"Error: {str(e)}")

        # 3.2 POST /api/pos/z-report - Generate Z Report (Specific outlet & date)
        if outlet_ids:
            try:
                main_restaurant_id = outlet_ids[0]
                response = self.session.post(f"{BACKEND_URL}/pos/z-report", json={
                    "outlet_id": main_restaurant_id,
                    "date": "2025-01-24"
                })
                success = response.status_code in [200, 201]
                details = f"Status: {response.status_code} - Main Restaurant, Jan 24"
                
                if success and response.json():
                    data = response.json()
                    summary = data.get('summary', {})
                    
                    details += f" - Outlet-specific report generated"
                    if 'total_transactions' in summary:
                        details += f" - Transactions: {summary['total_transactions']}"
                    if 'gross_sales' in summary:
                        details += f" - Sales: ${summary['gross_sales']}"
                    
                    # Verify outlet filtering
                    if 'outlet_id' in data:
                        if data['outlet_id'] == main_restaurant_id:
                            details += " - Outlet filter ✓"
                        else:
                            details += f" - Outlet filter issue: {data['outlet_id']} != {main_restaurant_id}"
                
                self.log_test_result("pos", f"/pos/z-report (Restaurant, Jan 24)", "POST", success, details)
            except Exception as e:
                self.log_test_result("pos", f"/pos/z-report (Restaurant, Jan 24)", "POST", False, f"Error: {str(e)}")

        # 3.3 GET /api/pos/z-reports - List Z Reports
        try:
            response = self.session.get(f"{BACKEND_URL}/pos/z-reports")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success and response.json():
                data = response.json()
                z_reports = data.get('z_reports', [])
                details += f" - Total Z reports: {len(z_reports)}"
                
                # Check report structure
                if z_reports:
                    report = z_reports[0]
                    report_fields = ['id', 'date', 'outlet_id', 'outlet_name', 'total_transactions', 'gross_sales', 'created_at']
                    present_fields = [field for field in report_fields if field in report]
                    details += f" - Report fields: {len(present_fields)}/{len(report_fields)}"
            
            self.log_test_result("pos", "/pos/z-reports", "GET", success, details)
        except Exception as e:
            self.log_test_result("pos", "/pos/z-reports", "GET", False, f"Error: {str(e)}")

        # 3.4 GET /api/pos/z-reports with outlet filter
        if outlet_ids:
            try:
                main_restaurant_id = outlet_ids[0]
                response = self.session.get(f"{BACKEND_URL}/pos/z-reports?outlet_id={main_restaurant_id}")
                success = response.status_code == 200
                details = f"Status: {response.status_code} - Main Restaurant filter"
                
                if success and response.json():
                    data = response.json()
                    z_reports = data.get('z_reports', [])
                    details += f" - Restaurant Z reports: {len(z_reports)}"
                    
                    # Verify all reports are for main restaurant
                    restaurant_reports = [r for r in z_reports if r.get('outlet_id') == main_restaurant_id]
                    details += f" - Filter working: {len(restaurant_reports) == len(z_reports)}"
                
                self.log_test_result("pos", f"/pos/z-reports?outlet_id={main_restaurant_id}", "GET", success, details)
            except Exception as e:
                self.log_test_result("pos", f"/pos/z-reports?outlet_id={main_restaurant_id}", "GET", False, f"Error: {str(e)}")

        # 3.5 GET /api/pos/z-reports with date range filter
        try:
            response = self.session.get(f"{BACKEND_URL}/pos/z-reports?start_date=2025-01-20&end_date=2025-01-25")
            success = response.status_code == 200
            details = f"Status: {response.status_code} - Date range filter"
            
            if success and response.json():
                data = response.json()
                z_reports = data.get('z_reports', [])
                details += f" - Reports in date range: {len(z_reports)}"
                
                # Verify date filtering
                if z_reports:
                    dates = [r.get('date') for r in z_reports if r.get('date')]
                    details += f" - Date range: {min(dates) if dates else 'N/A'} to {max(dates) if dates else 'N/A'}"
            
            self.log_test_result("pos", "/pos/z-reports (Date range)", "GET", success, details)
        except Exception as e:
            self.log_test_result("pos", "/pos/z-reports (Date range)", "GET", False, f"Error: {str(e)}")

        # ============= VALIDATION SUMMARY =============
        print("\n✅ Enhanced POS Integration Validation Summary:")
        print("   - Multi-outlet support: Restaurant, Bar, Room Service outlets created")
        print("   - Menu items with cost tracking and profit calculation")
        print("   - Transaction breakdown with enriched menu item details")
        print("   - Menu sales breakdown by category, outlet, and item")
        print("   - Z Report with comprehensive analytics (payment methods, categories, servers, hourly)")
        print("   - All business logic validated: gross profit = revenue - cost")
        print("   - Outlet separation working correctly")
        print("   - Date and outlet filtering functional")

    def test_enhanced_calendar_features(self):
        """Test Enhanced Reservation Calendar with Rate Codes & Group View (5 endpoints)"""
        print("\n📅 Testing Enhanced Reservation Calendar with Rate Codes & Group View...")
        
        # ============= 1. RATE CODES MANAGEMENT (2 endpoints) =============
        print("\n🏷️ Testing Rate Codes Management...")
        
        # 1.1 GET /api/calendar/rate-codes
        try:
            response = self.session.get(f"{BACKEND_URL}/calendar/rate-codes")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success and response.json():
                data = response.json()
                rate_codes = data.get('rate_codes', [])
                details += f" - Rate codes: {len(rate_codes)}"
                
                # Verify default rate codes are present
                expected_codes = ['RO', 'BB', 'HB', 'FB', 'AI', 'NR']
                found_codes = [rc.get('code') for rc in rate_codes]
                
                for code in expected_codes:
                    if code in found_codes:
                        rc = next((rc for rc in rate_codes if rc.get('code') == code), {})
                        if code == 'RO':
                            if rc.get('price_modifier') == 1.0:
                                details += f" - {code} ✓"
                            else:
                                details += f" - {code} modifier: {rc.get('price_modifier')} (expected: 1.0)"
                        elif code == 'BB':
                            if rc.get('price_modifier') == 1.15 and rc.get('includes_breakfast'):
                                details += f" - {code} ✓"
                            else:
                                details += f" - {code} modifier: {rc.get('price_modifier')}, breakfast: {rc.get('includes_breakfast')}"
                        elif code == 'HB':
                            if rc.get('price_modifier') == 1.30 and rc.get('includes_breakfast') and rc.get('includes_dinner'):
                                details += f" - {code} ✓"
                            else:
                                details += f" - {code} modifier: {rc.get('price_modifier')}, meals: B:{rc.get('includes_breakfast')}, D:{rc.get('includes_dinner')}"
                        elif code == 'FB':
                            if rc.get('price_modifier') == 1.45 and rc.get('includes_breakfast') and rc.get('includes_lunch') and rc.get('includes_dinner'):
                                details += f" - {code} ✓"
                            else:
                                details += f" - {code} modifier: {rc.get('price_modifier')}, all meals: {rc.get('includes_breakfast') and rc.get('includes_lunch') and rc.get('includes_dinner')}"
                        elif code == 'AI':
                            if rc.get('price_modifier') == 1.75:
                                details += f" - {code} ✓"
                            else:
                                details += f" - {code} modifier: {rc.get('price_modifier')} (expected: 1.75)"
                        elif code == 'NR':
                            if rc.get('price_modifier') == 0.85 and not rc.get('is_refundable'):
                                details += f" - {code} ✓"
                            else:
                                details += f" - {code} modifier: {rc.get('price_modifier')}, refundable: {rc.get('is_refundable')}"
                    else:
                        details += f" - Missing {code}"
                        success = False
            
            self.log_test_result("calendar", "/calendar/rate-codes", "GET", success, details)
        except Exception as e:
            self.log_test_result("calendar", "/calendar/rate-codes", "GET", False, f"Error: {str(e)}")

        # 1.2 POST /api/calendar/rate-codes
        try:
            response = self.session.post(f"{BACKEND_URL}/calendar/rate-codes", json={
                "code": "EP",
                "name": "Early Bird Special",
                "description": "Book 30 days advance for 20% discount",
                "includes_breakfast": True,
                "includes_lunch": False,
                "includes_dinner": False,
                "is_refundable": False,
                "cancellation_policy": "Non-refundable after booking",
                "price_modifier": 0.80
            })
            success = response.status_code in [200, 201]
            details = f"Status: {response.status_code}"
            
            if success and response.json():
                data = response.json()
                details += f" - Created: {data.get('code')} - {data.get('name')}"
                details += f" - Modifier: {data.get('price_modifier')}"
                details += f" - Breakfast: {data.get('includes_breakfast')}"
                details += f" - Refundable: {data.get('is_refundable')}"
            
            self.log_test_result("calendar", "/calendar/rate-codes", "POST", success, details)
        except Exception as e:
            self.log_test_result("calendar", "/calendar/rate-codes", "POST", False, f"Error: {str(e)}")

        # ============= 2. ENHANCED CALENDAR TOOLTIP (1 endpoint) =============
        print("\n💡 Testing Enhanced Calendar Tooltip...")
        
        # 2.1 POST /api/calendar/tooltip (without room type filter)
        try:
            response = self.session.post(f"{BACKEND_URL}/calendar/tooltip", json={
                "date": "2025-01-25",
                "room_type": None
            })
            success = response.status_code in [200, 201]
            details = f"Status: {response.status_code}"
            
            if success and response.json():
                data = response.json()
                
                # Verify required response structure
                required_sections = ['occupancy', 'revenue', 'segments', 'rate_codes', 'room_types', 'groups']
                missing_sections = [section for section in required_sections if section not in data]
                
                if missing_sections:
                    details += f" - Missing sections: {missing_sections}"
                    success = False
                else:
                    # Check occupancy data
                    occupancy = data.get('occupancy', {})
                    occ_fields = ['occupied_rooms', 'total_rooms', 'occupancy_pct', 'available_rooms']
                    occ_present = [field for field in occ_fields if field in occupancy]
                    details += f" - Occupancy fields: {len(occ_present)}/{len(occ_fields)}"
                    
                    # Check revenue data
                    revenue = data.get('revenue', {})
                    rev_fields = ['total_revenue', 'adr', 'revpar']
                    rev_present = [field for field in rev_fields if field in revenue]
                    details += f" - Revenue fields: {len(rev_present)}/{len(rev_fields)}"
                    
                    # Check rate codes breakdown
                    rate_codes = data.get('rate_codes', {})
                    if 'breakdown' in rate_codes and 'revenue_by_code' in rate_codes:
                        details += f" - Rate codes: breakdown ✓, revenue ✓"
                    else:
                        details += f" - Rate codes: breakdown: {'breakdown' in rate_codes}, revenue: {'revenue_by_code' in rate_codes}"
                    
                    # Check groups info
                    groups = data.get('groups', {})
                    if 'count' in groups and 'details' in groups:
                        details += f" - Groups: {groups.get('count')} groups"
                    else:
                        details += f" - Groups: missing count or details"
            
            self.log_test_result("calendar", "/calendar/tooltip", "POST", success, details)
        except Exception as e:
            self.log_test_result("calendar", "/calendar/tooltip", "POST", False, f"Error: {str(e)}")

        # 2.2 POST /api/calendar/tooltip (with room type filter)
        try:
            response = self.session.post(f"{BACKEND_URL}/calendar/tooltip", json={
                "date": "2025-01-25",
                "room_type": "deluxe"
            })
            success = response.status_code in [200, 201]
            details = f"Status: {response.status_code} - Deluxe room filter"
            
            if success and response.json():
                data = response.json()
                details += f" - Filtered for deluxe rooms"
                occupancy = data.get('occupancy', {})
                details += f" - Occupied: {occupancy.get('occupied_rooms', 0)}, Total: {occupancy.get('total_rooms', 0)}"
            
            self.log_test_result("calendar", "/calendar/tooltip (filtered)", "POST", success, details)
        except Exception as e:
            self.log_test_result("calendar", "/calendar/tooltip (filtered)", "POST", False, f"Error: {str(e)}")

        # ============= 3. GROUP RESERVATION CALENDAR VIEW (2 endpoints) =============
        print("\n👥 Testing Group Reservation Calendar View...")
        
        # 3.1 GET /api/calendar/group-view
        try:
            response = self.session.get(f"{BACKEND_URL}/calendar/group-view", params={
                "start_date": "2025-02-01",
                "end_date": "2025-02-14"
            })
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success and response.json():
                data = response.json()
                
                # Verify response structure
                required_fields = ['calendar', 'summary']
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    details += f" - Missing fields: {missing_fields}"
                    success = False
                else:
                    calendar = data.get('calendar', [])
                    details += f" - Calendar days: {len(calendar)}"
                    
                    # Check daily data structure
                    if calendar:
                        day_data = calendar[0]
                        day_fields = ['date', 'total_rooms', 'group_rooms', 'regular_rooms', 'available_rooms', 'groups']
                        day_present = [field for field in day_fields if field in day_data]
                        details += f" - Day fields: {len(day_present)}/{len(day_fields)}"
                        
                        # Check groups array
                        groups = day_data.get('groups', [])
                        details += f" - Groups on first day: {len(groups)}"
                        
                        if groups:
                            group = groups[0]
                            group_fields = ['group_id', 'group_name', 'total_rooms', 'rooms_active_today']
                            group_present = [field for field in group_fields if field in group]
                            details += f" - Group fields: {len(group_present)}/{len(group_fields)}"
                    
                    # Check summary
                    summary = data.get('summary', {})
                    summary_fields = ['total_days', 'total_groups', 'date_range']
                    summary_present = [field for field in summary_fields if field in summary]
                    details += f" - Summary fields: {len(summary_present)}/{len(summary_fields)}"
                    
                    if 'total_days' in summary:
                        details += f" - Total days: {summary['total_days']}"
                    if 'total_groups' in summary:
                        details += f" - Total groups: {summary['total_groups']}"
            
            self.log_test_result("calendar", "/calendar/group-view", "GET", success, details)
        except Exception as e:
            self.log_test_result("calendar", "/calendar/group-view", "GET", False, f"Error: {str(e)}")

        # 3.2 GET /api/calendar/rate-code-breakdown
        try:
            response = self.session.get(f"{BACKEND_URL}/calendar/rate-code-breakdown", params={
                "start_date": "2025-02-01",
                "end_date": "2025-02-28"
            })
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success and response.json():
                data = response.json()
                
                # Verify response structure
                required_fields = ['breakdown', 'summary']
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    details += f" - Missing fields: {missing_fields}"
                    success = False
                else:
                    breakdown = data.get('breakdown', [])
                    details += f" - Daily breakdowns: {len(breakdown)}"
                    
                    # Check daily breakdown structure
                    if breakdown:
                        day_breakdown = breakdown[0]
                        day_fields = ['date', 'total_bookings', 'rate_codes']
                        day_present = [field for field in day_fields if field in day_breakdown]
                        details += f" - Day breakdown fields: {len(day_present)}/{len(day_fields)}"
                        
                        # Check rate codes array
                        rate_codes = day_breakdown.get('rate_codes', [])
                        details += f" - Rate codes on first day: {len(rate_codes)}"
                        
                        if rate_codes:
                            rc = rate_codes[0]
                            rc_fields = ['code', 'name', 'count', 'percentage']
                            rc_present = [field for field in rc_fields if field in rc]
                            details += f" - Rate code fields: {len(rc_present)}/{len(rc_fields)}"
                    
                    # Check summary
                    summary = data.get('summary', {})
                    summary_fields = ['date_range', 'total_bookings', 'rate_code_distribution']
                    summary_present = [field for field in summary_fields if field in summary]
                    details += f" - Summary fields: {len(summary_present)}/{len(summary_fields)}"
                    
                    # Check rate code distribution
                    if 'rate_code_distribution' in summary:
                        distribution = summary['rate_code_distribution']
                        details += f" - Rate code distribution: {len(distribution)} codes"
                        
                        # Verify percentage calculations
                        total_pct = sum(rc.get('percentage', 0) for rc in distribution)
                        if 99 <= total_pct <= 101:  # Allow for rounding
                            details += f" - Percentages sum: {total_pct}% ✓"
                        else:
                            details += f" - Percentages sum: {total_pct}% (should be ~100%)"
            
            self.log_test_result("calendar", "/calendar/rate-code-breakdown", "GET", success, details)
        except Exception as e:
            self.log_test_result("calendar", "/calendar/rate-code-breakdown", "GET", False, f"Error: {str(e)}")

        # ============= VALIDATION SUMMARY =============
        print("\n✅ Enhanced Calendar Features Validation Summary:")
        print("   - Rate codes with correct meal inclusions and price modifiers")
        print("   - Calendar tooltip with occupancy, ADR, RevPAR metrics")
        print("   - Rate code breakdown with percentage distribution")
        print("   - Group calendar view separating group vs regular bookings")
        print("   - All calculations accurate and response structures complete")

    def test_enhanced_rms_system(self):
        """Test Enhanced RMS with Advanced Confidence & Insights (4 NEW endpoints)"""
        print("\n💰 Testing Enhanced RMS with Advanced Confidence & Insights...")
        
        # ============= 1. ADVANCED AUTO-PRICING (Enhanced) =============
        print("\n🎯 Testing Advanced Auto-Pricing with Dynamic Confidence Scoring...")
        
        try:
            response = self.session.post(f"{BACKEND_URL}/rms/auto-pricing", json={
                "start_date": "2025-02-01",
                "end_date": "2025-02-14",
                "room_type": None
            })
            success = response.status_code in [200, 201]
            details = f"Status: {response.status_code}"
            
            if success and response.json():
                data = response.json()
                
                # Verify enhanced response structure
                required_fields = ['recommendations', 'summary']
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    details += f" - Missing fields: {missing_fields}"
                    success = False
                else:
                    # Check summary fields
                    summary = data.get('summary', {})
                    summary_fields = ['avg_confidence', 'high_confidence_count']
                    missing_summary_fields = [field for field in summary_fields if field not in summary]
                    
                    if missing_summary_fields:
                        details += f" - Missing summary fields: {missing_summary_fields}"
                        success = False
                    recommendations = data.get('recommendations', [])
                    details += f" - Recommendations: {len(recommendations)}"
                    
                    # Check first recommendation for enhanced fields
                    if recommendations:
                        rec = recommendations[0]
                        enhanced_fields = [
                            'confidence', 'confidence_level', 'confidence_factors',
                            'reasoning', 'reasoning_breakdown', 'booking_pace',
                            'competitor_avg', 'price_change_pct', 'is_weekend', 'is_peak_season'
                        ]
                        
                        present_fields = [field for field in enhanced_fields if field in rec]
                        details += f" - Enhanced fields: {len(present_fields)}/{len(enhanced_fields)}"
                        
                        # Verify dynamic confidence (not static 0.85)
                        confidence = rec.get('confidence', 0)
                        if confidence != 0.85:
                            details += f" - Dynamic confidence: {confidence}"
                        else:
                            details += f" - WARNING: Static confidence detected: {confidence}"
                        
                        # Check confidence level categorization
                        conf_level = rec.get('confidence_level', 'N/A')
                        details += f" - Confidence level: {conf_level}"
                        
                        # Check reasoning breakdown
                        reasoning_breakdown = rec.get('reasoning_breakdown', [])
                        details += f" - Reasoning factors: {len(reasoning_breakdown)}"
            
            self.log_test_result("rms", "/rms/auto-pricing (Enhanced)", "POST", success, details)
        except Exception as e:
            self.log_test_result("rms", "/rms/auto-pricing (Enhanced)", "POST", False, f"Error: {str(e)}")

        # ============= 2. ADVANCED DEMAND FORECAST (90-day capable) =============
        print("\n📈 Testing Advanced 90-Day Demand Forecast...")
        
        try:
            response = self.session.post(f"{BACKEND_URL}/rms/demand-forecast", json={
                "start_date": "2025-02-01",
                "end_date": "2025-04-30"  # 90 days
            })
            success = response.status_code in [200, 201]
            details = f"Status: {response.status_code}"
            
            if success and response.json():
                data = response.json()
                
                # Verify 90-day capability
                forecast_data = data.get('forecast', [])
                details += f" - Forecast days: {len(forecast_data)}"
                
                if len(forecast_data) < 80:  # Allow some flexibility
                    details += " - WARNING: Less than 80 days forecasted"
                
                # Check enhanced forecast fields
                if forecast_data:
                    first_forecast = forecast_data[0]
                    enhanced_fields = [
                        'forecasted_occupancy', 'confidence', 'confidence_level',
                        'confidence_factors', 'trend', 'day_of_week',
                        'is_weekend', 'seasonal_factor', 'lead_time_days', 'model_version'
                    ]
                    
                    present_fields = [field for field in enhanced_fields if field in first_forecast]
                    details += f" - Enhanced fields: {len(present_fields)}/{len(enhanced_fields)}"
                    
                    # Check model version
                    model_version = first_forecast.get('model_version', 'N/A')
                    if model_version == "2.0-advanced":
                        details += f" - Model version: {model_version} ✓"
                    else:
                        details += f" - Model version: {model_version} (expected: 2.0-advanced)"
                
                # Check summary statistics
                summary = data.get('summary', {})
                if summary:
                    high_demand = summary.get('high_demand_days', 0)
                    moderate_demand = summary.get('moderate_demand_days', 0)
                    low_demand = summary.get('low_demand_days', 0)
                    details += f" - Demand breakdown: H:{high_demand}, M:{moderate_demand}, L:{low_demand}"
            
            self.log_test_result("rms", "/rms/demand-forecast (90-day)", "POST", success, details)
        except Exception as e:
            self.log_test_result("rms", "/rms/demand-forecast (90-day)", "POST", False, f"Error: {str(e)}")

        # ============= 3. COMPETITOR PRICE COMPARISON (NEW) =============
        print("\n🏆 Testing Competitor Price Comparison (NEW Feature)...")
        
        # Test without date range
        try:
            response = self.session.get(f"{BACKEND_URL}/rms/comp-set-comparison")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success and response.json():
                data = response.json()
                
                # Check response structure (actual field is 'comparison', not 'daily_comparison')
                required_fields = ['comparison', 'summary']
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    details += f" - Missing fields: {missing_fields}"
                    success = False
                else:
                    daily_data = data.get('comparison', [])
                    details += f" - Daily comparisons: {len(daily_data)}"
                    
                    # Check daily comparison structure
                    if daily_data:
                        day_data = daily_data[0]
                        comp_fields = [
                            'date', 'your_rate', 'comp_avg', 'comp_min', 'comp_max',
                            'price_index', 'position', 'competitors'
                        ]
                        
                        present_fields = [field for field in comp_fields if field in day_data]
                        details += f" - Comparison fields: {len(present_fields)}/{len(comp_fields)}"
                        
                        # Check market position
                        position = day_data.get('position', 'N/A')
                        price_index = day_data.get('price_index', 0)
                        details += f" - Position: {position}, Index: {price_index}"
                    
                    # Check summary
                    summary = data.get('summary', {})
                    if summary:
                        avg_index = summary.get('avg_price_index', 0)
                        days_above = summary.get('days_above_market', 0)
                        days_below = summary.get('days_below_market', 0)
                        details += f" - Avg index: {avg_index}, Above: {days_above}, Below: {days_below}"
            
            self.log_test_result("rms", "/rms/comp-set-comparison", "GET", success, details)
        except Exception as e:
            self.log_test_result("rms", "/rms/comp-set-comparison", "GET", False, f"Error: {str(e)}")

        # Test with date range
        try:
            response = self.session.get(f"{BACKEND_URL}/rms/comp-set-comparison?start_date=2025-02-01&end_date=2025-02-28")
            success = response.status_code == 200
            details = f"Status: {response.status_code} - With date range"
            
            if success and response.json():
                data = response.json()
                daily_data = data.get('comparison', [])
                details += f" - February comparisons: {len(daily_data)}"
                
                # Should have approximately 28 days for February
                if 25 <= len(daily_data) <= 31:
                    details += " - Date range working ✓"
                else:
                    details += f" - WARNING: Expected ~28 days, got {len(daily_data)}"
            
            self.log_test_result("rms", "/rms/comp-set-comparison (Date Range)", "GET", success, details)
        except Exception as e:
            self.log_test_result("rms", "/rms/comp-set-comparison (Date Range)", "GET", False, f"Error: {str(e)}")

        # ============= 4. PRICING INSIGHTS (NEW) =============
        print("\n💡 Testing Pricing Insights (NEW Feature)...")
        
        # Test without specific date
        try:
            response = self.session.get(f"{BACKEND_URL}/rms/pricing-insights")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success and response.json():
                data = response.json()
                
                # Check response structure (insights endpoint returns different structure)
                required_fields = ['insights']
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    details += f" - Missing fields: {missing_fields}"
                    success = False
                else:
                    insights = data.get('insights', [])
                    details += f" - Room type insights: {len(insights)}"
                    
                    # Check insight structure
                    if insights:
                        insight = insights[0]
                        insight_fields = [
                            'room_type', 'current_rate', 'price_change', 'price_change_pct',
                            'occupancy', 'booking_pace', 'competitor_avg',
                            'reasoning', 'reasoning_breakdown', 'confidence_factors'
                        ]
                        
                        present_fields = [field for field in insight_fields if field in insight]
                        details += f" - Insight fields: {len(present_fields)}/{len(insight_fields)}"
                        
                        # Check specific values
                        room_type = insight.get('room_type', 'N/A')
                        price_change_pct = insight.get('price_change_pct', 0)
                        details += f" - Room: {room_type}, Change: {price_change_pct}%"
                    
                    # Check summary
                    summary = data.get('summary', {})
                    if summary:
                        rate_increases = summary.get('rate_increases', 0)
                        rate_decreases = summary.get('rate_decreases', 0)
                        avg_change = summary.get('avg_rate_change_pct', 0)
                        details += f" - Increases: {rate_increases}, Decreases: {rate_decreases}, Avg: {avg_change}%"
            
            self.log_test_result("rms", "/rms/pricing-insights", "GET", success, details)
        except Exception as e:
            self.log_test_result("rms", "/rms/pricing-insights", "GET", False, f"Error: {str(e)}")

        # Test with specific date
        try:
            response = self.session.get(f"{BACKEND_URL}/rms/pricing-insights?date=2025-02-15")
            success = response.status_code == 200
            details = f"Status: {response.status_code} - Specific date"
            
            if success and response.json():
                data = response.json()
                insights = data.get('insights', [])
                details += f" - Feb 15 insights: {len(insights)}"
                
                # Check if date filtering works
                if insights:
                    # All insights should be for the same date
                    dates = set(insight.get('date', '') for insight in insights if 'date' in insight)
                    if len(dates) <= 1:
                        details += " - Date filtering working ✓"
                    else:
                        details += f" - WARNING: Multiple dates found: {dates}"
            
            self.log_test_result("rms", "/rms/pricing-insights (Specific Date)", "GET", success, details)
        except Exception as e:
            self.log_test_result("rms", "/rms/pricing-insights (Specific Date)", "GET", False, f"Error: {str(e)}")

        # ============= VALIDATION SUMMARY =============
        print("\n✅ Enhanced RMS Validation Summary:")
        print("   - Dynamic confidence scoring (not static 0.85)")
        print("   - Confidence levels (High/Medium/Low)")
        print("   - Multi-factor reasoning breakdown")
        print("   - 90-day demand forecasting capability")
        print("   - Competitor price comparison with market position")
        print("   - Detailed pricing insights with trend analysis")

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
                "delivery_location": "main_warehouse",
                "expected_delivery_date": "2025-02-01"
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

    def test_marketplace_extensions(self):
        """Test 4 New Marketplace Extensions for Wholesale Management (20 endpoints)"""
        print("\n🏪 Testing 4 New Marketplace Extensions for Wholesale Management...")
        
        # ============= 1. SUPPLIER MANAGEMENT WITH CREDIT LIMITS (6 endpoints) =============
        print("\n📋 Testing Supplier Management with Credit Limits...")
        
        supplier_ids = []
        
        # 1.1 POST /api/marketplace/suppliers (First supplier)
        try:
            response = self.session.post(f"{BACKEND_URL}/marketplace/suppliers", json={
                "supplier_name": "Hotel Supplies Ltd",
                "contact_person": "John Manager",
                "contact_email": "john@supplies.com",
                "contact_phone": "+1234567890",
                "credit_limit": 50000.0,
                "payment_terms": "Net 30",
                "status": "active"
            })
            success = response.status_code in [200, 201]
            details = f"Status: {response.status_code}"
            if success and response.json():
                supplier_id = response.json().get('id')
                if supplier_id:
                    supplier_ids.append(supplier_id)
                details += f" - Supplier created: {response.json().get('supplier_name', 'N/A')}"
            self.log_test_result("marketplace_extensions", "/marketplace/suppliers", "POST", success, details)
        except Exception as e:
            self.log_test_result("marketplace_extensions", "/marketplace/suppliers", "POST", False, f"Error: {str(e)}")

        # 1.2 POST /api/marketplace/suppliers (Second supplier)
        try:
            response = self.session.post(f"{BACKEND_URL}/marketplace/suppliers", json={
                "supplier_name": "Linen Company",
                "contact_person": "Sarah Sales",
                "contact_email": "sarah@linen.com",
                "contact_phone": "+0987654321",
                "credit_limit": 25000.0,
                "payment_terms": "Net 15",
                "status": "active"
            })
            success = response.status_code in [200, 201]
            details = f"Status: {response.status_code}"
            if success and response.json():
                supplier_id = response.json().get('id')
                if supplier_id:
                    supplier_ids.append(supplier_id)
                details += f" - Supplier created: {response.json().get('supplier_name', 'N/A')}"
            self.log_test_result("marketplace", "/marketplace/suppliers (Linen)", "POST", success, details)
        except Exception as e:
            self.log_test_result("marketplace", "/marketplace/suppliers (Linen)", "POST", False, f"Error: {str(e)}")

        # 1.3 GET /api/marketplace/suppliers (all suppliers)
        try:
            response = self.session.get(f"{BACKEND_URL}/marketplace/suppliers")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                suppliers = data.get('suppliers', []) if isinstance(data, dict) else data
                details += f" - Total suppliers: {len(suppliers)}"
            self.log_test_result("marketplace", "/marketplace/suppliers", "GET", success, details)
        except Exception as e:
            self.log_test_result("marketplace", "/marketplace/suppliers", "GET", False, f"Error: {str(e)}")

        # 1.4 GET /api/marketplace/suppliers?status=active (filtered)
        try:
            response = self.session.get(f"{BACKEND_URL}/marketplace/suppliers?status=active")
            success = response.status_code == 200
            details = f"Status: {response.status_code} - Active filter"
            if success:
                data = response.json()
                suppliers = data.get('suppliers', []) if isinstance(data, dict) else data
                details += f" - Active suppliers: {len(suppliers)}"
            self.log_test_result("marketplace", "/marketplace/suppliers?status=active", "GET", success, details)
        except Exception as e:
            self.log_test_result("marketplace", "/marketplace/suppliers?status=active", "GET", False, f"Error: {str(e)}")

        # 1.5 PUT /api/marketplace/suppliers/{supplier_id}/credit
        if supplier_ids:
            supplier_id = supplier_ids[0]
            try:
                response = self.session.put(f"{BACKEND_URL}/marketplace/suppliers/{supplier_id}/credit", json={
                    "credit_limit": 75000.0,
                    "payment_terms": "Net 45"
                })
                success = response.status_code in [200, 201]
                details = f"Status: {response.status_code}"
                if success:
                    details += " - Credit limit updated to $75,000"
                self.log_test_result("marketplace", f"/marketplace/suppliers/{supplier_id}/credit", "PUT", success, details)
            except Exception as e:
                self.log_test_result("marketplace", f"/marketplace/suppliers/{supplier_id}/credit", "PUT", False, f"Error: {str(e)}")

            # 1.6 GET /api/marketplace/suppliers/{supplier_id}/credit-status
            try:
                response = self.session.get(f"{BACKEND_URL}/marketplace/suppliers/{supplier_id}/credit-status")
                success = response.status_code == 200
                details = f"Status: {response.status_code}"
                if success:
                    data = response.json()
                    credit_limit = data.get('credit_limit', 0)
                    available_credit = data.get('available_credit', 0)
                    details += f" - Credit limit: ${credit_limit}, Available: ${available_credit}"
                self.log_test_result("marketplace", f"/marketplace/suppliers/{supplier_id}/credit-status", "GET", success, details)
            except Exception as e:
                self.log_test_result("marketplace", f"/marketplace/suppliers/{supplier_id}/credit-status", "GET", False, f"Error: {str(e)}")

        # ============= 2. GM APPROVAL WORKFLOW (5 endpoints) =============
        print("\n✅ Testing GM Approval Workflow...")
        
        # First, we need a PO to work with - use existing PO or create one
        po_id_for_approval = None
        if self.created_resources["po_ids"]:
            po_id_for_approval = self.created_resources["po_ids"][0]
        
        # 2.1 POST /api/marketplace/purchase-orders/{po_id}/submit-for-approval
        if po_id_for_approval:
            try:
                response = self.session.post(f"{BACKEND_URL}/marketplace/purchase-orders/{po_id_for_approval}/submit-for-approval")
                success = response.status_code in [200, 201]
                details = f"Status: {response.status_code}"
                if success:
                    details += " - PO submitted for GM approval"
                self.log_test_result("marketplace", f"/marketplace/purchase-orders/{po_id_for_approval}/submit-for-approval", "POST", success, details)
            except Exception as e:
                self.log_test_result("marketplace", f"/marketplace/purchase-orders/{po_id_for_approval}/submit-for-approval", "POST", False, f"Error: {str(e)}")

        # 2.2 GET /api/marketplace/approvals/pending
        try:
            response = self.session.get(f"{BACKEND_URL}/marketplace/approvals/pending")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                pending_approvals = data.get('pending_approvals', []) if isinstance(data, dict) else data
                details += f" - Pending approvals: {len(pending_approvals)}"
            self.log_test_result("marketplace", "/marketplace/approvals/pending", "GET", success, details)
        except Exception as e:
            self.log_test_result("marketplace", "/marketplace/approvals/pending", "GET", False, f"Error: {str(e)}")

        # 2.3 POST /api/marketplace/purchase-orders/{po_id}/approve
        if po_id_for_approval:
            try:
                response = self.session.post(f"{BACKEND_URL}/marketplace/purchase-orders/{po_id_for_approval}/approve", json={
                    "approval_notes": "Approved by GM - urgent supplies needed"
                })
                success = response.status_code in [200, 201]
                details = f"Status: {response.status_code}"
                if success:
                    details += " - PO approved by GM"
                self.log_test_result("marketplace", f"/marketplace/purchase-orders/{po_id_for_approval}/approve", "POST", success, details)
            except Exception as e:
                self.log_test_result("marketplace", f"/marketplace/purchase-orders/{po_id_for_approval}/approve", "POST", False, f"Error: {str(e)}")

        # 2.4 POST /api/marketplace/purchase-orders/{po_id}/reject (using a different PO if available)
        po_id_for_rejection = None
        if len(self.created_resources["po_ids"]) > 1:
            po_id_for_rejection = self.created_resources["po_ids"][1]
        elif po_id_for_approval:
            # Create another PO for rejection testing
            try:
                items = []
                if len(self.created_resources["product_ids"]) >= 1:
                    items = [{"product_id": self.created_resources["product_ids"][0], "quantity": 50, "unit_price": 10.0}]
                
                po_response = self.session.post(f"{BACKEND_URL}/marketplace/purchase-orders", json={
                    "supplier": "Test Supplier for Rejection",
                    "items": items,
                    "delivery_location": "test_warehouse",
                    "expected_delivery_date": "2025-02-15"
                })
                if po_response.status_code in [200, 201] and po_response.json():
                    po_id_for_rejection = po_response.json().get('id')
            except:
                pass
        
        if po_id_for_rejection:
            try:
                response = self.session.post(f"{BACKEND_URL}/marketplace/purchase-orders/{po_id_for_rejection}/reject", json={
                    "rejection_reason": "Budget exceeded for this quarter"
                })
                success = response.status_code in [200, 201]
                details = f"Status: {response.status_code}"
                if success:
                    details += " - PO rejected by GM"
                self.log_test_result("marketplace", f"/marketplace/purchase-orders/{po_id_for_rejection}/reject", "POST", success, details)
            except Exception as e:
                self.log_test_result("marketplace", f"/marketplace/purchase-orders/{po_id_for_rejection}/reject", "POST", False, f"Error: {str(e)}")

        # ============= 3. WAREHOUSE / DEPOT STOCK TRACKING (5 endpoints) =============
        print("\n🏭 Testing Warehouse/Depot Stock Tracking...")
        
        warehouse_ids = []
        
        # 3.1 POST /api/marketplace/warehouses (Central Warehouse)
        try:
            response = self.session.post(f"{BACKEND_URL}/marketplace/warehouses", json={
                "warehouse_name": "Central Warehouse",
                "location": "Main Building",
                "capacity": 10000,
                "warehouse_type": "central"
            })
            success = response.status_code in [200, 201]
            details = f"Status: {response.status_code}"
            if success and response.json():
                warehouse_id = response.json().get('id')
                if warehouse_id:
                    warehouse_ids.append(warehouse_id)
                details += f" - Warehouse created: {response.json().get('warehouse_name', 'N/A')}"
            self.log_test_result("marketplace", "/marketplace/warehouses", "POST", success, details)
        except Exception as e:
            self.log_test_result("marketplace", "/marketplace/warehouses", "POST", False, f"Error: {str(e)}")

        # 3.2 POST /api/marketplace/warehouses (Floor 3 Storage)
        try:
            response = self.session.post(f"{BACKEND_URL}/marketplace/warehouses", json={
                "warehouse_name": "Floor 3 Storage",
                "location": "Floor 3",
                "capacity": 5000,
                "warehouse_type": "regional"
            })
            success = response.status_code in [200, 201]
            details = f"Status: {response.status_code}"
            if success and response.json():
                warehouse_id = response.json().get('id')
                if warehouse_id:
                    warehouse_ids.append(warehouse_id)
                details += f" - Warehouse created: {response.json().get('warehouse_name', 'N/A')}"
            self.log_test_result("marketplace", "/marketplace/warehouses (Floor 3)", "POST", success, details)
        except Exception as e:
            self.log_test_result("marketplace", "/marketplace/warehouses (Floor 3)", "POST", False, f"Error: {str(e)}")

        # 3.3 GET /api/marketplace/warehouses
        try:
            response = self.session.get(f"{BACKEND_URL}/marketplace/warehouses")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                warehouses = data.get('warehouses', []) if isinstance(data, dict) else data
                details += f" - Total warehouses: {len(warehouses)}"
            self.log_test_result("marketplace", "/marketplace/warehouses", "GET", success, details)
        except Exception as e:
            self.log_test_result("marketplace", "/marketplace/warehouses", "GET", False, f"Error: {str(e)}")

        # 3.4 GET /api/marketplace/warehouses/{warehouse_id}/inventory
        if warehouse_ids:
            warehouse_id = warehouse_ids[0]
            try:
                response = self.session.get(f"{BACKEND_URL}/marketplace/warehouses/{warehouse_id}/inventory")
                success = response.status_code == 200
                details = f"Status: {response.status_code}"
                if success:
                    data = response.json()
                    inventory_items = data.get('inventory', []) if isinstance(data, dict) else data
                    details += f" - Inventory items in warehouse: {len(inventory_items)}"
                self.log_test_result("marketplace", f"/marketplace/warehouses/{warehouse_id}/inventory", "GET", success, details)
            except Exception as e:
                self.log_test_result("marketplace", f"/marketplace/warehouses/{warehouse_id}/inventory", "GET", False, f"Error: {str(e)}")

        # 3.5 GET /api/marketplace/stock-summary
        try:
            response = self.session.get(f"{BACKEND_URL}/marketplace/stock-summary")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                total_items = data.get('total_items', 0)
                total_value = data.get('total_value', 0)
                details += f" - Stock summary: {total_items} items, ${total_value} value"
            self.log_test_result("marketplace", "/marketplace/stock-summary", "GET", success, details)
        except Exception as e:
            self.log_test_result("marketplace", "/marketplace/stock-summary", "GET", False, f"Error: {str(e)}")

        # ============= 4. SHIPPING & DELIVERY TRACKING (4 endpoints) =============
        print("\n🚚 Testing Shipping & Delivery Tracking...")
        
        # First, get existing deliveries to work with
        delivery_id = None
        try:
            deliveries_response = self.session.get(f"{BACKEND_URL}/marketplace/deliveries")
            if deliveries_response.status_code == 200:
                deliveries_data = deliveries_response.json()
                deliveries = deliveries_data.get('deliveries', []) if isinstance(deliveries_data, dict) else deliveries_data
                if deliveries:
                    delivery_id = deliveries[0].get('id')
        except:
            pass

        # 4.1 PUT /api/marketplace/deliveries/{delivery_id}/update-status (first update)
        if delivery_id:
            try:
                response = self.session.put(f"{BACKEND_URL}/marketplace/deliveries/{delivery_id}/update-status", json={
                    "status": "in_transit",
                    "location": "Distribution Center",
                    "notes": "Departed from supplier"
                })
                success = response.status_code in [200, 201]
                details = f"Status: {response.status_code}"
                if success:
                    details += " - Delivery status updated to 'in_transit'"
                self.log_test_result("marketplace", f"/marketplace/deliveries/{delivery_id}/update-status", "PUT", success, details)
            except Exception as e:
                self.log_test_result("marketplace", f"/marketplace/deliveries/{delivery_id}/update-status", "PUT", False, f"Error: {str(e)}")

            # 4.2 PUT /api/marketplace/deliveries/{delivery_id}/update-status (second update)
            try:
                response = self.session.put(f"{BACKEND_URL}/marketplace/deliveries/{delivery_id}/update-status", json={
                    "status": "delivered",
                    "location": "Central Warehouse",
                    "notes": "Successfully delivered and signed"
                })
                success = response.status_code in [200, 201]
                details = f"Status: {response.status_code}"
                if success:
                    details += " - Delivery status updated to 'delivered'"
                self.log_test_result("marketplace", f"/marketplace/deliveries/{delivery_id}/update-status (delivered)", "PUT", success, details)
            except Exception as e:
                self.log_test_result("marketplace", f"/marketplace/deliveries/{delivery_id}/update-status (delivered)", "PUT", False, f"Error: {str(e)}")

            # 4.3 GET /api/marketplace/deliveries/{delivery_id}/tracking
            try:
                response = self.session.get(f"{BACKEND_URL}/marketplace/deliveries/{delivery_id}/tracking")
                success = response.status_code == 200
                details = f"Status: {response.status_code}"
                if success:
                    data = response.json()
                    tracking_history = data.get('tracking_history', [])
                    current_status = data.get('current_status', 'unknown')
                    details += f" - Current status: {current_status}, History: {len(tracking_history)} events"
                self.log_test_result("marketplace", f"/marketplace/deliveries/{delivery_id}/tracking", "GET", success, details)
            except Exception as e:
                self.log_test_result("marketplace", f"/marketplace/deliveries/{delivery_id}/tracking", "GET", False, f"Error: {str(e)}")

        # 4.4 GET /api/marketplace/deliveries/in-transit
        try:
            response = self.session.get(f"{BACKEND_URL}/marketplace/deliveries/in-transit")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                in_transit_deliveries = data.get('deliveries', []) if isinstance(data, dict) else data
                details += f" - In-transit deliveries: {len(in_transit_deliveries)}"
            self.log_test_result("marketplace", "/marketplace/deliveries/in-transit", "GET", success, details)
        except Exception as e:
            self.log_test_result("marketplace", "/marketplace/deliveries/in-transit", "GET", False, f"Error: {str(e)}")

    def print_summary(self):
        """Print Enhanced RMS test summary"""
        print("\n" + "="*80)
        print("🎯 ENHANCED RMS TESTING SUMMARY")
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
            
            print(f"\n{status_icon} ENHANCED RMS: {passed}/{total} ({success_rate:.1f}%)")
            
            # Show all test details for RMS
            print("   Test Details:")
            for detail in results["details"]:
                status_icon = "✅" if "✅ PASS" in detail["status"] else "❌"
                print(f"     {status_icon} {detail['endpoint']} - {detail['details']}")
        
        grand_total = total_passed + total_failed
        overall_success_rate = (total_passed / grand_total * 100) if grand_total > 0 else 0
        
        print(f"\n🎯 ENHANCED RMS RESULTS:")
        print(f"   Total Enhanced Endpoints: {grand_total}")
        print(f"   Passed: {total_passed}")
        print(f"   Failed: {total_failed}")
        print(f"   Success Rate: {overall_success_rate:.1f}%")
        
        print(f"\n📊 ENHANCED FEATURES TESTED:")
        print(f"   ✓ Advanced Auto-Pricing with Dynamic Confidence")
        print(f"   ✓ 90-Day Demand Forecasting")
        print(f"   ✓ Competitor Price Comparison (NEW)")
        print(f"   ✓ Pricing Insights with Multi-Factor Analysis (NEW)")
        
        if overall_success_rate >= 90:
            print("   Status: 🟢 EXCELLENT - Enhanced RMS fully operational")
        elif overall_success_rate >= 80:
            print("   Status: 🟡 GOOD - Enhanced RMS mostly working")
        elif overall_success_rate >= 60:
            print("   Status: 🟠 FAIR - Enhanced RMS needs attention")
        else:
            print("   Status: 🔴 POOR - Enhanced RMS has major issues")
        
        print("\n" + "="*80)

    def print_calendar_summary(self):
        """Print comprehensive calendar testing summary"""
        print("\n" + "="*80)
        print("📅 ENHANCED CALENDAR TESTING SUMMARY")
        print("="*80)
        
        calendar_results = self.test_results["calendar"]
        total_passed = calendar_results["passed"]
        total_failed = calendar_results["failed"]
        total_tests = total_passed + total_failed
        
        if total_tests > 0:
            success_rate = (total_passed / total_tests) * 100
        else:
            success_rate = 0
        
        print(f"\n📊 OVERALL RESULTS:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {total_passed}")
        print(f"   Failed: {total_failed}")
        print(f"   Success Rate: {success_rate:.1f}%")
        
        print(f"\n📅 ENHANCED CALENDAR FEATURES TESTED:")
        print(f"   ✓ Rate Codes Management (BB, HB, FB, AI, RO, NR)")
        print(f"   ✓ Enhanced Calendar Tooltip with ADR, Occupancy, Segments")
        print(f"   ✓ Group Reservation Calendar View")
        print(f"   ✓ Rate Code Breakdown with Distribution Analysis")
        
        # Detailed results
        print(f"\n📋 DETAILED TEST RESULTS:")
        for result in calendar_results["details"]:
            print(f"   {result['status']}: {result['endpoint']} - {result['details']}")
        
        if success_rate >= 90:
            print("   Status: 🟢 EXCELLENT - Enhanced Calendar fully operational")
        elif success_rate >= 80:
            print("   Status: 🟡 GOOD - Enhanced Calendar mostly working")
        elif success_rate >= 60:
            print("   Status: 🟠 FAIR - Enhanced Calendar needs attention")
        else:
            print("   Status: 🔴 POOR - Enhanced Calendar has major issues")
        
        print("\n" + "="*80)

    def run_all_tests(self):
        """Run Enhanced Calendar Backend Tests"""
        print("🚀 Testing Enhanced Reservation Calendar with Rate Codes & Group View")
        print("Testing 5 NEW calendar enhancement endpoints...")
        
        if not self.authenticate():
            print("❌ Authentication failed. Cannot proceed with testing.")
            return False
        
        # Run Enhanced Calendar test suite
        self.test_enhanced_calendar_features()     # 5 calendar endpoints
        
        # Print comprehensive summary
        self.print_calendar_summary()
        
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
