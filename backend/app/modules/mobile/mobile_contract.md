# Mobile BFF Contract — PR-5A

## Base Path
- `/api/v1/mobile`

## Auth
- Mobile app can continue using existing `/api/auth/login` and `/api/auth/refresh` during PR-5A.
- This phase adds mobile-facing read/projection endpoints behind bearer auth.

## Endpoints

### `GET /auth/me`
Returns a mobile-safe authenticated user payload.

Response fields:
- `id`
- `email`
- `name`
- `roles[]`
- `organization_id`
- `tenant_id`
- `current_session_id`
- `allowed_tenant_ids[]`

### `GET /dashboard/summary`
Returns mobile dashboard KPI summary.

Response fields:
- `bookings_today`
- `bookings_month`
- `revenue_month`
- `currency`

### `GET /bookings`
Returns mobile booking list.

Query params:
- `limit` (default `20`)
- `status_filter` (optional)

Response fields:
- `total`
- `items[]`

Each booking item:
- `id`
- `status`
- `total_price`
- `currency`
- `customer_name`
- `hotel_name`
- `check_in`
- `check_out`
- `source`
- `created_at`
- `updated_at`

### `GET /bookings/{id}`
Returns mobile booking detail.

Extra fields over summary:
- `tenant_id`
- `agency_id`
- `hotel_id`
- `booking_ref`
- `offer_ref`
- `notes`

### `POST /bookings`
Creates a tenant-scoped mobile booking draft by delegating to existing booking domain service.

Request fields:
- `amount`
- `currency`
- `customer_id`
- `customer_name`
- `guest_name`
- `hotel_id`
- `hotel_name`
- `supplier_id`
- `booking_ref`
- `offer_ref`
- `check_in`
- `check_out`
- `notes`
- `pricing`
- `occupancy`
- `source` (defaults to `mobile`)

### `GET /reports/summary`
Returns compact mobile reporting payload.

Response fields:
- `total_bookings`
- `total_revenue`
- `currency`
- `status_breakdown[]`
- `daily_sales[]`

## Security / Contract Rules
- Mongo `_id` must never leak to mobile responses.
- Mobile DTOs are separate from web DTOs.
- Mobile BFF is a projection/orchestration layer, not a business-logic owner.
- Tenant scoping uses existing request context and membership rules.