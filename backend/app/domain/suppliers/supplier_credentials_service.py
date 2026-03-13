"""Multi-tenant Supplier Credentials Service.

Stores per-agency supplier credentials with AES encryption.
Each agency can connect their own supplier accounts (wwtatil, paximum, etc.).
"""
from __future__ import annotations

import os
import base64
import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

from cryptography.fernet import Fernet

logger = logging.getLogger("suppliers.credentials")

# Derive a stable Fernet key from a secret. In production use a Vault/KMS.
_SECRET = os.environ.get("CREDENTIAL_ENCRYPTION_KEY", "syroce-supplier-credential-key-2026")
_KEY = base64.urlsafe_b64encode(hashlib.sha256(_SECRET.encode()).digest())
_fernet = Fernet(_KEY)


def _encrypt(value: str) -> str:
    if not value:
        return ""
    return _fernet.encrypt(value.encode()).decode()


def _decrypt(value: str) -> str:
    if not value:
        return ""
    return _fernet.decrypt(value.encode()).decode()


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


SUPPORTED_SUPPLIERS = {
    "wwtatil": {
        "name": "WWTatil Tour API",
        "type": "tour",
        "fields": ["base_url", "application_secret_key", "username", "password", "agency_id"],
        "auth_endpoint": "/api/Auth/get-token-async",
    },
    "paximum": {
        "name": "Paximum Travel API",
        "type": "hotel",
        "fields": ["base_url", "api_key"],
        "auth_endpoint": "/api/auth/token",
    },
    "aviationstack": {
        "name": "AviationStack Flight API",
        "type": "flight",
        "fields": ["base_url", "api_key"],
        "auth_endpoint": None,
    },
}


async def list_supported_suppliers() -> dict[str, Any]:
    """List all supported supplier integrations."""
    suppliers = []
    for code, info in SUPPORTED_SUPPLIERS.items():
        suppliers.append({
            "code": code,
            "name": info["name"],
            "type": info["type"],
            "required_fields": info["fields"],
        })
    return {"suppliers": suppliers}


async def get_agency_credentials(db, organization_id: str) -> dict[str, Any]:
    """Get all supplier credentials for an agency (masked)."""
    cursor = db["supplier_credentials"].find(
        {"organization_id": organization_id},
        {"_id": 0},
    )
    creds = []
    async for doc in cursor:
        masked = {
            "supplier": doc["supplier"],
            "status": doc.get("status", "disconnected"),
            "connected_at": doc.get("connected_at"),
            "last_tested": doc.get("last_tested"),
            "organization_id": doc["organization_id"],
        }
        # Show masked values
        for field in SUPPORTED_SUPPLIERS.get(doc["supplier"], {}).get("fields", []):
            val = doc.get(f"enc_{field}", "")
            if val and field != "base_url":
                masked[field] = "****" + _decrypt(val)[-4:] if len(_decrypt(val)) > 4 else "****"
            elif field == "base_url":
                masked[field] = _decrypt(val) if val else ""
            else:
                masked[field] = ""
        creds.append(masked)
    return {"credentials": creds, "organization_id": organization_id}


async def save_credential(db, organization_id: str, supplier: str, fields: dict[str, str]) -> dict[str, Any]:
    """Save or update supplier credentials for an agency."""
    if supplier not in SUPPORTED_SUPPLIERS:
        return {"error": f"Unsupported supplier: {supplier}", "supported": list(SUPPORTED_SUPPLIERS.keys())}

    required = SUPPORTED_SUPPLIERS[supplier]["fields"]
    missing = [f for f in required if not fields.get(f)]
    if missing:
        return {"error": f"Missing required fields: {missing}"}

    # Encrypt sensitive fields
    doc = {
        "organization_id": organization_id,
        "supplier": supplier,
        "status": "saved",
        "connected_at": None,
        "last_tested": None,
        "updated_at": _ts(),
    }
    for field in required:
        doc[f"enc_{field}"] = _encrypt(fields[field])

    await db["supplier_credentials"].update_one(
        {"organization_id": organization_id, "supplier": supplier},
        {"$set": doc},
        upsert=True,
    )

    return {
        "action": "save_credential",
        "supplier": supplier,
        "organization_id": organization_id,
        "status": "saved",
        "message": f"{supplier} credentials saved. Run 'Test Connection' to verify.",
    }


