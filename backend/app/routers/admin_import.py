"""Zero Migration Friction Engine — Admin Import API.

POST /api/admin/import/hotels/upload       — Upload CSV/XLSX, create job, return preview
POST /api/admin/import/hotels/validate      — Validate with mapping
POST /api/admin/import/hotels/execute       — Run bulk import
GET  /api/admin/import/jobs                 — List import jobs
GET  /api/admin/import/jobs/{job_id}        — Job detail + errors
GET  /api/admin/import/export-template      — Download XLSX template
POST /api/admin/import/sheet/connect        — Store Google Sheet connection (MOCKED sync)
POST /api/admin/import/sheet/sync           — Trigger sheet sync (MOCKED)
GET  /api/admin/import/sheet/connections     — List sheet connections
"""
from __future__ import annotations

import io
import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile
from pydantic import BaseModel, Field

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.errors import AppError
from app.services.import_service import (
    create_hotels_bulk,
    create_import_job,
    download_hotel_images,
    get_existing_hotel_names,
    map_columns,
    parse_excel,
    save_import_errors,
    update_job_status,
    validate_hotels,
    VALID_FIELDS,
)
from app.utils import now_utc, serialize_doc

router = APIRouter(prefix="/api/admin/import", tags=["admin_import"])
AdminDep = Depends(require_roles(["super_admin", "admin"]))

# In-memory temp storage for parsed data (keyed by job_id)
_temp_data: Dict[str, Any] = {}


# ── Upload ─────────────────────────────────────────────────────

