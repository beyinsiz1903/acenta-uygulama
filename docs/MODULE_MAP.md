# Syroce — Modül Haritası

> Bu doküman, platformdaki tüm modüllerin sınıflandırmasını, sorumluluklarını ve sahiplik alanlarını tanımlar.

---

## Modül Sınıflandırma Prensipleri

| Katman | Tanım | Kriter |
|--------|--------|--------|
| **Çekirdek** | Ürünün çalışması için zorunlu, her müşteride aktif | Kapatılamaz, her planda var |
| **Destekleyici Çekirdek** | Operasyonel derinlik sağlar, bazı müşteriler için kritik | Plan bazlı aktif/pasif olabilir |
| **Extension** | Ek değer katan, bağımsız çalışabilen modüller | Feature flag ile kontrol edilir |

---

## 1. Çekirdek Modüller

Platformun temel iskeletini oluşturur. Bu modüller olmadan ürün çalışmaz.

### 1.1 Identity & Tenant
| Alan | Konum | Sorumluluk |
|------|--------|------------|
| Tenant Isolation | `app/modules/tenant/` | Multi-tenant izolasyon, org context, guard |
| Identity | `app/modules/identity/` | Kullanıcı yönetimi, roller, acentalar, ayarlar, whitelabel |
| Auth | `app/modules/auth/` | JWT, 2FA, session, password reset, token blacklist |

**Router'lar:** `tenant/router.py`, `auth/__init__.py (domain_router)`, `identity/__init__.py (domain_router)`, `routers/settings.py`, `routers/enterprise_rbac.py`

### 1.2 Booking (Rezervasyon Motoru)
| Alan | Konum | Sorumluluk |
|------|--------|------------|
| State Machine | `app/modules/booking/` | Unified booking lifecycle, transitions, OCC |
| Booking Service | `app/services/booking_service.py` | CRUD, listing, query |
| Booking Events | `app/services/booking_events.py` | Lifecycle event yayını |
| Amendments | `app/services/booking_amendments.py` | Fiyat/tarih değişiklik akışı |

**Router'lar:** `modules/booking/router.py`, `routers/bookings.py` (legacy), `routers/booking_outcomes.py`, `routers/unified_booking_router.py`

### 1.3 Finance (Finans)
| Alan | Konum | Sorumluluk |
|------|--------|------------|
| Finance Domain | `app/modules/finance/` | Faturalama, ödemeler, mutabakat |
| Ledger | `app/services/finance_ledger_service.py` | Muhasebe defteri, posting |
| Settlements | `app/services/settlement_service.py` | Tedarikçi/acente mutabakat |
| Billing | `app/billing/` | Stripe/Iyzico, subscription lifecycle |
| Payments | `app/services/booking_payments.py` | Ödeme takibi |
| Invoice Engine | `app/services/invoice_engine.py` | Fatura üretimi |
| FX | `app/services/fx.py` | Döviz kuru yönetimi |

**Router'lar:** `modules/finance/__init__.py (domain_router)`, `routers/finance.py`, `routers/finance_ledger.py`, `routers/payments.py`, `routers/settlements.py`, `routers/invoice_engine.py`, `routers/billing_*.py`, `routers/efatura.py`

### 1.4 Supplier (Tedarikçi)
| Alan | Konum | Sorumluluk |
|------|--------|------------|
| Supplier Domain | `app/modules/supplier/` | Tedarikçi adapter'ları, sağlık izleme |
| Adapters | `app/suppliers/adapters/` | Paximum, RateHawk, vb. |
| Aggregator | `app/suppliers/aggregator/` | Çoklu tedarikçi araması |
| Health | `app/suppliers/health.py` | Circuit breaker, failover |
| Pricing | `app/suppliers/pricing.py` | Tedarikçi fiyatlandırması |

**Router'lar:** `modules/supplier/__init__.py (domain_router)`, `routers/suppliers.py`, `routers/supplier_*.py`, `suppliers/router.py`

### 1.5 CRM (Müşteri İlişkileri)
| Alan | Konum | Sorumluluk |
|------|--------|------------|
| CRM Domain | `app/modules/crm/` | Müşteri yönetimi, deal pipeline, görevler |
| Customers | `app/services/crm_customers.py` | Müşteri CRUD |
| Deals | `app/services/crm_deals.py` | Satış fırsatları |
| Tasks | `app/services/crm_tasks.py` | Görev takibi |
| Activities | `app/services/crm_activities.py` | Aktivite zaman çizelgesi |

**Router'lar:** `modules/crm/__init__.py (domain_router)`, `routers/crm_*.py`, `routers/customers.py`, `routers/leads.py`

---

## 2. Destekleyici Çekirdek (Operasyonel Derinlik)

Bazı müşteriler için operasyonun kritik parçası. Çekirdek kadar zorunlu değil ama derinlik sağlar.

