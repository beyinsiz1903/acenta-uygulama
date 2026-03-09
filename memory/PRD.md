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
- Authenticated app içinde `/app/settings/billing` yönetim yüzeyi eklendi:
  - mevcut plan
  - sonraki yenileme tarihi
  - aylık / yıllık durum
  - plan değiştir
  - dönem sonunda iptal
  - Stripe billing portal ile ödeme yöntemi güncelle
  - ödeme problemi uyarı alanı
- Subscription lifecycle kuralları uygulandı:
  - upgrade hemen aktif olur
  - downgrade bir sonraki döneme planlanır
  - cancel yalnız dönem sonunda uygulanır
  - Stripe portal dönüşü `/app/settings/billing` sayfasına döner
- Backend endpoint’leri eklendi:
  - `POST /api/billing/create-checkout`
  - `GET /api/billing/checkout-status/{session_id}`
  - `POST /api/webhook/stripe`
  - `GET /api/billing/subscription`
  - `POST /api/billing/customer-portal`
  - `POST /api/billing/change-plan`
  - `POST /api/billing/cancel-subscription`
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

## Son Uygulama Notu — 2026-03-08 (Subscription lifecycle + billing management)
- Checkout akışı subscription-mode Stripe Checkout olarak yükseltildi; yeni başarılı ödemeler gerçek `cus_` ve `sub_` kayıtlarıyla managed subscription state üretir
- `/app/settings/billing` sayfası teslim edildi:
  - summary kartları
  - managed vs legacy subscription guardrail ayrımı
  - plan değiştirme yüzeyi
  - cancel pending / scheduled downgrade banner’ları
  - Stripe billing portal ödeme yöntemi güncelleme akışı
- Onboarding redirect guardrail güncellendi; `/app/settings/*` rotaları onboarding zorlamasından muaf
- Managed flow doğrulandı:
  - expired trial kullanıcı gerçek Stripe test kartı ile başarılı ödeme sonrası managed subscription’a geçti
  - upgrade immediate mesajı doğrulandı: `Yeni planınız hemen aktif oldu`
  - downgrade scheduled mesajı doğrulandı: `Plan değişikliğiniz bir sonraki dönem başlayacak`
  - cancel period-end mesajı doğrulandı: `Aboneliğiniz dönem sonunda sona erecek`
  - Stripe portal round-trip doğrulandı: portal açıldı ve `Return to ...` ile `/app/settings/billing` sayfasına geri dönüldü
- Test kayıtları:
  - `/app/test_reports/iteration_29.json` → billing page + legacy lifecycle guardrails geçti
  - `/app/test_reports/iteration_30.json` → managed lifecycle backend doğrulaması ve manual follow-up adımları kaydedildi
  - managed subscription self-test + browser smoke + portal round-trip tamamlandı

## Son Uygulama Notu — 2026-03-08 (Billing P0 finalize + resiliency fixes)
- `/app/settings/billing` P0 doğrulaması tamamlandı
  - managed abonelik için `Aboneliği İptal Et -> dönem sonunda iptal` akışı doğrulandı
  - yeni `POST /api/billing/reactivate-subscription` endpoint’i ve UI butonu eklendi
  - reactivate sonrası pending banner / buton state’i otomatik temizleniyor
  - sayfa focus/visibility dönüşünde billing verisi yeniden yükleniyor
- Stripe dayanıklılık düzeltmeleri yapıldı
  - stale `sub_*` / `cus_*` kayıtları artık billing overview veya portal çağrısında 500 üretmiyor
  - geçersiz eski provider subscription referansları legacy guardrail state’ine düşürülüyor
  - geçersiz eski provider customer referansları portal açılışında otomatik onarılıyor
  - stale `price_*` katalog kayıtları checkout oluşturulurken otomatik yenileniyor
- Doğrulama ve testler:
  - gerçek Stripe test checkout ile `agent@acenta.test` hesabı Trial -> paid Starter managed subscription state’ine geçirildi
  - curl self-test: subscription, cancel, customer-portal, reactivate akışları geçti
  - browser self-test: billing ekranı, cancel dialog, pending state, reactivate, Stripe portal redirect geçti
  - testing agent raporu: `/app/test_reports/iteration_31.json` → backend %100 / frontend %100 billing lifecycle geçti

## Son Uygulama Notu — 2026-03-08 (Backend lint/install stabilizasyonu)
- `backend/requirements.txt` kurulum dayanıklılığı güncellendi
  - `emergentintegrations` çözümlemesi için CloudFront extra index satırı eklendi
  - `typer==0.21.0` → `typer==0.24.0` yükseltildi; `typer-slim==0.24.0` ile resolver çakışması giderildi
