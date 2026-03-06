# Mobile Cutover Runbook

## 1. Preconditions
- PR-5A Mobile BFF backend deploy edilmiş ve doğrulanmış olmalı.
- PR-5B mobil build, `SecureStore` migration + session bootstrap + `/api/v1/mobile/*` adoption içermeli.
- Login, refresh ve logout akışları staging ortamında test edilmiş olmalı.
- Cutover öncesi legacy mobil build rollback için erişilebilir olmalı.

## 2. Mobile Build Version
- Cutover build: `PR-5B compatible mobile release`
- Minimum içerik:
  - AsyncStorage → SecureStore migration
  - `GET /api/v1/mobile/auth/me` bootstrap
  - bookings / reports / dashboard için `/api/v1/mobile/*` route adoption

## 3. SecureStore Migration Flow
1. Uygulama açılışında legacy AsyncStorage auth anahtarlarını oku.
2. SecureStore boşsa token/session verisini tek seferlik taşı.
3. `migration_done` flag yaz.
4. İlk başarılı bootstrap sonrası legacy anahtarları temizle.
5. Migration veya refresh başarısızsa kullanıcıyı güvenli şekilde login ekranına düşür.

## 4. Endpoint Switch (`/api/v1/mobile`)
- Current user bootstrap → `GET /api/v1/mobile/auth/me`
- Dashboard → `GET /api/v1/mobile/dashboard/summary`
- Booking list → `GET /api/v1/mobile/bookings`
- Booking detail → `GET /api/v1/mobile/bookings/{id}`
- Draft booking create → `POST /api/v1/mobile/bookings`
- Reports summary → `GET /api/v1/mobile/reports/summary`

## 5. Rollout Steps
1. Staging build ile login/bootstrap smoke yap.
2. Limited internal user grubunda cutover build’i yayınla.
3. Auth success, refresh success, mobile BFF 2xx oranını 30-60 dk izle.
4. Kritik hata yoksa production rollout’u genişlet.
5. İlk 24 saatte rollback build hazır tutulur.

## 6. Monitoring
- Login başarı oranı
- Refresh başarısızlık oranı
- `401` ve `403` artışı
- `/api/v1/mobile/*` 5xx oranı
- Booking create hata oranı
- Session bootstrap sonrası beklenmeyen logout sayısı

## 7. Rollback
- Mobil istemci mapping’i legacy endpoint setine geri al.
- SecureStore verisini koru, ama yeni bootstrap logic’i devre dışı bırak.
- Gerekirse son stabil mobil build’i yeniden yayınla.
- Rollback sonrası login, bookings list, booking detail ve reports smoke tekrar çalıştır.
