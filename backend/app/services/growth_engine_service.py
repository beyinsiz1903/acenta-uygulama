"""Growth Engine Service.

Agency acquisition funnel, lead management, referral system,
activation metrics, customer success, onboarding automation,
agency segmentation, supplier expansion, and growth KPIs.
"""
from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Any

logger = logging.getLogger("growth_engine")

def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()

def _uid() -> str:
    return str(uuid.uuid4())[:12]

# ============================================================
# PART 1 — AGENCY ACQUISITION FUNNEL
# ============================================================

FUNNEL_STAGES = [
    {"key": "lead_captured", "label": "Lead Captured", "order": 1},
    {"key": "demo_scheduled", "label": "Demo Scheduled", "order": 2},
    {"key": "demo_completed", "label": "Demo Completed", "order": 3},
    {"key": "pilot_started", "label": "Pilot Started", "order": 4},
    {"key": "first_search", "label": "First Search", "order": 5},
    {"key": "first_booking", "label": "First Booking", "order": 6},
    {"key": "activated", "label": "Activated Customer", "order": 7},
]

async def get_funnel_metrics(db) -> dict[str, Any]:
    """Get funnel stage counts and conversion rates."""
    pipeline = [
        {"$group": {"_id": "$stage", "count": {"$sum": 1}}},
    ]
    cursor = db["growth_leads"].aggregate(pipeline)
    stage_counts = {}
    async for doc in cursor:
        stage_counts[doc["_id"]] = doc["count"]

    stages = []
    prev_count = None
    for s in FUNNEL_STAGES:
        count = stage_counts.get(s["key"], 0)
        conversion = round((count / prev_count * 100), 1) if prev_count and prev_count > 0 else 100.0 if count > 0 else 0.0
        stages.append({**s, "count": count, "conversion_pct": conversion})
        if count > 0:
            prev_count = count

    total_leads = await db["growth_leads"].count_documents({})
    activated = stage_counts.get("activated", 0)
    overall_conversion = round((activated / total_leads * 100), 1) if total_leads > 0 else 0.0

    return {
        "stages": stages,
        "total_leads": total_leads,
        "activated": activated,
        "overall_conversion_pct": overall_conversion,
    }


# ============================================================
# PART 2 — LEAD & DEMO MANAGEMENT
# ============================================================

async def list_leads(db, stage: str | None = None, limit: int = 50) -> dict[str, Any]:
    query = {}
    if stage:
        query["stage"] = stage
    cursor = db["growth_leads"].find(query, {"_id": 0}).sort("created_at", -1).limit(limit)
    leads = []
    async for doc in cursor:
        leads.append(doc)
    return {"leads": leads, "count": len(leads)}


async def create_lead(db, data: dict) -> dict[str, Any]:
    lead = {
        "lead_id": _uid(),
        "company_name": data.get("company_name", ""),
        "contact_name": data.get("contact_name", ""),
        "contact_email": data.get("contact_email", ""),
        "contact_phone": data.get("contact_phone", ""),
        "source": data.get("source", "inbound"),
        "stage": "lead_captured",
        "assigned_to": data.get("assigned_to", ""),
        "notes": data.get("notes", ""),
        "created_at": _ts(),
        "updated_at": _ts(),
    }
    await db["growth_leads"].insert_one(lead)
    lead.pop("_id", None)
    return lead


async def update_lead_stage(db, lead_id: str, new_stage: str) -> dict[str, Any]:
    valid = [s["key"] for s in FUNNEL_STAGES] + ["churned"]
    if new_stage not in valid:
        return {"error": f"Invalid stage: {new_stage}"}
    result = await db["growth_leads"].update_one(
        {"lead_id": lead_id},
        {"$set": {"stage": new_stage, "updated_at": _ts()}},
    )
    if result.matched_count == 0:
        return {"error": "Lead not found"}
    return {"lead_id": lead_id, "stage": new_stage, "updated": True}


