# CHANGELOG — Acenta Master Travel SaaS

## 2026-03-08 — Usage Metering PR-UM3 (`report.generated`, `export.generated`, `integration.call`)
- `backend/app/services/usage_service.py` genişletildi:
  - `track_report_generated(...)`
  - `track_export_generated(...)`
  - `track_integration_call(...)`
  - ortak tenant/org resolve + best-effort tracking helper
- Gerçek report output meterlandı:
  - `backend/app/services/report_output_service.py` eklendi
  - `backend/app/routers/admin_reports.py` match-risk executive PDF üretimini bu service’e taşıdı
- Gerçek export output meterlandı:
  - `backend/app/routers/reports.py` → `sales-summary.csv`
  - `backend/app/routers/enterprise_export.py` → tenant ZIP export
  - `backend/app/routers/enterprise_audit.py` → audit CSV streaming export
  - `backend/app/routers/exports.py` → persisted admin export run
- Google Sheets entegrasyon çağrısı instrumentation eklendi:
  - `backend/app/services/sheets_provider.py`
  - `backend/app/services/google_sheets_client.py`
  - `backend/app/services/hotel_portfolio_sync_service.py`
  - `backend/app/services/sheet_sync_service.py`
  - `backend/app/services/sheet_writeback_service.py`
- Guardrail doğrulamaları:
  - aynı `X-Correlation-Id` ile tekrar isteklerde double count oluşmuyor
  - JSON read/dashboard endpoint’leri usage artırmıyor
  - `integration.call` yalnız gerçek Google Sheets API call boundary’sinde tetiklenecek şekilde bağlandı
- Test / doğrulama:
  - manual curl smoke geçti
  - `testing_agent` iteration_20: 17/17 backend test geçti
  - `deep_testing_backend_v2` regression check geçti
  - Not: Google Sheets runtime config bu preview ortamında tanımlı değil; bu yüzden `integration.call` path’i kod + wiring seviyesinde doğrulandı, canlı dış çağrı smoke’u yapılamadı

## 2026-03-08 — Usage Metering PR-UM2 (`reservation.created`)
- Kanonik reservation create flow instrument edildi:
  - `backend/app/services/reservations.py`
  - `backend/app/routers/reservations.py`
  - `backend/app/routers/b2b.py`
  - `backend/app/routers/quotes.py`
- Direct reservation insert yapan tour path de kapsandı:
  - `backend/app/routers/tours_browse.py`
- `backend/app/services/usage_service.py` içine `track_reservation_created(...)` eklendi
  - önce business event / `source_event_id`
  - yoksa reservation `_id` fallback
  - yalnızca yeni create anında meter yazar
  - confirm / cancel / status update akışlarında yeni usage yazmaz
- Testler eklendi:
  - `backend/tests/integration/billing/test_usage_reservation_created.py`
- Doğrulama:
  - ilgili backend pytest senaryoları geçti
  - preview curl ile `/api/b2b/book` sonrası usage +1 doğrulandı
  - `/api/reservations/{id}/confirm` sonrası usage artmadığı doğrulandı

## 2026-03-08 — Demo Seed Data Utility
- `backend/seed_demo_data.py` eklendi; `python seed_demo_data.py --agency "Demo Travel" [--reset]` ile çalışır
- `backend/app/services/demo_seed_service.py` eklendi; modüler seed akışı içerir:
  - `create_demo_agency()`
  - `create_demo_user()`
  - `seed_tours()`
  - `seed_hotels()`
  - `seed_customers()`
  - `seed_reservations()`
  - `seed_availability()`
- Seed artık yeni demo tenant için gerçekçi satış demosu verisi üretir:
  - organization + tenant + membership + subscription + tenant capability
  - 5 tur ve bunlara bağlı supporting product/rate plan/inventory
  - 5 otel + agency-hotel link + 10 availability snapshot
  - 20 müşteri + 30 rezervasyon
- Doğrulama:
  - CLI smoke test geçti
  - tekrar çalıştırmada duplicate oluşmadığı doğrulandı
  - demo kullanıcı ile `/api/auth/login` başarılı

## 2026-03-07 — CI / Test Collection Compatibility Fix
- Preview-only backend test modülleri artık preview base URL yoksa collection aşamasında hata vermek yerine güvenli şekilde skip oluyor:
  - `test_admin_all_users_and_agency_nav.py`
  - `test_admin_all_users_crud.py`
  - `test_agency_modules_and_branding.py`
  - `test_agency_sheets_api.py`
  - `test_pr_v1_foundation_acceptance.py`
- `backend/tests/preview_auth_helper.py` içine `get_preview_base_url_or_skip(...)` eklendi
- `backend/pytest.ini` güncellendi; exit gate marker kayıtları tamamlandı ve unknown-mark kaynaklı warning kirliliği azaltıldı
- `backend/app/bootstrap/*` ve bazı yeni dosyalardaki newline / Ruff lint sorunları giderildi; `ruff check app/ --select E,F,W --ignore E501,E402` temiz geçti

