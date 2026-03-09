# CHANGELOG — Acenta Master Travel SaaS

## 2026-03-09 — Google Sheets admin validation UI + endpoint finalize
- Backend tamamlamaları:
  - `POST /api/admin/sheets/validate-sheet` eklendi; configured=false iken graceful checklist + required fields payload döner
  - `GET /api/admin/sheets/download-template/{template_name}` eklendi; `inventory-sync` ve `reservation-writeback` CSV indirme aktif
  - `POST /api/admin/sheets/connections` REST alias eklendi; mevcut connect flow ile hizalı
  - yeni servisler: `sheet_connection_service.py`, `sheet_template_service.py`
  - Service Account JSON doğrulaması sıkılaştırıldı; gerekli alanlar netleştirildi: `type`, `project_id`, `private_key`, `client_email`, `token_uri`
- Frontend teslimi:
  - `AdminPortfolioSyncPage` içine `Sheet şablon merkezi` ve `Sheet doğrulama merkezi` eklendi
  - yeni bileşenler: `SheetTemplateCenter.jsx`, `SheetValidationPanel.jsx`
  - connections table validation badge + write-back görünürlüğü aldı
- Doğrulama:
  - `pytest /app/backend/tests/test_admin_sheets_management.py -q` → 5/5 PASS
  - `pytest /app/backend/tests/test_agency_sheets_api.py -q` → 14/14 PASS
  - testing agent: `/app/test_reports/iteration_45.json` → backend %100 / frontend %100 PASS
  - `auto_frontend_testing_agent` → portfolio-sync smoke PASS
  - `deep_testing_backend_v2` → endpoint regression PASS

## 2026-03-09 — Google Sheets P0 hardening
- Backend hardening teslim edildi:
  - tenant-aware Google Sheets config cache eklendi; DB üzerinden kaydedilen service account artık tenant bağlamında okunuyor
  - yeni `GET /api/admin/sheets/templates` endpoint’i eklendi; zorunlu kolonlar + write-back başlık şablonu API’den döner hale geldi
  - admin ve agency connect akışları `validation_status`, `validation_summary` ve tutarlı `writeback_tab=Rezervasyonlar` alanlarıyla güçlendirildi
  - write-back tab bootstrap guard eklendi; yapılandırma varsa `Rezervasyonlar` sekmesi güvenli başlık kontrolü/oluşturması yapılıyor
  - legacy `GET /api/admin/import/sheet/config` tenant-aware config yoluna hizalandı
- Doğrulama:
  - Python lint: ilgili backend dosyaları PASS
  - manual curl smoke: `admin /api/admin/sheets/config`, `/templates`, `/admin/import/sheet/config` PASS
  - manual connect cleanup: admin ve agency fake `sheet_id` ile pending-configuration connect + delete PASS
  - `pytest /app/backend/tests/test_agency_sheets_api.py -q` → 14/14 PASS
  - `deep_testing_backend_v2` → Google Sheets hardening PASS (agency login sırasında rate limit notu dışında functional issue yok)

## 2026-03-09 — CI lint hotfix (requirements + LoginPage)
- Backend CI fix:
  - `backend/requirements.txt` içine CloudFront extra index satırı geri eklendi
  - amaç: CI install sırasında `emergentintegrations==0.1.0` paketinin çözülmesini garanti etmek
- Frontend lint fix:
  - `frontend/src/pages/LoginPage.jsx` içinde redirect guard için kullanılan `useRef` kaldırıldı
  - yerine `useState` kullanıldı; `react-hooks/refs` ESLint hatası temizlendi
- Doğrulama:
  - `mcp_lint_javascript` → `/app/frontend/src/pages/LoginPage.jsx` PASS
  - `PIP_CONFIG_FILE=/dev/null python -m pip install --dry-run -r requirements.txt` PASS
  - browser smoke: `/login` → admin login → `/app/admin/dashboard` PASS
  - `auto_frontend_testing_agent` → LoginPage regression PASS
  - `deep_testing_backend_v2` → auth + admin agencies PASS

