# PRD — Acenta Master Travel SaaS

## Orijinal Problem Tanımı
Kullanıcı, mevcut çok kiracılı (multi-tenant) seyahat/acenta SaaS platformunun enterprise seviyede denetlenmesini, refactor edilmesini ve gelir modeline uygun şekilde üretime hazır hale getirilmesini istedi.

## Ürün Hedefi
- Acentalar için satılabilir, güvenli ve ölçeklenebilir bir SaaS işletim sistemi oluşturmak
- B2B operasyon, rezervasyon, CRM, raporlama, finans ve entegrasyon modüllerini tek platformda toplamak
- Çok kiracılı mimaride tenant izolasyonu, güvenli auth/session ve versiyonlanmış API standardını korumak
- Planlama, yetkilendirme, limit ve kullanım ölçümü üzerinden gerçek bir paket/fiyatlandırma modeli açmak

## Çekirdek Kullanıcılar
- **Super Admin / Admin:** platform yönetimi, tenant yönetimi, planlama, audit, operasyon
- **Agency Admin / Agency Agent:** rezervasyon, B2B işlemler, CRM, raporlar
- **Hotel Admin / Hotel Staff:** otel operasyonları, envanter, entegrasyon, müsaitlik

## Temel Ürün Gereksinimleri
1. Güvenli web auth ve session yönetimi
2. Tenant-aware backend erişim modeli
3. `/api/v1` namespace standardizasyonu ve compat dönemi
4. Paketlenebilir entitlement sistemi:
   - tenant hangi planda?
   - hangi modülleri kullanabilir?
   - hangi limit/allowance’lara sahip?
5. Kullanım ölçümü ve sonrasında faturalama/limit enforcement
6. Admin araçları ile operasyonel görünürlük

## Güncel Mimari
- **Frontend:** React + CRA + Tailwind + shadcn/ui
- **Backend:** FastAPI
- **Veritabanı:** MongoDB
- **Auth:** JWT + cookie compat + session modeli
- **Preview routing:** frontend `/`, backend `/api/*`

## Kritik Teknik Guardrail’ler
- Frontend tüm API çağrılarında `process.env.REACT_APP_BACKEND_URL` tabanını kullanır
- Backend Mongo bağlantısını sadece `MONGO_URL` ve `DB_NAME` üzerinden kurar
- Backend yanıtlarında Mongo `_id` / `ObjectId` sızıntısı yapılmaz
- Tenant erişimi middleware + request context ile korunur
- Web auth kaynağı cookie compat flow’dur; legacy bearer yalnızca geçiş/uyumluluk içindir
- Preview-only testler, preview URL yapılandırılmadığında güvenli şekilde skip olmalıdır; collection-time hard failure üretmemelidir
- Local preview/test Mongo ortamları, orphan `agentis_test_*` veritabanlarını otomatik temizlemelidir; production Atlas verisine asla dokunulmamalıdır

## Monetizasyon Yönü
Platform artık sadece teknik hardening değil, doğrudan gelir modeline hizmet eden paketleme katmanına öncelik veriyor.

### Entitlement Projection Engine V1
- `starter`, `pro`, `enterprise` plan kataloğu
- Her plan için:
  - özellik/modül listesi
  - operasyon limitleri
  - usage allowance alanları
- Tenant bazında kanonik projection snapshot (`tenant_entitlements`)
- Admin ekranı ve public pricing sayfası aynı entitlement kaynağından beslenir

### Usage Metering Foundation
- Kanonik usage metric sabitleri tanımlandı
- Event ledger + günlük aggregate birlikte kullanılacak temel yapı kuruldu
- `reservation.created` için ilk gerçek business flow instrumentation teslim edildi
- Guardrail: yalnız yeni create anı sayılır; status update / cancel bu aşamada sayılmaz

