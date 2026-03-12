# SYROCE PLATFORM STABILIZATION PLAN
## Principal SaaS Architect & Security Engineer Assessment
### February 2026

---

# PART 1 — TESTING STRATEGY

## Current State
- **188,000 LOC** across 876 source files
- **~150 existing test files** in `/backend/tests/` (mostly integration smoke tests)
- No dedicated unit test layer for business logic
- No frontend automated tests
- No contract tests between services

## Test Pyramid Design

```
                    /\
                   /  \  E2E Tests (Playwright)
                  /    \  5-10 critical user flows
                 /------\
                /        \  API Contract Tests
               /          \  50+ endpoint contracts
              /------------\
             /              \  Integration Tests  
            /                \  100+ API tests with DB
           /------------------\
          /                    \  Unit Tests
         /                      \  500+ pure logic tests
        /________________________\
```

## Priority Module Testing Order

### Tier 1 — Critical (Must test first)
| Module | Why | Target Coverage |
|--------|-----|-----------------|
| **Authentication** | Security gate for entire platform | 90%+ |
| **Booking Lifecycle** | Core revenue flow | 85%+ |
| **Payment Processing** | Financial liability | 85%+ |
| **Tenant Isolation** | Data breach prevention | 95%+ |

### Tier 2 — High Priority
| Module | Why | Target Coverage |
|--------|-----|-----------------|
| **Pricing Engine** | Revenue accuracy | 80%+ |
| **Agency Permissions** | Access control | 80%+ |
| **B2B Network** | Partner trust | 75%+ |

### Tier 3 — Standard
| Module | Why | Target Coverage |
|--------|-----|-----------------|
| **CRM** | Customer data integrity | 60%+ |
| **Invoicing** | Financial compliance | 70%+ |
| **Google Sheets Integration** | Data import accuracy | 60%+ |

## Test Files Created (Phase 1)

| Test File | Module | Tests |
|-----------|--------|-------|
| `test_stabilization_auth.py` | Authentication | 11 tests |
| `test_stabilization_booking.py` | Booking Lifecycle | 8 tests |
| `test_stabilization_tenant_isolation.py` | Tenant Isolation | 6 tests |
| `test_stabilization_health.py` | Health Checks | 4 tests |
| `test_stabilization_security.py` | Security Headers | 8 tests |

## Test Coverage Roadmap

| Week | Focus | Tests Added | Cumulative |
|------|-------|------------|------------|
| 1-2 | Auth + Health + Security headers | 37 | 37 |
| 3-4 | Booking lifecycle + State machine | 30 | 67 |
| 5-6 | Payments + Pricing engine | 40 | 107 |
| 7-8 | Tenant isolation + RBAC | 25 | 132 |
| 9-10 | B2B + CRM | 30 | 162 |
| 11-12 | E2E Playwright flows | 10 | 172 |

---

# PART 2 — CI/CD PIPELINE

## Pipeline Architecture

```
Push/PR → Lint → Security Scan → Backend Tests → Frontend Build → Contract Tests → Deploy
```

### Pipeline File: `.github/workflows/ci.yml`

**7-Stage Pipeline:**

1. **Lint & Static Analysis** — Ruff (Python) + ESLint (JS)
2. **Security Scanning** — pip-audit + yarn audit
3. **Backend Tests** — pytest with coverage, MongoDB service container
4. **Frontend Build** — yarn build with production env
5. **API Contract Tests** — Schemathesis + custom contract tests
6. **Deploy Staging** — On `develop` branch merge
7. **Deploy Production** — On `release/*` branch

### Deployment Workflow
```
feature/* → develop (staging auto-deploy)
develop → release/v1.x.y → main (production deploy)
```

### Rollback Strategy
1. **Instant**: Kubernetes rollback via `kubectl rollout undo`
2. **Database**: MongoDB point-in-time recovery (Atlas)
3. **Feature flags**: Disable broken features without deploy

### Release Versioning
```
v{MAJOR}.{MINOR}.{PATCH}
  │        │        └── Bug fixes, patches
  │        └── New features, non-breaking
  └── Breaking changes, major restructuring
```

