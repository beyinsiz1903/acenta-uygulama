from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import Lock
from typing import Any, Optional

import requests
from httpx import ASGITransport, AsyncClient

from server import app


CACHE_FILE = Path(os.environ.get("PREVIEW_AUTH_CACHE_FILE", "/tmp/acenta-preview-auth-cache.json"))
CACHE_TTL_SECONDS = int(os.environ.get("PREVIEW_AUTH_CACHE_TTL_SECONDS", "240"))
REQUEST_TIMEOUT_SECONDS = int(os.environ.get("PREVIEW_AUTH_TIMEOUT_SECONDS", "15"))
ALLOW_LOCAL_BOOTSTRAP = os.environ.get("PREVIEW_AUTH_ALLOW_LOCAL_BOOTSTRAP", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

_CACHE_LOCK = Lock()


def resolve_preview_base_url(base_url: str) -> str:
    normalized = (base_url or "").rstrip("/")
    if normalized:
        return normalized

    frontend_env = Path(__file__).resolve().parents[2] / "frontend" / ".env"
    if frontend_env.exists():
        for line in frontend_env.read_text().splitlines():
            if line.startswith("REACT_APP_BACKEND_URL="):
                resolved = line.split("=", 1)[1].strip().rstrip("/")
                if resolved:
                    return resolved

    raise PreviewAuthError("Preview base URL is not configured")


@dataclass
class PreviewAuthContext:
    base_url: str
    email: str
    access_token: str
    refresh_token: Optional[str]
    tenant_id: Optional[str]
    tenant_slug: Optional[str]
    session_id: Optional[str]
    cached_until: float
    auth_source: str
    login_response: dict[str, Any]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PreviewAuthContext":
        return cls(**payload)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PreviewAuthError(RuntimeError):
    pass


def _cache_key(base_url: str, email: str, tenant_id: Optional[str], tenant_slug: Optional[str]) -> str:
    return "::".join([base_url.rstrip("/"), email.strip().lower(), tenant_id or "", tenant_slug or ""])


def _read_cache() -> dict[str, dict[str, Any]]:
    if not CACHE_FILE.exists():
        return {}
    try:
        return json.loads(CACHE_FILE.read_text())
    except Exception:
        return {}


def _write_cache(cache: dict[str, dict[str, Any]]) -> None:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, indent=2, sort_keys=True))


def invalidate_preview_auth_context(
    base_url: str,
    email: str,
    *,
    tenant_id: Optional[str] = None,
    tenant_slug: Optional[str] = None,
) -> None:
    key = _cache_key(base_url, email, tenant_id, tenant_slug)
    with _CACHE_LOCK:
        cache = _read_cache()
        if key in cache:
            cache.pop(key, None)
            _write_cache(cache)


def _cache_window(expires_in: Any) -> int:
    try:
        expires = int(expires_in)
    except (TypeError, ValueError):
        expires = CACHE_TTL_SECONDS
    if expires <= 90:
        return max(30, expires)
    return max(30, min(CACHE_TTL_SECONDS, expires - 60))


def _build_context(
    *,
    base_url: str,
    email: str,
    tenant_id: Optional[str],
    tenant_slug: Optional[str],
    payload: dict[str, Any],
    auth_source: str,
) -> PreviewAuthContext:
    resolved_tenant_id = payload.get("tenant_id") or tenant_id
    return PreviewAuthContext(
        base_url=base_url.rstrip("/"),
        email=email.strip().lower(),
        access_token=str(payload["access_token"]),
        refresh_token=payload.get("refresh_token"),
        tenant_id=resolved_tenant_id,
        tenant_slug=tenant_slug,
        session_id=payload.get("session_id"),
        cached_until=time.time() + _cache_window(payload.get("expires_in")),
        auth_source=auth_source,
        login_response=payload,
    )


def _request_json(method: str, url: str, *, session: Optional[requests.Session] = None, **kwargs) -> requests.Response:
    client = session or requests.Session()
    timeout = kwargs.pop("timeout", REQUEST_TIMEOUT_SECONDS)
    return client.request(method, url, timeout=timeout, **kwargs)


def _preview_login(
    base_url: str,
    *,
    email: str,
    password: str,
    tenant_id: Optional[str],
    tenant_slug: Optional[str],
) -> PreviewAuthContext:
    payload: dict[str, Any] = {"email": email, "password": password}
    if tenant_id:
        payload["tenant_id"] = tenant_id
    if tenant_slug:
        payload["tenant_slug"] = tenant_slug

    response = _request_json("POST", f"{base_url.rstrip('/')}/api/auth/login", json=payload)
    if response.status_code == 200:
        return _build_context(
            base_url=base_url,
            email=email,
            tenant_id=tenant_id,
            tenant_slug=tenant_slug,
            payload=response.json(),
            auth_source="preview_login",
        )
    raise PreviewAuthError(f"Preview login failed: {response.status_code} - {response.text}")


