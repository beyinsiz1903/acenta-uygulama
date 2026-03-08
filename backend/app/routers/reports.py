from __future__ import annotations


from fastapi import APIRouter, Depends, Request, Response

from app.auth import get_current_user
from app.constants.features import FEATURE_REPORTS
from app.db import get_db
from app.services.usage_service import track_export_generated
from app.utils import get_or_create_correlation_id
from app.security.feature_flags import require_tenant_feature
from app.utils import to_csv

router = APIRouter(prefix="/api/reports", tags=["reports"])

ReportsFeatureDep = Depends(require_tenant_feature(FEATURE_REPORTS))


@router.get("/reservations-summary", dependencies=[Depends(get_current_user)])
async def reservations_summary(user=Depends(get_current_user)):
    db = await get_db()
    pipeline = [
        {"$match": {"organization_id": user["organization_id"]}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    rows = await db.reservations.aggregate(pipeline).to_list(100)
    return [{"status": r["_id"], "count": r["count"]} for r in rows]


@router.get("/sales-summary", dependencies=[Depends(get_current_user)])
async def sales_summary(days: int = 14, user=Depends(get_current_user)):
    db = await get_db()

    # group by reservation created day (YYYY-MM-DD)
    pipeline = [
        {"$match": {"organization_id": user["organization_id"]}},
        {
            "$addFields": {
                "created_day": {"$substr": [{"$toString": "$created_at"}, 0, 10]}
            }
        },
        {
            "$group": {
                "_id": "$created_day",
                "revenue": {"$sum": "$total_price"},
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    rows = await db.reservations.aggregate(pipeline).to_list(400)
    return [{"day": r["_id"], "revenue": round(float(r.get("revenue") or 0), 2), "count": r["count"]} for r in rows]


@router.get("/sales-summary.csv", dependencies=[Depends(get_current_user)])
async def sales_summary_csv(request: Request, user=Depends(get_current_user)):
    rows = await sales_summary(user=user)
    csv_str = to_csv(rows, ["day", "revenue", "count"])
    await track_export_generated(
        organization_id=user.get("organization_id"),
        tenant_id=user.get("tenant_id"),
        export_type="sales_summary",
        output_format="csv",
        source="reports.sales_summary",
        source_event_id=f"{get_or_create_correlation_id(request, None)}:sales-summary-csv",
        metadata={"row_count": len(rows)},
    )
    return Response(content=csv_str, media_type="text/csv")
