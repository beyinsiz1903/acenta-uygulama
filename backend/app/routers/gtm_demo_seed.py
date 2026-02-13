from __future__ import annotations

import uuid
import random
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.services.audit import write_audit_log

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/demo", tags=["gtm-demo-seed"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ─── Rate limiting ─────────────────────────────────────────────────
SEED_RATE: dict = {}
SEED_LIMIT = 3  # max 3 seeds per minute per user


def _check_seed_rate(user_id: str) -> None:
    from app.errors import AppError
    now = _now()
    entry = SEED_RATE.get(user_id)
    if entry:
        count, window_start = entry
        if (now - window_start).total_seconds() < 60:
            if count >= SEED_LIMIT:
                raise AppError(429, "rate_limited", "Too many seed requests. Please wait.", {})
            SEED_RATE[user_id] = (count + 1, window_start)
        else:
            SEED_RATE[user_id] = (1, now)
    else:
        SEED_RATE[user_id] = (1, now)


# ─── Schemas ───────────────────────────────────────────────────────
class DemoSeedRequest(BaseModel):
    mode: str = Field(default="light", pattern="^(light|full)$")
    with_finance: bool = True
    with_crm: bool = True
    force: bool = False


class DemoSeedResponse(BaseModel):
    ok: bool
    already_seeded: bool = False
    counts: dict = {}


# ─── Helper: resolve tenant_id ─────────────────────────────────────
async def _resolve_tenant_id(user: dict) -> str:
    tenant_id = user.get("tenant_id")
    org_id = user.get("organization_id")
    if not tenant_id:
        db = await get_db()
        tenant = await db.tenants.find_one({"organization_id": org_id})
        if tenant:
            tenant_id = str(tenant["_id"])
    if not tenant_id:
        # Auto-create tenant for the organization if none exists
        import uuid as _uuid
        db = await get_db()
        tenant_id = str(_uuid.uuid4())
        await db.tenants.insert_one({
            "_id": tenant_id,
            "organization_id": org_id,
            "name": f"Tenant for {org_id}",
            "status": "active",
            "created_at": _now(),
        })
        logger.info("Auto-created tenant %s for org %s", tenant_id, org_id)
    return tenant_id


# ─── Demo data generators ──────────────────────────────────────────
def _gen_products(tenant_id: str, org_id: str, count: int = 3) -> list:
    names = ["Standart Oda", "Deluxe Suite", "Aile Odası", "Ekonomik Oda", "Penthouse"]
    products = []
    for i in range(count):
        products.append({
            "_id": f"demo_product_{i}_{uuid.uuid4().hex[:8]}",
            "organization_id": org_id,
            "tenant_id": tenant_id,
            "title": names[i % len(names)],
            "type": "room",
            "price": random.choice([500, 750, 1000, 1500, 2000]),
            "currency": "TRY",
            "status": "active",
            "source": "demo_seed",
            "created_at": _now(),
            "updated_at": _now(),
        })
    return products


def _gen_customers(tenant_id: str, org_id: str, count: int = 5) -> list:
    first_names = ["Ahmet", "Ayşe", "Mehmet", "Fatma", "Ali", "Zeynep", "Can", "Elif"]
    last_names = ["Yılmaz", "Kaya", "Demir", "Çelik", "Şahin", "Aydın", "Arslan", "Koç"]
    customers = []
    for i in range(count):
        first = random.choice(first_names)
        last = random.choice(last_names)
        customers.append({
            "id": f"demo_cust_{i}_{uuid.uuid4().hex[:8]}",
            "organization_id": org_id,
            "tenant_id": tenant_id,
            "type": random.choice(["individual", "corporate"]),
            "name": f"{first} {last}",
            "contacts": [
                {"type": "email", "value": f"{first.lower()}.{last.lower()}@example.com", "is_primary": True},
                {"type": "phone", "value": f"+90 5{random.randint(300000000, 599999999)}", "is_primary": False},
            ],
            "tags": random.sample(["VIP", "regular", "corporate", "new"], k=random.randint(0, 2)),
            "source": "demo_seed",
            "created_at": _now(),
            "updated_at": _now(),
        })
    return customers


def _gen_reservations(tenant_id: str, org_id: str, customer_ids: list, count: int = 10) -> list:
    statuses = ["pending"] * 4 + ["approved"] * 3 + ["paid"] * 3
    reservations = []
    for i in range(count):
        days_ahead = random.randint(3, 60)
        checkin = _now() + timedelta(days=days_ahead)
        checkout = checkin + timedelta(days=random.randint(1, 7))
        total = random.randint(1000, 10000)
        reservations.append({
            "_id": f"demo_res_{i}_{uuid.uuid4().hex[:8]}",
            "organization_id": org_id,
            "tenant_id": tenant_id,
            "customer_id": random.choice(customer_ids) if customer_ids else None,
            "status": statuses[i % len(statuses)],
            "checkin": checkin,
            "checkout": checkout,
            "total": total,
            "currency": "TRY",
            "guests": random.randint(1, 4),
            "source": "demo_seed",
            "created_at": _now() - timedelta(days=random.randint(0, 14)),
            "updated_at": _now(),
        })
    return reservations


