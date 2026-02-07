"""Enterprise Full Data Export (E4.2).

POST /api/admin/tenant/export
Returns a ZIP file with all tenant data as JSON files.
Admin only.
"""
from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.utils import serialize_doc

router = APIRouter(prefix="/api/admin/tenant", tags=["enterprise_export"])

AdminDep = Depends(require_roles(["super_admin", "admin"]))

# Collections to export with their query key
EXPORT_COLLECTIONS = [
    ("customers", "organization_id"),
    ("crm_deals", "organization_id"),
    ("crm_tasks", "organization_id"),
    ("reservations", "organization_id"),
    ("payments", "organization_id"),
    ("products", "organization_id"),
    ("crm_notes", "organization_id"),
    ("crm_activities", "organization_id"),
]


def _json_serial(obj: Any) -> str:
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)


@router.post("/export", dependencies=[AdminDep])
async def export_tenant_data(
    user=Depends(get_current_user),
):
    """Export all tenant data as a ZIP file."""
    db = await get_db()
    org_id = user["organization_id"]

    # Build ZIP in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for collection_name, query_key in EXPORT_COLLECTIONS:
            try:
                collection = db[collection_name]
                cursor = collection.find({query_key: org_id})
                docs = await cursor.to_list(length=10000)
                serialized = [serialize_doc(d) for d in docs]

                json_content = json.dumps(
                    serialized,
                    indent=2,
                    default=_json_serial,
                    ensure_ascii=False,
                )
                zf.writestr(f"{collection_name}.json", json_content)
            except Exception:
                # Skip collections that don't exist or error
                zf.writestr(f"{collection_name}.json", "[]")

        # Add export metadata
        meta = {
            "exported_at": datetime.utcnow().isoformat(),
            "organization_id": org_id,
            "exported_by": user.get("email", ""),
            "collections": [c[0] for c in EXPORT_COLLECTIONS],
        }
        zf.writestr("_metadata.json", json.dumps(meta, indent=2))

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=tenant_export_{org_id[:8]}.zip"
        },
    )
