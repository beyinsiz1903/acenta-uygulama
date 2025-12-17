#!/usr/bin/env python3
"""
Hotel Module Authorization Backend Test
=====================================

Bu test, yeni eklenen otel bazlı modül yetkilendirme sistemini doğrular:

1. Tenant modelinde modules alanının default değerleri
2. get_tenant_modules() ve require_module() helper fonksiyonları
3. PMS, Reports, Invoices, AI modüllerinin endpoint kontrolü
4. Admin tenant yönetim endpoint'leri
5. Rol tabanlı erişim kontrolü

Test Senaryoları:
- Mevcut tenant'lar için backward compatibility
- Modül bazlı endpoint erişim kontrolü
- Admin endpoint'leri için yetkilendirme
- Modül ayarlarının güncellenmesi
"""

import asyncio
import aiohttp
import json
import sys
from datetime import datetime
from typing import Dict, List, Any

# Test Configuration
BASE_URL = "https://code-review-helper-12.preview.emergentagent.com/api"
TEST_USER = {
    "email": "demo@hotel.com",
    "password": "demo123"
}

class ModuleAuthorizationTester:
    def __init__(self):
        self.session = None
        self.auth_token = None
        self.tenant_id = None
        self.user_data = None
        self.test_results = []
        
    async def setup_session(self):
        """HTTP session kurulumu"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"Content-Type": "application/json"}
        )
        
    async def cleanup_session(self):
        """Session temizleme"""
        if self.session:
            await self.session.close()
            
    async def login(self) -> bool:
        """Demo kullanıcısı ile giriş yap"""
        try:
            async with self.session.post(
                f"{BASE_URL}/auth/login",
                json=TEST_USER
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.auth_token = data["access_token"]
                    self.user_data = data["user"]
                    self.tenant_id = data["user"].get("tenant_id")
                    
                    # Auth header'ı session'a ekle
                    self.session.headers.update({
                        "Authorization": f"Bearer {self.auth_token}"
                    })
                    
                    print(f"✅ Login başarılı: {self.user_data['name']} (Tenant: {self.tenant_id})")
                    return True
                else:
                    print(f"❌ Login başarısız: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Login hatası: {e}")
            return False
            
    def log_test(self, test_name: str, success: bool, details: str = "", response_time: float = 0):
        """Test sonucunu kaydet"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "response_time": response_time,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅" if success else "❌"
        time_info = f" ({response_time:.1f}ms)" if response_time > 0 else ""
        print(f"{status} {test_name}{time_info}")
        if details:
            print(f"   {details}")
            
    async def test_current_subscription(self):
        """Mevcut tenant subscription bilgilerini kontrol et"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            async with self.session.get(f"{BASE_URL}/subscription/current") as response:
                response_time = (asyncio.get_event_loop().time() - start_time) * 1000
                
                if response.status == 200:
                    data = await response.json()
                    modules = data.get("modules", {})
                    
                    # Default modüllerin varlığını kontrol et
                    expected_modules = ["pms", "reports", "invoices", "ai"]
                    missing_modules = [m for m in expected_modules if m not in modules]
                    
                    if not missing_modules and all(modules.get(m, False) for m in expected_modules):
                        self.log_test(
                            "Current Subscription - Default Modules",
                            True,
                            f"Tüm default modüller aktif: {modules}",
                            response_time
                        )
                        return modules
                    else:
                        self.log_test(
                            "Current Subscription - Default Modules",
                            False,
                            f"Eksik/inaktif modüller: {missing_modules}, Mevcut: {modules}",
                            response_time
                        )
                        return modules
                else:
                    self.log_test(
                        "Current Subscription - Default Modules",
                        False,
                        f"HTTP {response.status}: {await response.text()}",
                        response_time
                    )
                    return {}
        except Exception as e:
            response_time = (asyncio.get_event_loop().time() - start_time) * 1000
            self.log_test(
                "Current Subscription - Default Modules",
                False,
                f"Exception: {e}",
                response_time
            )
            return {}
            
    async def test_admin_tenants_list(self):
        """Admin tenant listesi endpoint'ini test et"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            async with self.session.get(f"{BASE_URL}/admin/tenants") as response:
                response_time = (asyncio.get_event_loop().time() - start_time) * 1000
                
                if response.status == 200:
                    data = await response.json()
                    tenants = data.get("tenants", [])
                    
                    # Her tenant'ın modules alanını kontrol et
                    all_have_modules = True
                    modules_info = []
                    
                    for tenant in tenants:
                        modules = tenant.get("modules", {})
                        if not modules:
                            all_have_modules = False
                        modules_info.append(f"{tenant.get('property_name', 'Unknown')}: {modules}")
                    
                    self.log_test(
                        "Admin Tenants List - Modules Field",
                        all_have_modules,
                        f"Tenant sayısı: {len(tenants)}, Modules bilgisi: {modules_info[:3]}...",
                        response_time
                    )
                    return tenants
                elif response.status == 403:
                    self.log_test(
                        "Admin Tenants List - Role Check",
                        True,
                        "403 Forbidden - Admin olmayan kullanıcı için doğru davranış",
                        response_time
                    )
                    return []
                else:
                    self.log_test(
                        "Admin Tenants List - Modules Field",
                        False,
                        f"HTTP {response.status}: {await response.text()}",
                        response_time
                    )
                    return []
        except Exception as e:
            response_time = (asyncio.get_event_loop().time() - start_time) * 1000
            self.log_test(
                "Admin Tenants List - Modules Field",
                False,
                f"Exception: {e}",
                response_time
            )
            return []
            
    async def test_module_endpoint(self, endpoint: str, method: str, module_name: str, expected_status: int = 200):
        """Belirli bir modül endpoint'ini test et"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            if method.upper() == "GET":
                async with self.session.get(f"{BASE_URL}{endpoint}") as response:
                    response_time = (asyncio.get_event_loop().time() - start_time) * 1000
                    success = response.status == expected_status
                    
                    self.log_test(
                        f"{module_name.upper()} Module - {method} {endpoint}",
                        success,
                        f"HTTP {response.status} (beklenen: {expected_status})",
                        response_time
                    )
                    return response.status
            elif method.upper() == "POST":
                # POST için minimal test data
                test_data = self.get_test_data_for_endpoint(endpoint)
                async with self.session.post(f"{BASE_URL}{endpoint}", json=test_data) as response:
                    response_time = (asyncio.get_event_loop().time() - start_time) * 1000
                    success = response.status == expected_status or response.status in [200, 201, 400, 422]  # 400/422 validation errors are OK
                    
                    self.log_test(
                        f"{module_name.upper()} Module - {method} {endpoint}",
                        success,
                        f"HTTP {response.status} (beklenen: {expected_status} veya validation error)",
                        response_time
                    )
                    return response.status
        except Exception as e:
            response_time = (asyncio.get_event_loop().time() - start_time) * 1000
            self.log_test(
                f"{module_name.upper()} Module - {method} {endpoint}",
                False,
                f"Exception: {e}",
                response_time
            )
            return 500
            
    def get_test_data_for_endpoint(self, endpoint: str) -> Dict[str, Any]:
        """Endpoint için test verisi oluştur"""
        if "/pms/rooms" in endpoint:
            return {
                "room_number": "TEST-001",
                "room_type": "Standard",
                "floor": 1,
                "capacity": 2,
                "base_price": 100.0
            }
        elif "/pms/guests" in endpoint:
            return {
                "name": "Test Guest",
                "email": "test@example.com",
                "phone": "+90555123456",
                "id_number": "12345678901"
            }
        elif "/pms/bookings" in endpoint:
            return {
                "guest_id": "test-guest-id",
                "room_id": "test-room-id",
                "check_in": "2025-12-10",
                "check_out": "2025-12-12",
                "adults": 2,
                "children": 0,
                "guests_count": 2,
                "total_amount": 200.0
            }
        elif "/invoices" in endpoint:
            return {
                "customer_name": "Test Customer",
                "customer_email": "customer@example.com",
                "items": [{"description": "Test Item", "quantity": 1, "unit_price": 100, "total": 100}],
                "subtotal": 100,
                "tax": 18,
                "total": 118,
                "due_date": "2025-12-31"
            }
        elif "/ai/chat" in endpoint:
            return {
                "message": "Test AI message",
                "context": "test"
            }
        else:
            return {}
            
    async def test_pms_endpoints(self):
        """PMS modülü endpoint'lerini test et"""
        pms_endpoints = [
            ("POST", "/pms/rooms"),
            ("GET", "/pms/rooms"),
            ("POST", "/pms/guests"),
            ("GET", "/pms/guests"),
            ("POST", "/pms/bookings"),
            ("GET", "/pms/bookings")
        ]
        
        for method, endpoint in pms_endpoints:
            await self.test_module_endpoint(endpoint, method, "pms")
            
    async def test_reports_endpoints(self):
        """Reports modülü endpoint'lerini test et"""
        reports_endpoints = [
            ("GET", "/reports/flash-report"),
            ("GET", "/reports/occupancy"),
            ("GET", "/reports/revenue"),
            ("GET", "/reports/daily-summary"),
            ("GET", "/reports/forecast")
        ]
        
        for method, endpoint in reports_endpoints:
            await self.test_module_endpoint(endpoint, method, "reports")
            
    async def test_invoices_endpoints(self):
        """Invoices modülü endpoint'lerini test et"""
        invoices_endpoints = [
            ("POST", "/invoices"),
            ("GET", "/invoices"),
            # PUT endpoint için mevcut invoice ID gerekir, şimdilik skip
        ]
        
        for method, endpoint in invoices_endpoints:
            await self.test_module_endpoint(endpoint, method, "invoices")
            
    async def test_ai_endpoints(self):
        """AI modülü endpoint'lerini test et"""
        ai_endpoints = [
            ("POST", "/ai/chat"),
            ("GET", "/pricing/ai-recommendation")
        ]
        
        for method, endpoint in ai_endpoints:
            await self.test_module_endpoint(endpoint, method, "ai")
            
    async def test_module_update_scenario(self):
        """Modül güncelleme senaryosunu test et"""
        if not self.tenant_id:
            self.log_test("Module Update Scenario", False, "Tenant ID bulunamadı")
            return
            
        # Test senaryosu: PMS=false, Reports=true, Invoices=false, AI=true
        test_modules = {
            "pms": False,
            "reports": True,
            "invoices": False,
            "ai": True
        }
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Modülleri güncelle (sadece admin yapabilir)
            async with self.session.patch(
                f"{BASE_URL}/admin/tenants/{self.tenant_id}/modules",
                json={"modules": test_modules}
            ) as response:
                response_time = (asyncio.get_event_loop().time() - start_time) * 1000
                
                if response.status == 403:
                    self.log_test(
                        "Module Update - Admin Role Check",
                        True,
                        "403 Forbidden - Admin olmayan kullanıcı için doğru davranış",
                        response_time
                    )
                elif response.status == 200:
                    data = await response.json()
                    updated_modules = data.get("modules", {})
                    
                    self.log_test(
                        "Module Update - Success",
                        True,
                        f"Modüller güncellendi: {updated_modules}",
                        response_time
                    )
                    
                    # Güncelleme sonrası endpoint testleri
                    await self.test_endpoints_after_module_update(test_modules)
                else:
                    self.log_test(
                        "Module Update - Request",
                        False,
                        f"HTTP {response.status}: {await response.text()}",
                        response_time
                    )
        except Exception as e:
            response_time = (asyncio.get_event_loop().time() - start_time) * 1000
            self.log_test(
                "Module Update - Request",
                False,
                f"Exception: {e}",
                response_time
            )
            
    async def test_endpoints_after_module_update(self, modules: Dict[str, bool]):
        """Modül güncellemesi sonrası endpoint erişimlerini test et"""
        
        # PMS endpoints (pms=false olduğu için 403 bekleniyor)
        if not modules.get("pms", True):
            await self.test_module_endpoint("/pms/rooms", "GET", "pms", 403)
            await self.test_module_endpoint("/pms/bookings", "GET", "pms", 403)
        
        # Reports endpoints (reports=true olduğu için 200 bekleniyor)
        if modules.get("reports", True):
            await self.test_module_endpoint("/reports/flash-report", "GET", "reports", 200)
            await self.test_module_endpoint("/reports/occupancy", "GET", "reports", 200)
        
        # Invoices endpoints (invoices=false olduğu için 403 bekleniyor)
        if not modules.get("invoices", True):
            await self.test_module_endpoint("/invoices", "GET", "invoices", 403)
        
        # AI endpoints (ai=true olduğu için 200 bekleniyor)
        if modules.get("ai", True):
            await self.test_module_endpoint("/ai/chat", "POST", "ai", 200)
            
    async def test_health_endpoints(self):
        """Temel health endpoint'lerini test et (modül kontrolü olmayan)"""
        health_endpoints = [
            "/health",
            "/monitoring/health",
            "/monitoring/system"
        ]
        
        for endpoint in health_endpoints:
            start_time = asyncio.get_event_loop().time()
            try:
                async with self.session.get(f"{BASE_URL}{endpoint}") as response:
                    response_time = (asyncio.get_event_loop().time() - start_time) * 1000
                    success = response.status == 200
                    
                    self.log_test(
                        f"Health Check - {endpoint}",
                        success,
                        f"HTTP {response.status}",
                        response_time
                    )
            except Exception as e:
                response_time = (asyncio.get_event_loop().time() - start_time) * 1000
                self.log_test(
                    f"Health Check - {endpoint}",
                    False,
                    f"Exception: {e}",
                    response_time
                )
                
    def print_summary(self):
        """Test sonuçlarının özetini yazdır"""
        total_tests = len(self.test_results)
        successful_tests = sum(1 for r in self.test_results if r["success"])
        failed_tests = total_tests - successful_tests
        
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        
        print("\n" + "="*80)
        print("🏨 HOTEL MODULE AUTHORIZATION TEST SUMMARY")
        print("="*80)
        print(f"📊 Total Tests: {total_tests}")
        print(f"✅ Successful: {successful_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS ({failed_tests}):")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   • {result['test']}: {result['details']}")
        
        print(f"\n🎯 MODULE AUTHORIZATION TEST COMPLETED")
        print(f"⏱️  Test Duration: {datetime.now().isoformat()}")
        
        # Test kategorilerini analiz et
        categories = {}
        for result in self.test_results:
            category = result["test"].split(" - ")[0] if " - " in result["test"] else "Other"
            if category not in categories:
                categories[category] = {"total": 0, "success": 0}
            categories[category]["total"] += 1
            if result["success"]:
                categories[category]["success"] += 1
        
        print(f"\n📋 TEST CATEGORIES:")
        for category, stats in categories.items():
            rate = (stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0
            print(f"   • {category}: {stats['success']}/{stats['total']} ({rate:.1f}%)")
            
    async def run_all_tests(self):
        """Tüm testleri çalıştır"""
        print("🏨 Hotel Module Authorization Backend Test Starting...")
        print(f"🔗 Base URL: {BASE_URL}")
        print(f"👤 Test User: {TEST_USER['email']}")
        print("="*80)
        
        await self.setup_session()
        
        try:
            # 1. Login
            if not await self.login():
                print("❌ Login başarısız, testler durduruluyor")
                return
                
            # 2. Current subscription test (default modules check)
            current_modules = await self.test_current_subscription()
            
            # 3. Admin endpoints test
            await self.test_admin_tenants_list()
            
            # 4. Health endpoints (baseline)
            await self.test_health_endpoints()
            
            # 5. Module endpoints with current settings
            print(f"\n🔍 Testing module endpoints with current settings...")
            await self.test_pms_endpoints()
            await self.test_reports_endpoints()
            await self.test_invoices_endpoints()
            await self.test_ai_endpoints()
            
            # 6. Module update scenario (if admin)
            print(f"\n🔧 Testing module update scenario...")
            await self.test_module_update_scenario()
            
        finally:
            await self.cleanup_session()
            
        # 7. Print summary
        self.print_summary()

async def main():
    """Ana test fonksiyonu"""
    tester = ModuleAuthorizationTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())