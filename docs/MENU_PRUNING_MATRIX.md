# Menü Budama Matrisi (Faz 3 - Sprint 1)

## Karar Politikası

| Karar       | Kural                                                        |
|-------------|--------------------------------------------------------------|
| **KEEP**    | Haftada 1+ kullanım, persona top-5 işine hizmet ediyor       |
| **MERGE**   | Başka menü altında alt-sekme olabilir                         |
| **MOVE**    | İkincil yüzey / "Gelişmiş" altına taşınmalı                  |
| **HIDE**    | Sidebar'dan kaldır ama route erişimi koru (directAccessOnly)  |
| **REMOVE**  | Fiziksel route silme YOK (Faz 3 politikası). Sadece menüden   |

---

## Admin Persona - Menü Budama

### Grup 1: DASHBOARD
| Mevcut Menü                | Path                       | Karar  | Hedef Grup   |
|---------------------------|----------------------------|--------|--------------|
| Dashboard (Ana)            | /app                       | KEEP   | Dashboard    |
| Yönetici Dashboard         | /app/admin/dashboard       | MERGE  | Dashboard    |

### Grup 2: OPERASYON
| Mevcut Menü                | Path                            | Karar  | Hedef Grup   |
|---------------------------|----------------------------------|--------|--------------|
| Siparişler                 | /app/admin/orders                | KEEP   | Operasyon    |
| Onay Kutusu                | /app/admin/approval-inbox        | KEEP   | Operasyon    |
| Misafir Vakaları           | /app/ops/guest-cases             | KEEP   | Operasyon    |
| Operasyon Görevleri        | /app/ops/tasks                   | KEEP   | Operasyon    |
| Inbox                      | /app/inbox                       | KEEP   | Operasyon    |
| Oteller                    | /app/admin/hotels                | MOVE   | Operasyon (HIDE) |
| Turlar                     | /app/admin/tours                 | MOVE   | Operasyon (HIDE) |
| Ops B2B                    | /app/admin/ops/b2b               | HIDE   | directAccess |
| Ops Incidents              | /app/ops/incidents               | HIDE   | directAccess |

### Grup 3: REZERVASYONLAR
| Mevcut Menü                | Path                            | Karar  | Hedef Grup      |
|---------------------------|----------------------------------|--------|-----------------|
| Tüm Rezervasyonlar         | /app/reservations                | KEEP   | Rezervasyonlar  |
| İadeler                    | /app/admin/finance/refunds       | KEEP   | Rezervasyonlar  |
| Açık Bakiye                | /app/admin/finance/exposure      | KEEP   | Rezervasyonlar  |

### Grup 4: MÜŞTERİ & ACENTA
| Mevcut Menü                | Path                             | Karar  | Hedef Grup       |
|---------------------------|-----------------------------------|--------|------------------|
| Müşteriler                 | /app/crm/customers                | KEEP   | Müşteri&Acenta   |
| Acentalar                  | /app/admin/agencies               | KEEP   | Müşteri&Acenta   |
| İş Ortakları               | /app/admin/partners               | KEEP   | Müşteri&Acenta   |
| B2B Dashboard              | /app/admin/b2b/dashboard          | KEEP   | Müşteri&Acenta   |
| Acenta Sözleşmeleri        | /app/admin/agency-contracts       | HIDE   | directAccess     |
| B2B Marketplace            | /app/admin/b2b/marketplace        | HIDE   | directAccess     |
| B2B Funnel                 | /app/admin/b2b/funnel             | HIDE   | directAccess     |
| B2B Duyurular              | /app/admin/b2b/announcements      | HIDE   | directAccess     |
| Partner Ağı                | /app/partners                     | HIDE   | directAccess     |

### Grup 5: FİYATLANDIRMA
| Mevcut Menü                | Path                             | Karar  | Hedef Grup      |
|---------------------------|-----------------------------------|--------|-----------------|
| Fiyat Yönetimi             | /app/admin/pricing                | KEEP   | Fiyatlandırma   |
| Fiyat Kuralları            | /app/admin/pricing/rules          | KEEP   | Fiyatlandırma   |
| Kampanyalar                | /app/admin/campaigns              | KEEP   | Fiyatlandırma   |
| Kuponlar                   | /app/admin/coupons                | KEEP   | Fiyatlandırma   |
| B2B İndirimler             | /app/admin/b2b/discounts          | HIDE   | directAccess    |
| Pricing Engine             | /app/admin/pricing-engine         | HIDE   | directAccess    |
| Pricing Incidents          | /app/admin/pricing/incidents      | HIDE   | directAccess    |
| Pricing Funnel             | /app/admin/pricing/funnel         | HIDE   | directAccess    |

