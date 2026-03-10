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

## Son Bakım Güncellemesi — 2026-03-10 Login Network Error Hardening
- Kullanıcının bildirdiği `/login` ve `/b2b/login` üzerindeki `Network Error` akışı için frontend auth katmanı güçlendirildi.
- Login ve auth bootstrap isteklerine kısa gecikmeli retry + same-origin fallback eklendi.
- Raw `Network Error` mesajı yerine Türkçe ve aksiyon verici hata mesajı gösterilecek şekilde UX iyileştirildi.
- `/b2b/login` tarafında B2B yetki kontrol isteği de network fallback ile güçlendirildi.
- Smoke + frontend login regresyon testi sonucu: admin ve B2B login akışları geçti; `Network Error` yeniden üretilemedi.

## Son Bakım Güncellemesi — 2026-03-10 Perf RCA + Optimizasyon
- Perf dashboard’daki yavaş endpointlerin önemli kök nedenleri bulundu:
  - `/api/billing/subscription` her GET’te billing overview + Stripe sync yoluna girebiliyordu
  - dashboard endpointlerinde cold miss sırasında çoklu Mongo query yükü vardı
  - `endpoint_cache` Mongo fallback katmanı, naive/aware datetime karşılaştırma bug’ı yüzünden efektif çalışmıyordu
  - super_admin akışında tenant resolve için ek DB lookup yapılıyordu
- Yapılan iyileştirmeler:
  - billing overview için cache eklendi
  - tenant resolve için cached servis eklendi
  - dashboard KPI / weekly / reservation widgets akışlarında cache ve concurrency iyileştirildi
  - endpoint cache Mongo fallback düzeltildi; böylece Redis yokken de cache gerçekten hit alıyor
  - performans için ek index kapsamı genişletildi (`request_logs`, `storefront_sessions`, `products`, `tours`, `public_quotes`, billing collections)
- Ölçülen sonuç:
  - `/api/billing/subscription` tekrar eden isteklerde ~500-800ms bandından ~60-120ms bandına indi
  - `weekly-summary`, `tenant/features`, `kpi-stats`, `reservation-widgets` ~60-80ms bandında doğrulandı
- Not: Perf dashboard’daki **24 saatlik p95** metrikleri tarihsel örnekleri tuttuğu için eski yavaş sample’lar hemen kaybolmaz; 1 saatlik pencerede yeni iyileşme çok daha net görünür.

## Son Bakım Güncellemesi — 2026-03-10 Custom Domain CORS RCA
- Frontend için `backendUrl.js` yardımcı katmanı eklendi; custom domain ile backend env host'u farklıysa istekler artık same-origin `/api` üstünden çözülüyor.
- `lib/api.js` ve doğrudan backend URL kullanan indirme / voucher / asset akışları bu yardımcıya taşındı; böylece yeni build’de cross-origin bağımlılık azaltıldı.
- Backend CORS preview/dev modunda regex tabanlı explicit origin echo davranışına alındı; local preflight testinde `Origin: https://agency.syroce.com` için `Access-Control-Allow-Origin: https://agency.syroce.com` ve `allow-credentials: true` doğrulandı.
- Smoke sonucu: preview domain (`agency-ops-core.preview.emergentagent.com`) üzerinde login + `/app/reservations` geçti ve hata bannerı görünmedi.
- Kritik RCA: `agency.syroce.com` halen eski production bundle `main.a26343a0.js` servis ediyor; bundle içine `https://improvement-areas.emergent.host` hardcode gömülü. Yani custom domain şu an bu workspace’teki güncel frontend kodunu değil, eski deploy build’ini sunuyor.
- Sonuç: Kod düzeltmesi hazır ve preview’de doğrulandı; **custom domain canlı akışı deployment/cache senkronu olmadan tamamen düzelmiş sayılmaz**.

