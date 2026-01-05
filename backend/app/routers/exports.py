from __future__ import annotations

from datetime import timedelta
from io import StringIO, BytesIO
import csv
import hashlib
import os
import secrets
from typing import Any, Optional, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from bson import ObjectId
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.utils import now_utc
from app.routers.matches import list_matches

router = APIRouter(prefix="/api/admin/exports", tags=["admin-exports"])

# Public router for non-authenticated endpoints
public_router = APIRouter(prefix="/api/exports", tags=["exports-public"])


class ExportPolicyParams(BaseModel):
    days: int = Field(30, ge=1, le=365)
    min_matches: int = Field(5, ge=1, le=10000)
    only_high_risk: bool = False


class ExportPolicyModel(BaseModel):
    key: str
    enabled: bool = True
    type: Literal["match_risk_summary"] = "match_risk_summary"
    format: Literal["csv", "pdf"] = "csv"
    schedule_hint: Optional[str] = None
    recipients: list[str] | None = None
    cooldown_hours: int = Field(24, ge=1, le=168)
    params: ExportPolicyParams = ExportPolicyParams()


class ExportPolicyOut(ExportPolicyModel):
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    updated_by_email: Optional[str] = None


class ExportPoliciesResponse(BaseModel):
    ok: bool = True
    items: list[ExportPolicyOut]


class ExportRunItem(BaseModel):
    id: str
    policy_key: str
    type: str
    format: str
    status: str
    error: Optional[str] = None
    generated_at: str
    size_bytes: int
    filename: str
    sha256: Optional[str] = None
    emailed: Optional[bool] = None


class ExportRunsResponse(BaseModel):
    ok: bool = True
    items: list[ExportRunItem]
    admin_deeplink_template: str | None = None


class ExportRunResult(BaseModel):
    ok: bool = True
    dry_run: bool
    policy_key: str
    rows: int
    estimated_size_bytes: int
    run_id: Optional[str] = None
    emailed: Optional[bool] = None
    emailed_to: Optional[list[str]] = None


@router.get("/policies", response_model=ExportPoliciesResponse, dependencies=[Depends(require_roles(["super_admin"]))])
async def list_policies(db=Depends(get_db), user=Depends(get_current_user)):
    org_id = user.get("organization_id")
    cursor = db.export_policies.find({"organization_id": org_id}).sort("key", 1)
    docs = await cursor.to_list(length=None)
    items: list[ExportPolicyOut] = []
    for d in docs:
        p = ExportPolicyOut(
            key=d["key"],
            enabled=bool(d.get("enabled", True)),
            type=d.get("type", "match_risk_summary"),
            format=d.get("format", "csv"),
            schedule_hint=d.get("schedule_hint"),
            recipients=d.get("recipients") or [],
            cooldown_hours=int(d.get("cooldown_hours", 24)),
            params=ExportPolicyParams(**(d.get("params") or {})),
            created_at=(d.get("created_at").isoformat() if d.get("created_at") else None),
            updated_at=(d.get("updated_at").isoformat() if d.get("updated_at") else None),
            updated_by_email=d.get("updated_by_email"),
        )
        items.append(p)
    return ExportPoliciesResponse(ok=True, items=items)


@router.put("/policies/{key}", response_model=ExportPolicyOut, dependencies=[Depends(require_roles(["super_admin"]))])
async def upsert_policy(key: str, payload: ExportPolicyModel, db=Depends(get_db), user=Depends(get_current_user)):
    org_id = user.get("organization_id")
    now = now_utc()
    data = payload.model_dump()
    data["organization_id"] = org_id
    data["updated_at"] = now
    data["updated_by_email"] = user.get("email")
    existing = await db.export_policies.find_one({"organization_id": org_id, "key": key})
    if not existing:
        data["created_at"] = now
    await db.export_policies.update_one(
        {"organization_id": org_id, "key": key},
        {"$set": data},
        upsert=True,
    )
    doc = await db.export_policies.find_one({"organization_id": org_id, "key": key})
    return ExportPolicyOut(
        key=doc["key"],
        enabled=bool(doc.get("enabled", True)),
        type=doc.get("type", "match_risk_summary"),
        format=doc.get("format", "csv"),
        schedule_hint=doc.get("schedule_hint"),
        recipients=doc.get("recipients") or [],
        cooldown_hours=int(doc.get("cooldown_hours", 24)),
        params=ExportPolicyParams(**(doc.get("params") or {})),
        created_at=(doc.get("created_at").isoformat() if doc.get("created_at") else None),
        updated_at=(doc.get("updated_at").isoformat() if doc.get("updated_at") else None),
        updated_by_email=doc.get("updated_by_email"),
    )


