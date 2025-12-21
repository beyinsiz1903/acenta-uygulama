# 🔍 MEVCUT SİSTEM DURUMU - FAZ ANALİZİ

## 📋 İSTENEN BİLGİLER

### 1️⃣ 4 CORE ENDPOINT ÇİFTİ (Mevcut Durum)

#### **A) Availability Search (Acenta → PMS)**

**Endpoint:** `POST /api/agency/search`
**Dosya:** `/app/backend/app/routers/search.py`

**Akış:**
```
Agency User
    ↓
POST /api/agency/search
{
  hotel_id: UUID,
  check_in: "YYYY-MM-DD",
  check_out: "YYYY-MM-DD",
  occupancy: {adults: N, children: N}
}
    ↓
Connect Layer (services/connect_layer.py)
    ↓
PMS Client (MockPMS/RealPMS)
    ↓
hotel_availability.compute_availability()
  - Stop-sell check
  - Allocation check
  - Sold count calculation
    ↓
Search Cache (5dk TTL)
    ↓
Response: {
  search_id: UUID,
  hotel: {...},
  rooms: [
    {
      room_type_id, 
      room_type_name,
      rate_plans: [
        {rate_plan_id, price, availability}
      ]
    }
  ]
}
```

**Veri Kaynağı:** 
- **PMS Mock:** `hotels.room_types` (local DB)
- **PMS Real:** External API call
- **Stop-sell:** `stop_sell_rules` collection
- **Allocation:** `channel_allocations` collection

---

#### **B) Create Request (Acenta → Draft/Pending)**

**Endpoint:** `POST /api/agency/bookings/draft`
**Dosya:** `/app/backend/app/routers/agency_booking.py`

**Akış:**
```
Agency User (confirmed sonrası)
    ↓
POST /api/agency/bookings/draft
{
  search_id: UUID,
  hotel_id: UUID,
  room_type_id: UUID,
  rate_plan_id: UUID,
  guest: {full_name, email, phone},
  check_in, check_out, nights,
  adults, children
}
    ↓
Validation:
  - Agency-hotel link active?
  - Hotel exists?
    ↓
Create Draft:
{
  _id: "draft_xxxxx",
  organization_id,
  agency_id,
  hotel_id,
  status: "draft",
  guest, stay, occupancy,
  rate_snapshot: {price, commission},
  expires_at: now + 15 minutes (TTL)
}
    ↓
Response: draft object
```

