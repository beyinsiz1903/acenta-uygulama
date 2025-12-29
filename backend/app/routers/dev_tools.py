from fastapi import APIRouter, Depends, HTTPException

from app.db import get_db
from app.auth import require_roles
from app.auth import get_current_user

router = APIRouter(prefix="/api/dev", tags=["dev"])


@router.post(
    "/tours/{tour_id}/add-demo-images",
    dependencies=[Depends(require_roles(["super_admin", "agency_admin"]))],
)
async def add_demo_images(tour_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    """Add demo images to a tour for local/demo purposes.

    This endpoint is intended for local/demo usage to ensure at least one
    tour has multiple images so that the public gallery/lightbox can be
    demonstrated and tested.
    """
    org_id = str(user.get("organization_id")) if user else None
    if not org_id:
        raise HTTPException(status_code=403, detail="FORBIDDEN")

    demo_images = [
        "https://picsum.photos/seed/sapanca-1/1200/800",
        "https://picsum.photos/seed/sapanca-2/1200/800",
        "https://picsum.photos/seed/sapanca-3/1200/800",
    ]

    tour = await db.tours.find_one({"_id": tour_id, "organization_id": org_id})
    if not tour:
        raise HTTPException(status_code=404, detail="TOUR_NOT_FOUND")

    existing = tour.get("images") or []

    merged: list[str] = []
    for u in existing + demo_images:
        if isinstance(u, str):
            u = u.strip()
            if u and u not in merged:
                merged.append(u)

    await db.tours.update_one(
        {"_id": tour_id, "organization_id": org_id},
        {"$set": {"images": merged}},
    )

    return {"ok": True, "tour_id": tour_id, "images_count": len(merged)}
