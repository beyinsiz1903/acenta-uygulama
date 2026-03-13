"""PART 7 — Incident Response Playbooks.

Operational playbooks for:
- Supplier outage
- Queue backlog
- Payment failure

Each playbook: detection, triage, escalation, resolution, post-mortem.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("hardening.incident_playbooks")


PLAYBOOKS = {
    "supplier_outage": {
        "name": "Supplier Outage Playbook",
        "severity": "P1 — Critical",
        "detection": {
            "signals": [
                "Circuit breaker opens for a supplier",
                "Supplier error rate > 50% for 5 minutes",
                "Supplier latency P95 > 15 seconds",
                "No successful responses in 10 minutes",
            ],
            "alert_channels": ["Slack #ops-alerts", "PagerDuty", "Email to on-call"],
            "automated_actions": [
                "Circuit breaker activates (blocks further requests)",
                "Traffic redirected to failover supplier (if available)",
                "Incident automatically created in ops_incidents collection",
            ],
        },
        "triage": {
            "steps": [
                "1. Check supplier status page for known outages",
                "2. Verify API credentials haven't expired",
                "3. Check rate limit counters — are we being throttled?",
                "4. Test with a manual sandbox request",
                "5. Check network connectivity from pod to supplier endpoint",
                "6. Review recent deployment changes",
            ],
            "owner": "Ops Admin",
            "sla_minutes": 15,
        },
        "escalation": {
            "tiers": [
                {"tier": "L1", "role": "On-call Ops", "sla_minutes": 5, "actions": ["Acknowledge alert", "Initial triage"]},
                {"tier": "L2", "role": "Senior Ops Engineer", "sla_minutes": 15, "actions": ["Deep investigation", "Contact supplier"]},
                {"tier": "L3", "role": "Platform Architect", "sla_minutes": 30, "actions": ["Architecture decisions", "Emergency patches"]},
            ],
        },
        "resolution": {
            "actions": [
                "Wait for supplier recovery and verify health",
                "Gradually re-enable traffic (canary → full)",
                "Process DLQ messages for failed bookings",
                "Notify affected agencies about service restoration",
                "Update supplier status in the reliability dashboard",
            ],
        },
        "post_mortem": {
            "template": [
                "Impact: Number of affected bookings/searches",
                "Duration: Time from detection to resolution",
                "Root Cause: Why did the outage happen?",
                "Detection: How was it detected? Could we detect faster?",
                "Response: Was the playbook followed? What worked?",
                "Prevention: What changes prevent recurrence?",
            ],
        },
    },
    "queue_backlog": {
        "name": "Queue Backlog Playbook",
        "severity": "P2 — High",
        "detection": {
            "signals": [
                "Queue depth > 100 for critical queue",
                "Task processing rate drops below 50% of normal",
                "DLQ messages growing steadily",
                "Task latency P95 > 60 seconds",
            ],
            "alert_channels": ["Slack #ops-alerts", "Dashboard notification"],
            "automated_actions": [
                "Auto-scale workers (if configured)",
                "Alert on-call engineer",
                "Pause non-critical queues to free resources",
            ],
        },
        "triage": {
            "steps": [
                "1. Check Redis health and memory usage",
                "2. Verify worker processes are running",
                "3. Check for poison messages (tasks that always fail)",
                "4. Review worker logs for errors",
                "5. Check if a specific task type is causing the backlog",
                "6. Verify broker connectivity",
            ],
            "owner": "Ops Admin",
            "sla_minutes": 10,
        },
        "escalation": {
            "tiers": [
                {"tier": "L1", "role": "On-call Ops", "sla_minutes": 5, "actions": ["Check dashboard", "Scale workers"]},
                {"tier": "L2", "role": "Backend Engineer", "sla_minutes": 15, "actions": ["Debug failing tasks", "Fix poison messages"]},
            ],
        },
        "resolution": {
            "actions": [
                "Scale workers to process backlog",
                "Move poison messages to DLQ",
                "Clear backlog and verify processing rate",
                "Reset auto-scaling thresholds if needed",
            ],
        },
        "post_mortem": {
            "template": [
                "Impact: Delayed notifications/vouchers/payments",
                "Duration: Time from backlog start to clear",
                "Root Cause: Why did the backlog form?",
                "Prevention: Auto-scaling adjustments needed?",
            ],
        },
    },
    "payment_failure": {
        "name": "Payment Failure Playbook",
        "severity": "P1 — Critical",
        "detection": {
            "signals": [
                "Payment success rate drops below 95%",
                "Stripe webhook delivery failures",
                "Payment timeout rate > 5%",
                "Refund processing failures",
            ],
            "alert_channels": ["Slack #finance-alerts", "PagerDuty", "Email to finance team"],
            "automated_actions": [
                "Pause auto-confirm for new bookings",
                "Log all failed payment attempts with full context",
                "Alert finance admin immediately",
            ],
        },
        "triage": {
            "steps": [
                "1. Check Stripe Dashboard for service status",
                "2. Verify Stripe API key is valid",
                "3. Check webhook endpoint health",
                "4. Review payment error codes in logs",
                "5. Check if specific payment methods are failing",
                "6. Verify currency conversion is working",
            ],
            "owner": "Finance Admin",
            "sla_minutes": 10,
        },
        "escalation": {
            "tiers": [
                {"tier": "L1", "role": "Finance Admin", "sla_minutes": 5, "actions": ["Acknowledge", "Check Stripe dashboard"]},
                {"tier": "L2", "role": "Backend Engineer", "sla_minutes": 10, "actions": ["Debug webhook", "Check API errors"]},
                {"tier": "L3", "role": "Stripe Support", "sla_minutes": 30, "actions": ["Contact Stripe", "Emergency escalation"]},
            ],
        },
        "resolution": {
            "actions": [
                "Fix root cause (API key, webhook, network)",
                "Retry failed payments in batch",
                "Reconcile payment records with Stripe",
                "Notify affected agencies about payment status",
                "Resume auto-confirm for bookings",
            ],
        },
        "post_mortem": {
            "template": [
                "Impact: Revenue affected, bookings delayed",
                "Duration: Time from first failure to resolution",
                "Root Cause: Technical failure details",
                "Financial Impact: Total failed amount, recovered amount",
                "Prevention: Monitoring improvements",
            ],
        },
    },
}


async def get_incident_playbooks() -> dict:
    """Get all incident response playbooks."""
    return {
        "playbooks": PLAYBOOKS,
        "total": len(PLAYBOOKS),
        "severities": {k: v["severity"] for k, v in PLAYBOOKS.items()},
    }


async def simulate_incident_response(db, incident_type: str) -> dict:
    """Simulate an incident response for testing."""
    playbook = PLAYBOOKS.get(incident_type)
    if not playbook:
        return {"error": f"Unknown incident type: {incident_type}"}

    simulation = {
        "incident_type": incident_type,
        "playbook_name": playbook["name"],
        "severity": playbook["severity"],
        "simulation_steps": [],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Simulate detection
    simulation["simulation_steps"].append({
        "phase": "detection",
        "signals_checked": len(playbook["detection"]["signals"]),
        "automated_actions": len(playbook["detection"]["automated_actions"]),
        "status": "triggered",
    })

    # Simulate triage
    simulation["simulation_steps"].append({
        "phase": "triage",
        "steps": len(playbook["triage"]["steps"]),
        "owner": playbook["triage"]["owner"],
        "sla_minutes": playbook["triage"]["sla_minutes"],
        "status": "completed",
    })

    # Simulate escalation
    for tier in playbook["escalation"]["tiers"]:
        simulation["simulation_steps"].append({
            "phase": "escalation",
            "tier": tier["tier"],
            "role": tier["role"],
            "sla_minutes": tier["sla_minutes"],
            "status": "notified",
        })

    simulation["total_steps"] = len(simulation["simulation_steps"])
    simulation["estimated_resolution_minutes"] = sum(
        t["sla_minutes"] for t in playbook["escalation"]["tiers"]
    )

    await db.incident_simulations.insert_one({**simulation})
    return simulation
