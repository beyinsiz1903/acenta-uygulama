from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError

from app.auth import get_current_user, require_roles, require_hotel_capability
from app.db import get_db
from app.services.channels.ari_apply import apply_ari_to_pms
from app.services.channels.ari_normalizer import normalize_exely_ari
from app.services.channels.registry import get_provider_adapter
from app.services.channels.types import ChannelAriResult, ChannelTestResult
from app.utils import to_object_id

router = APIRouter(prefix="/api/channels", tags=["channels"])


ALLOWED_PROVIDERS = {"exely", "expedia", "etstur", "bookingcom", "airbnb", "other", "mock_ari"}
ALLOWED_CAPABILITIES = {"ARI_read", "ARI_push", "booking_write", "webhook_in", "webhook_out"}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_hotel_context(user: dict[str, Any]) -> tuple[str, str]:
    org_id = user.get("organization_id")
    hotel_id = user.get("hotel_id")
    if not org_id or not hotel_id:
        raise HTTPException(status_code=403, detail="NOT_LINKED_TO_HOTEL")
    return str(org_id), str(hotel_id)


def _mask_credentials(creds: Optional[dict]) -> dict:
    if not creds:
        return {}
    masked: dict[str, Any] = {}
    for k, v in creds.items():
        if v is None or v == "":
            masked[k] = v
        elif isinstance(v, str):
            masked[k] = "****"
        else:
            masked[k] = v
    return masked


class ChannelConnectorCreate(BaseModel):
    provider: str = Field(..., pattern="^(exely|expedia|etstur|bookingcom|airbnb|other|mock_ari)$")
    display_name: Optional[str] = None
    credentials: dict[str, Any] = Field(default_factory=dict)
    capabilities: List[str] = Field(default_factory=list)
    settings: dict[str, Any] = Field(default_factory=dict)


class ChannelConnectorUpdate(BaseModel):
    display_name: Optional[str] = None
    status: Optional[str] = Field(default=None, pattern="^(disconnected|connected|error|limited)$")
    credentials: Optional[dict[str, Any]] = None
    capabilities: Optional[List[str]] = None
    settings: Optional[dict[str, Any]] = None


class RoomTypeMappingIn(BaseModel):
    pms_room_type_id: str
    channel_room_type_id: str
    channel_room_name: Optional[str] = None
    active: bool = True


class RatePlanMappingIn(BaseModel):
    pms_rate_plan_id: str
    channel_rate_plan_id: str
    channel_rate_name: Optional[str] = None
    active: bool = True


class ChannelMappingsUpsert(BaseModel):
    room_type_mappings: List[RoomTypeMappingIn] = Field(default_factory=list)
    rate_plan_mappings: List[RatePlanMappingIn] = Field(default_factory=list)


class TestConnectionResponse(BaseModel):
    status: str
    run_id: Optional[str] = None
    message: Optional[str] = None





class AriApplyIn(BaseModel):
    from_date: date
    to_date: date
    mode: str = Field("rates_and_availability", description="Which ARI slice to apply")


class AriApplyOut(BaseModel):
    ok: bool
    status: str
    run_id: str
    summary: Dict[str, Any] = Field(default_factory=dict)
    diff: Dict[str, Any] = Field(default_factory=dict)
    error: Dict[str, Any] | None = None

class AriReadResponse(BaseModel):
    ok: bool
    code: str | None = None
    message: str | None = None
    run_id: str | None = None
    data: Any | None = None


@router.get(
    "/connectors",
    dependencies=[
        Depends(require_roles(["hotel_admin", "hotel_staff"])),
        Depends(require_hotel_capability("channel_hub")),
    ],
)
async def list_connectors(user=Depends(get_current_user)) -> dict[str, Any]:
    """List channel connectors for current hotel."""
    db = await get_db()
    org_id, hotel_id = _normalize_hotel_context(user)

    cursor = db.channel_connectors.find({
        "organization_id": org_id,
        "hotel_id": hotel_id,
    }).sort("updated_at", -1)

    items: List[dict[str, Any]] = []
    async for doc in cursor:
        items.append(
            {
                "_id": str(doc.get("_id")),
                "provider": doc.get("provider"),
                "display_name": doc.get("display_name") or doc.get("provider"),
                "status": doc.get("status") or "disconnected",
                "capabilities": doc.get("capabilities") or [],
                "last_test_at": doc.get("last_test_at"),
                "last_success_at": doc.get("last_success_at"),
                "last_error": doc.get("last_error"),
            }
        )

    return {"items": items}