- Doğrulama:
  - `PIP_CONFIG_FILE=/dev/null python -m pip install --dry-run -r requirements.txt` başarılı
  - aktif backend sanal ortamında `typer==0.24.0` kurulumu tamamlandı

## Son Uygulama Notu — 2026-03-08 (CI lint + exit gate hardening)
- Backend tarafında trailing newline eksikleri temizlendi; screenshot’taki `W292 / No newline at end of file` sınıfı hatalar giderildi
- Preview tabanlı testlerde güvenli skip standardı genişletildi
  - `test_usage_metering_pr_um3.py` ve `test_mobile_bff_preview_api.py` artık preview URL yoksa collection-time crash yerine güvenli skip davranışı kullanıyor
  - ek olarak bazı legacy/manual test dosyaları da hardcoded preview URL yerine `get_preview_base_url_or_skip(...)` ile hizalandı
  - `test_inbox_guardrails.py` içinde pytest collection warning üreten yardımcı sınıf `__test__ = False` ile koleksiyondan çıkarıldı
- Doğrulama:
  - `python` ile backend/app + backend/tests altında tüm `.py` dosyalarında trailing newline kontrolü geçti
  - `mcp_lint_python` ile `/app/backend/app` lint geçti
  - `pytest --collect-only tests/test_usage_metering_pr_um3.py -q` ve `pytest --collect-only tests/test_inbox_guardrails.py -q` hata vermeden tamamlandı

## Son Uygulama Notu — 2026-03-08 (Billing lifecycle lint hotfix)
- `app/routers/billing_lifecycle.py` içindeki kullanılmayan `Request` import’u kaldırıldı
- Doğrulama: ilgili router dosyası için Python lint temiz geçti

## Son Uygulama Notu — 2026-03-09 (Ürün yüzeyi sadeleştirme + modül sınıflandırma)
- Repo, ürün konumlandırması açısından yeniden değerlendirildi: hedef kategori `Travel Agency Operating System`
- Modül çerçevesi netleştirildi:
  - **CORE:** rezervasyon / booking, müşteri & CRM, operasyon görünürlüğü, finans / ödeme / mutabakat, temel raporlama
  - **EXPANSION:** B2B portal, storefront, entegrasyonlar, supplier bağlantıları
  - **ENTERPRISE:** tenant yönetimi, audit/export, governance, white-label, gelişmiş izinler
  - **SECONDARY / PRUNE CANDIDATES:** marketplace, partner graph, advanced campaigns, kompleks raporlama alt yüzeyleri, çeşitli admin araçları
- `frontend/src/components/AppShell.jsx` içindeki ana sidebar sadeleştirildi:
  - **Ana Menü:** Dashboard, Rezervasyonlar, Müşteriler, Finans, Raporlar
  - **Gelişmiş:** Entegrasyonlar, Kampanyalar
  - **Admin / Enterprise:** Tenant yönetimi, Audit, Advanced permissions
- Partner graph giriş yüzeyi genel shell’den gizlendi; yalnızca kullanıcı `/app/partners` içindeyse görünür bırakıldı
- Rol bazlı sade menü doğrulandı:
  - Admin için tüm hedef menü blokları görünür
  - Agency kullanıcı için sadece çekirdek + gelişmiş bloklar görünür; admin/enterprise öğeleri gizli kalır
- Test sonucu:
  - frontend smoke + frontend testing agent geçti
  - backend smoke agent geçti
  - Not: `/api/agency/bookings` ve `/api/agency/settlements` 404 dönüyor; bu issue önceden mevcut, menü sadeleştirme değişikliğinden kaynaklanmıyor

## Son Uygulama Notu — 2026-03-09 (Billing P0 revalidation + lifecycle stabilizasyonu)
- `/app/settings/billing` P0 hattı tekrar önceliklendirildi ve uçtan uca yeniden doğrulandı
- Stripe dayanıklılık düzeltmesi güçlendirildi:
  - `stripe_checkout_service.create_checkout_session(...)` stale / silinmiş Stripe customer referansında artık 500 üretmiyor
  - geçersiz customer referansı temizlenip checkout oluşturma güvenli şekilde yeniden deneniyor
  - `_repair_customer_reference(...)` payment transaction içindeki provider customer / subscription referanslarını da kullanacak şekilde sertleştirildi
- Legacy ve managed state guardrail’leri yeniden doğrulandı:
  - legacy state için `change-plan -> checkout_redirect`, `cancel/reactivate -> 409 guardrail`, portal URL üretimi geçti
  - managed state için `cancel -> pending`, `reactivate -> active`, `upgrade -> immediate`, `downgrade -> scheduled`, portal round-trip geçti
