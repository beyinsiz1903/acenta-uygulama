#!/usr/bin/env python3
"""
Document Vault Audit & Events Testing

This test suite verifies the document upload/delete audit logging and booking events
for the Document Vault functionality in refund cases.

Test Scenarios:
1. Upload a document for an existing refund case
2. Check audit_logs for document_upload action
3. Check booking_events for DOCUMENT_UPLOADED event
4. Delete the document
5. Check audit_logs for document_delete action
6. Check booking_events for DOCUMENT_DELETED event
7. Verify counts in both collections
"""

import requests
import json
import uuid
import os
import io
from datetime import datetime, timedelta
from pymongo import MongoClient
from typing import Dict, Any, Optional

# Configuration - Use production URL from frontend/.env
BASE_URL = "https://bayi-platform.preview.emergentagent.com"

def get_mongo_client():
    """Get MongoDB client for direct database access"""
    # Use the same MongoDB URL as backend
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017/test_database")
    return MongoClient(mongo_url)

def login_admin():
    """Login as admin user and return token, org_id, email"""
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
    )
    assert r.status_code == 200, f"Admin login failed: {r.text}"
    data = r.json()
    user = data["user"]
    return data["access_token"], user["organization_id"], user["email"]

def find_existing_refund_case(admin_headers: Dict[str, str], org_id: str) -> Optional[Dict[str, Any]]:
    """Find an existing refund case or create one if none exists"""
    print("   🔍 Looking for existing refund case...")
    
    # Try to get existing refund cases
    r = requests.get(
        f"{BASE_URL}/api/ops/finance/refunds",
        headers=admin_headers,
        params={"limit": 10}
    )
    
    if r.status_code == 200:
        data = r.json()
        cases = data.get("items", [])
        
        # Look for a case in 'open' status
        for case in cases:
            if case.get("status") == "open" and case.get("booking_id"):
                print(f"   ✅ Found existing refund case: {case['id']} (booking: {case['booking_id']})")
                return case
    
    # If no suitable case found, create one
    print("   📝 No suitable refund case found, creating one...")
    return create_refund_case(admin_headers, org_id)

def create_refund_case(admin_headers: Dict[str, str], org_id: str) -> Dict[str, Any]:
    """Create a refund case for testing"""
    # First, find an existing booking
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    # Look for an existing booking
    booking = db.bookings.find_one({"organization_id": org_id})
    
    if not booking:
        # Create a minimal booking for testing
        from bson import ObjectId
        booking_id = ObjectId()
        now = datetime.utcnow()
        
        booking_doc = {
            "_id": booking_id,
            "organization_id": org_id,
            "booking_code": f"TEST-{uuid.uuid4().hex[:8].upper()}",
            "status": "confirmed",
            "created_at": now,
            "updated_at": now,
            "guest": {
                "full_name": "Test Guest",
                "email": "test@example.com"
            },
            "total_amount": 500.0,
            "currency": "EUR"
        }
        db.bookings.insert_one(booking_doc)
        booking_id = str(booking_id)
        print(f"   ✅ Created test booking: {booking_id}")
    else:
        booking_id = str(booking["_id"])
        print(f"   ✅ Using existing booking: {booking_id}")
    
    mongo_client.close()
    
    # Create refund case via API
    refund_payload = {
        "booking_id": booking_id,
        "type": "full_refund",
        "requested_amount": 450.0,
        "currency": "EUR",
        "reason": "audit_test_case",
        "guest_note": "Test refund case for document audit testing"
    }
    
    r = requests.post(
        f"{BASE_URL}/api/ops/finance/refunds",
        headers=admin_headers,
        json=refund_payload
    )
    
    if r.status_code == 200:
        case = r.json()
        print(f"   ✅ Created refund case: {case['id']} (booking: {booking_id})")
        return case
    else:
        print(f"   ❌ Failed to create refund case: {r.status_code} - {r.text}")
        raise Exception(f"Failed to create refund case: {r.status_code} - {r.text}")