### Usage Metering PR-UM3
- `report.generated` gerçek PDF rapor üretim anında meterlanır
- `export.generated` yalnız gerçek CSV/ZIP/stream output üretiminde meterlanır; tekrar indirme sayılmaz
- `integration.call` Google Sheets provider/client katmanında gerçek dış servis çağrısı yapıldığında meterlanacak şekilde hazırlandı

### Usage Visibility PR-UM4
- Tenant için `GET /api/tenant/usage-summary` aktif
- Admin için `GET /api/admin/billing/tenants/{tenant_id}/usage` trend verisiyle genişletildi
- Tenant dashboard’da mini usage kartı ve ayrı `/app/usage` sayfası aktif
- Admin tenant features ekranında `Usage Overview` kartı ve 30 günlük trend görünürlüğü aktif

### Soft Quota Warning PR-UM5
- 70% / 85% / 100% eşiklerinde `warning` / `critical` / `limit_reached` seviyeleri üretilir
- Tenant dashboard ve `/app/usage` sayfasında warning mikro copy + upgrade CTA gösterilir
- Trial tenant’lar için kullanım oranına göre plan önerisi (`Starter` / `Pro` / `Enterprise`) üretilir
- Admin usage görünümü read-only kalır; CTA göstermez
- CTA etiketi `Planları Görüntüle` olarak sabitlendi; hedef rota `/pricing`
- Cookie-compat auth bootstrap akışında `/api/auth/me` artık `tenant_id` döner; frontend tenant bağlamını korur
- Trial önerisi rezervasyon kullanım oranı odaklı çalışır; %70 demo senaryosunda `Pro Plan` önerilir

### Trial Expiry & Demo-Filled Onboarding
- Trial süresi dolan kullanıcılar için `/app` içinde tam sayfa bloklayıcı conversion ekranı aktif
- Ekran metni: `Deneme süreniz sona erdi` + `Tüm verileriniz korunuyor`; her plan için `Plan Seç` CTA’sı `/pricing` sayfasına gider
- Trial durumu kontrolü düzeltildi; artık non-trial kullanıcılar yanlışlıkla expired görünmez
- Yeni Trial signup hesapları signup tamamlanır tamamlanmaz otomatik demo veri ile beslenir
- Otomatik demo seed kapsamı: 20 müşteri, 30 rezervasyon, 5 tur, 5 otel, 5 destek ürünü

### Stripe Checkout Monetization Flow
- Starter ve Pro planları için Stripe test-mode checkout akışı aktif
- `/pricing` sayfasında aylık / yıllık toggle eklendi:
  - Starter: ₺990 / ay, ₺9.900 / yıl
  - Pro: ₺2.490 / ay, ₺24.900 / yıl
- Enterprise checkout dışı bırakıldı; CTA `İletişime Geç` akışında kalır
- Başarılı ödeme yönlendirme rotası `/payment-success` olarak standartlaştırıldı; `/billing/success` backward-compatible alias olarak korunur
- `/payment-success` ekranı artık aktivasyon odaklı onboarding checklist içerir; role göre güvenli dashboard CTA ve yetkili kullanıcılara `İlk Rezervasyonu Oluştur` CTA gösterilir
- Backend endpoint’leri eklendi:
  - `POST /api/billing/create-checkout`
  - `GET /api/billing/checkout-status/{session_id}`
  - `POST /api/webhook/stripe`
- Yeni `payment_transactions` koleksiyonu checkout oturumlarını ve fulfillment durumunu takip eder
- Başarılı ödeme sonrası:
  - `subscriptions`, `billing_subscriptions`, `tenant_capabilities` güncellenir
  - entitlement/projection planı yenilenir
  - kullanıcı `/billing/success` sayfasından `/app` içine döner
- Not: mevcut entegrasyon Stripe test-mode checkout üzerinden plan aktivasyonu yapar; tam recurring subscription lifecycle / yenileme yönetimi ayrı bir P1 iyileştirme olarak ele alınacaktır