- UI doğrulamaları tamamlandı:
  - Türkçe başlıklar, tarih formatı (`09 Nisan 2026`), durum etiketleri (`Aylık · Aktif`) doğru
  - cancel dialog, pending banner, reactivate butonu, scheduled downgrade banner ve portal dönüşü `/app/settings/billing` üzerinde doğrulandı
- Doğrulama kaynakları:
  - `/app/test_reports/iteration_32.json` → legacy/stale reference + checkout redirect + billing UI geçti
  - self-test + browser smoke → managed lifecycle, portal round-trip, scheduled downgrade banner geçti
  - backend deep validation ve frontend automation validation başarılı tamamlandı
- Güncel test hesap state’i:
  - `agent@acenta.test` artık managed Stripe subscription state’inde (`Pro / monthly / active`)
  - `billing.test.83ce5350@example.com` QA hesabı ile managed lifecycle UI/API tekrar doğrulandı

## Son Uygulama Notu — 2026-03-09 (NewSidebar entegrasyonu + sade route temizliği)
- Ürün yüzeyi demo/onboarding odağıyla yeniden sadeleştirildi:
  - yeni `NewSidebar.jsx` bileşeni çıkarıldı ve `AppShell` içine entegre edildi
  - görünür ana navigasyon yalnız çekirdek menüye indirildi: `Dashboard`, `Rezervasyonlar`, `Müşteriler`, `Finans`, `Raporlar`
  - `EXPANSION` ve `ENTERPRISE` yüzeyleri route katalogunda korunup görünür sidebar’dan çıkarıldı
- Hesap yardımcı erişimleri korundu:
  - sidebar footer’da `Faturalama` ve `Ayarlar` linkleri bırakıldı
  - `redirectByRole` agency/admin kullanıcıları için `/app` iniş noktasına hizalandı; login sonrası kullanıcı artık `/app/partners` içine düşmüyor
- Route cleanup tamamlandı:
  - `App.js` içinde admin / agency / hotel index redirectleri eklendi
  - legacy `/app/customers` rotası çekirdek CRM yoluna yönlendirildi
- Agency 404 hattı giderildi:
  - backend `router_registry.py` içine `agency hotels`, `agency bookings`, `agency settlements` ve `hotel settlements` router include’ları eklendi
  - `GET /api/agency/bookings`, `GET /api/agency/settlements`, `GET /api/agency/hotels` artık 200 dönüyor
- Yan etki olarak ortaya çıkan frontend crash de düzeltildi:
  - `BookingDetailDrawer.jsx` içindeki `loadEvents` TDZ hatası giderildi; rezervasyon listesi artık drawer açılışında çökme üretmiyor
- Doğrulama:
  - curl self-test: agency bookings / settlements / hotels endpoint’leri geçti
  - browser smoke: agency login → `/app`, simplified sidebar, bookings ve settlements sayfaları geçti
  - testing agent raporu: `/app/test_reports/iteration_33.json` → backend %100 / frontend %100 geçti

## Son Uygulama Notu — 2026-03-09 (Agency endpoint logic finalize)
- P0 agency endpoint hattı gerçek veri mantığıyla tamamlandı
  - `GET /api/agency/bookings` artık agency kapsamındaki booking kayıtlarını normalize ederek UI’nin beklediği alanlarla döndürüyor
  - sparse / legacy kayıtlar için `hotel_name`, `stay`, `guest`, `rate_snapshot`, `status_tr/en`, `total_amount` gibi alanlar türetiliyor
  - `GET /api/agency/bookings/{booking_id}` artık hem string ID hem Mongo `ObjectId` tabanlı kayıtları açabiliyor
- `GET /api/agency/settlements` agency finans kayıtları yoksa booking’lerden türetilmiş settlement satırları üretir hale getirildi
  - önce gerçek `booking_financial_entries` okunuyor
  - eksik durumda agency booking kayıtlarından aylık settlement görünümü derive ediliyor
  - response içinde `hotel_name`, `booking_id`, `settlement_status`, `source_status`, `derived_from_booking` alanları korunuyor
- Doğrulama:
  - local backend self-test: login, bookings list/detail, settlements `2026-03` ve `2026-02` geçti
  - backend deep testing: agency bookings normalize alanları, ObjectId detay açılışı ve derived settlements doğrulandı
  - frontend smoke: preview `/pricing` yükleniyor, blank/crash yok

## Son Uygulama Notu — 2026-03-09 (Billing history timeline teslimi)
- `/api/billing/history` endpoint’i eklendi
  - kaynak: `audit_logs` içindeki `scope=billing` kayıtları
  - kullanıcı dostu timeline alanları dönüyor: `id`, `title`, `description`, `occurred_at`, `actor_label`, `actor_type`, `tone`
  - desteklenen olaylar: checkout completion, immediate/scheduled plan change, cancel/reactivate, invoice paid, payment failed, subscription canceled