**Özellikler:**
- ✅ TTL 15 dakika (otomatik cleanup)
- ✅ Rate snapshot (fiyat değişse bile sabit)
- ✅ Commission calculation (link'ten)
- ❌ PMS'e henüz GÖNDERİLMEZ

---

#### **C) Approve/Confirm (Draft → Confirmed)**

**Endpoint:** `POST /api/agency/bookings/confirm`
**Dosya:** `/app/backend/app/routers/agency_booking.py`

**Akış:**
```
Agency User
    ↓
POST /api/agency/bookings/confirm
{draft_id: "draft_xxxxx"}
    ↓
1. Draft al
2. PMS'e gönder
   ↓
   connect_layer.create_booking(
     idempotency_key=draft_id,
     booking_data={...}
   )
   ↓
   MockPMS/RealPMS.create_booking()
   ↓
   Success: pms_booking_id döner
   Fail: NO_INVENTORY/PRICE_CHANGED/UNAVAILABLE
    ↓
3. PMS Success ise → DB'ye booking yaz
{
  _id: UUID (yeni),
  status: "confirmed",
  pms_booking_id: "pms_xxx",
  pms_status: "confirmed",
  source: "pms",
  
  // Financial snapshot
  gross: X,
  commission: Y,
  net: X - Y,
  
  // Timestamps
  check_in_date: UTC midnight,
  check_out_date: UTC midnight,
  created_at, updated_at
}
    ↓
4. Side effects:
   - booking_financial_entries oluştur (month bazlı)
   - voucher token generate
   - email_outbox job ekle (booking.confirmed)
   - booking_events write (booking.created)
   - audit_log write
    ↓
5. Draft sil (cleanup)
    ↓
Response: confirmed booking object
```

**Kritik Noktalar:**
- ✅ **Idempotent:** Aynı draft_id → aynı PMS booking
- ✅ **PMS-first:** PMS fail → DB'ye yazmaz
- ✅ **Commission snapshot:** Link değişse bile sabit
- ✅ **Event cascade:** Financial + voucher + email + audit

**Şu anki durum:**
- ❌ Hotel approval yok (direkt confirmed)
- ❌ "Pending" status yok
- ❌ Hotel'in onay/red mekanizması yok

---

#### **D) Cancel (Her İki Taraf)**

**Endpoint:** `POST /api/bookings/{booking_id}/cancel`
**Dosya:** `/app/backend/app/routers/bookings.py`

**Akış:**
```
Agency veya Hotel User
    ↓
POST /api/bookings/{booking_id}/cancel
{reason: "optional text"}
    ↓
1. Ownership check
   - Agency: kendi agency_id
   - Hotel: kendi hotel_id
    ↓
2. Status check
   - Zaten cancelled ise → error
    ↓
3. PMS cancel (varsa)
   connect_layer.cancel_booking(pms_booking_id)
    ↓
4. DB update
{
  status: "cancelled",
  cancellation: {
    cancelled_at: now,
    cancelled_by: user.email,
    reason: reason
  }
}
    ↓
5. Commission reversal
   - Negatif financial entry oluştur
   - commission_reversed: true flag
    ↓
6. Side effects:
   - Email outbox (booking.cancelled → hem otel hem acenta)
   - Booking event (booking.cancelled)
   - Audit log
    ↓
Response: updated booking
```

**Kritik:**
- ✅ İki taraf da iptal edebilir
- ✅ Reversal financial entry (mutabakat için)
- ✅ Email notification (both sides)
- ❌ "Kim iptal etti" tracking net değil (cancelled_by var ama UX'te ayrımı net değil)

---

### 2️⃣ MUTABAKAT SİSTEMİ

**✅ VAR - FAZ-6'da implement edilmiş**

**Endpoints:**

**A) Otel Mutabakat:**
```
GET /api/hotel/settlements?month=2026-03&status=open&export=csv
```

**Response:**
```json
{
  "items": [
    {
      "agency_id": "...",
      "agency_name": "Demo Acente A",
      "currency": "TRY",
      "gross_total": 12600.0,
      "commission_total": 1260.0,
      "net_total": 11340.0,
      "count": 7
    }
  ]
}
```

**B) Acenta Mutabakat:**
```
GET /api/agency/settlements?month=2026-03&status=open&export=csv
```

**Response:**
```json
{
  "items": [
    {
      "hotel_id": "...",
      "hotel_name": "Demo Hotel 1",
      "currency": "TRY",
      "gross_total": 16800.0,
      "commission_total": 1680.0,
      "net_total": 15120.0,
      "count": 6
    }
  ]
}
```

**CSV Export:** ✅ Destekli (export=csv query param)

---

### 3️⃣ KOMİSYON MODELİ

**✅ ACENTA BAZLI - Agency-Hotel Link Seviyesinde**

**Veri Modeli (agency_hotel_links):**
```javascript
{
  _id: UUID,
  organization_id: UUID,
  agency_id: UUID,
  hotel_id: UUID,
  active: Boolean,
  
  // Komisyon config
  commission_type: "percent" | "fixed_per_booking",
  commission_value: Number,  // %10 ise 10.0, sabit ise tutar
  
  // Audit
  created_at: DateTime,
  updated_at: DateTime,
  created_by: String,
  updated_by: String
}
```

