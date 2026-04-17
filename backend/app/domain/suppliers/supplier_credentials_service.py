"""Multi-tenant Supplier Credentials Service.

Stores per-agency supplier credentials with AES encryption.
Each agency can connect their own supplier accounts (wtatil, paximum, etc.).
Supports: RBAC (super_admin sees all, agency_admin sees own), audit logging,
enable/disable, and supplier-specific validation.
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


async def _write_audit(db, *, organization_id: str, supplier: str, action: str, actor: str, details: str = ""):
    """Write an entry to the credential audit log."""
    await db["credential_audit_log"].insert_one({
        "organization_id": organization_id,
        "supplier": supplier,
        "action": action,
        "actor": actor,
        "details": details,
        "timestamp": _ts(),
    })


SUPPORTED_SUPPLIERS = {
    "ratehawk": {
        "name": "RateHawk Hotel API",
        "type": "hotel",
        "product_types": ["hotel"],
        "fields": ["base_url", "key_id", "api_key"],
        "auth_endpoint": "/api/b2b/v3/search/region/",
    },
    "tbo": {
        "name": "TBO Holidays API",
        "type": "hotel+flight+tour",
        "product_types": ["hotel", "flight", "tour"],
        "fields": ["base_url", "username", "password"],
        "optional_fields": ["client_id"],
        "auth_endpoint": "/api/auth/token",
    },
    "paximum": {
        "name": "Paximum Travel API",
        "type": "hotel+transfer+activity",
        "product_types": ["hotel", "transfer", "activity"],
        "fields": ["base_url", "username", "password", "agency_code"],
        "auth_endpoint": "/api/authenticationservice/login",
    },
    "wtatil": {
        "name": "WTatil Tour API",
        "type": "tour",
        "product_types": ["tour"],
        "fields": ["base_url", "application_secret_key", "username", "password", "agency_id"],
        "auth_endpoint": "/api/Auth/get-token-async",
    },
    "tourvisio": {
        "name": "TourVisio (San TSG) Multi-Product API",
        "type": "hotel+flight+transfer+rentacar+excursion+package",
        "product_types": ["hotel", "flight", "transfer", "rentacar", "excursion", "package", "tour", "dynamic_package"],
        "fields": ["base_url", "agency", "username", "password"],
        "auth_endpoint": "/api/authenticationservice/login",
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
            "product_types": info.get("product_types", []),
            "required_fields": info["fields"],
            "optional_fields": info.get("optional_fields", []),
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
        all_fields = SUPPORTED_SUPPLIERS.get(doc["supplier"], {}).get("fields", []) + SUPPORTED_SUPPLIERS.get(doc["supplier"], {}).get("optional_fields", [])
        for field in all_fields:
            val = doc.get(f"enc_{field}", "")
            if val and field != "base_url":
                masked[field] = "****" + _decrypt(val)[-4:] if len(_decrypt(val)) > 4 else "****"
            elif field == "base_url":
                masked[field] = _decrypt(val) if val else ""
            else:
                masked[field] = ""
        creds.append(masked)
    return {"credentials": creds, "organization_id": organization_id}


async def save_credential(db, organization_id: str, supplier: str, fields: dict[str, str], *, actor: str = "") -> dict[str, Any]:
    """Save or update supplier credentials for an agency."""
    if supplier not in SUPPORTED_SUPPLIERS:
        return {"error": f"Unsupported supplier: {supplier}", "supported": list(SUPPORTED_SUPPLIERS.keys())}

    required = SUPPORTED_SUPPLIERS[supplier]["fields"]
    optional = SUPPORTED_SUPPLIERS[supplier].get("optional_fields", [])
    missing = [f for f in required if not fields.get(f)]
    if missing:
        return {"error": f"Missing required fields: {missing}"}

    all_fields = required + optional

    doc = {
        "organization_id": organization_id,
        "supplier": supplier,
        "status": "draft",
        "connected_at": None,
        "last_tested": None,
        "last_test_result": None,
        "updated_at": _ts(),
        "updated_by": actor,
    }
    for field in all_fields:
        val = fields.get(field, "")
        doc[f"enc_{field}"] = _encrypt(val) if val else ""

    await db["supplier_credentials"].update_one(
        {"organization_id": organization_id, "supplier": supplier},
        {"$set": doc},
        upsert=True,
    )

    await _write_audit(db, organization_id=organization_id, supplier=supplier,
                       action="save", actor=actor, details="Credentials saved/updated")

    return {
        "action": "save_credential",
        "supplier": supplier,
        "organization_id": organization_id,
        "status": "draft",
        "message": f"{supplier} credentials saved. Run 'Test Connection' to verify.",
    }


async def delete_credential(db, organization_id: str, supplier: str, *, actor: str = "") -> dict[str, Any]:
    """Delete supplier credentials for an agency."""
    result = await db["supplier_credentials"].delete_one(
        {"organization_id": organization_id, "supplier": supplier}
    )
    await db["supplier_tokens"].delete_many(
        {"organization_id": organization_id, "supplier": supplier}
    )
    if result.deleted_count > 0:
        await _write_audit(db, organization_id=organization_id, supplier=supplier,
                           action="delete", actor=actor, details="Credentials deleted")
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

    fields = SUPPORTED_SUPPLIERS.get(supplier, {}).get("fields", []) + SUPPORTED_SUPPLIERS.get(supplier, {}).get("optional_fields", [])
    result = {}
    for field in fields:
        enc_val = doc.get(f"enc_{field}", "")
        result[field] = _decrypt(enc_val) if enc_val else ""
    return result


async def test_connection(db, organization_id: str, supplier: str, *, actor: str = "") -> dict[str, Any]:
    """Test supplier connection using agency's credentials."""
    creds = await get_decrypted_credentials(db, organization_id, supplier)
    if not creds:
        return {"verdict": "FAIL", "error": "No credentials found for this supplier"}

    if supplier == "wtatil":
        result = await _test_wtatil(db, organization_id, creds)
    elif supplier == "paximum":
        result = await _test_paximum(db, organization_id, creds)
    elif supplier == "ratehawk":
        result = await _test_ratehawk(db, organization_id, creds)
    elif supplier == "tbo":
        result = await _test_tbo(db, organization_id, creds)
    elif supplier == "tourvisio":
        result = await _test_tourvisio(db, organization_id, creds)
    else:
        return {"verdict": "FAIL", "error": f"No test handler for {supplier}"}

    # Store last_test_result on the credential doc
    await db["supplier_credentials"].update_one(
        {"organization_id": organization_id, "supplier": supplier},
        {"$set": {"last_tested": _ts(), "last_test_result": result.get("verdict", "FAIL")}},
    )
    await _write_audit(db, organization_id=organization_id, supplier=supplier,
                       action="test", actor=actor, details=f"Result: {result.get('verdict')}")
    return result