### Pricing & Demo Sales Surface
- Public `/pricing` sayfası satış odaklı olarak yeniden kurgulandı; Türkçe satış copy, net plan kartları ve sosyal kanıt bloğu ile finalize edildi
- Public `/demo` sayfası funnel başlangıcı olarak finalize edildi; `Hero -> Problem -> Çözüm -> CTA` yapısı canlı
- Public `/signup` akışı Trial-first olacak şekilde güncellendi ve CTA’lar `/pricing` + `/demo` üzerinden buna bağlandı
- `/api/onboarding/plans` plan kataloğu gerçek fiyat ve limitlerle hizalı; frontend tarafında API fallback kataloğu da eklendi

#### Canlı Fiyat Matrisi
- **Trial:** 14 gün, 100 rezervasyon, 2 kullanıcı, tüm çekirdek özellikler açık
- **Starter:** ₺990 / ay, 100 rezervasyon, 3 kullanıcı
- **Pro:** ₺2.490 / ay, 500 rezervasyon, 10 kullanıcı
- **Enterprise:** ₺6.990 / ay, sınırsız rezervasyon / kullanıcı

## Test Kimlik Bilgileri
| Portal | Email | Password | Rol |
|---|---|---|---|
| Admin | admin@acenta.test | admin123 | Super Admin |
| B2B | agent@acenta.test | agent123 | Agency Admin |

## Referans Ana Dosyalar
- `backend/app/services/entitlement_service.py`
- `backend/app/routers/admin_tenant_features.py`
- `backend/app/routers/tenant_features.py`
- `backend/app/routers/onboarding.py`
- `backend/seed_demo_data.py`
- `backend/app/services/demo_seed_service.py`
- `frontend/src/pages/admin/AdminTenantFeaturesPage.jsx`
- `frontend/src/components/admin/TenantEntitlementOverview.jsx`
- `frontend/src/pages/public/PricingPage.jsx`

## Son Eklenen Backend Yardımcıları
- Demo tenant / agency satış sunumu için idempotent demo seed utility eklendi
- Script hedef veri seti üretir:
  - 1 demo agency
  - 1 admin kullanıcı
  - 5 tur
  - 5 otel
  - 20 müşteri
  - 30 rezervasyon
  - 10 availability kaydı
- Script yalnız hedef demo tenant kapsamını temizleyen `--reset` desteği sunar

## Aktif Monetizasyon Durumu
- Entitlement projection katmanı aktif
- Usage metering için ilk canlı iş metriği aktif: `reservation.created`
- PR-UM3 kapsamı aktif:
  - `report.generated` → match-risk executive PDF
  - `export.generated` → sales summary CSV, tenant ZIP export, audit CSV export
  - `integration.call` → Google Sheets provider/client çağrı katmanı
- PR-UM4 kapsamı aktif:
  - tenant usage summary + 30 gün trend
  - admin usage raw görünümü + trend
  - dashboard mini usage kartı
  - detay usage sayfası
- PR-UM5 kapsamı aktif:
  - soft quota warning seviyeleri
  - dashboard + usage page upgrade CTA
  - trial conversion recommendation

## Son Uygulama Notu — 2026-03-08
- PR-UM5 tamamlandı; kullanıcı manuel doğrulaması daha sonra yapılabilir, fakat önce go-to-market yüzeyi tamamlandı
- Public acquisition funnel finalize edildi:
  - `/pricing` başlığı `Acenteniz için doğru planı seçin` olarak güncellendi
  - Planlar: Starter ₺990, Pro ₺2.490, Enterprise ₺6.990; her kart kullanıcı tarafından verilen net bullet listeleri gösteriyor
  - Kritik sosyal kanıt bloğu eklendi: `Turizm acenteleri Syroce ile operasyon süreçlerini %40 daha hızlı yönetiyor.`
  - `/demo` sayfası kullanıcı isteğine göre `Hero -> Problem -> Çözüm -> CTA` yapısında finalize edildi
