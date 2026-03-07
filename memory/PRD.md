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
- `frontend/src/pages/admin/AdminTenantFeaturesPage.jsx`
- `frontend/src/components/admin/TenantEntitlementOverview.jsx`
- `frontend/src/pages/public/PricingPage.jsx`

## Bu Dosyanın Kapsamı
Bu PRD dosyası yalnızca statik ürün bağlamını taşır.
Detaylı uygulama geçmişi için `CHANGELOG.md`, kalan işler için `ROADMAP.md` kullanılmalıdır.