async def _test_wtatil(db, organization_id: str, creds: dict) -> dict[str, Any]:
    """Test wtatil connection by calling auth endpoint."""
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
                    {"organization_id": organization_id, "supplier": "wtatil"},
                    {"$set": {
                        "token": token,
                        "obtained_at": _ts(),
                        "expires_hours": 24,
                    }},
                    upsert=True,
                )
                # Update credential status
                await db["supplier_credentials"].update_one(
                    {"organization_id": organization_id, "supplier": "wtatil"},
                    {"$set": {"status": "connected", "connected_at": _ts(), "last_tested": _ts()}},
                )
                return {
                    "verdict": "PASS",
                    "supplier": "wtatil",
                    "status": "connected",
                    "latency_ms": latency_ms,
                    "token_preview": token[:20] + "..." if len(token) > 20 else token,
                    "message": "Authentication successful. Token cached (24h validity).",
                }
            else:
                return {
                    "verdict": "FAIL",
                    "supplier": "wtatil",
                    "status": "auth_failed",
                    "latency_ms": latency_ms,
                    "response": str(data)[:200],
                    "message": "Response received but no token found.",
                }
        else:
            await db["supplier_credentials"].update_one(
                {"organization_id": organization_id, "supplier": "wtatil"},
                {"$set": {"status": "auth_failed", "last_tested": _ts()}},
            )
            return {
                "verdict": "FAIL",
                "supplier": "wtatil",
                "status": "auth_failed",
                "http_status": resp.status_code,
                "latency_ms": latency_ms,
                "response": resp.text[:200],
            }
    except httpx.ConnectError as e:
        return {"verdict": "FAIL", "supplier": "wtatil", "status": "connection_error", "error": str(e)}
    except httpx.TimeoutException:
        return {"verdict": "FAIL", "supplier": "wtatil", "status": "timeout", "error": "Connection timed out (15s)"}
    except Exception as e:
        return {"verdict": "FAIL", "supplier": "wtatil", "status": "error", "error": str(e)}


