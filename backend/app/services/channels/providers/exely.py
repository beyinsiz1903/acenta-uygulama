from __future__ import annotations

import time
from typing import Any, Dict
from urllib.parse import urljoin

import httpx

from app.services.channels.providers.base import BaseChannelProvider
from app.services.channels.types import ChannelAriResult, ChannelTestResult

from datetime import date



class ExelyChannelProvider(BaseChannelProvider):
  """Exely adapter with real HTTP-based test_connection.

  Behaviour:
    - Requires a non-empty API key.
    - Requires a base_url coming either from credentials.base_url or
      settings.base_url.
    - Optionally uses settings.test_path (default "/ping") as the relative
      ping endpoint.
    - Performs a GET request with Authorization / X-API-Key headers and maps
      HTTP responses to ChannelTestResult codes.
  """

  provider_name = "exely"

  def _get_base_url(self, connector: Dict[str, Any]) -> str:
    creds = connector.get("credentials") or {}
    settings = connector.get("settings") or {}

    base_url = (
      (isinstance(creds, dict) and creds.get("base_url"))
      or (isinstance(settings, dict) and settings.get("base_url"))
      or ""
    )
    return str(base_url).strip()

  def _get_test_path(self, connector: Dict[str, Any]) -> str:
    settings = connector.get("settings") or {}
    test_path = (isinstance(settings, dict) and settings.get("test_path")) or "/ping"
    test_path = str(test_path).strip() or "/ping"
    return test_path

  def _get_api_key(self, connector: Dict[str, Any]) -> str:
    creds = connector.get("credentials") or {}
    api_key = (isinstance(creds, dict) and creds.get("api_key")) or ""
    return str(api_key).strip()

  async def test_connection(self, *, connector: Dict[str, Any]) -> ChannelTestResult:
    api_key = self._get_api_key(connector)
    if not api_key:
      return ChannelTestResult(
        ok=False,
        code="AUTH_FAILED",
        message="Exely API key boş veya geçersiz.",
        meta={"provider": self.provider_name},
      )

    base_url = self._get_base_url(connector)
    if not base_url:
      # Do not pretend connection is fine without a concrete base URL.
      return ChannelTestResult(
        ok=False,
        code="CONFIG_ERROR",
        message=(
          "Exely base_url tanımlı değil. "
          "credentials.base_url veya settings.base_url alanını doldurun."
        ),
        meta={"provider": self.provider_name},
      )

    test_path = self._get_test_path(connector)

    # Normalize URL
    if not base_url.endswith("/"):
      base_url = base_url + "/"
    url = urljoin(base_url, test_path.lstrip("/"))

    headers = {
      "Accept": "application/json",
      "User-Agent": "Syroce-ChannelHub/1.0",
      "Authorization": f"Bearer {api_key}",
      "X-API-Key": api_key,
    }

    timeout_s = 5.0
    started = time.perf_counter()

    try:
      async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_s)) as client:
        resp = await client.get(url, headers=headers)
    except httpx.TimeoutException:
      latency_ms = int((time.perf_counter() - started) * 1000)
      return ChannelTestResult(
        ok=False,
        code="TIMEOUT",
        message="Exely servisine erişim zaman aşımına uğradı.",
        meta={
          "provider": self.provider_name,
          "endpoint": url,
          "latency_ms": latency_ms,
        },
      )
    except httpx.RequestError as e:
      latency_ms = int((time.perf_counter() - started) * 1000)
      return ChannelTestResult(
        ok=False,
        code="PROVIDER_UNAVAILABLE",
        message=f"Exely servisine erişilemiyor: {str(e) or 'request error'}",
        meta={
          "provider": self.provider_name,
          "endpoint": url,
          "latency_ms": latency_ms,
        },
      )

    latency_ms = int((time.perf_counter() - started) * 1000)
    status = resp.status_code

    # Auth failure
    if status in (401, 403):
      return ChannelTestResult(
        ok=False,
        code="AUTH_FAILED",
        message=(
          "Exely kimlik doğrulama başarısız (401/403). "
          "API key veya yetkileri kontrol edin."
        ),
        meta={
          "provider": self.provider_name,
          "endpoint": url,
          "status_code": status,
          "latency_ms": latency_ms,
        },
      )

    # Provider unavailable / rate limited
    if status == 429 or 500 <= status <= 599:
      return ChannelTestResult(
        ok=False,
        code="PROVIDER_UNAVAILABLE",
        message=f"Exely geçici olarak erişilemiyor (HTTP {status}).",
        meta={
          "provider": self.provider_name,
          "endpoint": url,
          "status_code": status,
          "latency_ms": latency_ms,
        },
      )

    if 200 <= status <= 299:
      return ChannelTestResult(
        ok=True,
        code="OK",
        message="Exely bağlantısı doğrulandı.",
        meta={
          "provider": self.provider_name,
          "endpoint": url,
          "status_code": status,
          "latency_ms": latency_ms,
        },
      )

    # Fallback for unexpected status codes
    return ChannelTestResult(
      ok=False,
      code="UNKNOWN_ERROR",
      message=f"Beklenmeyen Exely yanıtı (HTTP {status}).",
      meta={
        "provider": self.provider_name,
        "endpoint": url,
        "status_code": status,
        "latency_ms": latency_ms,
      },
    )

  async def fetch_ari(self, *, connector: Dict[str, Any], from_date: date, to_date: date) -> ChannelAriResult:
    """Skeleton ARI read implementation for Exely.

    For now this performs a read-only HTTP GET against an optional
    `settings.ari_path` endpoint and returns the raw JSON (or text) payload in
    `data`.  No normalization or PMS writes are performed in this phase.
    """

    base_url = self._get_base_url(connector)
    if not base_url:
      return ChannelAriResult(
        ok=False,
        code="CONFIG_ERROR",
        message=(
          "Exely base_url tanımlı değil. "
          "credentials.base_url veya settings.base_url alanını doldurun."
        ),
        meta={"provider": self.provider_name},
      )

    settings = connector.get("settings") or {}
    ari_path = (isinstance(settings, dict) and settings.get("ari_path")) or "/ari"
    ari_path = str(ari_path).strip() or "/ari"

    if not base_url.endswith("/"):
      base_url = base_url + "/"
    url = urljoin(base_url, ari_path.lstrip("/"))

    api_key = self._get_api_key(connector)
    headers = {
      "Accept": "application/json",
      "User-Agent": "Syroce-ChannelHub/1.0",
    }
    if api_key:
      headers["Authorization"] = f"Bearer {api_key}"
      headers["X-API-Key"] = api_key

    timeout_s = 10.0
    started = time.perf_counter()

    try:
      async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_s)) as client:
        resp = await client.get(
          url,
          headers=headers,
          params={"from": from_date.isoformat(), "to": to_date.isoformat()},
        )
    except httpx.TimeoutException:
      latency_ms = int((time.perf_counter() - started) * 1000)
      return ChannelAriResult(
        ok=False,
        code="TIMEOUT",
        message="Exely ARI servisine erişim zaman aşımına uğradı.",
        meta={
          "provider": self.provider_name,
          "endpoint": url,
          "latency_ms": latency_ms,
        },
      )
    except httpx.RequestError as e:
      latency_ms = int((time.perf_counter() - started) * 1000)
      return ChannelAriResult(
        ok=False,
        code="PROVIDER_UNAVAILABLE",
        message=f"Exely ARI servisine erişilemiyor: {str(e) or 'request error'}",
        meta={
          "provider": self.provider_name,
          "endpoint": url,
          "latency_ms": latency_ms,
        },
      )

    latency_ms = int((time.perf_counter() - started) * 1000)
    status = resp.status_code

    try:
      payload = resp.json()
    except ValueError:
      payload = {"raw": resp.text}

    if 200 <= status <= 299:
      return ChannelAriResult(
        ok=True,
        code="OK",
        message="Exely ARI okuması başarılı.",
        data=payload,
        meta={
          "provider": self.provider_name,
          "endpoint": url,
          "status_code": status,
          "latency_ms": latency_ms,
        },
      )

    return ChannelAriResult(
      ok=False,
      code="UNKNOWN_ERROR",
      message=f"Beklenmeyen Exely ARI yanıtı (HTTP {status}).",
      data=payload,
      meta={
        "provider": self.provider_name,
        "endpoint": url,
        "status_code": status,
        "latency_ms": latency_ms,
      },
    )