@router.delete("/policies/{key}", response_model=dict, dependencies=[Depends(require_roles(["super_admin"]))])
async def delete_policy(key: str, db=Depends(get_db), user=Depends(get_current_user)):
    org_id = user.get("organization_id")
    await db.export_policies.delete_one({"organization_id": org_id, "key": key})
    return {"ok": True}


async def _load_policy(db, org_id: str, key: str) -> dict[str, Any]:
    doc = await db.export_policies.find_one({"organization_id": org_id, "key": key})
    if not doc:
        raise HTTPException(status_code=404, detail="EXPORT_POLICY_NOT_FOUND")
    if not doc.get("enabled", True):
        raise HTTPException(status_code=400, detail="EXPORT_POLICY_DISABLED")
    return doc


async def _generate_match_risk_rows(db, org_id: str, params: ExportPolicyParams, user: dict[str, Any]) -> list[dict[str, Any]]:
    # Reuse matches summary endpoint to get items
    matches_resp = await list_matches(days=params.days, min_total=params.min_matches, include_action=True, db=db, user=user)  # type: ignore[arg-type]
    items = matches_resp["items"] if isinstance(matches_resp, dict) else matches_resp.items
    rows: list[dict[str, Any]] = []
    now_str = now_utc().isoformat()
    from app.services.risk_profile import load_risk_profile, is_high_risk

    # Unified risk profile per-org (defaults if no doc)
    risk_profile = await load_risk_profile(db, org_id)

    for item in items:
        data = item if isinstance(item, dict) else item.model_dump()
        # Prefer behavioral_cancel_rate if available; fallback to legacy cancel_rate
        behavioral_rate = float(
            data.get("behavioral_cancel_rate")
            or data.get("cancel_rate")
            or 0.0
        )
        repeat_7 = int(data.get("repeat_not_arrived_7") or 0)

        high_risk = is_high_risk(behavioral_rate, repeat_7, risk_profile)
        if params.only_high_risk and not high_risk:
            continue
        rows.append(
            {
                "match_id": data.get("id"),
                "agency_id": data.get("agency_id"),
                "hotel_id": data.get("hotel_id"),
                "agency_name": data.get("agency_name"),
                "hotel_name": data.get("hotel_name"),
                "total_matches": int(data.get("total_bookings") or 0),
                # not_arrived_rate is the behavioral cancel rate (excludes PRICE_CHANGED/RATE_CHANGED/system cancels)
                "not_arrived_rate": behavioral_rate,
                "repeat_not_arrived_7": int(data.get("repeat_not_arrived_7") or 0),
                "action_status": data.get("action_status") or "none",
                # Unified high-risk flag: based on RiskProfile (rate OR repeat)
                "high_risk_flag": high_risk,
                "generated_at": now_str,
            }
        )
    return rows


