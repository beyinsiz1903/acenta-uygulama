from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.routers.matches import list_matches
from app.services.email_outbox import enqueue_generic_email
from app.services.match_webhook import send_match_alert_webhook
from app.utils import now_utc

router = APIRouter(prefix="/api/admin/match-alerts", tags=["admin-match-alerts"])


@dataclass
class MatchAlertPolicy:
    organization_id: str
    enabled: bool = True
    threshold_not_arrived_rate: float = 0.5
    threshold_repeat_not_arrived_7: int = 3
    min_matches_total: int = 5
    cooldown_hours: int = 24
    email_recipients: list[str] | None = None
    webhook_url: str | None = None
    webhook_enabled: bool = False
    webhook_secret: str | None = None
    webhook_timeout_ms: int = 4000


class MatchAlertPolicyModel(BaseModel):
    enabled: bool = True
    threshold_not_arrived_rate: float = Field(0.5, ge=0.0, le=1.0)
    threshold_repeat_not_arrived_7: int = Field(3, ge=0)
    min_matches_total: int = Field(5, ge=1)
    cooldown_hours: int = Field(24, ge=1, le=168)
    email_recipients: list[str] | None = None
    webhook_url: str | None = None
    webhook_enabled: bool = False
    webhook_secret: str | None = None
    webhook_timeout_ms: int = Field(4000, ge=500, le=10000)


class MatchAlertPolicyResponse(BaseModel):
    organization_id: str
    policy: MatchAlertPolicyModel


class MatchAlertRunItem(BaseModel):
    match_id: str
    agency_id: str
    agency_name: Optional[str] = None
    hotel_id: str
    hotel_name: Optional[str] = None
    total_bookings: int
    cancel_rate: float
    repeat_not_arrived_7: Optional[int] = None
    action_status: Optional[str] = None
    triggered_by_rate: bool
    triggered_by_repeat: bool


class MatchAlertRunResult(BaseModel):
    ok: bool = True
    evaluated_count: int
    triggered_count: int
    sent_count: int
    failed_count: int
    dry_run: bool
    items: list[MatchAlertRunItem]


async def _load_policy(db, org_id: str) -> MatchAlertPolicy:
    doc = await db.match_alert_policies.find_one({"organization_id": org_id})
    if not doc:
        return MatchAlertPolicy(organization_id=org_id)

    return MatchAlertPolicy(
        organization_id=org_id,
        enabled=bool(doc.get("enabled", True)),
        threshold_not_arrived_rate=float(doc.get("threshold_not_arrived_rate", 0.5)),
        threshold_repeat_not_arrived_7=int(doc.get("threshold_repeat_not_arrived_7", 3)),
        min_matches_total=int(doc.get("min_matches_total", 5)),
        cooldown_hours=int(doc.get("cooldown_hours", 24)),
        email_recipients=list(doc.get("email_recipients") or []),
        webhook_url=doc.get("webhook_url"),
        webhook_enabled=bool(doc.get("webhook_enabled", False)),
        webhook_secret=doc.get("webhook_secret"),
        webhook_timeout_ms=int(doc.get("webhook_timeout_ms", 4000)),
    )


@router.get("/policy", response_model=MatchAlertPolicyResponse, dependencies=[Depends(require_roles(["super_admin"]))])
async def get_policy(db=Depends(get_db), user=Depends(get_current_user)):
    org_id = user.get("organization_id")
    policy = await _load_policy(db, org_id)
    return MatchAlertPolicyResponse(organization_id=org_id, policy=MatchAlertPolicyModel(**asdict(policy)))


@router.put("/policy", response_model=MatchAlertPolicyResponse, dependencies=[Depends(require_roles(["super_admin"]))])
async def update_policy(payload: MatchAlertPolicyModel, db=Depends(get_db), user=Depends(get_current_user)):
    org_id = user.get("organization_id")
    data = payload.model_dump()
    data["organization_id"] = org_id

    await db.match_alert_policies.update_one(
        {"organization_id": org_id},
        {"$set": data},
        upsert=True,
    )

    return MatchAlertPolicyResponse(organization_id=org_id, policy=payload)


