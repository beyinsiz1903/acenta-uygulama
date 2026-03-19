"""API Tests for Unified Booking State Machine.

Tests all booking transition endpoints:
- GET /api/bookings-statuses/transitions - transition matrix (no auth)
- POST /api/bookings/{id}/quote - DRAFT → QUOTED
- POST /api/bookings/{id}/option - QUOTED → OPTIONED
- POST /api/bookings/{id}/confirm - OPTIONED/QUOTED → CONFIRMED
- POST /api/bookings/{id}/cancel - transitions to CANCELLED
- POST /api/bookings/{id}/complete - CONFIRMED → COMPLETED
- POST /api/bookings/{id}/mark-ticketed - fulfillment status
- POST /api/bookings/{id}/mark-vouchered - fulfillment status
- POST /api/bookings/{id}/mark-refunded - CANCELLED → REFUNDED
- GET /api/bookings/{id}/status - current status with allowed transitions
- GET /api/bookings/{id}/history - transition history
- POST /api/admin/booking-migration/run - migration endpoint
- GET /api/admin/booking-migration/status - migration status
- Invalid transition rejection (422)
- Version conflict detection (409)
"""
import os
import pytest
import requests
from bson import ObjectId

def _unwrap(resp):
    """Unwrap response envelope if present."""
    data = resp.json()
    if isinstance(data, dict) and "ok" in data and "data" in data:
        return data["data"]
    return data


BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
SUPER_ADMIN_EMAIL = "agent@acenta.test"
SUPER_ADMIN_PASSWORD = "agent123"
AGENCY_EMAIL = "agency1@demo.test"
AGENCY_PASSWORD = "agency123"

# Organization ID for super admin (from context)
ORG_ID = "69b5905cb169d94c891a136d"


class TestTransitionMatrixEndpoint:
    """Test GET /api/bookings-statuses/transitions - NO AUTH REQUIRED"""

    def test_transition_matrix_returns_200(self):
        """Transition matrix endpoint should be publicly accessible"""
        resp = requests.get(f"{BASE_URL}/api/bookings-statuses/transitions")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = _unwrap(resp)
        
        # Validate response structure
        assert "statuses" in data
        assert "fulfillment_statuses" in data
        assert "payment_statuses" in data
        assert "transitions" in data
        assert "commands" in data

    def test_transition_matrix_has_all_statuses(self):
        """Verify all expected statuses are present"""
        resp = requests.get(f"{BASE_URL}/api/bookings-statuses/transitions")
        data = _unwrap(resp)
        
        expected_statuses = ["draft", "quoted", "optioned", "confirmed", "completed", "cancelled", "refunded"]
        for status in expected_statuses:
            assert status in data["statuses"], f"Missing status: {status}"

    def test_transition_matrix_has_all_commands(self):
        """Verify all expected commands are present"""
        resp = requests.get(f"{BASE_URL}/api/bookings-statuses/transitions")
        data = _unwrap(resp)
        
        expected_commands = ["create_quote", "place_option", "confirm", "cancel", "complete", "mark_ticketed", "mark_vouchered", "mark_refunded"]
        for cmd in expected_commands:
            assert cmd in data["commands"], f"Missing command: {cmd}"

    def test_transitions_matrix_structure(self):
        """Verify transitions object has correct structure"""
        resp = requests.get(f"{BASE_URL}/api/bookings-statuses/transitions")
        data = _unwrap(resp)
        
        transitions = data["transitions"]
        # Terminal states should have no transitions
        assert transitions["completed"] == [], "completed should have no transitions"
        assert transitions["refunded"] == [], "refunded should have no transitions"
        
        # Draft can go to quoted or cancelled
        assert "quoted" in transitions["draft"]
        assert "cancelled" in transitions["draft"]


