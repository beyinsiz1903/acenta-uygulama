#!/usr/bin/env python3
"""
Stripe Payment Succeeded Funnel Integration Test - No Channel Metadata

Test scenario for when channel metadata is missing:
- Should default to 'public.payment.succeeded' event
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
CORRELATION_ID = "fc_test_payment_no_channel_01"

# Generate unique IDs for each test run
import time
PAYMENT_INTENT_ID = f"pi_test_no_channel_{int(time.time())}"
EVENT_ID = f"evt_test_no_channel_{int(time.time())}"

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

def create_fake_stripe_event_no_channel(booking_id):
    """Create a fake Stripe payment_intent.succeeded event payload WITHOUT channel metadata."""
    
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
                    "payment_id": PAYMENT_INTENT_ID
                    # NOTE: No "channel" metadata - should default to "public"
                }
            }
        }
    }
    
    print(f"✅ Created fake Stripe event WITHOUT channel: {EVENT_ID}")
    return fake_event

async def check_funnel_events_no_channel(db, booking_id):
    """Check funnel_events collection for payment.succeeded event with default channel."""
    
    print("🔄 Checking funnel_events collection for default channel...")
    
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
            print(f"✅ Found payment.succeeded event (default channel):")
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

async def main():
    """Main test function for no channel metadata scenario."""
    
    print("🚀 Starting Stripe Payment Succeeded Funnel Integration Test - No Channel Metadata")
    print("=" * 80)
    
    # Connect to database
    await connect_mongo()
    db = await get_db()
    
    try:
        # Step 1: Create test booking
        print("\n📝 Step 1: Creating test booking...")
        booking_id = await create_test_booking(db)
        
        # Step 2: Prepare fake Stripe event WITHOUT channel metadata
        print("\n🎭 Step 2: Preparing fake Stripe event WITHOUT channel...")
        fake_event = create_fake_stripe_event_no_channel(booking_id)
        
        # Step 3: Call handler directly
        print("\n⚡ Step 3: Calling payment handler...")
        status, body = await _handle_payment_intent_succeeded(fake_event)
        print(f"✅ Handler response: status={status}, body={body}")
        
        # Verify handler response
        expected_status = 200
        expected_body = {"ok": True}
        
        if status == expected_status and body == expected_body:
            print("✅ Handler response matches expected values")
        else:
            print(f"❌ Handler response mismatch:")
            print(f"   Expected: status={expected_status}, body={expected_body}")
            print(f"   Actual: status={status}, body={body}")
        
        # Step 4: Check funnel events for default channel
        print("\n📊 Step 4: Checking funnel events for default channel...")
        payment_event = await check_funnel_events_no_channel(db, booking_id)
        
        if payment_event:
            print("✅ Payment succeeded event found in funnel_events")
            
            # Verify required fields for default channel
            required_fields = {
                "event_name": "public.payment.succeeded",
                "entity_type": "booking",
                "entity_id": booking_id,
                "channel": "public"  # Should default to "public"
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
                print("✅ All funnel event fields are correct (default channel)")
            
        else:
            print("❌ Payment succeeded event NOT found in funnel_events")
        
        # Final summary
        print("\n" + "=" * 80)
        print("📋 TEST SUMMARY (No Channel Metadata):")
        print(f"✅ Handler call: status={status}, body={body}")
        
        if payment_event:
            channel = payment_event.get("channel")
            event_name = payment_event.get("event_name")
            print(f"✅ Funnel event: {event_name} found with channel='{channel}'")
        else:
            print("❌ Funnel event: public.payment.succeeded NOT found")
        
        # Determine overall success
        success_criteria = [
            status == 200 and body == {"ok": True},
            payment_event is not None,
            payment_event.get("channel") == "public" if payment_event else False,
            payment_event.get("event_name") == "public.payment.succeeded" if payment_event else False
        ]
        
        if all(success_criteria):
            print("\n🎉 OVERALL RESULT: ✅ ALL TESTS PASSED")
            print("✅ Default channel behavior working correctly - defaults to 'public.payment.succeeded'!")
        else:
            print("\n⚠️ OVERALL RESULT: ❌ SOME TESTS FAILED")
            print("❌ Issues found in default channel behavior")
        
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