**Hesaplama (Booking Confirm Anında):**
```python
# Link'ten komisyon config al
link = await db.agency_hotel_links.find_one({
    "agency_id": agency_id,
    "hotel_id": hotel_id,
    "active": True
})

if link.commission_type == "percent":
    gross = room_rate * nights
    commission = gross * link.commission_value / 100
    net = gross - commission
elif link.commission_type == "fixed_per_booking":
    gross = room_rate * nights
    commission = link.commission_value
    net = gross - commission

# Booking'e snapshot
booking.gross = gross
booking.commission = commission
booking.net = net
```

**Commission Snapshot:**
- ✅ Booking confirm anında hesaplanır ve snapshot'lanır
- ✅ Link'teki commission değeri sonra değişse bile booking değişmez
- ✅ Financial entry ayrı kaydedilir (mutabakat için)

---

## 📊 MEVCUT VERİ MODELLERİ

### PMS Veri Sözleşmesi (Şu anki)

**1. Rooms/RoomTypes:**
```javascript
// hotels.room_types (embedded)
{
  room_type_id: "rt_deluxe",
  room_type_name: "Deluxe Oda",
  rate_plans: [
    {
      rate_plan_id: "rp_refundable",
      rate_plan_name: "İade Edilebilir",
      board: "RO|BB|HB|FB",
      base_price: 2450.0,
      currency: "TRY"
    }
  ]
}
```

**Kaynak:** 
- Mock: `hotels` collection (embedded)
- Real PMS: External API

**2. Availability/Inventory:**
```javascript
// Hesaplanır (real-time)
availability = capacity_total - sold_count - stop_sell - allocation_limit
```

**Kaynak:**
- `hotels.room_types[].capacity` (base)
- `bookings` (sold_count aggregation)
- `stop_sell_rules` (blok edilen günler)
- `channel_allocations` (acenta limiti)

**3. Stop-sell:**
```javascript
stop_sell_rules {
  organization_id,
  hotel_id,
  room_type_id,
  start_dt: "YYYY-MM-DD",
  end_dt: "YYYY-MM-DD",
  reason: String,
  active: Boolean,
  source: "local"  // PMS entegrasyonuna hazır
}
```

**4. Quota (Acenta Bazlı):**
```javascript
channel_allocations {
  organization_id,
  hotel_id,
  room_type_id,
  allotment: Number,  // Max kapasite
  start_dt: "YYYY-MM-DD",
  end_dt: "YYYY-MM-DD",
  active: Boolean,
  source: "local"
}

// Kullanım
sold_count = bookings.count({
  hotel_id,
  room_type_id,
  check_in: {$gte: date},
  check_out: {$lte: date},
  status: "confirmed"
})

available = min(
  capacity_total - sold_count,
  allotment - sold_count  // Allocation limiti
)
```

---

### Acenta Katmanı (Şu anki Durum)

**✅ MEVCUT:**
- ✅ Komisyon (agency_hotel_links seviyesinde)
- ✅ Mutabakat ekranı (settlements)
- ✅ Booking history
- ✅ WhatsApp share functionality

**❌ MEVCUT OLMAYAN (Senin önerilerin):**
- ❌ `agency_hotel_contracts` (ayrı contract collection)
- ❌ `agency_overrides` (acenta özel fiyat override)
- ❌ `agency_content_overrides` (acenta özel görsel/metin)
- ❌ `inventory_snapshots` (performance cache)

**Şu anki model:**
- Komisyon: `agency_hotel_links` içinde
- Override: YOK (her acenta aynı fiyatı görür)
- Content: YOK (her acenta aynı hotel bilgisini görür)

---

## 🎯 ENDPOINT KAPSAMLI LİSTESİ

### Agency Booking Endpoints

```
POST   /api/agency/search                  → Availability search (PMS)
POST   /api/agency/bookings/draft          → Draft oluştur
POST   /api/agency/bookings/confirm        → Confirm (PMS'e gönder)
GET    /api/agency/bookings                → Booking listesi
GET    /api/agency/bookings/{id}           → Booking detay
GET    /api/agency/hotels                  → Linked oteller (cm_status ile)
GET    /api/agency/settlements             → Mutabakat (month bazlı)
```

