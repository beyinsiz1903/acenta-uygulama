"""PMS cancellation requires an explicit positive acknowledgement."""
import asyncio

import httpx
import pytest

from app.services.syroce import agent
from app.services.syroce.errors import SyroceError


@pytest.mark.parametrize("status,content", [
    (200, b"{}"), (200, b'{"ok":false}'), (200, b'{"ok":"true"}'),
    (200, b'{"ok":1}'), (200, b"[]"), (200, b"null"),
    (200, b"<html>proxy error</html>"), (204, b""), (302, b"{}"),
    (503, b'{"detail":"unavailable"}'),
])
def test_ambiguous_cancellation_is_not_success(monkeypatch, status, content):
    monkeypatch.setenv("SYROCE_BASE_URL", "https://pms.example")
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, content=content)

    real_client = httpx.AsyncClient
    monkeypatch.setattr(agent.httpx, "AsyncClient", lambda **kw: real_client(
        transport=httpx.MockTransport(handler), **kw))
    client = agent.SyroceAgentClient(organization_id="org-1", api_key="test-key")
    with pytest.raises(SyroceError) as caught:
        asyncio.run(client.cancel_reservation("reservation-1", reason="customer_request"))
    assert caught.value.http_status == (503 if status == 503 else 502)
    assert len(calls) == 1  # No automatic retry of an ambiguous write.
    assert calls[0].method == "DELETE"
    assert calls[0].url.path == "/api/marketplace/v1/reservations/reservation-1"
    assert calls[0].url.params["reason"] == "customer_request"


@pytest.mark.parametrize("message", ["Rezervasyon iptal edildi", "Rezervasyon zaten iptal edilmiş"])
def test_confirmed_and_already_cancelled_acknowledgements_are_accepted(monkeypatch, message):
    monkeypatch.setenv("SYROCE_BASE_URL", "https://pms.example")
    response = {"ok": True, "message": message}
    real_client = httpx.AsyncClient
    monkeypatch.setattr(agent.httpx, "AsyncClient", lambda **kw: real_client(
        transport=httpx.MockTransport(lambda req: httpx.Response(200, json=response)), **kw))
    client = agent.SyroceAgentClient(organization_id="org-1", api_key="test-key")
    assert asyncio.run(client.cancel_reservation("reservation-1")) == response