def upload_document(admin_headers: Dict[str, str], case_id: str) -> Dict[str, Any]:
    """Upload a document to a refund case"""
    print(f"   📤 Uploading document to refund case: {case_id}")
    
    # Create a small test file
    test_content = b"This is a test document for audit hardening test"
    test_file = io.BytesIO(test_content)
    
    files = {
        'file': ('audit_test_document.txt', test_file, 'text/plain')
    }
    
    data = {
        'entity_type': 'refund_case',
        'entity_id': case_id,
        'tag': 'refund_proof',
        'note': 'audit_hardening_test'
    }
    
    r = requests.post(
        f"{BASE_URL}/api/ops/documents/upload",
        headers=admin_headers,
        files=files,
        data=data
    )
    
    assert r.status_code == 200, f"Document upload failed: {r.status_code} - {r.text}"
    
    doc_data = r.json()
    print(f"   ✅ Document uploaded: {doc_data['document_id']}")
    print(f"   📋 Filename: {doc_data['filename']}")
    print(f"   📋 Tag: {doc_data['tag']}")
    print(f"   📋 Size: {doc_data['size_bytes']} bytes")
    
    return doc_data

def delete_document(admin_headers: Dict[str, str], document_id: str) -> Dict[str, Any]:
    """Delete a document"""
    print(f"   🗑️  Deleting document: {document_id}")
    
    payload = {
        "reason": "audit_delete_test"
    }
    
    r = requests.delete(
        f"{BASE_URL}/api/ops/documents/{document_id}",
        headers=admin_headers,
        json=payload
    )
    
    assert r.status_code == 200, f"Document delete failed: {r.status_code} - {r.text}"
    
    result = r.json()
    print(f"   ✅ Document deleted successfully")
    
    return result

def check_audit_logs(org_id: str, action: str, target_id: str) -> Dict[str, Any]:
    """Check audit logs for specific action and target"""
    print(f"   🔍 Checking audit_logs for action='{action}', target.id='{target_id}'")
    
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    # Query audit logs
    query = {
        "organization_id": org_id,
        "action": action,
        "target.id": target_id
    }
    
    audit_logs = list(db.audit_logs.find(query).sort("created_at", -1).limit(5))
    mongo_client.close()
    
    if audit_logs:
        log = audit_logs[0]  # Get the most recent one
        print(f"   ✅ Found audit log: {log['_id']}")
        print(f"   📋 Action: {log['action']}")
        print(f"   📋 Target type: {log['target']['type']}")
        print(f"   📋 Target id: {log['target']['id']}")
        
        if 'meta' in log:
            meta = log['meta']
            print(f"   📋 Meta entity_type: {meta.get('entity_type')}")
            print(f"   📋 Meta entity_id: {meta.get('entity_id')}")
            print(f"   📋 Meta filename: {meta.get('filename')}")
            if action == "document_delete":
                print(f"   📋 Meta reason: {meta.get('reason')}")
        
        return log
    else:
        print(f"   ❌ No audit log found for action='{action}', target.id='{target_id}'")
        return None

def check_booking_events(org_id: str, booking_id: str, event_type: str) -> Dict[str, Any]:
    """Check booking events for specific event type"""
    print(f"   🔍 Checking booking_events for booking_id='{booking_id}', event='{event_type}'")
    
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    # Query booking events
    query = {
        "organization_id": org_id,
        "booking_id": booking_id,
        "event": event_type
    }
    
    events = list(db.booking_events.find(query).sort("created_at", -1).limit(5))
    mongo_client.close()
    
    if events:
        event = events[0]  # Get the most recent one
        print(f"   ✅ Found booking event: {event['_id']}")
        print(f"   📋 Event: {event['event']}")
        print(f"   📋 Booking ID: {event['booking_id']}")
        
        if 'meta' in event:
            meta = event['meta']
            print(f"   📋 Meta entity_type: {meta.get('entity_type')}")
            print(f"   📋 Meta entity_id: {meta.get('entity_id')}")
            print(f"   📋 Meta document_id: {meta.get('document_id')}")
            print(f"   📋 Meta filename: {meta.get('filename')}")
            print(f"   📋 Meta tag: {meta.get('tag')}")
            print(f"   📋 Meta by_email: {meta.get('by_email')}")
            if event_type == "DOCUMENT_DELETED":
                print(f"   📋 Meta reason: {meta.get('reason')}")
        
        return event
    else:
        print(f"   ❌ No booking event found for booking_id='{booking_id}', event='{event_type}'")
        return None

