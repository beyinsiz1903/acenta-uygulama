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

## Son Uygulama Güncellemesi — 2026-03-09
- Admin Google Sheets yüzeyi `/app/admin/portfolio-sync` için UX sağlamlaştırıldı; `/app/admin/google-sheets` alias route'u eklendi.
- Connect wizard içinde `writeback_tab` alanı frontend formuna bağlandı ve API payload'una eklendi.
- Admin aksiyonlarına toast geri bildirimi eklendi: service account kaydetme, sync çalıştırma, toggle, silme, bağlantı oluşturma.
- Kritik admin ve agency UI elemanlarına ek `data-testid` alanları eklendi.
- Agency `Otellerim` kartlarında sheet ile ilişkili görünür alanlar için test kapsamı güçlendirildi.
- Test sonucu: Iteration 47 raporunda admin + agency Google Sheets akışı ve ilgili backend endpointleri geçti; credential yokken graceful `not_configured` davranışı doğrulandı.

## Son Doğrulama Notu — 2026-03-10
- Admin Portfolio Sync sayfası yeniden doğrulandı; `/app/admin/google-sheets` alias yönlendirmesi, manuel sync toast akışı ve connect wizard stabil çalışıyor.
- Agency bağlantı bölümü ve health kartları için ek `data-testid` kapsaması tamamlandı; agency bağlantı formu artık daha güçlü testlenebilir durumda.
- `Otellerim`/agency hotels akışı agency kullanıcı ile yeniden smoke test edildi; 7 otel kartı yüklendi ve beklenen alanlar doğrulandı.
- Backend smoke testlerinde `config`, `status`, `connections`, `sync/{hotel_id}` ve `agency/hotels` endpointleri geçti; Google credential hâlâ eksik olduğundan canlı sync yerine graceful `not_configured` davranışı beklenen şekilde sürüyor.

## Son Uygulama Güncellemesi — 2026-03-10 Bulk Connection Sprint
- Admin Portfolio Sync içine **Toplu Bağlantı** akışı eklendi; 300+ otel bağlantısını tek seferde kurmak için ayrı modal hazırlandı.
- Aynı bulk akış agency-specific bağlantı alanına da eklendi; böylece otel×acenta bazlı toplu sheet bağlantısı kurulabiliyor.
- Desteklenen giriş yöntemleri: **CSV/XLSX yükleme**, **tablo yapıştırma**, **master Google Sheet önizleme**.
- Bulk akışta kullanıcı tercihi doğrultusunda **önizleme + doğrulama + sonra kaydet** modeli uygulandı.
- Yeni backend endpointleri: `bulk-template/{scope}`, `bulk/preview-upload`, `bulk/preview-text`, `bulk/preview-master-sheet`, `bulk/execute`.
- CSV parser semicolon / comma / tab delimiter için güçlendirildi; Türkçe locale export'larında daha dayanıklı hale getirildi.
- Test sonucu: Iteration 48 raporunda bulk hotel + bulk agency akışı, template indirme, upload/paste preview, execute ve credential yokken graceful master-sheet davranışı geçti.

## Son Bakım Güncellemesi — 2026-03-10 Lint Fix
- Backend Ruff lint hataları temizlendi: kullanılmayan import kaldırıldı ve eksik EOF newline sorunları düzeltildi.
- `ruff check app` yeniden çalıştırıldı ve temiz geçti.
- Hızlı smoke test sonucu: admin login, `/api/admin/sheets/config`, `/api/admin/sheets/bulk-template/hotel` ve admin Portfolio Sync sayfası başarılı çalıştı.

## Kalan Öncelikli İşler
- P0: Kullanıcıdan gerçek Google Service Account JSON alıp canlı doğrulama ve gerçek sync smoke test yapmak.
- P1: Zamanlanmış otomatik sync davranışını gerçek credential ile doğrulamak ve gerekiyorsa UI'daki interval beklentisiyle birebir hizalamak.
- P1: Bulk master sheet akışını gerçek Google credential ile canlı sheet üzerinden smoke test etmek.
- P1: Sheet'ten gelen rezervasyonların rezervasyon listesi / durum yaşam döngüsü görünürlüğünü güçlendirmek.
- P2: Önceki fork'tan kalan diğer UI doğrulamalarını topluca gözden geçirmek.

## Doküman Ayrımı
- Bu dosya statik ürün bağlamını taşır
- Detaylı teslim geçmişi için `CHANGELOG.md`
- Kalan ve öncelikli işler için `ROADMAP.md`