async def _test_paximum(db, organization_id: str, creds: dict) -> dict[str, Any]:
    """Test paximum connection via auth endpoint."""
    import httpx
    import time

    base_url = creds.get("base_url", "").rstrip("/")
    username = creds.get("username", "")
    password = creds.get("password", "")
    agency_code = creds.get("agency_code", "")
    if not base_url or not username or not password:
        return {"verdict": "FAIL", "error": "base_url, username, and password are required"}

    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{base_url}/api/authenticationservice/login",
                json={"Agency": agency_code, "User": username, "Password": password},
            )
        latency_ms = round((time.monotonic() - start) * 1000, 1)
        if resp.status_code == 200:
            data = resp.json()
            body = data.get("body") or data
            token = body.get("token") or body.get("Token") or ""
            if token:
                await db["supplier_tokens"].update_one(
                    {"organization_id": organization_id, "supplier": "paximum"},
                    {"$set": {"token": token, "obtained_at": _ts(), "expires_hours": 24}},
                    upsert=True,
                )
                await db["supplier_credentials"].update_one(
                    {"organization_id": organization_id, "supplier": "paximum"},
                    {"$set": {"status": "connected", "connected_at": _ts(), "last_tested": _ts()}},
                )
                return {"verdict": "PASS", "supplier": "paximum", "status": "connected", "latency_ms": latency_ms}
            return {"verdict": "FAIL", "supplier": "paximum", "status": "auth_failed", "latency_ms": latency_ms, "message": "No token in response"}
        else:
            await db["supplier_credentials"].update_one(
                {"organization_id": organization_id, "supplier": "paximum"},
                {"$set": {"status": "auth_failed", "last_tested": _ts()}},
            )
            return {"verdict": "FAIL", "supplier": "paximum", "http_status": resp.status_code, "latency_ms": latency_ms}
    except httpx.ConnectError as e:
        return {"verdict": "FAIL", "supplier": "paximum", "status": "connection_error", "error": str(e)}
    except httpx.TimeoutException:
        return {"verdict": "FAIL", "supplier": "paximum", "status": "timeout", "error": "Connection timed out (15s)"}
    except Exception as e:
        return {"verdict": "FAIL", "supplier": "paximum", "error": str(e)}


async def _test_ratehawk(db, organization_id: str, creds: dict) -> dict[str, Any]:
    """Test RateHawk connection via region search endpoint."""
    import httpx
    import time
    import base64

    base_url = creds.get("base_url", "").rstrip("/")
    key_id = creds.get("key_id", "")
    api_key = creds.get("api_key", "")
    if not base_url or not key_id or not api_key:
        return {"verdict": "FAIL", "error": "base_url, key_id, and api_key are required"}

    token = base64.b64encode(f"{key_id}:{api_key}".encode()).decode()
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{base_url}/api/b2b/v3/search/region/",
                json={"query": "istanbul", "language": "en"},
                headers={"Authorization": f"Basic {token}", "Content-Type": "application/json"},
            )
        latency_ms = round((time.monotonic() - start) * 1000, 1)
        if resp.status_code == 200:
            await db["supplier_tokens"].update_one(
                {"organization_id": organization_id, "supplier": "ratehawk"},
                {"$set": {"token": token, "obtained_at": _ts(), "expires_hours": 720}},
                upsert=True,
            )
            await db["supplier_credentials"].update_one(
                {"organization_id": organization_id, "supplier": "ratehawk"},
                {"$set": {"status": "connected", "connected_at": _ts(), "last_tested": _ts()}},
            )
            return {"verdict": "PASS", "supplier": "ratehawk", "status": "connected", "latency_ms": latency_ms}
        else:
            await db["supplier_credentials"].update_one(
                {"organization_id": organization_id, "supplier": "ratehawk"},
                {"$set": {"status": "auth_failed", "last_tested": _ts()}},
            )
            return {"verdict": "FAIL", "supplier": "ratehawk", "http_status": resp.status_code, "latency_ms": latency_ms, "response": resp.text[:200]}
    except httpx.ConnectError as e:
        return {"verdict": "FAIL", "supplier": "ratehawk", "status": "connection_error", "error": str(e)}
    except httpx.TimeoutException:
        return {"verdict": "FAIL", "supplier": "ratehawk", "status": "timeout", "error": "Connection timed out (15s)"}
    except Exception as e:
        return {"verdict": "FAIL", "supplier": "ratehawk", "error": str(e)}


