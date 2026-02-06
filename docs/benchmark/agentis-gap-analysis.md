# Platform Analizi — Agentis Benchmark Karşılaştırması

> Tarih: 2026-02-06
> Analiz: Mevcut uygulama vs Agentis referans

---

## 1) Ürün Konumu

**Uygulama şu anda: Multi-tenant B2B Travel ERP + SaaS Billing Platform**

Tek cümlede: Acenta/operatör yönetimi için modüler ERP, B2B network + marketplace altyapısı ile, üzerine plan-based SaaS monetization engine kurulmuş durumda.

**Agentis ile kıyasla:**
- Agentis = Acenta operasyon yazılımı (rezervasyon-merkezli, CRM, B2B, finans)
- Bizim uygulama = Aynı domain AMA altyapı katmanı çok daha derin (billing engine, plan inheritance, usage metering, multi-tenant SaaS)
- Agentis özellik genişliğinde ileride, biz altyapı derinliğinde iledeyiz

---

## 2) Mevcut Modüller — Detaylı Envanter

### Production-Ready (Backend + Frontend) ✅

| Modül | Backend | Frontend | Derinlik | Agentis'te Var? |
|---|---|---|---|---|
| **Auth & RBAC** | ✅ JWT, roles, password reset | ✅ Login, guard | Derin | ✅ |
| **Multi-Tenant SaaS** | ✅ Middleware, membership, tenant resolution | ✅ Tenant switcher | Derin | ❌ (single-tenant) |
| **B2B Exchange** | ✅ Listings, match requests, status machine | ✅ PartnerB2BNetworkPage, drawer | Derin (13 test) | ✅ |
| **B2B Portal** | ✅ Bookings, account, search | ✅ Dedicated layout | Orta | ✅ |
| **Partner Network** | ✅ Invites, relationships, discovery, statements | ✅ 6 sub-page | Derin | ✅ |
| **CRM** | ✅ Customers, deals, pipeline, tasks, events, duplicates, merge | ✅ 6 page | Orta-Derin | ✅ |
| **Booking/Reservation** | ✅ Lifecycle, FX, cancel, amend, financials | ✅ Agency flow | Derin | ✅ |
| **Inventory** | ✅ Upsert, bulk, availability | ✅ Page | Orta | ✅ |
| **Products** | ✅ Hotels, tours, rate plans | ✅ Catalog pages | Orta | ✅ |
| **Pricing Engine** | ✅ Rules, quotes, trace, incidents, audit | ✅ Admin pages | Derin | ✅ |
| **Settlements / Mutabakat** | ✅ Runs, statements, ledger, bridge | ✅ Admin + agency | Derin | ✅ |
| **Finance** | ✅ Refunds, exposure, ledger, FX snapshots | ✅ Admin pages | Derin | ✅ |
| **Ops** | ✅ Cases, incidents, tasks, B2B queues | ✅ Pages | Orta | ✅ |
| **Reports** | ✅ Reservations summary, sales | ✅ Page | Basit | ✅ |
| **Plan Engine** | ✅ Plan matrix, inheritance, add-ons | ✅ Admin UI | Derin | ❌ |
| **Billing / Subscription** | ✅ Stripe, webhooks, metered, finalize, cron | ✅ Panels | Derin | ❌ |
| **Usage Tracking** | ✅ Ledger, quota, push | ✅ Banners + panel | Derin | ❌ |
| **Revenue Analytics** | ✅ MRR, buckets, candidates | ✅ Dashboard | Orta | ❌ |
| **Audit / Observability** | ✅ Audit logs, B2B events, webhook events | ✅ Page + timeline | Derin | Kısmen |
| **Marketplace** | ✅ Listings, supplier mapping | ✅ Pages | Orta | ✅ |
| **Storefront** | ✅ Search, offer, checkout | ✅ Public pages | Basit | Kısmen |
| **CMS** | ✅ Pages | ✅ Public | Basit | ✅ |
| **Campaigns / Coupons** | ✅ CRUD + public | ✅ Admin + public | Basit | ✅ |
| **Integrations** | ✅ Hub, iCal, Paximum adapter, Parasut mock | ✅ Admin page | Orta | ✅ |
| **Theme / Whitelabel** | ✅ Theme API, whitelabel settings | ✅ Theme page | Basit | Kısmen |

### Backend Var, Frontend Eksik/Zayıf ⚠️

| Modül | Backend | Frontend Durumu |
|---|---|---|
| **WebPOS** | ❌ Yok | ❌ Yok |
| **Muhasebe (Accounting)** | ✅ admin_accounting (transactions, CSV export) | ⚠️ Sadece admin, acenta görmez |
| **Dashboard** | ✅ Metrics, reports endpoints | ⚠️ Basit sidebar stats, Agentis seviyesinde değil |
| **Raporlama** | ✅ Basit (summary + sales) | ⚠️ Agentis'in detaylı raporlarına kıyasla zayıf |

