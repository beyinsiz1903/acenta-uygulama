"""C - Interactive Demo Guide Endpoint.

GET /api/admin/system/demo-guide - Returns structured demo steps with screen links
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import require_roles

router = APIRouter(
    prefix="/api/admin/system",
    tags=["demo_guide"],
)

DEMO_STEPS = [
    {
        "id": "opening",
        "time": "0:00-1:30",
        "title": "A\u00e7\u0131l\u0131\u015f \u2014 Neyi \u00e7\u00f6z\u00fcy\u00f6ruz?",
        "message": "Turizm operasyonunu ERP + B2B + Finance olarak tek \u00e7ekirdekte, enterprise y\u00f6neti\u015fimle sunuyoruz.",
        "screen": "/app",
        "screen_label": "Dashboard",
        "talking_points": [
            "5-6 farkl\u0131 ara\u00e7 yerine tek platform",
            "Veri tutarl\u0131l\u0131\u011f\u0131 + maliyet d\u00fc\u015f\u00fc\u015f\u00fc",
            "Enterprise standart y\u00f6neti\u015fim"
        ],
    },
    {
        "id": "security",
        "time": "1:30-3:30",
        "title": "Multi-tenant & Roles (G\u00fcven)",
        "message": "Tenant izolasyonu, RBAC v2, 2FA, IP whitelist. Her i\u015flem kriptografik zincirle ba\u011fl\u0131.",
        "screen": "/app/admin/tenant-health",
        "screen_label": "Tenant Health",
        "talking_points": [
            "Her m\u00fc\u015fteri izole tenant",
            "Gran\u00fcler roller ve izinler",
            "2FA + IP k\u0131s\u0131tlamas\u0131",
            "Immutable audit chain"
        ],
    },
    {
        "id": "crm",
        "time": "3:30-5:30",
        "title": "CRM Pipeline (Sat\u0131\u015f)",
        "message": "Drag-drop pipeline, deal drawer, customer 360. \u0130zlenebilir sat\u0131\u015f s\u00fcreci.",
        "screen": "/app/crm/pipeline",
        "screen_label": "CRM Pipeline",
        "talking_points": [
            "Pipeline board drag-drop",
            "Deal drawer: tasks, notes, activity",
            "Customer 360 sayfas\u0131",
            "Timeline + audit feed"
        ],
    },
    {
        "id": "finance",
        "time": "5:30-7:30",
        "title": "Finance & Ledger",
        "message": "Append-only ledger, refund approval flow, settlement & reconciliation.",
        "screen": "/app/admin/finance/settlements",
        "screen_label": "Finance",
        "talking_points": [
            "Ledger append-only",
            "\u0130ade onay mekanizmas\u0131",
            "Settlement & mutabakat",
            "Multi-currency"
        ],
    },
    {
        "id": "reporting",
        "time": "7:30-9:00",
        "title": "Raporlama",
        "message": "Advanced reports, CSV export, scheduled delivery.",
        "screen": "/app/admin/reporting",
        "screen_label": "Reports",
        "talking_points": [
            "Financial / Product / Partner raporlar\u0131",
            "CSV export",
            "Zamanlanm\u0131\u015f raporlar"
        ],
    },
    {
        "id": "efatura",
        "time": "9:00-10:30",
        "title": "E-Fatura (Uyum)",
        "message": "Provider-agnostic e-fatura. Mock \u2192 production adapter 1-2 hafta.",
        "screen": "/app/admin/efatura",
        "screen_label": "E-Fatura",
        "talking_points": [
            "Fatura olu\u015ftur (sat\u0131r + vergi)",
            "G\u00f6nder (mock provider)",
            "Durum takibi: taslak \u2192 kabul",
            "Provider se\u00e7imi m\u00fc\u015fteride"
        ],
    },
    {
        "id": "sms",
        "time": "10:30-11:30",
        "title": "SMS Bildirimleri",
        "message": "Template + bulk SMS, provider abstraction, audit log.",
        "screen": "/app/admin/sms",
        "screen_label": "SMS",
        "talking_points": [
            "Template se\u00e7imi",
            "Tekli/toplu SMS",
            "Log'da delivered durumu",
            "Netgsm/Twilio pluggable"
        ],
    },
    {
        "id": "tickets",
        "time": "11:30-12:30",
        "title": "QR Ticket & Check-in",
        "message": "QR bilet, check-in guard'lar\u0131: already checked-in / canceled / expired.",
        "screen": "/app/admin/tickets",
        "screen_label": "Tickets",
        "talking_points": [
            "Bilet olu\u015ftur (QR)",
            "Check-in yap",
            "Duplicate guard",
            "\u0130ptal korumas\u0131"
        ],
    },
    {
        "id": "ops",
        "time": "12:30-14:00",
        "title": "Ops Excellence (Enterprise fark\u0131)",
        "message": "Preflight, Runbook, Metrics, Errors, Uptime, Perf Dashboard.",
        "screen": "/app/admin/preflight",
        "screen_label": "Preflight",
        "talking_points": [
            "GO/NO-GO banner",
            "P0 incident runbook",
            "8 metrik kart\u0131",
            "p50/p95/p99 performance",
            "Backup/restore tested"
        ],
        "sub_screens": [
            {"label": "Runbook", "path": "/app/admin/runbook"},
            {"label": "Metrics", "path": "/app/admin/system-metrics"},
            {"label": "Errors", "path": "/app/admin/system-errors"},
            {"label": "Uptime", "path": "/app/admin/system-uptime"},
            {"label": "Perf", "path": "/app/admin/perf-dashboard"},
        ],
    },
    {
        "id": "closing",
        "time": "14:00-15:00",
        "title": "Kapan\u0131\u015f & Next Steps",
        "message": "2 haftal\u0131k pilot + 1 hafta e\u011fitim + go-live checklist ile production.",
        "screen": "/app/admin/preflight",
        "screen_label": "Preflight (GO)",
        "talking_points": [
            "2 hafta pilot (ger\u00e7ek veri)",
            "1 hafta e\u011fitim",
            "Go-live checklist haz\u0131r",
            "Risk s\u0131f\u0131r"
        ],
    },
]


@router.get("/demo-guide")
async def get_demo_guide(
    user=Depends(require_roles(["super_admin"])),
):
    """Return structured demo guide steps."""
    return {
        "title": "15 Dakika Enterprise Demo",
        "total_steps": len(DEMO_STEPS),
        "total_time": "15 dakika",
        "steps": DEMO_STEPS,
    }
