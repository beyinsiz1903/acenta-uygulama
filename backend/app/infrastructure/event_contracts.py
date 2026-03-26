"""Domain Event Contracts — Standard event payloads for Syroce domain events.

Her domain event'in:
  1. Benzersiz bir event_type adı vardır
  2. Standart bir payload yapısı vardır
  3. Hangi cache key'leri invalidate edeceği bellidir

Event Naming Convention:
  {domain}.{entity}.{action}
  Örnek: booking.reservation.created, ops.checkin.completed

Bu dosya "event catalog" olarak da canlı dokümantasyon görevi görür.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class DomainEvent:
    """Base domain event contract."""
    event_type: str
    aggregate_id: str           # Primary entity ID (e.g., reservation_id)
    org_id: str                 # Tenant/organization scope
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    actor: str = ""             # Who triggered (user_id or "system")
    payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type,
            "aggregate_id": self.aggregate_id,
            "org_id": self.org_id,
            "timestamp": self.timestamp,
            "actor": self.actor,
            "payload": self.payload,
            "metadata": self.metadata,
        }


# ═══════════════════════════════════════════════════════════
# EVENT TYPE CATALOG
# ═══════════════════════════════════════════════════════════
# Each entry: (event_type, description, invalidated_cache_prefixes)

EVENT_CATALOG: list[dict] = [
    # ── Booking Domain ─────────────────────────────────
    {
        "event_type": "booking.reservation.created",
        "description": "Yeni rezervasyon oluşturuldu",
        "invalidates": ["dash_admin_today", "dash_agency_today", "dash_hotel_today", "dash_kpi"],
    },
    {
        "event_type": "booking.reservation.updated",
        "description": "Rezervasyon güncellendi (tarih, oda, fiyat vb.)",
        "invalidates": ["dash_admin_today", "dash_agency_today", "dash_hotel_today"],
    },
    {
        "event_type": "booking.reservation.cancelled",
        "description": "Rezervasyon iptal edildi",
        "invalidates": ["dash_admin_today", "dash_agency_today", "dash_hotel_today", "dash_kpi"],
    },
    {
        "event_type": "booking.reservation.confirmed",
        "description": "Rezervasyon onaylandı",
        "invalidates": ["dash_admin_today", "dash_agency_today"],
    },

    # ── Operations Domain ──────────────────────────────
    {
        "event_type": "ops.checkin.completed",
        "description": "Misafir check-in yaptı",
        "invalidates": ["dash_hotel_today"],
    },
    {
        "event_type": "ops.checkout.completed",
        "description": "Misafir check-out yaptı",
        "invalidates": ["dash_hotel_today"],
    },
    {
        "event_type": "ops.incident.created",
        "description": "Yeni operasyonel olay / şikayet",
        "invalidates": ["dash_admin_today"],
    },
    {
        "event_type": "ops.task.completed",
        "description": "Operasyonel görev tamamlandı",
        "invalidates": ["dash_admin_today"],
    },

    # ── Finance Domain ─────────────────────────────────
    {
        "event_type": "finance.payment.received",
        "description": "Ödeme alındı",
        "invalidates": ["dash_admin_today", "dash_agency_today", "dash_kpi"],
    },
    {
        "event_type": "finance.payment.overdue",
        "description": "Ödeme vadesi geçti",
        "invalidates": ["dash_admin_today", "dash_agency_today"],
    },
    {
        "event_type": "finance.invoice.issued",
        "description": "Fatura kesildi",
        "invalidates": ["dash_admin_today"],
    },

    # ── Enterprise / Approval Domain ───────────────────
    {
        "event_type": "enterprise.approval.requested",
        "description": "Onay talebi oluşturuldu",
        "invalidates": ["dash_admin_today"],
    },
    {
        "event_type": "enterprise.approval.approved",
        "description": "Onay verildi",
        "invalidates": ["dash_admin_today"],
    },
    {
        "event_type": "enterprise.approval.rejected",
        "description": "Onay reddedildi",
        "invalidates": ["dash_admin_today"],
    },

    # ── B2B Domain ─────────────────────────────────────
    {
        "event_type": "b2b.partner.activated",
        "description": "B2B partner aktif edildi",
        "invalidates": ["dash_b2b_today", "dash_admin_today"],
    },
    {
        "event_type": "b2b.booking.created",
        "description": "B2B kanalından rezervasyon",
        "invalidates": ["dash_b2b_today", "dash_admin_today", "dash_kpi"],
    },
    {
        "event_type": "b2b.offer.expired",
        "description": "B2B teklifi süresi doldu",
        "invalidates": ["dash_b2b_today"],
    },

    # ── Pricing Domain ─────────────────────────────────
    {
        "event_type": "pricing.rule.updated",
        "description": "Fiyatlama kuralı güncellendi",
        "invalidates": ["dash_admin_today"],
    },

    # ── Dashboard Meta ─────────────────────────────────
    {
        "event_type": "dashboard.summary.invalidated",
        "description": "Dashboard özeti manuel olarak invalidate edildi",
        "invalidates": ["dash_admin_today", "dash_agency_today", "dash_hotel_today", "dash_b2b_today", "dash_kpi"],
    },
]


def get_invalidation_targets(event_type: str) -> list[str]:
    """Get cache prefixes to invalidate for a given event type."""
    for entry in EVENT_CATALOG:
        if entry["event_type"] == event_type:
            return entry["invalidates"]
    return []


def get_event_catalog() -> list[dict]:
    """Return the full event catalog for documentation."""
    return EVENT_CATALOG
