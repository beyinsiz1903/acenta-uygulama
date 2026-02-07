# Ops Runbook (Playbook)

## P0 Incident: Sistem Erişilemiyor (Hedef: 5 dk)

1. `/api/health/live` → down mı?
2. `/api/health/ready` → DB / disk / scheduler failure mı?
3. Maintenance mode aç:
   - Admin → Tenant Maintenance ON
4. `system_errors` sayfasında son signature’a bak
5. Rollback kararı:
   - Son deployment revert
6. Incident oluştur:
   - severity=critical
   - start_time
   - affected tenants

## P1 Incident: DB Sorunları / Latency Artışı (Hedef: 15 dk)

1. Metrics → error_rate, latency, disk_usage kontrol
2. Slow requests signature’larını incele
3. Index missing şüphesi:
   - Son 24 saatte yeni query pattern?
4. Geçici çözüm:
   - Heavy endpoint rate limit arttır / limit düşür
   - Export/backup disable (gerekirse)

## P1 Incident: Billing Finalize Hatası (Hedef: 15 dk)

1. Slack alert geldi mi?
2. Billing Ops widget:
   - pending_after > 0 mı?
   - error_count kaç?
3. Manual retry:
   - `/api/admin/billing/finalize-period`
4. Stripe webhook event backlog kontrol:
   - `billing_webhook_events`

## P2 Incident: Veri Bütünlüğü İhlali (Hedef: 30 dk)

1. Bütünlük raporu:
   - orphan count
   - ledger mismatch
   - audit hash broken
2. Hash chain broken ise:
   - Write path’te update yapan endpoint var mı? (bug)
3. Ledger mismatch:
   - Append-only policy ihlali var mı?
4. Incident severity:
   - audit chain broken → critical

## Scheduled: Backup & Restore Test (Haftalık)

1. Manuel yedek al: `/app/admin/system-backups`
2. Restore test: `python scripts/restore_test.py /var/backups/app/<dosya>.gz`
3. Koleksiyon sayıları ve audit chain doğrula
4. 30 gün retention kontrolü