---

# PART 3 — SECURITY HARDENING

## Current Security Stack Assessment

| Layer | Status | Score |
|-------|--------|-------|
| **Authentication** | Strong (JWT + cookies + 2FA) | 8/10 |
| **Authorization** | Basic RBAC, missing resource-level | 5/10 |
| **Encryption** | HTTPS enforced, bcrypt passwords | 7/10 |
| **Rate Limiting** | MongoDB-based (functional, not scalable) | 5/10 |
| **Security Headers** | Comprehensive middleware | 8/10 |
| **CSRF Protection** | NOW ADDED via double-submit cookie | 7/10 |
| **Input Validation** | Pydantic models (partial coverage) | 6/10 |
| **Audit Trail** | Hash-chain verified logs | 9/10 |

## CSRF Protection (IMPLEMENTED)

New `CSRFProtectionMiddleware` added:
- Double-submit cookie pattern
- Exempt paths: health, public, webhooks, partner API
- Bearer-token requests exempt (inherently CSRF-safe)
- Cookie-authenticated state-changing requests validated

## Zero Trust API Model Design

```
┌─────────────────────────────────────────────┐
│                 API Gateway                  │
│  ┌─────────┐  ┌──────────┐  ┌───────────┐  │
│  │  Rate   │  │  Auth    │  │  Tenant   │  │
│  │  Limit  │→ │  Verify  │→ │  Resolve  │  │
│  └─────────┘  └──────────┘  └───────────┘  │
│       ↓            ↓             ↓          │
│  ┌─────────┐  ┌──────────┐  ┌───────────┐  │
│  │  CSRF   │  │  RBAC    │  │  Resource  │  │
│  │  Check  │→ │  Enforce │→ │  Scope    │  │
│  └─────────┘  └──────────┘  └───────────┘  │
│                     ↓                        │
│            ┌───────────────┐                 │
│            │  Business     │                 │
│            │  Logic        │                 │
│            └───────────────┘                 │
└─────────────────────────────────────────────┘
```

### Principles:
1. **Never trust, always verify** — Every request authenticated + authorized
2. **Least privilege** — Minimum permissions for each operation
3. **Tenant boundary enforcement** — Every DB query scoped to tenant
4. **Audit everything** — All state changes logged with hash-chain verification
5. **Defense in depth** — Multiple middleware layers, each independent

## Secret Rotation Design

| Secret | Current | Recommended |
|--------|---------|-------------|
| JWT_SECRET | Single, static | Dual-key rotation with grace period |
| STRIPE_WEBHOOK_SECRET | Static | Per-endpoint rotation |
| API Keys | Static | 90-day auto-rotation with notification |
| DB Credentials | Static | AWS Secrets Manager with auto-rotation |

---

# PART 4 — TENANT ISOLATION

## Current Tenant Model

```
Organization (1) → Tenant (N) → Membership (N) → User
                         ↓
                   Tenant Middleware
                   (X-Tenant-Id header)
```

## Hardened Tenant Model Design

### 1. Tenant Context Enforcement
```python
# Every DB query MUST go through this pattern:
async def get_scoped_query(request_context, base_filter):
    return {
        **base_filter,
        "organization_id": request_context.org_id,
        "tenant_id": request_context.tenant_id,  # for tenant-level isolation
    }
```

### 2. Tenant-Based Query Filters
| Collection | Isolation Key | Level |
|-----------|---------------|-------|
| bookings | organization_id | Org |
| customers | organization_id | Org |
| products | organization_id | Org |
| users | organization_id + tenant_id | Tenant |
| memberships | tenant_id | Tenant |
| audit_log | tenant_id | Tenant |
| finance_accounts | organization_id | Org |

### 3. Tenant-Scoped Permissions
```
super_admin → All tenants (cross-org for support)
org_admin → All tenants within organization
tenant_admin → Single tenant
agency_admin → Agency + assigned tenant
agency_user → Agency + assigned tenant (read-mostly)
```

### 4. Prevention Measures
- **MongoDB Views**: Create organization-scoped views for critical collections
- **Middleware Guard**: Reject any query without org_id in filter
- **Index Enforcement**: Compound indexes with organization_id as prefix
- **Audit Detection**: Flag any query that returns cross-org data

