"""T007 — Per-tenant rate limiting unit tests (DB-free).

Covers:
- Plan multiplier resolution (built-ins + env override + unknown fallback)
- Per-tier scaling (tenant_* tiers scaled, IP/auth tiers untouched)
- Plan cache TTL behaviour in the middleware helper
"""
from __future__ import annotations


import pytest

from app.infrastructure.rate_limiter import (
    PLAN_MULTIPLIERS,
    RATE_TIERS,
    _resolve_plan_multiplier,
    _scaled_config,
)


def test_plan_multiplier_known_plans():
    assert _resolve_plan_multiplier("free") == PLAN_MULTIPLIERS["free"]
    assert _resolve_plan_multiplier("basic") == 1.0
    assert _resolve_plan_multiplier("pro") == PLAN_MULTIPLIERS["pro"]
    assert _resolve_plan_multiplier("enterprise") == PLAN_MULTIPLIERS["enterprise"]


def test_plan_multiplier_case_and_whitespace_insensitive():
    assert _resolve_plan_multiplier("  PRO  ") == PLAN_MULTIPLIERS["pro"]
    assert _resolve_plan_multiplier("Enterprise") == PLAN_MULTIPLIERS["enterprise"]


def test_plan_multiplier_unknown_falls_back_to_basic():
    assert _resolve_plan_multiplier("not_a_real_plan") == 1.0
    assert _resolve_plan_multiplier(None) == 1.0
    assert _resolve_plan_multiplier("") == 1.0


def test_plan_multiplier_env_override(monkeypatch):
    monkeypatch.setenv("SYROCE_RATE_PLAN_MULT_PRO", "12.5")
    assert _resolve_plan_multiplier("pro") == 12.5

    # Invalid env values are ignored — fall through to built-in.
    monkeypatch.setenv("SYROCE_RATE_PLAN_MULT_PRO", "not-a-number")
    assert _resolve_plan_multiplier("pro") == PLAN_MULTIPLIERS["pro"]

    # Negative or zero env values are also ignored.
    monkeypatch.setenv("SYROCE_RATE_PLAN_MULT_PRO", "-1")
    assert _resolve_plan_multiplier("pro") == PLAN_MULTIPLIERS["pro"]


def test_scaled_config_tenant_tier_scales_with_plan():
    base = RATE_TIERS["tenant_global"]
    pro = _scaled_config("tenant_global", "pro")
    assert pro["capacity"] == int(base["capacity"] * PLAN_MULTIPLIERS["pro"])
    assert pro["refill_rate"] == pytest.approx(base["refill_rate"] * PLAN_MULTIPLIERS["pro"])

    free = _scaled_config("tenant_global", "free")
    assert free["capacity"] == int(base["capacity"] * PLAN_MULTIPLIERS["free"])
    assert free["refill_rate"] == pytest.approx(base["refill_rate"] * PLAN_MULTIPLIERS["free"])
    assert free["capacity"] >= 1  # never collapses to zero


def test_scaled_config_non_tenant_tier_ignores_plan():
    """IP-keyed and auth tiers must NOT be scaled by plan — otherwise an
    enterprise tenant could brute-force /auth/login by burning their tenant's
    quota. Only tenant_* tiers are plan-scaled.
    """
    for tier in ("auth_login", "auth_signup", "api_global", "public_checkout"):
        scaled = _scaled_config(tier, "enterprise")
        assert scaled is RATE_TIERS[tier] or scaled == RATE_TIERS[tier], (
            f"tier {tier} must not be scaled by plan"
        )


def test_scaled_config_basic_plan_returns_base_unchanged():
    base = RATE_TIERS["tenant_global"]
    assert _scaled_config("tenant_global", "basic") is base


def test_scaled_config_unknown_tier_falls_back_to_api_global():
    fallback = _scaled_config("nonexistent_tier", None)
    assert fallback is RATE_TIERS["api_global"]


