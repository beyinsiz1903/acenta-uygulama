"""Runbook Endpoint — serves structured ops playbook data.

GET /api/admin/system/runbook - Returns structured runbook entries
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import require_roles

router = APIRouter(
    prefix="/api/admin/system",
    tags=["system_runbook"],
)

RUNBOOK_ENTRIES = [
    {
        "id": "p0-system-down",
        "severity": "P0",
        "title": "Sistem Erişilemiyor",
        "target_time": "5 dakika",
        "steps": [
            {"order": 1, "action": "Health check", "detail": "/api/health/live kontrol et → down mı?", "api": "/api/health/live"},
            {"order": 2, "action": "Readiness check", "detail": "/api/health/ready → DB / disk / scheduler failure mı?", "api": "/api/health/ready"},
            {"order": 3, "action": "Maintenance mode aç", "detail": "Admin → Tenant Maintenance ON", "api": "PATCH /api/admin/tenant/maintenance"},
            {"order": 4, "action": "Hata loglarını incele", "detail": "system_errors sayfasında son signature'a bak", "page": "/app/admin/system-errors"},
            {"order": 5, "action": "Rollback kararı", "detail": "Son deployment'ı revert et"},
            {"order": 6, "action": "Incident oluştur", "detail": "severity=critical, start_time, affected tenants", "page": "/app/admin/system-incidents"},
        ],
    },
    {
        "id": "p1-db-latency",
        "severity": "P1",
        "title": "DB Sorunları / Latency Artışı",
        "target_time": "15 dakika",
        "steps": [
            {"order": 1, "action": "Metrikleri kontrol et", "detail": "error_rate, latency, disk_usage", "page": "/app/admin/system-metrics"},
            {"order": 2, "action": "Slow request signature'larını incele", "detail": "system_errors → severity=warning filtrele", "page": "/app/admin/system-errors"},
            {"order": 3, "action": "Index analizi", "detail": "Son 24 saatte yeni query pattern var mı?"},
            {"order": 4, "action": "Geçici çözüm", "detail": "Heavy endpoint rate limit arttır / export-backup disable et"},
        ],
    },
    {
        "id": "p1-billing-fail",
        "severity": "P1",
        "title": "Billing Finalize Hatası",
        "target_time": "15 dakika",
        "steps": [
            {"order": 1, "action": "Slack alert kontrol", "detail": "Billing webhook alert geldi mi?"},
            {"order": 2, "action": "Billing ops widget kontrol", "detail": "pending_after > 0 mı? error_count kaç?"},
            {"order": 3, "action": "Manual retry", "detail": "/api/admin/billing/finalize-period", "api": "POST /api/admin/billing/finalize-period"},
            {"order": 4, "action": "Stripe webhook backlog", "detail": "billing_webhook_events koleksiyonunu kontrol et"},
        ],
    },
    {
        "id": "p2-data-integrity",
        "severity": "P2",
        "title": "Veri Bütünlüğü İhlali",
        "target_time": "30 dakika",
        "steps": [
            {"order": 1, "action": "Bütünlük raporu çalıştır", "detail": "orphan count, ledger mismatch, audit hash broken", "page": "/app/admin/system-integrity"},
            {"order": 2, "action": "Hash chain kırık ise", "detail": "Write path'te update yapan endpoint var mı? (bug)"},
            {"order": 3, "action": "Ledger mismatch", "detail": "Append-only policy ihlali var mı?"},
            {"order": 4, "action": "Severity belirle", "detail": "audit chain broken → critical incident oluştur", "page": "/app/admin/system-incidents"},
        ],
    },
    {
        "id": "scheduled-backup-restore",
        "severity": "Scheduled",
        "title": "Backup & Restore Test (Haftalık)",
        "target_time": "Planlı",
        "steps": [
            {"order": 1, "action": "Manuel yedek al", "detail": "Sistem Yedekleri → Yedek Al", "page": "/app/admin/system-backups"},
            {"order": 2, "action": "Restore test çalıştır", "detail": "python scripts/restore_test.py /var/backups/app/<dosya>.gz"},
            {"order": 3, "action": "Sonucu doğrula", "detail": "Koleksiyon sayıları ve audit chain doğrula"},
            {"order": 4, "action": "30 gün retention kontrolü", "detail": "Eski yedekler otomatik siliniyor mu?"},
        ],
    },
]


@router.get("/runbook")
async def get_runbook(
    user=Depends(require_roles(["super_admin"])),
):
    """Return structured runbook / ops playbook entries."""
    return {"entries": RUNBOOK_ENTRIES, "total": len(RUNBOOK_ENTRIES)}
