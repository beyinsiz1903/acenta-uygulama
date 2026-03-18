"""Standard API Response helpers.

Usage in endpoints:

    from app.response import paginated, success

    @router.get("/items")
    async def list_items(page: int = 1, per_page: int = 20):
        items, total = await get_items(page, per_page)
        return paginated(items, page=page, per_page=per_page, total=total)

    @router.post("/items")
    async def create_item(body: ItemCreate):
        item = await insert_item(body)
        return success(item, status="created")
"""
from __future__ import annotations

import math
from typing import Any


def paginated(
    items: list[Any],
    *,
    page: int = 1,
    per_page: int = 20,
    total: int = 0,
) -> dict[str, Any]:
    """Return a paginated response with pagination metadata.

    The envelope middleware will wrap this as:
    {
      "ok": true,
      "data": {
        "items": [...],
        "pagination": { "page": 1, "per_page": 20, "total": 100, "total_pages": 5 }
      },
      "meta": { ... }
    }
    """
    total_pages = math.ceil(total / per_page) if per_page > 0 else 0
    return {
        "items": items,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        },
    }