def _preview_refresh(
    base_url: str,
    *,
    refresh_token: str,
    email: str,
    tenant_id: Optional[str],
    tenant_slug: Optional[str],
) -> Optional[PreviewAuthContext]:
    response = _request_json(
        "POST",
        f"{base_url.rstrip('/')}/api/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    if response.status_code != 200:
        return None
    payload = response.json()
    if refresh_token and not payload.get("refresh_token"):
        payload["refresh_token"] = refresh_token
    return _build_context(
        base_url=base_url,
        email=email,
        tenant_id=tenant_id,
        tenant_slug=tenant_slug,
        payload=payload,
        auth_source="preview_refresh",
    )


def _validate_cached_context(context: PreviewAuthContext) -> bool:
    response = _request_json(
        "GET",
        f"{context.base_url}/api/auth/me",
        headers={"Authorization": f"Bearer {context.access_token}"},
    )
    return response.status_code == 200


async def _local_login_async(payload: dict[str, Any]) -> dict[str, Any]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", timeout=REQUEST_TIMEOUT_SECONDS) as client:
        response = await client.post("/api/auth/login", json=payload)
    if response.status_code != 200:
        raise PreviewAuthError(f"Local ASGI login failed: {response.status_code} - {response.text}")
    return response.json()


def _local_login(
    base_url: str,
    *,
    email: str,
    password: str,
    tenant_id: Optional[str],
    tenant_slug: Optional[str],
) -> PreviewAuthContext:
    payload: dict[str, Any] = {"email": email, "password": password}
    if tenant_id:
        payload["tenant_id"] = tenant_id
    if tenant_slug:
        payload["tenant_slug"] = tenant_slug
    response_payload = asyncio.run(_local_login_async(payload))
    return _build_context(
        base_url=base_url,
        email=email,
        tenant_id=tenant_id,
        tenant_slug=tenant_slug,
        payload=response_payload,
        auth_source="local_asgi_fallback",
    )


def get_preview_auth_context(
    base_url: str,
    *,
    email: str,
    password: str,
    tenant_id: Optional[str] = None,
    tenant_slug: Optional[str] = None,
    force_relogin: bool = False,
) -> PreviewAuthContext:
    resolved_base_url = resolve_preview_base_url(base_url)
    key = _cache_key(resolved_base_url, email, tenant_id, tenant_slug)

    with _CACHE_LOCK:
        cache = _read_cache()
        cached_payload = cache.get(key)

    cached_context = PreviewAuthContext.from_dict(cached_payload) if cached_payload else None
    if cached_context and not force_relogin and cached_context.cached_until > time.time():
        return cached_context

    if cached_context and _validate_cached_context(cached_context):
        cached_context.cached_until = time.time() + CACHE_TTL_SECONDS
        with _CACHE_LOCK:
            cache = _read_cache()
            cache[key] = cached_context.to_dict()
            _write_cache(cache)
        return cached_context

    if cached_context and cached_context.refresh_token:
        refreshed = _preview_refresh(
            resolved_base_url,
            refresh_token=cached_context.refresh_token,
            email=email,
            tenant_id=tenant_id,
            tenant_slug=tenant_slug,
        )
        if refreshed is not None:
            with _CACHE_LOCK:
                cache = _read_cache()
                cache[key] = refreshed.to_dict()
                _write_cache(cache)
            return refreshed

    try:
        fresh = _preview_login(
            resolved_base_url,
            email=email,
            password=password,
            tenant_id=tenant_id,
            tenant_slug=tenant_slug,
        )
    except PreviewAuthError as exc:
        if not ALLOW_LOCAL_BOOTSTRAP or "429" not in str(exc):
            raise
        fresh = _local_login(
            resolved_base_url,
            email=email,
            password=password,
            tenant_id=tenant_id,
            tenant_slug=tenant_slug,
        )

    with _CACHE_LOCK:
        cache = _read_cache()
        cache[key] = fresh.to_dict()
        _write_cache(cache)
    return fresh


def build_preview_auth_headers(
    context: PreviewAuthContext,
    *,
    include_tenant: bool = False,
) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {context.access_token}"}
    if include_tenant and context.tenant_id:
        headers["X-Tenant-Id"] = context.tenant_id
    return headers


class PreviewAuthSession:
    def __init__(
        self,
        base_url: str,
        *,
        email: str,
        password: str,
        tenant_id: Optional[str] = None,
        tenant_slug: Optional[str] = None,
        include_tenant_header: bool = False,
        default_headers: Optional[dict[str, str]] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.base_url = resolve_preview_base_url(base_url)
        self.email = email
        self.password = password
        self.tenant_id = tenant_id
        self.tenant_slug = tenant_slug
        self.include_tenant_header = include_tenant_header
        self.session = requests.Session()
        if default_headers:
            self.session.headers.update(default_headers)

    def invalidate(self) -> None:
        invalidate_preview_auth_context(
            self.base_url,
            self.email,
            tenant_id=self.tenant_id,
            tenant_slug=self.tenant_slug,
        )

    def auth_context(self, *, force_relogin: bool = False) -> PreviewAuthContext:
        return get_preview_auth_context(
            self.base_url,
            email=self.email,
            password=self.password,
            tenant_id=self.tenant_id,
            tenant_slug=self.tenant_slug,
            force_relogin=force_relogin,
        )

    def request(self, method: str, path: str, **kwargs) -> requests.Response:
        context = self.auth_context()
        headers = dict(self.session.headers)
        headers.update(kwargs.pop("headers", {}))
        headers.update(build_preview_auth_headers(context, include_tenant=self.include_tenant_header))
        target_url = path if path.startswith(("http://", "https://")) else f"{self.base_url}{path}"
        response = self.session.request(method, target_url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS, **kwargs)
        if response.status_code != 401:
            return response

        self.invalidate()
        refreshed = self.auth_context(force_relogin=True)
        retry_headers = dict(self.session.headers)
        retry_headers.update(headers)
        retry_headers.update(build_preview_auth_headers(refreshed, include_tenant=self.include_tenant_header))
        return self.session.request(method, target_url, headers=retry_headers, timeout=REQUEST_TIMEOUT_SECONDS, **kwargs)

    def get(self, path: str, **kwargs) -> requests.Response:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> requests.Response:
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs) -> requests.Response:
        return self.request("PUT", path, **kwargs)

    def patch(self, path: str, **kwargs) -> requests.Response:
        return self.request("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs) -> requests.Response:
        return self.request("DELETE", path, **kwargs)