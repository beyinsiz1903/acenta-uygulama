# Router Map — Endpoint → Domain
> Auto-generated: 2026-03-26 09:08 UTC
> Source: `app/modules/*/` router registrations

## AUTH

| Import | Alias |
|--------|-------|
| `router` | `auth_core_router` |
| `router` | `password_reset_router` |
| `router` | `enterprise_2fa_router` |

## B2B

| Import | Alias |
|--------|-------|
| `router` | `b2b_router` |
| `router` | `b2b_bookings_router` |
| `router` | `b2b_bookings_list_router` |
| `router` | `b2b_cancel_router` |
| `router` | `b2b_quotes_router` |
| `router` | `b2b_hotels_search_router` |
| `router` | `b2b_portal_router` |
| `router` | `b2b_announcements_router` |
| `router` | `b2b_events_router` |
| `router` | `b2b_exchange_router` |
| `router` | `b2b_marketplace_booking_router` |
| `router` | `b2b_network_bookings_router` |
| `router` | `admin_b2b_agencies_router` |
| `router` | `admin_b2b_announcements_router` |
| `router` | `admin_b2b_discounts_router` |
| `router` | `admin_b2b_funnel_router` |
| `router` | `admin_b2b_marketplace_router` |
| `router` | `admin_b2b_pricing_router` |
| `router` | `admin_b2b_visibility_router` |
| `router` | `ops_b2b_router` |
| `router` | `partner_graph_router` |
| `router` | `partner_v1_router` |
| `router` | `admin_partners_router` |

## BOOKING

| Import | Alias |
|--------|-------|
| `router` | `booking_commands_router` |
| `router` | `booking_migration_router` |
| `router` | `bookings_legacy_router` |
| `router` | `booking_outcomes_router` |
| `router` | `unified_booking_router` |
| `router` | `cancel_reasons_router` |
| `router` | `vouchers_router` |
| `router` | `voucher_router` |
| `router` | `matches_router` |
| `router` | `match_alerts_router` |
| `router` | `match_unblock_router` |

## CRM

| Import | Alias |
|--------|-------|
| `router` | `crm_customers_router` |
| `router` | `crm_deals_router` |
| `router` | `crm_tasks_router` |
| `router` | `crm_activities_router` |
| `router` | `crm_notes_router` |
| `router` | `crm_events_router` |
| `router` | `crm_timeline_router` |
| `router` | `crm_customer_inbox_router` |
| `router` | `customers_router` |
| `router` | `leads_router` |
| `router` | `inbox_router` |
| `router` | `inbox_v2_router` |

## ENTERPRISE

| Import | Alias |
|--------|-------|
| `router` | `enterprise_approvals_router` |
| `router` | `enterprise_audit_router` |
| `router` | `enterprise_health_router` |
| `router` | `enterprise_schedules_router` |
| `router` | `audit_router` |
| `router` | `governance_router` |
| `router` | `risk_snapshots_router` |
| `router` | `action_policies_router` |
| `router` | `approval_tasks_router` |

## FINANCE

| Import | Alias |
|--------|-------|
| `router` | `finance_router` |
| `router` | `admin_billing_router` |
| `router` | `admin_settlements_router` |
| `router` | `admin_statements_router` |
| `router` | `admin_parasut_router` |
| `router` | `admin_accounting_router` |
| `router` | `billing_checkout_router` |
| `router` | `billing_lifecycle_router` |
| `router` | `billing_webhooks_router` |
| `router` | `payments_router` |
| `router` | `payments_stripe_router` |
| `router` | `efatura_router` |
| `router` | `invoice_engine_router` |
| `router` | `reconciliation_router` |
| `router` | `multicurrency_router` |
| `router` | `accounting_sync_router` |
| `router` | `accounting_providers_router` |
| `router` | `commission_rules_router` |
| `router` | `ops_finance_router` |
| `router` | `ops_finance_accounts_router` |
| `router` | `ops_finance_refunds_router` |
| `router` | `ops_finance_settlements_router` |
| `router` | `ops_finance_documents_router` |
| `router` | `ops_finance_suppliers_router` |
| `router` | `ops_click_to_pay_router` |
| `router` | `public_click_to_pay_router` |
| `router` | `order_router` |

## IDENTITY

| Import | Alias |
|--------|-------|
| `router` | `admin_agencies_router` |
| `router` | `admin_agency_users_router` |
| `all_users_router` | `admin_all_users_router` |
| `router` | `admin_api_keys_router` |
| `router` | `admin_audit_logs_router` |
| `router` | `admin_whitelabel_router` |
| `router` | `enterprise_rbac_router` |
| `router` | `enterprise_ip_whitelist_router` |
| `router` | `enterprise_whitelabel_router` |
| `router` | `enterprise_export_router` |
| `router` | `gdpr_router` |
| `router` | `saas_tenants_router` |
| `router` | `tenant_features_router` |
| `router` | `admin_tenant_features_router` |
| `router` | `tenant_health_router` |
| `router` | `settings_router` |
| `router` | `agency_profile_router` |
| `router` | `agency_contracts_router` |
| `router` | `onboarding_router` |