### Grup 6: RAPORLAR
| Mevcut Menü                | Path                                 | Karar  | Hedef Grup  |
|---------------------------|---------------------------------------|--------|-------------|
| Gelir Analizi              | /app/admin/analytics                  | KEEP   | Raporlar    |
| Raporlama                  | /app/admin/reporting                  | KEEP   | Raporlar    |
| Mutabakat                  | /app/admin/finance/settlements        | KEEP   | Raporlar    |
| Dışa Aktarma               | /app/admin/exports                    | KEEP   | Raporlar    |
| Eşleşmeler                | /app/admin/matches                    | KEEP   | Raporlar    |
| Zamanlanmış Raporlar       | /app/admin/scheduled-reports          | HIDE   | directAccess|
| Match Risk Trends          | /app/admin/reports/match-risk-trends  | HIDE   | directAccess|
| KPI Analitik               | /app/admin/analytics-kpi             | HIDE   | directAccess|
| Audit Logları              | /app/admin/audit-logs                | HIDE   | directAccess|
| Email Logları              | /app/admin/email-logs                | HIDE   | directAccess|

### Grup 7: AYARLAR
| Mevcut Menü                | Path                             | Karar  | Hedef Grup  |
|---------------------------|-----------------------------------|--------|-------------|
| Kullanıcılar               | /app/admin/all-users              | KEEP   | Ayarlar     |
| Entegrasyonlar             | /app/admin/integrations           | KEEP   | Ayarlar     |
| Tenant Ayarları            | /app/admin/tenant-features        | KEEP   | Ayarlar     |
| Branding                   | /app/admin/branding               | KEEP   | Ayarlar     |
| API Anahtarları            | /app/admin/api-keys               | KEEP   | Ayarlar     |
| Acenta Modülleri           | /app/admin/agency-modules         | HIDE   | directAccess|
| Tema                       | /app/admin/theme                  | HIDE   | directAccess|
| CMS Sayfaları              | /app/admin/cms/pages              | HIDE   | directAccess|
| SMS                        | /app/admin/sms                    | HIDE   | directAccess|
| E-Fatura                   | /app/admin/efatura                | HIDE   | directAccess|
| Muhasebe                   | /app/admin/accounting             | HIDE   | directAccess|
| Jobs                       | /app/admin/jobs                   | HIDE   | directAccess|
| Tickets                    | /app/admin/tickets                | HIDE   | directAccess|

### SİSTEM & GELİŞMİŞ (sidebar'da görünmez)
| Mevcut Menü                | Path                                    | Karar  |
|---------------------------|-----------------------------------------|--------|
| System Backups             | /app/admin/system-backups               | HIDE   |
| System Integrity           | /app/admin/system-integrity             | HIDE   |
| System Metrics             | /app/admin/system-metrics               | HIDE   |
| System Errors              | /app/admin/system-errors                | HIDE   |
| System Uptime              | /app/admin/system-uptime                | HIDE   |
| System Incidents           | /app/admin/system-incidents             | HIDE   |
| Preflight                  | /app/admin/preflight                    | HIDE   |
| Runbook                    | /app/admin/runbook                      | HIDE   |
| Perf Dashboard             | /app/admin/perf-dashboard               | HIDE   |
| Platform Hardening         | /app/admin/platform-hardening           | HIDE   |
| Platform Monitoring        | /app/admin/platform-monitoring          | HIDE   |
| Reconciliation             | /app/admin/reconciliation               | HIDE   |
| Supplier Economics         | /app/admin/supplier-economics           | HIDE   |
| Revenue Optimization       | /app/admin/revenue-optimization         | HIDE   |
| Operations Readiness       | /app/admin/operations-readiness         | HIDE   |
| Market Launch              | /app/admin/market-launch                | HIDE   |
| Growth Engine              | /app/admin/growth-engine                | HIDE   |
| Supplier Credentials       | /app/admin/supplier-credentials         | HIDE   |
| Supplier Onboarding        | /app/admin/supplier-onboarding          | HIDE   |
| Certification Console      | /app/admin/certification-console        | HIDE   |
| Cache Health               | /app/admin/cache-health                 | HIDE   |
| Pilot Dashboard            | /app/admin/pilot-dashboard              | HIDE   |
| Pilot Wizard               | /app/admin/pilot-wizard                 | HIDE   |
| Pilot Onboarding           | /app/admin/pilot-onboarding             | HIDE   |
| Demo Guide                 | /app/admin/demo-guide                   | HIDE   |
| Tenant Export              | /app/admin/tenant-export                | HIDE   |
| Import                     | /app/admin/import                       | HIDE   |
| Portfolio Sync             | /app/admin/portfolio-sync               | HIDE   |
| Product Mode               | /app/admin/product-mode                 | HIDE   |
| All Modules                | /app/admin/modules                      | HIDE   |
| Tenant Health              | /app/admin/tenant-health                | HIDE   |
| Platform Metrics           | /app/admin/metrics                      | HIDE   |