async def list_demos(db, status: str | None = None) -> dict[str, Any]:
    query = {}
    if status:
        query["status"] = status
    cursor = db["growth_demos"].find(query, {"_id": 0}).sort("scheduled_at", -1).limit(50)
    demos = []
    async for doc in cursor:
        demos.append(doc)
    return {"demos": demos, "count": len(demos)}


async def create_demo(db, data: dict) -> dict[str, Any]:
    demo = {
        "demo_id": _uid(),
        "lead_id": data.get("lead_id", ""),
        "company_name": data.get("company_name", ""),
        "contact_name": data.get("contact_name", ""),
        "scheduled_at": data.get("scheduled_at", ""),
        "status": "scheduled",
        "outcome": None,
        "follow_up_date": data.get("follow_up_date"),
        "notes": data.get("notes", ""),
        "created_at": _ts(),
    }
    await db["growth_demos"].insert_one(demo)
    demo.pop("_id", None)
    # Update lead stage
    if data.get("lead_id"):
        await db["growth_leads"].update_one(
            {"lead_id": data["lead_id"]},
            {"$set": {"stage": "demo_scheduled", "updated_at": _ts()}},
        )
    return demo


async def update_demo(db, demo_id: str, data: dict) -> dict[str, Any]:
    updates = {"updated_at": _ts()}
    if "status" in data:
        updates["status"] = data["status"]
    if "outcome" in data:
        updates["outcome"] = data["outcome"]
    if "notes" in data:
        updates["notes"] = data["notes"]
    result = await db["growth_demos"].update_one({"demo_id": demo_id}, {"$set": updates})
    if result.matched_count == 0:
        return {"error": "Demo not found"}
    # If completed, update lead stage
    if data.get("status") == "completed":
        demo = await db["growth_demos"].find_one({"demo_id": demo_id}, {"_id": 0})
        if demo and demo.get("lead_id"):
            await db["growth_leads"].update_one(
                {"lead_id": demo["lead_id"]},
                {"$set": {"stage": "demo_completed", "updated_at": _ts()}},
            )
    return {"demo_id": demo_id, "updated": True}


# ============================================================
# PART 3 — REFERRAL SYSTEM
# ============================================================

REFERRAL_REWARDS = {
    "registered": {"type": "discount", "amount": 10, "unit": "percent", "description": "10% ilk ay indirimi"},
    "activated": {"type": "credit", "amount": 50, "unit": "EUR", "description": "50 EUR komisyon kredisi"},
}

async def list_referrals(db, referrer_agency_id: str | None = None) -> dict[str, Any]:
    query = {}
    if referrer_agency_id:
        query["referrer_agency_id"] = referrer_agency_id
    cursor = db["growth_referrals"].find(query, {"_id": 0}).sort("created_at", -1).limit(50)
    referrals = []
    async for doc in cursor:
        referrals.append(doc)

    stats = {
        "total": len(referrals),
        "pending": sum(1 for r in referrals if r.get("status") == "pending"),
        "registered": sum(1 for r in referrals if r.get("status") == "registered"),
        "activated": sum(1 for r in referrals if r.get("status") == "activated"),
        "rewarded": sum(1 for r in referrals if r.get("status") == "rewarded"),
    }
    return {"referrals": referrals, "stats": stats, "reward_rules": REFERRAL_REWARDS}


async def create_referral(db, data: dict) -> dict[str, Any]:
    # Fraud check: same email already referred?
    existing = await db["growth_referrals"].find_one(
        {"referred_email": data.get("referred_email", "")}, {"_id": 0}
    )
    if existing:
        return {"error": "Bu email adresi zaten referans edilmis"}

    referral = {
        "referral_id": _uid(),
        "referrer_agency_id": data.get("referrer_agency_id", ""),
        "referrer_name": data.get("referrer_name", ""),
        "referred_company_name": data.get("referred_company_name", ""),
        "referred_contact_name": data.get("referred_contact_name", ""),
        "referred_email": data.get("referred_email", ""),
        "referred_phone": data.get("referred_phone", ""),
        "status": "pending",
        "reward_type": None,
        "reward_amount": None,
        "created_at": _ts(),
    }
    await db["growth_referrals"].insert_one(referral)
    referral.pop("_id", None)
    return referral


