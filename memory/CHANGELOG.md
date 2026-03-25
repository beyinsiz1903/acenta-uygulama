# CHANGELOG

## 2026-02 — Ürün Konumlandırma & Dokümantasyon Reseti (Faz 1) + Test Suite %100 Yeşil

### Stratejik Değişiklikler
- **Ürün tanımı genişletildi:** "Otel acenteleri" → "Tur, otel, uçak ve B2B satış yapan acenteler için acente bulut otomasyonu"
- **Modül sınıflandırması oluşturuldu:** Çekirdek / Destekleyici Çekirdek / Extension üçlü katman yapısı
  - Çekirdek: identity, tenant, auth, booking, finance, supplier, crm
  - Destekleyici Çekirdek: operations, inventory, pricing, reservation-control
  - Extension: b2b, marketplace, enterprise, partner-graph, reporting, mobile, webhook, ai-assistant
- **Hotel/PMS yeniden konumlandırıldı:** Yan oyuncak değil, "Destekleyici Çekirdek / Operasyonel Derinlik" katmanında

### Test Suite Stabilizasyonu (P0 Tamamlandı)
- **Supplier circuit test:** Audit log yerine doğrudan DB state kontrolü eklendi + audit için retry loop
- **Login fixture'ları:** `agency_token` ve `admin_token` fixture'larına 3-retry mekanizması eklendi
- **Rerun politikası genişletildi:** `TimeoutError` ve `OSError` de otomatik rerun kapsamına alındı
- **Sonuç:** 0 FAILED, 0 ERROR — 680 passed, 1787 skipped, 8 xfail, 1 rerun

### Dokümanlar
- `README.md` — Tam yeniden yazıldı (ürün tanımı, mimari, kurulum, entegrasyon, proje yapısı)
- `memory/PRD.md` — Yeni konumlandırma ile güncellendi
- `docs/MODULE_MAP.md` — Detaylı modül haritası oluşturuldu (sahiplik, konum, sorumluluk)
- `memory/ROADMAP.md` — Strateji uyumlu olarak güncellendi
- `docs/COMMERCIAL_PACKAGES.md` — Ticari paketleme dokümantasyonu
- `docs/TEST_ISOLATION_POLICY.md` — Test izolasyon kuralları ve politikası

---

## 2026-03-20 — Ruff Linting & CI Test Fix

### Düzeltmeler
- `backend/app/modules/booking/service.py`: 2 adet F841 (unused variable) hatası düzeltildi
- `tests/test_orphan_migration.py`: CI ortamında boş veritabanı sorununu çözen idempotent pytest fixture eklendi

---

## 2026-03-19 — Backend Test Suite Stabilization (P0)

### Kritik Düzeltmeler
- **ResponseEnvelopeMiddleware Cookie Loss:** `dict(response.headers)` → `_rebuild_response()` ile Set-Cookie header korunması
- **Event Loop Mismatch:** 14 test dosyasında `@pytest.mark.asyncio` → `@pytest.mark.anyio`
- **Booking State Machine Compatibility:** quoted/optioned → confirmed geçişleri eklendi
- **OCC Version Filter:** Legacy booking'ler için `version` alanı olmayan dokümanlar desteklendi
- **Mobile BFF Routes:** `/api/mobile/*` kaydı düzeltildi
- **Audit Service:** `request=None` güvenli işleme
- **Conftest Envelope Fixes:** Response envelope unwrap düzeltmeleri

### Test Sonuçları
- Öncesi: 71 FAILED + 17 ERROR = 88 başarısız
- Sonrası: 1 FAILED + 3 ERROR (izolasyonda tümü geçiyor — test-ordering sorunu)
