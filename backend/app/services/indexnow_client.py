from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class IndexNowSettings:
    """Lightweight settings holder for IndexNow integration.

    Uses plain environment variable access to avoid adding extra config
    complexity. Behaviour:
    - If INDEXNOW_ENABLED is not "1", submissions are treated as disabled.
    - If enabled but INDEXNOW_KEY or INDEXNOW_SITE_HOST are missing, we
      gracefully skip submissions ("not_configured").
    """

    def __init__(self) -> None:
        self.enabled_raw = os.environ.get("INDEXNOW_ENABLED", "0")
        self.key = os.environ.get("INDEXNOW_KEY")
        # Use explicit SITE_HOST env to avoid coupling to request.host alone
        self.site_host = os.environ.get("INDEXNOW_SITE_HOST")
        self.endpoint = os.environ.get("INDEXNOW_ENDPOINT", "https://api.indexnow.org/indexnow")
        try:
            self.timeout_seconds = int(os.environ.get("INDEXNOW_TIMEOUT_SECONDS", "10"))
        except ValueError:
            self.timeout_seconds = 10

    @property
    def enabled(self) -> bool:
        return self.enabled_raw in {"1", "true", "TRUE", "yes", "on"}

    def is_configured(self) -> bool:
        return self.enabled and bool(self.key and self.site_host)


class IndexNowClient:
    """Async HTTP client wrapper for IndexNow submissions.

    This client is designed to be used from background jobs. If IndexNow is
    disabled or not fully configured, it returns "skipped" results so that
    the job system can mark the job as completed without retries.
    """

    def __init__(self, settings: Optional[IndexNowSettings] = None) -> None:
        self.settings = settings or IndexNowSettings()
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            timeout = httpx.Timeout(
                timeout=float(self.settings.timeout_seconds),
                connect=5.0,
                read=float(self.settings.timeout_seconds),
                write=5.0,
                pool=5.0,
            )
            self._client = httpx.AsyncClient(timeout=timeout, headers={"Content-Type": "application/json"})
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def submit_single_url(self, url: str) -> Dict[str, Any]:
        """Submit a single URL via GET endpoint.

        Returns a small dict that the job platform can use to decide whether to
        retry or mark as completed. Does not raise for network errors; instead
        encodes them into the result payload.
        """

        if not self.settings.enabled:
            logger.info("IndexNow disabled; skipping submission for %s", url)
            return {"status": "skipped", "reason": "disabled"}

        if not self.settings.is_configured():
            logger.warning("IndexNow not fully configured; skipping submission for %s", url)
            return {"status": "skipped", "reason": "not_configured"}

        client = await self._get_client()

        try:
            resp = await client.get(
                self.settings.endpoint,
                params={"url": url, "key": self.settings.key},
            )
            logger.info("IndexNow single submit %s -> %s", url, resp.status_code)
            if resp.status_code == 200:
                return {"status": "success", "status_code": 200}
            return {
                "status": "error",
                "status_code": resp.status_code,
                "response_text": resp.text[:500],
            }
        except httpx.TimeoutException as exc:  # type: ignore[attr-defined]
            logger.error("IndexNow timeout for %s: %s", url, exc)
            return {"status": "error", "error_type": "timeout", "message": str(exc)}
        except httpx.RequestError as exc:
            logger.error("IndexNow request error for %s: %s", url, exc)
            return {"status": "error", "error_type": "request_error", "message": str(exc)}
        except Exception as exc:  # pragma: no cover - safety net
            logger.error("Unexpected IndexNow error for %s: %s", url, exc)
            return {"status": "error", "error_type": "unexpected", "message": str(exc)}

    async def submit_batch(self, urls: List[str]) -> Dict[str, Any]:
        """Submit multiple URLs via JSON payload.

        Follows IndexNow batch format with host/key/keyLocation.
        """

        if not self.settings.enabled:
            logger.info("IndexNow disabled; skipping batch of %d URLs", len(urls))
            return {"status": "skipped", "reason": "disabled"}

        if not self.settings.is_configured():
            logger.warning("IndexNow not fully configured; skipping batch of %d URLs", len(urls))
            return {"status": "skipped", "reason": "not_configured"}

        if not urls:
            return {"status": "skipped", "reason": "empty"}

        if len(urls) > 10000:
            urls = urls[:10000]

        client = await self._get_client()

        payload: Dict[str, Any] = {
            "host": self.settings.site_host,
            "key": self.settings.key,
            "keyLocation": f"https://{self.settings.site_host}/{self.settings.key}.txt",
            "urlList": urls,
        }

        try:
            resp = await client.post(self.settings.endpoint, json=payload)
            logger.info("IndexNow batch submit %d URLs -> %s", len(urls), resp.status_code)
            if resp.status_code == 200:
                return {"status": "success", "status_code": 200, "url_count": len(urls)}
            return {
                "status": "error",
                "status_code": resp.status_code,
                "response_text": resp.text[:500],
                "url_count": len(urls),
            }
        except httpx.TimeoutException as exc:  # type: ignore[attr-defined]
            logger.error("IndexNow batch timeout (%d URLs): %s", len(urls), exc)
            return {
                "status": "error",
                "error_type": "timeout",
                "message": str(exc),
                "url_count": len(urls),
            }
        except httpx.RequestError as exc:
            logger.error("IndexNow batch request error (%d URLs): %s", len(urls), exc)
            return {
                "status": "error",
                "error_type": "request_error",
                "message": str(exc),
                "url_count": len(urls),
            }
        except Exception as exc:  # pragma: no cover - safety net
            logger.error("Unexpected IndexNow batch error (%d URLs): %s", len(urls), exc)
            return {
                "status": "error",
                "error_type": "unexpected",
                "message": str(exc),
                "url_count": len(urls),
            }