## Son Uygulama Güncellemesi — 2026-03-10 Demo Seed Target User Flow
- Superadmin için demo seed akışı genişletildi: demo verisi artık **hedef agency kullanıcı** seçilerek yüklenebiliyor.
- Yeni backend endpointi: `GET /api/admin/demo/seed-targets` → agency rolündeki ve acenteye bağlı kullanıcıları döndürür.
- `POST /api/admin/demo/seed` artık `target_user_id` kabul ediyor; seed işlemi seçilen agency kullanıcısının tenant/acenta bağlamında çalışıyor.
- `already_seeded` yanıtı da hedef kullanıcı/acenta bilgisini koruyacak şekilde güçlendirildi.
- Frontend’de `DemoSeedButton` modalına kullanıcı seçici eklendi; `Kullanıcı Yönetimi` ekranında her agency kullanıcı satırına hızlı **Demo** butonu yerleştirildi.
- Doğrulama: Iteration 49 raporunda backend endpointleri ve row-level Demo butonu + modal hedef kullanıcı seçimi geçti.

## Son Uygulama Güncellemesi — 2026-03-10 Agency Contract / Süre Yönetimi
- Acenta bazlı sözleşme alanları eklendi: `contract_start_date`, `contract_end_date`, `payment_status`, `package_type`, `user_limit`.
- `/api/admin/agencies` ve `/api/admin/agencies/` artık sözleşme özetini (`contract_summary`), aktif kullanıcı sayısını ve kalan koltuk bilgisini döndürüyor; legacy `/api/admin/agencies` yolu yeni davranışla hizalandı.
- Superadmin kullanıcı oluşturma ve acentaya kullanıcı bağlama akışlarında **kullanıcı limiti enforcement** eklendi; limit doluysa `agency_user_limit_reached` ile bloklanıyor.
- Admin `Acentalar`, `Kullanıcı Yönetimi` ve `Acenta Kullanıcıları` sayfaları sözleşme süresi, ödeme durumu, paket tipi ve kullanıcı limiti görünürlüğüyle güncellendi.
- Agency kullanıcı oturumunda 30 gün kala üst uyarı banner’ı, süre geçince de erişim kısıtlı overlay’i eklendi.
- Doğrulama: backend pytest dosyası `test_admin_agency_contract_controls.py` geçti; preview smoke + backend/ frontend test agent akışları create/update/list/user-limit senaryolarını doğruladı.

## Son Uygulama Güncellemesi — 2026-03-10 Landing Hero Typography Fix
- Kullanıcının bildirdiği desktop/fullscreen hero mockup yazı kesilmesi için `LandingDashboardMockup.jsx` tipografi güvenlik payı artırıldı.
- Üst mockup kartı, status badge’leri, KPI etiketleri, rezervasyon satırları, CRM ve finans metinlerinde line-height/padding değerleri genişletildi; böylece descender clipping riski azaltıldı.
- Aynı mockup component landing içinde birden fazla yerde tekrar kullanıldığı için düzeltme ilgili önizleme kartlarına da yansıdı.
- Doğrulama: screenshot smoke + frontend testing agent ile `1920x800`, `1600x900`, `1366x768` viewportlarında kritik hero metinlerinde clipping/overflow görülmedi.

## Son Uygulama Güncellemesi — 2026-03-10 Landing Floating Card + Pricing Refresh
- Kullanıcının ikinci görsel geri bildirimi sonrası hero’daki sol floating kart yeniden konumlandırıldı; artık büyük dashboard kutusunun altında yarım görünmüyor. Kartlar sadece `min-[1700px]` genişlikte gösteriliyor ve dashboard’ın dışında konumlanıyor.
- Landing page fiyatlandırma bölümü Agentis mantığı incelenerek yeniden yazıldı: `Giriş`, `Standart`, `Profesyonel`, `Platinum` paketleri; aylık/yıllık görünüm, özel teklif barı ve **Google Sheets / E-Tablo entegrasyonu Standart paket ve üstünde** vurgusu eklendi.
- `/pricing` sayfası tamamen yenilendi: yeni hero, 4 paket kartı, aylık/yıllık toggle, detaylı karşılaştırma tablosu ve Syroce’a özel SSS bölümü eklendi.
- Landing page içine de ayrı bir SSS accordion bölümü eklendi; navbar’a `SSS` anchor bağlantısı bağlandı.
- Doğrulama: Iteration 50 frontend test raporunda hero floating kart fix’i, 4 paket görünürlüğü, E-Tablo vurgusu, comparison table ve FAQ accordion akışları %100 geçti.