@router.post(
    "/connectors",
    dependencies=[
        Depends(require_roles(["hotel_admin"])),
        Depends(require_hotel_capability("channel_hub")),
    ],
)
async def create_connector(payload: ChannelConnectorCreate, user=Depends(get_current_user)) -> dict[str, Any]:
    db = await get_db()
    org_id, hotel_id = _normalize_hotel_context(user)

    if payload.provider not in ALLOWED_PROVIDERS:
        raise HTTPException(status_code=422, detail="INVALID_PROVIDER")

    caps = [c for c in (payload.capabilities or []) if c in ALLOWED_CAPABILITIES]

    now = _utc_now()
    doc: dict[str, Any] = {
        "organization_id": org_id,
        "hotel_id": hotel_id,
        "provider": payload.provider,
        "display_name": payload.display_name or payload.provider,
        "status": "disconnected",
        "capabilities": caps,
        "credentials": payload.credentials or {},
        "settings": payload.settings or {},
        "last_test_at": None,
        "last_success_at": None,
        "last_error": None,
        "created_at": now,
        "updated_at": now,
        "created_by": user.get("email"),
        "updated_by": user.get("email"),
    }

    try:
        res = await db.channel_connectors.insert_one(doc)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=409,
            detail={"code": "PROVIDER_ALREADY_CONNECTED", "message": "Bu sağlayıcı için zaten bir connector var."},
        )

    saved = await db.channel_connectors.find_one({"_id": res.inserted_id})
    return {
        "_id": str(saved.get("_id")),
        "provider": saved.get("provider"),
        "display_name": saved.get("display_name"),
        "status": saved.get("status") or "disconnected",
        "capabilities": saved.get("capabilities") or [],
        "credentials": _mask_credentials(saved.get("credentials") or {}),
        "settings": saved.get("settings") or {},
        "last_test_at": saved.get("last_test_at"),
        "last_success_at": saved.get("last_success_at"),
        "last_error": saved.get("last_error"),
    }


async def _get_connector_or_404(db, org_id: str, hotel_id: str, connector_id: str) -> dict[str, Any]:
    from app.utils import to_object_id
    try:
        oid = to_object_id(connector_id)
    except:
        raise HTTPException(status_code=404, detail="CONNECTOR_NOT_FOUND")
        
    doc = await db.channel_connectors.find_one(
        {
            "organization_id": org_id,
            "hotel_id": hotel_id,
            "_id": oid,
        }
    )
    if not doc:
        raise HTTPException(status_code=404, detail="CONNECTOR_NOT_FOUND")
    return doc


@router.get(
    "/connectors/{connector_id}",
    dependencies=[
        Depends(require_roles(["hotel_admin", "hotel_staff"])),
        Depends(require_hotel_capability("channel_hub")),
    ],
)
async def get_connector(connector_id: str, user=Depends(get_current_user)) -> dict[str, Any]:
    db = await get_db()
    org_id, hotel_id = _normalize_hotel_context(user)
    doc = await _get_connector_or_404(db, org_id, hotel_id, connector_id)

    return {
        "_id": str(doc.get("_id")),
        "provider": doc.get("provider"),
        "display_name": doc.get("display_name"),
        "status": doc.get("status") or "disconnected",
        "capabilities": doc.get("capabilities") or [],
        "credentials": _mask_credentials(doc.get("credentials") or {}),
        "settings": doc.get("settings") or {},
        "last_test_at": doc.get("last_test_at"),
        "last_success_at": doc.get("last_success_at"),
        "last_error": doc.get("last_error"),
    }