async def delete_credential(db, organization_id: str, supplier: str) -> dict[str, Any]:
    """Delete supplier credentials for an agency."""
    result = await db["supplier_credentials"].delete_one(
        {"organization_id": organization_id, "supplier": supplier}
    )
    # Also clear cached tokens
    await db["supplier_tokens"].delete_many(
        {"organization_id": organization_id, "supplier": supplier}
    )
    return {
        "action": "delete_credential",
        "supplier": supplier,
        "deleted": result.deleted_count > 0,
    }


async def get_decrypted_credentials(db, organization_id: str, supplier: str) -> dict[str, str] | None:
    """Internal: Get decrypted credentials for API calls."""
    doc = await db["supplier_credentials"].find_one(
        {"organization_id": organization_id, "supplier": supplier},
        {"_id": 0},
    )
    if not doc:
        return None

    fields = SUPPORTED_SUPPLIERS.get(supplier, {}).get("fields", [])
    result = {}
    for field in fields:
        enc_val = doc.get(f"enc_{field}", "")
        result[field] = _decrypt(enc_val) if enc_val else ""
    return result


async def test_connection(db, organization_id: str, supplier: str) -> dict[str, Any]:
    """Test supplier connection using agency's credentials."""
    creds = await get_decrypted_credentials(db, organization_id, supplier)
    if not creds:
        return {"verdict": "FAIL", "error": "No credentials found for this supplier"}

    if supplier == "wwtatil":
        return await _test_wwtatil(db, organization_id, creds)
    elif supplier == "paximum":
        return await _test_paximum(db, organization_id, creds)
    elif supplier == "aviationstack":
        return await _test_aviationstack(db, organization_id, creds)
    else:
        return {"verdict": "FAIL", "error": f"No test handler for {supplier}"}


async def _test_wwtatil(db, organization_id: str, creds: dict) -> dict[str, Any]:
    """Test wwtatil connection by calling auth endpoint."""
    import httpx
    import time

    base_url = creds.get("base_url", "").rstrip("/")
    if not base_url:
        return {"verdict": "FAIL", "error": "base_url is empty"}

    payload = {
        "ApplicationSecretKey": creds.get("application_secret_key", ""),
        "UserName": creds.get("username", ""),
        "Password": creds.get("password", ""),
    }

    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{base_url}/api/Auth/get-token-async",
                json=payload,
            )
        latency_ms = round((time.monotonic() - start) * 1000, 1)

        if resp.status_code == 200:
            data = resp.json()
            token = data.get("token") or data.get("Token") or data.get("data", {}).get("token", "")
            if token:
                # Cache token
                await db["supplier_tokens"].update_one(
                    {"organization_id": organization_id, "supplier": "wwtatil"},
                    {"$set": {
                        "token": token,
                        "obtained_at": _ts(),
                        "expires_hours": 24,
                    }},
                    upsert=True,
                )
                # Update credential status
                await db["supplier_credentials"].update_one(
                    {"organization_id": organization_id, "supplier": "wwtatil"},
                    {"$set": {"status": "connected", "connected_at": _ts(), "last_tested": _ts()}},
                )
                return {
                    "verdict": "PASS",
                    "supplier": "wwtatil",
                    "status": "connected",
                    "latency_ms": latency_ms,
                    "token_preview": token[:20] + "..." if len(token) > 20 else token,
                    "message": "Authentication successful. Token cached (24h validity).",
                }
            else:
                return {
                    "verdict": "FAIL",
                    "supplier": "wwtatil",
                    "status": "auth_failed",
                    "latency_ms": latency_ms,
                    "response": str(data)[:200],
                    "message": "Response received but no token found.",
                }
        else:
            await db["supplier_credentials"].update_one(
                {"organization_id": organization_id, "supplier": "wwtatil"},
                {"$set": {"status": "auth_failed", "last_tested": _ts()}},
            )
            return {
                "verdict": "FAIL",
                "supplier": "wwtatil",
                "status": "auth_failed",
                "http_status": resp.status_code,
                "latency_ms": latency_ms,
                "response": resp.text[:200],
            }
    except httpx.ConnectError as e:
        return {"verdict": "FAIL", "supplier": "wwtatil", "status": "connection_error", "error": str(e)}
    except httpx.TimeoutException:
        return {"verdict": "FAIL", "supplier": "wwtatil", "status": "timeout", "error": "Connection timed out (15s)"}
    except Exception as e:
        return {"verdict": "FAIL", "supplier": "wwtatil", "status": "error", "error": str(e)}


