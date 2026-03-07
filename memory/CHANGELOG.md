# CHANGELOG — Acenta Master Travel SaaS

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