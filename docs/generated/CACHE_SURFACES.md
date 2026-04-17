# Cache Surfaces & TTL Strategy
> Auto-generated: 2026-04-17 14:54 UTC
> Source: `app/services/cache_ttl_config.py`, `app/infrastructure/event_contracts.py`

## TTL Matrix (Default)

| Category | Redis L1 (s) | MongoDB L2 (s) | Notes |
|----------|-------------|---------------|-------|
| `agency_list` | 300 | 900 | Medium, semi-static |
| `availability_check` | 45 | 120 | Short, near real-time |
| `booking_precheck` | 10 | 30 | Ultra-short, high freshness |
| `booking_status` | 15 | 60 | Ultra-short, high freshness |
| `cms_pages` | 600 | 1800 | Long, mostly static |
| `dashboard_charts` | 180 | 600 | Medium, semi-static |
| `dashboard_kpi` | 120 | 300 | Short, near real-time |
| `fx_rates` | 600 | 1800 | Long, mostly static |
| `health_check` | 30 | 60 | Ultra-short, high freshness |
| `hotel_detail` | 300 | 900 | Medium, semi-static |
| `price_revalidation` | 30 | 90 | Ultra-short, high freshness |
| `pricing_rules` | 300 | 900 | Medium, semi-static |
| `product_detail` | 300 | 900 | Medium, semi-static |
| `room_types` | 300 | 600 | Medium, semi-static |
| `search_results` | 60 | 180 | Short, near real-time |
| `supplier_city_index` | 600 | 1800 | Long, mostly static |
| `supplier_inventory` | 600 | 1800 | Long, mostly static |
| `supplier_registry` | 1800 | 3600 | Very long, rarely changes |
| `tenant_features` | 300 | 900 | Medium, semi-static |
| `warmup_data` | 300 | 600 | Medium, semi-static |

## Supplier-Specific Overrides

| Supplier | Category | Redis (s) | MongoDB (s) |
|----------|----------|-----------|------------|
| `hotelbeds` | `search_results` | 90 | 240 |
| `hotelbeds` | `supplier_inventory` | 600 | 1800 |
| `juniper` | `search_results` | 120 | 300 |
| `juniper` | `supplier_inventory` | 900 | 2700 |
| `paximum` | `search_results` | 120 | 300 |
| `paximum` | `supplier_inventory` | 900 | 2700 |
| `ratehawk` | `search_results` | 90 | 240 |
| `ratehawk` | `supplier_inventory` | 600 | 1800 |
| `tbo` | `search_results` | 60 | 180 |
| `tbo` | `supplier_inventory` | 600 | 1800 |
| `wtatil` | `search_results` | 180 | 600 |
| `wtatil` | `supplier_inventory` | 1200 | 3600 |

## Cache Invalidation Matrix

Shows which events invalidate which cache prefixes:

| Cache Prefix | Invalidated By |
|-------------|---------------|
| `dash_admin_today` | `booking.reservation.created`, `booking.reservation.updated`, `booking.reservation.cancelled`, `booking.reservation.confirmed`, `ops.incident.created` (+11 more) |
| `dash_agency_today` | `booking.reservation.created`, `booking.reservation.updated`, `booking.reservation.cancelled`, `booking.reservation.confirmed`, `finance.payment.received` (+2 more) |
| `dash_b2b_today` | `b2b.partner.activated`, `b2b.booking.created`, `b2b.offer.expired`, `dashboard.summary.invalidated` |
| `dash_hotel_today` | `booking.reservation.created`, `booking.reservation.updated`, `booking.reservation.cancelled`, `ops.checkin.completed`, `ops.checkout.completed` (+1 more) |
| `dash_kpi` | `booking.reservation.created`, `booking.reservation.cancelled`, `finance.payment.received`, `b2b.booking.created`, `dashboard.summary.invalidated` |

## Cache Policy Guidelines

### Cache Safely
- Dashboard summaries (eventual consistency acceptable)
- KPI aggregations
- Static metadata (hotel details, supplier registry)
- CMS pages

### Do NOT Cache Aggressively
- Booking status checks (financial accuracy)
- Payment verifications
- Real-time availability during booking flow
- Auth tokens / session data
