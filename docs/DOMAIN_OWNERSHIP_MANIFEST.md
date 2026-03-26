# Domain Ownership Manifest — Phase 2 Complete

> Bu doküman, tüm router'ların domain sahipliklerini gösterir.
> Her satır: `router dosyası → domain owner → prefix pattern`

## Durum: ✅ TAMAMLANDI (Faz 2)

Önceki durum: ~109 router "REMAINING" bölümünde, domain'siz
Şimdiki durum: 0 router REMAINING'de, 16 domain modülü aktif

---

## Domain 0: Tenant (Security Boundary)
| Router Dosyası | Prefix | Modül |
|---|---|---|
| `modules/tenant/router.py` | (built-in) | `modules/tenant/` |
| `routers/admin_orphan_migration.py` | (built-in) | registry (cross-domain) |
| `routers/admin_outbox.py` | /api | registry (cross-domain) |
| `routers/webhooks.py` | /api | registry (webhook) |
| `routers/admin_webhooks.py` | /api | registry (webhook) |

## Domain 1: Booking
| Router Dosyası | Prefix | Modül |
|---|---|---|
| `modules/booking/router.py` | /api + /bookings | `modules/booking/` |
| `modules/booking/migration_router.py` | /api + /admin/booking-migration | `modules/booking/` |
| `routers/bookings.py` | /api + /bookings | `modules/booking/` |
| `routers/booking_outcomes.py` | /api + /admin/booking-outcomes | `modules/booking/` |
| `routers/unified_booking_router.py` | /api/unified-booking | `modules/booking/` |
| `routers/cancel_reasons.py` | /api/reference | `modules/booking/` |
| `routers/vouchers.py` | /api + (ops/bookings/...) | `modules/booking/` |
| `routers/voucher.py` | /api/voucher | `modules/booking/` |
| `routers/matches.py` | /api/admin/matches | `modules/booking/` |
| `routers/match_alerts.py` | /api/admin/match-alerts | `modules/booking/` |
| `routers/match_unblock.py` | /api/admin/matches | `modules/booking/` |

## Domain 2: Auth
| Router Dosyası | Prefix | Modül |
|---|---|---|
| `routers/auth.py` | (built-in) | `modules/auth/` |
| `routers/auth_password_reset.py` | (built-in) | `modules/auth/` |
| `routers/enterprise_2fa.py` | (built-in) | `modules/auth/` |

## Domain 3: Identity
| Router Dosyası | Prefix | Modül |
|---|---|---|
| `routers/admin_agencies.py` | (built-in) | `modules/identity/` |
| `routers/admin_agency_users.py` | (built-in) | `modules/identity/` |
| `routers/admin_api_keys.py` | (built-in) | `modules/identity/` |
| `routers/admin_audit_logs.py` | (built-in) | `modules/identity/` |
| `routers/admin_whitelabel.py` | (built-in) | `modules/identity/` |
| `routers/enterprise_rbac.py` | (built-in) | `modules/identity/` |
| `routers/enterprise_ip_whitelist.py` | (built-in) | `modules/identity/` |
| `routers/enterprise_whitelabel.py` | (built-in) | `modules/identity/` |
| `routers/enterprise_export.py` | (built-in) | `modules/identity/` |
| `routers/gdpr.py` | (built-in) | `modules/identity/` |
| `routers/saas_tenants.py` | (built-in) | `modules/identity/` |
| `routers/tenant_features.py` | (built-in) | `modules/identity/` |
| `routers/admin_tenant_features.py` | (built-in) | `modules/identity/` |
| `routers/tenant_health.py` | (built-in) | `modules/identity/` |
| `routers/settings.py` | (built-in) | `modules/identity/` |
| `routers/agency_profile.py` | (built-in) | `modules/identity/` |
| `routers/agency_contracts.py` | (built-in) | `modules/identity/` |
| `routers/onboarding.py` | (built-in) | `modules/identity/` |

## Domain 4: B2B
| Router Dosyası | Prefix | Modül |
|---|---|---|
| `routers/b2b.py` | (built-in) | `modules/b2b/` |
| `routers/b2b_bookings.py` | (built-in) | `modules/b2b/` |
| `routers/b2b_bookings_list.py` | (built-in) | `modules/b2b/` |
| `routers/b2b_cancel.py` | (built-in) | `modules/b2b/` |
| `routers/b2b_quotes.py` | (built-in) | `modules/b2b/` |
| `routers/b2b_hotels_search.py` | (built-in) | `modules/b2b/` |
| `routers/b2b_portal.py` | (built-in) | `modules/b2b/` |
| `routers/b2b_announcements.py` | (built-in) | `modules/b2b/` |
| `routers/b2b_events.py` | (built-in) | `modules/b2b/` |
| `routers/b2b_exchange.py` | (built-in) | `modules/b2b/` |
| `routers/b2b_marketplace_booking.py` | /api | `modules/b2b/` |
| `routers/b2b_network_bookings.py` | (built-in) | `modules/b2b/` |
| `routers/admin_b2b_*.py` (7 files) | (built-in) | `modules/b2b/` |
| `routers/ops_b2b.py` | (built-in) | `modules/b2b/` |
| `routers/partner_graph.py` | /api/partner-graph | `modules/b2b/` |
| `routers/partner_v1.py` | /api/partner | `modules/b2b/` |
| `routers/admin_partners.py` | (built-in) | `modules/b2b/` |