### 2.1 Operations (Operasyon Merkezi)
| Alan | Konum | Sorumluluk |
|------|--------|------------|
| Operations Domain | `app/modules/operations/` | Vaka yönetimi, görev dağıtımı, olay takibi |
| Ops Cases | `app/services/ops_cases.py` | Müşteri destek vakaları |
| Ops Tasks | `app/services/ops_tasks.py` | Operasyonel görev listesi |
| Ops Incidents | `app/services/ops_incidents_service.py` | Olay/arıza yönetimi |

**Router'lar:** `modules/operations/__init__.py (domain_router)`, `routers/ops_*.py`

### 2.2 Inventory & Availability (Envanter Yönetimi)
| Alan | Konum | Sorumluluk |
|------|--------|------------|
| Inventory | `app/services/inventory.py` | Stok/oda yönetimi, allocasyon |
| Availability | `app/services/hotel_availability.py` | Müsaitlik kontrolü |
| Sync | `app/services/inventory_sync_service.py` | Tedarikçi envanter senkronizasyonu |
| Snapshots | `app/services/inventory_snapshot_service.py` | Envanter anlık görüntüleri |
| iCal | `app/services/ical_sync.py` | iCal takvim entegrasyonu |

**Router'lar:** `routers/inventory.py`, `routers/inventory/`, `routers/agency_availability.py`, `routers/agency_reservations.py`, `routers/admin_ical.py`

### 2.3 Pricing (Fiyatlandırma Motoru)
| Alan | Konum | Sorumluluk |
|------|--------|------------|
| Pricing Engine | `app/services/pricing_service.py` | Fiyat hesaplama motoru |
| Pricing Rules | `app/services/pricing_rules.py` | Kural tabanlı fiyatlandırma |
| Pricing Graph | `app/services/pricing_graph/` | Çok katmanlı fiyat grafiği |
| Quote Engine | `app/services/pricing_quote_engine.py` | Teklif oluşturma |
| Commission | `app/services/commission_service.py` | Komisyon hesaplama |

**Router'lar:** `routers/pricing.py`, `routers/pricing_rules.py`, `routers/pricing_quote.py`, `routers/pricing_engine_router.py`, `routers/admin_pricing*.py`

### 2.4 Reservation Control (PMS Operasyon Disiplini)
| Alan | Konum | Sorumluluk |
|------|--------|------------|
| Reservations | `app/services/reservations.py` | Rezervasyon kontrol katmanı |
| PMS Client | `app/services/pms_client.py` | PMS entegrasyonu |
| PMS Mapper | `app/services/pms_booking_mapper.py` | PMS veri dönüşümü |
| Sheets | `app/services/sheet_*.py` | Google Sheets entegrasyonu |

**Router'lar:** `routers/reservations.py`, `routers/agency_pms.py`, `routers/agency_pms_accounting.py`, `routers/agency_sheets.py`

---

## 3. Extension Modüller

Bağımsız çalışan, feature flag ile kontrol edilen genişleme modülleri.

### 3.1 B2B Network & Distribution
| Alan | Konum | Sorumluluk |
|------|--------|------------|
| B2B Domain | `app/modules/b2b/` | B2B ağı, dağıtım, exchange |
| B2B Bookings | `app/services/b2b_booking.py` | B2B rezervasyon akışı |
| B2B Pricing | `app/services/b2b_pricing.py` | B2B fiyatlandırma katmanı |
| B2B Commission | `app/services/b2b_commission.py` | B2B komisyon yönetimi |

**Feature Flag:** `b2b` | **Plan:** Enterprise, Trial

### 3.2 Marketplace & Storefront
| Alan | Konum | Sorumluluk |
|------|--------|------------|
| Marketplace | `routers/marketplace.py` | Pazar yeri |
| Public Search | `routers/public_search.py` | Halka açık arama |
| Public Checkout | `routers/public_checkout.py` | Online satış |
| Storefront | `routers/storefront.py` | Vitrin yönetimi |
| SEO | `routers/seo.py` | Arama motoru optimizasyonu |

### 3.3 Enterprise Governance
| Alan | Konum | Sorumluluk |
|------|--------|------------|
| Enterprise Domain | `app/modules/enterprise/` | Kurumsal yönetişim |
| Audit | `app/services/audit.py` | İşlem geçmişi |
| Approvals | `app/services/approval_service.py` | Onay akışları |
| GDPR | `app/services/gdpr_service.py` | Veri koruma |
| IP Whitelist | `routers/enterprise_ip_whitelist.py` | IP kısıtlama |

### 3.4 Partner Graph
| Alan | Konum | Sorumluluk |
|------|--------|------------|
| Partner Graph | `app/services/partner_graph_service.py` | İş ortağı ilişki ağı |
| Partner Auth | `app/services/partner_auth.py` | İş ortağı kimlik doğrulama |