@router.patch(
    "/connectors/{connector_id}",
    dependencies=[
        Depends(require_roles(["hotel_admin"])),
        Depends(require_hotel_capability("channel_hub")),
    ],
)
async def update_connector(connector_id: str, payload: ChannelConnectorUpdate, user=Depends(get_current_user)) -> dict[str, Any]:
    db = await get_db()
    org_id, hotel_id = _normalize_hotel_context(user)

    existing = await _get_connector_or_404(db, org_id, hotel_id, connector_id)

    update: dict[str, Any] = {"updated_at": _utc_now(), "updated_by": user.get("email")}

    if payload.display_name is not None:
        update["display_name"] = payload.display_name
    if payload.status is not None:
        update["status"] = payload.status
    if payload.credentials is not None:
        merged = existing.get("credentials") or {}
        merged.update(payload.credentials)
        update["credentials"] = merged
    if payload.capabilities is not None:
        update["capabilities"] = [c for c in payload.capabilities if c in ALLOWED_CAPABILITIES]
    if payload.settings is not None:
        merged_settings = existing.get("settings") or {}
        merged_settings.update(payload.settings)
        update["settings"] = merged_settings

    await db.channel_connectors.update_one(
        {"_id": to_object_id(connector_id), "organization_id": org_id, "hotel_id": hotel_id},
        {"$set": update},
    )

    doc = await _get_connector_or_404(db, org_id, hotel_id, connector_id)
    return {
        "_id": str(doc.get("_id")),
        "provider": doc.get("provider"),
        "display_name": doc.get("display_name"),
        "status": doc.get("status") or "disconnected",
        "capabilities": doc.get("capabilities") or [],
        "credentials": _mask_credentials(doc.get("credentials") or {}),
        "settings": doc.get("settings") or {},
        "last_test_at": doc.get("last_test_at"),
        "last_success_at": doc.get("last_success_at"),
        "last_error": doc.get("last_error"),
    }


@router.delete(
    "/connectors/{connector_id}",
    dependencies=[
        Depends(require_roles(["hotel_admin"])),
        Depends(require_hotel_capability("channel_hub")),
    ],
)
async def delete_connector(connector_id: str, user=Depends(get_current_user)) -> dict[str, Any]:
    db = await get_db()
    org_id, hotel_id = _normalize_hotel_context(user)

    existing = await _get_connector_or_404(db, org_id, hotel_id, connector_id)

    await db.channel_connectors.delete_one({"_id": to_object_id(connector_id), "organization_id": org_id, "hotel_id": hotel_id})
    # Also cleanup mappings (runs kept for history)
    await db.channel_mappings.delete_one({
        "organization_id": org_id,
        "hotel_id": hotel_id,
        "connector_id": connector_id,
    })

    return {"ok": True, "deleted_id": str(existing.get("_id"))}