- `/app/settings/billing` içine yeni `Faturalama Geçmişi` kartı eklendi
  - loading / error / empty / populated state’leri hazır
  - manuel `Geçmişi Yenile` aksiyonu eklendi
  - mevcut billing overview, yönetim kartı ve plan değiştirme kartı korunarak regression’sız entegre edildi
- Doğrulama:
  - curl self-test: `GET /api/billing/subscription` ve `GET /api/billing/history` geçti
  - browser smoke: preview üzerinde billing page + history card/list doğrulandı
  - testing agent raporu: `/app/test_reports/iteration_34.json` → backend %100 / frontend %100 geçti

## Son Uygulama Notu — 2026-03-09 (Payment failure lifecycle hardening)
- Stripe billing lifecycle hattı payment failure görünürlüğü için sertleştirildi
  - ana `/api/webhook/stripe` akışında `invoice.paid`, `invoice.payment_failed` ve `customer.subscription.deleted` olayları artık ortak helper’larla işleniyor
  - yeni helper’lar: `mark_invoice_paid`, `mark_payment_failed`, `mark_subscription_canceled`
  - payment failure state temizleme / kurma kuralları hizalandı: `grace_period_until`, `last_payment_failed_at`, `last_payment_failed_amount`, `invoice_hosted_url`, `invoice_pdf_url`
- `GET /api/billing/subscription` payment issue payload’ı zenginleştirildi
  - yeni alanlar: `severity`, `title`, `grace_period_until`, `last_failed_at`, `last_failed_amount`, `last_failed_amount_label`, `invoice_hosted_url`, `invoice_pdf_url`
  - başarılı tahsilat sonrası payment issue alanları temizleniyor; canceled state scheduled/failure artıklarını da siliyor
- Billing UI iyileştirildi
  - yeni `BillingPaymentIssueBanner` bileşeni eklendi
  - banner artık durum seviyesi, başarısız tutar, son deneme zamanı, son gün ve varsa direkt fatura linkini gösteriyor
  - `SettingsBillingPage` içinde entegre edildi; canlı payment issue yoksa görünmemesi korunuyor
- Doğrulama:
  - backend self-test: temp tenant ile `mark_payment_failed -> get_billing_overview -> mark_invoice_paid` lifecycle doğrulandı
  - browser smoke: mocked subscription response ile payment issue banner renderı doğrulandı
  - testing agent raporu: `/app/test_reports/iteration_35.json` → backend %100 / frontend %100 geçti
  - frontend testing subagent + backend deep testing subagent no-regression geçti

## Son Uygulama Notu — 2026-03-09 (Frontend auth redirect refactor)
- Frontend auth yönlendirme/state mantığı merkezi helper’a taşındı
  - yeni `frontend/src/lib/authRedirect.js` eklendi
  - `acenta_post_login_redirect` ve `acenta_session_expired` sessionStorage anahtarları artık tek yerden okunup yazılıyor
  - `RequireAuth`, `LoginPage`, `B2BLoginPage` ve `lib/api` bu ortak helper ile hizalandı
- Kritik regresyon düzeltildi
  - login submit sonrası redirect ile bootstrap effect’in çakışmasından doğan double-redirect bug’ı giderildi
  - kullanıcı artık session-expired sonrası hedef sayfaya dönünce `/app` içine ikinci kez sıçramıyor
- Doğrulama:
  - frontend automation: expired session banner, post-login return-to `/app/settings/billing`, sessionStorage cleanup ve normal login akışı geçti
  - backend deep validation: `POST /api/auth/login`, `GET /api/auth/me`, `GET /api/billing/subscription`, `GET /api/billing/history` geçti; regression yok

## Son Uygulama Notu — 2026-03-09 (Yıllık fiyatlandırma E2E revalidation)
- Yıllık fiyatlandırma hattı mevcut sade ürün yüzeyi üzerinde yeniden uçtan uca doğrulandı
  - public `/pricing` yıllık toggle: Starter `₺9.900`, Pro `₺24.900`, `2 ay ücretsiz` badge görünürlüğü geçti
  - unauthenticated CTA yönlendirmesi `selectedPlan` parametresi korunarak `/signup` akışına düştü
  - authenticated checkout create/status hattı `interval=yearly` ile tekrar doğrulandı
  - `/app/settings/billing` yıllık toggle, yıllık plan kartları ve badge görünürlüğü regresyonsuz geçti
