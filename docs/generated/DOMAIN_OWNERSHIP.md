# Domain Ownership Map
> Auto-generated: 2026-04-17 18:18 UTC
> Source: `app/modules/*/` structure and `__init__.py` imports

| Domain | Router Count | Has Dedicated Routers Dir | Docstring |
|--------|-------------|--------------------------|-----------|
| **auth** | 3 | Yes | Yes |
| **b2b** | 23 | Yes | Yes |
| **booking** | 11 | Yes | Yes |
| **crm** | 12 | Yes | Yes |
| **enterprise** | 9 | Yes | Yes |
| **finance** | 35 | Yes | Yes |
| **identity** | 21 | Yes | Yes |
| **inventory** | 30 | Yes | Yes |
| **mobile** | 0 | No | Yes |
| **operations** | 15 | Yes | Yes |
| **pricing** | 12 | Yes | Yes |
| **public** | 13 | Yes | Yes |
| **reporting** | 15 | Yes | Yes |
| **supplier** | 8 | Yes | Yes |
| **system** | 55 | Yes | Yes |
| **tenant** | 0 | No | Yes |

**Total**: 262 routers across 16 domains

## Domain Descriptions

- **auth**: Auth domain — aggregates all authentication/authorization routers.
- **b2b**: B2B domain — all B2B network, marketplace, exchange, partner routers.
- **booking**: Booking domain module — unified state machine, command-based transitions.
- **crm**: CRM domain — customers, deals, tasks, activities, notes, timeline, leads, inbox.
- **enterprise**: Enterprise domain — audit, approvals, health, schedules, governance, risk, policies.
- **finance**: Finance domain — billing, payments, settlements, invoicing, accounting, ledger.
- **identity**: Identity domain — users, agencies, RBAC, API keys, whitelabel, GDPR.
- **inventory**: Inventory domain — stock, availability, PMS, sheets, hotel management, search.
- **mobile**: Mobile domain — BFF (Backend for Frontend) for mobile clients.
- **operations**: Operations domain — ops cases, tasks, incidents, booking events, tickets.
- **pricing**: Pricing domain — pricing engine, rules, quotes, offers, marketplace.
- **public**: Public domain — storefront, public search, checkout, booking view, tours, SEO.
- **reporting**: Reporting domain — reports, advanced reports, exports, analytics, dashboard.
- **supplier**: Supplier domain — supplier adapters, aggregation, health, credentials, activation, ecosystem.
- **system**: System domain — health, infrastructure, monitoring, cache, admin system ops, platform layers.
- **tenant**: Tenant Isolation Module — enforces strict multi-tenant data boundaries.