def _gen_webpos_payments(tenant_id: str, org_id: str, count: int = 5) -> tuple:
    payments = []
    ledger_entries = []
    for i in range(count):
        pay_id = f"demo_pay_{i}_{uuid.uuid4().hex[:8]}"
        amount = random.choice([500, 1000, 1500, 2000, 3000])
        payments.append({
            "_id": pay_id,
            "tenant_id": tenant_id,
            "organization_id": org_id,
            "amount": amount,
            "currency": "TRY",
            "method": random.choice(["cash", "credit_card", "bank_transfer"]),
            "reference": f"DEMO-PAY-{i}",
            "note": "Demo ödeme",
            "status": "completed",
            "source": "demo_seed",
            "created_at": _now() - timedelta(days=random.randint(0, 14)),
        })
        ledger_entries.append({
            "_id": f"demo_ledger_{i}_{uuid.uuid4().hex[:8]}",
            "tenant_id": tenant_id,
            "organization_id": org_id,
            "type": "debit",
            "amount": amount,
            "currency": "TRY",
            "reference_type": "payment",
            "reference_id": pay_id,
            "description": "Demo ödeme kaydı",
            "source": "demo_seed",
            "created_at": _now() - timedelta(days=random.randint(0, 14)),
        })
    # Add 1 refund
    refund_id = f"demo_refund_0_{uuid.uuid4().hex[:8]}"
    payments.append({
        "_id": refund_id,
        "tenant_id": tenant_id,
        "organization_id": org_id,
        "amount": 500,
        "currency": "TRY",
        "method": "cash",
        "reference": "DEMO-REFUND-0",
        "note": "Demo iade",
        "status": "refunded",
        "source": "demo_seed",
        "created_at": _now() - timedelta(days=1),
    })
    ledger_entries.append({
        "_id": f"demo_ledger_refund_0_{uuid.uuid4().hex[:8]}",
        "tenant_id": tenant_id,
        "organization_id": org_id,
        "type": "credit",
        "amount": 500,
        "currency": "TRY",
        "reference_type": "refund",
        "reference_id": refund_id,
        "description": "Demo iade kaydı",
        "source": "demo_seed",
        "created_at": _now() - timedelta(days=1),
    })
    return payments, ledger_entries


def _gen_cases(tenant_id: str, org_id: str, count: int = 3) -> list:
    case_titles = ["Oda temizlik şikayeti", "Fatura sorunu", "Erken check-out talebi", "Oda değişikliği", "Gürültü şikayeti"]
    case_statuses = ["open", "in_progress", "open"]
    cases = []
    for i in range(count):
        case_id = f"demo_case_{i}_{uuid.uuid4().hex[:8]}"
        cases.append({
            "_id": case_id,
            "case_id": case_id,
            "organization_id": org_id,
            "tenant_id": tenant_id,
            "title": case_titles[i % len(case_titles)],
            "status": case_statuses[i % len(case_statuses)],
            "priority": random.choice(["low", "medium", "high"]),
            "source": "demo_seed",
            "created_at": _now() - timedelta(days=random.randint(0, 7)),
            "updated_at": _now(),
        })
    return cases


def _gen_crm_deals(tenant_id: str, org_id: str, customer_ids: list, user_id: str, count: int = 5) -> list:
    stages = ["lead", "contacted", "proposal", "won", "lost"]
    titles = ["Yaz sezonu grup rezervasyonu", "Kurumsal toplantı paketi", "Düğün organizasyonu",
             "Hafta sonu konaklama", "Balayi paketi", "Konferans rezervasyonu"]
    deals = []
    for i in range(count):
        stage = stages[i % len(stages)]
        status = "won" if stage == "won" else ("lost" if stage == "lost" else "open")
        deals.append({
            "id": f"demo_deal_{i}_{uuid.uuid4().hex[:8]}",
            "organization_id": org_id,
            "tenant_id": tenant_id,
            "customer_id": random.choice(customer_ids) if customer_ids else None,
            "title": titles[i % len(titles)],
            "amount": random.choice([5000, 10000, 15000, 25000, 50000]),
            "currency": "TRY",
            "stage": stage,
            "status": status,
            "owner_user_id": user_id,
            "next_action_at": _now() + timedelta(days=random.randint(1, 14)),
            "source": "demo_seed",
            "created_at": _now() - timedelta(days=random.randint(0, 30)),
            "updated_at": _now(),
        })
    return deals


