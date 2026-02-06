from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Response

from app.auth import get_current_user
from app.constants.features import FEATURE_REPORTS
from app.db import get_db
from app.security.feature_flags import require_tenant_feature
from app.utils import serialize_doc, to_csv

router = APIRouter(prefix="/api/reports", tags=["reports"])

ReportsFeatureDep = Depends(require_tenant_feature(FEATURE_REPORTS))


@router.get("/reservations-summary", dependencies=[Depends(get_current_user), ReportsFeatureDep])
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
async def sales_summary_csv(user=Depends(get_current_user)):
    rows = await sales_summary(user=user)
    csv_str = to_csv(rows, ["day", "revenue", "count"])
    return Response(content=csv_str, media_type="text/csv")