@router.post(
    "/connectors/{connector_id}/test",
    response_model=TestConnectionResponse,
    dependencies=[
        Depends(require_roles(["hotel_admin"])),
        Depends(require_hotel_capability("channel_hub")),
    ],
)
async def test_connection(connector_id: str, user=Depends(get_current_user)) -> TestConnectionResponse:
    """Provider-aware test connection.

    Uses the channel provider registry to delegate to the correct adapter
    (e.g. ExelyChannelProvider) and maps ChannelTestResult to HTTP and run
    documents.
    """
    db = await get_db()
    org_id, hotel_id = _normalize_hotel_context(user)

    doc = await _get_connector_or_404(db, org_id, hotel_id, connector_id)

    provider_name = doc.get("provider") or "unknown"
    adapter = get_provider_adapter(provider_name)

    try:
        result: ChannelTestResult = await adapter.test_connection(connector=doc)
    except Exception as e:  # Safety net so adapters don't bring API down
        result = ChannelTestResult(
            ok=False,
            code="UNKNOWN_ERROR",
            message=str(e) or "Bilinmeyen bir hata oluştu.",
            meta={"provider": provider_name},
        )

    now = _utc_now()

    # Map ChannelTestResult to run status + HTTP code
    status = "success" if result.ok else "failed"
    error_doc = None
    http_status = 200

    if not result.ok:
        code = (result.code or "UNKNOWN_ERROR").upper()
        error_doc = {"code": code, "message": result.message}
        if code == "AUTH_FAILED":
            http_status = 400
        elif code == "NOT_IMPLEMENTED":
            http_status = 501
        elif code in {"PROVIDER_UNAVAILABLE", "TIMEOUT"}:
            http_status = 503
        else:
            http_status = 500

    run_doc: dict[str, Any] = {
        "organization_id": org_id,
        "hotel_id": hotel_id,
        "connector_id": connector_id,
        "type": "test_connection",
        "status": status,
        "started_at": now,
        "finished_at": now,
        "duration_ms": 0,
        "summary": {"requests": 1, "success": 1 if result.ok else 0, "failed": 0 if result.ok else 1},
        "error": error_doc,
        "meta": {"invoked_by": "hotel_panel", "provider": provider_name},
    }

    ins = await db.channel_sync_runs.insert_one(run_doc)
    run_id = str(ins.inserted_id)

    # Update connector status + last_* fields
    update: dict[str, Any] = {
        "last_test_at": now,
        "updated_at": now,
        "updated_by": user.get("email"),
    }
    if result.ok:
        update["status"] = "connected"
        update["last_success_at"] = now
        update["last_error"] = None
    else:
        update["status"] = "error"
        update["last_error"] = error_doc

    await db.channel_connectors.update_one(
        {"_id": to_object_id(connector_id), "organization_id": org_id, "hotel_id": hotel_id},
        {"$set": update},
    )

    if not result.ok:
        # Raise HTTPException with structured detail so UI can map
        raise HTTPException(status_code=http_status, detail=error_doc)

    return TestConnectionResponse(status="success", run_id=run_id, message=result.message or "Connected")


@router.get(
    "/connectors/{connector_id}/mappings",
    dependencies=[
        Depends(require_roles(["hotel_admin", "hotel_staff"])),
        Depends(require_hotel_capability("channel_hub")),
    ],
)
async def get_mappings(connector_id: str, user=Depends(get_current_user)) -> dict[str, Any]:
    db = await get_db()
    org_id, hotel_id = _normalize_hotel_context(user)

    doc = await db.channel_mappings.find_one(
        {
            "organization_id": org_id,
            "hotel_id": hotel_id,
            "connector_id": connector_id,
        }
    )

    if not doc:
        return {
            "connector_id": connector_id,
            "room_type_mappings": [],
            "rate_plan_mappings": [],
        }

    return {
        "connector_id": connector_id,
        "room_type_mappings": doc.get("room_type_mappings") or [],
        "rate_plan_mappings": doc.get("rate_plan_mappings") or [],
    }


