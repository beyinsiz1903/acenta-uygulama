from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response

from app.auth import require_super_admin_only
from app.db import get_db
from app.services.report_output_service import generate_match_risk_executive_pdf
from app.utils import get_or_create_correlation_id

router = APIRouter(prefix="/api/admin/reports/match-risk", tags=["admin-match-risk-reports"])


@router.get("/executive-summary.pdf", dependencies=[Depends(require_super_admin_only())])
async def download_match_risk_executive_pdf(
  request: Request,
  db=Depends(get_db),
  user=Depends(require_super_admin_only()),
):
  artifact = await generate_match_risk_executive_pdf(
    db,
    organization_id=user.get("organization_id"),
    organization_name=user.get("organization_name") or "",
    correlation_id=get_or_create_correlation_id(request, None),
    tenant_id=user.get("tenant_id"),
  )

  return Response(
    content=artifact["content"],
    media_type="application/pdf",
    headers={
      "Content-Type": "application/pdf",
      "Content-Disposition": f"attachment; filename=\"{artifact['filename']}\"",
    },
  )