## INVENTORY

| Import | Alias |
|--------|-------|
| `router` | `inventory_shares_router` |
| `router` | `inventory_snapshots_api_router` |
| `router` | `products_router` |
| `router` | `agency_hotels_router` |
| `router` | `hotel_integrations_router` |
| `router` | `rateplans_router` |
| `router` | `search_router` |
| `router` | `reservations_router` |
| `router` | `agency_availability_router` |
| `router` | `agency_reservations_router` |
| `router` | `agency_pms_router` |
| `router` | `agency_pms_accounting_router` |
| `router` | `agency_sheets_router` |
| `router` | `agency_writeback_router` |
| `router` | `agency_booking_router` |
| `router` | `admin_hotels_router` |
| `router` | `admin_ical_router` |
| `router` | `admin_sheets_router` |
| `router` | `admin_catalog_router` |
| `router` | `admin_tours_router` |

## MOBILE

| Import | Alias |
|--------|-------|
| `router` | `router` |

## OPERATIONS

| Import | Alias |
|--------|-------|
| `router` | `ops_cases_router` |
| `router` | `ops_tasks_router` |
| `router` | `ops_incidents_router` |
| `router` | `ops_booking_events_router` |
| `router` | `tickets_router` |

## PRICING

| Import | Alias |
|--------|-------|
| `router` | `pricing_router` |
| `router` | `pricing_rules_router` |
| `router` | `pricing_quote_router` |
| `router` | `pricing_engine_router` |
| `router` | `admin_pricing_router` |
| `router` | `admin_pricing_incidents_router` |
| `router` | `admin_pricing_trace_router` |
| `router` | `offers_router` |
| `router` | `offers_booking_router` |
| `router` | `quotes_router` |
| `router` | `marketplace_router` |
| `router` | `marketplace_supplier_mapping_router` |

## PUBLIC

| Import | Alias |
|--------|-------|
| `router` | `public_bookings_router` |
| `router` | `public_campaigns_router` |
| `router` | `public_checkout_router` |
| `router` | `public_cms_pages_router` |
| `router` | `public_my_booking_router` |
| `router` | `public_partners_router` |
| `router` | `public_search_router` |
| `router` | `public_tours_router` |
| `router` | `storefront_router` |
| `router` | `seo_router` |
| `router` | `tours_browse_router` |
| `router` | `web_booking_router` |
| `router` | `web_catalog_router` |

## REPORTING

| Import | Alias |
|--------|-------|
| `router` | `reports_router` |
| `router` | `advanced_reports_router` |
| `router` | `exports_router` |
| `public_router` | `public_exports_router` |
| `router` | `admin_analytics_router` |
| `router` | `admin_reporting_router` |
| `router` | `admin_reports_router` |
| `router` | `admin_funnel_router` |
| `router` | `admin_insights_router` |
| `router` | `dashboard_enhanced_router` |
| `router` | `dashboard_agency_router` |
| `router` | `dashboard_admin_router` |
| `router` | `dashboard_hotel_router` |
| `router` | `dashboard_b2b_router` |
| `router` | `revenue_router` |

## SUPPLIER

| Import | Alias |
|--------|-------|
| `router` | `suppliers_router` |
| `router` | `paximum_router` |
| `router` | `admin_supplier_health_router` |
| `router` | `ops_supplier_operations_router` |
| `router` | `supplier_activation_router` |
| `router` | `supplier_credentials_router` |
| `router` | `supplier_aggregator_router` |
| `router` | `supplier_ecosystem_router` |

## SYSTEM

| Import | Alias |
|--------|-------|
| `router` | `health_router` |
| `router` | `health_dashboard_router` |
| `router` | `cache_health_router` |
| `router` | `cache_management_router` |
| `router` | `infrastructure_router` |
| `router` | `distributed_locks_router` |
| `router` | `metrics_router` |
| `router` | `notifications_router` |
| `router` | `sms_notifications_router` |
| `router` | `reliability_router` |
| `router` | `admin_system_backups_router` |
| `router` | `admin_system_integrity_router` |
| `router` | `admin_system_metrics_router` |
| `router` | `admin_system_errors_router` |
| `router` | `admin_system_uptime_router` |
| `router` | `admin_system_incidents_router` |
| `router` | `admin_maintenance_router` |
| `router` | `admin_system_preflight_router` |
| `router` | `admin_system_runbook_router` |
| `router` | `admin_system_perf_router` |
| `router` | `system_product_mode_router` |
| `router` | `admin_product_mode_router` |
| `router` | `production_router` |
| `router` | `hardening_router` |
| `router` | `worker_infra_router` |
| `router` | `stress_test_router` |
| `router` | `pilot_launch_router` |
| `router` | `intelligence_router` |
| `router` | `scalability_router` |
| `router` | `operations_router` |
| ... | 25 more |