## Domain 5: Supplier
| Router Dosyası | Prefix | Modül |
|---|---|---|
| `routers/suppliers.py` | /api + /suppliers | `modules/supplier/` |
| `routers/paximum_router.py` | /api + /paximum | `modules/supplier/` |
| `routers/admin_supplier_health.py` | (built-in) | `modules/supplier/` |
| `routers/ops_supplier_operations.py` | (built-in) | `modules/supplier/` |
| `routers/supplier_activation.py` | /api/supplier-activation | `modules/supplier/` |
| `routers/supplier_credentials_router.py` | /api/supplier-credentials | `modules/supplier/` |
| `routers/supplier_aggregator_router.py` | /api/supplier-aggregator | `modules/supplier/` |
| `suppliers/router.py` | /api/suppliers/ecosystem | `modules/supplier/` |

## Domain 6: Finance
| Router Dosyası | Prefix | Modül |
|---|---|---|
| `routers/finance.py` | /api + /finance | `modules/finance/` |
| `routers/admin_billing.py` | (built-in) | `modules/finance/` |
| `routers/admin_settlements.py` | (built-in) | `modules/finance/` |
| `routers/admin_statements.py` | (built-in) | `modules/finance/` |
| `routers/admin_parasut.py` | (built-in) | `modules/finance/` |
| `routers/admin_accounting.py` | /api/admin/accounting | `modules/finance/` |
| `routers/billing_*.py` (3 files) | (built-in) | `modules/finance/` |
| `routers/payments.py` | /api + /payments | `modules/finance/` |
| `routers/payments_stripe.py` | /api + /payments | `modules/finance/` |
| `routers/efatura.py` | (built-in) | `modules/finance/` |
| `routers/invoice_engine.py` | (built-in) | `modules/finance/` |
| `routers/reconciliation.py` | (built-in) | `modules/finance/` |
| `routers/multicurrency.py` | (built-in) | `modules/finance/` |
| `routers/accounting_*.py` (2 files) | (built-in) | `modules/finance/` |
| `routers/commission_rules.py` | (built-in) | `modules/finance/` |
| `routers/ops_finance*.py` (6 files) | (built-in) | `modules/finance/` |
| `routers/ops_click_to_pay.py` | (built-in) | `modules/finance/` |
| `routers/public_click_to_pay.py` | (built-in) | `modules/finance/` |
| `routers/finance_ledger.py` (4 routers) | /api/finance/* | `modules/finance/` |
| `routers/settlements.py` (3 routers) | /api/agency, /api/hotel, /api/settlements | `modules/finance/` |
| `routers/order_router.py` | /api/orders | `modules/finance/` |

## Domain 7: CRM
| Router Dosyası | Prefix | Modül |
|---|---|---|
| `routers/crm_*.py` (7 files) | (built-in) | `modules/crm/` |
| `routers/customers.py` | (built-in) | `modules/crm/` |
| `routers/leads.py` | (built-in) | `modules/crm/` |
| `routers/inbox.py` | /inbox | `modules/crm/` |
| `routers/inbox_v2.py` | /api/inbox | `modules/crm/` |

## Domain 8: Operations
| Router Dosyası | Prefix | Modül |
|---|---|---|
| `routers/ops_cases.py` | (built-in) | `modules/operations/` |
| `routers/ops_tasks.py` | (built-in) | `modules/operations/` |
| `routers/ops_incidents.py` | (built-in) | `modules/operations/` |
| `routers/ops_booking_events.py` | /api | `modules/operations/` |
| `routers/tickets.py` | /api/tickets | `modules/operations/` |

## Domain 9: Enterprise
| Router Dosyası | Prefix | Modül |
|---|---|---|
| `routers/enterprise_approvals.py` | (built-in) | `modules/enterprise/` |
| `routers/enterprise_audit.py` | (built-in) | `modules/enterprise/` |
| `routers/enterprise_health.py` | (built-in) | `modules/enterprise/` |
| `routers/enterprise_schedules.py` | (built-in) | `modules/enterprise/` |
| `routers/audit.py` | (built-in) | `modules/enterprise/` |
| `routers/governance.py` | (built-in) | `modules/enterprise/` |
| `routers/risk_snapshots.py` | /api/admin/risk-snapshots | `modules/enterprise/` |
| `routers/action_policies.py` | /api/admin/action-policies | `modules/enterprise/` |
| `routers/approval_tasks.py` | /api/admin/approval-tasks | `modules/enterprise/` |

## Domain 10: System
| Router Dosyası | Prefix | Modül |
|---|---|---|
| `routers/health.py` | (built-in) | `modules/system/` |
| `routers/health_dashboard.py` | (built-in) | `modules/system/` |
| `routers/cache_*.py` (2 files) | (built-in) | `modules/system/` |
| `routers/infrastructure.py` | (built-in) | `modules/system/` |
| `routers/distributed_locks.py` | (built-in) | `modules/system/` |
| `routers/metrics.py` | (built-in) | `modules/system/` |
| `routers/admin_system_*.py` (8 files) | (built-in) | `modules/system/` |
| `routers/admin_maintenance.py` | (built-in) | `modules/system/` |
| `routers/system_product_mode.py` | (built-in) | `modules/system/` |
| `routers/admin_product_mode.py` | (built-in) | `modules/system/` |
| `routers/notifications.py` | (built-in) | `modules/system/` |
| `routers/sms_notifications.py` | (built-in) | `modules/system/` |
| `routers/reliability.py` | (built-in) | `modules/system/` |
| `routers/production.py` | /api/production | `modules/system/` |
| `routers/hardening.py` | /api/hardening | `modules/system/` |
| `routers/worker_infrastructure.py` | /api/workers | `modules/system/` |
| `routers/stress_test_router.py` | /api/stress-test | `modules/system/` |
| `routers/pilot_launch_router.py` | /api/pilot | `modules/system/` |
| `routers/intelligence_router.py` | /api/intelligence | `modules/system/` |
| `routers/scalability_router.py` | /api/scalability | `modules/system/` |
| `routers/operations_router.py` | /api/operations | `modules/system/` |
| `routers/market_launch_router.py` | /api/market-launch | `modules/system/` |
| `routers/growth_engine_router.py` | /api/growth | `modules/system/` |
| `routers/pilot_onboarding_router.py` | /api/pilot/onboarding | `modules/system/` |
| `routers/gtm_demo_seed.py` | /api/admin/demo | `modules/system/` |
| `routers/activation_checklist.py` | /api/activation | `modules/system/` |
| `routers/admin.py` | (built-in) | `modules/system/` |
| `routers/admin_demo_guide.py` | (built-in) | `modules/system/` |
| `routers/admin_import.py` | (built-in) | `modules/system/` |
| `routers/admin_integrations.py` | (built-in) | `modules/system/` |
| `routers/admin_jobs.py` | (built-in) | `modules/system/` |
| `routers/admin_links.py` | (built-in) | `modules/system/` |
| `routers/admin_metrics.py` | (built-in) | `modules/system/` |
| `routers/admin_demo_seed.py` | /api/admin/demo | `modules/system/` |
| `routers/dev_saas.py` | /api/dev | `modules/system/` |
| `routers/demo_scale_ui_proof.py` | (built-in) | `modules/system/` |
| `routers/integrator_management.py` | /api/integrators | `modules/system/` |
| `routers/theme.py` | (built-in) | `modules/system/` |
| `routers/upgrade_requests.py` | (built-in) | `modules/system/` |
| `routers/activity_timeline_router.py` | /api/activity-timeline | `modules/system/` |
| `routers/config_versions_router.py` | /api/config-versions | `modules/system/` |
| `routers/admin_campaigns.py` | /api/admin/campaigns | `modules/system/` |
| `routers/admin_cms_pages.py` | /api/admin/cms/pages | `modules/system/` |
| `routers/admin_coupons.py` | /api/admin/coupons | `modules/system/` |
| `routers/webpos.py` | /api/webpos | `modules/system/` |
| `routers/ai_assistant.py` | /api/ai-assistant | `modules/system/` |

## Domain 11: Inventory
| Router Dosyası | Prefix | Modül |
|---|---|---|
| `routers/inventory_shares.py` | /api/inventory-shares | `modules/inventory/` |
| `routers/inventory_snapshots_api.py` | /api/inventory | `modules/inventory/` |
| `routers/products.py` | /api + /products | `modules/inventory/` |
| `routers/hotel.py` | /api/hotel | `modules/inventory/` |
| `routers/hotel_integrations.py` | /api/hotel/integrations | `modules/inventory/` |
| `routers/rateplans.py` | /api/rateplans | `modules/inventory/` |
| `routers/search.py` | /api + (search) | `modules/inventory/` |
| `routers/reservations.py` | /api + /reservations | `modules/inventory/` |
| `routers/agency_availability.py` | /api/agency/availability | `modules/inventory/` |
| `routers/agency_reservations.py` | /api/agency/reservations | `modules/inventory/` |
| `routers/agency_pms.py` | /api/agency/pms | `modules/inventory/` |
| `routers/agency_pms_accounting.py` | /api/agency/pms/accounting | `modules/inventory/` |
| `routers/agency_sheets.py` | /api/agency/sheets | `modules/inventory/` |
| `routers/agency_writeback.py` | /api/agency/writeback | `modules/inventory/` |
| `routers/agency_booking.py` | /api/agency/bookings | `modules/inventory/` |
| `routers/admin_hotels.py` | /api/admin/hotels | `modules/inventory/` |
| `routers/admin_ical.py` | /api/admin/ical | `modules/inventory/` |
| `routers/admin_sheets.py` | /api/admin/sheets | `modules/inventory/` |
| `routers/admin_catalog.py` | /api/admin/catalog | `modules/inventory/` |
| `routers/admin_tours.py` | /api/admin/tours | `modules/inventory/` |
| `routers/inventory/sync_router.py` | (built-in) | `modules/inventory/` |
| `routers/inventory/booking_router.py` | (built-in) | `modules/inventory/` |
| `routers/inventory/diagnostics_router.py` | (built-in) | `modules/inventory/` |
| `routers/inventory/onboarding_router.py` | (built-in) | `modules/inventory/` |

## Domain 12: Pricing
| Router Dosyası | Prefix | Modül |
|---|---|---|
| `routers/pricing.py` | /api + /pricing | `modules/pricing/` |
| `routers/pricing_rules.py` | /api + /pricing/rules | `modules/pricing/` |
| `routers/pricing_quote.py` | /api/pricing | `modules/pricing/` |
| `routers/pricing_engine_router.py` | /api/pricing-engine | `modules/pricing/` |
| `routers/admin_pricing.py` | /api/admin/pricing | `modules/pricing/` |
| `routers/admin_pricing_incidents.py` | /api/admin/pricing/incidents | `modules/pricing/` |
| `routers/admin_pricing_trace.py` | /api/admin/pricing/graph | `modules/pricing/` |
| `routers/offers.py` | /api/offers | `modules/pricing/` |
| `routers/offers_booking.py` | /api/bookings (offers) | `modules/pricing/` |
| `routers/quotes.py` | /api/quotes | `modules/pricing/` |
| `routers/marketplace.py` | /api + /marketplace | `modules/pricing/` |
| `routers/marketplace_supplier_mapping.py` | /api + /marketplace | `modules/pricing/` |

## Domain 13: Public
| Router Dosyası | Prefix | Modül |
|---|---|---|
| `routers/public_bookings.py` | (built-in) | `modules/public/` |
| `routers/public_campaigns.py` | (built-in) | `modules/public/` |
| `routers/public_checkout.py` | (built-in) | `modules/public/` |
| `routers/public_cms_pages.py` | (built-in) | `modules/public/` |
| `routers/public_my_booking.py` | (built-in) | `modules/public/` |
| `routers/public_partners.py` | (built-in) | `modules/public/` |
| `routers/public_search.py` | (built-in) | `modules/public/` |
| `routers/public_tours.py` | (built-in) | `modules/public/` |
| `routers/storefront.py` | (built-in) | `modules/public/` |
| `routers/seo.py` | (built-in) | `modules/public/` |
| `routers/tours_browse.py` | (built-in) | `modules/public/` |
| `routers/web_booking.py` | /api | `modules/public/` |
| `routers/web_catalog.py` | /api | `modules/public/` |

## Domain 14: Reporting
| Router Dosyası | Prefix | Modül |
|---|---|---|
| `routers/reports.py` | /api/reports | `modules/reporting/` |
| `routers/advanced_reports.py` | /api/reports | `modules/reporting/` |
| `routers/exports.py` (2 routers) | /api/admin/exports, /api/exports | `modules/reporting/` |
| `routers/admin_analytics.py` | (built-in) | `modules/reporting/` |
| `routers/admin_reporting.py` | (built-in) | `modules/reporting/` |
| `routers/admin_reports.py` | (built-in) | `modules/reporting/` |
| `routers/admin_funnel.py` | (built-in) | `modules/reporting/` |
| `routers/admin_insights.py` | (built-in) | `modules/reporting/` |
| `routers/dashboard_enhanced.py` | /api/dashboard | `modules/reporting/` |
| `routers/revenue_router.py` | /api/revenue | `modules/reporting/` |

---

*Son güncelleme: Şubat 2026 — Faz 2 tamamlandı*
*Toplam domain: 16 | Toplam router: ~160+ | REMAINING: 0*
