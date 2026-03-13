from __future__ import annotations

from bson import ObjectId
import pytest

from app.utils import now_utc


async def _seed_tenant_plan(test_db, tenant_id: str, plan: str) -> None:
    now = now_utc()
    await test_db.tenant_capabilities.update_one(
        {"tenant_id": tenant_id},
        {
            "$set": {
                "tenant_id": tenant_id,
                "plan": plan,
                "add_ons": [],
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )


async def _seed_usage_count(test_db, *, tenant_id: str, organization_id: str, metric: str, count: int) -> None:
    now = now_utc()
    await test_db.usage_daily.update_one(
        {
            "tenant_id": tenant_id,
            "organization_id": organization_id,
            "metric": metric,
            "date": now.date().isoformat(),
        },
        {
            "$set": {
                "tenant_id": tenant_id,
                "organization_id": organization_id,
                "metric": metric,
                "date": now.date().isoformat(),
                "count": count,
                "last_event_at": now,
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )


async def _seed_reservation_catalog(test_db, organization_id: str) -> tuple[str, str]:
    now = now_utc()
    product_id = ObjectId()
    customer_id = ObjectId()

    await test_db.products.insert_one(
        {
            "_id": product_id,
            "organization_id": organization_id,
            "title": "Test Otel",
            "type": "hotel",
            "created_at": now,
            "updated_at": now,
        }
    )
    await test_db.customers.insert_one(
        {
            "_id": customer_id,
            "organization_id": organization_id,
            "name": "Quota Test Customer",
            "email": "quota@test.local",
            "created_at": now,
            "updated_at": now,
        }
    )
    await test_db.rate_plans.insert_one(
        {
            "_id": ObjectId(),
            "organization_id": organization_id,
            "product_id": product_id,
            "currency": "TRY",
            "base_net_price": 1500,
            "created_at": now,
            "updated_at": now,
        }
    )
    await test_db.inventory.insert_one(
        {
            "_id": ObjectId(),
            "organization_id": organization_id,
            "product_id": product_id,
            "date": "2026-04-10",
            "capacity_available": 5,
            "price": 1500,
            "created_at": now,
            "updated_at": now,
        }
    )
    return str(product_id), str(customer_id)


@pytest.mark.anyio
async def test_reservation_creation_is_blocked_when_reservation_quota_is_full(async_client, agency_headers, test_db):
    organization = await test_db.organizations.find_one({"slug": "default"}, {"_id": 1})
    assert organization is not None
    organization_id = str(organization["_id"])
    tenant_id = "tenant_default"

    await _seed_tenant_plan(test_db, tenant_id, "trial")
    await _seed_usage_count(
        test_db,
        tenant_id=tenant_id,
        organization_id=organization_id,
        metric="reservation.created",
        count=100,
    )
    product_id, customer_id = await _seed_reservation_catalog(test_db, organization_id)

    response = await async_client.post(
        "/api/reservations/reserve",
        headers=agency_headers,
        json={
            "product_id": product_id,
            "customer_id": customer_id,
            "start_date": "2026-04-10",
            "end_date": None,
            "pax": 2,
            "channel": "direct",
        },
    )

    assert response.status_code == 403
    payload = response.json()["error"]
    assert payload["code"] == "quota_exceeded"
    assert payload["details"]["metric"] == "reservation.created"
    assert payload["details"]["limit"] == 100
    assert payload["details"]["cta_href"] == "/pricing"
    assert await test_db.reservations.count_documents({"organization_id": organization_id}) == 0


@pytest.mark.anyio
async def test_sales_summary_csv_is_blocked_when_export_quota_is_full(async_client, agency_headers, test_db):
    organization = await test_db.organizations.find_one({"slug": "default"}, {"_id": 1})
    assert organization is not None
    organization_id = str(organization["_id"])
    tenant_id = "tenant_default"

    await _seed_tenant_plan(test_db, tenant_id, "trial")
    await _seed_usage_count(
        test_db,
        tenant_id=tenant_id,
        organization_id=organization_id,
        metric="export.generated",
        count=10,
    )

    response = await async_client.get("/api/reports/sales-summary.csv", headers=agency_headers)

    assert response.status_code == 403
    payload = response.json()["error"]
    assert payload["code"] == "quota_exceeded"
    assert payload["details"]["metric"] == "export.generated"
    assert payload["details"]["limit"] == 10


@pytest.mark.anyio
async def test_admin_report_download_is_blocked_when_report_quota_is_full(async_client, admin_headers, test_db):
    organization = await test_db.organizations.find_one({"slug": "default"}, {"_id": 1})
    assert organization is not None
    organization_id = str(organization["_id"])
    tenant_id = "tenant_default"

    await _seed_tenant_plan(test_db, tenant_id, "trial")
    await _seed_usage_count(
        test_db,
        tenant_id=tenant_id,
        organization_id=organization_id,
        metric="report.generated",
        count=20,
    )

    response = await async_client.get(
        "/api/admin/reports/match-risk/executive-summary.pdf",
        headers=admin_headers,
    )

    assert response.status_code == 403
    payload = response.json()["error"]
    assert payload["code"] == "quota_exceeded"
    assert payload["details"]["metric"] == "report.generated"
    assert payload["details"]["limit"] == 20
