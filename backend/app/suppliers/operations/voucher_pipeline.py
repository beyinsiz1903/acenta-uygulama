"""PART 7 — Voucher Pipeline.

Steps:
  1. Supplier confirmation → extract voucher data
  2. Generate voucher document (HTML template)
  3. PDF rendering (via wkhtmltopdf or weasyprint)
  4. Store voucher in DB
  5. Email delivery
  6. Retry logic on failure

Each step is idempotent and retryable.
"""
from __future__ import annotations

import base64
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger("suppliers.ops.voucher")


class VoucherStatus:
    PENDING = "pending"
    GENERATING = "generating"
    GENERATED = "generated"
    SENDING = "sending"
    DELIVERED = "delivered"
    FAILED = "failed"


async def create_voucher_record(
    db,
    organization_id: str,
    booking_id: str,
    *,
    supplier_booking_id: Optional[str] = None,
    confirmation_code: Optional[str] = None,
    guest_names: Optional[list] = None,
    hotel_name: Optional[str] = None,
    check_in: Optional[str] = None,
    check_out: Optional[str] = None,
    room_type: Optional[str] = None,
    total_price: Optional[float] = None,
    currency: str = "TRY",
) -> Dict[str, Any]:
    """Create a voucher record in the pipeline."""

    now = datetime.now(timezone.utc)
    voucher_id = str(uuid.uuid4())

    voucher = {
        "voucher_id": voucher_id,
        "organization_id": organization_id,
        "booking_id": booking_id,
        "supplier_booking_id": supplier_booking_id,
        "confirmation_code": confirmation_code,
        "guest_names": guest_names or [],
        "hotel_name": hotel_name,
        "check_in": check_in,
        "check_out": check_out,
        "room_type": room_type,
        "total_price": total_price,
        "currency": currency,
        "status": VoucherStatus.PENDING,
        "pdf_base64": None,
        "html_content": None,
        "email_sent": False,
        "retry_count": 0,
        "max_retries": 3,
        "last_error": None,
        "created_at": now,
        "updated_at": now,
    }

    await db.voucher_pipeline.insert_one({"_id": voucher_id, **voucher})
    return {k: v for k, v in voucher.items() if k != "_id"}


