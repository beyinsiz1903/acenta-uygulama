"""Enterprise Governance — Security Alerting Service (Part 8).

Detects suspicious activity, privilege escalation, and mass data access.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from app.domain.governance.models import SECURITY_ALERT_TYPES, SECURITY_SEVERITY

logger = logging.getLogger("governance.security_alerting")


async def create_security_alert(
    db: Any,
    org_id: str,
    *,
    alert_type: str,
    severity: str,
    title: str,
    description: str,
    actor_email: str = "",
    source_ip: str = "",
    affected_resource: str = "",
    evidence: Optional[dict] = None,
) -> dict:
    """Create a security alert."""
    now = datetime.now(timezone.utc)
    doc = {
        "_id": str(uuid.uuid4()),
        "organization_id": org_id,
        "alert_type": alert_type,
        "severity": severity,
        "title": title,
        "description": description,
        "actor_email": actor_email,
        "source_ip": source_ip,
        "affected_resource": affected_resource,
        "evidence": evidence or {},
        "status": "open",
        "created_at": now,
        "acknowledged_at": None,
        "acknowledged_by": None,
        "resolved_at": None,
        "resolved_by": None,
    }
    await db.gov_security_alerts.insert_one(doc)
    return {
        "alert_id": doc["_id"],
        "alert_type": alert_type,
        "severity": severity,
        "status": "open",
        "timestamp": now.isoformat(),
    }


async def detect_suspicious_login(
    db: Any, org_id: str, user_email: str, ip_address: str,
) -> Optional[dict]:
    """Detect suspicious login patterns."""
    now = datetime.now(timezone.utc)
    one_hour_ago = now - timedelta(hours=1)

    # Check for multiple failed logins
    failed_count = await db.gov_audit_log.count_documents({
        "organization_id": org_id,
        "actor_email": user_email,
        "action": "auth.login.failed",
        "timestamp": {"$gte": one_hour_ago},
    })

    if failed_count >= 5:
        return await create_security_alert(
            db, org_id,
            alert_type="brute_force_attempt",
            severity="high",
            title=f"Brute force attempt detected: {user_email}",
            description=f"{failed_count} failed login attempts in the last hour",
            actor_email=user_email,
            source_ip=ip_address,
            evidence={"failed_attempts": failed_count, "period": "1h"},
        )

    # Check for login from new IP
    recent_ips = await db.gov_audit_log.distinct(
        "ip_address",
        {
            "organization_id": org_id,
            "actor_email": user_email,
            "action": "auth.login.success",
            "timestamp": {"$gte": now - timedelta(days=30)},
        },
    )
    if ip_address and recent_ips and ip_address not in recent_ips:
        return await create_security_alert(
            db, org_id,
            alert_type="suspicious_login",
            severity="medium",
            title=f"Login from new IP: {user_email}",
            description=f"User logged in from {ip_address}, not seen in last 30 days",
            actor_email=user_email,
            source_ip=ip_address,
            evidence={"new_ip": ip_address, "known_ips": recent_ips[:5]},
        )
    return None


async def detect_privilege_escalation(
    db: Any, org_id: str, target_email: str, old_roles: list[str], new_roles: list[str], actor_email: str,
) -> Optional[dict]:
    """Detect potential privilege escalation."""
    from app.domain.governance.models import ROLE_HIERARCHY

    old_max = max((ROLE_HIERARCHY.get(r, 0) for r in old_roles), default=0)
    new_max = max((ROLE_HIERARCHY.get(r, 0) for r in new_roles), default=0)

    if new_max > old_max and new_max >= 80:  # Escalation to ops_admin or higher
        return await create_security_alert(
            db, org_id,
            alert_type="privilege_escalation",
            severity="high",
            title=f"Privilege escalation: {target_email}",
            description=f"Roles changed from {old_roles} to {new_roles} by {actor_email}",
            actor_email=actor_email,
            affected_resource=target_email,
            evidence={
                "target_user": target_email,
                "old_roles": old_roles,
                "new_roles": new_roles,
            },
        )
    return None


async def detect_mass_data_access(
    db: Any, org_id: str, actor_email: str, resource_type: str, access_count: int,
) -> Optional[dict]:
    """Detect mass data access patterns."""
    threshold = 500  # Configurable per org

    if access_count >= threshold:
        return await create_security_alert(
            db, org_id,
            alert_type="mass_data_access",
            severity="high",
            title=f"Mass data access: {actor_email}",
            description=f"User accessed {access_count} {resource_type} records in a single request",
            actor_email=actor_email,
            affected_resource=resource_type,
            evidence={
                "access_count": access_count,
                "threshold": threshold,
                "resource_type": resource_type,
            },
        )
    return None


async def list_security_alerts(
    db: Any,
    org_id: str,
    *,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    alert_type: Optional[str] = None,
    limit: int = 50,
    skip: int = 0,
) -> dict:
    """List security alerts with filters."""
    query: dict[str, Any] = {"organization_id": org_id}
    if status:
        query["status"] = status
    if severity:
        query["severity"] = severity
    if alert_type:
        query["alert_type"] = alert_type

    total = await db.gov_security_alerts.count_documents(query)
    cursor = db.gov_security_alerts.find(query).sort("created_at", -1).skip(skip).limit(limit)
    docs = []
    async for doc in cursor:
        doc["alert_id"] = doc.pop("_id")
        docs.append(doc)

    return {"total": total, "items": docs, "limit": limit, "skip": skip}


async def acknowledge_security_alert(
    db: Any, org_id: str, alert_id: str, actor_email: str,
) -> dict:
    """Acknowledge a security alert."""
    now = datetime.now(timezone.utc)
    result = await db.gov_security_alerts.update_one(
        {"_id": alert_id, "organization_id": org_id, "status": "open"},
        {"$set": {
            "status": "acknowledged",
            "acknowledged_at": now,
            "acknowledged_by": actor_email,
        }},
    )
    return {
        "alert_id": alert_id,
        "acknowledged": result.modified_count > 0,
        "timestamp": now.isoformat(),
    }


async def resolve_security_alert(
    db: Any, org_id: str, alert_id: str, actor_email: str, resolution: str = "",
) -> dict:
    """Resolve a security alert."""
    now = datetime.now(timezone.utc)
    result = await db.gov_security_alerts.update_one(
        {"_id": alert_id, "organization_id": org_id},
        {"$set": {
            "status": "resolved",
            "resolved_at": now,
            "resolved_by": actor_email,
            "resolution": resolution,
        }},
    )
    return {
        "alert_id": alert_id,
        "resolved": result.modified_count > 0,
        "timestamp": now.isoformat(),
    }


async def get_security_dashboard(db: Any, org_id: str) -> dict:
    """Get security alerting dashboard summary."""
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)

    pipeline = [
        {"$match": {"organization_id": org_id, "created_at": {"$gte": seven_days_ago}}},
        {"$group": {
            "_id": {"severity": "$severity", "status": "$status"},
            "count": {"$sum": 1},
        }},
    ]
    results = await db.gov_security_alerts.aggregate(pipeline).to_list(50)

    open_critical = 0
    open_high = 0
    total_open = 0
    total_week = sum(r["count"] for r in results)

    for r in results:
        if r["_id"]["status"] == "open":
            total_open += r["count"]
            if r["_id"]["severity"] == "critical":
                open_critical += r["count"]
            elif r["_id"]["severity"] == "high":
                open_high += r["count"]

    return {
        "period": "7d",
        "total_alerts_this_week": total_week,
        "open_alerts": total_open,
        "open_critical": open_critical,
        "open_high": open_high,
        "alert_types": SECURITY_ALERT_TYPES,
        "severity_levels": SECURITY_SEVERITY,
        "timestamp": now.isoformat(),
    }
