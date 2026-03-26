# ROADMAP — Syroce Platform

## Completed
- [x] Phase 1: Foundation (PRD, module maps, packaging)
- [x] Phase 2: Router & Domain Cleanup (160+ routers, architecture guard)
- [x] Phase 3: Persona-Based UI & Dashboards (all 4 personas)
- [x] Phase 4 Faz A: CI Quality Gates & Scope Audit
- [x] Phase 4 Faz B: Physical Router Migration (230 files)
- [x] Phase 4 Faz C: Event-Driven Core + Cache Strategy
- [x] Phase 4 Faz D: Live Architecture Documentation

## P1 — Next Up
- [ ] Coverage threshold gradual increase (20% → 30% → 50%)
- [ ] Shim file cleanup: Gradually remove backward-compat shims after verifying all imports
- [ ] WebSocket Real-Time Dashboard Integration

## P2 — Backlog
- [ ] Feature flag / package scope enforcement
- [ ] In-Product Analytics & Usage Visibility
- [ ] Event-driven expansion: Add actual handlers for booking/payment flows
- [ ] Redis integration hardening (currently optional/graceful degradation)
- [ ] React Router v7 migration (resolve future flag warnings)
- [ ] Service layer refactoring (remove FastAPI imports from services)
- [ ] Orphan router assignment (4 remaining)
