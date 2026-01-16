from __future__ import annotations

from typing import Any, Dict, List

from fastapi import Header, HTTPException, Request

from app.auth import load_org_doc, resolve_org_features
from app.services.api_keys import resolve_api_key
from app.services.rate_limit import enforce_rate_limit


def require_partner_key(scopes: List[str]):
    """Factory returning FastAPI dependency for Partner API.

    Usage:
        partner = Depends(require_partner_key(["products:read"]))
    """

    async def _dep(
        x_api_key: str = Header("", alias="X-API-Key"),
        request: Request = None,
    ) -> Dict[str, Any]:
        api_key_doc = await resolve_api_key(x_api_key)
        if not api_key_doc:
            raise HTTPException(status_code=401, detail="INVALID_API_KEY")

        org_id = api_key_doc.get("organization_id")
        key_scopes = api_key_doc.get("scopes") or []
        key_name = api_key_doc.get("name") or ""

        # Enforce required scopes at API-key level
        missing = [s for s in scopes if s not in key_scopes]
        if missing:
            raise HTTPException(status_code=403, detail="INSUFFICIENT_SCOPE")

        # Feature-gate via organization document (no JWT required)
        if org_id:
            org_doc = await load_org_doc(org_id)
            if not org_doc:
                raise HTTPException(status_code=404, detail="Organization not found")
            features = resolve_org_features(org_doc)
            if not bool(features.get("partner_api", False)):
                # 403 instead of 404 here so callers can distinguish feature-off
                raise HTTPException(status_code=403, detail="PARTNER_API_DISABLED")

        ip = ""
        if request is not None and request.client:
            ip = request.client.host or ""

        await enforce_rate_limit(
            organization_id=org_id,
            key_id=key_name or "unknown",
            ip=ip,
        )

        return {
            "organization_id": org_id,
            "key_name": key_name,
            "scopes": key_scopes,
        }

    return _dep
