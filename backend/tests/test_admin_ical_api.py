"""Test suite for Villa iCal admin endpoints.

Tests the new iCal sync functionality including:
- GET /api/admin/ical/feeds?product_id=<PRODUCT_ID>
- POST /api/admin/ical/feeds
- POST /api/admin/ical/sync
- GET /api/admin/ical/calendar?product_id=<PRODUCT_ID>&year=<YYYY>&month=<MM>
"""

from datetime import date
from typing import Any, Dict

import pytest
from httpx import AsyncClient

from app.utils import now_utc


@pytest.mark.anyio
async def test_admin_ical_feeds_list_empty(
    async_client: AsyncClient,
    admin_token: str,
    test_db: Any,
) -> None:
    """Test GET /api/admin/ical/feeds returns empty list when no feeds exist."""
    
    # Create a test product for filtering
    org_id = "695e03c80b04ed31c4eaa899"
    product_id = "test_product_123"
    
    # Ensure organization exists
    await test_db.organizations.insert_one({
        "_id": org_id,
        "slug": "test-org",
        "name": "Test Organization"
    })
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Test without product_id filter
    response = await async_client.get("/api/admin/ical/feeds", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0
    
    # Test with product_id filter
    response = await async_client.get(
        f"/api/admin/ical/feeds?product_id={product_id}",
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.anyio
async def test_admin_ical_feeds_create(
    async_client: AsyncClient,
    admin_token: str,
    test_db: Any,
) -> None:
    """Test POST /api/admin/ical/feeds creates a feed document."""
    
    org_id = "695e03c80b04ed31c4eaa899"
    product_id = "test_product_villa_123"
    
    # Ensure organization exists
    await test_db.organizations.insert_one({
        "_id": org_id,
        "slug": "test-org",
        "name": "Test Organization"
    })
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    payload = {
        "product_id": product_id,
        "url": "mock://villa-demo"
    }
    
    response = await async_client.post("/api/admin/ical/feeds", headers=headers, json=payload)
    assert response.status_code == 200
    
    data = response.json()
    
    # Verify response structure
    assert "id" in data
    assert data["product_id"] == product_id
    assert data["url"] == "https://example.com/villa-demo.ics"
    assert data["status"] == "active"
    assert data["last_sync_at"] is None
    
    # Verify internal fields are excluded from response
    assert "organization_id" not in data
    assert "_id" not in data
    
    # Verify document was created in database
    feed_doc = await test_db.ical_feeds.find_one({"id": data["id"]})
    assert feed_doc is not None
    assert feed_doc["organization_id"] == org_id
    assert feed_doc["product_id"] == product_id
    assert feed_doc["url"] == "https://example.com/villa-demo.ics"
    assert feed_doc["status"] == "active"
    assert feed_doc["created_at"] is not None
    assert feed_doc["last_sync_at"] is None
    
    return data["id"]  # Return feed_id for use in other tests


@pytest.mark.anyio
async def test_admin_ical_sync_mock_functionality(
    async_client: AsyncClient,
    admin_token: str,
    test_db: Any,
) -> None:
    """Test POST /api/admin/ical/sync with mock URL by directly inserting mock feed."""
    
    org_id = "695e03c80b04ed31c4eaa899"
    product_id = "test_product_villa_sync_mock"
    
    # Ensure organization exists
    await test_db.organizations.insert_one({
        "_id": org_id,
        "slug": "test-org",
        "name": "Test Organization"
    })
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Directly insert a feed with mock URL into database (bypassing Pydantic validation)
    from uuid import uuid4
    from app.utils import now_utc
    
    feed_id = str(uuid4())
    feed_doc = {
        "id": feed_id,
        "organization_id": org_id,
        "product_id": product_id,
        "url": "mock://villa-demo",
        "status": "active",
        "created_at": now_utc().isoformat(),
        "last_sync_at": None,
    }
    await test_db.ical_feeds.insert_one(feed_doc)
    
    # Now sync the feed
    sync_payload = {"feed_id": feed_id}
    
    response = await async_client.post("/api/admin/ical/sync", headers=headers, json=sync_payload)
    assert response.status_code == 200
    
    data = response.json()
    
    # Verify sync response structure
    assert data["ok"] is True
    assert data["feed_id"] == feed_id
    assert data["events"] >= 1  # Mock generates at least 1 event
    assert data["blocks_created"] >= 1  # Should create at least 1 block
    
    # Verify availability_blocks were created
    blocks = await test_db.availability_blocks.find({
        "organization_id": org_id,
        "product_id": product_id,
        "source": "ical",
        "source_ref.feed_id": feed_id
    }).to_list(100)
    
    assert len(blocks) >= 1
    
    # Verify block structure
    block = blocks[0]
    assert block["id"] is not None
    assert block["organization_id"] == org_id
    assert block["product_id"] == product_id
    assert block["source"] == "ical"
    assert block["source_ref"]["feed_id"] == feed_id
    assert block["source_ref"]["uid"] is not None
    assert block["date_from"] is not None
    assert block["date_to"] is not None
    assert block["created_at"] is not None
    
    # Verify dates are stored as ISO strings
    assert isinstance(block["date_from"], str)
    assert isinstance(block["date_to"], str)
    
    # Verify feed last_sync_at was updated
    updated_feed = await test_db.ical_feeds.find_one({"id": feed_id})
    assert updated_feed["last_sync_at"] is not None
    
    return feed_id, product_id


@pytest.mark.anyio
async def test_admin_ical_sync(
    async_client: AsyncClient,
    admin_token: str,
    test_db: Any,
) -> None:
    """Test POST /api/admin/ical/sync with real HTTP URL (expects failure in test environment)."""
    
    org_id = "695e03c80b04ed31c4eaa899"
    product_id = "test_product_villa_sync"
    
    # Ensure organization exists
    await test_db.organizations.insert_one({
        "_id": org_id,
        "slug": "test-org",
        "name": "Test Organization"
    })
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # First create a feed
    feed_payload = {
        "product_id": product_id,
        "url": "https://example.com/villa-demo.ics"
    }
    
    create_response = await async_client.post("/api/admin/ical/feeds", headers=headers, json=feed_payload)
    assert create_response.status_code == 200
    feed_data = create_response.json()
    feed_id = feed_data["id"]
    
    # Now sync the feed (this will fail because example.com doesn't have a real iCal file)
    sync_payload = {"feed_id": feed_id}
    
    response = await async_client.post("/api/admin/ical/sync", headers=headers, json=sync_payload)
    # In test environment, this should fail with 502 (ical_fetch_failed)
    assert response.status_code == 502
    
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "ical_fetch_failed"


@pytest.mark.anyio
async def test_admin_ical_calendar(
    async_client: AsyncClient,
    admin_token: str,
    test_db: Any,
) -> None:
    """Test GET /api/admin/ical/calendar returns blocked dates."""
    
    org_id = "695e03c80b04ed31c4eaa899"
    product_id = "test_product_villa_calendar"
    
    # Ensure organization exists
    await test_db.organizations.insert_one({
        "_id": org_id,
        "slug": "test-org",
        "name": "Test Organization"
    })
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Directly insert a feed with mock URL and sync it
    from uuid import uuid4
    from app.utils import now_utc
    
    feed_id = str(uuid4())
    feed_doc = {
        "id": feed_id,
        "organization_id": org_id,
        "product_id": product_id,
        "url": "mock://villa-demo",
        "status": "active",
        "created_at": now_utc().isoformat(),
        "last_sync_at": None,
    }
    await test_db.ical_feeds.insert_one(feed_doc)
    
    # Sync the feed to create availability blocks
    sync_payload = {"feed_id": feed_id}
    sync_response = await async_client.post("/api/admin/ical/sync", headers=headers, json=sync_payload)
    assert sync_response.status_code == 200
    
    # Get current date for testing
    today = now_utc().date()
    current_year = today.year
    current_month = today.month
    
    # Test calendar endpoint
    response = await async_client.get(
        f"/api/admin/ical/calendar?product_id={product_id}&year={current_year}&month={current_month}",
        headers=headers
    )
    assert response.status_code == 200
    
    data = response.json()
    
    # Verify response structure
    assert data["product_id"] == product_id
    assert data["year"] == current_year
    assert data["month"] == current_month
    assert "blocked_dates" in data
    assert isinstance(data["blocked_dates"], list)
    
    # Mock generator blocks days 10-12 of current month, so we should have at least 3 blocked dates
    blocked_dates = data["blocked_dates"]
    assert len(blocked_dates) >= 3
    
    # Verify all blocked dates are in correct ISO format (YYYY-MM-DD)
    for blocked_date in blocked_dates:
        assert isinstance(blocked_date, str)
        # Verify it's a valid ISO date
        parsed_date = date.fromisoformat(blocked_date)
        assert parsed_date.year == current_year
        assert parsed_date.month == current_month
    
    # Verify expected dates (10, 11, 12) are present
    expected_dates = [
        date(current_year, current_month, 10).isoformat(),
        date(current_year, current_month, 11).isoformat(),
        date(current_year, current_month, 12).isoformat(),
    ]
    
    for expected_date in expected_dates:
        assert expected_date in blocked_dates


@pytest.mark.anyio
async def test_admin_ical_feeds_list_with_data(
    async_client: AsyncClient,
    admin_token: str,
    test_db: Any,
) -> None:
    """Test GET /api/admin/ical/feeds returns feeds after creation."""
    
    org_id = "695e03c80b04ed31c4eaa899"
    product_id = "test_product_villa_list"
    
    # Ensure organization exists
    await test_db.organizations.insert_one({
        "_id": org_id,
        "slug": "test-org",
        "name": "Test Organization"
    })
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create a feed
    feed_payload = {
        "product_id": product_id,
        "url": "https://example.com/villa-demo.ics"
    }
    
    create_response = await async_client.post("/api/admin/ical/feeds", headers=headers, json=feed_payload)
    assert create_response.status_code == 200
    feed_data = create_response.json()
    
    # Test list all feeds
    response = await async_client.get("/api/admin/ical/feeds", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    
    # Find our created feed
    our_feed = next((f for f in data if f["id"] == feed_data["id"]), None)
    assert our_feed is not None
    assert our_feed["product_id"] == product_id
    assert our_feed["url"] == "https://example.com/villa-demo.ics"
    assert our_feed["status"] == "active"
    
    # Test list with product_id filter
    response = await async_client.get(
        f"/api/admin/ical/feeds?product_id={product_id}",
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    
    # All returned feeds should match the product_id filter
    for feed in data:
        assert feed["product_id"] == product_id


@pytest.mark.anyio
async def test_admin_ical_sync_nonexistent_feed(
    async_client: AsyncClient,
    admin_token: str,
    test_db: Any,
) -> None:
    """Test POST /api/admin/ical/sync returns 404 for non-existent feed."""
    
    org_id = "695e03c80b04ed31c4eaa899"
    
    # Ensure organization exists
    await test_db.organizations.insert_one({
        "_id": org_id,
        "slug": "test-org",
        "name": "Test Organization"
    })
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Try to sync a non-existent feed
    sync_payload = {"feed_id": "non-existent-feed-id"}
    
    response = await async_client.post("/api/admin/ical/sync", headers=headers, json=sync_payload)
    assert response.status_code == 404
    
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "ical_feed_not_found"


@pytest.mark.anyio
async def test_admin_ical_auth_required(
    async_client: AsyncClient,
    test_db: Any,
) -> None:
    """Test that all iCal endpoints require authentication."""
    
    # Test without authentication headers
    
    # GET /feeds
    response = await async_client.get("/api/admin/ical/feeds")
    assert response.status_code == 401
    
    # POST /feeds
    response = await async_client.post("/api/admin/ical/feeds", json={
        "product_id": "test",
        "url": "https://example.com/test.ics"
    })
    assert response.status_code == 401
    
    # POST /sync
    response = await async_client.post("/api/admin/ical/sync", json={
        "feed_id": "test"
    })
    assert response.status_code == 401
    
    # GET /calendar
    response = await async_client.get("/api/admin/ical/calendar?product_id=test&year=2024&month=1")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_admin_ical_comprehensive_flow(
    async_client: AsyncClient,
    admin_token: str,
    test_db: Any,
) -> None:
    """Test complete iCal workflow: create feed -> sync -> check calendar."""
    
    org_id = "695e03c80b04ed31c4eaa899"
    product_id = "test_product_villa_comprehensive"
    
    # Ensure organization exists
    await test_db.organizations.insert_one({
        "_id": org_id,
        "slug": "test-org",
        "name": "Test Organization"
    })
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Step 1: Check empty feeds list
    response = await async_client.get(
        f"/api/admin/ical/feeds?product_id={product_id}",
        headers=headers
    )
    assert response.status_code == 200
    assert len(response.json()) == 0
    
    # Step 2: Create feed
    feed_payload = {
        "product_id": product_id,
        "url": "https://example.com/villa-demo.ics"
    }
    
    response = await async_client.post("/api/admin/ical/feeds", headers=headers, json=feed_payload)
    assert response.status_code == 200
    feed_data = response.json()
    feed_id = feed_data["id"]
    
    # Verify response excludes internal fields
    assert "organization_id" not in feed_data
    assert "_id" not in feed_data
    
    # Step 3: Update feed to use mock URL for testing (direct database update)
    await test_db.ical_feeds.update_one(
        {"id": feed_id},
        {"$set": {"url": "mock://villa-demo"}}
    )
    
    # Step 4: Sync feed
    sync_payload = {"feed_id": feed_id}
    
    response = await async_client.post("/api/admin/ical/sync", headers=headers, json=sync_payload)
    assert response.status_code == 200
    sync_data = response.json()
    
    assert sync_data["ok"] is True
    assert sync_data["feed_id"] == feed_id
    assert sync_data["events"] >= 1
    assert sync_data["blocks_created"] >= 1
    
    # Step 5: Check calendar
    today = now_utc().date()
    current_year = today.year
    current_month = today.month
    
    response = await async_client.get(
        f"/api/admin/ical/calendar?product_id={product_id}&year={current_year}&month={current_month}",
        headers=headers
    )
    assert response.status_code == 200
    calendar_data = response.json()
    
    assert calendar_data["product_id"] == product_id
    assert calendar_data["year"] == current_year
    assert calendar_data["month"] == current_month
    assert len(calendar_data["blocked_dates"]) >= 3
    
    # Verify all blocked dates are in correct format
    for blocked_date in calendar_data["blocked_dates"]:
        parsed_date = date.fromisoformat(blocked_date)
        assert parsed_date.year == current_year
        assert parsed_date.month == current_month
    
    # Step 5: Verify availability_blocks in database
    blocks = await test_db.availability_blocks.find({
        "organization_id": org_id,
        "product_id": product_id,
        "source": "ical",
        "source_ref.feed_id": feed_id
    }).to_list(100)
    
    assert len(blocks) >= 1
    
    for block in blocks:
        # Verify required fields
        assert "id" in block
        assert block["organization_id"] == org_id
        assert block["product_id"] == product_id
        assert block["source"] == "ical"
        assert "feed_id" in block["source_ref"]
        assert "uid" in block["source_ref"]
        assert "date_from" in block
        assert "date_to" in block
        assert "created_at" in block
        
        # Verify date format (ISO strings)
        assert isinstance(block["date_from"], str)
        assert isinstance(block["date_to"], str)
        date.fromisoformat(block["date_from"])  # Should not raise
        date.fromisoformat(block["date_to"])    # Should not raise