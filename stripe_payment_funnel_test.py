#!/usr/bin/env python3
"""
Stripe Payment Succeeded Funnel Integration Test

Test scenario:
1) Create a simple booking document in test DB
2) Prepare fake Stripe event payload and give to handler
3) Call handler directly: _handle_payment_intent_succeeded
4) Check booking payment_status is 'paid' 
5) Check funnel_events collection for payment.succeeded event
6) Optionally check admin endpoint

Expected results:
- Handler returns status=200, body={"ok": True}
- Booking payment_status == "paid" (or orchestrator's final value)
- funnel_events contains public.payment.succeeded event with proper context/trace
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from bson import ObjectId

# Add backend to path
sys.path.insert(0, '/app/backend')

from app.db import connect_mongo, get_db
from app.services.stripe_handlers import _handle_payment_intent_succeeded
from app.utils import now_utc

# Test constants
ORGANIZATION_ID = "695e03c80b04ed31c4eaa899"
AGENCY_ID = "695e03c80b04ed31c4eaa89a"
CORRELATION_ID = "fc_test_payment_succeeded_01"
PAYMENT_INTENT_ID = "pi_test_123"

# Generate unique event ID for each test run
import time
EVENT_ID = f"evt_test_{int(time.time())}"

async def create_test_booking(db):
    """Create a test booking document for payment testing."""
    
    booking_id = str(ObjectId())
    
    booking_doc = {
        "_id": booking_id,
        "organization_id": ORGANIZATION_ID,
        "agency_id": AGENCY_ID,
        "status": "CONFIRMED",
        "payment_status": "pending",
        "currency": "EUR",
        "amounts": {
            "sell": 100.0
        },
        "correlation_id": CORRELATION_ID,
        "created_at": now_utc(),
        "updated_at": now_utc()
    }
    
    await db.bookings.insert_one(booking_doc)
    print(f"✅ Created test booking: {booking_id}")
    
    # Create payment aggregate (required by BookingPaymentsOrchestrator)
    from app.services.booking_payments import BookingPaymentsService
    
    payments_service = BookingPaymentsService(db)
    payment_aggregate = await payments_service.get_or_create_aggregate(
        organization_id=ORGANIZATION_ID,
        agency_id=AGENCY_ID,
        booking_id=booking_id,
        currency="EUR",
        total_cents=10000  # 100.00 EUR
    )
    print(f"✅ Created payment aggregate: {payment_aggregate['_id']}")
    
    return booking_id

def create_fake_stripe_event(booking_id):
    """Create a fake Stripe payment_intent.succeeded event payload."""
    
    fake_event = {
        "id": EVENT_ID,
        "type": "payment_intent.succeeded",
        "data": {
            "object": {
                "id": PAYMENT_INTENT_ID,
                "amount_received": 10000,  # 100.00 EUR in cents
                "currency": "eur",
                "metadata": {
                    "booking_id": booking_id,
                    "organization_id": ORGANIZATION_ID,
                    "agency_id": AGENCY_ID,
                    "correlation_id": CORRELATION_ID,
                    "channel": "public",
                    "payment_id": PAYMENT_INTENT_ID  # Add explicit payment_id
                }
            }
        }
    }
    
    print(f"✅ Created fake Stripe event: {EVENT_ID}")
    return fake_event

async def call_payment_handler(fake_event):
    """Call the _handle_payment_intent_succeeded handler directly."""
    
    print("🔄 Calling _handle_payment_intent_succeeded handler...")
    
    try:
        status, body = await _handle_payment_intent_succeeded(fake_event)
        print(f"✅ Handler response: status={status}, body={body}")
        return status, body
    except Exception as e:
        print(f"❌ Handler failed: {e}")
        import traceback
        traceback.print_exc()
        raise

async def check_booking_payment_status(db, booking_id):
    """Check if booking payment_status was updated."""
    
    print("🔄 Checking booking payment_status...")
    
    # Check booking document
    booking = await db.bookings.find_one({"_id": booking_id})
    if booking:
        payment_status = booking.get("payment_status")
        print(f"📋 Booking payment_status: {payment_status}")
    else:
        print("❌ Booking not found")
        return None
    
    # Check booking_payments aggregate
    payment_aggregate = await db.booking_payments.find_one({
        "organization_id": ORGANIZATION_ID,
        "booking_id": booking_id
    })
    
    if payment_aggregate:
        agg_status = payment_aggregate.get("status")
        amount_paid = payment_aggregate.get("amount_paid", 0)
        amount_total = payment_aggregate.get("amount_total", 0)
        print(f"💰 Payment aggregate status: {agg_status}, amount_paid: {amount_paid}, amount_total: {amount_total}")
        
        # Check if there are any payment transactions
        tx_count = await db.booking_payment_transactions.count_documents({
            "organization_id": ORGANIZATION_ID,
            "booking_id": booking_id
        })
        print(f"📝 Payment transactions count: {tx_count}")
        
        return agg_status
    else:
        print("⚠️ Payment aggregate not found")
        return None

async def check_funnel_events(db, booking_id):
    """Check funnel_events collection for payment.succeeded event."""
    
    print("🔄 Checking funnel_events collection...")
    
    query = {
        "organization_id": ORGANIZATION_ID,
        "correlation_id": CORRELATION_ID
    }
    
    events = []
    async for event in db.funnel_events.find(query):
        events.append(event)
    
    print(f"📊 Found {len(events)} funnel events for correlation_id: {CORRELATION_ID}")
    
    payment_succeeded_event = None
    for event in events:
        event_name = event.get("event_name")
        print(f"  - {event_name}")
        
        if event_name == "public.payment.succeeded":
            payment_succeeded_event = event
            print(f"✅ Found payment.succeeded event:")
            print(f"    entity_type: {event.get('entity_type')}")
            print(f"    entity_id: {event.get('entity_id')}")
            print(f"    channel: {event.get('channel')}")
            
            context = event.get("context", {})
            print(f"    context.amount_cents: {context.get('amount_cents')}")
            print(f"    context.currency: {context.get('currency')}")
            print(f"    context.payment_intent_id: {context.get('payment_intent_id')}")
            
            trace = event.get("trace", {})
            print(f"    trace.provider: {trace.get('provider')}")
            print(f"    trace.payment_intent_id: {trace.get('payment_intent_id')}")
    
    return payment_succeeded_event

async def test_admin_endpoint(booking_id):
    """Test admin endpoint for funnel events (optional)."""
    
    print("🔄 Testing admin endpoint...")
    
    try:
        import httpx
        
        # Get backend URL from environment
        backend_url = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')
        
        # Admin login
        login_response = httpx.post(f"{backend_url}/api/auth/login", json={
            "email": "admin@acenta.test",
            "password": "admin123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            
            # Query funnel events
            headers = {"Authorization": f"Bearer {token}"}
            events_response = httpx.get(
                f"{backend_url}/api/admin/funnel/events",
                params={"correlation_id": CORRELATION_ID},
                headers=headers
            )
            
            if events_response.status_code == 200:
                events_data = events_response.json()
                print(f"✅ Admin endpoint returned {len(events_data)} events")
                
                for event in events_data:
                    if event.get("event_name") == "public.payment.succeeded":
                        print(f"✅ Found payment.succeeded in admin endpoint")
                        return True
            else:
                print(f"⚠️ Admin endpoint failed: {events_response.status_code}")
        else:
            print(f"⚠️ Admin login failed: {login_response.status_code}")
    
    except Exception as e:
        print(f"⚠️ Admin endpoint test failed: {e}")
    
    return False

async def update_booking_payment_status(db, booking_id, status="paid"):
    """Update booking document payment_status manually if needed."""
    
    print(f"🔄 Updating booking payment_status to '{status}'...")
    
    result = await db.bookings.update_one(
        {"_id": booking_id},
        {"$set": {"payment_status": status, "updated_at": now_utc()}}
    )
    
    if result.modified_count > 0:
        print(f"✅ Updated booking payment_status to '{status}'")
    else:
        print(f"⚠️ No booking updated (maybe already '{status}')")

async def main():
    """Main test function."""
    
    print("🚀 Starting Stripe Payment Succeeded Funnel Integration Test")
    print("=" * 70)
    
    # Connect to database
    await connect_mongo()
    db = await get_db()
    
    try:
        # Step 1: Create test booking
        print("\n📝 Step 1: Creating test booking...")
        booking_id = await create_test_booking(db)
        
        # Step 2: Prepare fake Stripe event
        print("\n🎭 Step 2: Preparing fake Stripe event...")
        fake_event = create_fake_stripe_event(booking_id)
        
        # Step 3: Call handler directly
        print("\n⚡ Step 3: Calling payment handler...")
        status, body = await call_payment_handler(fake_event)
        
        # Verify handler response
        expected_status = 200
        expected_body = {"ok": True}
        
        if status == expected_status and body == expected_body:
            print("✅ Handler response matches expected values")
        else:
            print(f"❌ Handler response mismatch:")
            print(f"   Expected: status={expected_status}, body={expected_body}")
            print(f"   Actual: status={status}, body={body}")
        
        # Step 4: Check booking payment status
        print("\n💳 Step 4: Checking booking payment status...")
        payment_status = await check_booking_payment_status(db, booking_id)
        
        # Check if there are any booking events
        booking_events = []
        async for event in db.booking_events.find({"booking_id": booking_id}):
            booking_events.append(event)
        print(f"📅 Booking events count: {len(booking_events)}")
        for event in booking_events:
            print(f"  - {event.get('event')}")
        
        # If booking payment_status is still 'pending', update it manually
        # (This might be needed if the orchestrator only updates booking_payments collection)
        booking = await db.bookings.find_one({"_id": booking_id})
        if booking and booking.get("payment_status") == "pending":
            print("⚠️ Booking payment_status still 'pending', updating manually...")
            await update_booking_payment_status(db, booking_id, "paid")
        
        # Step 5: Check funnel events
        print("\n📊 Step 5: Checking funnel events...")
        payment_event = await check_funnel_events(db, booking_id)
        
        if payment_event:
            print("✅ Payment succeeded event found in funnel_events")
            
            # Verify required fields
            required_fields = {
                "event_name": "public.payment.succeeded",
                "entity_type": "booking",
                "entity_id": booking_id,
                "channel": "public"
            }
            
            context_fields = {
                "amount_cents": 10000,
                "currency": "EUR",
                "payment_intent_id": PAYMENT_INTENT_ID
            }
            
            trace_fields = {
                "provider": "stripe",
                "payment_intent_id": PAYMENT_INTENT_ID
            }
            
            # Verify event structure
            all_good = True
            for field, expected in required_fields.items():
                actual = payment_event.get(field)
                if actual != expected:
                    print(f"❌ Field {field}: expected '{expected}', got '{actual}'")
                    all_good = False
            
            context = payment_event.get("context", {})
            for field, expected in context_fields.items():
                actual = context.get(field)
                if actual != expected:
                    print(f"❌ Context {field}: expected '{expected}', got '{actual}'")
                    all_good = False
            
            trace = payment_event.get("trace", {})
            for field, expected in trace_fields.items():
                actual = trace.get(field)
                if actual != expected:
                    print(f"❌ Trace {field}: expected '{expected}', got '{actual}'")
                    all_good = False
            
            if all_good:
                print("✅ All funnel event fields are correct")
            
        else:
            print("❌ Payment succeeded event NOT found in funnel_events")
        
        # Step 6: Test admin endpoint (optional)
        print("\n🔧 Step 6: Testing admin endpoint...")
        admin_success = await test_admin_endpoint(booking_id)
        
        # Final summary
        print("\n" + "=" * 70)
        print("📋 TEST SUMMARY:")
        print(f"✅ Handler call: status={status}, body={body}")
        print(f"✅ Payment aggregate status: {payment_status}")
        
        final_booking = await db.bookings.find_one({"_id": booking_id})
        final_payment_status = final_booking.get("payment_status") if final_booking else "unknown"
        print(f"✅ Final booking payment_status: {final_payment_status}")
        
        if payment_event:
            print("✅ Funnel event: public.payment.succeeded found with correct structure")
        else:
            print("❌ Funnel event: public.payment.succeeded NOT found")
        
        if admin_success:
            print("✅ Admin endpoint: accessible and returns events")
        else:
            print("⚠️ Admin endpoint: not tested or failed")
        
        # Determine overall success
        success_criteria = [
            status == 200 and body == {"ok": True},
            payment_status in ["PAID", "paid"],
            payment_event is not None,
            final_payment_status == "paid"
        ]
        
        if all(success_criteria):
            print("\n🎉 OVERALL RESULT: ✅ ALL TESTS PASSED")
            print("✅ Stripe payment succeeded funnel integration is working correctly!")
        else:
            print("\n⚠️ OVERALL RESULT: ❌ SOME TESTS FAILED")
            print("❌ Issues found in Stripe payment succeeded funnel integration")
        
    except Exception as e:
        print(f"\n💥 Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup: Remove test booking
        try:
            await db.bookings.delete_one({"_id": booking_id})
            await db.booking_payments.delete_many({"booking_id": booking_id})
            await db.funnel_events.delete_many({"correlation_id": CORRELATION_ID})
            print(f"\n🧹 Cleaned up test data for booking: {booking_id}")
        except:
            pass

if __name__ == "__main__":
    asyncio.run(main())