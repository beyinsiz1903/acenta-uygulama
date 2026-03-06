# PR-5B Entegrasyon Checklist

> Kapsam: Mevcut mobil yapıyı koruyarak `SecureStore + session bootstrap + /api/v1/mobile route adoption` geçişini hazırlamak.
> Referans backend contract: `backend/app/modules/mobile/mobile_contract.md`

## 1. Amaç
- Mobil repo geldiğinde PR-5A ile açılan Mobile BFF contract’ına hızlı ve düşük riskli şekilde bağlanmak.
- AsyncStorage tabanlı auth/token akışını SecureStore’a taşımak.
- Mobil istemciyi yeni `/api/v1/mobile/*` endpoint’lerine geçirmek.

## 2. Mobil repo geldiğinde değişecek dosyalar
- Mevcut auth storage/helper dosyası (`AsyncStorage` kullanan yer)
- Mevcut auth service / API client dosyası (`login`, `refresh`, `logout`, `me` çağrıları)
- Uygulama bootstrap/root entry dosyası (app açılışında session restore yapan yer)
- Login ekranı / auth store / auth context dosyası
- Dashboard ekranı veya data hook’u
- Rezervasyon liste ekranı veya data hook’u
- Rezervasyon detay ekranı veya data hook’u
- Rapor/özet ekranı veya data hook’u
- Gerekirse mevcut mobile backend/proxy base URL config dosyası

> Not: Repo henüz workspace’te olmadığı için yukarıdaki maddeler mevcut mobil yapının birebir karşılık gelen dosyalarına uygulanacak; yeni klasör mimarisi önerilmeyecek.

## 3. Eklenecek yeni dosyalar
- `mobile/src/lib/secureStoreSession.(ts|js)`
  - access token, refresh token, tenant id, session id okuma/yazma/temizleme
- `mobile/src/lib/sessionBootstrap.(ts|js)`
  - app açılışında restore → validate → refresh fallback → logout karar akışı
- `mobile/src/lib/mobileBffClient.(ts|js)`
  - `/api/v1/mobile/*` route mapping ve ortak header yönetimi (`Authorization`, `X-Tenant-Id`)

## 4. SecureStore migration akışı
1. İlk açılışta eski `AsyncStorage` auth key’lerini oku.
2. `SecureStore` boş, legacy token’lar doluysa tek seferlik kopyala.
3. `migration_done` benzeri bir flag yaz.
4. İlk başarılı bootstrap sonrası eski auth key’lerini temizle.
5. Migration yarıda kalırsa aynı release içinde sadece read-fallback ver; uzun süre dual-write yapma.

Taşınacak minimum alanlar:
- `access_token`
- `refresh_token`
- `tenant_id`
- `session_id`

## 5. Session bootstrap akışı
1. App cold start → `SecureStore` içinden token/session/tenant verisini yükle.
2. `access_token` varsa `GET /api/v1/mobile/auth/me` çağır.
3. Header’lar:
   - `Authorization: Bearer <access_token>`
   - `X-Tenant-Id: <tenant_id>` (varsa)
4. `/auth/me` 200 dönerse kullanıcı state’ini hydrate et.
5. `/auth/me` 401 dönerse `POST /api/auth/refresh` ile refresh dene.
6. Refresh başarılıysa yeni token’ları `SecureStore`’a yaz ve `/auth/me` tekrar çağır.
7. Refresh başarısızsa tüm session verisini temizle ve login ekranına yönlendir.

## 6. Login / refresh / logout davranışı
### Login
- Endpoint: `POST /api/auth/login`
- Request minimum:
  - `email`
  - `password`
  - `tenant_id` veya `tenant_slug` (tenant-seçimli akış varsa)
- Beklenen alanlar:
  - `access_token`
  - `refresh_token`
  - `tenant_id`
  - `session_id`
  - `expires_in`
  - `auth_transport` (`bearer` beklenir)
- Başarılı login sonrası token/session alanlarını `SecureStore`’a yaz, sonra `GET /api/v1/mobile/auth/me` ile bootstrap et.

### Refresh
- Endpoint: `POST /api/auth/refresh`
- Request body:
  - `refresh_token`
- Beklenen alanlar:
  - `access_token`
  - `refresh_token` (rotation var; eskisini overwrite et)
  - `expires_in`
  - `auth_transport`

### Logout
- Endpoint: `POST /api/auth/logout`
- Request:
  - bearer access token
- Davranış:
  - response ne olursa olsun local `SecureStore` temizlenecek
  - auth state resetlenecek
  - login ekranına dönülecek

