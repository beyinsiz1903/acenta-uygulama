"""Product Mode definitions.

Modes control UI visibility, NOT backend capabilities.
Capabilities stay. UI surface changes.

Each tenant has a product_mode stored in tenant_settings collection.
Default = 'enterprise' for backward compatibility.
"""
from __future__ import annotations

from typing import List

# ── Ordered modes (low → high) ──────────────────────────
MODES = ["lite", "pro", "enterprise"]
MODE_ORDER = {m: i for i, m in enumerate(MODES)}
DEFAULT_MODE = "enterprise"


def is_valid_mode(mode: str) -> bool:
    return mode in MODE_ORDER


def is_at_least(current_mode: str, required_mode: str) -> bool:
    """Check if current_mode is >= required_mode in the mode hierarchy."""
    return MODE_ORDER.get(current_mode, 0) >= MODE_ORDER.get(required_mode, 0)


# ── Visibility config per mode ──────────────────────────
# Keys are sidebar group/item identifiers used by the frontend.
# "visible_nav_groups" controls which sidebar groups are shown.
# "visible_nav_items" fine-grained per-item control (overrides group).
# "hidden_nav_items" explicit hide list (takes priority).
#
# Frontend uses minMode on each nav item; this config is the
# authoritative server-side source of truth.

MODE_VISIBILITY = {
    "lite": {
        "visible_nav_groups": [
            "CORE",
            "CRM",
            "FİNANS",
            "YÖNETİM",
        ],
        "hidden_nav_items": [
            # B2B AĞ - entire group hidden
            "partner_yonetimi",
            "b2b_acenteler",
            "marketplace",
            "b2b_funnel",
            # FİNANS - advanced items hidden
            "webpos",
            "mutabakat",
            "exposure",
            # OPS - entire group hidden
            "guest_cases",
            "ops_tasks",
            "ops_incidents",
            # YÖNETİM - advanced items hidden
            "acentalar",
            "fiyatlandirma",
            "kuponlar",
            "kampanyalar",
            "linkler",
            "cms",
            "tenant_ayarlari",
            "tenant_saglik",
            "audit_log",
            # ENTERPRISE - entire group hidden
            "white_label",
            "onay_istekleri",
            "veri_export",
            "zamanlanmis_raporlar",
            "efatura",
            "sms",
            "qr_bilet",
            # OPERATIONAL EXCELLENCE hidden
            "system_backups",
            "system_integrity",
            "system_metrics",
            "system_errors",
            "system_uptime",
            "system_incidents",
            "preflight",
            "runbook",
            "perf_dashboard",
            "demo_guide",
        ],
        "label_overrides": {
            "approval_engine": "Onay",
            "immutable_audit": "Hareket Geçmişi",
            "settlement": "Ödeme Mutabakatı",
            "ledger": "İşlem Geçmişi",
            "integrity": "Sistem Kontrolü",
        },
    },
    "pro": {
        "visible_nav_groups": [
            "CORE",
            "CRM",
            "B2B AĞ",
            "FİNANS",
            "OPS",
            "YÖNETİM",
        ],
        "hidden_nav_items": [
            # ENTERPRISE - group hidden
            "white_label",
            "onay_istekleri",
            "veri_export",
            "zamanlanmis_raporlar",
            "efatura",
            "sms",
            "qr_bilet",
            # OPS EXCELLENCE - advanced hidden
            "system_integrity",
            "system_backups",
            "preflight",
            "perf_dashboard",
            "demo_guide",
        ],
        "label_overrides": {},
    },
    "enterprise": {
        "visible_nav_groups": [
            "CORE",
            "CRM",
            "B2B AĞ",
            "FİNANS",
            "OPS",
            "YÖNETİM",
            "ENTERPRISE",
        ],
        "hidden_nav_items": [],
        "label_overrides": {},
    },
}


def get_mode_config(mode: str) -> dict:
    """Return visibility config for given mode."""
    return MODE_VISIBILITY.get(mode, MODE_VISIBILITY[DEFAULT_MODE])


def get_hidden_items_for_mode(mode: str) -> List[str]:
    """Return list of hidden nav item keys for mode."""
    cfg = get_mode_config(mode)
    return cfg.get("hidden_nav_items", [])


def get_mode_diff(from_mode: str, to_mode: str) -> dict:
    """Return what changes when switching from from_mode to to_mode.

    Returns:
        {
            "newly_visible": [...],  # items that become visible
            "newly_hidden": [...],   # items that become hidden
            "from_mode": str,
            "to_mode": str,
            "is_upgrade": bool,
        }
    """
    from_hidden = set(get_hidden_items_for_mode(from_mode))
    to_hidden = set(get_hidden_items_for_mode(to_mode))

    return {
        "from_mode": from_mode,
        "to_mode": to_mode,
        "is_upgrade": MODE_ORDER.get(to_mode, 0) > MODE_ORDER.get(from_mode, 0),
        "newly_visible": sorted(from_hidden - to_hidden),
        "newly_hidden": sorted(to_hidden - from_hidden),
    }