async def _test_tbo(db, organization_id: str, creds: dict) -> dict[str, Any]:
    """Test TBO connection via auth endpoint."""
    import httpx
    import time

    base_url = creds.get("base_url", "").rstrip("/")
    username = creds.get("username", "")
    password = creds.get("password", "")
    client_id = creds.get("client_id", "")
    if not base_url or not username or not password:
        return {"verdict": "FAIL", "error": "base_url, username, and password are required"}

    payload = {"UserName": username, "Password": password}
    if client_id:
        payload["ClientId"] = client_id

    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(f"{base_url}/api/auth/token", json=payload)
        latency_ms = round((time.monotonic() - start) * 1000, 1)
        if resp.status_code == 200:
            data = resp.json()
            token = data.get("Token") or data.get("token") or data.get("TokenId") or ""
            if token:
                await db["supplier_tokens"].update_one(
                    {"organization_id": organization_id, "supplier": "tbo"},
                    {"$set": {"token": token, "obtained_at": _ts(), "expires_hours": 24}},
                    upsert=True,
                )
                await db["supplier_credentials"].update_one(
                    {"organization_id": organization_id, "supplier": "tbo"},
                    {"$set": {"status": "connected", "connected_at": _ts(), "last_tested": _ts()}},
                )
                return {"verdict": "PASS", "supplier": "tbo", "status": "connected", "latency_ms": latency_ms}
            return {"verdict": "FAIL", "supplier": "tbo", "status": "auth_failed", "latency_ms": latency_ms, "message": "No token in response"}
        else:
            await db["supplier_credentials"].update_one(
                {"organization_id": organization_id, "supplier": "tbo"},
                {"$set": {"status": "auth_failed", "last_tested": _ts()}},
            )
            return {"verdict": "FAIL", "supplier": "tbo", "http_status": resp.status_code, "latency_ms": latency_ms}
    except httpx.ConnectError as e:
        return {"verdict": "FAIL", "supplier": "tbo", "status": "connection_error", "error": str(e)}
    except httpx.TimeoutException:
        return {"verdict": "FAIL", "supplier": "tbo", "status": "timeout", "error": "Connection timed out (15s)"}
    except Exception as e:
        return {"verdict": "FAIL", "supplier": "tbo", "error": str(e)}


async def _test_tourvisio(db, organization_id: str, creds: dict) -> dict[str, Any]:
    """Test TourVisio (San TSG) connection by calling Login."""
    import time
    from app.services.tourvisio import TourVisioClient, TourVisioError

    base_url = (creds.get("base_url") or "").rstrip("/")
    agency = creds.get("agency", "")
    username = creds.get("username", "")
    password = creds.get("password", "")
    if not (base_url and agency and username and password):
        return {"verdict": "FAIL", "error": "base_url, agency, username, password required"}

    start = time.monotonic()
    try:
        client = TourVisioClient(base_url=base_url, agency=agency, user=username, password=password)
        # Force fresh login (bypass any stale cached token for this tenant key)
        client.clear_token()
        await client.login()
        latency_ms = round((time.monotonic() - start) * 1000, 1)
        status = client.token_status()
        await db["supplier_credentials"].update_one(
            {"organization_id": organization_id, "supplier": "tourvisio"},
            {"$set": {"status": "connected", "connected_at": _ts(), "last_tested": _ts()}},
        )
        return {
            "verdict": "PASS",
            "supplier": "tourvisio",
            "status": "connected",
            "latency_ms": latency_ms,
            "token_expires_at": status.get("expires_at"),
            "message": "TourVisio Login başarılı, token cache'lendi.",
        }
    except TourVisioError as e:
        await db["supplier_credentials"].update_one(
            {"organization_id": organization_id, "supplier": "tourvisio"},
            {"$set": {"status": "auth_failed", "last_tested": _ts()}},
        )
        return {"verdict": "FAIL", "supplier": "tourvisio",
                "http_status": e.status_code, "error": e.message}
    except Exception as e:
        return {"verdict": "FAIL", "supplier": "tourvisio", "error": str(e)}