@router.post("/hotels/upload", dependencies=[AdminDep])
async def upload_hotels_file(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Upload CSV/XLSX file, create import job, return preview."""
    filename = file.filename or "unknown"
    if not filename.lower().endswith((".csv", ".xlsx", ".xls")):
        raise AppError(400, "invalid_file", "Sadece CSV veya XLSX dosyaları kabul edilir.")

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:  # 10MB limit
        raise AppError(400, "file_too_large", "Dosya boyutu 10MB'dan büyük olamaz.")

    try:
        headers, rows = parse_excel(contents, filename)
    except Exception as e:
        raise AppError(400, "parse_error", f"Dosya okunamadı: {str(e)}")

    org_id = user["organization_id"]
    tenant_id = user.get("tenant_id") or org_id

    job = await create_import_job(
        db,
        tenant_id=tenant_id,
        organization_id=org_id,
        entity_type="hotel",
        source="excel",
        total_rows=len(rows),
        filename=filename,
    )

    # Store parsed data temporarily
    _temp_data[job["_id"]] = {
        "headers": headers,
        "rows": rows,
        "org_id": org_id,
    }

    # Preview: first 20 rows
    preview_rows = rows[:20]

    return {
        "job_id": job["_id"],
        "filename": filename,
        "total_rows": len(rows),
        "headers": headers,
        "preview": preview_rows,
        "available_fields": VALID_FIELDS,
    }


# ── Validate ───────────────────────────────────────────────────

class ValidateRequest(BaseModel):
    job_id: str
    mapping: Dict[str, str]  # { "0": "name", "1": "city", ... }


@router.post("/hotels/validate", dependencies=[AdminDep])
async def validate_hotels_endpoint(
    body: ValidateRequest,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Validate all rows with the given column mapping."""
    temp = _temp_data.get(body.job_id)
    if not temp:
        raise AppError(404, "job_not_found", "Import job bulunamadı veya süresi dolmuş.")

    org_id = temp["org_id"]
    mapped = map_columns(temp["headers"], temp["rows"], body.mapping)

    existing_names = await get_existing_hotel_names(db, org_id)
    valid, errors = validate_hotels(mapped, existing_names)

    # Save errors
    await save_import_errors(db, body.job_id, errors)

    # Update job
    await update_job_status(
        db, body.job_id, "validated",
        valid_count=len(valid),
        error_count=len(errors),
    )

    # Store validated data + mapping
    temp["mapping"] = body.mapping
    temp["valid_rows"] = valid
    temp["validation_errors"] = errors

    return {
        "job_id": body.job_id,
        "total_rows": len(temp["rows"]),
        "valid_count": len(valid),
        "error_count": len(errors),
        "errors": errors[:50],  # Return first 50 errors
        "preview_valid": valid[:10],
    }


# ── Execute ────────────────────────────────────────────────────

class ExecuteRequest(BaseModel):
    job_id: str


async def _run_import(job_id: str, org_id: str, valid_rows: List[Dict], created_by: str):
    """Background task to run the actual import."""
    from app.db import get_db as _get_db
    db = await _get_db()
    try:
        await update_job_status(db, job_id, "processing")

        success, err_count, errors = await create_hotels_bulk(
            db, org_id, valid_rows, created_by, job_id
        )

        if errors:
            await save_import_errors(db, job_id, errors)

        # Download images in background
        img_count = 0
        try:
            img_count = await download_hotel_images(db, org_id, job_id)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("Image download failed: %s", e)

        await update_job_status(
            db, job_id,
            "completed" if err_count == 0 else "completed",
            success_count=success,
            error_count=err_count,
            images_downloaded=img_count,
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("Import job %s failed: %s", job_id, e)
        await update_job_status(db, job_id, "failed", error_message=str(e))


@router.post("/hotels/execute", dependencies=[AdminDep])
async def execute_import(
    body: ExecuteRequest,
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Execute the import. Runs in background."""
    temp = _temp_data.get(body.job_id)
    if not temp:
        raise AppError(404, "job_not_found", "Import job bulunamadı.")

    valid_rows = temp.get("valid_rows", [])
    if not valid_rows:
        raise AppError(400, "no_valid_rows", "Geçerli satır bulunamadı.")

    org_id = temp["org_id"]
    created_by = user.get("email", "import")

    background_tasks.add_task(_run_import, body.job_id, org_id, valid_rows, created_by)

    # Clean up temp data
    _temp_data.pop(body.job_id, None)

    return {
        "job_id": body.job_id,
        "status": "processing",
        "message": f"{len(valid_rows)} otel import ediliyor...",
    }


# ── Jobs ───────────────────────────────────────────────────────

@router.get("/jobs", dependencies=[AdminDep])
async def list_import_jobs(
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    org_id = user["organization_id"]
    docs = await db.import_jobs.find(
        {"organization_id": org_id}
    ).sort("created_at", -1).to_list(100)
    return [serialize_doc(d) for d in docs]


@router.get("/jobs/{job_id}", dependencies=[AdminDep])
async def get_import_job(
    job_id: str,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    org_id = user["organization_id"]
    job = await db.import_jobs.find_one({"_id": job_id, "organization_id": org_id})
    if not job:
        raise AppError(404, "job_not_found", "Import job bulunamadı.")

    errors = await db.import_errors.find({"job_id": job_id}).to_list(200)
    result = serialize_doc(job)
    result["errors"] = [serialize_doc(e) for e in errors]
    return result


# ── Export Template ────────────────────────────────────────────

@router.get("/export-template")
async def export_template(user=Depends(require_roles(["super_admin", "admin"]))):
    """Download example XLSX template for hotel import."""
    from openpyxl import Workbook
    from fastapi.responses import StreamingResponse

    wb = Workbook()
    ws = wb.active
    ws.title = "Hotels"
    ws.append(["Otel Adı", "Şehir", "Ülke", "Açıklama", "Fiyat", "Yıldız", "Adres", "Telefon", "Email", "Resim URL"])
    ws.append(["Demo Hotel Istanbul", "İstanbul", "TR", "Boğaz manzaralı otel", "1500", "5", "Beşiktaş, İstanbul", "+90 212 555 00 00", "info@demo.com", ""])
    ws.append(["Demo Hotel Antalya", "Antalya", "TR", "Denize sıfır", "2000", "4", "Konyaaltı, Antalya", "+90 242 555 00 00", "info@demo2.com", ""])

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=otel_import_sablonu.xlsx"},
    )


# ── Google Sheets (MOCKED) ─────────────────────────────────────

class SheetConnectRequest(BaseModel):
    sheet_id: str
    worksheet_name: str = "Sheet1"
    column_mapping: Dict[str, str] = {}
    sync_enabled: bool = False


@router.post("/sheet/connect", dependencies=[AdminDep])
async def connect_sheet(
    body: SheetConnectRequest,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Store a Google Sheet connection. Sync is MOCKED."""
    org_id = user["organization_id"]
    tenant_id = user.get("tenant_id") or org_id

    doc = {
        "_id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "organization_id": org_id,
        "sheet_id": body.sheet_id,
        "worksheet_name": body.worksheet_name,
        "column_mapping": body.column_mapping,
        "sync_enabled": body.sync_enabled,
        "last_sync_at": None,
        "status": "connected",
        "created_at": now_utc(),
    }
    await db.sheet_connections.insert_one(doc)
    return serialize_doc(doc)


@router.post("/sheet/sync", dependencies=[AdminDep])
async def sync_sheet(
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Trigger a Google Sheet sync. MOCKED — returns simulated result."""
    org_id = user["organization_id"]
    conn = await db.sheet_connections.find_one(
        {"organization_id": org_id, "status": "connected"}
    )
    if not conn:
        raise AppError(404, "no_connection", "Bağlı Google Sheet bulunamadı.")

    # MOCKED sync
    await db.sheet_connections.update_one(
        {"_id": conn["_id"]},
        {"$set": {"last_sync_at": now_utc()}},
    )

    return {
        "status": "synced",
        "message": "Google Sheets senkronizasyonu simüle edildi (MOCK). Gerçek API key gerekli.",
        "sheet_id": conn["sheet_id"],
        "last_sync_at": now_utc().isoformat(),
    }


@router.get("/sheet/connections", dependencies=[AdminDep])
async def list_sheet_connections(
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    org_id = user["organization_id"]
    docs = await db.sheet_connections.find(
        {"organization_id": org_id}
    ).sort("created_at", -1).to_list(50)
    return [serialize_doc(d) for d in docs]