async def update_referral_status(db, referral_id: str, new_status: str) -> dict[str, Any]:
    valid = ["pending", "registered", "activated", "rewarded", "rejected"]
    if new_status not in valid:
        return {"error": f"Invalid status: {new_status}"}

    updates: dict[str, Any] = {"status": new_status, "updated_at": _ts()}
    # Apply reward
    reward = REFERRAL_REWARDS.get(new_status)
    if reward:
        updates["reward_type"] = reward["type"]
        updates["reward_amount"] = reward["amount"]

    result = await db["growth_referrals"].update_one({"referral_id": referral_id}, {"$set": updates})
    if result.matched_count == 0:
        return {"error": "Referral not found"}
    return {"referral_id": referral_id, "status": new_status, "updated": True}


# ============================================================
# PART 4 — ACTIVATION METRICS
# ============================================================

ACTIVATION_MILESTONES = [
    {"key": "credential_entered", "label": "Credential Entered", "weight": 20},
    {"key": "connection_tested", "label": "Connection Tested", "weight": 20},
    {"key": "first_search", "label": "First Search", "weight": 20},
    {"key": "first_booking", "label": "First Booking", "weight": 25},
    {"key": "first_revenue", "label": "First Revenue", "weight": 15},
]

async def get_agency_activation(db, agency_id: str) -> dict[str, Any]:
    """Get activation score and milestones for an agency."""
    cursor = db["growth_activation_events"].find(
        {"agency_id": agency_id}, {"_id": 0}
    ).sort("timestamp", 1)
    events = []
    achieved = set()
    async for doc in cursor:
        events.append(doc)
        achieved.add(doc["event_type"])

    milestones = []
    score = 0
    for m in ACTIVATION_MILESTONES:
        done = m["key"] in achieved
        milestones.append({**m, "completed": done})
        if done:
            score += m["weight"]

    status = "activated" if score >= 80 else "progressing" if score >= 40 else "new"
    return {
        "agency_id": agency_id,
        "activation_score": score,
        "status": status,
        "milestones": milestones,
        "events": events,
    }


async def record_activation_event(db, agency_id: str, event_type: str, details: str = "") -> dict[str, Any]:
    valid = [m["key"] for m in ACTIVATION_MILESTONES]
    if event_type not in valid:
        return {"error": f"Invalid event type: {event_type}"}
    existing = await db["growth_activation_events"].find_one(
        {"agency_id": agency_id, "event_type": event_type}, {"_id": 0}
    )
    if existing:
        return {"message": "Event already recorded", "event_type": event_type}

    event = {
        "agency_id": agency_id,
        "event_type": event_type,
        "details": details,
        "timestamp": _ts(),
    }
    await db["growth_activation_events"].insert_one(event)
    event.pop("_id", None)
    return event


async def list_all_activations(db) -> dict[str, Any]:
    """Get activation overview for all agencies."""
    pipeline = [
        {"$group": {
            "_id": "$agency_id",
            "events": {"$addToSet": "$event_type"},
            "event_count": {"$sum": 1},
            "latest_event": {"$max": "$timestamp"},
        }},
        {"$sort": {"latest_event": -1}},
    ]
    cursor = db["growth_activation_events"].aggregate(pipeline)
    agencies = []
    async for doc in cursor:
        achieved = set(doc["events"])
        score = sum(m["weight"] for m in ACTIVATION_MILESTONES if m["key"] in achieved)
        status = "activated" if score >= 80 else "progressing" if score >= 40 else "new"
        agencies.append({
            "agency_id": doc["_id"],
            "activation_score": score,
            "status": status,
            "milestones_completed": len(achieved),
            "milestones_total": len(ACTIVATION_MILESTONES),
            "latest_event": doc["latest_event"],
        })
    return {"agencies": agencies, "total": len(agencies)}


# ============================================================
# PART 5 — CUSTOMER SUCCESS DASHBOARD
# ============================================================

