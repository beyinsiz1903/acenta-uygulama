#!/usr/bin/env python3
"""
Test the build_booking_public_view function directly
"""
import sys
import os
sys.path.append('/app/backend')

from app.utils import build_booking_public_view
from datetime import datetime, timezone

def test_build_booking_public_view():
    """Test the build_booking_public_view function with mock data"""
    print("🔍 Testing build_booking_public_view function...")
    
    # Create a mock booking document (similar to what would be in MongoDB)
    mock_booking = {
        "_id": "bkg_test123456789",
        "organization_id": "org_demo",
        "agency_id": "9876ff5c-de12-44cc-85ca-d612ced359b1",
        "hotel_id": "ab0b4cf1-87c1-476e-8b51-124cf9b86e62",
        "hotel_name": "Demo Hotel 1",
        "agency_name": "Demo Acente A",
        "status": "confirmed",
        "stay": {
            "check_in": "2026-03-10",
            "check_out": "2026-03-12",
            "nights": 2
        },
        "occupancy": {
            "adults": 2,
            "children": 0
        },
        "guest": {
            "full_name": "Ahmet Yılmaz",
            "email": "ahmet.yilmaz@example.com",
            "phone": "+905551234567"
        },
        "rate_snapshot": {
            "room_type_name": "Standard Room",
            "rate_plan_name": "Base Rate",
            "board": "RO",
            "price": {
                "currency": "TRY",
                "total": 4200.0,
                "per_night": 2100.0
            }
        },
        "gross_amount": 4200.0,
        "commission_amount": 420.0,
        "net_amount": 3780.0,
        "currency": "TRY",
        "payment_status": "pending",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "source": "pms"
    }
    
    # Test the function
    try:
        result = build_booking_public_view(mock_booking)
        
        # Check required fields
        required_fields = ['id', 'code', 'status', 'status_tr', 'status_en']
        missing_fields = [f for f in required_fields if f not in result]
        
        if missing_fields:
            print(f"❌ Missing required fields: {missing_fields}")
            return False
        
        print(f"✅ All required fields present: {required_fields}")
        
        # Check status translations
        if result['status'] == 'confirmed':
            print(f"✅ Status correct: {result['status']}")
        else:
            print(f"❌ Status incorrect: {result['status']}")
            return False
            
        if result['status_tr'] == 'Onaylandı':
            print(f"✅ Turkish status correct: {result['status_tr']}")
        else:
            print(f"❌ Turkish status incorrect: {result['status_tr']}")
            return False
            
        if result['status_en'] == 'Confirmed':
            print(f"✅ English status correct: {result['status_en']}")
        else:
            print(f"❌ English status incorrect: {result['status_en']}")
            return False
        
        # Check other fields
        expected_values = {
            'id': 'bkg_test123456789',
            'code': 'bkg_test123456789',
            'hotel_name': 'Demo Hotel 1',
            'guest_name': 'Ahmet Yılmaz',
            'check_in_date': '2026-03-10',
            'check_out_date': '2026-03-12',
            'nights': 2,
            'room_type': 'Standard Room',
            'board_type': 'RO',
            'adults': 2,
            'children': 0,
            'total_amount': 4200.0,
            'currency': 'TRY',
            'source': 'pms',
            'payment_status': 'pending'
        }
        
        for key, expected in expected_values.items():
            actual = result.get(key)
            if actual == expected:
                print(f"✅ {key}: {actual}")
            else:
                print(f"❌ {key}: expected {expected}, got {actual}")
                return False
        
        # Check JSON serializable
        import json
        try:
            json.dumps(result)
            print(f"✅ Result is JSON serializable")
        except Exception as e:
            print(f"❌ Result not JSON serializable: {e}")
            return False
        
        print(f"\n✅ build_booking_public_view function working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Function failed with error: {e}")
        return False

def test_cancelled_booking():
    """Test with cancelled booking"""
    print("\n🔍 Testing build_booking_public_view with cancelled booking...")
    
    mock_booking = {
        "_id": "bkg_cancelled123",
        "status": "cancelled",
        "stay": {
            "check_in": "2026-03-10",
            "check_out": "2026-03-12",
            "nights": 2
        },
        "guest": {
            "full_name": "Mehmet Özkan"
        },
        "hotel_name": "Demo Hotel 2",
        "currency": "TRY"
    }
    
    try:
        result = build_booking_public_view(mock_booking)
        
        if result['status'] == 'cancelled' and result['status_tr'] == 'İptal Edildi' and result['status_en'] == 'Cancelled':
            print(f"✅ Cancelled status translations correct")
            return True
        else:
            print(f"❌ Cancelled status translations incorrect: {result['status']}, {result['status_tr']}, {result['status_en']}")
            return False
            
    except Exception as e:
        print(f"❌ Function failed with error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing FAZ-9.1 build_booking_public_view Function")
    
    success1 = test_build_booking_public_view()
    success2 = test_cancelled_booking()
    
    if success1 and success2:
        print(f"\n✅ ALL TESTS PASSED - build_booking_public_view function is working correctly!")
        sys.exit(0)
    else:
        print(f"\n❌ SOME TESTS FAILED")
        sys.exit(1)