### Hotel Endpoints

```
GET    /api/hotel/bookings                 → Gelen talepler
POST   /api/hotel/bookings/{id}/note       → Not ekle
POST   /api/hotel/bookings/{id}/guest-note → Misafir notu
POST   /api/hotel/bookings/{id}/cancel-request → İptal talebi

POST   /api/hotel/stop-sell                → Stop-sell oluştur
GET    /api/hotel/stop-sell                → Stop-sell listesi
PATCH  /api/hotel/stop-sell/{id}           → Toggle active
DELETE /api/hotel/stop-sell/{id}           → Sil

POST   /api/hotel/allocations              → Allocation oluştur
GET    /api/hotel/allocations              → Allocation listesi
PATCH  /api/hotel/allocations/{id}         → Toggle active
DELETE /api/hotel/allocations/{id}         → Sil

GET    /api/hotel/settlements              → Mutabakat (agency bazlı)
GET    /api/hotel/integrations             → CM integrations
PUT    /api/hotel/integrations/channel-manager → Update config
POST   /api/hotel/integrations/channel-manager/sync → Sync trigger
```

### Bookings (Shared - Ownership Check)

```
POST   /api/bookings/{id}/cancel           → İptal (agency veya hotel)
POST   /api/bookings/{id}/track/whatsapp-click → WhatsApp tracking
```

### Admin Endpoints

```
GET    /api/admin/agencies                 → Acenta CRUD
POST   /api/admin/agencies                 → Acenta oluştur
GET    /api/admin/hotels                   → Otel CRUD
POST   /api/admin/hotels                   → Otel oluştur
GET    /api/admin/agency-hotel-links       → Link yönetimi
POST   /api/admin/agency-hotel-links       → Link oluştur
PATCH  /api/admin/agency-hotel-links/{id}  → Link güncelle (commission)
PATCH  /api/admin/hotels/{id}/force-sales  → Emergency override
GET    /api/admin/pilot/summary            → KPI dashboard
GET    /api/admin/email-outbox             → Email jobs
POST   /api/admin/email-outbox/{id}/retry  → Retry email
GET    /api/admin/audit/logs               → Audit logs
```

---

## 🔄 APPROVAL/REJECT MEKANİZMASI

### ❌ ŞU AN YOK - KRİTİK EKSİK

**Mevcut Akış:**
```
Draft → Confirm → Direkt "confirmed" status
```

**Eksikler:**
1. ❌ Hotel approval step yok
2. ❌ "pending" status yok
3. ❌ Hotel'in "approve" veya "reject" endpoint'i yok
4. ❌ Status machine: draft → pending → confirmed/rejected

**Şu anki workaround:**
- Hotel `/cancel-request` endpoint var (iptal talebi)
- Ama "reject before confirm" yok

---

## 💡 ÖNERİLEN YENİ VERİ MODELLERİ

### 1. agency_hotel_contracts (Senin önerindiğin)

```javascript
{
  _id: UUID,
  organization_id: UUID,
  agency_id: UUID,
  hotel_id: UUID,
  
  // Contract terms
  commission: {
    type: "percent|fixed",
    value: Number,
    override_allowed: Boolean  // Acenta özel override
  },
  
  // Content customization
  content_overrides: {
    description: String,      // Acenta özel otel açıklaması
    images: [String],         // Acenta özel görseller
    highlight_text: String    // Öne çıkan özellik
  },
  
  // Pricing overrides
  pricing_overrides: {
    enabled: Boolean,
    rules: [
      {
        room_type_id: String,
        markup_percent: Number,  // +%10 veya -%5
        fixed_price: Number       // Sabit fiyat override
      }
    ]
  },
  
  // Quota
  quotas: [
    {
      room_type_id: String,
      allotment: Number,
      date_range: [Date, Date]
    }
  ],
  
  valid_from: DateTime,
  valid_to: DateTime,
  active: Boolean
}
```

