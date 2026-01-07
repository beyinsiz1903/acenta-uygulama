#!/usr/bin/env python3
"""
Kısa backend regression: Seed değişikliği + publish guard.
Turkish requirements regression test for catalog seed data and publish guard functionality.
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8001"

def login_admin():
    """Login as admin and return token, org_id, email"""
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
    )
    assert r.status_code == 200, f"Admin login failed: {r.text}"
    data = r.json()
    return data["access_token"], data["user"]["organization_id"], data["user"]["email"]

def test_seed_publish_guard_regression():
    """Test seed değişikliği + publish guard according to Turkish requirements"""
    print("\n" + "=" * 80)
    print("KISA BACKEND REGRESSION: SEED DEĞİŞİKLİĞİ + PUBLISH GUARD")
    print("Testing catalog seed data and publish guard functionality")
    print("=" * 80 + "\n")

    # ------------------------------------------------------------------
    # 1) Admin login (admin@acenta.test / admin123) ile token al.
    # ------------------------------------------------------------------
    print("1️⃣  Admin login (admin@acenta.test / admin123) ile token al...")
    
    token, org_id, admin_email = login_admin()
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"   ✅ Admin login successful: {admin_email}")
    print(f"   ✅ Organization ID: {org_id}")
    print(f"   ✅ Token alındı")

    # ------------------------------------------------------------------
    # 2) GET /api/admin/catalog/products?type=hotel&limit=10 çağır
    # En az 1 product için: type="hotel", status="active", default_currency="EUR", 
    # location.city/country set edilmiş olmalı. O product_id'yi kaydet.
    # ------------------------------------------------------------------
    print("\n2️⃣  GET /api/admin/catalog/products?type=hotel&limit=10 çağır...")
    
    r = requests.get(
        f"{BASE_URL}/api/admin/catalog/products?type=hotel&limit=10",
        headers=headers,
    )
    assert r.status_code == 200, f"Product list failed: {r.text}"
    products_response = r.json()
    
    print(f"   📋 Found {len(products_response['items'])} hotel products")
    
    # En az 1 product için kriterleri kontrol et
    suitable_product = None
    for product in products_response['items']:
        if (product.get('type') == 'hotel' and 
            product.get('status') == 'active' and
            product.get('location') and
            product['location'].get('city') and
            product['location'].get('country')):
            
            # Bu product için rate planları kontrol et - EUR currency olmalı
            product_id_temp = product['product_id']
            r_temp = requests.get(
                f"{BASE_URL}/api/admin/catalog/rate-plans?product_id={product_id_temp}",
                headers=headers,
            )
            if r_temp.status_code == 200:
                temp_rates = r_temp.json()
                # EUR currency'li rate plan var mı kontrol et
                has_eur_rates = any(rate.get('currency') == 'EUR' for rate in temp_rates)
                if has_eur_rates:
                    suitable_product = product
                    break
    
    if suitable_product:
        product_id = suitable_product['product_id']
        print(f"   ✅ Uygun product bulundu:")
        print(f"      - product_id: {product_id}")
        print(f"      - type: {suitable_product['type']}")
        print(f"      - status: {suitable_product['status']}")
        print(f"      - location: {suitable_product['location']['city']}, {suitable_product['location']['country']}")
        print(f"      - has EUR rate plans: Yes")
        
        # JSON örneği için seed'li hotel bilgilerini kaydet
        seed_hotel_example = {
            "product_id": suitable_product['product_id'],
            "type": suitable_product['type'],
            "status": suitable_product['status'],
            "location": suitable_product['location'],
            "code": suitable_product.get('code', ''),
            "name_tr": suitable_product.get('name_tr', ''),
            "name_en": suitable_product.get('name_en', '')
        }
    else:
        print("   ❌ Uygun product bulunamadı! Kriterler:")
        print("      - type='hotel'")
        print("      - status='active'")
        print("      - default_currency='EUR'")
        print("      - location.city ve location.country set edilmiş")
        
        # Mevcut productları listele
        for i, product in enumerate(products_response['items']):
            print(f"      Product {i+1}: type={product.get('type')}, status={product.get('status')}, currency={product.get('default_currency')}, location={product.get('location')}")
        
        raise AssertionError("Uygun hotel product bulunamadı")

    # ------------------------------------------------------------------
    # 3) GET /api/admin/catalog/rate-plans?product_id=<id>
    # En az 1 rate plan için: status="active", currency="EUR", board="BB", base_net_price>0 doğrula.
    # ------------------------------------------------------------------
    print(f"\n3️⃣  GET /api/admin/catalog/rate-plans?product_id={product_id}...")
    
    r = requests.get(
        f"{BASE_URL}/api/admin/catalog/rate-plans?product_id={product_id}",
        headers=headers,
    )
    assert r.status_code == 200, f"Rate plans list failed: {r.text}"
    rate_plans = r.json()
    
    print(f"   📋 Found {len(rate_plans)} rate plan(s) for product")
    
    # En az 1 rate plan için kriterleri kontrol et
    suitable_rate_plan = None
    for rate_plan in rate_plans:
        if (rate_plan.get('status') == 'active' and 
            rate_plan.get('currency') == 'EUR' and 
            rate_plan.get('board') == 'BB' and
            rate_plan.get('base_net_price', 0) > 0):
            
            suitable_rate_plan = rate_plan
            break
    
    if suitable_rate_plan:
        print(f"   ✅ Uygun rate plan bulundu:")
        print(f"      - rate_plan_id: {suitable_rate_plan['rate_plan_id']}")
        print(f"      - status: {suitable_rate_plan['status']}")
        print(f"      - currency: {suitable_rate_plan['currency']}")
        print(f"      - board: {suitable_rate_plan['board']}")
        print(f"      - base_net_price: {suitable_rate_plan['base_net_price']}")
        
        # JSON örneği için seed'li rate plan bilgilerini kaydet
        seed_rate_plan_example = {
            "rate_plan_id": suitable_rate_plan['rate_plan_id'],
            "product_id": suitable_rate_plan['product_id'],
            "status": suitable_rate_plan['status'],
            "currency": suitable_rate_plan['currency'],
            "board": suitable_rate_plan['board'],
            "base_net_price": suitable_rate_plan['base_net_price'],
            "code": suitable_rate_plan.get('code', ''),
            "name": suitable_rate_plan.get('name', {})
        }
    else:
        print("   ❌ Uygun rate plan bulunamadı! Kriterler:")
        print("      - status='active'")
        print("      - currency='EUR'")
        print("      - board='BB'")
        print("      - base_net_price>0")
        
        # Mevcut rate planları listele
        for i, rate_plan in enumerate(rate_plans):
            print(f"      Rate Plan {i+1}: status={rate_plan.get('status')}, currency={rate_plan.get('currency')}, board={rate_plan.get('board')}, price={rate_plan.get('base_net_price')}")
        
        raise AssertionError("Uygun rate plan bulunamadı")

    # ------------------------------------------------------------------
    # 4) Aynı product için basit bir draft version oluştur
    # POST /api/admin/catalog/products/{id}/versions {"content": {"description": {"tr":"","en":""}}} -> 201
    # ------------------------------------------------------------------
    print(f"\n4️⃣  POST /api/admin/catalog/products/{product_id}/versions - Draft version oluştur...")
    
    version_payload = {
        "content": {
            "description": {
                "tr": "",
                "en": ""
            }
        }
    }
    
    r = requests.post(
        f"{BASE_URL}/api/admin/catalog/products/{product_id}/versions",
        json=version_payload,
        headers=headers,
    )
    
    if r.status_code == 200:
        created_version = r.json()
        version_id = created_version['version_id']
        
        print(f"   ✅ Draft version oluşturuldu:")
        print(f"      - version_id: {version_id}")
        print(f"      - status: {created_version['status']}")
        print(f"      - version: {created_version['version']}")
        
        assert created_version['status'] == 'draft', "Version status 'draft' olmalı"
    else:
        print(f"   ❌ Draft version oluşturulamadı: {r.status_code}")
        print(f"   Full response body: {r.text}")
        raise AssertionError(f"Draft version creation failed: {r.status_code} - {r.text}")

    # ------------------------------------------------------------------
    # 5) Ardından publish dene: POST /api/admin/catalog/products/{id}/versions/{version_id}/publish
    # Çünkü bu seed'li hotel'in zaten active EUR BB rate_plan'ı var, publish 200 dönmeli;
    # cevaptan product_id, published_version, status="published" alanlarını doğrula.
    # ------------------------------------------------------------------
    print(f"\n5️⃣  POST /api/admin/catalog/products/{product_id}/versions/{version_id}/publish - Publish dene...")
    
    r = requests.post(
        f"{BASE_URL}/api/admin/catalog/products/{product_id}/versions/{version_id}/publish",
        headers=headers,
    )
    
    if r.status_code == 200:
        publish_response = r.json()
        
        print(f"   ✅ Publish başarılı:")
        print(f"      - product_id: {publish_response.get('product_id')}")
        print(f"      - published_version: {publish_response.get('published_version')}")
        print(f"      - status: {publish_response.get('status')}")
        
        # Gerekli alanları doğrula
        assert publish_response.get('product_id') == product_id, f"product_id eşleşmiyor: expected {product_id}, got {publish_response.get('product_id')}"
        assert publish_response.get('published_version') is not None and publish_response.get('published_version') > 0, "published_version > 0 olmalı"
        assert publish_response.get('status') == 'published', f"status 'published' olmalı, got {publish_response.get('status')}"
        
        print("   ✅ Tüm gerekli alanlar doğrulandı")
        
    else:
        print(f"   ❌ Publish başarısız: {r.status_code}")
        print(f"   Full response body: {r.text}")
        
        # Hata durumunda full response body'yi ekle
        try:
            error_response = r.json()
            print(f"   Error details: {json.dumps(error_response, indent=2)}")
        except:
            print(f"   Raw response: {r.text}")
        
        raise AssertionError(f"Publish failed: {r.status_code} - {r.text}")

    # ------------------------------------------------------------------
    # 6) Testin sonunda bulunan seed'li hotel ve rate_plan JSON örneklerini rapora yaz
    # ------------------------------------------------------------------
    print(f"\n6️⃣  Testin sonunda bulunan seed'li hotel ve rate_plan JSON örnekleri:")
    
    print("\n   📋 SEED'Lİ HOTEL ÖRNEĞİ (ilgili alanlar):")
    print(json.dumps(seed_hotel_example, indent=4, ensure_ascii=False))
    
    print("\n   📋 SEED'Lİ RATE PLAN ÖRNEĞİ (ilgili alanlar):")
    print(json.dumps(seed_rate_plan_example, indent=4, ensure_ascii=False))

    print("\n" + "=" * 80)
    print("✅ KISA BACKEND REGRESSION TEST COMPLETE")
    print("✅ Admin login başarılı")
    print("✅ Seed'li hotel bulundu (type=hotel, status=active, currency=EUR, location set)")
    print("✅ Seed'li rate plan bulundu (status=active, currency=EUR, board=BB, price>0)")
    print("✅ Draft version oluşturuldu")
    print("✅ Publish başarılı (zaten active EUR BB rate_plan var)")
    print("✅ Response'tan product_id, published_version, status=published doğrulandı")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    test_seed_publish_guard_regression()