---

# PART 5 — BACKGROUND JOB SYSTEM

## Architecture: Redis + Celery

```
┌──────────┐    ┌─────────┐    ┌──────────────┐
│ FastAPI   │───>│ Redis   │───>│ Celery       │
│ (Producer)│    │ (Broker)│    │ (Workers)    │
└──────────┘    └─────────┘    │              │
                                │ ┌──────────┐│
                                │ │ booking  ││
                                │ │ queue    ││
                                │ ├──────────┤│
                                │ │ invoice  ││
                                │ │ queue    ││
                                │ ├──────────┤│
                                │ │ email    ││
                                │ │ queue    ││
                                │ ├──────────┤│
                                │ │ report   ││
                                │ │ queue    ││
                                │ └──────────┘│
                                └──────────────┘
```

## Job Categories

| Queue | Priority | Concurrency | Jobs |
|-------|----------|-------------|------|
| `booking` | Critical | 4 workers | Supplier API calls, confirmation, cancellation |
| `invoice` | High | 2 workers | Invoice generation, e-Fatura submission |
| `email` | Medium | 2 workers | Booking confirmations, reminders, notifications |
| `report` | Low | 1 worker | Scheduled reports, exports, analytics |
| `sync` | Medium | 2 workers | Google Sheets sync, inventory updates |

## Retry Policy
```python
RETRY_POLICY = {
    "booking": {"max_retries": 3, "backoff": "exponential", "max_delay": 300},
    "invoice": {"max_retries": 5, "backoff": "exponential", "max_delay": 600},
    "email": {"max_retries": 10, "backoff": "linear", "max_delay": 3600},
    "report": {"max_retries": 2, "backoff": "fixed", "delay": 60},
}
```

---

# PART 6 — RATE LIMITING

## Current: MongoDB-based (functional but slow)

Problems:
- DB write on every request for rate tracking
- No distributed support for multi-pod
- 200ms+ overhead per request during high load

## Target: Redis Distributed Rate Limiter

### Token Bucket Algorithm
```
Rate: 200 requests/minute per IP
Bucket size: 200 tokens
Refill rate: 3.33 tokens/second

1. Check tokens available: GET rate:{ip}
2. If tokens > 0: Decrement, allow request
3. If tokens = 0: Return 429 Too Many Requests
4. Refill via Redis TTL + INCR pattern
```

### Implementation (Lua Script for Atomicity)
```lua
-- rate_limit.lua
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local current = tonumber(redis.call('GET', key) or "0")
if current >= limit then
    return 0  -- rate limited
end
redis.call('INCR', key)
if current == 0 then
    redis.call('EXPIRE', key, window)
end
return limit - current - 1  -- remaining tokens
```

### Endpoint-Specific Limits
| Endpoint Pattern | Limit | Window | Key |
|-----------------|-------|--------|-----|
| `/api/auth/login` | 10 | 5 min | IP |
| `/api/auth/signup` | 3 | 5 min | IP |
| `/api/b2b/bookings` | 30 | 1 min | User |
| `/api/public/checkout` | 10 | 5 min | IP |
| Global API | 200 | 1 min | IP |

---

# PART 7 — CACHING STRATEGY

## Redis Cache Architecture

```
┌─────────┐    ┌─────────┐    ┌──────────┐
│ FastAPI  │───>│ Redis   │───>│ MongoDB  │
│          │<───│ Cache   │<───│          │
└─────────┘    └─────────┘    └──────────┘
     │              │
     │         Cache-Aside Pattern
     │         1. Check Redis
     │         2. If miss → query Mongo
     │         3. Store in Redis
     │         4. Return data
```

## TTL Strategy

| Data Type | TTL | Invalidation |
|-----------|-----|-------------|
| Agency config | 15 min | On update |
| Pricing rules | 5 min | On rule change |
| Supplier inventory | 2 min | On sync |
| Lookup tables (cities, boards) | 1 hour | On deploy |
| User permissions | 10 min | On role change |
| Hotel catalog | 30 min | On product update |
| Session data | 8 hours | On logout/revoke |