### 2. inventory_snapshots (Performance)

```javascript
{
  _id: UUID,
  organization_id: UUID,
  hotel_id: UUID,
  date: "YYYY-MM-DD",
  
  // Pre-computed availability
  rooms: [
    {
      room_type_id: String,
      capacity_total: Number,
      sold_count: Number,
      stop_sell: Boolean,
      allocation_limit: Number,
      available: Number  // Hesaplanmış
    }
  ],
  
  // Cache metadata
  computed_at: DateTime,
  ttl: Number,  // Saniye (örn. 300 = 5dk)
  expires_at: DateTime
}

// Use case: Busy dates için pre-compute
// Search API önce snapshot'a bakar, yoksa real-time hesaplar
```

---

## 🚨 KRİTİK EKSİKLER (FAZ-2 İçin)

### 1. Approval Workflow YOK

**İhtiyaç:**
```
Status Machine:
draft → pending → confirmed
              ↘ rejected

Endpoints:
POST /api/hotel/bookings/{id}/approve
POST /api/hotel/bookings/{id}/reject {reason}
```

### 2. Acenta Özel Fiyatlandırma YOK

**İhtiyaç:**
- Bazı acenteler %10 indirimli görsün
- Bazı acenteler sabit fiyat görsün
- Link bazlı pricing override

### 3. Acenta Özel Content YOK

**İhtiyaç:**
- Acenta A: Otel fotoğrafları set-1
- Acenta B: Otel fotoğrafları set-2
- Promosyon metinleri farklı

### 4. Performance Cache YOK

**İhtiyaç:**
- Busy dates (Ocak, Şubat) → Her search real-time hesaplama ağır
- Pre-computed snapshots (günlük job)

---

## 📋 SONRAKI ADIMLAR (FAZ-2 ve FAZ-3)

### FAZ-2: Tek Gerçeklik Motoru

**Yapılacaklar:**
1. ✅ Veri sözleşmesi netleştir (PMS vs Acenta katmanı)
2. ✅ Approval workflow ekle (pending status)
3. ✅ Hotel approve/reject endpoints
4. ✅ Status machine implement
5. ✅ Event cascade düzenle

**Süre:** 1 hafta

### FAZ-3: Core Operasyonel

**Yapılacaklar:**
1. ✅ Stop-sell iyileştirme (zaten var, audit ekle)
2. ✅ Acenta kotası (zaten var, log/usage)
3. ✅ Talep listesi SLA (onay süresi renkleri)
4. ✅ İptal neden kodları (KPI için)
5. ✅ Mutabakat basitleştirme (ay kapatma)

**Süre:** 1-2 hafta

---

## ✅ CEVAPLAR

**Senin sorduğun 4 endpoint:**

1. **Availability Search:** ✅ VAR - `POST /api/agency/search`
2. **Create Request:** ✅ VAR - `POST /api/agency/bookings/draft`
3. **Approve/Reject:** ❌ YOK - Direkt confirm oluyor
4. **Cancel:** ✅ VAR - `POST /api/bookings/{id}/cancel`

**Mutabakat:**
- ✅ VAR - `/api/hotel/settlements` ve `/api/agency/settlements`
- ✅ CSV export destekli
- ✅ Month bazlı filtering

**Komisyon:**
- ✅ Acenta bazlı (agency_hotel_links seviyesinde)
- ✅ Type: percent veya fixed_per_booking
- ✅ Snapshot'lı (değişim geçmişi etkilemez)

---

**Detaylı rapor: `/app/SYSTEM_STATE_ANALYSIS.md`**

Sıradaki: Senin çıkaracağın şemayı bekliyorum (FAZ-2 için approval workflow + veri modelleri) 🚀