async def get_customer_success_dashboard(db) -> dict[str, Any]:
    """Build the customer success overview."""
    # Get all organizations
    orgs_cursor = db["organizations"].find({}, {"_id": 0, "org_id": 1, "name": 1, "created_at": 1})
    all_orgs = []
    async for org in orgs_cursor:
        all_orgs.append(org)

    # Get credential statuses
    cred_pipeline = [
        {"$group": {
            "_id": "$organization_id",
            "connected": {"$sum": {"$cond": [{"$eq": ["$status", "connected"]}, 1, 0]}},
            "failed": {"$sum": {"$cond": [{"$in": ["$status", ["auth_failed", "failed"]]}, 1, 0]}},
            "total": {"$sum": 1},
        }},
    ]
    cred_cursor = db["supplier_credentials"].aggregate(cred_pipeline)
    cred_map = {}
    async for doc in cred_cursor:
        cred_map[doc["_id"]] = doc

    # Get booking counts (last 30 days)
    thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    booking_pipeline = [
        {"$match": {"created_at": {"$gte": thirty_days_ago}}},
        {"$group": {"_id": "$organization_id", "bookings": {"$sum": 1}}},
    ]
    booking_cursor = db["bookings"].aggregate(booking_pipeline)
    booking_map = {}
    async for doc in booking_cursor:
        booking_map[doc["_id"]] = doc["bookings"]

    # Get activation scores
    activation_data = await list_all_activations(db)
    activation_map = {a["agency_id"]: a for a in activation_data["agencies"]}

    # Categorize agencies
    active, dormant, at_risk, failed_connections, zero_bookings = [], [], [], [], []

    for org in all_orgs:
        oid = org.get("org_id", "")
        creds = cred_map.get(oid, {})
        bookings_30d = booking_map.get(oid, 0)
        activation = activation_map.get(oid, {})

        agency_info = {
            "organization_id": oid,
            "name": org.get("name", oid),
            "connected_suppliers": creds.get("connected", 0),
            "failed_suppliers": creds.get("failed", 0),
            "bookings_30d": bookings_30d,
            "activation_score": activation.get("activation_score", 0),
        }

        if creds.get("failed", 0) > 0:
            failed_connections.append(agency_info)
        if bookings_30d == 0 and creds.get("total", 0) > 0:
            zero_bookings.append(agency_info)
        if creds.get("connected", 0) > 0 and bookings_30d > 0:
            active.append(agency_info)
        elif creds.get("total", 0) > 0 and bookings_30d == 0:
            dormant.append(agency_info)
        if activation.get("activation_score", 0) > 0 and activation.get("activation_score", 0) < 40:
            at_risk.append(agency_info)

    return {
        "summary": {
            "total_agencies": len(all_orgs),
            "active": len(active),
            "dormant": len(dormant),
            "at_risk": len(at_risk),
            "failed_connections": len(failed_connections),
            "zero_bookings": len(zero_bookings),
        },
        "active_agencies": active[:20],
        "dormant_agencies": dormant[:20],
        "at_risk_agencies": at_risk[:20],
        "failed_connection_agencies": failed_connections[:20],
        "zero_booking_agencies": zero_bookings[:20],
        "success_playbook": [
            {"trigger": "zero_bookings_7d", "action": "Acente ile iletisime gec, ilk booking rehberi gonder"},
            {"trigger": "failed_supplier_connection", "action": "Credential kontrol et, supplier destek ekibiyle iletisim kur"},
            {"trigger": "dormant_14d", "action": "Re-engagement email gonder, ozel teklif sun"},
            {"trigger": "at_risk_score_below_40", "action": "Customer success temsilcisi ata, onboarding tekrar baslat"},
        ],
    }


# ============================================================
# PART 6 — SUPPLIER EXPANSION MODEL
# ============================================================

async def list_supplier_requests(db) -> dict[str, Any]:
    cursor = db["growth_supplier_requests"].find({}, {"_id": 0}).sort("priority_score", -1)
    requests = []
    async for doc in cursor:
        requests.append(doc)
    return {"requests": requests, "total": len(requests)}