## 7. Hangi ekran hangi `/api/v1/mobile` endpoint’ine bağlanacak
- App bootstrap / current user → `GET /api/v1/mobile/auth/me`
- Ana ekran / dashboard kartları → `GET /api/v1/mobile/dashboard/summary`
- Rezervasyon liste ekranı → `GET /api/v1/mobile/bookings`
- Rezervasyon filtreleri → `GET /api/v1/mobile/bookings?status_filter=<status>&limit=<n>`
- Rezervasyon detay ekranı → `GET /api/v1/mobile/bookings/{id}`
- Hızlı rezervasyon / draft create ekranı → `POST /api/v1/mobile/bookings`
- Rapor / satış özeti ekranı → `GET /api/v1/mobile/reports/summary`

Değiştirilecek legacy çağrılar:
- `/api/bookings` → `/api/v1/mobile/bookings`
- `/api/reports/summary` → `/api/v1/mobile/reports/summary`
- Kullanıcı bilgisi için legacy web shape kullanan çağrılar → `/api/v1/mobile/auth/me`

## 8. Beklenen request/response shape özeti
### `POST /api/auth/login`
```json
{
  "access_token": "...",
  "refresh_token": "...",
  "expires_in": 28800,
  "tenant_id": "tenant_x",
  "session_id": "session_x",
  "auth_transport": "bearer"
}
```

### `GET /api/v1/mobile/auth/me`
```json
{
  "id": "user_x",
  "email": "user@example.com",
  "name": "User",
  "roles": ["agency_admin"],
  "organization_id": "org_x",
  "tenant_id": "tenant_x",
  "current_session_id": "session_x",
  "allowed_tenant_ids": ["tenant_x"]
}
```

### `GET /api/v1/mobile/dashboard/summary`
```json
{
  "bookings_today": 0,
  "bookings_month": 0,
  "revenue_month": 0,
  "currency": "TRY"
}
```

### `GET /api/v1/mobile/bookings`
```json
{
  "total": 1,
  "items": [
    {
      "id": "booking_x",
      "status": "draft",
      "total_price": 3499.5,
      "currency": "TRY",
      "customer_name": "Jane Doe",
      "hotel_name": "Mobile Hotel",
      "check_in": "2026-03-10",
      "check_out": "2026-03-12",
      "source": "mobile",
      "created_at": "2026-03-06T00:00:00+00:00",
      "updated_at": "2026-03-06T00:00:00+00:00"
    }
  ]
}
```

### `POST /api/v1/mobile/bookings`
Request minimum:
```json
{
  "amount": 3499.5,
  "currency": "TRY",
  "customer_name": "Jane Doe",
  "hotel_name": "Mobile Hotel",
  "booking_ref": "MB-1001",
  "check_in": "2026-03-10",
  "check_out": "2026-03-12",
  "notes": "Late arrival"
}
```

Response minimum:
```json
{
  "id": "booking_x",
  "tenant_id": "tenant_x",
  "agency_id": "agency_x",
  "status": "draft",
  "total_price": 3499.5,
  "currency": "TRY",
  "customer_name": "Jane Doe",
  "hotel_name": "Mobile Hotel",
  "booking_ref": "MB-1001"
}
```

### `GET /api/v1/mobile/reports/summary`
```json
{
  "total_bookings": 2,
  "total_revenue": 2300,
  "currency": "TRY",
  "status_breakdown": [
    {"status": "booked", "count": 1},
    {"status": "draft", "count": 1}
  ],
  "daily_sales": [
    {"day": "2026-03-06", "revenue": 1500, "count": 1}
  ]
}
```

## 9. Test checklist
- Fresh install → login → app bootstrap başarılı
- Upgrade install → AsyncStorage verisi SecureStore’a tek seferde migrate oluyor
- Expired access token → refresh rotation çalışıyor
- Refresh başarısız → kullanıcı temiz şekilde logout/login ekranına düşüyor
- Dashboard yeni mobile endpoint’ten veri alıyor
- Rezervasyon listesi yeni mobile endpoint’ten veri alıyor
- Rezervasyon detayı yeni mobile endpoint’ten veri alıyor
- Draft booking create yeni mobile endpoint ile çalışıyor
- Reports summary yeni mobile endpoint’ten veri alıyor
- `X-Tenant-Id` header tenant-scoped ekranlarda doğru gidiyor
- `_id` bekleyen legacy mapper kalmıyor; tüm ekranlar `id` alanını kullanıyor

## 10. Rollback / edge-case notları
- Route adoption bir adapter katmanı üzerinden yapılmalı; kritik hata olursa eski endpoint mapping’e hızlı dönüş mümkün olsun.
- Legacy `AsyncStorage` read-fallback en fazla bir release tutulmalı; sonra tamamen kaldırılmalı.
- Refresh loop sonsuz olmamalı; tek retry sonrası logout yapılmalı.
- `tenant_id` login response’unda gelmezse tenant-scoped bootstrap zorlanmamalı; kullanıcıya yeniden login/tenant seçimi akışı uygulanmalı.
- SecureStore write/read hata verirse auth state yarım bırakılmamalı; temizleyip güvenli şekilde login ekranına dönülmeli.