- Trial conversion akışı aktif:
  - `/pricing` ve `/demo` CTA’ları `/signup?plan=trial` akışına bağlandı
  - Plan bazlı CTA’lar `selectedPlan` query param ile signup ekranına yönlendiriyor
- Yeni conversion / retention iyileştirmeleri tamamlandı:
  - Trial expiry full-screen gate aktif; expired hesaplar `/app` içinde bloklanıyor ve `/pricing` yönüne itiliyor
  - `/pricing` sayfasına `Problem`, `Çözüm` ve `ROI` blokları eklendi
  - Trial signup sonrası demo veri otomatik seed ediliyor; ilk çalışma alanı boş gelmiyor
  - Stripe checkout tabanlı ödeme akışı Starter/Pro için canlı test edildi
  - `/billing/success` sayfası eklendi; ödeme sonrası polling + aktivasyon görünürlüğü sağlar
- Doğrulama tamamlandı:
  - Manuel smoke test: preview üzerinde `/pricing -> /demo` geçişi doğrulandı
  - Testing agent raporu: `/app/test_reports/iteration_25.json` → frontend %100 geçti
  - Testing agent raporu: `/app/test_reports/iteration_26.json` → trial expiry + signup seed + pricing blokları geçti
  - Gerçek Stripe test kartı (`4242 4242 4242 4242`) ile checkout tamamlandı; plan aktivasyonu doğrulandı
  - Testing agent raporu: `/app/test_reports/iteration_27.json` → Stripe checkout + billing success + backend activation geçti

## Son Uygulama Notu — 2026-03-08 (Fork doğrulama + route standardizasyonu)
- Stripe checkout success redirect rotası `/payment-success` olarak hizalandı; eski `/billing/success` route’u korunarak geriye dönük uyumluluk sağlandı
- Preview üzerinde `/pricing` smoke testi tekrar yapıldı; yıllık toggle ve fiyat kartları çalışıyor
- Testing agent raporu: `/app/test_reports/iteration_28.json` → `/payment-success`, Enterprise CTA guardrail, webhook ve fulfillment idempotency, paid user plan state doğrulandı
- Frontend testing agent doğrulaması: `/pricing`, `/payment-success`, `/billing/success` ekranları geçti
- Backend deep testing doğrulaması: checkout/create-checkout, checkout-status, webhook ve duplicate event koruması geçti

## Son Uygulama Notu — 2026-03-08 (Payment success aktivasyon UX)
- `/payment-success` success state satış mesajından aktivasyon akışına çevrildi
- Yeni içerik:
  - başlık: `Ödemeniz başarıyla tamamlandı`
  - alt metin: ilk rezervasyonu oluşturmaya yönlendiren aktivasyon copy
  - 4 maddelik statik onboarding checklist
  - birincil CTA: role-aware `Panele Git`
  - ikincil CTA: yalnız rezervasyon yetkili rollerde `İlk Rezervasyonu Oluştur`
- Güvenli fallback kuralı uygulandı: role resolve edilemezse dashboard CTA `/app` hedefine düşer
- Frontend doğrulama tamamlandı: success state ve boş session error state birlikte test edildi

## Öncelikli Sonraki Adımlar
- **P1:** Trial signup akışını satış funnel’ı ile daha sıkı bağlama (ilk giriş sonrası onboarding/paket yönlendirme polish)
- **P1:** Stripe checkout akışını gerçek recurring subscription lifecycle / renewal / cancel / downgrade yönetimine yükseltme
- **P1:** Hard quota enforcement
- **P2:** Admin demo agency oluşturma butonu
- **P2:** Admin endpoint cleanup (`/api/partner-graph/notifications/summary`, `/api/tenant/features`, `/api/tenant/quota-status`)

## Bu Dosyanın Kapsamı
Bu PRD dosyası yalnızca statik ürün bağlamını taşır.
Detaylı uygulama geçmişi için `CHANGELOG.md`, kalan işler için `ROADMAP.md` kullanılmalıdır.