async def create_supplier_request(db, data: dict) -> dict[str, Any]:
    supplier_name = data.get("supplier_name", "")
    existing = await db["growth_supplier_requests"].find_one(
        {"supplier_name": supplier_name}, {"_id": 0}
    )
    if existing:
        # Increment demand
        await db["growth_supplier_requests"].update_one(
            {"supplier_name": supplier_name},
            {
                "$inc": {"demand_count": 1},
                "$addToSet": {"requested_by": data.get("requested_by", "")},
                "$set": {"updated_at": _ts()},
            },
        )
        return {"message": f"Demand increased for {supplier_name}", "supplier_name": supplier_name}

    doc = {
        "request_id": _uid(),
        "supplier_name": supplier_name,
        "supplier_type": data.get("supplier_type", "hotel"),
        "region": data.get("region", ""),
        "demand_count": 1,
        "requested_by": [data.get("requested_by", "")],
        "priority_score": data.get("priority_score", 50),
        "status": "requested",
        "notes": data.get("notes", ""),
        "created_at": _ts(),
        "updated_at": _ts(),
    }
    await db["growth_supplier_requests"].insert_one(doc)
    doc.pop("_id", None)
    return doc


async def update_supplier_request(db, request_id: str, data: dict) -> dict[str, Any]:
    updates = {"updated_at": _ts()}
    for key in ["status", "priority_score", "notes"]:
        if key in data:
            updates[key] = data[key]
    result = await db["growth_supplier_requests"].update_one(
        {"request_id": request_id}, {"$set": updates}
    )
    if result.matched_count == 0:
        return {"error": "Request not found"}
    return {"request_id": request_id, "updated": True}


# ============================================================
# PART 7 — GROWTH KPI DASHBOARD
# ============================================================