def _match_fingerprint(match_id: str, *, days: int, min_total: int, thr_rate: float, thr_repeat: int, flags: str) -> str:
    return f"{match_id}|d={days}|min={min_total}|r>={thr_rate}|rep>={thr_repeat}|{flags}"


async def _already_sent_recently(db, org_id: str, match_id: str, fingerprint: str, cooldown_hours: int) -> bool:
    now = now_utc()
    cutoff = now - timedelta(hours=cooldown_hours)
    doc = await db.match_alert_deliveries.find_one(
        {
            "organization_id": org_id,
            "match_id": match_id,
            "fingerprint": fingerprint,
            "sent_at": {"$gte": cutoff},
        }
    )
    return doc is not None


async def _record_delivery(
    db,
    org_id: str,
    match_id: str,
    fingerprint: str,
    channel: str,
    status: str,
    *,
    error: str | None = None,
    delivery_target: str | None = None,
    http_status: int | None = None,
    response_snippet: str | None = None,
    outbox_id: str | None = None,
    retry_outbox_id: str | None = None,
    attempt: int = 1,
) -> None:
    now = now_utc()
    update: dict[str, Any] = {
        "organization_id": org_id,
        "match_id": match_id,
        "fingerprint": fingerprint,
        "channel": channel,
        "status": status,
        "error": error,
        "delivery_target": delivery_target,
        "http_status": http_status,
        "response_snippet": response_snippet,
        "outbox_id": outbox_id,
        "retry_outbox_id": retry_outbox_id,
        "attempt": attempt,
        "sent_at": now,
    }

    await db.match_alert_deliveries.update_one(
        {
            "organization_id": org_id,
            "match_id": match_id,
            "fingerprint": fingerprint,
            "channel": channel,
        },
        {"$set": update},
        upsert=True,
    )


async def _send_alert_email(
    db,
    *,
    org_id: str,
    recipients: list[str],
    item: MatchAlertRunItem,
    policy: MatchAlertPolicy,
) -> str:
    if not recipients:
        return ""

    subject = f"[MatchRisk] High risk detected for {item.hotel_name or item.hotel_id}"

    flags = []
    if item.triggered_by_rate:
        flags.append(f"cancel_rate>={policy.threshold_not_arrived_rate:.2f}")
    if item.triggered_by_repeat:
        flags.append(f"repeat_not_arrived_7>={policy.threshold_repeat_not_arrived_7}")

    flags_str = ", ".join(flags)

    html_body = f"""
<h2>High risk match detected</h2>
<p><strong>Agency:</strong> {item.agency_name or item.agency_id}</p>
<p><strong>Hotel:</strong> {item.hotel_name or item.hotel_id}</p>
<p><strong>Match ID:</strong> {item.match_id}</p>
<p><strong>Total bookings (period):</strong> {item.total_bookings}</p>
<p><strong>Cancel rate:</strong> {item.cancel_rate:.2%}</p>
<p><strong>Triggered by:</strong> {flags_str}</p>
<p><strong>Current action:</strong> {item.action_status or "none"}</p>
""".strip()

    text_body = (
        f"High risk match detected\n"
        f"Agency: {item.agency_name or item.agency_id}\n"
        f"Hotel: {item.hotel_name or item.hotel_id}\n"
        f"Match ID: {item.match_id}\n"
        f"Total bookings (period): {item.total_bookings}\n"
        f"Cancel rate: {item.cancel_rate:.2%}\n"
        f"Triggered by: {flags_str}\n"
        f"Current action: {item.action_status or 'none'}\n"
    )

    outbox_id = await enqueue_generic_email(
        db,
        organization_id=org_id,
        to_addresses=recipients,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        event_type="match.alert",
    )
    
    return outbox_id


class MatchAlertDeliveryItem(BaseModel):
    match_id: str
    channel: str
    status: str
    error: Optional[str] = None
    fingerprint: str
    sent_at: str
    delivery_target: Optional[str] = None
    http_status: Optional[int] = None


class MatchAlertDeliveriesResponse(BaseModel):
    ok: bool = True
    items: list[MatchAlertDeliveryItem]


