# Runtime Operations

## 1. Runtime overview
- `server:app` sadece **compat** amaçlıdır.
- Kalıcı hedef runtime'lar:
  - API → `app.bootstrap.api_app:create_app`
  - Worker → `app.bootstrap.worker_app`
  - Scheduler → `app.bootstrap.scheduler_app`
- Operasyonel hedef: API, worker ve scheduler'ın ayrı process olarak çalıştırılması; worker/scheduler işlerinin API process içine geri taşınmaması.

## 2. Entrypoint'ler
- **API entrypoint:** `uvicorn app.bootstrap.api_app:create_app --factory --host 0.0.0.0 --port 8001`
- **Worker entrypoint:** `python -m app.bootstrap.worker_app`
- **Scheduler entrypoint:** `python -m app.bootstrap.scheduler_app`
- Hazır script'ler:
  - `scripts/run_api_runtime.sh`
  - `scripts/run_worker_runtime.sh`
  - `scripts/run_scheduler_runtime.sh`

## 3. Process sorumlulukları
- **API**
  - HTTP request/response trafiği
  - middleware + router registration
  - auth/session/tenant kontrolü
  - `/health` ve uygulama root endpoint'leri
- **Worker**
  - email outbox dispatch
  - integration sync outbox processing
  - jobs queue consumer
  - seed/cache warm-up boot task'leri
- **Scheduler**
  - billing finalize cron
  - report schedule polling
  - uptime / integrity / backup cleanup işleri
  - Google Sheets sync + portfolio sync + write-back job'ları

## 4. Local çalıştırma komutları
```bash
cd /app/backend

# API
./scripts/run_api_runtime.sh

# Worker
./scripts/run_worker_runtime.sh

# Scheduler
./scripts/run_scheduler_runtime.sh
```

Ham komut karşılıkları:
```bash
cd /app/backend && uvicorn app.bootstrap.api_app:create_app --factory --host 0.0.0.0 --port 8001
cd /app/backend && python -m app.bootstrap.worker_app
cd /app/backend && python -m app.bootstrap.scheduler_app
```

## 5. Preview / staging / prod çalıştırma yaklaşımı
- Her runtime ayrı process tanımı olarak ayağa kaldırılmalı.
- **API** için hedef komut `app.bootstrap.api_app:create_app` olmalı.
- **Worker** ve **Scheduler** için birer dedicated process kullanılmalı.
- `server:app` sadece geçiş/compat amaçlı tutulmalı; yeni kalıcı deploy wiring bunun üstüne kurulmamamalı.
- Worker ve scheduler için tek instance ile başlayın; yatay ölçekleme gerekiyorsa idempotency/locking davranışları ayrıca doğrulanmalı.

## 6. Health check yaklaşımı
- **API:** HTTP `GET /health`
- **Worker:** heartbeat dosyası kontrolü
  - heartbeat yolu: `${RUNTIME_HEALTH_DIR:-/tmp/acenta-runtime-health}/worker.json`
  - kontrol komutu: `python scripts/check_runtime_health.py worker`
- **Scheduler:** heartbeat dosyası kontrolü
  - heartbeat yolu: `${RUNTIME_HEALTH_DIR:-/tmp/acenta-runtime-health}/scheduler.json`
  - kontrol komutu: `python scripts/check_runtime_health.py scheduler`
- Worker/scheduler process'leri `SIGTERM`/`SIGINT` aldığında kontrollü shutdown yapar ve heartbeat durumunu günceller.

## 7. Deploy sonrası smoke checklist
1. `curl -f <base-url>/health`
2. Web login sonrası `GET /api/auth/me`
3. Mobile BFF auth doğrulaması: `GET /api/v1/mobile/auth/me`
4. Worker heartbeat fresh mi: `python scripts/check_runtime_health.py worker`
5. Scheduler heartbeat fresh mi: `python scripts/check_runtime_health.py scheduler`
6. Worker log'larında email/job/integration loop başlangıcı görüldü mü?
7. Scheduler log'larında billing/report/ops schedulers start oldu mu?
8. Route inventory export: `python scripts/export_route_inventory.py --environment <preview|staging|prod>`
9. Route summary parity: `python scripts/check_route_inventory_parity.py preview=... staging=... prod=... --fail-on-mismatch`

## 8. Rollback notları
- API rollback gerekirse `server:app` compat entrypoint geçici emniyet supabı olarak kullanılabilir.
- Rollback, worker/scheduler'ı API process içine geri gömmek anlamına gelmemeli; mümkünse önceki stabil ayrı-process runtime tanımına dönülmeli.
- Rollback sonrası minimum smoke tekrar çalıştır:
  - `/health`
  - `/api/auth/me`
  - `/api/v1/mobile/auth/me`
  - worker heartbeat
  - scheduler heartbeat

## 9. P0 notu
- **PR-7'ye geçmeden önce dedicated worker + scheduler runtime wiring tamamen kapatılmalı.**
- Aktif cihazlar / oturumlar ekranı değerli ama operasyonel split canlıya hazır hale gelmeden öne alınmamalı.

## 10. Route inventory parity
- Preview / staging / prod parity süreci için kısa operasyonel kaynak: `app/bootstrap/route_inventory_parity.md`
- API runtime boot sırasında best-effort olarak hem `route_inventory.json` hem `route_inventory_summary.json` üretir.
- CI artifact'leri üzerinden `diff` ve ortamlar arası `parity` kontrolü çalıştırılmalıdır; sadece preview sonucu yeterli kabul edilmemelidir.