## Son Uygulama Güncellemesi — 2026-03-10 Landing Hero Floating Cards Removal
- Kullanıcının son görsel tercihi doğrultusunda hero mockup üstündeki iki floating metin kartı tamamen kaldırıldı:
  - `12 yeni rezervasyon bugün`
  - `Tahsilat süresi %40 daha hızlı`
- Hero görsel alanı sadeleştirildi; dashboard mockup tek başına bırakılarak daha temiz bir ilk izlenim sağlandı.
- Doğrulama: screenshot smoke + frontend verification agent ile bu iki metnin artık DOM’da görünmediği ve hero’da clipping/overlap olmadığı doğrulandı.

## Son Bakım Güncellemesi — 2026-03-10 Backend Lint EOF Fix
- CI ekranında görünen `agency_contract_status_service.py` dosyası için EOF/trailing newline sorunu düzeltildi.
- Lokal doğrulama: `ruff check /app/backend/app/services/agency_contract_status_service.py` temiz geçti.

## Son Bakım Güncellemesi — 2026-03-10 Agency User Tenant Membership Fix
- Kullanıcının ekran görüntüsündeki `Aktif tenant üyeliği bulunamadı` login hatası için agency kullanıcı yaratma akışı güçlendirildi.
- Yeni servis: `tenant_membership_repair_service.py` ile kullanıcı oluşturma / acentaya bağlama / kullanıcı güncelleme akışlarında tenant membership otomatik upsert ediliyor.
- Login context ve tenant middleware içine self-heal eklendi; membership eksik legacy kullanıcılar login veya admin repair akışı sırasında otomatik toparlanabiliyor.
- Yeni admin endpoint: `POST /api/admin/all-users/repair-memberships` → mevcut agency kullanıcılarını topluca onarıyor.
- Preview’de toplu onarım çalıştırıldı: `scanned: 11, repaired: 11, skipped: 0`.
- Doğrulama: backend pytest `test_admin_user_membership_repair.py` geçti; preview smoke testte yeni oluşturulan kullanıcı login’i 200 döndü ve membership hatası yeniden oluşmadı.

## Son Bakım Güncellemesi — 2026-03-10 Production Deploy Healthz Fix
- Emergent deployment loglarında görülen ana blocker tespit edildi: platform `GET /api/healthz` probe atıyor, uygulama ise bu endpointi 404 döndürüyordu.
- `backend/app/routers/health.py` içine hafif ve authsuz readiness endpointleri eklendi:
  - `/api/healthz`
  - `/api/health/ready`
  - mevcut `/api/health` korunuyor
- Tenant middleware zaten `/api/healthz` ve `/api/health/*` yollarını auth/tenant çözümlemesinden muaf tuttuğu için endpointler deploy probe’ları için uygun hale geldi.
- Doğrulama: backend smoke + backend testing agent ile `/api/healthz`, `/api/health/ready`, `/api/health` üçü de 200 döndü; authsuz `/api/auth/me` 401 davranışının normal olduğu not edildi.

## Son Doğrulama Notu — 2026-03-10 Custom Domain 502 Verification
- Kullanıcının önceliği doğrultusunda deploy sonrası custom domain tekrar doğrulandı.
- Smoke sonuçları:
  - Preview `GET /api/healthz` → `200`
  - Preview `POST /api/auth/login` (`agent@acenta.test` / `agent123`) → `200`
  - Custom domain `https://agency.syroce.com/api/healthz` → `200`
  - Custom domain `POST /api/auth/login` → `200`
  - Browser smoke: `https://agency.syroce.com/login` üzerinden giriş sonrası `/app` ekranına başarılı yönlendirme doğrulandı.
- Ek not: current custom bundle içinde build-time `REACT_APP_BACKEND_URL` olarak eski host string hâlâ gömülü görünüyor; ancak `frontend/src/lib/backendUrl.js` same-origin fallback’i sayesinde canlı custom domain login akışı kırılmadan çalışıyor.