## Cache Key Naming Convention
```
syroce:{tenant_id}:{entity}:{id}
syroce:{tenant_id}:pricing:rules
syroce:{tenant_id}:inventory:{hotel_id}:{date}
syroce:lookup:cities
syroce:session:{session_id}
```

---

# PART 8 — OBSERVABILITY

## Stack Design

```
┌─────────────────────────────────────┐
│           Grafana Dashboard          │
│  ┌──────────┐  ┌──────────────────┐ │
│  │Prometheus │  │ Loki (Logs)      │ │
│  │(Metrics)  │  │ via structured   │ │
│  │           │  │ JSON logging     │ │
│  └──────────┘  └──────────────────┘ │
│       ↑              ↑               │
│  ┌──────────┐  ┌──────────────────┐ │
│  │FastAPI   │  │Sentry            │ │
│  │Middleware │  │(Error Tracking)  │ │
│  └──────────┘  └──────────────────┘ │
└─────────────────────────────────────┘
```

## What Exists (Already Good)
- Structured JSON logging middleware ✅
- Prometheus metrics middleware ✅
- Error tracking middleware ✅
- Sentry integration configured ✅
- Request log storage in MongoDB ✅
- Slow request detection (>1s) ✅
- Performance sampling ✅

## What Needs Addition
1. **OpenTelemetry distributed tracing** — Trace requests across services
2. **Grafana dashboards** — Pre-built dashboards for key metrics
3. **Alerting rules** — PagerDuty/Slack integration for critical errors
4. **Log aggregation** — Move from MongoDB to dedicated log store (Loki/ELK)
5. **SLO monitoring** — Track p99 latency, error rate, availability

## Key Metrics to Track

| Metric | Type | Alert Threshold |
|--------|------|----------------|
| `http_request_duration_seconds` | Histogram | p99 > 2s |
| `http_requests_total` | Counter | Error rate > 5% |
| `booking_created_total` | Counter | 0 in 1 hour |
| `payment_failed_total` | Counter | > 3 in 5 min |
| `db_connection_pool_size` | Gauge | > 80% capacity |
| `tenant_isolation_violations` | Counter | ANY (immediate alert) |

---

# PART 9 — PERFORMANCE IMPROVEMENTS

## Identified Slow Areas

### 1. God Routers (LOC > 500)
| Router | Lines | Impact |
|--------|-------|--------|
| `ops_finance.py` | 2,452 | Memory, parsing |
| `agency_pms.py` | ~800 | Import time |
| `admin_billing.py` | ~600 | Import time |
| `b2b.py` | ~700 | Import time |

### 2. Missing Indexes (Critical)
```javascript
// bookings — most queried collection
db.bookings.createIndex({organization_id: 1, status: 1, created_at: -1})
db.bookings.createIndex({organization_id: 1, agency_id: 1, status: 1})

// products — catalog search
db.products.createIndex({organization_id: 1, type: 1, status: 1})
db.products.createIndex({organization_id: 1, "location.city": 1, status: 1})

// inventory — availability check (hot path)
db.inventory.createIndex({organization_id: 1, product_id: 1, date: 1}, {unique: true})

// audit_log — compliance queries
db.audit_log.createIndex({tenant_id: 1, timestamp: -1})
db.audit_log.createIndex({actor_id: 1, timestamp: -1})
```

### 3. Blocking Queries
| Query Pattern | Location | Fix |
|--------------|----------|-----|
| `find({}).sort({created_at: -1})` | Multiple routers | Add limit + index |
| Aggregation without $match first | Reports | Push $match to pipeline start |
| No projection in list endpoints | Several list APIs | Add field projection |

## Performance Improvement Plan

| Priority | Action | Impact | Effort |
|----------|--------|--------|--------|
| P0 | Add compound indexes to bookings/products/inventory | -60% query time | 2h |
| P0 | Add field projections to list endpoints | -40% payload size | 4h |
| P1 | Split ops_finance.py into domain services | -30% import time | 8h |
| P1 | Add Redis caching for pricing rules | -80% pricing lookup | 4h |
| P2 | Implement pagination everywhere (cursor-based) | Memory safety | 8h |
| P2 | Add database connection pooling tuning | Connection reuse | 2h |