### 3.5 Reporting & Analytics
| Alan | Konum | Sorumluluk |
|------|--------|------------|
| Reports | `app/services/report_output_service.py` | Rapor üretimi |
| Advanced Reports | `app/services/advanced_reports_service.py` | Gelişmiş raporlar |
| Dashboard | `routers/dashboard_enhanced.py` | Yönetim panosu |
| Analytics | `routers/admin_analytics.py` | Gelir analizi |

**Feature Flag:** `reports`

### 3.6 Diğer Extension'lar
| Modül | Konum | Sorumluluk |
|-------|--------|------------|
| Mobile BFF | `app/modules/mobile/` | Mobil uygulama backend |
| Webhook System | `app/services/webhook_service.py` | Harici entegrasyon webhook'ları |
| AI Assistant | `app/services/ai_assistant_service.py` | Yapay zeka asistanı |
| Campaigns | `routers/admin_campaigns.py` | Kampanya yönetimi |
| CMS Pages | `routers/admin_cms_pages.py` | İçerik yönetimi |
| Coupons | `routers/admin_coupons.py` | Kupon sistemi |
| SMS | `app/services/sms/` | SMS bildirim |
| Email | `app/services/email.py` | E-posta servisi |
| Notifications | `app/services/notification_service.py` | Bildirim merkezi |

---

## 4. Altyapı Katmanı

Platform genelinde kullanılan teknik bileşenler.

| Bileşen | Konum | Sorumluluk |
|---------|--------|------------|
| Event Bus | `app/infrastructure/event_bus.py` | Event publish/subscribe |
| Outbox Consumer | `app/infrastructure/outbox_consumer.py` | Transactional outbox |
| Circuit Breaker | `app/infrastructure/circuit_breaker.py` | Hata yönetimi |
| Rate Limiter | `app/infrastructure/rate_limiter.py` | İstek sınırlama |
| Redis Client | `app/infrastructure/redis_client.py` | Redis bağlantısı |
| Celery App | `app/infrastructure/celery_app.py` | Görev kuyruğu |

---

## 5. Router Sahiplik Tablosu

### Domain'e Taşınmış (modules/ altında)
| Domain | Modül Yolu | Router Sayısı |
|--------|-----------|---------------|
| Tenant | `modules/tenant/` | 1 |
| Auth | `modules/auth/` | Aggregate (domain_router) |
| Identity | `modules/identity/` | Aggregate (domain_router) |
| Booking | `modules/booking/` | 2 (commands + migration) |
| B2B | `modules/b2b/` | Aggregate (domain_router) |
| Supplier | `modules/supplier/` | Aggregate (domain_router) |
| Finance | `modules/finance/` | Aggregate (domain_router) |
| CRM | `modules/crm/` | Aggregate (domain_router) |
| Operations | `modules/operations/` | Aggregate (domain_router) |
| Enterprise | `modules/enterprise/` | Aggregate (domain_router) |
| System | `modules/system/` | Aggregate (domain_router) |

### Henüz Taşınmamış (routers/ altında)
| Grup | Yaklaşık Router Sayısı | Hedef Domain |
|------|----------------------|--------------|
| Admin Core | ~22 | identity, system |
| Inventory/Agency | ~15 | inventory (yeni modül) |
| Public/Storefront | ~13 | public (yeni modül) |
| Marketplace/Pricing | ~11 | pricing, marketplace |
| Reports | ~4 | reporting |
| Misc Specialized | ~18 | ilgili domain'lere dağıtım |
| Platform Layers | ~18 | system |
| Finance Ledger | ~4 | finance |
| Settlements | ~4 | finance |

**Toplam taşınmamış: ~109 router** → Router Consolidation Phase 2 hedefi

---

## 6. Veritabanı Koleksiyonları (Önemli)

| Koleksiyon | Domain | Açıklama |
|-----------|--------|----------|
| `organizations` | tenant | Acente/organizasyon kayıtları |
| `users` | identity | Kullanıcı hesapları |
| `bookings` | booking | Tüm rezervasyonlar |
| `invoices` | finance | Faturalar |
| `payments` | finance | Ödeme kayıtları |
| `settlement_ledger` | finance | Mutabakat defteri |
| `crm_customers` | crm | Müşteri kayıtları |
| `crm_deals` | crm | Satış fırsatları |
| `outbox_events` | infrastructure | Event outbox |
| `webhook_subscriptions` | webhook | Webhook abonelikleri |
| `webhook_deliveries` | webhook | Webhook teslim kayıtları |
| `ops_cases` | operations | Operasyon vakaları |
| `supplier_health` | supplier | Tedarikçi sağlık durumu |

---

*Son güncelleme: Şubat 2026*
*Kaynak: Codebase analizi + stratejik ürün konumlandırması*