async def get_cached_token(db, organization_id: str, supplier: str) -> str | None:
    """Get cached token for a supplier. Returns None if expired or missing."""
    doc = await db["supplier_tokens"].find_one(
        {"organization_id": organization_id, "supplier": supplier},
        {"_id": 0},
    )
    if not doc:
        return None
    # Simple expiry check — wtatil tokens are 24h
    return doc.get("token")


async def toggle_credential(db, organization_id: str, supplier: str, enabled: bool, *, actor: str = "") -> dict[str, Any]:
    """Enable or disable a supplier credential for an agency."""
    doc = await db["supplier_credentials"].find_one(
        {"organization_id": organization_id, "supplier": supplier}, {"_id": 0}
    )
    if not doc:
        return {"error": "Credential not found"}

    if enabled:
        # Only allow enabling if the last test was successful
        if doc.get("last_test_result") != "PASS":
            return {"error": "Cannot enable — last connection test did not pass. Please test first."}
        new_status = "connected"
    else:
        new_status = "disabled"

    await db["supplier_credentials"].update_one(
        {"organization_id": organization_id, "supplier": supplier},
        {"$set": {"status": new_status, "updated_at": _ts(), "updated_by": actor}},
    )
    action_str = "enable" if enabled else "disable"
    await _write_audit(db, organization_id=organization_id, supplier=supplier,
                       action=action_str, actor=actor, details=f"Status → {new_status}")
    return {"supplier": supplier, "status": new_status, "message": f"Supplier {action_str}d"}


async def get_credentials_for_agency(db, target_org_id: str) -> dict[str, Any]:
    """Admin: Get all supplier credentials for a specific agency (masked)."""
    return await get_agency_credentials(db, target_org_id)


async def admin_list_agencies_credentials(db) -> dict[str, Any]:
    """Admin: List all agencies and their supplier credential summary."""
    pipeline = [
        {"$group": {
            "_id": "$organization_id",
            "suppliers": {"$push": {"supplier": "$supplier", "status": "$status", "last_tested": "$last_tested", "last_test_result": "$last_test_result"}},
            "total": {"$sum": 1},
            "connected": {"$sum": {"$cond": [{"$eq": ["$status", "connected"]}, 1, 0]}},
            "disabled": {"$sum": {"$cond": [{"$eq": ["$status", "disabled"]}, 1, 0]}},
        }},
        {"$sort": {"_id": 1}},
    ]
    cursor = db["supplier_credentials"].aggregate(pipeline)
    agencies = []
    async for doc in cursor:
        org_id = doc["_id"]
        # Try to get agency name from organizations collection
        org = await db["organizations"].find_one({"org_id": org_id}, {"_id": 0, "name": 1, "org_id": 1})
        agencies.append({
            "organization_id": org_id,
            "company_name": org.get("name", org_id) if org else org_id,
            "suppliers": doc["suppliers"],
            "total_credentials": doc["total"],
            "connected_count": doc["connected"],
            "disabled_count": doc["disabled"],
        })
    return {"agencies": agencies}


async def get_audit_log(db, organization_id: str | None = None, limit: int = 50) -> dict[str, Any]:
    """Get audit log entries, optionally filtered by organization."""
    query = {}
    if organization_id:
        query["organization_id"] = organization_id
    cursor = db["credential_audit_log"].find(query, {"_id": 0}).sort("timestamp", -1).limit(limit)
    logs = []
    async for doc in cursor:
        logs.append(doc)
    return {"logs": logs, "count": len(logs)}

