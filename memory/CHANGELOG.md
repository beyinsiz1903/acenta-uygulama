# CHANGELOG — Acenta Master Travel SaaS

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