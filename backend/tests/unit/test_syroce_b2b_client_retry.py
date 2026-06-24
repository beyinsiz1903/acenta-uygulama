"""DB-free unit tests for Syroce PMS B2B client retry-safety + idempotency.

Locks in the Scenario B contract guarantees:
  - keyless (non-idempotent) writes FAIL CLOSED on ambiguous failures
    (timeout / network / 5xx) — no automatic retry, no double-apply.
  - GETs and keyed writes retry the SAME request on ambiguous failures.
  - 429 is treated as not-applied and retried (with Retry-After honoured).
  - permanent business statuses (401/402/403/404/409/422) never retry.
  - ``is_valid_key`` only accepts canonical UUIDs.

These tests monkeypatch ``httpx.AsyncClient`` so no network or DB is touched.
"""
from __future__ import annotations

import json as _json
import uuid

import httpx
import pytest

from app.services.syroce_b2b import client as client_mod
from app.services.syroce_b2b.client import SyroceB2BClient
from app.services.syroce_b2b.config import SyroceB2BConfig
from app.services.syroce_b2b.errors import SyroceB2BError
from app.services.syroce_b2b.idempotency import is_valid_key

pytestmark = pytest.mark.anyio


def _cfg() -> SyroceB2BConfig:
    return SyroceB2BConfig(
        base_url="https://pms.example/api/b2b", tenant_id="t1", api_key_env=""
    )


def _make_client() -> SyroceB2BClient:
    return SyroceB2BClient(api_key="k-secret", config=_cfg(), timeout=1.0)


class _FakeResp:
    def __init__(self, status_code: int, json_data=None, headers=None):
        self.status_code = status_code
        self._json = json_data
        self.headers = headers or {}
        self.content = _json.dumps(json_data).encode() if json_data is not None else b""

    def json(self):
        if self._json is None:
            raise ValueError("no json")
        return self._json


class _FakeAsyncClient:
    """Replays a class-level list of behaviors (callables) one per request()."""

    behaviors: list = []
    calls: list = []

    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def request(self, method, url, headers=None, params=None, json=None):
        idx = len(_FakeAsyncClient.calls)
        _FakeAsyncClient.calls.append({"method": method, "headers": headers or {}, "json": json})
        behavior = _FakeAsyncClient.behaviors[min(idx, len(_FakeAsyncClient.behaviors) - 1)]
        return behavior()


@pytest.fixture(autouse=True)
def _patch_httpx_and_sleep(monkeypatch):
    _FakeAsyncClient.behaviors = []
    _FakeAsyncClient.calls = []
    monkeypatch.setattr(client_mod.httpx, "AsyncClient", _FakeAsyncClient)
    # Zero the backoff so retries run instantly. We deliberately do NOT patch the
    # global ``asyncio.sleep`` (that would break anyio's own event loop) —
    # ``asyncio.sleep(0)`` already returns immediately.
    monkeypatch.setattr(client_mod, "_BACKOFF_BASE", 0.0)
    monkeypatch.setattr(client_mod, "_DEFAULT_RETRY_AFTER", 0.0)
    yield


def _raise_timeout():
    raise httpx.TimeoutException("boom")


def _raise_network():
    raise httpx.ConnectError("refused")


def _resp(status, body=None, headers=None):
    return lambda: _FakeResp(status, body, headers)


# ── keyless writes fail closed ───────────────────────────────────

async def test_keyless_post_timeout_does_not_retry():
    _FakeAsyncClient.behaviors = [_raise_timeout]
    c = _make_client()
    with pytest.raises(SyroceB2BError) as ei:
        await c.add_folio_charge("bk1", {"amount": 10})
    assert ei.value.code == "timeout"
    assert len(_FakeAsyncClient.calls) == 1  # no retry


async def test_keyless_post_5xx_does_not_retry():
    _FakeAsyncClient.behaviors = [_resp(503, {"error": {"message": "down"}})]
    c = _make_client()
    with pytest.raises(SyroceB2BError) as ei:
        await c.register_webhook({"url": "https://x", "events": ["a"]})
    assert ei.value.http_status == 503
    assert len(_FakeAsyncClient.calls) == 1


async def test_keyless_put_network_error_does_not_retry():
    _FakeAsyncClient.behaviors = [_raise_network]
    c = _make_client()
    with pytest.raises(SyroceB2BError):
        await c.cancel_reservation("r1")
    assert len(_FakeAsyncClient.calls) == 1


# ── GET + keyed writes retry the same request ────────────────────

async def test_get_retries_on_timeout_then_succeeds():
    _FakeAsyncClient.behaviors = [_raise_timeout, _resp(200, {"room_types": []})]
    c = _make_client()
    out = await c.get_availability(check_in="2026-07-01", check_out="2026-07-02")
    assert out == {"room_types": []}
    assert len(_FakeAsyncClient.calls) == 2


async def test_reservation_retries_with_same_key():
    key = str(uuid.uuid4())
    _FakeAsyncClient.behaviors = [_resp(503, {"error": {"message": "x"}}), _resp(201, {"id": "R1"})]
    c = _make_client()
    out = await c.create_reservation({"room_type": "std"}, idempotency_key=key)
    assert out["id"] == "R1"
    assert len(_FakeAsyncClient.calls) == 2
    # Same Idempotency-Key sent on BOTH attempts.
    assert _FakeAsyncClient.calls[0]["headers"]["Idempotency-Key"] == key
    assert _FakeAsyncClient.calls[1]["headers"]["Idempotency-Key"] == key


async def test_429_retries_after_retry_after():
    _FakeAsyncClient.behaviors = [
        _resp(429, {}, {"Retry-After": "0"}),
        _resp(200, {"ok": True}),
    ]
    c = _make_client()
    out = await c.get_rates(start_date="2026-07-01", end_date="2026-07-05")
    assert out == {"ok": True}
    assert len(_FakeAsyncClient.calls) == 2


# ── permanent business errors never retry ────────────────────────

@pytest.mark.parametrize("status", [400, 401, 402, 403, 404, 409, 422])
async def test_permanent_status_no_retry(status):
    key = str(uuid.uuid4())
    _FakeAsyncClient.behaviors = [_resp(status, {"error": {"message": "no"}})]
    c = _make_client()
    with pytest.raises(SyroceB2BError) as ei:
        await c.create_reservation({"room_type": "std"}, idempotency_key=key)
    assert ei.value.http_status == status
    assert ei.value.retryable is False
    assert len(_FakeAsyncClient.calls) == 1


async def test_create_reservation_requires_key():
    c = _make_client()
    with pytest.raises(SyroceB2BError) as ei:
        await c.create_reservation({"room_type": "std"}, idempotency_key="")
    assert ei.value.http_status == 422
    assert len(_FakeAsyncClient.calls) == 0  # never sent


# ── is_valid_key ─────────────────────────────────────────────────

def test_is_valid_key_accepts_uuid():
    assert is_valid_key(str(uuid.uuid4())) is True


@pytest.mark.parametrize("bad", [None, "", "not-a-uuid", "1234", "g" * 36])
def test_is_valid_key_rejects_non_uuid(bad):
    assert is_valid_key(bad) is False