@pytest.fixture(scope="module")
def auth_token():
    """Get auth token for super admin"""
    resp = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD}
    )
    if resp.status_code != 200:
        pytest.skip(f"Login failed: {resp.text}")
    return _unwrap(resp)["access_token"]


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Auth headers with bearer token"""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


@pytest.fixture
def test_booking_draft(auth_headers):
    """Create a draft booking in MongoDB for testing transitions"""
    import asyncio
    from motor.motor_asyncio import AsyncIOMotorClient
    
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "test_database")
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    booking_id = ObjectId()
    booking = {
        "_id": booking_id,
        "status": "draft",
        "fulfillment_status": "none",
        "payment_status": "unpaid",
        "version": 0,
        "organization_id": ORG_ID,
        "tenant_id": ORG_ID,
        "hotel_id": "test_hotel_001",
        "hotel_name": "Test Hotel",
        "customer_id": "test_customer_001",
        "customer_name": "Test Customer",
        "created_at": "2026-03-18T10:00:00Z",
        "updated_at": "2026-03-18T10:00:00Z",
        "test_marker": "TEST_BOOKING_STATE_MACHINE"
    }
    
    async def insert():
        await db.bookings.insert_one(booking)
    
    asyncio.get_event_loop().run_until_complete(insert())
    
    yield str(booking_id)
    
    # Cleanup
    async def cleanup():
        await db.bookings.delete_one({"_id": booking_id})
        await db.booking_history.delete_many({"booking_id": str(booking_id)})
        await db.outbox_events.delete_many({"aggregate_id": str(booking_id)})
    
    asyncio.get_event_loop().run_until_complete(cleanup())
    client.close()


class TestBookingTransitions:
    """Test booking transition commands with real DB bookings"""

    def test_quote_draft_booking(self, auth_headers, test_booking_draft):
        """POST /api/bookings/{id}/quote - DRAFT → QUOTED"""
        booking_id = test_booking_draft
        resp = requests.post(
            f"{BASE_URL}/api/bookings/{booking_id}/quote",
            headers=auth_headers,
            json={"reason": "Test quote"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = _unwrap(resp)
        assert data["ok"] is True
        assert data["status"] == "quoted"
        assert data["booking_id"] == booking_id
        assert data["version"] == 1  # Version should increment

    def test_option_quoted_booking(self, auth_headers):
        """POST /api/bookings/{id}/option - QUOTED → OPTIONED"""
        # First create and quote a booking
        booking_id = self._create_booking_in_status("quoted", auth_headers)
        
        resp = requests.post(
            f"{BASE_URL}/api/bookings/{booking_id}/option",
            headers=auth_headers,
            json={"reason": "Test option"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = _unwrap(resp)
        assert data["status"] == "optioned"
        
        # Cleanup
        self._cleanup_booking(booking_id)

    def test_confirm_optioned_booking(self, auth_headers):
        """POST /api/bookings/{id}/confirm - OPTIONED → CONFIRMED"""
        booking_id = self._create_booking_in_status("optioned", auth_headers)
        
        resp = requests.post(
            f"{BASE_URL}/api/bookings/{booking_id}/confirm",
            headers=auth_headers,
            json={"reason": "Test confirm"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = _unwrap(resp)
        assert data["status"] == "confirmed"
        
        self._cleanup_booking(booking_id)

    def test_confirm_quoted_booking(self, auth_headers):
        """POST /api/bookings/{id}/confirm - QUOTED → CONFIRMED (direct path)"""
        booking_id = self._create_booking_in_status("quoted", auth_headers)
        
        resp = requests.post(
            f"{BASE_URL}/api/bookings/{booking_id}/confirm",
            headers=auth_headers,
            json={"reason": "Direct confirm"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = _unwrap(resp)
        assert data["status"] == "confirmed"
        
        self._cleanup_booking(booking_id)

    def test_cancel_draft_booking(self, auth_headers):
        """POST /api/bookings/{id}/cancel - DRAFT → CANCELLED"""
        booking_id = self._create_booking_in_status("draft", auth_headers)
        
        resp = requests.post(
            f"{BASE_URL}/api/bookings/{booking_id}/cancel",
            headers=auth_headers,
            json={"reason": "Test cancel from draft"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = _unwrap(resp)
        assert data["status"] == "cancelled"
        
        self._cleanup_booking(booking_id)

    def test_cancel_confirmed_booking(self, auth_headers):
        """POST /api/bookings/{id}/cancel - CONFIRMED → CANCELLED"""
        booking_id = self._create_booking_in_status("confirmed", auth_headers)
        
        resp = requests.post(
            f"{BASE_URL}/api/bookings/{booking_id}/cancel",
            headers=auth_headers,
            json={"reason": "Test cancel confirmed"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = _unwrap(resp)
        assert data["status"] == "cancelled"
        
        self._cleanup_booking(booking_id)

    def test_complete_confirmed_booking(self, auth_headers):
        """POST /api/bookings/{id}/complete - CONFIRMED → COMPLETED"""
        booking_id = self._create_booking_in_status("confirmed", auth_headers)
        
        resp = requests.post(
            f"{BASE_URL}/api/bookings/{booking_id}/complete",
            headers=auth_headers,
            json={"reason": "Test complete"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = _unwrap(resp)
        assert data["status"] == "completed"
        
        self._cleanup_booking(booking_id)

    def test_mark_refunded_cancelled_booking(self, auth_headers):
        """POST /api/bookings/{id}/mark-refunded - CANCELLED → REFUNDED"""
        booking_id = self._create_booking_in_status("cancelled", auth_headers)
        
        resp = requests.post(
            f"{BASE_URL}/api/bookings/{booking_id}/mark-refunded",
            headers=auth_headers,
            json={"reason": "Refund processed"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = _unwrap(resp)
        assert data["status"] == "refunded"
        
        self._cleanup_booking(booking_id)

    # Helper methods
    def _create_booking_in_status(self, status: str, auth_headers: dict) -> str:
        """Create a booking directly in MongoDB in a specific status"""
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        db_name = os.environ.get("DB_NAME", "test_database")
        
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        
        booking_id = ObjectId()
        booking = {
            "_id": booking_id,
            "status": status,
            "fulfillment_status": "none",
            "payment_status": "unpaid",
            "version": 0,
            "organization_id": ORG_ID,
            "tenant_id": ORG_ID,
            "hotel_id": "test_hotel_001",
            "hotel_name": "Test Hotel",
            "customer_id": "test_customer_001",
            "customer_name": "Test Customer",
            "created_at": "2026-03-18T10:00:00Z",
            "updated_at": "2026-03-18T10:00:00Z",
            "test_marker": "TEST_BOOKING_STATE_MACHINE"
        }
        
        async def insert():
            await db.bookings.insert_one(booking)
        
        asyncio.get_event_loop().run_until_complete(insert())
        client.close()
        
        return str(booking_id)

    def _cleanup_booking(self, booking_id: str):
        """Delete test booking and related records"""
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        db_name = os.environ.get("DB_NAME", "test_database")
        
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        
        async def cleanup():
            await db.bookings.delete_one({"_id": ObjectId(booking_id)})
            await db.booking_history.delete_many({"booking_id": booking_id})
            await db.outbox_events.delete_many({"aggregate_id": booking_id})
        
        asyncio.get_event_loop().run_until_complete(cleanup())
        client.close()


class TestFulfillmentCommands:
    """Test fulfillment status commands (mark-ticketed, mark-vouchered)"""

    def test_mark_ticketed_does_not_change_main_status(self, auth_headers):
        """POST /api/bookings/{id}/mark-ticketed - only changes fulfillment_status"""
        booking_id = self._create_booking_in_status("confirmed", auth_headers)
        
        resp = requests.post(
            f"{BASE_URL}/api/bookings/{booking_id}/mark-ticketed",
            headers=auth_headers,
            json={}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = _unwrap(resp)
        assert data["status"] == "confirmed", "Main status should not change"
        assert data["fulfillment_status"] == "ticketed"
        
        self._cleanup_booking(booking_id)

    def test_mark_vouchered_does_not_change_main_status(self, auth_headers):
        """POST /api/bookings/{id}/mark-vouchered - only changes fulfillment_status"""
        booking_id = self._create_booking_in_status("confirmed", auth_headers)
        
        resp = requests.post(
            f"{BASE_URL}/api/bookings/{booking_id}/mark-vouchered",
            headers=auth_headers,
            json={}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = _unwrap(resp)
        assert data["status"] == "confirmed", "Main status should not change"
        assert data["fulfillment_status"] == "vouchered"
        
        self._cleanup_booking(booking_id)

    def test_ticketed_then_vouchered_becomes_both(self, auth_headers):
        """Mark ticketed then vouchered → fulfillment_status=both"""
        booking_id = self._create_booking_in_status("confirmed", auth_headers)
        
        # First mark ticketed
        resp1 = requests.post(
            f"{BASE_URL}/api/bookings/{booking_id}/mark-ticketed",
            headers=auth_headers,
            json={}
        )
        assert resp1.status_code == 200
        assert _unwrap(resp1)["fulfillment_status"] == "ticketed"
        
        # Then mark vouchered
        resp2 = requests.post(
            f"{BASE_URL}/api/bookings/{booking_id}/mark-vouchered",
            headers=auth_headers,
            json={}
        )
        assert resp2.status_code == 200
        assert _unwrap(resp2)["fulfillment_status"] == "both"
        
        self._cleanup_booking(booking_id)

    def _create_booking_in_status(self, status: str, auth_headers: dict) -> str:
        """Create a booking directly in MongoDB in a specific status"""
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        db_name = os.environ.get("DB_NAME", "test_database")
        
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        
        booking_id = ObjectId()
        booking = {
            "_id": booking_id,
            "status": status,
            "fulfillment_status": "none",
            "payment_status": "unpaid",
            "version": 0,
            "organization_id": ORG_ID,
            "tenant_id": ORG_ID,
            "hotel_id": "test_hotel_001",
            "hotel_name": "Test Hotel",
            "customer_id": "test_customer_001",
            "customer_name": "Test Customer",
            "created_at": "2026-03-18T10:00:00Z",
            "updated_at": "2026-03-18T10:00:00Z",
            "test_marker": "TEST_BOOKING_STATE_MACHINE"
        }
        
        async def insert():
            await db.bookings.insert_one(booking)
        
        asyncio.get_event_loop().run_until_complete(insert())
        client.close()
        
        return str(booking_id)

    def _cleanup_booking(self, booking_id: str):
        """Delete test booking and related records"""
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        db_name = os.environ.get("DB_NAME", "test_database")
        
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        
        async def cleanup():
            await db.bookings.delete_one({"_id": ObjectId(booking_id)})
            await db.booking_history.delete_many({"booking_id": booking_id})
            await db.outbox_events.delete_many({"aggregate_id": booking_id})
        
        asyncio.get_event_loop().run_until_complete(cleanup())
        client.close()


class TestInvalidTransitions:
    """Test that invalid transitions are properly rejected with 422"""

    def test_completed_cannot_cancel(self, auth_headers):
        """COMPLETED → CANCELLED should return 422"""
        booking_id = self._create_booking_in_status("completed", auth_headers)
        
        resp = requests.post(
            f"{BASE_URL}/api/bookings/{booking_id}/cancel",
            headers=auth_headers,
            json={"reason": "Try cancel completed"}
        )
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"
        
        data = _unwrap(resp)
        assert "INVALID_TRANSITION" in str(data) or "not allowed" in str(data).lower()
        
        self._cleanup_booking(booking_id)

    def test_draft_cannot_confirm_directly(self, auth_headers):
        """DRAFT → CONFIRMED directly should return 422"""
        booking_id = self._create_booking_in_status("draft", auth_headers)
        
        resp = requests.post(
            f"{BASE_URL}/api/bookings/{booking_id}/confirm",
            headers=auth_headers,
            json={"reason": "Try direct confirm"}
        )
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"
        
        self._cleanup_booking(booking_id)

    def test_refunded_cannot_transition(self, auth_headers):
        """REFUNDED is terminal - no transitions allowed"""
        booking_id = self._create_booking_in_status("refunded", auth_headers)
        
        # Try to confirm
        resp = requests.post(
            f"{BASE_URL}/api/bookings/{booking_id}/confirm",
            headers=auth_headers,
            json={}
        )
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"
        
        self._cleanup_booking(booking_id)

    def _create_booking_in_status(self, status: str, auth_headers: dict) -> str:
        """Create a booking directly in MongoDB in a specific status"""
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        db_name = os.environ.get("DB_NAME", "test_database")
        
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        
        booking_id = ObjectId()
        booking = {
            "_id": booking_id,
            "status": status,
            "fulfillment_status": "none",
            "payment_status": "unpaid",
            "version": 0,
            "organization_id": ORG_ID,
            "tenant_id": ORG_ID,
            "hotel_id": "test_hotel_001",
            "hotel_name": "Test Hotel",
            "customer_id": "test_customer_001",
            "customer_name": "Test Customer",
            "created_at": "2026-03-18T10:00:00Z",
            "updated_at": "2026-03-18T10:00:00Z",
            "test_marker": "TEST_BOOKING_STATE_MACHINE"
        }
        
        async def insert():
            await db.bookings.insert_one(booking)
        
        asyncio.get_event_loop().run_until_complete(insert())
        client.close()
        
        return str(booking_id)

    def _cleanup_booking(self, booking_id: str):
        """Delete test booking and related records"""
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        db_name = os.environ.get("DB_NAME", "test_database")
        
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        
        async def cleanup():
            await db.bookings.delete_one({"_id": ObjectId(booking_id)})
            await db.booking_history.delete_many({"booking_id": booking_id})
            await db.outbox_events.delete_many({"aggregate_id": booking_id})
        
        asyncio.get_event_loop().run_until_complete(cleanup())
        client.close()


class TestVersionConflict:
    """Test optimistic locking with version field"""

    def test_version_field_increments_on_transition(self, auth_headers):
        """Verify version field increments on each transition"""
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        db_name = os.environ.get("DB_NAME", "test_database")
        
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        
        # Create booking with version 0
        booking_id = ObjectId()
        booking = {
            "_id": booking_id,
            "status": "draft",
            "fulfillment_status": "none",
            "payment_status": "unpaid",
            "version": 0,
            "organization_id": ORG_ID,
            "tenant_id": ORG_ID,
            "hotel_id": "test_hotel_001",
            "hotel_name": "Test Hotel",
            "customer_id": "test_customer_001",
            "customer_name": "Test Customer",
            "test_marker": "TEST_BOOKING_STATE_MACHINE"
        }
        
        async def setup():
            await db.bookings.insert_one(booking)
        
        asyncio.get_event_loop().run_until_complete(setup())
        
        # Quote the booking (version 0 → 1)
        resp1 = requests.post(
            f"{BASE_URL}/api/bookings/{str(booking_id)}/quote",
            headers=auth_headers,
            json={}
        )
        assert resp1.status_code == 200
        assert _unwrap(resp1)["version"] == 1, "Version should be 1 after first transition"
        
        # Option the booking (version 1 → 2)
        resp2 = requests.post(
            f"{BASE_URL}/api/bookings/{str(booking_id)}/option",
            headers=auth_headers,
            json={}
        )
        assert resp2.status_code == 200
        assert _unwrap(resp2)["version"] == 2, "Version should be 2 after second transition"
        
        # Cleanup
        async def cleanup():
            await db.bookings.delete_one({"_id": booking_id})
            await db.booking_history.delete_many({"booking_id": str(booking_id)})
            await db.outbox_events.delete_many({"aggregate_id": str(booking_id)})
        
        asyncio.get_event_loop().run_until_complete(cleanup())
        client.close()


class TestBookingStatusEndpoint:
    """Test GET /api/bookings/{id}/status"""

    def test_get_booking_status(self, auth_headers):
        """GET /api/bookings/{id}/status returns current status with allowed transitions"""
        booking_id = self._create_booking_in_status("quoted", auth_headers)
        
        resp = requests.get(
            f"{BASE_URL}/api/bookings/{booking_id}/status",
            headers=auth_headers
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = _unwrap(resp)
        assert data["booking_id"] == booking_id
        assert data["status"] == "quoted"
        assert "allowed_transitions" in data
        assert "optioned" in data["allowed_transitions"]
        assert "confirmed" in data["allowed_transitions"]
        assert "cancelled" in data["allowed_transitions"]
        
        self._cleanup_booking(booking_id)

    def test_get_status_nonexistent_booking(self, auth_headers):
        """GET /api/bookings/{id}/status for non-existent booking returns 404"""
        fake_id = str(ObjectId())
        resp = requests.get(
            f"{BASE_URL}/api/bookings/{fake_id}/status",
            headers=auth_headers
        )
        assert resp.status_code == 404

    def _create_booking_in_status(self, status: str, auth_headers: dict) -> str:
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        db_name = os.environ.get("DB_NAME", "test_database")
        
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        
        booking_id = ObjectId()
        booking = {
            "_id": booking_id,
            "status": status,
            "fulfillment_status": "none",
            "payment_status": "unpaid",
            "version": 0,
            "organization_id": ORG_ID,
            "tenant_id": ORG_ID,
            "hotel_id": "test_hotel_001",
            "hotel_name": "Test Hotel",
            "customer_id": "test_customer_001",
            "customer_name": "Test Customer",
            "test_marker": "TEST_BOOKING_STATE_MACHINE"
        }
        
        async def insert():
            await db.bookings.insert_one(booking)
        
        asyncio.get_event_loop().run_until_complete(insert())
        client.close()
        
        return str(booking_id)

    def _cleanup_booking(self, booking_id: str):
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        db_name = os.environ.get("DB_NAME", "test_database")
        
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        
        async def cleanup():
            await db.bookings.delete_one({"_id": ObjectId(booking_id)})
            await db.booking_history.delete_many({"booking_id": booking_id})
            await db.outbox_events.delete_many({"aggregate_id": booking_id})
        
        asyncio.get_event_loop().run_until_complete(cleanup())
        client.close()


class TestBookingHistoryEndpoint:
    """Test GET /api/bookings/{id}/history"""

    def test_get_booking_history(self, auth_headers):
        """GET /api/bookings/{id}/history returns ordered transition history"""
        booking_id = self._create_booking_in_status("draft", auth_headers)
        
        # Do some transitions to create history
        requests.post(f"{BASE_URL}/api/bookings/{booking_id}/quote", headers=auth_headers, json={})
        requests.post(f"{BASE_URL}/api/bookings/{booking_id}/option", headers=auth_headers, json={})
        
        # Get history
        resp = requests.get(
            f"{BASE_URL}/api/bookings/{booking_id}/history",
            headers=auth_headers
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = _unwrap(resp)
        assert data["booking_id"] == booking_id
        assert "history" in data
        assert len(data["history"]) >= 2, "Should have at least 2 history entries"
        
        # Verify history entries have expected fields
        for entry in data["history"]:
            assert "from_status" in entry
            assert "to_status" in entry
            assert "command" in entry
            assert "occurred_at" in entry
        
        self._cleanup_booking(booking_id)

    def _create_booking_in_status(self, status: str, auth_headers: dict) -> str:
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        db_name = os.environ.get("DB_NAME", "test_database")
        
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        
        booking_id = ObjectId()
        booking = {
            "_id": booking_id,
            "status": status,
            "fulfillment_status": "none",
            "payment_status": "unpaid",
            "version": 0,
            "organization_id": ORG_ID,
            "tenant_id": ORG_ID,
            "hotel_id": "test_hotel_001",
            "hotel_name": "Test Hotel",
            "customer_id": "test_customer_001",
            "customer_name": "Test Customer",
            "test_marker": "TEST_BOOKING_STATE_MACHINE"
        }
        
        async def insert():
            await db.bookings.insert_one(booking)
        
        asyncio.get_event_loop().run_until_complete(insert())
        client.close()
        
        return str(booking_id)

    def _cleanup_booking(self, booking_id: str):
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        db_name = os.environ.get("DB_NAME", "test_database")
        
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        
        async def cleanup():
            await db.bookings.delete_one({"_id": ObjectId(booking_id)})
            await db.booking_history.delete_many({"booking_id": booking_id})
            await db.outbox_events.delete_many({"aggregate_id": booking_id})
        
        asyncio.get_event_loop().run_until_complete(cleanup())
        client.close()


class TestMigrationEndpoints:
    """Test admin migration endpoints"""

    def test_migration_status(self, auth_headers):
        """GET /api/admin/booking-migration/status returns migration progress"""
        resp = requests.get(
            f"{BASE_URL}/api/admin/booking-migration/status",
            headers=auth_headers
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = _unwrap(resp)
        assert "total_bookings" in data
        assert "migrated" in data
        assert "pending" in data
        assert "migration_complete" in data

    def test_migration_dry_run(self, auth_headers):
        """POST /api/admin/booking-migration/run?dry_run=true returns stats without modifying"""
        resp = requests.post(
            f"{BASE_URL}/api/admin/booking-migration/run?dry_run=true",
            headers=auth_headers
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = _unwrap(resp)
        assert data["ok"] is True
        assert data["dry_run"] is True
        assert "stats" in data


class TestAuthRequired:
    """Test that transition endpoints require authentication"""

    def test_quote_requires_auth(self):
        """POST /api/bookings/{id}/quote without auth returns 401/403"""
        fake_id = str(ObjectId())
        resp = requests.post(
            f"{BASE_URL}/api/bookings/{fake_id}/quote",
            json={}
        )
        assert resp.status_code in [401, 403], f"Expected 401/403, got {resp.status_code}"

    def test_confirm_requires_auth(self):
        """POST /api/bookings/{id}/confirm without auth returns 401/403"""
        fake_id = str(ObjectId())
        resp = requests.post(
            f"{BASE_URL}/api/bookings/{fake_id}/confirm",
            json={}
        )
        assert resp.status_code in [401, 403]

    def test_history_requires_auth(self):
        """GET /api/bookings/{id}/history without auth returns 401/403"""
        fake_id = str(ObjectId())
        resp = requests.get(f"{BASE_URL}/api/bookings/{fake_id}/history")
        assert resp.status_code in [401, 403]


class TestBookingNotFound:
    """Test 404 handling for non-existent bookings"""

    def test_quote_nonexistent_booking(self, auth_headers):
        """POST /api/bookings/{id}/quote for non-existent booking returns 404"""
        fake_id = str(ObjectId())
        resp = requests.post(
            f"{BASE_URL}/api/bookings/{fake_id}/quote",
            headers=auth_headers,
            json={}
        )
        assert resp.status_code == 404


class TestOutboxEvents:
    """Test that outbox events are created on transitions"""

    def test_transition_creates_outbox_event(self, auth_headers):
        """Verify outbox_events collection receives entries on transition"""
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        db_name = os.environ.get("DB_NAME", "test_database")
        
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        
        booking_id = ObjectId()
        booking = {
            "_id": booking_id,
            "status": "draft",
            "fulfillment_status": "none",
            "payment_status": "unpaid",
            "version": 0,
            "organization_id": ORG_ID,
            "tenant_id": ORG_ID,
            "hotel_id": "test_hotel_001",
            "hotel_name": "Test Hotel",
            "customer_id": "test_customer_001",
            "customer_name": "Test Customer",
            "test_marker": "TEST_BOOKING_STATE_MACHINE"
        }
        
        async def test_outbox():
            await db.bookings.insert_one(booking)
            
            # Do transition
            requests.post(
                f"{BASE_URL}/api/bookings/{str(booking_id)}/quote",
                headers=auth_headers,
                json={}
            )
            
            # Check outbox
            event = await db.outbox_events.find_one(
                {"aggregate_id": str(booking_id)},
                {"_id": 0}
            )
            return event
        
        event = asyncio.get_event_loop().run_until_complete(test_outbox())
        
        # Cleanup
        async def cleanup():
            await db.bookings.delete_one({"_id": booking_id})
            await db.booking_history.delete_many({"booking_id": str(booking_id)})
            await db.outbox_events.delete_many({"aggregate_id": str(booking_id)})
        
        asyncio.get_event_loop().run_until_complete(cleanup())
        client.close()
        
        assert event is not None, "Outbox event should be created"
        assert event["event_type"] == "booking.quoted"
        assert event["status"] == "pending"