## 2026-03-07 — Deployment / Mongo Migration Hardening
- Root cause doğrulandı: preview/sandbox local Mongo örneğinde yüzlerce `agentis_test_*` test veritabanı birikmişti; bu durum Atlas migration/user creation aşamasında `COLLECTION_ROLES_LIMIT_EXCEEDED` limitine yol açıyordu
- `backend/app/bootstrap/runtime_init.py` içine `cleanup_nonprod_test_databases(...)` eklendi
  - sadece non-production + local Mongo ortamlarında çalışır
  - `agentis_test_*` ve `agentis_test_seeded_*` veritabanlarını temizler
  - production/staging Atlas ortamına dokunmaz
- `backend/tests/conftest.py` session başlangıç/bitişinde orphan test DB cleanup yapacak şekilde güçlendirildi
- Doğrulama:
  - local Mongo test DB sayısı `127 -> 0`
  - `/api/health` ve `/api/auth/login` çalışmaya devam ediyor
  - preview-only test dosyaları `--collect-only` ile hatasız

## 2026-03-07 — Usage Metering PR-UM1 Foundation
- `backend/app/constants/usage_metrics.py` eklendi; kanonik metrik sabitleri tanımlandı:
  - `reservation.created`
  - `report.generated`
  - `export.generated`
  - `integration.call`
- Geriye dönük uyumluluk için legacy metric desteği korundu: `b2b.match_request`
- `backend/app/repositories/usage_daily_repository.py` eklendi; günlük aggregate read-model oluşturuldu
- `backend/app/repositories/usage_ledger_repository.py` genişletildi:
  - `organization_id`
  - `metadata`
  - ek indeksler
  - kanonik `insert_event(...)` akışı
- `backend/app/services/usage_service.py` foundation seviyesinde refactor edildi:
  - `track_usage_event(...)`
  - metric validation
  - ledger + daily birlikte yazım
  - `get_usage_summary(...)` artık `totals_source` döndürüyor (`usage_daily` / `usage_ledger`)
- `backend/app/indexes/seed_indexes.py` içine usage ledger + usage daily indexleri eklendi
- Testler eklendi / güncellendi:
  - `backend/tests/integration/billing/test_usage_metering_foundation.py`
  - `backend/tests/integration/billing/test_usage_tracking.py`
- Kapsam dışı bırakıldı:
  - hiçbir business flow instrumentation yapılmadı
  - hiçbir UI değişikliği yapılmadı

## 2026-03-07 — Entitlement Projection Engine V1
- Kanonik entitlement katmanı eklendi:
  - `backend/app/services/entitlement_service.py`
  - `backend/app/repositories/tenant_entitlement_repository.py`
- Plan kataloğu `starter / pro / enterprise` için zenginleştirildi:
  - plan açıklaması
  - özellik listesi
  - limitler (`users.active`, `reservations.monthly`)
  - usage allowance alanları (`reservation.created`, `report.generated`, `export.generated`, `integration.call`, `b2b.match_request`)
- Admin tenant feature endpoint’leri entitlement projection dönecek şekilde genişletildi
- Tenant self-service surface artık kanonik entitlement shape döndürüyor:
  - `GET /api/tenant/features`
  - `GET /api/tenant/entitlements`
- Public pricing kaynağı hardcoded matrixten entitlement service’e taşındı:
  - `GET /api/onboarding/plans`
- Frontend entitlement UI teslim edildi:
  - Admin entitlement overview kartı
  - Public pricing sayfasında limit ve usage allowance blokları
- Testler:
  - backend pytest paketleri geçti
  - testing agent iteration_19 geçti
  - frontend entitlement UI smoke ve otomasyon geçti
  - backend deep validation geçti

## 2026-03-07 — `/api/v1` Standardizasyonu Tamamlandı
- PR-V1-0 foundation / route inventory tamamlandı
- PR-V1-1 low-risk system/public metadata alias rollout tamamlandı
- PR-V1-2A auth bootstrap alias-first rollout tamamlandı
- PR-V1-2B session management alias-first rollout tamamlandı
- PR-V1-2C settings alias-first rollout tamamlandı
- `domain_v1_progress` ve `migration_velocity` route inventory tooling’e eklendi

## 2026-03-06 — Auth, Session ve Runtime Hardening
- Web cookie auth compat cleanup tamamlandı
- Persistent session modeli ve refresh rotation sertleştirildi
- Tenant-bound login ve tenant guardrail’leri eklendi
- Mobile BFF (`/api/v1/mobile/*`) kontratı teslim edildi
- Runtime composition `server.py` dışına ayrıştırıldı
- Worker / scheduler dedicated runtime wiring tamamlandı

## 2026-03-06 — Operasyonel ve Yönetimsel İyileştirmeler
- Audit, tenant health, admin araçları ve çeşitli yönetim ekranları stabilize edildi
- Google Sheets sync ve agency module yönetimi geliştirildi
- Web aktif session / active devices ekranı tamamlandı

## Notlar
- Entitlement V1 şu aşamada projection ve görünürlük katmanıdır.
- Gerçek usage instrumentation, quota enforcement ve billing uyumu bir sonraki roadmap adımıdır.