## 2026-03-09 — Fork revalidation (kod değişikliği yok)
- Bu forkta ek ürün kodu yazılmadan kalite turu tekrar koşuldu.
- Doğrulama:
  - manuel API self-test: admin + agency `login` / `me` PASS
  - browser smoke: landing, signup CTA, admin dashboard redirect ve logout PASS
  - `auto_frontend_testing_agent` → 21/21 PASS
  - `deep_testing_backend_v2` → auth, public theme, onboarding plans, admin/agency hafif endpoint regresyonları PASS
- Sonuç: beyaz ekran, kırık CTA veya görünür Türkçe copy problemi bu doğrulama turunda reproduce edilmedi.

## 2026-03-09 — Admin Tenant Panel Cleanup
- Backend enrichment:
  - `GET /api/admin/tenants` response’u plan + billing lifecycle alanlarıyla genişletildi
  - yeni `summary` payload eklendi: total, payment_issue_count, trial_count, canceling_count, active_count, by_plan, lifecycle
  - legacy subscription fallback korunarak admin liste görünümü daha dayanıklı hale getirildi
- Frontend cleanup:
  - `frontend/src/pages/admin/AdminTenantFeaturesPage.jsx` içinde yeni `Tenant Paket Merkezi` üst özet kartları eklendi
  - tenant dizinine filtre chip’leri, manuel yenile butonu ve risk odaklı sıralama eklendi
  - tenant satırları artık plan badge, lifecycle badge ve varsa grace date gösteriyor
  - mevcut feature yönetimi / subscription / usage / entitlement paneli regressionsız korundu
- Doğrulama:
  - `pytest /app/backend/tests/integration/feature_flags/test_admin_tenant_features.py -q` → 5/5 PASS
  - preview curl smoke: admin login + `/api/admin/tenants?limit=5` response shape PASS
  - browser smoke screenshot: `/app/admin/tenant-features` render PASS
  - `auto_frontend_testing_agent` → admin tenant cleanup akışı PASS
  - `deep_testing_backend_v2` → backend enrichment PASS

## 2026-03-09 — Billing redirect re-smoke + AppShell branding guard
- Frontend stabilizasyonu:
  - `frontend/src/components/AppShell.jsx` içinde admin-only branding isteği role guard ile sınırlandı
  - agency kullanıcıları artık `/api/admin/whitelabel-settings` endpoint’ine gereksiz 403 request atmıyor
- Doğrulama:
  - browser smoke: direkt `/app/settings/billing` → `/login` → başarılı giriş sonrası tekrar `/app/settings/billing`
  - yıllık toggle ve billing summary kartları regresyonsuz geçti
  - `auto_frontend_testing_agent` sonucu: 6/6 PASS, admin whitelabel request’i agency kullanıcı için artık yok
  - `deep_testing_backend_v2` sonucu: auth + billing regression PASS
- Test notu:
  - `agent@acenta.test` doğrulama sırasında `Pro / yearly / active` state’ine geçti ve backend bu state’i tutarlı döndürüyor

## 2026-03-09 — Billing History Timeline
- Backend teslimi:
  - `GET /api/billing/history` endpoint’i eklendi
  - `backend/app/services/billing_history_service.py` ile billing audit log’ları kullanıcı dostu timeline item’larına çevriliyor
  - event mapping kapsamı: `billing.checkout_completed`, `billing.plan_changed_now`, `billing.plan_change_scheduled`, `billing.subscription_cancel_scheduled`, `billing.subscription_reactivated`, `subscription.invoice_paid`, `subscription.payment_failed`, `subscription.canceled`
- Frontend teslimi:
  - `frontend/src/components/settings/BillingHistoryTimeline.jsx` eklendi
  - `frontend/src/pages/SettingsBillingPage.jsx` içine timeline kartı entegre edildi
  - loading / error / empty / populated state + `Geçmişi Yenile` butonu teslim edildi