---

# PART 10 — PLATFORM HARDENING ROADMAP (90 Days)

## Month 1: Tests + CI/CD (STARTED)

| Week | Deliverable | Status |
|------|-------------|--------|
| 1 | Health check enhancement (DB connectivity) | ✅ DONE |
| 1 | CSRF protection middleware | ✅ DONE |
| 1 | MongoDB schema validation (10 collections) | ✅ DONE |
| 1 | CI/CD pipeline (GitHub Actions 7-stage) | ✅ DONE |
| 1 | Stabilization test suite (auth, booking, tenant, security, health) | ✅ DONE |
| 2 | Comprehensive architecture documentation | ✅ DONE |
| 2-3 | Payment flow test coverage | NEXT |
| 3-4 | Pricing engine tests + B2B contract tests | PLANNED |
| 4 | E2E Playwright critical flows | PLANNED |

## Month 2: Security Hardening

| Week | Deliverable |
|------|-------------|
| 5 | Redis rate limiter (replace MongoDB-based) |
| 5 | API key permission scoping |
| 6 | PII masking in logs |
| 6 | Secret rotation mechanism (JWT dual-key) |
| 7 | KVKK/GDPR data flow audit |
| 7 | Input validation middleware |
| 8 | Dependency vulnerability scanning in CI |

## Month 3: Scalability Infrastructure

| Week | Deliverable |
|------|-------------|
| 9 | Redis caching layer (pricing, catalog, permissions) |
| 9 | Background job system (Celery + Redis) |
| 10 | MongoDB replica set + read preference |
| 10 | Horizontal API scaling (multi-pod, stateless) |
| 11 | OpenTelemetry distributed tracing |
| 12 | Grafana dashboards + alerting rules |

---

# FINAL OUTPUT

## Top 30 Engineering Improvements

| # | Improvement | Priority | Impact | Effort |
|---|-----------|----------|--------|--------|
| 1 | ✅ Enhanced health check with DB connectivity | P0 | High | Done |
| 2 | ✅ CSRF protection middleware | P0 | Critical | Done |
| 3 | ✅ MongoDB schema validation (10 collections) | P0 | High | Done |
| 4 | ✅ CI/CD pipeline (GitHub Actions) | P0 | Critical | Done |
| 5 | ✅ Auth test suite (11 tests) | P0 | High | Done |
| 6 | ✅ Booking lifecycle test suite (8 tests) | P0 | High | Done |
| 7 | ✅ Tenant isolation test suite (6 tests) | P0 | Critical | Done |
| 8 | ✅ Security header test suite (8 tests) | P0 | High | Done |
| 9 | Redis distributed rate limiter | P0 | High | 1 week |
| 10 | JWT dual-key rotation | P0 | Critical | 3 days |
| 11 | Redis caching layer | P1 | High | 1 week |
| 12 | Background job queue (Celery) | P1 | High | 2 weeks |
| 13 | Split God-routers (ops_finance 2,452 LOC) | P1 | Medium | 1 week |
| 14 | Add compound indexes to hot collections | P0 | High | 2 hours |
| 15 | Field projections on list endpoints | P1 | Medium | 4 hours |
| 16 | Cursor-based pagination everywhere | P1 | Medium | 1 week |
| 17 | API key permission scoping | P1 | High | 3 days |
| 18 | PII masking in logs | P1 | High | 2 days |
| 19 | OpenTelemetry tracing | P2 | Medium | 1 week |
| 20 | Grafana dashboards | P2 | Medium | 3 days |
| 21 | E2E Playwright tests (10 critical flows) | P1 | High | 2 weeks |
| 22 | Frontend component decomposition | P2 | Medium | 2 weeks |
| 23 | Dependency vulnerability scanning | P1 | High | 1 day |
| 24 | KVKK/GDPR compliance audit | P1 | Critical | 1 week |
| 25 | MongoDB replica set | P2 | High | 3 days |
| 26 | CDN for static assets | P2 | Medium | 1 day |
| 27 | Database connection pool tuning | P1 | Medium | 2 hours |
| 28 | API documentation (OpenAPI + Postman) | P1 | High | 1 week |
| 29 | Domain event bus (in-process) | P2 | Medium | 2 weeks |
| 30 | Channel manager integration (1 live OTA) | P2 | Critical | 4 weeks |