def verify_counts(org_id: str) -> Dict[str, int]:
    """Verify counts in audit_logs and booking_events collections"""
    print("   📊 Verifying document audit/event counts...")
    
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    # Count audit logs
    upload_audit_count = db.audit_logs.count_documents({
        "organization_id": org_id,
        "action": "document_upload"
    })
    
    delete_audit_count = db.audit_logs.count_documents({
        "organization_id": org_id,
        "action": "document_delete"
    })
    
    # Count booking events
    upload_event_count = db.booking_events.count_documents({
        "organization_id": org_id,
        "event": "DOCUMENT_UPLOADED"
    })
    
    delete_event_count = db.booking_events.count_documents({
        "organization_id": org_id,
        "event": "DOCUMENT_DELETED"
    })
    
    mongo_client.close()
    
    counts = {
        "upload_audit_count": upload_audit_count,
        "delete_audit_count": delete_audit_count,
        "upload_event_count": upload_event_count,
        "delete_event_count": delete_event_count
    }
    
    print(f"   📋 Document upload audit logs: {upload_audit_count}")
    print(f"   📋 Document delete audit logs: {delete_audit_count}")
    print(f"   📋 Document upload events: {upload_event_count}")
    print(f"   📋 Document delete events: {delete_event_count}")
    
    return counts