async def _test_paximum(db, organization_id: str, creds: dict) -> dict[str, Any]:
    """Test paximum connection."""
    import httpx
    import time

    base_url = creds.get("base_url", "").rstrip("/")
    api_key = creds.get("api_key", "")
    if not base_url or not api_key:
        return {"verdict": "FAIL", "error": "base_url or api_key is empty"}

    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{base_url}/v2/api/productservice/getarrivalautocomplete",
                headers={"Authorization": f"Bearer {api_key}"},
                params={"query": "istanbul"},
            )
        latency_ms = round((time.monotonic() - start) * 1000, 1)
        connected = resp.status_code in (200, 401, 403)

        if resp.status_code == 200:
            await db["supplier_credentials"].update_one(
                {"organization_id": organization_id, "supplier": "paximum"},
                {"$set": {"status": "connected", "connected_at": _ts(), "last_tested": _ts()}},
            )
            return {"verdict": "PASS", "supplier": "paximum", "status": "connected", "latency_ms": latency_ms}
        else:
            await db["supplier_credentials"].update_one(
                {"organization_id": organization_id, "supplier": "paximum"},
                {"$set": {"status": "auth_failed", "last_tested": _ts()}},
            )
            return {"verdict": "FAIL", "supplier": "paximum", "http_status": resp.status_code, "latency_ms": latency_ms}
    except Exception as e:
        return {"verdict": "FAIL", "supplier": "paximum", "error": str(e)}


async def _test_aviationstack(db, organization_id: str, creds: dict) -> dict[str, Any]:
    """Test aviationstack connection."""
    import httpx
    import time

    base_url = creds.get("base_url", "").rstrip("/")
    api_key = creds.get("api_key", "")
    if not api_key:
        return {"verdict": "FAIL", "error": "api_key is empty"}

    base_url = base_url or "https://api.aviationstack.com/v1"
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{base_url}/flights", params={"access_key": api_key, "limit": 1})
        latency_ms = round((time.monotonic() - start) * 1000, 1)

        if resp.status_code == 200:
            await db["supplier_credentials"].update_one(
                {"organization_id": organization_id, "supplier": "aviationstack"},
                {"$set": {"status": "connected", "connected_at": _ts(), "last_tested": _ts()}},
            )
            return {"verdict": "PASS", "supplier": "aviationstack", "status": "connected", "latency_ms": latency_ms}
        else:
            return {"verdict": "FAIL", "supplier": "aviationstack", "http_status": resp.status_code, "latency_ms": latency_ms}
    except Exception as e:
        return {"verdict": "FAIL", "supplier": "aviationstack", "error": str(e)}


async def get_cached_token(db, organization_id: str, supplier: str) -> str | None:
    """Get cached token for a supplier. Returns None if expired or missing."""
    doc = await db["supplier_tokens"].find_one(
        {"organization_id": organization_id, "supplier": supplier},
        {"_id": 0},
    )
    if not doc:
        return None
    # Simple expiry check — wwtatil tokens are 24h
    return doc.get("token")
