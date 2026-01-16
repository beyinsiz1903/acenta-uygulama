from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from app.auth import require_feature, require_roles
from app.db import get_db

router = APIRouter(prefix="/api", tags=["metrics"])


AdminDep = Depends(require_roles(["super_admin"]))
FeatureDep = Depends(require_feature("ops_observability"))


@router.get("/metrics", response_class=PlainTextResponse)
async def metrics(
    _user=AdminDep,  # noqa: B008
    _feature=FeatureDep,  # noqa: B008
    db=Depends(get_db),
) -> str:
    """Minimal Prometheus-style metrics for jobs.

    We compute aggregate counts on demand from the jobs collection. This is not
    a full time-series store but good enough for basic observability.
    """

    pipeline = [
        {
            "$group": {
                "_id": {"type": "$type", "status": "$status"},
                "count": {"$sum": 1},
            }
        }
    ]
    rows: list[Dict[str, Any]] = await db.jobs.aggregate(pipeline).to_list(length=1000)

    lines: list[str] = []
    lines.append("# TYPE jobs_processed_total counter")

    for row in rows:
        group = row.get("_id") or {}
        job_type = (group.get("type") or "unknown").replace("\n", "_")
        status = (group.get("status") or "unknown").replace("\n", "_")
        count = int(row.get("count") or 0)
        lines.append(f"jobs_processed_total{{type=\"{job_type}\",status=\"{status}\"}} {count}")

    dead_rows = [r for r in rows if (r.get("_id") or {}).get("status") == "dead"]
    lines.append("# TYPE jobs_dead_total counter")
    for row in dead_rows:
        job_type = (row["_id"].get("type") or "unknown").replace("\n", "_")
        count = int(row.get("count") or 0)
        lines.append(f"jobs_dead_total{{type=\"{job_type}\"}} {count}")

    return "\n".join(lines) + "\n"