def test_document_vault_audit_events():
    """Test complete document vault audit & events flow"""
    print("\n" + "=" * 80)
    print("DOCUMENT VAULT AUDIT & EVENTS TEST")
    print("Testing document upload/delete audit logging and booking events")
    print("=" * 80 + "\n")
    
    # Setup
    admin_token, org_id, admin_email = login_admin()
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    print(f"📋 Organization: {org_id}")
    print(f"📋 Admin user: {admin_email}")
    
    try:
        # 1. Find or create a refund case
        print("\n1️⃣  Finding/creating refund case...")
        refund_case = find_existing_refund_case(admin_headers, org_id)
        case_id = refund_case["id"]
        booking_id = refund_case["booking_id"]
        
        print(f"   📋 Using refund case: {case_id}")
        print(f"   📋 Associated booking: {booking_id}")
        
        # 2. Upload a document
        print("\n2️⃣  Uploading document...")
        doc_data = upload_document(admin_headers, case_id)
        document_id = doc_data["document_id"]
        filename = doc_data["filename"]
        
        # 3. Check audit logs for upload
        print("\n3️⃣  Checking audit logs for document upload...")
        upload_audit = check_audit_logs(org_id, "document_upload", document_id)
        
        if upload_audit:
            # Verify audit log structure
            assert upload_audit["target"]["type"] == "document", "Target type should be 'document'"
            assert upload_audit["meta"]["entity_type"] == "refund_case", "Meta entity_type should be 'refund_case'"
            assert upload_audit["meta"]["entity_id"] == case_id, f"Meta entity_id should be '{case_id}'"
            assert upload_audit["meta"]["filename"] == filename, f"Meta filename should be '{filename}'"
            print("   ✅ Upload audit log structure verified")
        else:
            print("   ❌ Upload audit log not found")
            
        # 4. Check booking events for upload
        print("\n4️⃣  Checking booking events for document upload...")
        upload_event = check_booking_events(org_id, booking_id, "DOCUMENT_UPLOADED")
        
        if upload_event:
            # Verify event structure
            assert upload_event["meta"]["entity_type"] == "refund_case", "Meta entity_type should be 'refund_case'"
            assert upload_event["meta"]["entity_id"] == case_id, f"Meta entity_id should be '{case_id}'"
            assert upload_event["meta"]["document_id"] == document_id, f"Meta document_id should be '{document_id}'"
            assert upload_event["meta"]["filename"] == filename, f"Meta filename should be '{filename}'"
            assert upload_event["meta"]["tag"] == "refund_proof", "Meta tag should be 'refund_proof'"
            assert upload_event["meta"]["by_email"] == admin_email, f"Meta by_email should be '{admin_email}'"
            print("   ✅ Upload event structure verified")
        else:
            print("   ❌ Upload event not found")
        
        # 5. Delete the document
        print("\n5️⃣  Deleting document...")
        delete_result = delete_document(admin_headers, document_id)
        
        # 6. Check audit logs for delete
        print("\n6️⃣  Checking audit logs for document delete...")
        delete_audit = check_audit_logs(org_id, "document_delete", document_id)
        
        if delete_audit:
            # Verify audit log structure
            assert delete_audit["target"]["type"] == "document", "Target type should be 'document'"
            assert delete_audit["meta"]["reason"] == "audit_delete_test", "Meta reason should be 'audit_delete_test'"
            assert delete_audit["meta"]["filename"] == filename, f"Meta filename should be '{filename}'"
            print("   ✅ Delete audit log structure verified")
        else:
            print("   ❌ Delete audit log not found")
        
        # 7. Check booking events for delete
        print("\n7️⃣  Checking booking events for document delete...")
        delete_event = check_booking_events(org_id, booking_id, "DOCUMENT_DELETED")
        
        if delete_event:
            # Verify event structure
            assert delete_event["meta"]["entity_type"] == "refund_case", "Meta entity_type should be 'refund_case'"
            assert delete_event["meta"]["entity_id"] == case_id, f"Meta entity_id should be '{case_id}'"
            assert delete_event["meta"]["document_id"] == document_id, f"Meta document_id should be '{document_id}'"
            assert delete_event["meta"]["filename"] == filename, f"Meta filename should be '{filename}'"
            assert delete_event["meta"]["tag"] == "refund_proof", "Meta tag should be 'refund_proof'"
            assert delete_event["meta"]["reason"] == "audit_delete_test", "Meta reason should be 'audit_delete_test'"
            assert delete_event["meta"]["by_email"] == admin_email, f"Meta by_email should be '{admin_email}'"
            print("   ✅ Delete event structure verified")
        else:
            print("   ❌ Delete event not found")
        
        # 8. Verify counts
        print("\n8️⃣  Verifying final counts...")
        counts = verify_counts(org_id)
        
        # Verify minimum counts
        assert counts["upload_audit_count"] > 0, "Should have at least one document upload audit log"
        assert counts["delete_audit_count"] > 0, "Should have at least one document delete audit log"
        assert counts["upload_event_count"] > 0, "Should have at least one document upload event"
        assert counts["delete_event_count"] > 0, "Should have at least one document delete event"
        
        print("   ✅ All counts verified")
        
        # Summary
        print("\n" + "=" * 80)
        print("TEST RESULTS SUMMARY")
        print("=" * 80)
        
        results = {
            "upload_audit_found": upload_audit is not None,
            "upload_event_found": upload_event is not None,
            "delete_audit_found": delete_audit is not None,
            "delete_event_found": delete_event is not None,
            "counts_verified": True
        }
        
        success_count = sum(results.values())
        total_checks = len(results)
        
        print(f"✅ Upload audit log: {'PASS' if results['upload_audit_found'] else 'FAIL'}")
        print(f"✅ Upload booking event: {'PASS' if results['upload_event_found'] else 'FAIL'}")
        print(f"✅ Delete audit log: {'PASS' if results['delete_audit_found'] else 'FAIL'}")
        print(f"✅ Delete booking event: {'PASS' if results['delete_event_found'] else 'FAIL'}")
        print(f"✅ Counts verification: {'PASS' if results['counts_verified'] else 'FAIL'}")
        
        print(f"\n📊 Overall: {success_count}/{total_checks} checks passed")
        
        if success_count == total_checks:
            print("🎉 ALL TESTS PASSED! Document Vault audit & events working correctly.")
            return True
        else:
            print(f"⚠️  {total_checks - success_count} check(s) failed.")
            return False
            
    except Exception as e:
        print(f"\n❌ TEST FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_test():
    """Run the document vault audit & events test"""
    print("\n" + "🚀" * 80)
    print("DOCUMENT VAULT AUDIT & EVENTS VERIFICATION")
    print("Testing audit logging and booking events for document upload/delete")
    print("🚀" * 80)
    
    success = test_document_vault_audit_events()
    
    print("\n" + "🏁" * 80)
    print("FINAL RESULT")
    print("🏁" * 80)
    
    if success:
        print("✅ Document Vault audit & events test PASSED")
    else:
        print("❌ Document Vault audit & events test FAILED")
    
    return success

if __name__ == "__main__":
    success = run_test()
    exit(0 if success else 1)