- Kod değişikliği gerekmedi; mevcut annual pricing implementasyonu stabil bulundu
- Doğrulama:
  - testing agent raporu: `/app/test_reports/iteration_36.json` → backend %100 / frontend %100 annual pricing geçti
  - oluşturulan referans test dosyası: `/app/backend/tests/test_annual_pricing_e2e_iter36.py`

## Son Uygulama Notu — 2026-03-09 (Billing redirect re-smoke + branding request guard)
- Agency kullanıcı için `AppShell` branding yükleme akışı role guard ile sertleştirildi
  - admin olmayan kullanıcılar artık `/api/admin/whitelabel-settings` endpoint’ine istek atmıyor
  - billing/settings gibi agency yüzeylerinde gereksiz 403 console gürültüsü kaldırıldı
- `/app/settings/billing` post-login return-to akışı tekrar doğrulandı
  - direkt korumalı route açılışı → `/login`
  - giriş sonrası hedef sayfaya güvenli dönüş
  - yıllık toggle ve billing summary görünümü regresyonsuz geçti
- Doğrulama:
  - browser smoke + console kontrolü geçti; admin whitelabel request’i agency kullanıcı için artık görünmüyor
  - `auto_frontend_testing_agent` → 6/6 PASS
  - `deep_testing_backend_v2` → auth + billing regression PASS
- Test account durumu:
  - `agent@acenta.test` bu doğrulama turunda `Pro / yearly / active` state’inde teyit edildi

## Son Uygulama Notu — 2026-03-09 (Stripe webhook secret + invoice.paid state fix)
- Stripe billing webhook hattı güvenlik ve state transition açısından tekrar sertleştirildi
  - `backend/.env` içine `STRIPE_WEBHOOK_SECRET=whsec_test` eklendi
  - ana `StripeCheckoutService.handle_webhook(...)` içinde missing-secret guard eklendi; secret yoksa webhook artık fail-fast davranıyor
- `invoice.paid` stale subscription fallback bug’ı düzeltildi
  - daha önce stale / senkronize edilemeyen provider subscription referansında payment issue alanları temizlenmesine rağmen status yanlışlıkla `past_due` kalabiliyordu
  - artık `invoice.paid` sonrası durum güvenli şekilde `active`’a normalize ediliyor ve payment issue alanları temizleniyor
- Doğrulama:
  - imzalı mock webhook self-test: `invoice.payment_failed`, `customer.subscription.deleted`, `invoice.paid` → hepsi preview backend üzerinde geçti
  - auth smoke: `POST /api/auth/login` + `GET /api/billing/subscription` geçti, `payment_issue` payload’ı doğrulandı
  - `deep_testing_backend_v2` doğrulaması: Stripe billing webhook akışları PASS
  - `auto_frontend_testing_agent` smoke: `/app/settings/billing` render ve no-regression PASS

## Son Uygulama Notu — 2026-03-09 (Hard quota enforcement)
- Monetizasyon katmanı soft warning’den hard enforcement seviyesine taşındı
  - yeni `backend/app/services/quota_enforcement_service.py` eklendi
  - `reservation.created`, `report.generated`, `export.generated` metrikleri için guard snapshot + `quota_exceeded` AppError zarfı standartlaştırıldı
  - hata detayları artık `metric`, `limit`, `used`, `remaining`, `period`, `plan`, `cta_href=/pricing`, `cta_label=Planları Görüntüle` alanlarını döndürüyor
- Enforcement entegrasyonları tamamlandı
  - rezervasyon oluşturma: `services/reservations.py`
  - tur rezervasyonu: `routers/tours_browse.py`
  - PDF rapor üretimi: `services/report_output_service.py`
  - CSV / ZIP / audit export akışları: `routers/reports.py`, `routers/exports.py`, `routers/enterprise_export.py`, `routers/enterprise_audit.py`
  - usage event sonrası tenant usage/quota cache invalidation eklendi; kullanım kartları daha hızlı güncelleniyor
- Frontend UX hardening
  - `frontend/src/lib/api.js` artık standardize backend error envelope içindeki `error.message` alanını okuyarak kullanıcıya doğru Türkçe mesajı gösterebiliyor
- Doğrulama:
  - pytest: `/app/backend/tests/test_hard_quota_enforcement.py` → 3/3 PASS
  - testing agent raporu: `/app/test_reports/iteration_37.json` → backend unit validation PASS, frontend no-regression PASS, canlı preview smoke rate-limit dışında temiz
  - self-test: preview üzerinde login + `GET /api/billing/subscription` 200, `/app/usage` smoke PASS
  - `auto_frontend_testing_agent` → `/app/usage` + `/app/settings/billing` regression PASS
  - `deep_testing_backend_v2` → auth, usage-summary, billing subscription, CSV export, admin export ve audit export PASS