- Doğrulama:
  - manual curl smoke: `/api/billing/subscription`, `/api/billing/history`
  - preview browser smoke: `/app/settings/billing`
  - `testing_agent` iteration_34: backend 12/12 PASS + frontend PASS

## 2026-03-08 — Soft Quota Warning + Upgrade CTA PR-UM5
- Backend warning katmanı eklendi:
  - `backend/app/services/quota_warning_service.py`
  - 70% → `warning`
  - 85% → `critical`
  - 100%+ → `limit_reached`
  - trial recommendation rule:
    - `<40%` → `Starter`
    - `40-80%` → `Pro`
    - `>80%` → `Enterprise`
- `backend/app/services/usage_read_service.py` genişletildi:
  - metric bazında `warning_level`, `warning_message`, `upgrade_recommended`
  - `cta_href=/pricing`, `cta_label=Planları Gör`
  - summary bazında `trial_conversion` payload
  - legacy `subscriptions` koleksiyonundan `trialing` durumu fallback ile okunuyor
- `backend/app/routers/tenant_features.py` quota-status response’u warning alanları ile genişletildi
- Frontend CTA / conversion yüzeyleri eklendi:
  - `frontend/src/components/usage/UsageQuotaCard.jsx`
  - `frontend/src/components/usage/UsageTrialRecommendation.jsx`
  - dashboard usage kartı warning + CTA gösterir
  - `/app/usage` usage kartları warning + CTA gösterir
  - admin usage overview bilinçli olarak CTA göstermez (`showCta={false}`)
  - app shell quota banner’ları admin olmayan kullanıcılarla sınırlandı
- Testler:
  - `backend/tests/test_usage_warning_levels.py` eklendi
  - `testing_agent` iteration_22: backend 18/18 PASS + frontend PASS
  - `auto_frontend_testing_agent` ile trial tenant üstünde CTA ve admin no-CTA guardrail doğrulandı
- Preview doğrulama notu:
  - trial CTA yüzeyini test etmek için demo trial tenant üzerinde `export.generated=85/100` preview usage verisi hazırlandı

## 2026-03-08 — Usage Visibility PR-UM4
- Backend read-model katmanı eklendi:
  - `backend/app/services/usage_read_service.py`
  - `backend/app/repositories/usage_daily_repository.py` içine daily trend yardımcıları
- Tenant endpoint eklendi / güçlendirildi:
  - `GET /api/tenant/usage-summary?days=30`
  - `backend/app/routers/tenant_features.py`
  - tenant context fallback eklendi: request state → user tenant_id → organization_id üzerinden tenant lookup
- Admin usage endpoint trend ile genişletildi:
  - `GET /api/admin/billing/tenants/{tenant_id}/usage?days=30`
  - `backend/app/routers/admin_billing.py`
- Frontend usage görünürlüğü teslim edildi:
  - `frontend/src/components/usage/UsageMetricTiles.jsx`
  - `frontend/src/components/usage/UsageTrendChart.jsx`
  - `frontend/src/components/usage/DashboardUsageSummaryCard.jsx`
  - `frontend/src/components/admin/AdminTenantUsageOverview.jsx`
  - `frontend/src/pages/UsagePage.jsx`
  - `frontend/src/lib/usage.js`
  - `frontend/src/pages/DashboardPage.jsx`
  - `frontend/src/pages/admin/AdminTenantFeaturesPage.jsx`
  - `frontend/src/components/AppShell.jsx`
  - `frontend/src/App.js`
- UX guardrail’leri uygulandı:
  - dashboard mini kartı yalnız `reservation.created`, `report.generated`, `export.generated` gösteriyor
  - tenant detay usage sayfası metrik kartları + 30 gün trend içeriyor
  - upgrade CTA bilinçli olarak eklenmedi; PR-UM5’e bırakıldı
- Testler:
  - `backend/tests/test_usage_metering_pr_um4.py` eklendi
  - `testing_agent` iteration_21: backend 15/15 PASS, frontend PASS
  - `auto_frontend_testing_agent` ile tenant context blocker tespit edildi ve fix sonrası tüm UI akışları doğrulandı

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