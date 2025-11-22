# Test Kullanıcıları - Hotel PMS

## 🔑 Kalıcı Test Kullanıcıları

Bu kullanıcılar MongoDB'de kalıcı olarak saklanmaktadır ve her zaman kullanılabilir.

### 1. Test Kullanıcı (Genel Test)
```
Email: test@test.com
Şifre: test123
Otel: Test Otel
Lokasyon: Istanbul
```

### 2. Demo Kullanıcı (Demo Amaçlı)
```
Email: demo@demo.com
Şifre: demo123
Otel: Demo Hotel
Lokasyon: Ankara
```

### 3. Patron Hesabı (Patron/Yatırımcı)
```
Email: patron@hotel.com
Şifre: patron123
Otel: Patron Otel
Lokasyon: Izmir
```

### 4. Admin Test Kullanıcı
```
Email: admin@hoteltest.com
Şifre: admin123
Otel: Test Otel
```

### 5. Dashboard Test Kullanıcı
```
Email: dashboard@testhotel.com
Şifre: testpass123
Otel: Dashboard Test Hotel
```

## 📱 Mobil Erişim Linkleri

### Revenue Management (Gelir Yönetimi)
- URL: `/mobile/revenue`
- Özellikler: ADR, RevPAR, Total Revenue, Segment Dağılımı, Pickup Grafiği, Forecast, Kanal Dağılımı, İptal Raporları

### F&B Management
- URL: `/mobile/fnb`
- Özellikler: Günlük satışlar, Menu performans, Gelir grafikleri

### Dashboard (Ana Ekran)
- URL: `/mobile/dashboard`
- Özellikler: Tüm modüllere hızlı erişim

## 🔧 API Test Endpointleri

### Dashboard Enhancements
```bash
# Gelir-Gider Grafiği
GET /api/dashboard/revenue-expense-chart?period=30days

# Bütçe vs Gerçekleşen
GET /api/dashboard/budget-vs-actual?month=2025-01

# Aylık Kârlılık
GET /api/dashboard/monthly-profitability?months=6

# Trend KPI'lar
GET /api/dashboard/trend-kpis?period=7days
```

### Revenue Mobile
```bash
# ADR
GET /api/revenue-mobile/adr

# RevPAR
GET /api/revenue-mobile/revpar

# Total Revenue
GET /api/revenue-mobile/total-revenue

# Segment Distribution
GET /api/revenue-mobile/segment-distribution

# Pickup Graph
GET /api/revenue-mobile/pickup-graph

# Forecast
GET /api/revenue-mobile/forecast?days_ahead=30

# Channel Distribution
GET /api/revenue-mobile/channel-distribution

# Cancellation Report
GET /api/revenue-mobile/cancellation-report

# Rate Override
POST /api/revenue-mobile/rate-override
```

### F&B Module
```bash
# F&B Dashboard
GET /api/fnb/dashboard

# Sales Report
GET /api/fnb/sales-report

# Menu Performance
GET /api/fnb/menu-performance

# Revenue Chart
GET /api/fnb/revenue-chart?period=30days
```

## 🔐 Authentication

Tüm endpoint'ler için Bearer token gereklidir:

```bash
# Login
curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@test.com", "password": "test123"}'

# Response
{
  "access_token": "eyJhbGci...",
  "user": {
    "id": "...",
    "email": "test@test.com",
    "name": "Test Kullanıcı",
    "role": "admin",
    "tenant_id": "..."
  }
}

# API İsteği
curl -X GET http://localhost:8001/api/revenue-mobile/adr \
  -H "Authorization: Bearer eyJhbGci..."
```

## ⚠️ Önemli Notlar

1. **Şifre Güvenliği**: Production ortamında mutlaka güçlü şifreler kullanın
2. **Token Süresi**: Access token'lar 24 saat geçerlidir
3. **Rol Yönetimi**: Tüm test kullanıcıları "admin" rolüne sahiptir
4. **Veri Kalıcılığı**: MongoDB container restart olsa bile veriler korunur

## 📊 Test Senaryoları

### Senaryo 1: Revenue Dashboard Test
1. `patron@hotel.com` ile login
2. `/mobile/revenue` sayfasına git
3. Farklı periyotlar dene (7/30/60/90 gün)
4. Tüm görünümleri test et (Genel, Segment, Kanal, Pickup, Forecast, İptal)

### Senaryo 2: F&B Analiz Test
1. `test@test.com` ile login
2. `/mobile/fnb` sayfasına git
3. Günlük satış raporlarını kontrol et
4. Menu performans analizini incele

### Senaryo 3: Dashboard KPI Test
1. `demo@demo.com` ile login
2. Dashboard endpoint'lerini test et
3. Gelir-gider grafiğini kontrol et
4. Bütçe vs gerçekleşen karşılaştırmasını incele

## 🔄 Veri Sıfırlama (Gerekirse)

Tüm test verilerini sıfırlamak için:
```bash
python3 << 'EOF'
import pymongo
from pymongo import MongoClient
import os

mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = MongoClient(mongo_url)
db = client['hotel_pms']

# Test tenant'ları sil
test_emails = ['test@test.com', 'demo@demo.com', 'patron@hotel.com']
for email in test_emails:
    user = db.users.find_one({'email': email})
    if user:
        tenant_id = user.get('tenant_id')
        # Tüm tenant verilerini sil
        db.users.delete_many({'tenant_id': tenant_id})
        db.bookings.delete_many({'tenant_id': tenant_id})
        db.rooms.delete_many({'tenant_id': tenant_id})
        print(f"Deleted data for {email}")
EOF
```

---
**Son Güncelleme:** $(date +%Y-%m-%d)
**Versiyon:** 3.0
**Durum:** ✅ Aktif ve Kullanılabilir