@pytest.mark.anyio
async def test_resolve_org_plan_caches_within_ttl(monkeypatch):
    """The middleware-level plan cache must coalesce repeated lookups for the
    same org within the TTL window down to a single DB hit.
    """
    from app.middleware import rate_limit_middleware as mw

    # Reset cache state for a clean test.
    mw._PLAN_CACHE.clear()

    call_count = {"n": 0}

    class _FakeOrgs:
        async def find_one(self, *args, **kwargs):
            call_count["n"] += 1
            return {"_id": "org_xyz", "plan": "pro"}

    class _FakeDB:
        organizations = _FakeOrgs()

    async def _fake_get_db():
        return _FakeDB()

    monkeypatch.setattr("app.db.get_db", _fake_get_db)

    plan1 = await mw._resolve_org_plan("org_xyz")
    plan2 = await mw._resolve_org_plan("org_xyz")
    plan3 = await mw._resolve_org_plan("org_xyz")

    assert plan1 == "pro"
    assert plan2 == "pro"
    assert plan3 == "pro"
    assert call_count["n"] == 1, "plan lookup should hit DB only once within TTL"


@pytest.mark.anyio
async def test_resolve_org_plan_returns_none_on_db_error(monkeypatch):
    """A DB failure must NOT raise — middleware must remain non-blocking."""
    from app.middleware import rate_limit_middleware as mw

    mw._PLAN_CACHE.clear()

    async def _broken_get_db():
        raise RuntimeError("simulated db outage")

    monkeypatch.setattr("app.db.get_db", _broken_get_db)

    plan = await mw._resolve_org_plan("org_unreachable")
    assert plan is None  # caller will treat as basic (1.0×)


@pytest.mark.anyio
async def test_check_rate_limit_raises_unavailable_on_redis_init_failure(monkeypatch):
    """When the Redis client itself can't be acquired, check_rate_limit must
    raise RateLimiterUnavailable so the middleware can switch to Mongo
    fallback (rather than silently fail-open and hide an infra outage).
    """
    from app.infrastructure import rate_limiter as rl

    async def _broken_redis():
        raise ConnectionError("simulated redis outage")

    monkeypatch.setattr(
        "app.infrastructure.redis_client.get_async_redis", _broken_redis
    )

    with pytest.raises(rl.RateLimiterUnavailable):
        await rl.check_rate_limit("k", "tenant_global", plan_slug="pro")


@pytest.mark.anyio
async def test_check_rate_limit_raises_unavailable_on_script_load_outage(monkeypatch):
    """If Redis is reachable for client init but `script_load` fails with a
    connection-class error, check_rate_limit must STILL raise
    RateLimiterUnavailable so the middleware can fall back. Previously this
    path was caught by the outer broad except and silently failed open.
    """
    from app.infrastructure import rate_limiter as rl

    class _FakeRedis:
        async def script_load(self, *args, **kwargs):
            raise ConnectionError("simulated redis outage during script_load")

    async def _ok_redis():
        return _FakeRedis()

    monkeypatch.setattr(
        "app.infrastructure.redis_client.get_async_redis", _ok_redis
    )
    # Force a fresh script-load attempt by clearing the cached SHA.
    monkeypatch.setattr(rl, "_lua_sha", None)

    with pytest.raises(rl.RateLimiterUnavailable):
        await rl.check_rate_limit("k", "tenant_global", plan_slug="enterprise")


@pytest.mark.anyio
async def test_check_rate_limit_fail_open_when_redis_disabled(monkeypatch):
    """When Redis is intentionally disabled (get_async_redis returns None),
    check_rate_limit must fail-open WITHOUT raising — unlike an outage.
    """
    from app.infrastructure import rate_limiter as rl

    async def _redis_disabled():
        return None

    monkeypatch.setattr(
        "app.infrastructure.redis_client.get_async_redis", _redis_disabled
    )

    result = await rl.check_rate_limit("k", "tenant_global")
    assert result.allowed is True
    assert result.remaining == -1


@pytest.mark.anyio
async def test_resolve_org_plan_handles_missing_org(monkeypatch):
    from app.middleware import rate_limit_middleware as mw

    mw._PLAN_CACHE.clear()

    class _EmptyOrgs:
        async def find_one(self, *args, **kwargs):
            return None

    class _FakeDB:
        organizations = _EmptyOrgs()

    async def _fake_get_db():
        return _FakeDB()

    monkeypatch.setattr("app.db.get_db", _fake_get_db)

    plan = await mw._resolve_org_plan("org_missing")
    assert plan is None
