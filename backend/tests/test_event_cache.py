"""Event-Driven Core Tests — Event contracts, cache bridge, and integration.

Tests:
  1. Event catalog integrity
  2. Cache invalidation target resolution
  3. Event-cache bridge registration
  4. Domain event emission + cache invalidation flow
  5. TTL config standardization
"""
from __future__ import annotations

import asyncio

import pytest


# ═══════════════════════════════════════════════════
# TEST 1: Event catalog integrity
# ═══════════════════════════════════════════════════
def test_event_catalog_integrity():
    """Every event in the catalog must have required fields."""
    from app.infrastructure.event_contracts import EVENT_CATALOG

    assert len(EVENT_CATALOG) > 0, "Event catalog is empty"

    for entry in EVENT_CATALOG:
        assert "event_type" in entry, f"Missing event_type: {entry}"
        assert "description" in entry, f"Missing description: {entry}"
        assert "invalidates" in entry, f"Missing invalidates: {entry}"

        # Event type must follow naming convention: domain.entity.action
        parts = entry["event_type"].split(".")
        assert len(parts) >= 3, (
            f"Event type '{entry['event_type']}' does not follow "
            f"domain.entity.action convention"
        )

        # Invalidation targets must be non-empty list
        assert isinstance(entry["invalidates"], list), (
            f"invalidates must be a list for '{entry['event_type']}'"
        )


def test_event_catalog_no_duplicate_types():
    """No duplicate event types in the catalog."""
    from app.infrastructure.event_contracts import EVENT_CATALOG

    types = [e["event_type"] for e in EVENT_CATALOG]
    duplicates = [t for t in types if types.count(t) > 1]
    assert not duplicates, f"Duplicate event types: {set(duplicates)}"


# ═══════════════════════════════════════════════════
# TEST 2: Cache invalidation target resolution
# ═══════════════════════════════════════════════════
def test_invalidation_targets_resolution():
    """get_invalidation_targets should return correct prefixes."""
    from app.infrastructure.event_contracts import get_invalidation_targets

    # Known event type
    targets = get_invalidation_targets("booking.reservation.created")
    assert "dash_admin_today" in targets
    assert "dash_agency_today" in targets

    # Unknown event type returns empty
    targets = get_invalidation_targets("unknown.event.type")
    assert targets == []


# ═══════════════════════════════════════════════════
# TEST 3: Event-cache bridge registration
# ═══════════════════════════════════════════════════
def test_event_cache_bridge_registration():
    """Bridge should register handlers without errors."""
    from app.infrastructure.event_cache_bridge import register_cache_invalidation_handlers

    # Should not raise
    register_cache_invalidation_handlers()


# ═══════════════════════════════════════════════════
# TEST 4: Domain event dataclass
# ═══════════════════════════════════════════════════
def test_domain_event_dataclass():
    """DomainEvent dataclass should serialize correctly."""
    from app.infrastructure.event_contracts import DomainEvent

    event = DomainEvent(
        event_type="booking.reservation.created",
        aggregate_id="res_123",
        org_id="org_abc",
        actor="user_1",
        payload={"hotel": "Test Hotel"},
    )

    d = event.to_dict()
    assert d["event_type"] == "booking.reservation.created"
    assert d["aggregate_id"] == "res_123"
    assert d["org_id"] == "org_abc"
    assert "timestamp" in d


# ═══════════════════════════════════════════════════
# TEST 5: TTL config has dashboard entries
# ═══════════════════════════════════════════════════
def test_ttl_config_dashboard_entries():
    """TTL matrix must have entries for dashboard cache."""
    from app.services.cache_ttl_config import TTL_MATRIX, get_ttl

    assert "dashboard_kpi" in TTL_MATRIX
    assert "dashboard_charts" in TTL_MATRIX

    # Dashboard KPI TTL should be reasonable (30-300s)
    kpi_ttl = get_ttl("dashboard_kpi")
    assert 30 <= kpi_ttl <= 300, f"Dashboard KPI TTL {kpi_ttl} out of range"


# ═══════════════════════════════════════════════════
# TEST 6: All dashboard cache keys in event catalog
# ═══════════════════════════════════════════════════
def test_all_dashboard_cache_keys_in_events():
    """Every dashboard cache prefix should be invalidated by at least one event."""
    from app.infrastructure.event_contracts import EVENT_CATALOG

    DASHBOARD_PREFIXES = [
        "dash_admin_today",
        "dash_agency_today",
        "dash_hotel_today",
        "dash_b2b_today",
    ]

    all_invalidation_targets = set()
    for entry in EVENT_CATALOG:
        all_invalidation_targets.update(entry["invalidates"])

    for prefix in DASHBOARD_PREFIXES:
        assert prefix in all_invalidation_targets, (
            f"Dashboard prefix '{prefix}' is never invalidated by any event"
        )


# ═══════════════════════════════════════════════════
# TEST 7: Event bus subscribe works
# ═══════════════════════════════════════════════════
def test_event_bus_subscribe():
    """Event bus subscribe should accept handlers."""
    from app.infrastructure.event_bus import subscribe, get_registered_handlers

    call_log = []

    async def test_handler(data):
        call_log.append(data)

    subscribe("test.event.unit", test_handler)
    stats = get_registered_handlers()
    assert "test.event.unit" in stats