@router.put(
    "/connectors/{connector_id}/mappings",
    dependencies=[
        Depends(require_roles(["hotel_admin"])),
        Depends(require_hotel_capability("channel_hub")),
    ],
)
async def upsert_mappings(
    connector_id: str,
    payload: ChannelMappingsUpsert,
    user=Depends(get_current_user),
) -> dict[str, Any]:
    db = await get_db()
    org_id, hotel_id = _normalize_hotel_context(user)

    # Ensure connector exists
    await _get_connector_or_404(db, org_id, hotel_id, connector_id)

    now = _utc_now()

    await db.channel_mappings.update_one(
        {
            "organization_id": org_id,
            "hotel_id": hotel_id,
            "connector_id": connector_id,
        },
        {
            "$set": {
                "room_type_mappings": [m.model_dump() for m in payload.room_type_mappings],
                "rate_plan_mappings": [m.model_dump() for m in payload.rate_plan_mappings],
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )

    return await get_mappings(connector_id, user)


@router.get(
    "/connectors/{connector_id}/runs",
    dependencies=[
        Depends(require_roles(["hotel_admin", "hotel_staff"])),
        Depends(require_hotel_capability("channel_hub")),
    ],
)
async def list_runs(
    connector_id: str,
    limit: int = Query(20, ge=1, le=100),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    db = await get_db()
    org_id, hotel_id = _normalize_hotel_context(user)

    cursor = db.channel_sync_runs.find(
        {
            "organization_id": org_id,
            "hotel_id": hotel_id,
            "connector_id": connector_id,
        }
    ).sort("started_at", -1).limit(int(limit))

    items: List[dict[str, Any]] = []
    async for doc in cursor:
        items.append(
            {
                "_id": str(doc.get("_id")),
                "type": doc.get("type"),
                "status": doc.get("status"),
                "started_at": doc.get("started_at"),
                "finished_at": doc.get("finished_at"),
                "duration_ms": doc.get("duration_ms"),
            }
        )

    return {"items": items}


@router.get(
    "/connectors/{connector_id}/ari",
    response_model=AriReadResponse,
    dependencies=[
        Depends(require_roles(["hotel_admin", "hotel_staff"])),
        Depends(require_hotel_capability("channel_hub")),
    ],
)
async def fetch_ari(
    connector_id: str,
    from_date: datetime,
    to_date: datetime,
    user=Depends(get_current_user),
) -> AriReadResponse:
    """Trigger a read-only ARI fetch for a connector.

    This does **not** write anything to PMS or local inventory. It only records
    a channel_sync_runs entry with type="ari_read" and returns the raw
    provider payload.
    """

    db = await get_db()
    org_id, hotel_id = _normalize_hotel_context(user)

    connector = await _get_connector_or_404(db, org_id, hotel_id, connector_id)
    provider_name = connector.get("provider") or "unknown"
    adapter = get_provider_adapter(provider_name)

    # Delegate to provider adapter
    from app.services.channels.types import ChannelAriResult

    try:
        result: ChannelAriResult = await adapter.fetch_ari(
            connector=connector,
            from_date=from_date.date(),
            to_date=to_date.date(),
        )
    except Exception as e:
        result = ChannelAriResult(
            ok=False,
            code="UNKNOWN_ERROR",
            message=str(e) or "Bilinmeyen bir hata oluştu.",
            data={},
            meta={"provider": provider_name},
        )

    now = _utc_now()

    status = "success" if result.ok else "failed"
    error_doc = None
    if not result.ok:
        error_doc = {"code": (result.code or "UNKNOWN_ERROR").upper(), "message": result.message}

    run_doc: dict[str, Any] = {
        "organization_id": org_id,
        "hotel_id": hotel_id,
        "connector_id": connector_id,
        "type": "ari_read",
        "status": status,
        "started_at": now,
        "finished_at": now,
        "duration_ms": 0,
        "summary": {
            "from_date": from_date,
            "to_date": to_date,
        },
        "error": error_doc,
        "meta": {
            "invoked_by": "hotel_panel",
            "provider": provider_name,
            **(result.meta or {}),
        },
    }

    ins = await db.channel_sync_runs.insert_one(run_doc)
    run_id = str(ins.inserted_id)

    return AriReadResponse(
        ok=result.ok,
        code=result.code,
        message=result.message,
        run_id=run_id,
        data=result.data,
    )



@router.post(
    "/connectors/{connector_id}/ari/apply",
    response_model=AriApplyOut,
    dependencies=[
        Depends(require_roles(["hotel_admin", "hotel_staff"])),
        Depends(require_hotel_capability("channel_hub")),
    ],
)
async def ari_apply(
    connector_id: str,
    payload: AriApplyIn,
    dry_run: int = Query(1, ge=0, le=1),
    user=Depends(get_current_user),
) -> AriApplyOut:
    """Fetch ARI from provider, normalize and (optionally) apply to PMS.

    - When dry_run=1 (default), no write is performed; we return a diff + summary
      and record a channel_sync_runs document with type="ari_apply".
    - When dry_run=0, we also upsert into PMS snapshot collections.
    """

    db = await get_db()
    org_id, hotel_id = _normalize_hotel_context(user)

    connector = await _get_connector_or_404(db, org_id, hotel_id, connector_id)
    provider_name = connector.get("provider") or "unknown"
    adapter = get_provider_adapter(provider_name)

    mappings_doc = await db.channel_mappings.find_one(
        {
            "organization_id": org_id,
            "hotel_id": hotel_id,
            "connector_id": connector_id,
        }
    ) or {"room_type_mappings": [], "rate_plan_mappings": []}

    # Idempotency key: connector + date range + mode + dry_run flag
    idem_key = (
        f"ari_apply:{connector_id}:"
        f"{payload.from_date.isoformat()}:{payload.to_date.isoformat()}:"
        f"{payload.mode}:dry={dry_run}"
    )

    existing_run = await db.channel_sync_runs.find_one(
        {
            "organization_id": org_id,
            "hotel_id": hotel_id,
            "connector_id": connector_id,
            "idempotency_key": idem_key,
            "type": "ari_apply",
        }
    )
    if existing_run:
        status = existing_run.get("status") or "failed"
        return AriApplyOut(
            ok=status in ["success", "partial"],
            status=status,
            run_id=str(existing_run.get("_id")),
            summary=existing_run.get("summary") or {},
            diff=existing_run.get("diff") or {},
            error=existing_run.get("error"),
        )

    now = _utc_now()
    started = now
    status = "failed"
    error_doc: dict[str, Any] | None = None
    summary: dict[str, Any] = {
        "from_date": payload.from_date.isoformat(),
        "to_date": payload.to_date.isoformat(),
        "mode": payload.mode,
        "dry_run": bool(dry_run),
    }
    diff_out: dict[str, Any] = {"rates": [], "availability": []}

    run_doc: dict[str, Any] = {
        "organization_id": org_id,
        "hotel_id": hotel_id,
        "connector_id": connector_id,
        "type": "ari_apply",
        "status": "running",
        "started_at": started,
        "finished_at": None,
        "duration_ms": None,
        "summary": summary,
        "diff": {},
        "error": None,
        "meta": {
            "invoked_by": "hotel_panel",
            "provider": provider_name,
        },
        "idempotency_key": idem_key,
    }

    ins = await db.channel_sync_runs.insert_one(run_doc)
    run_id = str(ins.inserted_id)

    try:
        # 1) Fetch ARI from provider
        ari_result: ChannelAriResult = await adapter.fetch_ari(
            connector=connector,
            from_date=payload.from_date,
            to_date=payload.to_date,
        )
        if not ari_result.ok:
            status = "failed"
            error_doc = {
                "code": ari_result.code or "UNKNOWN_ERROR",
                "message": ari_result.message,
            }
            raise RuntimeError(ari_result.message or "ARI fetch failed")

        raw = ari_result.data or {}

        # 2) Normalize (currently Exely-specific)
        canonical, norm_stats = await normalize_exely_ari(
            raw=raw,
            mappings=mappings_doc,
            from_date=payload.from_date,
            to_date=payload.to_date,
        )
        # Merge normalization stats into summary
        summary.update(norm_stats or {})

        # 3) Apply to PMS (or dry-run)
        apply_result = await apply_ari_to_pms(
            db=db,
            canonical=canonical,
            org_id=org_id,
            hotel_id=hotel_id,
            connector_id=connector_id,
            mode=payload.mode,
            dry_run=bool(dry_run),
            idempotency_key=idem_key,
        )

        status = apply_result.get("status") or "failed"
        summary.update(apply_result.get("summary") or {})
        diff_out = apply_result.get("diff") or diff_out

        # If we had unmapped items but wrote something, mark as partial
        if status == "success" and (
            summary.get("unmapped_rooms") or summary.get("unmapped_rates")
        ):
            status = "partial"

    except Exception as e:  # noqa: BLE001
        if not error_doc:
            error_doc = {
                "code": "UNKNOWN_ERROR",
                "message": str(e) or "Bilinmeyen hata",
            }

    finished = _utc_now()
    duration_ms = int((finished - started).total_seconds() * 1000)

    await db.channel_sync_runs.update_one(
        {"_id": ins.inserted_id},
        {
            "$set": {
                "status": status,
                "finished_at": finished,
                "duration_ms": duration_ms,
                "summary": summary,
                "diff": diff_out,
                "error": error_doc,
            }
        },
    )

    ok = status in ["success", "partial"]
    return AriApplyOut(ok=ok, status=status, run_id=run_id, summary=summary, diff=diff_out, error=error_doc)