async def get_growth_kpis(db, days: int = 30) -> dict[str, Any]:
    """Comprehensive growth KPIs."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    # New leads
    new_leads = await db["growth_leads"].count_documents({"created_at": {"$gte": cutoff}})
    total_leads = await db["growth_leads"].count_documents({})

    # Activated agencies
    activated = await db["growth_leads"].count_documents({"stage": "activated"})

    # First booking rate
    first_booking_events = await db["growth_activation_events"].count_documents(
        {"event_type": "first_booking"}
    )
    total_agencies_with_events = len(
        await db["growth_activation_events"].distinct("agency_id")
    )
    first_booking_rate = round(
        (first_booking_events / total_agencies_with_events * 100), 1
    ) if total_agencies_with_events > 0 else 0.0

    # Referral stats
    total_referrals = await db["growth_referrals"].count_documents({})
    referral_conversions = await db["growth_referrals"].count_documents(
        {"status": {"$in": ["activated", "rewarded"]}}
    )

    # Supplier expansion
    pending_supplier_requests = await db["growth_supplier_requests"].count_documents(
        {"status": "requested"}
    )

    # Bookings
    total_bookings = await db["bookings"].count_documents({"created_at": {"$gte": cutoff}})

    # Stage distribution
    stage_pipeline = [
        {"$group": {"_id": "$stage", "count": {"$sum": 1}}},
    ]
    stage_cursor = db["growth_leads"].aggregate(stage_pipeline)
    stage_dist = {}
    async for doc in stage_cursor:
        stage_dist[doc["_id"]] = doc["count"]

    return {
        "period_days": days,
        "kpis": {
            "new_leads": new_leads,
            "total_leads": total_leads,
            "activated_agencies": activated,
            "first_booking_rate_pct": first_booking_rate,
            "total_referrals": total_referrals,
            "referral_conversions": referral_conversions,
            "referral_conversion_rate_pct": round(
                (referral_conversions / total_referrals * 100), 1
            ) if total_referrals > 0 else 0.0,
            "bookings_period": total_bookings,
            "pending_supplier_requests": pending_supplier_requests,
        },
        "funnel_distribution": stage_dist,
    }


# ============================================================
# PART 8 — ONBOARDING AUTOMATION
# ============================================================

ONBOARDING_CHECKLIST = [
    {"key": "welcome_email", "title": "Hosgeldiniz emaili gonderildi", "auto": True},
    {"key": "account_created", "title": "Platform hesabi olusturuldu", "auto": True},
    {"key": "first_login", "title": "Ilk giris yapildi", "auto": False},
    {"key": "supplier_credential_entered", "title": "Supplier credential girildi", "auto": False},
    {"key": "connection_test_passed", "title": "Supplier baglanti testi basarili", "auto": False},
    {"key": "first_search_completed", "title": "Ilk arama yapildi", "auto": False},
    {"key": "first_booking_created", "title": "Ilk rezervasyon olusturuldu", "auto": False},
    {"key": "training_completed", "title": "Platform egitimi tamamlandi", "auto": False},
]

ONBOARDING_TRIGGERS = [
    {"trigger": "no_login_3d", "action": "Giris hatirlatma emaili gonder", "delay_days": 3},
    {"trigger": "no_credential_7d", "action": "Supplier credential hatirlatmasi gonder", "delay_days": 7},
    {"trigger": "no_search_14d", "action": "Ilk arama rehberi emaili gonder", "delay_days": 14},
    {"trigger": "no_booking_21d", "action": "Inaktif acente uyarisi + ozel teklif", "delay_days": 21},
    {"trigger": "inactive_30d", "action": "Customer success temsilcisi ata", "delay_days": 30},
]

async def get_onboarding_status(db, agency_id: str) -> dict[str, Any]:
    cursor = db["growth_onboarding_tasks"].find(
        {"agency_id": agency_id}, {"_id": 0}
    )
    completed = {}
    async for doc in cursor:
        completed[doc["task_key"]] = {
            "completed": doc.get("completed", False),
            "completed_at": doc.get("completed_at"),
        }

    checklist = []
    done_count = 0
    for item in ONBOARDING_CHECKLIST:
        status = completed.get(item["key"], {"completed": False, "completed_at": None})
        done = status["completed"]
        if done:
            done_count += 1
        checklist.append({
            **item,
            "completed": done,
            "completed_at": status.get("completed_at"),
        })

    progress = round((done_count / len(ONBOARDING_CHECKLIST) * 100), 1) if ONBOARDING_CHECKLIST else 0
    return {
        "agency_id": agency_id,
        "checklist": checklist,
        "progress_pct": progress,
        "completed_count": done_count,
        "total_tasks": len(ONBOARDING_CHECKLIST),
        "triggers": ONBOARDING_TRIGGERS,
    }


async def complete_onboarding_task(db, agency_id: str, task_key: str) -> dict[str, Any]:
    valid = [item["key"] for item in ONBOARDING_CHECKLIST]
    if task_key not in valid:
        return {"error": f"Invalid task: {task_key}"}

    await db["growth_onboarding_tasks"].update_one(
        {"agency_id": agency_id, "task_key": task_key},
        {"$set": {"completed": True, "completed_at": _ts(), "agency_id": agency_id, "task_key": task_key}},
        upsert=True,
    )
    return {"agency_id": agency_id, "task_key": task_key, "completed": True}


# ============================================================
# PART 9 — AGENCY SEGMENTATION
# ============================================================

async def get_agency_segments(db) -> dict[str, Any]:
    """Segment agencies by volume, revenue, and growth potential."""
    # Get all organizations
    orgs_cursor = db["organizations"].find({}, {"_id": 0, "org_id": 1, "name": 1})
    orgs = []
    async for org in orgs_cursor:
        orgs.append(org)

    # Get booking counts
    booking_pipeline = [
        {"$group": {"_id": "$organization_id", "count": {"$sum": 1}}},
    ]
    bcursor = db["bookings"].aggregate(booking_pipeline)
    booking_map = {}
    async for doc in bcursor:
        booking_map[doc["_id"]] = doc["count"]

    # Get credential counts
    cred_pipeline = [
        {"$group": {
            "_id": "$organization_id",
            "connected": {"$sum": {"$cond": [{"$eq": ["$status", "connected"]}, 1, 0]}},
            "total": {"$sum": 1},
        }},
    ]
    ccursor = db["supplier_credentials"].aggregate(cred_pipeline)
    cred_map = {}
    async for doc in ccursor:
        cred_map[doc["_id"]] = doc

    # Activation data
    activation_data = await list_all_activations(db)
    act_map = {a["agency_id"]: a for a in activation_data["agencies"]}

    # Segment
    segments = {"enterprise": [], "growth": [], "starter": [], "inactive": []}
    for org in orgs:
        oid = org.get("org_id", "")
        bookings = booking_map.get(oid, 0)
        creds = cred_map.get(oid, {})
        activation = act_map.get(oid, {})

        agency = {
            "organization_id": oid,
            "name": org.get("name", oid),
            "bookings": bookings,
            "connected_suppliers": creds.get("connected", 0),
            "total_suppliers": creds.get("total", 0),
            "activation_score": activation.get("activation_score", 0),
        }

        if bookings >= 50:
            agency["segment"] = "enterprise"
            segments["enterprise"].append(agency)
        elif bookings >= 10:
            agency["segment"] = "growth"
            segments["growth"].append(agency)
        elif bookings >= 1 or creds.get("connected", 0) > 0:
            agency["segment"] = "starter"
            segments["starter"].append(agency)
        else:
            agency["segment"] = "inactive"
            segments["inactive"].append(agency)

    return {
        "segments": segments,
        "summary": {
            "enterprise": len(segments["enterprise"]),
            "growth": len(segments["growth"]),
            "starter": len(segments["starter"]),
            "inactive": len(segments["inactive"]),
        },
        "segmentation_rules": {
            "enterprise": "50+ bookings",
            "growth": "10-49 bookings",
            "starter": "1-9 bookings or connected suppliers",
            "inactive": "No bookings, no connections",
        },
    }


# ============================================================
# PART 10 — GROWTH ARCHITECTURE & RISKS
# ============================================================

async def get_growth_report(db) -> dict[str, Any]:
    """Full growth engine report."""
    kpis = await get_growth_kpis(db)
    funnel = await get_funnel_metrics(db)
    segments = await get_agency_segments(db)
    success = await get_customer_success_dashboard(db)
    supplier_requests = await list_supplier_requests(db)

    implementation_tasks = [
        {"priority": "P0", "task": "3 pilot acente icin gercek credential testi"},
        {"priority": "P0", "task": "Ilk gercek booking akisini tamamla"},
        {"priority": "P0", "task": "Lead capture formu canli yap"},
        {"priority": "P0", "task": "Onboarding email otomasyonunu aktif et"},
        {"priority": "P0", "task": "Customer success dashboard'u gunluk takibe al"},
        {"priority": "P1", "task": "Referral programini pilot acentelere ac"},
        {"priority": "P1", "task": "Demo takvim entegrasyonunu kur"},
        {"priority": "P1", "task": "Aktivasyon metriklerini otomatik event'lerle besle"},
        {"priority": "P1", "task": "Agency segmentasyonuna gore fiyatlandirma optimize et"},
        {"priority": "P1", "task": "Inaktif acente re-engagement kampanyasi baslat"},
        {"priority": "P1", "task": "Supplier expansion voting sistemini acentelere ac"},
        {"priority": "P1", "task": "Growth KPI dashboard'u haftalik rapor olarak gonder"},
        {"priority": "P1", "task": "Dormant acente uyari sistemini otomatiklestir"},
        {"priority": "P2", "task": "A/B test altyapisi kur (landing page, pricing)"},
        {"priority": "P2", "task": "Multi-channel lead capture (LinkedIn, Google Ads)"},
        {"priority": "P2", "task": "Agency NPS survey otomasyonu"},
        {"priority": "P2", "task": "Cohort analizi dashboard'u"},
        {"priority": "P2", "task": "Revenue forecasting modeli"},
        {"priority": "P2", "task": "Churn prediction modeli"},
        {"priority": "P2", "task": "White-label partner programi"},
        {"priority": "P2", "task": "API marketplace icin developer portal"},
        {"priority": "P2", "task": "Multi-region expansion plani"},
        {"priority": "P2", "task": "Enterprise SSO entegrasyonu"},
        {"priority": "P2", "task": "Otomatik supplier credential health check"},
        {"priority": "P2", "task": "Growth hacking metrikleri (viral coefficient)"},
    ]

    growth_risks = [
        {"risk": "Pilot acenteler gercek booking yapamadan churn edebilir", "severity": "high", "mitigation": "Ilk 48 saatte hands-on destek"},
        {"risk": "Supplier API'leri instabil olabilir", "severity": "high", "mitigation": "Fallback logic + supplier health monitoring"},
        {"risk": "Pricing modeli pazara uygun olmayabilir", "severity": "high", "mitigation": "Ilk 3 ay free tier agirlikli, data-driven pricing"},
        {"risk": "Lead-to-activation sureci cok uzun olabilir", "severity": "medium", "mitigation": "Onboarding otomasyonu + proaktif destek"},
        {"risk": "Referral sistemi kotu niyetli kullanilabilir", "severity": "medium", "mitigation": "Email dogrulama + manual approval"},
        {"risk": "Rakip platformlar daha dusuk komisyon sunabilir", "severity": "medium", "mitigation": "Deger odakli farklilasmak, multi-supplier avantaji"},
        {"risk": "Teknik destek talebi olceklenemeyebilir", "severity": "medium", "mitigation": "Self-service dokumantasyon + chatbot"},
        {"risk": "Supplier expansion talepleri karsilanamayabilir", "severity": "low", "mitigation": "Onceliklendirme + community voting"},
        {"risk": "Agency churn rate yuksek olabilir", "severity": "high", "mitigation": "Customer success program + early warning system"},
        {"risk": "Multi-tenant performans sorunlari", "severity": "medium", "mitigation": "Rate limiting + caching + monitoring"},
        {"risk": "KVKK/GDPR uyumluluk riskleri", "severity": "medium", "mitigation": "Data processing agreement + consent yonetimi"},
        {"risk": "Payment gateway entegrasyon gecikmeleri", "severity": "low", "mitigation": "Manuel faturalama ile baslayip otomasyona gec"},
        {"risk": "Seasonal demand dalgalanmalari", "severity": "medium", "mitigation": "Esnek fiyatlandirma + kampanya altyapisi"},
        {"risk": "Tek bolge bagimliligi", "severity": "low", "mitigation": "Multi-region roadmap"},
        {"risk": "Ekip buyume hizi platform buyumesinin gerisinde kalabilir", "severity": "high", "mitigation": "Otomasyon oncelikli yaklas + outsource plani"},
    ]

    total_score = 0
    dimension_scores = {
        "acquisition": min(10, (kpis["kpis"]["total_leads"] / 10) * 10) if kpis["kpis"]["total_leads"] > 0 else 2,
        "activation": min(10, (kpis["kpis"]["activated_agencies"] / 5) * 10) if kpis["kpis"]["activated_agencies"] > 0 else 2,
        "retention": 5,  # Needs real data over time
        "referral": min(10, (kpis["kpis"]["total_referrals"] / 5) * 10) if kpis["kpis"]["total_referrals"] > 0 else 2,
        "revenue": min(10, (kpis["kpis"]["bookings_period"] / 20) * 10) if kpis["kpis"]["bookings_period"] > 0 else 2,
        "supplier_ecosystem": 8,  # 4 suppliers integrated
        "platform_maturity": 9.5,
    }
    total_score = round(sum(dimension_scores.values()) / len(dimension_scores), 2)

    return {
        "growth_maturity_score": total_score,
        "dimension_scores": dimension_scores,
        "kpis": kpis["kpis"],
        "funnel_summary": {
            "total_leads": funnel["total_leads"],
            "activated": funnel["activated"],
            "overall_conversion_pct": funnel["overall_conversion_pct"],
        },
        "segments_summary": segments["summary"],
        "customer_success_summary": success["summary"],
        "supplier_requests_count": supplier_requests["total"],
        "implementation_tasks": implementation_tasks,
        "growth_risks": growth_risks,
    }