## Son Bakım Güncellemesi — 2026-03-10 Agency Login Unauthorized Redirect Fix
- Kullanıcının bildirdiği agency kullanıcı login sonrası yanlışlıkla `/unauthorized` ekranına düşme problemi frontend redirect katmanında ele alındı.
- Kök neden: sessionStorage içinde kalan eski `/app/admin/...` post-login redirect değeri agency kullanıcı login’inde yeniden tüketilip yetkisiz admin route’una götürebiliyordu.
- `frontend/src/lib/authRedirect.js` içine role-aware güvenlik kontrolü eklendi; artık hatalı/stale redirect sadece kullanıcı rolüyle uyumluysa tüketiliyor, aksi halde güvenli fallback kullanılıyor.
- `frontend/src/pages/LoginPage.jsx` login sonrası yönlendirmeyi yeni güvenli helper ile güncellendi; agency kullanıcılar varsayılan olarak `/app` dashboard’a düşüyor.
- Doğrulama: preview üzerinde `acenta_post_login_redirect=/app/admin/agency-modules` seed edilerek agency login testi çalıştırıldı; sonuç `/app`, `/unauthorized` değil.

## Son Bakım Güncellemesi — 2026-03-10 Agency Sidebar Module Visibility Fix
- Kullanıcının bildirdiği “Google Sheets / turlar / oteller / müşteriler seçili ama görünmüyor” problemi agency sidebar ve modül anahtarı eşleme katmanında çözüldü.
- Yeni normalizasyon katmanı eklendi: legacy modül anahtarları (`turlarimiz`, `urunler`, `musaitlik_takibi`, `google_sheet_baglantisi`) artık canonical anahtarlara (`turlar`, `oteller`, `musaitlik`, `sheet_baglantilari`) çevriliyor.
- Backend `admin_agencies` ve `agency_profile` endpointleri normalize edilmiş `allowed_modules` döndürecek ve kayıt sırasında canonical liste saklayacak şekilde güncellendi.
- Frontend `AppShell` agency filtreleme mantığı artık sadece non-core öğelerde değil, dashboard hariç tüm modül bazlı sidebar öğelerinde çalışıyor; böylece seçilen agency ekranları gerçekten görünür/gizli hale geliyor.
- Agency sidebar'a görünür yeni bölüm eklendi: `Oteller`, `Müsaitlik`, `Turlar`, `Google Sheets`.
- `AdminAgencyModulesPage` gerçek agency ekranlarını yönetecek şekilde sadeleştirildi ve canonical anahtarlarla hizalandı.
- Doğrulama:
  - Frontend verification agent: 17/17 test geçti; login, sidebar görünürlüğü ve 4 hedef sayfa navigasyonu doğrulandı.
  - Backend testing agent: 6/6 test geçti; alias normalizasyonu ve profile/modules endpointleri doğrulandı.

## Kalan Öncelikli İşler
- P0: Kullanıcıdan gerçek Google Service Account JSON alıp canlı doğrulama ve gerçek sync smoke test yapmak.
- P0: Agency sözleşme süresi dolunca backend tarafında route-level enforcement gerekip gerekmediğini kullanıcıyla doğrulayıp karar vermek (şu an UI kısıtlaması aktif).
- P1: Agency bazlı modül görünürlüğüsünden kullanıcı bazlı ekran/izin modeline geçiş için veri modeli ve admin UX tasarımını netleştirmek.
- P1: Custom domain build-time env string’ini tamamen temizleyecek daha katı runtime-only çözüm gerekip gerekmediğini izlemek (şu an canlı login akışı çalışıyor).
- P1: Bu login redirect fix’inin custom domain build’ine yansımasını doğrulamak; preview doğrulandı, live domain eski bundle cache’i varsa yeniden gözlemek.
- P1: Demo seed akışına acenta/tenant filtreleri ve toplu hedefleme (tek seferde birden fazla agency kullanıcı) eklemek.
- P1: Zamanlanmış otomatik sync davranışını gerçek credential ile doğrulamak ve gerekiyorsa UI'daki interval beklentisiyle birebir hizalamak.
- P1: Bulk master sheet akışını gerçek Google credential ile canlı sheet üzerinden smoke test etmek.
- P1: Sheet'ten gelen rezervasyonların rezervasyon listesi / durum yaşam döngüsü görünürlüğünü güçlendirmek.
- P2: Önceki fork'tan kalan diğer UI doğrulamalarını topluca gözden geçirmek.

## Doküman Ayrımı
- Bu dosya statik ürün bağlamını taşır
- Detaylı teslim geçmişi için `CHANGELOG.md`
- Kalan ve öncelikli işler için `ROADMAP.md`