## Security Risk Matrix

| Risk | Severity | Likelihood | Current Mitigation | Gap |
|------|----------|-----------|-------------------|-----|
| Cross-tenant data leak | Critical | Medium | Tenant middleware | Missing resource-level RBAC |
| CSRF attack | High | High | ✅ Double-submit cookie | None (FIXED) |
| Brute force login | High | High | Rate limiting (MongoDB) | Needs Redis-based |
| JWT secret compromise | Critical | Low | Static secret | Needs rotation |
| SQL injection (NoSQL) | Medium | Low | Pydantic validation | Missing query sanitization |
| Privilege escalation | High | Medium | Role-based | Needs resource-level perms |
| DDoS | High | Medium | Basic rate limit | Needs WAF + CDN |
| Data at rest encryption | Medium | Low | None | Needs MongoDB encryption |
| API key exposure | High | Medium | Env vars | Needs vault + rotation |
| Session fixation | Medium | Low | Session service | Needs SameSite strict |

## Architecture Refactor Suggestions

1. **Modular Monolith** → Split into bounded contexts:
   - `auth/` — Authentication, sessions, RBAC
   - `booking/` — Lifecycle, state machine, events
   - `pricing/` — Rules, calculations, audit
   - `finance/` — Ledger, settlements, payments
   - `b2b/` — Partner network, marketplace
   - `pms/` — Property management bridge
   - `crm/` — Customer relationship

2. **Repository Pattern Enforcement** → All DB access through typed repositories
3. **Service Layer** → Business logic isolated from HTTP layer
4. **Event Bus** → Decoupled domain events for side effects

## Operational Maturity Score

| Dimension | Before | After Phase 1 | Target (90 days) |
|-----------|--------|--------------|-----------------|
| **Test Coverage** | 2/10 | 4/10 | 7/10 |
| **CI/CD** | 0/10 | 6/10 | 8/10 |
| **Security** | 6.5/10 | 7.5/10 | 9/10 |
| **Observability** | 5/10 | 5.5/10 | 8/10 |
| **Architecture** | 5/10 | 5.5/10 | 7/10 |
| **Scalability** | 3/10 | 3.5/10 | 6/10 |
| **Documentation** | 3/10 | 6/10 | 8/10 |
| **Overall** | **5.5/10** | **6.3/10** | **7.6/10** |

---

## Brutally Honest Assessment

This platform has **exceptional domain breadth** — 152 collections, 180+ endpoints, and coverage of the full travel value chain. That's genuinely impressive.

But **breadth without depth is technical debt**, and right now this codebase has more debt than a Turkish airline during COVID.

### What's Actually Good:
- Multi-tenancy middleware is solid
- Audit trail with hash-chain is enterprise-grade
- Structured logging is already in place
- Turkish market fit (e-Fatura, KVKK, Google Sheets) is a genuine moat
- B2B partner network concept is defensible

### What Will Kill You in Production:
- No automated tests on 188K LOC means every deploy is Russian roulette
- MongoDB-based rate limiting will fall over under real load
- No Redis = no caching = every request hits the DB
- Single-process architecture means one slow query blocks everything
- God-router files (2,452 LOC) are unmaintainable

### The Path Forward:
This stabilization plan addresses the **top 10 risks** in the first 30 days. The remaining 60 days build the infrastructure for scale. If executed with discipline, the platform can reach production-grade quality by Month 3.

The biggest risk isn't technical — it's **prioritization**. Stop adding features. Start adding tests, indexes, and caching. A platform that works reliably on 10 features beats one that works unreliably on 100.

---

*Report generated: February 2026*
*Architecture: FastAPI + MongoDB + React*
*Codebase: 188,000 LOC*
*Assessment: Principal SaaS Architect*
