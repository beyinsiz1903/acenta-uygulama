# Syroce — ROADMAP

## P0 — Critical Path
- [ ] Activate real supplier API credentials (RateHawk, TBO, Paximum, WWTatil)
- [ ] End-to-end real booking test with at least 1 supplier

## P1 — Near-Term
- [ ] Search Caching & Optimization (reduce fan-out API costs)
- [ ] Agency Behavior Personalization (per-agency models)
- [ ] Scheduled Reconciliation Jobs (hourly sync, daily reconciliation, price mismatch)
- [ ] Commission/markup integration into actual booking flow (record commission on each booking)

## P2 — Medium-Term
- [ ] SaaS Pricing Model infrastructure
- [ ] Prometheus / Grafana metrics export
- [ ] Shadow traffic activation for new supplier testing
- [ ] Cross-tenant security audit
- [ ] PyMongo AutoReconnect resilience fix

## P3 — Backlog
- [ ] Advanced agency tiering system (VIP, Standard, Basic)
- [ ] Seasonal markup automation (auto-activate season rules)
- [ ] Multi-currency commission tracking
- [ ] Revenue alert system (notify on margin drops)
- [ ] API rate limiting per agency tier

## Completed
- [x] Core Platform (Auth, Multi-tenancy, RBAC)
- [x] Production Hardening (Security, Reliability, Monitoring)
- [x] Multi-Tenant Supplier Integration
- [x] Supplier Adapter Pattern + Aggregator
- [x] Unified Booking & Fallback Layer
- [x] Commercial Booking Experience Layer
- [x] Smart Search & Supplier Intelligence Layer
- [x] Revenue & Supplier Optimization Engine