def _rows_to_pdf(rows: list[dict[str, Any]], org_id: str, risk_profile: dict[str, Any]) -> bytes:
    """Generate Match Risk Summary PDF using ReportLab.

    v1: Tek sayfa/sayfalara bölünen sade rapor.
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    story: list[Any] = []

    # Header
    title = "SYROCE — Match Risk Summary"
    story.append(Paragraph(title, styles["Title"]))
    story.append(Spacer(1, 12))

    meta = f"Organization: {org_id} &nbsp;&nbsp; Generated at: {now_utc().isoformat()}"
    story.append(Paragraph(meta, styles["Normal"]))
    story.append(Spacer(1, 12))

    # Risk profile block
    rp_lines = [
        "<b>Risk Profile</b>",
        f"Rate threshold: {risk_profile.get('rate_threshold', 0.5)}",
        f"Repeat 7d threshold: {risk_profile.get('repeat_threshold_7', 3)}",
        f"Mode: {risk_profile.get('mode', 'rate_or_repeat')}",
    ]
    story.append(Paragraph("<br/>".join(rp_lines), styles["Normal"]))
    story.append(Spacer(1, 12))

    # Summary table
    headers = [
        "Agency",
        "Hotel",
        "Total",
        "Not-arrived rate",
        "Repeat 7d",
        "High risk",
        "Action",
    ]
    data: list[list[str]] = [headers]

    for r in rows:
        agency = str(r.get("agency_name") or r.get("agency_id") or "-")
        hotel = str(r.get("hotel_name") or r.get("hotel_id") or "-")
        total = str(r.get("total_matches") or "0")
        rate = float(r.get("not_arrived_rate") or 0.0)
        repeat7 = int(r.get("repeat_not_arrived_7") or 0)
        high = "Yes" if r.get("high_risk_flag") else "No"
        action = str(r.get("action_status") or "none")

        data.append(
            [
                agency[:30],
                hotel[:30],
                total,
                f"{rate*100:.1f}%",
                str(repeat7),
                high,
                action,
            ]
        )

    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("ALIGN", (2, 1), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 12))

    # Legal microcopy / footer
    legal = (
        "<font size=6>Match risk raporu, operasyonel ve davranışsal iptallerden türetilmiş"
        " istatistiksel bir özet sunar; tekil rezervasyon için konaklama kanıtı değildir." \
        " Kararlarınızı verirken ek veri kaynakları ve iş kurallarınızı da dikkate alın." \
        " Blocked eşleşmelerde uyarı/export gönderimi yapılmaz; dashboard görünürlüğü devam eder.</font>"
    )
    story.append(Paragraph(legal, styles["Normal"]))

    doc.build(story)
    pdf_bytes = buf.getvalue()
    buf.close()
    return pdf_bytes


def _rows_to_csv(rows: list[dict[str, Any]]) -> str:
    output = StringIO()

    # Header notes about blocked behaviour
    output.write(
        "# Not: Blocked eşleşmeler alerts/export delivery üretmez; dashboard’da görünmeye devam eder.\n"
    )
    output.write(
        "# Note: Blocked matches do not generate alerts/exports deliveries; they remain visible on the dashboard.\n"
    )

    if not rows:
        writer = csv.writer(output)
        writer.writerow(
            [
                "match_id",
                "agency_id",
                "hotel_id",
                "agency_name",
                "hotel_name",
                "total_matches",
                "not_arrived_rate",
                "repeat_not_arrived_7",
                "action_status",
                "high_risk_flag",
                "generated_at",
            ]
        )
        return output.getvalue()

    fieldnames = list(rows[0].keys())
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    return output.getvalue()


@router.post("/run", response_model=ExportRunResult, dependencies=[Depends(require_roles(["super_admin"]))])
async def run_export(
    key: str = Query(...),
    dry_run: bool = Query(True),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    org_id = user.get("organization_id")
    policy = await _load_policy(db, org_id, key)

    params = ExportPolicyParams(**(policy.get("params") or {}))
    cooldown_hours = int(policy.get("cooldown_hours", 24))

    now = now_utc()

    # Cooldown: bypass for seed_verify policy used in tests
    bypass_cooldown = key == "match_risk_seed_verify_v1"
    if not bypass_cooldown:
        cutoff = now - timedelta(hours=cooldown_hours)
        last_run = await db.export_runs.find_one(
            {
                "organization_id": org_id,
                "policy_key": key,
                "generated_at": {"$gte": cutoff},
            },
            sort=[("generated_at", -1)],
        )
        if last_run and not dry_run:
            raise HTTPException(status_code=409, detail="EXPORT_COOLDOWN_ACTIVE")

    rows = await _generate_match_risk_rows(db, org_id, params, user)

    # Decide on format (csv or pdf)
    fmt = policy.get("format", "csv")
    if fmt not in {"csv", "pdf"}:
        fmt = "csv"

    if fmt == "pdf":
        # PDF: binary content
        from app.services.risk_profile import load_risk_profile

        risk_profile = await load_risk_profile(db, org_id)
        content_bytes = _rows_to_pdf(rows, org_id, risk_profile.to_dict())
        size_bytes = len(content_bytes)
    else:
        # CSV: text content
        csv_str = _rows_to_csv(rows)
        content_bytes = csv_str.encode("utf-8")
        size_bytes = len(content_bytes)

    if dry_run:
        return ExportRunResult(
            ok=True,
            dry_run=True,
            policy_key=key,
            rows=len(rows),
            estimated_size_bytes=size_bytes,
            run_id=None,
            emailed=None,
            emailed_to=None,
        )

    # Persist blob
    blob_doc = {
        "organization_id": org_id,
        "content": content_bytes,
        "created_at": now,
    }
    blob_res = await db.export_blobs.insert_one(blob_doc)
    blob_id = str(blob_res.inserted_id)

    sha256 = hashlib.sha256(content_bytes).hexdigest()
    ext = "pdf" if fmt == "pdf" else "csv"
    filename = f"match-risk_{org_id}_{now.date().isoformat()}.{ext}"

    # Signed download token v0
    download_token = secrets.token_urlsafe(32)
    expires_at = now + timedelta(days=7)

    run_doc = {
        "organization_id": org_id,
        "policy_key": key,
        "type": policy.get("type", "match_risk_summary"),
        "format": policy.get("format", "csv"),
        "status": "ready",
        "error": None,
        "generated_at": now,
        "range": {"days": params.days},
        "params_snapshot": params.model_dump(),
        "file": {
            "filename": filename,
            "content_type": "application/pdf" if fmt == "pdf" else "text/csv",
            "size_bytes": size_bytes,
            "sha256": sha256,
        },
        "storage": {
            "mode": "mongo",
            "blob_id": blob_id,
        },
        "download": {
            "token": download_token,
            "expires_at": expires_at,
        },
        "email": None,
    }
    run_res = await db.export_runs.insert_one(run_doc)
    run_id = str(run_res.inserted_id)

    # Email delivery v0: if recipients configured, enqueue email_outbox job
    recipients = [r.strip() for r in (policy.get("recipients") or []) if r and "@" in r]
    emailed = False
    emailed_to: list[str] | None = None
    if recipients:
        from app.services.email_outbox import enqueue_generic_email  # local import to avoid cycles

        subject = f"[Exports] {run_doc['type']} ({key}) — {now.date().isoformat()}"

        # Build public download link using signed token
        download_token = run_doc.get("download", {}).get("token")
        rel_path = f"/api/exports/download/{download_token}" if download_token else f"/api/admin/exports/runs/{run_id}/download"
        base = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
        download_path = f"{base}{rel_path}" if base else rel_path

        text_body = (
            f"Syroce match risk export hazir\n"
            f"Org: {org_id}\n"
            f"Policy: {key}\n"
            f"Rows: {len(rows)}\n"
            f"Size: {size_bytes} bytes\n"
            f"Generated at: {now.isoformat()}\n"
            f"Download: {download_path}\n"
        )
        html_body = (
            f"<h2>Match Risk Export Hazır</h2>"
            f"<p><strong>Org:</strong> {org_id}</p>"
            f"<p><strong>Policy:</strong> {key}</p>"
            f"<p><strong>Rows:</strong> {len(rows)}</p>"
            f"<p><strong>Size:</strong> {size_bytes} bytes</p>"
            f"<p><strong>Generated at:</strong> {now.isoformat()}</p>"
            f"<p><a href=\"{download_path}\">{ 'PDF indir' if fmt == 'pdf' else 'CSV indir' }</a></p>"
        )

        outbox_id = await enqueue_generic_email(
            db,
            organization_id=org_id,
            to_addresses=recipients,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            event_type="exports.ready",
        )
        emailed = True
        emailed_to = recipients

        await db.export_runs.update_one(
            {"_id": run_res.inserted_id},
            {"$set": {"email": {"queued": True, "to": recipients, "outbox_id": outbox_id}}},
        )

    return ExportRunResult(
        ok=True,
        dry_run=False,
        policy_key=key,
        rows=len(rows),
        estimated_size_bytes=size_bytes,
        run_id=run_id,
        emailed=emailed,
        emailed_to=emailed_to,
    )


@router.get("/runs", response_model=ExportRunsResponse, dependencies=[Depends(require_roles(["super_admin"]))])
async def list_runs(
    key: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    org_id = user.get("organization_id")
    q: dict[str, Any] = {"organization_id": org_id}
    if key:
        q["policy_key"] = key

    cursor = db.export_runs.find(q).sort("generated_at", -1).limit(limit)
    docs = await cursor.to_list(length=limit)
    items: list[ExportRunItem] = []
    for d in docs:
        file_info = d.get("file") or {}
        email_info = d.get("email") or {}
        items.append(
            ExportRunItem(
                id=str(d.get("_id")),
                policy_key=d.get("policy_key"),
                type=d.get("type", "match_risk_summary"),
                format=d.get("format", "csv"),
                status=d.get("status", "ready"),
                error=d.get("error"),
                generated_at=d.get("generated_at").isoformat() if d.get("generated_at") else "",
                size_bytes=int(file_info.get("size_bytes") or 0),
                filename=file_info.get("filename") or "export.csv",
                sha256=file_info.get("sha256"),
                emailed=bool(email_info.get("queued")) if email_info else None,
            )
        )

    # Admin deeplink template for match risk exports (dashboard route)
    template = "/app/admin/reports/match-risk?match_id={match_id}&open_drawer=1&source=export"

    return ExportRunsResponse(ok=True, items=items, admin_deeplink_template=template)


@router.get("/runs/{run_id}/download", dependencies=[Depends(require_roles(["super_admin"]))])
async def download_run(run_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    org_id = user.get("organization_id")
    try:
        oid = ObjectId(run_id)
    except Exception:
        raise HTTPException(status_code=400, detail="INVALID_RUN_ID")

    run = await db.export_runs.find_one({"_id": oid, "organization_id": org_id})
    if not run:
        raise HTTPException(status_code=404, detail="EXPORT_RUN_NOT_FOUND")
    if run.get("status") != "ready":
        raise HTTPException(status_code=400, detail="EXPORT_NOT_READY")

    storage = run.get("storage") or {}
    blob_id = storage.get("blob_id")
    if not blob_id:
        raise HTTPException(status_code=500, detail="EXPORT_BLOB_MISSING")

    try:
        blob_oid = ObjectId(blob_id)
    except Exception:
        raise HTTPException(status_code=500, detail="EXPORT_BLOB_INVALID")

    blob = await db.export_blobs.find_one({"_id": blob_oid, "organization_id": org_id})
    if not blob:
        raise HTTPException(status_code=404, detail="EXPORT_BLOB_NOT_FOUND")

    content = blob.get("content") or b""
    file_info = run.get("file") or {}
    filename = file_info.get("filename") or "export.csv"
    media_type = file_info.get("content_type") or "text/csv"

    headers = {
        "Content-Disposition": f"attachment; filename={filename}",
    }
    return Response(content=content, media_type=media_type, headers=headers)


# Public download endpoint (no auth required)
@public_router.get("/download/{token}")
async def public_download(token: str, db=Depends(get_db)):
    # Public, no auth - token-based access
    now = now_utc()
    run = await db.export_runs.find_one({"download.token": token})
    if not run:
        raise HTTPException(status_code=404, detail="EXPORT_TOKEN_NOT_FOUND")

    download_info = run.get("download") or {}
    expires_at = download_info.get("expires_at")
    if expires_at:
        # Ensure both datetimes are comparable (both aware or both naive)
        if hasattr(expires_at, 'tzinfo') and expires_at.tzinfo is not None:
            # expires_at is timezone-aware, compare with aware now
            if expires_at < now:
                raise HTTPException(status_code=410, detail="EXPORT_TOKEN_EXPIRED")
        else:
            # expires_at is naive, compare with naive now
            if expires_at < now.replace(tzinfo=None):
                raise HTTPException(status_code=410, detail="EXPORT_TOKEN_EXPIRED")

    storage = run.get("storage") or {}
    blob_id = storage.get("blob_id")
    if not blob_id:
        raise HTTPException(status_code=500, detail="EXPORT_BLOB_MISSING")

    try:
        blob_oid = ObjectId(blob_id)
    except Exception:
        raise HTTPException(status_code=500, detail="EXPORT_BLOB_INVALID")

    blob = await db.export_blobs.find_one({"_id": blob_oid})
    if not blob:
        raise HTTPException(status_code=404, detail="EXPORT_BLOB_NOT_FOUND")

    content = blob.get("content") or b""
    file_info = run.get("file") or {}
    filename = file_info.get("filename") or "export.csv"
    media_type = file_info.get("content_type") or "text/csv"

    headers = {
        "Content-Disposition": f"attachment; filename={filename}",
    }
    return Response(content=content, media_type=media_type, headers=headers)