## Son Uygulama Notu — 2026-03-09 (Admin tenant panel cleanup)
- Admin tenant yönetim ekranı operasyon ekibi için daha aksiyon odaklı hale getirildi
  - `GET /api/admin/tenants` artık yalnız temel tenant bilgisi değil, aynı zamanda `plan`, `plan_label`, `subscription_status`, `cancel_at_period_end`, `grace_period_until`, `current_period_end`, `lifecycle_stage`, `has_payment_issue` alanlarını döndürüyor
  - response içine yeni `summary` objesi eklendi: `total`, `payment_issue_count`, `trial_count`, `canceling_count`, `active_count`, `by_plan`, `lifecycle`
  - legacy subscription fallback korunarak liste görünümü billing_subscriptions olmayan tenant’larda da güvenli kaldı
- `frontend/src/pages/admin/AdminTenantFeaturesPage.jsx` ekranı sadeleştirildi ve yeniden kurgulandı
  - yeni üst özet kartları: `Toplam tenant`, `Ödeme sorunu`, `Trial`, `İptal sırada`
  - tenant dizini için risk odaklı sıralama eklendi: payment issue → canceling → trial → active
  - filtre chip’leri ve manuel `Yenile` aksiyonu eklendi
  - her tenant satırında plan badge + lifecycle badge + varsa grace date görünürlüğü verildi
  - mevcut sağ panel (`Subscription`, `Usage Overview`, `Tenant Entitlement Overview`) korunarak no-regression entegrasyon yapıldı
- Doğrulama:
  - pytest: `/app/backend/tests/integration/feature_flags/test_admin_tenant_features.py` → 5/5 PASS
  - preview curl smoke: `POST /api/auth/login` + `GET /api/admin/tenants?limit=5` geçti; yeni `summary` ve item alanları doğrulandı
  - browser smoke: admin login → `/app/admin/tenant-features` summary cards + filter bar render PASS
  - `auto_frontend_testing_agent` → admin tenant cleanup akışı PASS
  - `deep_testing_backend_v2` → admin tenant enrichment ve features no-regression PASS

## Son Uygulama Notu — 2026-03-09 (Fork doğrulama takibi)
- Bu forkta kullanıcı onayı öncesi kota görünürlüğü tekrar doğrulandı; ek kod değişikliği yapılmadı
  - `agent@acenta.test` hesabıyla preview login akışı geçti
  - dashboard üzerindeki `Kullanım özeti` kartı ve `/app/usage` sayfası başarıyla açıldı
- Manuel API doğrulaması tamamlandı
  - `GET /api/tenant/usage-summary?days=30` → plan `Pro`, dönem `2026-03`, reservation/report/export metrikleri doğru döndü
  - `GET /api/tenant/quota-status` → quota oranları ve warning alanları beklendiği gibi döndü
  - `GET /api/reports/sales-summary.csv` çağrısı sonrası `export.generated` sayacı 14 → 15 artarak hard quota metering zincirinin canlı çalıştığı tekrar doğrulandı

## Son Uygulama Notu — 2026-03-09 (Admin all-users doğrulaması)
- Super admin kullanıcı yönetimi akışı canlı preview üzerinde backend ağırlıklı olarak doğrulandı; ek kod değişikliği gerekmedi
  - `GET /api/admin/all-users` listeleme geçti
  - `POST /api/admin/all-users` ile kullanıcı oluşturma geçti
  - `PUT /api/admin/all-users/{user_id}` ile ad / rol / durum güncelleme geçti
  - `DELETE /api/admin/all-users/{user_id}` ile silme ve sonrasında listeden düşmesi geçti
- Frontend tarafı için `/app/admin/all-users` smoke doğrulaması alındı; ekran render ve veri görünürlüğü doğru
  - testing agent raporu: `/app/test_reports/iteration_38.json`
  - backend sonucu: `16/16 PASS`
  - hard quota readiness regresyonu: `GET /api/tenant/usage-summary` ve `GET /api/billing/subscription` PASS
- Not: bağımsız Playwright login doğrulaması aynı turda preview rate limit (`429 / 300s cooldown`) nedeniyle tam koşulamadı; bu uygulama kodunda fonksiyonel hata olarak raporlanmadı

## Son Uygulama Notu — 2026-03-09 (Agency reports + global search + admin plan confirmation)
- Placeholder olarak kalan arama/rapor yüzeyi gerçek iş mantığıyla güçlendirildi
  - yeni `GET /api/search` federated operasyon araması eklendi; `customers`, `bookings`, `hotels`, `tours` bölümlerini döner
  - agency kullanıcılarında sonuçlar otomatik `agency` scope’a daralır; admin tarafında organization-wide çalışır
  - mevcut `POST /api/agency/search` availability akışı korunarak cache/PMS quote davranışı bozulmadı
