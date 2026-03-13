"""P10 — Reliability Roadmap & Maturity Score.

Top 20 reliability improvements, risk analysis, and maturity scoring.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.domain.reliability.models import MATURITY_DIMENSIONS

logger = logging.getLogger("reliability.roadmap")

RELIABILITY_IMPROVEMENTS = [
    # (rank, title, category, risk, effort, impact, description)
    (1, "Real supplier adapter integration (Paximum, Amadeus)", "resilience", "critical", "high", "critical",
     "Replace mock adapters with real supplier APIs. Without this, the entire resilience layer operates on synthetic data."),
    (2, "Circuit breaker per adapter method", "resilience", "critical", "medium", "high",
     "Implement per-method circuit breakers (search vs confirm) to avoid blanket supplier disabling."),
    (3, "Idempotency enforcement on payment endpoints", "idempotency", "critical", "medium", "critical",
     "All payment mutations must be idempotent. Duplicate charges are a regulatory and financial risk."),
    (4, "DLQ consumer workers (Celery)", "retry_dlq", "high", "medium", "high",
     "Dead-letter queue entries must be processed by dedicated workers. Currently they only pile up."),
    (5, "Contract validation on every supplier response", "contract_safety", "high", "medium", "high",
     "Every supplier response must be validated before entering the booking pipeline."),
    (6, "Automated incident detection scheduler", "incident_response", "high", "medium", "high",
     "A Celery beat task should run detect_supplier_issues every 5 minutes."),
    (7, "Supplier sandbox for staging/QA", "sandbox", "medium", "low", "medium",
     "Enable sandbox mode in staging environments to test adapter changes without affecting production."),
    (8, "Prometheus metrics exporter", "observability", "high", "medium", "high",
     "Export integration metrics in Prometheus exposition format for Grafana dashboards."),
    (9, "Rate limiter with Redis backing", "resilience", "medium", "medium", "medium",
     "Current in-memory rate limiter does not survive restarts. Move to Redis-backed distributed rate limiting."),
    (10, "Request deduplication cache with TTL", "idempotency", "medium", "low", "medium",
     "Short-window dedup to prevent user double-clicks from creating duplicate bookings."),
    (11, "Schema drift alerting", "contract_safety", "medium", "low", "medium",
     "Automatically alert when a supplier changes their response schema (detected via hash drift)."),
    (12, "Adapter versioning with rollback", "versioning", "medium", "medium", "medium",
     "Support running multiple adapter versions and instantly rolling back to a previous version."),
    (13, "DLQ overflow alerting", "retry_dlq", "high", "low", "medium",
     "Alert when DLQ size exceeds threshold — indicates systemic failures."),
    (14, "Supplier SLA tracking", "observability", "medium", "medium", "medium",
     "Track supplier uptime against SLA agreements and auto-generate SLA breach reports."),
    (15, "Graceful degradation with cached results", "resilience", "medium", "high", "medium",
     "When a supplier is down, serve cached search results with clear staleness indicators."),
    (16, "Incident auto-escalation", "incident_response", "medium", "low", "medium",
     "Unresolved incidents should auto-escalate after configurable thresholds."),
    (17, "Integration health Slack/webhook notifications", "incident_response", "medium", "low", "medium",
     "Push notifications to Slack/webhook when supplier status changes."),
    (18, "Adapter performance regression tests", "observability", "low", "medium", "medium",
     "Automated tests that detect adapter performance degradation in CI/CD."),
    (19, "Multi-region supplier failover", "resilience", "medium", "high", "high",
     "Support failover to supplier endpoints in different regions for geo-redundancy."),
    (20, "ML-based anomaly detection on metrics", "observability", "low", "high", "high",
     "Use statistical/ML methods to detect anomalous patterns in supplier metrics."),
]


async def get_reliability_roadmap(db, org_id: str) -> dict[str, Any]:
    """Generate the full reliability roadmap with maturity score."""
    maturity = await compute_maturity_score(db, org_id)

    improvements = []
    for rank, title, category, risk, effort, impact, desc in RELIABILITY_IMPROVEMENTS:
        improvements.append({
            "rank": rank,
            "title": title,
            "category": category,
            "risk_level": risk,
            "effort": effort,
            "impact": impact,
            "description": desc,
        })

    risk_analysis = _compute_risk_analysis(maturity)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "maturity_score": maturity,
        "improvements": improvements,
        "risk_analysis": risk_analysis,
    }


async def compute_maturity_score(db, org_id: str) -> dict[str, Any]:
    """Compute platform reliability maturity score (0-100)."""

    scores: dict[str, float] = {}

    # Resilience: Do we have resilience config?
    resilience_cfg = await db.rel_resilience_config.find_one({"organization_id": org_id})
    has_overrides = bool(resilience_cfg and resilience_cfg.get("supplier_overrides"))
    events = await db.rel_resilience_events.count_documents({"organization_id": org_id})
    scores["resilience"] = min(100, (40 if resilience_cfg else 0) + (30 if has_overrides else 0) + min(30, events * 0.5))

    # Observability: Metrics collection
    metrics = await db.rel_metrics.count_documents({"organization_id": org_id})
    scores["observability"] = min(100, metrics * 0.3)

    # Idempotency: Keys stored
    idem = await db.rel_idempotency_store.count_documents({"organization_id": org_id})
    scores["idempotency"] = min(100, (50 if idem > 0 else 0) + min(50, idem * 2))

    # Contract safety: Contracts defined
    contracts = await db.rel_contract_schemas.count_documents({"organization_id": org_id})
    violations = await db.rel_contract_violations.count_documents({"organization_id": org_id})
    scores["contract_safety"] = min(100, (50 if contracts > 0 else 0) + max(0, 50 - violations * 5))

    # Incident response: Resolved incidents
    total_incidents = await db.rel_incidents.count_documents({"organization_id": org_id})
    resolved = await db.rel_incidents.count_documents({"organization_id": org_id, "status": "resolved"})
    if total_incidents > 0:
        scores["incident_response"] = min(100, 30 + (resolved / total_incidents) * 70)
    else:
        scores["incident_response"] = 30  # no incidents yet = baseline

    # Retry/DLQ
    dlq_pending = await db.rel_dead_letter_queue.count_documents({"organization_id": org_id, "status": "pending"})
    scores["retry_dlq"] = max(0, 100 - dlq_pending * 10)

    # Versioning
    versions = await db.rel_api_versions.count_documents({"organization_id": org_id})
    scores["versioning"] = min(100, versions * 20)

    # Sandbox
    sandbox = await db.rel_sandbox_config.find_one({"organization_id": org_id})
    scores["sandbox"] = 100 if sandbox and sandbox.get("enabled") else 20

    # Weighted composite
    composite = sum(scores.get(dim, 0) * weight for dim, weight in MATURITY_DIMENSIONS.items())

    # Grade
    if composite >= 80:
        grade = "A"
    elif composite >= 65:
        grade = "B"
    elif composite >= 50:
        grade = "C"
    elif composite >= 35:
        grade = "D"
    else:
        grade = "F"

    return {
        "overall_score": round(composite, 1),
        "grade": grade,
        "dimensions": {dim: round(scores.get(dim, 0), 1) for dim in MATURITY_DIMENSIONS},
        "weights": MATURITY_DIMENSIONS,
    }


def _compute_risk_analysis(maturity: dict) -> dict[str, Any]:
    """Compute risk analysis based on maturity scores."""
    dims = maturity.get("dimensions", {})
    risks = []

    if dims.get("resilience", 0) < 50:
        risks.append({"level": "critical", "area": "resilience",
                       "description": "Supplier API resilience is below acceptable threshold. Outages will cascade."})
    if dims.get("idempotency", 0) < 50:
        risks.append({"level": "critical", "area": "idempotency",
                       "description": "Idempotency not enforced. Duplicate bookings/payments are likely."})
    if dims.get("contract_safety", 0) < 50:
        risks.append({"level": "high", "area": "contract_safety",
                       "description": "Contract validation gaps. Supplier schema changes can break booking pipeline silently."})
    if dims.get("incident_response", 0) < 50:
        risks.append({"level": "high", "area": "incident_response",
                       "description": "Incident response immaturity. Supplier outages may go undetected."})
    if dims.get("observability", 0) < 40:
        risks.append({"level": "medium", "area": "observability",
                       "description": "Limited integration metrics. Blind to supplier performance trends."})
    if dims.get("retry_dlq", 0) < 50:
        risks.append({"level": "medium", "area": "retry_dlq",
                       "description": "DLQ overflow risk. Failed operations may be permanently lost."})
    if dims.get("versioning", 0) < 30:
        risks.append({"level": "low", "area": "versioning",
                       "description": "No version management. Supplier API upgrades require manual coordination."})
    if dims.get("sandbox", 0) < 30:
        risks.append({"level": "low", "area": "sandbox",
                       "description": "No sandbox environment. Testing supplier changes requires production traffic."})

    if not risks:
        risks.append({"level": "info", "area": "general", "description": "All reliability dimensions above threshold."})

    return {
        "total_risks": len(risks),
        "critical": sum(1 for r in risks if r["level"] == "critical"),
        "high": sum(1 for r in risks if r["level"] == "high"),
        "medium": sum(1 for r in risks if r["level"] == "medium"),
        "low": sum(1 for r in risks if r["level"] == "low"),
        "risks": risks,
    }