@router.get("/deliveries", response_model=MatchAlertDeliveriesResponse, dependencies=[Depends(require_roles(["super_admin"]))])
async def list_deliveries(
    limit: int = Query(50, ge=1, le=200),
    status: str = Query("all"),
    match_id: Optional[str] = Query(None),
    channel: Optional[str] = Query(None),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    org_id = user.get("organization_id")

    q: dict[str, Any] = {"organization_id": org_id}
    if status in {"sent", "failed"}:
        q["status"] = status
    if match_id:
        q["match_id"] = match_id
    if channel in {"email", "webhook"}:
        q["channel"] = channel

    cursor = (
        db.match_alert_deliveries.find(q)
        .sort("sent_at", -1)
        .limit(limit)
    )
    docs = await cursor.to_list(length=limit)

    items: list[MatchAlertDeliveryItem] = []
    for d in docs:
        sent_at = d.get("sent_at")
        if hasattr(sent_at, "isoformat"):
            sent_at = sent_at.isoformat()
        items.append(
            MatchAlertDeliveryItem(
                match_id=d.get("match_id", ""),
                channel=d.get("channel", "email"),
                status=d.get("status", "sent"),
                error=d.get("error"),
                fingerprint=d.get("fingerprint", ""),
                sent_at=sent_at,
                delivery_target=d.get("delivery_target"),
                http_status=d.get("http_status"),
            )
        )

    return MatchAlertDeliveriesResponse(ok=True, items=items)


class WebhookTestRequest(BaseModel):
    webhook_url: str
    webhook_secret: str | None = None


class WebhookTestResponse(BaseModel):
    ok: bool
    http_status: int | None = None
    snippet: str | None = None
    error: str | None = None


@router.post("/webhook-test", response_model=WebhookTestResponse, dependencies=[Depends(require_roles(["super_admin"]))])
async def test_webhook(payload: WebhookTestRequest, db=Depends(get_db), user=Depends(get_current_user)):
    """Test webhook endpoint with a sample payload"""
    org_id = user.get("organization_id")
    
    # Create a test payload
    test_payload = {
        "event": "match.alert.test",
        "organization_id": org_id,
        "generated_at": now_utc().isoformat(),
        "test": True,
        "message": "This is a test webhook from Syroce Match Alerts"
    }
    
    # Send test webhook
    ok_wh, http_status, snippet, err = await send_match_alert_webhook(
        organization_id=org_id,
        webhook_url=payload.webhook_url,
        webhook_secret=payload.webhook_secret,
        timeout_ms=4000,  # Default timeout
        payload=test_payload,
    )
    
    return WebhookTestResponse(
        ok=ok_wh,
        http_status=http_status,
        snippet=snippet,
        error=err
    )



@router.post("/run", response_model=MatchAlertRunResult, dependencies=[Depends(require_roles(["super_admin"]))])
async def run_match_alerts(
    days: int = Query(30, ge=1, le=365),
    min_total: int = Query(5, ge=1, le=1000),
    dry_run: bool = Query(True),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    org_id = user.get("organization_id")
    policy = await _load_policy(db, org_id)

    if not policy.enabled:
        return MatchAlertRunResult(
            ok=True,
            evaluated_count=0,
            triggered_count=0,
            sent_count=0,
            failed_count=0,
            dry_run=dry_run,
            items=[],
        )

    # Reuse matches aggregation with include_action=1
    matches_resp = await list_matches(days=days, min_total=min_total, include_action=True, db=db, user=user)  # type: ignore[arg-type]
    items_raw = matches_resp["items"] if isinstance(matches_resp, dict) else matches_resp.items

    evaluated_count = 0
    triggered: list[MatchAlertRunItem] = []

    for row in items_raw:
        # row may be dict or Pydantic model
        data: dict[str, Any]
        if isinstance(row, dict):
            data = row
        else:
            data = row.model_dump()

        evaluated_count += 1

        total = int(data.get("total_bookings") or 0)
        if total < policy.min_matches_total:
            continue

        cancel_rate = float(data.get("cancel_rate") or 0.0)
        repeat_7 = int(data.get("repeat_not_arrived_7") or 0)

        triggered_by_rate = cancel_rate >= policy.threshold_not_arrived_rate
        triggered_by_repeat = repeat_7 >= policy.threshold_repeat_not_arrived_7

        if not (triggered_by_rate or triggered_by_repeat):
            continue

        action_status = data.get("action_status") or "none"
        if action_status == "blocked":
            # Already blocked; skip alerts to avoid spam
            continue

        item = MatchAlertRunItem(
            match_id=data.get("id"),
            agency_id=data.get("agency_id"),
            agency_name=data.get("agency_name"),
            hotel_id=data.get("hotel_id"),
            hotel_name=data.get("hotel_name"),
            total_bookings=total,
            cancel_rate=cancel_rate,
            repeat_not_arrived_7=repeat_7,
            action_status=action_status,
            triggered_by_rate=triggered_by_rate,
            triggered_by_repeat=triggered_by_repeat,
        )
        triggered.append(item)

    sent_count = 0
    failed_count = 0

    # Resolve recipients: policy.email_recipients or fallback to current user
    recipients: list[str] = []
    if policy.email_recipients:
        recipients = [e for e in policy.email_recipients if e]
    else:
        email = user.get("email")
        if email:
            recipients = [email]

    # Email channel
    if not dry_run and triggered and recipients:
        for item in triggered:
            flags = []
            if item.triggered_by_rate:
                flags.append("rate")
            if item.triggered_by_repeat:
                flags.append("repeat")
            flags_str = "+".join(flags) or "none"

            fingerprint = _match_fingerprint(
                item.match_id,
                days=days,
                min_total=min_total,
                thr_rate=policy.threshold_not_arrived_rate,
                thr_repeat=policy.threshold_repeat_not_arrived_7,
                flags=flags_str,
            )

            already = await _already_sent_recently(
                db,
                org_id,
                item.match_id,
                fingerprint,
                policy.cooldown_hours,
            )
            if already:
                continue

            try:
                outbox_id = await _send_alert_email(db, org_id=org_id, recipients=recipients, item=item, policy=policy)
                await _record_delivery(
                    db,
                    org_id,
                    item.match_id,
                    fingerprint,
                    channel="email",
                    status="sent",
                    error=None,
                    delivery_target=",".join(recipients),
                    outbox_id=outbox_id,
                )
                sent_count += 1
            except Exception as e:  # pragma: no cover - email failures shouldn't break whole run
                await _record_delivery(
                    db,
                    org_id,
                    item.match_id,
                    fingerprint,
                    channel="email",
                    status="failed",
                    error=str(e),
                    delivery_target=",".join(recipients),
                )
                failed_count += 1

    # Webhook channel
    if not dry_run and triggered and policy.webhook_enabled and policy.webhook_url:
        for item in triggered:
            flags = []
            if item.triggered_by_rate:
                flags.append("rate")
            if item.triggered_by_repeat:
                flags.append("repeat")
            flags_str = "+".join(flags) or "none"

            fingerprint = _match_fingerprint(
                item.match_id,
                days=days,
                min_total=min_total,
                thr_rate=policy.threshold_not_arrived_rate,
                thr_repeat=policy.threshold_repeat_not_arrived_7,
                flags=f"webhook-{flags_str}",
            )

            already = await _already_sent_recently(
                db,
                org_id,
                item.match_id,
                fingerprint,
                policy.cooldown_hours,
            )
            if already:
                continue

            payload = {
                "event": "match.alert",
                "organization_id": org_id,
                "generated_at": now_utc().isoformat(),
                "window": {"days": days, "min_total": min_total},
                "policy": {
                    "threshold_not_arrived_rate": policy.threshold_not_arrived_rate,
                    "cooldown_hours": policy.cooldown_hours,
                },
                "item": item.model_dump(),
            }

            ok_wh, http_status, snippet, err = await send_match_alert_webhook(
                organization_id=org_id,
                webhook_url=policy.webhook_url,
                webhook_secret=policy.webhook_secret,
                timeout_ms=policy.webhook_timeout_ms,
                payload=payload,
            )

            await _record_delivery(
                db,
                org_id,
                item.match_id,
                fingerprint,
                channel="webhook",
                status="sent" if ok_wh else "failed",
                error=err,
                delivery_target=policy.webhook_url,
                http_status=http_status,
                response_snippet=snippet,
            )

    return MatchAlertRunResult(
        ok=True,
        evaluated_count=evaluated_count,
        triggered_count=len(triggered),
        sent_count=sent_count,
        failed_count=failed_count,
        dry_run=dry_run,
        items=triggered,
    )