def _gen_crm_tasks(tenant_id: str, org_id: str, deal_ids: list, customer_ids: list, user_id: str, count: int = 10) -> list:
    task_titles = ["Müşteriye teklif gönder", "Fiyat güncelle", "Oda durumu kontrol et",
                   "Depozito takibi", "Check-in hazırlığı", "Müşteri geri bildirimi al",
                   "Sözleşme gönder", "Ödeme hatırlatması", "Rezervasyon onayla", "İade işlemi"]
    tasks = []
    for i in range(count):
        tasks.append({
            "id": f"demo_task_{i}_{uuid.uuid4().hex[:8]}",
            "organization_id": org_id,
            "tenant_id": tenant_id,
            "deal_id": random.choice(deal_ids) if deal_ids and random.random() > 0.3 else None,
            "customer_id": random.choice(customer_ids) if customer_ids and random.random() > 0.3 else None,
            "title": task_titles[i % len(task_titles)],
            "due_at": _now() + timedelta(days=random.randint(-3, 14)),
            "due_date": _now() + timedelta(days=random.randint(-3, 14)),
            "status": "open" if i < 7 else "done",
            "assignee_user_id": user_id,
            "owner_user_id": user_id,
            "priority": random.choice(["low", "normal", "high"]),
            "source": "demo_seed",
            "created_at": _now() - timedelta(days=random.randint(0, 14)),
            "updated_at": _now(),
        })
    return tasks


# ─── Main Endpoint ─────────────────────────────────────────────────
@router.post("/seed", response_model=DemoSeedResponse)
async def seed_demo_data(
    body: DemoSeedRequest,
    request: Request,
    db=Depends(get_db),
    user=Depends(require_roles(["super_admin", "tenant_admin", "admin"])),
):
    """1-click demo data seeder. Tenant-scoped, idempotent."""
    user_id = user.get("id") or user.get("_id") or user.get("email")
    org_id = user.get("organization_id")
    tenant_id = await _resolve_tenant_id(user)

    _check_seed_rate(str(user_id))

    # Idempotency check
    existing_run = await db.demo_seed_runs.find_one({"tenant_id": tenant_id})
    if existing_run and not body.force:
        return DemoSeedResponse(ok=True, already_seeded=True, counts=existing_run.get("counts", {}))

    counts = {}

    # Clean previous demo data if force
    if body.force and existing_run:
        for coll_name in ["products", "customers", "reservations", "webpos_payments", "webpos_ledger",
                          "ops_cases", "crm_deals", "crm_tasks", "notifications"]:
            await db[coll_name].delete_many({"source": "demo_seed", "tenant_id": tenant_id})
            await db[coll_name].delete_many({"source": "demo_seed", "organization_id": org_id})
        await db.demo_seed_runs.delete_one({"tenant_id": tenant_id})

    # Products
    prod_count = 3 if body.mode == "light" else 5
    products = _gen_products(tenant_id, org_id, prod_count)
    if products:
        await db.products.insert_many(products)
    counts["products"] = len(products)

    # Customers
    cust_count = 5 if body.mode == "light" else 10
    customers = _gen_customers(tenant_id, org_id, cust_count)
    if customers:
        await db.customers.insert_many(customers)
    customer_ids = [c["id"] for c in customers]
    counts["customers"] = len(customers)

    # Reservations
    res_count = 10 if body.mode == "light" else 20
    reservations = _gen_reservations(tenant_id, org_id, customer_ids, res_count)
    if reservations:
        await db.reservations.insert_many(reservations)
    counts["reservations"] = len(reservations)

    # WebPOS + Ledger (if with_finance)
    if body.with_finance:
        pay_count = 5 if body.mode == "light" else 10
        payments, ledger = _gen_webpos_payments(tenant_id, org_id, pay_count)
        if payments:
            await db.webpos_payments.insert_many(payments)
        if ledger:
            await db.webpos_ledger.insert_many(ledger)
        counts["payments"] = len(payments)
        counts["ledger_entries"] = len(ledger)

    # Cases
    case_count = 3 if body.mode == "light" else 6
    cases = _gen_cases(tenant_id, org_id, case_count)
    if cases:
        await db.ops_cases.insert_many(cases)
    counts["cases"] = len(cases)

    # CRM Deals + Tasks (if with_crm)
    if body.with_crm:
        deal_count = 5 if body.mode == "light" else 10
        deals = _gen_crm_deals(tenant_id, org_id, customer_ids, str(user_id), deal_count)
        if deals:
            await db.crm_deals.insert_many(deals)
        deal_ids = [d["id"] for d in deals]
        counts["deals"] = len(deals)

        task_count = 10 if body.mode == "light" else 20
        tasks = _gen_crm_tasks(tenant_id, org_id, deal_ids, customer_ids, str(user_id), task_count)
        if tasks:
            await db.crm_tasks.insert_many(tasks)
        counts["tasks"] = len(tasks)

    # Record seed run
    await db.demo_seed_runs.update_one(
        {"tenant_id": tenant_id},
        {"$set": {
            "tenant_id": tenant_id,
            "organization_id": org_id,
            "mode": body.mode,
            "counts": counts,
            "seeded_at": _now(),
            "seeded_by": str(user_id),
        }},
        upsert=True,
    )

    # Audit log
    try:
        await write_audit_log(
            db,
            organization_id=org_id,
            actor={"actor_type": "user", "actor_id": str(user_id), "email": user.get("email"), "roles": user.get("roles", [])},
            request=request,
            action="demo.seed_run",
            target_type="demo_seed",
            target_id=tenant_id,
            meta={"mode": body.mode, "counts": counts},
        )
    except Exception as e:
        logger.warning("Audit log failed for demo seed: %s", e)

    return DemoSeedResponse(ok=True, already_seeded=False, counts=counts)