- Yeni `GET/POST /api/reports/generate` operasyon raporu eklendi
  - payload içinde `period`, `kpis`, `status_breakdown`, `daily_revenue`, `top_hotels`, `payment_health`, `source_breakdown`, `recent_bookings` alanları dönüyor
  - `report.generated` hard quota guard + usage metering bağlı çalışıyor
  - tenant context olmayan agency oturumlarında yeni fallback (`_resolve_report_tenant_id`) ile `tenant_context_missing` hatası giderildi
  - `GET /api/reports/sales-summary` artık `days` filtresini gerçekten uygular; CSV export da aynı filtreyle hizalandı
- Frontend reports deneyimi yeniden kurgulandı (`/app/reports`)
  - üstte gün filtreleri: `Son 7 / 30 / 90 gün`
  - yeni `Hızlı operasyon araması` kartı canlı `/api/search` sonucunu render ediyor
  - yeni `Operasyon raporu üret` kartı manuel rapor üretimi, KPI kartları ve breakdown blokları gösteriyor
  - mevcut satış özeti ve CSV export yüzeyi korunarak no-regression entegre edildi
- Admin tenant management UX güçlendirildi
  - subscription iptali için `subscription-cancel-confirm-dialog` eklendi; `window.confirm` kaldırıldı
  - plan değişikliği için `PlanChangeImpactCard` + `plan-change-confirm-dialog` eklendi
  - plan geçişinde kullanıcı/adet/rapor kotası farkları kaydetmeden önce görünür hale geldi
- Doğrulama:
  - self-test: agency login ile `GET /api/agency/hotels`, `GET /api/agency/bookings`, `GET /api/agency/settlements?month=2026-03`, `GET /api/search?q=demo`, `GET /api/reports/generate?days=30` geçti
  - browser smoke: `/app/reports` üzerinde global search + operations report generation görünürlüğü geçti
  - `auto_frontend_testing_agent` raporu: tenant fallback bug’ı yakaladı; ardından fix uygulandı
  - `deep_testing_backend_v2` → 11/11 PASS, tenant fallback fix doğrulandı
  - testing agent raporu: `/app/test_reports/iteration_39.json` → backend %100 / frontend %100 PASS

## Son Uygulama Notu — 2026-03-09 (P0 email notification queue + P1 doğrulama)
- P0 email notification pipeline teslim edildi
  - yeni `backend/app/services/notification_email_service.py` eklendi
  - `stripe_checkout_service.mark_payment_failed(...)` artık `billing.payment_failed` outbox job oluşturuyor
  - `usage_service.track_usage_event(...)` artık 70% / 85% / 100% eşik geçişlerinde `usage.quota_warning`, `usage.quota_critical`, `usage.quota_limit_reached` outbox job üretiyor
- Email outbox dayanıklılığı güçlendirildi
  - `enqueue_generic_email(...)` artık `tenant_id`, `metadata`, `dedupe_key` destekliyor
  - `email_outbox` için `dedupe_key` unique+sparse index eklendi
  - provider konfigürasyonu yoksa worker artık job’ı yanlışlıkla `sent` işaretlemek yerine `skipped` durumuna alıyor
- P1 search / reports hattı yeniden doğrulandı; ek geliştirme gerektirmeden çalışıyor
  - preview self-test: `GET /api/search?q=demo`, `GET /api/reports/generate?days=30`, `GET /api/reports/sales-summary.csv?days=7` geçti
  - testing agent raporu: `/app/test_reports/iteration_40.json` → email queue + skipped behavior PASS, search/reports no-regression PASS
  - frontend smoke: `/pricing` ve `/app/reports` blank/crash olmadan geçti
- Not:
  - **MOCKED / DEGRADED:** canlı dış email teslimatı bu run’da aktif değil; provider credential verilmediği için doğrulanan kapsam `email_outbox` job creation + `skipped` davranışıdır

## Son Uygulama Notu — 2026-03-09 (Syroce landing page dönüşüm yüzeyi)
- Public `/` ana sayfası yüksek dönüşüm odaklı Syroce landing page olarak yeniden tasarlandı
  - bölümler: Hero, Trust Bar, Problem, Çözüm, Product Preview, How It Works, ROI, B2B Network, Pricing, Final CTA, Footer
  - CTA akışı kullanıcı tercihiyle hizalandı: Trial → `/signup?plan=trial`, Demo → `/login`
  - Starter / Pro / Enterprise fiyat kartları landing içine taşındı; aylık / yıllık toggle eklendi