---

## 3) Kullanıcı Segmenti

**Mevcut roller:**
- `super_admin` / `admin` — Platform operatörü
- `agency_admin` / `agency_agent` — Acenta kullanıcıları
- `hotel_admin` / `hotel_staff` — Otel tarafı
- `b2b_agent` — B2B portal kullanıcısı

**Hedef kitle:** Orta ölçekli acenta operatörleri + B2B network oyuncuları.

**Agentis kıyasla:**
- Agentis küçük-orta acenta hedefler (1-50 kullanıcı)
- Bizim sistem multi-tenant SaaS olduğu için franchise/network modeline daha uygun
- Enterprise segment (plan engine sayesinde) daha güçlü

---

## 4) En Zayıf Alanlar

### 🔴 Kritik Eksikler (Agentis'e göre)

**1. Dashboard Zayıf**
- Agentis: Haftalık özet, satış grafiği, dönüşüm oranı, online durumu, aksiyon kartları
- Biz: Sidebar'da basit sayılar (toplam, bekleyen, ciro). Merkezi dashboard yok.
- **Etki**: İlk izlenim zayıf, kullanıcı değer algılamaz

**2. WebPOS Yok**
- Agentis: WebPOS + tahsilat yönetimi
- Biz: Hiç yok (backend + frontend)
- **Etki**: Fiziksel ofisi olan acentalar için eksik

**3. Raporlama Yüzeysel**
- Agentis: Detaylı raporlar (satış, dönüşüm, acenta performansı, ürün bazlı)
- Biz: 2 basit endpoint (reservations-summary, sales-summary)
- **Etki**: Karar verici (patron) için yetersiz

**4. Ürün Modülleri Eksik**
- Agentis: Tur, otel, uçak, transfer, diğer hizmetler — hepsi ayrı modül
- Biz: Otel + tur var, diğerleri eksik
- **Etki**: Çok-ürünlü acenta için yetersiz

### 🟡 Orta Eksikler

**5. Acenta Dashboard Yok**
- Agency kullanıcıları için özel dashboard eksik (kendi satışları, performansı)

**6. Mobil UX Optimize Değil**
- Responsive var ama mobil-first deneyim değil

**7. Bildirim/Notification Sistemi Zayıf**
- In-app notification yok (sadece quota banner)
- Email notification minimal

---

## 5) Öncelik Analizi — Agentis Seviyesine Çıkmak

### Özellik olarak:
- Dashboard, Raporlama, Ürün çeşitliliği eksik
- WebPOS eksik

### UX olarak:
- Dashboard deneyimi Agentis'in çok gerisinde
- Sidebar-based navigation vs Agentis'in sol menü yapısı

### Operasyonel derinlik olarak:
- **Biz ilerideyiz**: Multi-tenant, billing engine, usage metering, audit — Agentis'te yok
- Ama kullanıcı bunu görmez; dashboard gösterilmezse "boş" hisseder

### Güven algısı olarak:
- Agentis: Yoğun veri + aksiyon = "bu sistem her şeyi yapıyor" hissi
- Biz: Altyapı güçlü ama ön yüz bunu yansıtmıyor

---

## 6) Teknik Stack

| Katman | Teknoloji | Durum |
|---|---|---|
| Backend | FastAPI (Python 3.11) | 134 router, 104 service, 24 repository |
| Frontend | React + Shadcn UI | ~100 sayfa |
| Database | MongoDB (Motor async) | 138 collection, multi-tenant |
| Auth | JWT + RBAC + multi-role | Production |
| Billing | Stripe SDK + BillingProvider ABC | Production |
| Scheduler | APScheduler | Production |
| Tests | Pytest (63+ integration) + Playwright | Aktif |
| Multi-tenant | TenantResolutionMiddleware + FeatureContext | Production |
| Observability | Audit logs + B2B events + Slack alerts | Production |

---

## Sonuç: Gap Analizi Özeti

| Alan | Biz | Agentis | Gap |
|---|---|---|---|
| Altyapı (SaaS, Billing) | ⭐⭐⭐⭐⭐ | ⭐⭐ | Biz ilerideyiz |
| B2B Network | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Eşit |
| Dashboard UX | ⭐⭐ | ⭐⭐⭐⭐⭐ | Kritik gap |
| Raporlama | ⭐⭐ | ⭐⭐⭐⭐ | Büyük gap |
| Ürün Çeşitliliği | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Orta gap |
| CRM | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Eşit |
| Finans/Mutabakat | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Biz ilerideyiz |
| Operasyon (Ops) | ⭐⭐⭐⭐ | ⭐⭐⭐ | Biz ilerideyiz |
| WebPOS | ⭐ | ⭐⭐⭐⭐ | Kritik gap |
| Mobil UX | ⭐⭐ | ⭐⭐⭐⭐ | Orta gap |