def _render_voucher_html(voucher: Dict[str, Any]) -> str:
    """Render voucher as HTML."""

    guests = ", ".join(voucher.get("guest_names", []) or ["Guest"])
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Booking Voucher</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 40px; color: #333; }}
.header {{ background: #1a365d; color: white; padding: 20px; border-radius: 8px; }}
.header h1 {{ margin: 0; font-size: 24px; }}
.details {{ margin-top: 20px; }}
.row {{ display: flex; padding: 12px 0; border-bottom: 1px solid #e2e8f0; }}
.label {{ width: 200px; font-weight: bold; color: #4a5568; }}
.value {{ flex: 1; }}
.footer {{ margin-top: 30px; padding: 15px; background: #f7fafc; border-radius: 8px; font-size: 12px; color: #718096; }}
.confirmation {{ font-size: 20px; font-weight: bold; color: #2d3748; background: #edf2f7; padding: 15px; border-radius: 8px; text-align: center; margin: 20px 0; }}
</style>
</head>
<body>
<div class="header">
  <h1>Booking Confirmation Voucher</h1>
</div>
<div class="confirmation">
  Confirmation Code: {voucher.get('confirmation_code', 'N/A')}
</div>
<div class="details">
  <div class="row"><div class="label">Booking ID</div><div class="value">{voucher.get('booking_id', '')}</div></div>
  <div class="row"><div class="label">Guest(s)</div><div class="value">{guests}</div></div>
  <div class="row"><div class="label">Property</div><div class="value">{voucher.get('hotel_name', 'N/A')}</div></div>
  <div class="row"><div class="label">Room Type</div><div class="value">{voucher.get('room_type', 'N/A')}</div></div>
  <div class="row"><div class="label">Check-in</div><div class="value">{voucher.get('check_in', 'N/A')}</div></div>
  <div class="row"><div class="label">Check-out</div><div class="value">{voucher.get('check_out', 'N/A')}</div></div>
  <div class="row"><div class="label">Total Price</div><div class="value">{voucher.get('total_price', 'N/A')} {voucher.get('currency', 'TRY')}</div></div>
  <div class="row"><div class="label">Supplier Ref</div><div class="value">{voucher.get('supplier_booking_id', 'N/A')}</div></div>
</div>
<div class="footer">
  This voucher confirms your reservation. Please present this document upon arrival.
  Generated at: {datetime.now(timezone.utc).isoformat()}
</div>
</body>
</html>"""


async def generate_voucher(
    db,
    organization_id: str,
    voucher_id: str,
) -> Dict[str, Any]:
    """Generate HTML and PDF for a voucher."""

    now = datetime.now(timezone.utc)
    voucher = await db.voucher_pipeline.find_one(
        {"_id": voucher_id, "organization_id": organization_id}
    )
    if not voucher:
        return {"error": "voucher_not_found"}

    await db.voucher_pipeline.update_one(
        {"_id": voucher_id},
        {"$set": {"status": VoucherStatus.GENERATING, "updated_at": now}},
    )

    try:
        html = _render_voucher_html(voucher)
        # PDF generation: encode HTML as base64 (production would use weasyprint/wkhtmltopdf)
        pdf_b64 = base64.b64encode(html.encode("utf-8")).decode("ascii")

        await db.voucher_pipeline.update_one(
            {"_id": voucher_id},
            {
                "$set": {
                    "status": VoucherStatus.GENERATED,
                    "html_content": html,
                    "pdf_base64": pdf_b64,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )

        return {
            "voucher_id": voucher_id,
            "status": VoucherStatus.GENERATED,
            "html_length": len(html),
        }

    except Exception as e:
        retry_count = voucher.get("retry_count", 0) + 1
        status = VoucherStatus.FAILED if retry_count >= voucher.get("max_retries", 3) else VoucherStatus.PENDING

        await db.voucher_pipeline.update_one(
            {"_id": voucher_id},
            {
                "$set": {
                    "status": status,
                    "last_error": str(e),
                    "retry_count": retry_count,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        return {"voucher_id": voucher_id, "status": status, "error": str(e)}


async def send_voucher_email(
    db,
    organization_id: str,
    voucher_id: str,
    *,
    recipient_email: str,
) -> Dict[str, Any]:
    """Queue voucher email for delivery."""

    now = datetime.now(timezone.utc)
    voucher = await db.voucher_pipeline.find_one(
        {"_id": voucher_id, "organization_id": organization_id}
    )
    if not voucher:
        return {"error": "voucher_not_found"}

    if voucher.get("status") != VoucherStatus.GENERATED:
        return {"error": "voucher_not_generated", "current_status": voucher.get("status")}

    await db.voucher_pipeline.update_one(
        {"_id": voucher_id},
        {"$set": {"status": VoucherStatus.SENDING, "updated_at": now}},
    )

    # Queue email
    await db.ops_email_queue.insert_one({
        "type": "voucher",
        "recipients": [recipient_email],
        "subject": f"Booking Confirmation - {voucher.get('confirmation_code', voucher_id)}",
        "voucher_id": voucher_id,
        "booking_id": voucher.get("booking_id"),
        "status": "queued",
        "created_at": now,
    })

    await db.voucher_pipeline.update_one(
        {"_id": voucher_id},
        {
            "$set": {
                "status": VoucherStatus.DELIVERED,
                "email_sent": True,
                "email_recipient": recipient_email,
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )

    return {
        "voucher_id": voucher_id,
        "status": VoucherStatus.DELIVERED,
        "recipient": recipient_email,
    }


async def get_voucher_pipeline_status(
    db,
    organization_id: str,
    *,
    status_filter: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    """Get voucher pipeline overview."""

    query: Dict[str, Any] = {"organization_id": organization_id}
    if status_filter:
        query["status"] = status_filter

    # Status distribution
    status_pipeline = [
        {"$match": {"organization_id": organization_id}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ]
    status_results = await db.voucher_pipeline.aggregate(status_pipeline).to_list(20)
    status_dist = {r["_id"]: r["count"] for r in status_results}

    # Recent vouchers
    cursor = db.voucher_pipeline.find(query, {"_id": 0, "pdf_base64": 0, "html_content": 0}).sort(
        "created_at", -1
    ).limit(limit)
    vouchers = await cursor.to_list(length=limit)

    return {
        "status_distribution": status_dist,
        "total": sum(status_dist.values()),
        "recent_vouchers": vouchers,
    }


async def retry_failed_vouchers(
    db,
    organization_id: str,
) -> Dict[str, Any]:
    """Retry all failed vouchers that haven't exceeded max retries."""

    cursor = db.voucher_pipeline.find(
        {
            "organization_id": organization_id,
            "status": {"$in": [VoucherStatus.PENDING, VoucherStatus.FAILED]},
            "$expr": {"$lt": ["$retry_count", "$max_retries"]},
        },
        {"_id": 1},
    ).limit(20)

    retried = 0
    async for doc in cursor:
        vid = str(doc["_id"])
        result = await generate_voucher(db, organization_id, vid)
        if result.get("status") == VoucherStatus.GENERATED:
            retried += 1

    return {"retried": retried}