---

## Agency Persona - Menü Budama

| Mevcut Menü                | Path                         | Karar  | Hedef Grup       |
|---------------------------|-------------------------------|--------|------------------|
| Dashboard                  | /app                          | KEEP   | Dashboard        |
| Otel Arama                 | /app/agency/hotels            | KEEP   | Arama & Satış    |
| Çoklu Supplier Arama       | /app/agency/unified-search    | KEEP   | Arama & Satış    |
| Müsaitlik                  | /app/agency/availability      | KEEP   | Arama & Satış    |
| Turlar                     | /app/tours                    | KEEP   | Arama & Satış    |
| Rezervasyonlarım           | /app/agency/bookings          | KEEP   | Rezervasyonlar   |
| Tüm Rezervasyonlar         | /app/reservations             | HIDE   | directAccess     |
| Pipeline                   | /app/crm/pipeline             | KEEP   | Teklifler        |
| CRM Görevleri              | /app/crm/tasks                | KEEP   | Teklifler        |
| Müşteriler                 | /app/crm/customers            | KEEP   | Müşteriler       |
| Mutabakat                  | /app/agency/settlements       | KEEP   | Hesap / Finans   |
| PMS Paneli                 | /app/agency/pms               | KEEP   | Hesap / Finans   |
| Muhasebe                   | /app/agency/pms/accounting    | KEEP   | Hesap / Finans   |
| Faturalar                  | /app/invoices                 | KEEP   | Hesap / Finans   |
| Yardım                     | /app/agency/help              | KEEP   | Destek           |
| Google Sheets              | /app/agency/sheets            | KEEP   | Destek           |
| Raporlar                   | /app/reports                  | HIDE   | directAccess     |
| Oda Yönetimi               | /app/agency/pms/rooms         | HIDE   | directAccess     |

---

## Hotel Persona - Menü Budama

| Mevcut Menü                | Path                         | Karar  | Hedef Grup      |
|---------------------------|-------------------------------|--------|-----------------|
| Dashboard                  | /app/hotel/bookings           | KEEP   | Dashboard       |
| Kontenjan                  | /app/hotel/allocations        | KEEP   | Envanter        |
| Gelen Talepler             | /app/hotel/bookings           | KEEP   | Rezervasyonlar  |
| Stop Sell                  | /app/hotel/stop-sell          | KEEP   | Kısıtlar        |
| Entegrasyonlar             | /app/hotel/integrations       | KEEP   | Ayarlar         |
| Mutabakat                  | /app/hotel/settlements        | KEEP   | Ayarlar         |
| Yardım                     | /app/hotel/help               | KEEP   | Ayarlar         |

---

## B2B Persona - Menü Budama

| Mevcut Menü                | Path                  | Karar  | Hedef Grup       |
|---------------------------|-----------------------|--------|------------------|
| Rezervasyonlarım           | /b2b/bookings         | KEEP   | Rezervasyonlarım |
| Cari Hesap                 | /b2b/account          | KEEP   | Hesap Özeti      |

---

## Birleştirme Kararları Özeti

| Eski Ayrı Menüler                                   | Yeni Tek Menü        |
|------------------------------------------------------|----------------------|
| Reports + Analytics + Exports                         | Raporlar             |
| Users + Roles + Permissions + Modules                 | Ayarlar > Kullanıcılar|
| Pricing + Markup + Commission + Rules                 | Fiyatlandırma        |
| Inventory + Availability + Allotment + Stop Sale      | Envanter + Kısıtlar  |
| Settings + Config + Parameters + Integrations         | Ayarlar              |
| Bookings + Orders + Confirmations + Cancellations     | Rezervasyonlar       |
| PMS Dashboard + Accounting + Invoices                 | Hesap / Finans       |

## İstatistikler

| Persona  | Önceki Sidebar Menü | Yeni Sidebar Menü | Azalma |
|----------|---------------------|--------------------|--------|
| Admin    | ~60+                | 27                 | %55+   |
| Agency   | ~15                 | 14                 | %7     |
| Hotel    | 6                   | 7 (genişletildi)   | -      |
| B2B      | 2                   | 6 (genişletildi)   | -      |
