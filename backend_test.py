#!/usr/bin/env python3
"""
Comprehensive Backend Testing Script for Voucher Endpoints
Testing on: https://booking-suite-pro.preview.emergentagent.com/api
"""

import requests
import json
from typing import Dict, Any, Optional
import re
from bs4 import BeautifulSoup
import sys

# Backend API Base URL
BASE_URL = "https://booking-suite-pro.preview.emergentagent.com/api"

# Test credentials
CREDENTIALS = {
    "email": "admin@acenta.test",
    "password": "admin123"
}

class VoucherTester:
    def __init__(self):
        self.session = requests.Session()
        self.auth_token = None
        self.results = []
        
    def log(self, message: str, level: str = "INFO"):
        """Log test results"""
        print(f"[{level}] {message}")
        self.results.append(f"[{level}] {message}")
        
    def login(self) -> bool:
        """Login and get authentication token"""
        try:
            response = self.session.post(
                f"{BASE_URL}/auth/login",
                json=CREDENTIALS,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                if self.auth_token:
                    self.session.headers.update({
                        "Authorization": f"Bearer {self.auth_token}"
                    })
                    self.log("✅ Login successful")
                    return True
                else:
                    self.log("❌ Login failed: No access token in response", "ERROR")
                    return False
            else:
                self.log(f"❌ Login failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Login error: {e}", "ERROR")
            return False
    
    def test_list_reservations(self) -> Optional[list]:
        """Test GET /api/reservations to get existing reservations"""
        try:
            response = self.session.get(f"{BASE_URL}/reservations")
            
            if response.status_code == 200:
                reservations = response.json()
                self.log(f"✅ Found {len(reservations)} reservations")
                
                for idx, res in enumerate(reservations[:3]):  # Show first 3
                    pnr = res.get("pnr", "N/A")
                    status = res.get("status", "N/A")
                    res_id = res.get("id", res.get("_id", "N/A"))
                    self.log(f"   {idx+1}. ID: {res_id}, PNR: {pnr}, Status: {status}")
                
                return reservations
                
            else:
                self.log(f"❌ Failed to list reservations: {response.status_code} - {response.text}", "ERROR")
                return None
                
        except Exception as e:
            self.log(f"❌ Error listing reservations: {e}", "ERROR")
            return None

    def create_test_reservation(self) -> Optional[Dict[str, Any]]:
        """Create a test reservation if needed"""
        try:
            # First get products
            products_response = self.session.get(f"{BASE_URL}/products")
            if products_response.status_code != 200:
                self.log(f"❌ Failed to get products: {products_response.status_code}", "ERROR")
                return None
                
            products = products_response.json()
            if not products:
                self.log("❌ No products available for reservation", "ERROR")
                return None
                
            product = products[0]
            product_id = product.get("_id")
            self.log(f"✅ Using product: {product.get('title', 'Unknown')} (ID: {product_id})")
            
            # Create reservation payload
            reservation_data = {
                "product_id": product_id,
                "start_date": "2024-03-15",
                "end_date": "2024-03-17",
                "pax": {"adults": 2, "children": 0},
                "customer_name": "Test Customer",
                "customer_email": "test@example.com",
                "customer_phone": "+90 555 123 4567"
            }
            
            response = self.session.post(
                f"{BASE_URL}/reservations/reserve",
                json=reservation_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code in [200, 201]:
                reservation = response.json()
                self.log(f"✅ Created test reservation: {reservation.get('pnr', 'N/A')}")
                return reservation
            else:
                self.log(f"❌ Failed to create reservation: {response.status_code} - {response.text}", "ERROR")
                return None
                
        except Exception as e:
            self.log(f"❌ Error creating reservation: {e}", "ERROR")
            return None

    def test_voucher_endpoint(self, reservation_id: str, pnr: str) -> bool:
        """Test voucher endpoint for a specific reservation"""
        try:
            self.log(f"\n🎫 Testing voucher for reservation {reservation_id} (PNR: {pnr})")
            
            response = self.session.get(f"{BASE_URL}/reservations/{reservation_id}/voucher")
            
            if response.status_code == 200:
                content_type = response.headers.get("Content-Type", "")
                
                if "text/html" in content_type:
                    html_content = response.text
                    self.log(f"✅ Voucher endpoint returned HTML (Length: {len(html_content)} chars)")
                    
                    # Parse HTML and verify required sections
                    return self.verify_voucher_html(html_content, pnr)
                else:
                    self.log(f"❌ Voucher endpoint returned wrong content type: {content_type}", "ERROR")
                    return False
            else:
                self.log(f"❌ Voucher endpoint failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Error testing voucher endpoint: {e}", "ERROR")
            return False

    def verify_voucher_html(self, html_content: str, pnr: str) -> bool:
        """Verify the voucher HTML contains required sections"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            passed_checks = 0
            total_checks = 0
            
            # Check 1: Basic voucher text
            total_checks += 1
            if any(text in html_content.upper() for text in ["REZERVASYON VOUCHER", "RESERVATION VOUCHER", "BOOKING VOUCHER"]):
                self.log("✅ Found voucher title text")
                passed_checks += 1
            else:
                self.log("❌ Missing voucher title text", "ERROR")
            
            # Check 2: PNR and Voucher No in header
            total_checks += 1
            if pnr in html_content:
                self.log(f"✅ Found PNR {pnr} in voucher")
                passed_checks += 1
            else:
                self.log(f"❌ PNR {pnr} not found in voucher", "ERROR")
            
            # Check 3: Hotel/Accommodation Info Section
            total_checks += 1
            if any(text in html_content for text in ["Otel / Konaklama Bilgileri", "Otel Bilgileri", "Tur Bilgileri"]):
                self.log("✅ Found hotel/product information section")
                passed_checks += 1
            else:
                self.log("❌ Missing hotel/product information section", "ERROR")
            
            # Check 4: Guest Information Section
            total_checks += 1
            if "Misafir Bilgileri" in html_content:
                self.log("✅ Found guest information section")
                passed_checks += 1
            else:
                self.log("❌ Missing guest information section", "ERROR")
            
            # Check 5: Date Information Section
            total_checks += 1
            if any(text in html_content for text in ["Konaklama Tarihleri", "Seyahat Tarihi"]):
                self.log("✅ Found date information section")
                passed_checks += 1
            else:
                self.log("❌ Missing date information section", "ERROR")
            
            # Check 6: Payment Details Section
            total_checks += 1
            if "Ödeme Detayları" in html_content:
                self.log("✅ Found payment details section")
                passed_checks += 1
            else:
                self.log("❌ Missing payment details section", "ERROR")
            
            # Check 7: Cancellation Policy Section
            total_checks += 1
            if "İptal ve Değişiklik Politikası" in html_content:
                self.log("✅ Found cancellation policy section")
                passed_checks += 1
            else:
                self.log("❌ Missing cancellation policy section", "ERROR")
            
            # Check 8: Terms and Conditions Section
            total_checks += 1
            if "Genel Şartlar ve Koşullar" in html_content:
                self.log("✅ Found terms and conditions section")
                passed_checks += 1
            else:
                self.log("❌ Missing terms and conditions section", "ERROR")
            
            # Check 9: Contact and Emergency Section
            total_checks += 1
            if "İletişim ve Acil Durum" in html_content:
                self.log("✅ Found contact and emergency section")
                passed_checks += 1
            else:
                self.log("❌ Missing contact and emergency section", "ERROR")
            
            # Check 10: Money formatting (Turkish format with commas/dots)
            total_checks += 1
            money_patterns = re.findall(r'\d{1,3}(?:\.\d{3})*(?:,\d{2})?\s*(?:TRY|USD|EUR|\₺)', html_content)
            if money_patterns:
                self.log(f"✅ Found proper money formatting: {money_patterns[:2]}")  # Show first 2 examples
                passed_checks += 1
            else:
                self.log("❌ No proper money formatting found", "ERROR")
            
            # Check if this is a tour reservation (PNR starts with TR-)
            is_tour = pnr.startswith("TR-")
            if is_tour:
                self.log(f"🎯 Detected tour reservation (PNR: {pnr})")
                passed_checks += self.verify_tour_specific_sections(html_content)
                total_checks += 4  # 4 additional tour checks
            
            success_rate = (passed_checks / total_checks) * 100
            self.log(f"📊 Voucher verification: {passed_checks}/{total_checks} checks passed ({success_rate:.1f}%)")
            
            return success_rate >= 80  # Pass if 80% or more checks pass
            
        except Exception as e:
            self.log(f"❌ Error verifying voucher HTML: {e}", "ERROR")
            return False

    def verify_tour_specific_sections(self, html_content: str) -> int:
        """Verify tour-specific sections in voucher"""
        tour_checks = 0
        
        # Check 1: Tour Information section
        if "Tur Bilgileri" in html_content:
            self.log("✅ Found tour information section")
            tour_checks += 1
        else:
            self.log("❌ Missing tour information section", "ERROR")
        
        # Check 2: Tour Highlights section
        if "Tur Öne Çıkanlar" in html_content:
            self.log("✅ Found tour highlights section")
            tour_checks += 1
        else:
            self.log("❌ Missing tour highlights section", "ERROR")
        
        # Check 3: Tour Program/Itinerary section
        if "Tur Programı" in html_content:
            self.log("✅ Found tour program section")
            tour_checks += 1
        else:
            self.log("❌ Missing tour program section", "ERROR")
        
        # Check 4: Includes/Excludes section
        if "Dahil ve Hariç Hizmetler" in html_content:
            self.log("✅ Found includes/excludes section")
            tour_checks += 1
        else:
            self.log("❌ Missing includes/excludes section", "ERROR")
            
        return tour_checks

    def run_tests(self):
        """Run all voucher tests"""
        self.log("🚀 Starting Voucher Endpoint Tests")
        self.log("=" * 60)
        
        # Step 1: Login
        if not self.login():
            self.log("❌ Test suite failed: Cannot login", "ERROR")
            return
        
        # Step 2: Get reservations
        reservations = self.test_list_reservations()
        
        if not reservations:
            self.log("⚠️ No existing reservations, creating test reservation")
            test_reservation = self.create_test_reservation()
            if test_reservation:
                reservations = [test_reservation]
            else:
                self.log("❌ Cannot create test reservation", "ERROR")
                return
        
        # Step 3: Test vouchers for each reservation (max 3)
        voucher_tests_passed = 0
        voucher_tests_total = 0
        
        for reservation in reservations[:3]:  # Test first 3 reservations
            reservation_id = reservation.get("_id")
            pnr = reservation.get("pnr", "N/A")
            
            if reservation_id:
                voucher_tests_total += 1
                if self.test_voucher_endpoint(reservation_id, pnr):
                    voucher_tests_passed += 1
        
        # Final results
        self.log("\n" + "=" * 60)
        self.log("📈 FINAL RESULTS")
        self.log(f"✅ Voucher tests passed: {voucher_tests_passed}/{voucher_tests_total}")
        
        if voucher_tests_passed == voucher_tests_total and voucher_tests_total > 0:
            self.log("🎉 ALL VOUCHER TESTS PASSED!")
            return True
        elif voucher_tests_passed > 0:
            self.log("⚠️ SOME VOUCHER TESTS FAILED")
            return False
        else:
            self.log("❌ ALL VOUCHER TESTS FAILED")
            return False

def main():
    tester = VoucherTester()
    success = tester.run_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()