- UI yaklaşımı
  - dashboard / rezervasyon / CRM / finans önizlemeleri gerçek ekran görüntüsü yerine CSS + HTML mockup olarak üretildi
  - yeni yardımcı bileşenler: `frontend/src/components/landing/LandingDashboardMockup.jsx`, `LandingSectionHeading.jsx`
  - `frontend/src/index.css` içinde marka renkleri `#2563EB / #0EA5E9 / #F8FAFC` yönüne hizalandı, smooth scroll ve landing texture utility eklendi
- İstenen tasarım çıktıları ürün içine ve dokümana işlendi
  - **Wireframe akışı:** Hero → Trust → Problem → Solution → Product Preview → How It Works → ROI → Network → Pricing → Final CTA
  - **Section UX mantığı:** üst katman problem farkındalığı + güven, orta katman ürün değeri + ekran önizlemesi, alt katman ROI + pricing + conversion kapanışı
  - **Mobil yaklaşım:** hero tek kolona iner, mockup kartları stack olur, pricing kartları tek sütuna düşer, mobil menü CTA odaklı kalır
  - **Dashboard mockup önerisi:** KPI satırı + rezervasyon listesi + CRM paneli + finans chart bileşimiyle “tek panel” algısı verilir
  - **Growth funnel:** Instagram → Landing Page → Trial → Onboarding → Subscription
- Doğrulama
  - screenshot smoke: preview `/` hero yüklemesi geçti
  - testing agent raporu: `/app/test_reports/iteration_41.json` → frontend %100 PASS
  - `auto_frontend_testing_agent` → landing page validation PASS
  - `deep_testing_backend_v2` → backend no-regression PASS

## Son Uygulama Notu — 2026-03-09 (Landing hero overlap + login görünürlüğü hotfix)
- Kullanıcı geri bildirimi üzerine landing ve login yüzeyi hızlıca düzeltildi
  - Hero mockup üst satırında wrap/çakışma riski azaltıldı; topbar artık wrap-safe ve responsive
  - Hero sağ mockup genişliği sınırlandı, floating kartlar daha geç breakpoint’lerde görünür hale getirildi
  - Navbar’da görünür `Giriş` erişimi eklendi; `Demo` etiketi kısaltılarak 1100px civarı wrap problemi giderildi
  - Hero içine ayrıca `Zaten hesabınız var mı? Giriş Yap` yardımcı linki eklendi
- `/login` sayfası Syroce markasıyla yeniden kurgulandı
  - eski `Acenta Master` branding kaldırıldı
  - giriş formu artık daha görünür, üst katmanda ve dönüşüm odaklı bir düzen içinde sunuluyor
  - ek olarak trial CTA ve ana sayfaya dönüş aksiyonları eklendi
- Doğrulama
  - manuel screenshot smoke: `/` 1100px ve `/login` görünürlüğü doğrulandı
  - `auto_frontend_testing_agent` → 7/7 PASS (hero overlap yok, login form above-the-fold, CTA’lar çalışıyor)
  - `deep_testing_backend_v2` → auth ve public route no-regression PASS

## Öncelikli Sonraki Adımlar
- **P0:** Canlı email provider credential/config aktivasyonu yapılıp outbox -> gerçek teslimat hattını production benzeri ortamda doğrulama
- **P1:** Renewal / invoice paid / payment_failed lifecycle’ını timeline + banner + operasyon akışlarıyla daha da birleştirme
- **P1:** Admin kullanıcı yönetimi ve tenant paneli için ikinci tur UX polish: aktif abonelikli tenant’larda cancel/reactivate ve plan geçiş mikro-copy optimizasyonu
- **P1:** Admin cleanup faz-2: `partner-graph` ve tenant self-service duplicate endpoint’lerini (`/api/tenant/features`, `/api/tenant/quota-status`) konsolide etme
- **P1:** CORE olmayan route yüzeyleri için ikinci faz pruning uygulaması: `partners`, marketplace, advanced campaign, sms/qr ve benzeri modülleri `internal-only / addon / remove` sınıflarına indirgeme
- **P1:** `integration.call` ve gerekirse `b2b.match_request` için aynı hard quota guard modelini dış servis çağrısı öncesine genişletme
- **P1:** Billing analytics / churn görünürlüğü
- **P2:** Admin demo agency oluşturma butonu
- **P2:** Admin endpoint cleanup kalan parçaları (`/api/partner-graph/notifications/summary` kullanım sadeleştirmesi ve duplicate tenant endpoint alias cleanup)

## Bu Dosyanın Kapsamı
Bu PRD dosyası yalnızca statik ürün bağlamını taşır.
Detaylı uygulama geçmişi için `CHANGELOG.md`, kalan işler için `ROADMAP.md` kullanılmalıdır.