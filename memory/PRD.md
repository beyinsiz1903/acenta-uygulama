# PRD — Syroce Travel Agency Operating System

## Orijinal Problem Tanımı
Kullanıcı, mevcut çok kiracılı seyahat/acenta SaaS ürününü üretime daha hazır hale getirmeyi, kritik akışları sağlamlaştırmayı ve gelir modeliyle uyumlu şekilde geliştirmeyi istedi.

Son kritik ürün odağı Google Sheets entegrasyonu oldu:
- admin panelden yönetilebilir olmalı
- eksik credential durumunda crash etmemeli
- otel envanteri / kontenjan senkronu güvenilir çalışmalı
- sheet üzerinden gelen rezervasyonlar sistemde ilgili otelin akışına düşebilmeli

## Ürün Hedefi
- Acenta, otel ve yönetim ekiplerini tek panelde birleştiren bir işletim sistemi sunmak
- Rezervasyon, müşteri, finans, raporlama ve entegrasyon operasyonlarını tek üründe toplamak
- Çok kiracılı mimari, güvenli auth/session ve tenant izolasyonunu korumak
- Paketleme, entitlement ve kullanım ölçümü ile sürdürülebilir SaaS gelir modeli kurmak

## Çekirdek Kullanıcılar
- **Super Admin / Admin:** tenant, katalog, entegrasyon ve platform operasyonları
- **Agency Admin / Agency Agent:** rezervasyon, B2B satış, müşteri ve rapor akışları
- **Hotel Admin / Hotel Staff:** otel rezervasyonları, allotment, stop-sell ve müsaitlik yönetimi

## Güncel Mimari
- **Frontend:** React + CRA + Tailwind + shadcn/ui
- **Backend:** FastAPI
- **Database:** MongoDB
- **Auth:** JWT + cookie compat/session modeli
- **Preview routing:** frontend `/`, backend `/api/*`

## Kritik Teknik Guardrail'ler
- Frontend tüm API çağrılarında `process.env.REACT_APP_BACKEND_URL` kullanır
- Backend yalnız `MONGO_URL` ve `DB_NAME` ile Mongo'ya bağlanır
- Mongo `_id` / `ObjectId` response'a sızdırılmaz
- Tenant erişimi request context ve role guard'larla korunur
- Preview testleri preview URL yoksa güvenli skip davranışı göstermelidir

## Temel Ürün Gereksinimleri
1. Güvenli giriş, oturum ve rol bazlı yönlendirme
2. Tenant-aware backend erişimi ve veri izolasyonu
3. Rezervasyon/booking, CRM, finans ve raporlama çekirdeği
4. Entegrasyon yönetimi, özellikle Google Sheets için yönetilebilir admin yüzeyi
5. Paket / entitlement / usage metering katmanı
6. Trial → paid dönüşümünü destekleyen satış yüzeyi

## Google Sheets Entegrasyonu — Güncel Kapsam

### Tamamlananlar
- Admin Google Sheets config durumu endpoint'i ve graceful degraded davranış
- Sheet template merkezi, doğrulama paneli ve bağlantı yönetim UI'si
- Service Account JSON doğrulaması ve tenant-aware config cache
- Inventory sync için kolon/doğrulama ve write-back şablon akışı
- `Rezervasyonlar` sekmesi için write-back başlık standardı
- **Yeni:** `incoming_reservation` / `external_reservation` tipli sheet satırlarının otel rezervasyon akışına import edilmesi
- **Yeni:** sheet senkronundan gelen kontenjan sinyalinin agency `Otellerim` ekranına yansıtılması

### Hâlâ Bloklu Olanlar
- Canlı Google API erişimi için gerçek Service Account credential henüz paylaşılmadı
- Bu nedenle gerçek sheet üzerinde end-to-end canlı doğrulama henüz tamamlanmadı

### Beklenen Kullanım Modeli
- Ana veri sekmesi: `Tarih`, `Oda Tipi`, `Fiyat`, `Kontenjan` kolonları
- Write-back / reservation sekmesi: `Rezervasyonlar`
- Sheet'ten sisteme rezervasyon importu için `Kayit Tipi` alanı:
  - `incoming_reservation`
  - `external_reservation`

## Monetizasyon ve Growth Özeti
- Entitlement projection aktif
- Usage metering ve quota warning aktif
- Trial signup + demo seed aktif
- Stripe checkout ve billing yönetim yüzeyi aktif
- Public landing, pricing ve login yüzeyi satış odaklı finalize edildi

## Test Kimlik Bilgileri
| Portal | Email | Password | Rol |
|---|---|---|---|
| Admin | admin@acenta.test | admin123 | Super Admin |
| Agency | agent@acenta.test | agent123 | Agency Admin |

## Bu Sprint İçin Referans Dosyalar
- `backend/app/services/sheet_connection_service.py`
- `backend/app/services/hotel_portfolio_sync_service.py`
- `backend/app/services/sheet_reservation_import_service.py`
- `backend/app/services/google_sheet_schema_service.py`
- `backend/app/routers/admin_sheets.py`
- `backend/app/routers/agency.py`
- `frontend/src/pages/admin/AdminPortfolioSyncPage.jsx`
- `frontend/src/components/admin/sheets/SheetTemplateCenter.jsx`
- `frontend/src/components/admin/sheets/SheetValidationPanel.jsx`
- `frontend/src/pages/AgencyHotelsPage.jsx`

## Güncel Odak
- P0: Google Sheets entegrasyonunu gerçek credential ile aktive edip canlı smoke test yapmak
- P0: Kullanıcıya Service Account kurulum rehberini net vermek
- P1: Google Sheets üzerinden gelen rezervasyonların hotel-side status lifecycle/write-back kapanışını daha da güçlendirmek

## Doküman Ayrımı
- Bu dosya statik ürün bağlamını taşır
- Detaylı teslim geçmişi için `CHANGELOG.md`
- Kalan ve öncelikli işler için `ROADMAP.md`