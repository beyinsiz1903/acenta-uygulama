# Production Go-Live Checklist (Enterprise)

## 1) Ortamlar
- [ ] **staging** ve **production** ayrı namespace
- [ ] Ayrı Mongo cluster (en azından ayrı DB + user)
- [ ] Ayrı Stripe keys / webhook secrets
- [ ] Ayrı Slack webhook channel (ops vs dev)

## 2) Secrets & Config
- [ ] `JWT_SECRET` rotation planı var
- [ ] `SLACK_BILLING_WEBHOOK_URL` prod set
- [ ] `BACKUP_PATH=/var/backups/app` persistent volume
- [ ] `MAINTENANCE_MODE_DEFAULT=false`
- [ ] `RATE_LIMIT_*` değerleri prod için ayarlı

## 3) DB (Mongo)
- [ ] Index migration script’leri staging’de koştu
- [ ] TTL index’ler çalışıyor (rate limit, request_logs)
- [ ] Backup/restore test staging’de 1 kez geçti (`scripts/restore_test.py`)
- [ ] Retention cron çalışıyor (30 gün)

## 4) Jobs / Scheduler
- [ ] APScheduler “single leader” çalışıyor (multi-replica varsa duplicate job engeli)
- [ ] Billing finalize cron + integrity cron + uptime cron enabled
- [ ] Job status sayfası OK (ops widget + Slack alert)

## 5) Observability
- [ ] `/api/health/live` → 200
- [ ] `/api/health/ready` → 200 (DB + scheduler + disk OK)
- [ ] `X-Request-Id` header response’ta
- [ ] Error aggregation sayfası boş değilse triage edilmiş

## 6) Security
- [ ] 2FA enable/disable akışı prod’da çalışıyor
- [ ] IP whitelist test edildi
- [ ] Password policy enforced
- [ ] Export endpoint rate limited

## 7) Access / Roles
- [ ] super_admin role sadece belirli hesaplarda
- [ ] Approval inbox permission setleri hazır
- [ ] Export/backup endpoints sadece system.backup.manage vb permission ile

---

## GO / NO-GO Kabul Kriterleri

### ✅ GO:
- restore_test geçti
- health/ready 24 saat stabil
- uptime tracker çalışıyor
- billing finalize otomatik ve 1 cycle başarıyla geçti
- E2E suite %100 green

### ❌ NO-GO:
- Scheduler duplicate job çalıştırıyorsa
- Backup path persistent değilse
- Audit chain integrity fail veriyorsa

---

## Otomatik Preflight Kontrolü

```bash
# API üzerinden:
curl -H "Authorization: Bearer $TOKEN" /api/admin/system/preflight

# Veya UI:
/app/admin/preflight
```
