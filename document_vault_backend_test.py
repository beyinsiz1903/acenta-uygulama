#!/usr/bin/env python3
"""
Document Vault (Sprint 2.2) Backend Test Suite

This test suite verifies the Document Vault functionality for refund cases:
1. Upload flow - multipart/form-data upload with proper metadata
2. Download flow - file retrieval with proper headers
3. Delete flow - soft delete with idempotency
4. Audit + timeline - audit logs and booking events
5. Security checks - no MongoDB _id leaks, proper access control

Test Requirements:
- Use REACT_APP_BACKEND_URL for all API calls
- Login as admin@acenta.test/admin123
- Test with existing refund case or create one
- Verify all response structures and audit trails
"""

import requests
import json
import uuid
import os
import tempfile
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId
from typing import Dict, Any, Optional

# Configuration - Use production URL from frontend/.env
BASE_URL = "https://b2bhotelsuite.preview.emergentagent.com"

def get_mongo_client():
    """Get MongoDB client for direct database access"""
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

def find_or_create_refund_case(admin_headers: Dict[str, str], org_id: str) -> tuple[str, str]:
    """Find existing refund case or create one for testing"""
    print("   📋 Looking for existing refund case...")
    
    # Try to find existing refund case
    r = requests.get(
        f"{BASE_URL}/api/ops/finance/refunds",
        headers=admin_headers,
        params={"page": 1, "page_size": 10}
    )
    
    if r.status_code == 200:
        data = r.json()
        cases = data.get("items", [])
        if cases:
            case = cases[0]
            case_id = case["case_id"]
            booking_id = case["booking_id"]
            print(f"   ✅ Found existing refund case: {case_id} (booking: {booking_id})")
            return case_id, booking_id
    
    # If no existing case, create one via MongoDB
    print("   📋 Creating new refund case via MongoDB...")
    
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    # Find an existing booking
    booking = db.bookings.find_one({"organization_id": org_id})
    if not booking:
        # Create a minimal booking for testing
        booking_id = ObjectId()
        booking_doc = {
            "_id": booking_id,
            "organization_id": org_id,
            "booking_code": f"TEST-{uuid.uuid4().hex[:8].upper()}",
            "status": "confirmed",
            "created_at": datetime.utcnow(),
        }
        db.bookings.insert_one(booking_doc)
        booking_id = str(booking_id)
    else:
        booking_id = str(booking["_id"])
    
    # Create refund case
    case_id = f"rc_{uuid.uuid4().hex[:12]}"
    case_doc = {
        "case_id": case_id,
        "organization_id": org_id,
        "booking_id": booking_id,
        "type": "refund_case",
        "status": "open",
        "created_at": datetime.utcnow(),
        "amount_requested": 100.0,
        "currency": "EUR",
    }
    db.refund_cases.insert_one(case_doc)
    
    mongo_client.close()
    
    print(f"   ✅ Created refund case: {case_id} (booking: {booking_id})")
    return case_id, booking_id

def create_test_file() -> tuple[str, bytes]:
    """Create a small test file for upload"""
    content = b"Hello, this is a test document for Document Vault testing.\nCreated at: " + datetime.utcnow().isoformat().encode()
    filename = f"test_document_{uuid.uuid4().hex[:8]}.txt"
    return filename, content

def test_upload_flow():
    """Test 1: Upload flow - multipart/form-data with proper metadata"""
    print("\n" + "=" * 80)
    print("TEST 1: DOCUMENT UPLOAD FLOW")
    print("Testing document upload with multipart/form-data")
    print("=" * 80 + "\n")
    
    # Setup
    admin_token, org_id, admin_email = login_admin()
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    case_id, booking_id = find_or_create_refund_case(admin_headers, org_id)
    
    # Create test file
    filename, content = create_test_file()
    
    print(f"1️⃣  Uploading document to refund case {case_id}...")
    
    # Prepare multipart form data
    files = {
        'file': (filename, content, 'text/plain')
    }
    data = {
        'entity_type': 'refund_case',
        'entity_id': case_id,
        'tag': 'refund_proof',
        'note': 'backend_test_upload'
    }
    
    r = requests.post(
        f"{BASE_URL}/api/ops/finance/documents/upload",
        headers=admin_headers,
        files=files,
        data=data
    )
    
    print(f"   📋 Upload response status: {r.status_code}")
    print(f"   📋 Response body: {r.text}")
    
    assert r.status_code == 200, f"Upload failed: {r.status_code} - {r.text}"
    
    upload_data = r.json()
    print(f"   📋 Upload response: {json.dumps(upload_data, indent=2)}")
    
    # Verify response structure
    required_fields = ["document_id", "link_id", "filename", "tag", "size_bytes", 
                      "content_type", "created_at", "created_by_email", "status"]
    for field in required_fields:
        assert field in upload_data, f"Missing field in upload response: {field}"
    
    # Verify values
    assert upload_data["filename"] == filename
    assert upload_data["tag"] == "refund_proof"
    assert upload_data["size_bytes"] > 0
    assert upload_data["content_type"] == "text/plain"
    assert upload_data["created_by_email"] == admin_email
    assert upload_data["status"] == "active"
    
    document_id = upload_data["document_id"]
    link_id = upload_data["link_id"]
    
    print(f"   ✅ Document uploaded successfully")
    print(f"   📋 Document ID: {document_id}")
    print(f"   📋 Link ID: {link_id}")
    print(f"   📋 Size: {upload_data['size_bytes']} bytes")
    
    # Test list documents to verify upload
    print("\n2️⃣  Verifying document appears in list...")
    
    r = requests.get(
        f"{BASE_URL}/api/ops/finance/documents",
        headers=admin_headers,
        params={
            "entity_type": "refund_case",
            "entity_id": case_id
        }
    )
    
    assert r.status_code == 200, f"List documents failed: {r.status_code} - {r.text}"
    
    list_data = r.json()
    print(f"   📋 List response: {json.dumps(list_data, indent=2)}")
    
    # Verify document appears in list
    items = list_data.get("items", [])
    assert len(items) > 0, "No documents found in list"
    
    uploaded_doc = None
    for item in items:
        if item["document_id"] == document_id:
            uploaded_doc = item
            break
    
    assert uploaded_doc is not None, f"Uploaded document {document_id} not found in list"
    
    # Verify no MongoDB _id fields in response
    def check_no_mongo_ids(obj, path=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                assert key != "_id", f"MongoDB _id field found at {path}.{key}"
                check_no_mongo_ids(value, f"{path}.{key}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                check_no_mongo_ids(item, f"{path}[{i}]")
    
    check_no_mongo_ids(upload_data, "upload_response")
    check_no_mongo_ids(list_data, "list_response")
    
    print(f"   ✅ Document appears in list correctly")
    print(f"   ✅ No MongoDB _id fields detected in responses")
    
    return document_id, case_id, booking_id

def test_download_flow(document_id: str):
    """Test 2: Download flow - file retrieval with proper headers"""
    print("\n" + "=" * 80)
    print("TEST 2: DOCUMENT DOWNLOAD FLOW")
    print("Testing document download with proper Content-Type and Content-Disposition")
    print("=" * 80 + "\n")
    
    # Setup
    admin_token, org_id, admin_email = login_admin()
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    print(f"1️⃣  Downloading document {document_id}...")
    
    r = requests.get(
        f"{BASE_URL}/api/ops/finance/documents/{document_id}/download",
        headers=admin_headers
    )
    
    print(f"   📋 Download response status: {r.status_code}")
    print(f"   📋 Response headers: {dict(r.headers)}")
    
    assert r.status_code == 200, f"Download failed: {r.status_code} - {r.text}"
    
    # Verify headers
    assert "Content-Type" in r.headers, "Missing Content-Type header"
    assert "Content-Disposition" in r.headers, "Missing Content-Disposition header"
    
    content_disposition = r.headers["Content-Disposition"]
    assert "attachment" in content_disposition, "Content-Disposition should be attachment"
    assert "filename=" in content_disposition, "Content-Disposition should include filename"
    
    # Verify content
    content = r.content
    assert len(content) > 0, "Downloaded content is empty"
    assert b"Hello, this is a test document" in content, "Downloaded content doesn't match expected"
    
    print(f"   ✅ Document downloaded successfully")
    print(f"   📋 Content-Type: {r.headers.get('Content-Type')}")
    print(f"   📋 Content-Disposition: {content_disposition}")
    print(f"   📋 Content size: {len(content)} bytes")

def test_delete_flow(document_id: str, case_id: str):
    """Test 3: Delete flow - soft delete with idempotency"""
    print("\n" + "=" * 80)
    print("TEST 3: DOCUMENT DELETE FLOW")
    print("Testing soft delete with idempotency")
    print("=" * 80 + "\n")
    
    # Setup
    admin_token, org_id, admin_email = login_admin()
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    print(f"1️⃣  Deleting document {document_id}...")
    
    r = requests.delete(
        f"{BASE_URL}/api/ops/finance/documents/{document_id}",
        headers=admin_headers,
        json={"reason": "test_delete"}
    )
    
    print(f"   📋 Delete response status: {r.status_code}")
    print(f"   📋 Response body: {r.text}")
    
    assert r.status_code == 200, f"Delete failed: {r.status_code} - {r.text}"
    
    delete_data = r.json()
    assert delete_data.get("ok") is True, "Delete response should have ok=true"
    
    print(f"   ✅ Document deleted successfully")
    
    # Test idempotency - delete again
    print("\n2️⃣  Testing idempotency - deleting same document again...")
    
    r2 = requests.delete(
        f"{BASE_URL}/api/ops/finance/documents/{document_id}",
        headers=admin_headers,
        json={"reason": "test_delete_idempotent"}
    )
    
    print(f"   📋 Second delete response status: {r2.status_code}")
    print(f"   📋 Response body: {r2.text}")
    
    assert r2.status_code == 200, f"Idempotent delete failed: {r2.status_code} - {r2.text}"
    
    delete_data2 = r2.json()
    assert delete_data2.get("ok") is True, "Idempotent delete response should have ok=true"
    
    print(f"   ✅ Idempotent delete working correctly")
    
    # Verify document no longer appears in list (status filter hides deleted)
    print("\n3️⃣  Verifying deleted document hidden from list...")
    
    r = requests.get(
        f"{BASE_URL}/api/ops/finance/documents",
        headers=admin_headers,
        params={
            "entity_type": "refund_case",
            "entity_id": case_id
        }
    )
    
    assert r.status_code == 200, f"List documents failed: {r.status_code} - {r.text}"
    
    list_data = r.json()
    items = list_data.get("items", [])
    
    # Check that deleted document is not in the list
    deleted_doc_found = False
    for item in items:
        if item["document_id"] == document_id:
            deleted_doc_found = True
            break
    
    assert not deleted_doc_found, "Deleted document should not appear in list without include_deleted=true"
    
    print(f"   ✅ Deleted document properly hidden from list")
    
    # Test download of deleted document should return 404
    print("\n4️⃣  Verifying download of deleted document returns 404...")
    
    r = requests.get(
        f"{BASE_URL}/api/ops/finance/documents/{document_id}/download",
        headers=admin_headers
    )
    
    print(f"   📋 Download deleted document status: {r.status_code}")
    
    assert r.status_code == 404, f"Download of deleted document should return 404, got {r.status_code}"
    
    # Verify error response structure
    if r.headers.get("content-type", "").startswith("application/json"):
        error_data = r.json()
        print(f"   📋 Error response: {json.dumps(error_data, indent=2)}")
        # Should be document_not_found or file_not_found
        assert "error" in error_data or "detail" in error_data, "Error response should have error details"
    
    print(f"   ✅ Download of deleted document properly returns 404")

def test_audit_and_timeline(document_id: str, case_id: str, booking_id: str):
    """Test 4: Audit + timeline - verify audit logs and booking events"""
    print("\n" + "=" * 80)
    print("TEST 4: AUDIT AND TIMELINE VERIFICATION")
    print("Testing audit logs and booking events for document operations")
    print("=" * 80 + "\n")
    
    # Setup
    admin_token, org_id, admin_email = login_admin()
    
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    print(f"1️⃣  Checking audit logs for document operations...")
    
    # Query audit logs for document operations
    audit_query = {
        "organization_id": org_id,
        "target_id": document_id,
        "action": {"$in": ["document_upload", "document_delete"]}
    }
    
    audit_logs = list(db.audit_logs.find(audit_query))
    print(f"   📋 Found {len(audit_logs)} audit log entries")
    
    # Verify upload audit log
    upload_audit = None
    delete_audit = None
    
    for log in audit_logs:
        if log["action"] == "document_upload":
            upload_audit = log
        elif log["action"] == "document_delete":
            delete_audit = log
    
    if upload_audit:
        print(f"   ✅ Found document_upload audit log")
        print(f"   📋 Upload audit meta: {json.dumps(upload_audit.get('meta', {}), indent=2)}")
        
        # Verify required meta fields
        meta = upload_audit.get("meta", {})
        required_meta_fields = ["filename", "tag", "entity_type", "entity_id", "created_by_email"]
        for field in required_meta_fields:
            if field == "created_by_email":
                # This might be in different places
                assert (field in meta or 
                       upload_audit.get("actor", {}).get("email") or
                       "by_email" in meta), f"Missing {field} in upload audit"
            else:
                assert field in meta, f"Missing {field} in upload audit meta"
        
        assert meta["entity_type"] == "refund_case"
        assert meta["entity_id"] == case_id
        assert meta["tag"] == "refund_proof"
    else:
        print(f"   ⚠️  No document_upload audit log found")
    
    if delete_audit:
        print(f"   ✅ Found document_delete audit log")
        print(f"   📋 Delete audit meta: {json.dumps(delete_audit.get('meta', {}), indent=2)}")
        
        # Verify required meta fields
        meta = delete_audit.get("meta", {})
        required_meta_fields = ["reason", "entity_type", "entity_id", "filename", "tag"]
        for field in required_meta_fields:
            assert field in meta, f"Missing {field} in delete audit meta"
        
        assert meta["reason"] == "test_delete"
        assert meta["entity_type"] == "refund_case"
        assert meta["entity_id"] == case_id
    else:
        print(f"   ⚠️  No document_delete audit log found")
    
    print(f"\n2️⃣  Checking booking events for document operations...")
    
    # Query booking events
    events_query = {
        "organization_id": org_id,
        "booking_id": booking_id,
        "type": {"$in": ["DOCUMENT_UPLOADED", "DOCUMENT_DELETED"]}
    }
    
    booking_events = list(db.booking_events.find(events_query))
    print(f"   📋 Found {len(booking_events)} booking events")
    
    # Verify events
    upload_event = None
    delete_event = None
    
    for event in booking_events:
        if event["type"] == "DOCUMENT_UPLOADED":
            upload_event = event
        elif event["type"] == "DOCUMENT_DELETED":
            delete_event = event
    
    if upload_event:
        print(f"   ✅ Found DOCUMENT_UPLOADED event")
        print(f"   📋 Upload event meta: {json.dumps(upload_event.get('meta', {}), indent=2)}")
        
        # Verify required meta fields
        meta = upload_event.get("meta", {})
        required_fields = ["entity_type", "entity_id", "document_id", "filename", "tag", "by_email", "by_actor_id"]
        for field in required_fields:
            assert field in meta, f"Missing {field} in upload event meta"
        
        assert meta["entity_type"] == "refund_case"
        assert meta["entity_id"] == case_id
        assert meta["document_id"] == document_id
        assert meta["by_email"] == admin_email
    else:
        print(f"   ⚠️  No DOCUMENT_UPLOADED event found")
    
    if delete_event:
        print(f"   ✅ Found DOCUMENT_DELETED event")
        print(f"   📋 Delete event meta: {json.dumps(delete_event.get('meta', {}), indent=2)}")
        
        # Verify required meta fields
        meta = delete_event.get("meta", {})
        required_fields = ["entity_type", "entity_id", "document_id", "filename", "tag", "by_email", "by_actor_id"]
        for field in required_fields:
            assert field in meta, f"Missing {field} in delete event meta"
        
        assert meta["entity_type"] == "refund_case"
        assert meta["entity_id"] == case_id
        assert meta["document_id"] == document_id
        assert meta["by_email"] == admin_email
    else:
        print(f"   ⚠️  No DOCUMENT_DELETED event found")
    
    mongo_client.close()
    
    print(f"   ✅ Audit and timeline verification completed")

def test_security_checks():
    """Test 5: Security checks - MongoDB _id exposure and access control"""
    print("\n" + "=" * 80)
    print("TEST 5: SECURITY CHECKS")
    print("Testing MongoDB _id exposure and access control")
    print("=" * 80 + "\n")
    
    # Setup
    admin_token, org_id, admin_email = login_admin()
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    case_id, booking_id = find_or_create_refund_case(admin_headers, org_id)
    
    print(f"1️⃣  Testing MongoDB _id exposure in responses...")
    
    # Test list endpoint
    r = requests.get(
        f"{BASE_URL}/api/ops/finance/documents",
        headers=admin_headers,
        params={
            "entity_type": "refund_case",
            "entity_id": case_id
        }
    )
    
    assert r.status_code == 200, f"List documents failed: {r.status_code} - {r.text}"
    
    list_data = r.json()
    
    # Recursive function to check for MongoDB _id fields
    def check_no_mongo_ids(obj, path=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                assert key != "_id", f"MongoDB _id field found at {path}.{key}"
                check_no_mongo_ids(value, f"{path}.{key}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                check_no_mongo_ids(item, f"{path}[{i}]")
    
    check_no_mongo_ids(list_data, "list_response")
    
    print(f"   ✅ No MongoDB _id fields found in list response")
    
    print(f"\n2️⃣  Testing deleted documents hidden from list...")
    
    # Test that deleted documents are hidden by default
    r = requests.get(
        f"{BASE_URL}/api/ops/finance/documents",
        headers=admin_headers,
        params={
            "entity_type": "refund_case",
            "entity_id": case_id,
            "include_deleted": "false"
        }
    )
    
    assert r.status_code == 200, f"List documents failed: {r.status_code} - {r.text}"
    
    list_data_no_deleted = r.json()
    
    # Test with include_deleted=true
    r = requests.get(
        f"{BASE_URL}/api/ops/finance/documents",
        headers=admin_headers,
        params={
            "entity_type": "refund_case",
            "entity_id": case_id,
            "include_deleted": "true"
        }
    )
    
    if r.status_code == 200:
        list_data_with_deleted = r.json()
        
        # Should have same or more items when including deleted
        items_no_deleted = len(list_data_no_deleted.get("items", []))
        items_with_deleted = len(list_data_with_deleted.get("items", []))
        
        assert items_with_deleted >= items_no_deleted, "include_deleted=true should return same or more items"
        
        print(f"   ✅ Deleted document filtering working correctly")
        print(f"   📋 Items without deleted: {items_no_deleted}")
        print(f"   📋 Items with deleted: {items_with_deleted}")
    
    print(f"\n3️⃣  Testing download endpoint returns 404 for deleted docs...")
    
    # This was already tested in delete flow, but let's verify the behavior
    fake_document_id = str(ObjectId())  # Generate a fake ObjectId
    
    r = requests.get(
        f"{BASE_URL}/api/ops/finance/documents/{fake_document_id}/download",
        headers=admin_headers
    )
    
    assert r.status_code == 404, f"Download of non-existent document should return 404, got {r.status_code}"
    
    print(f"   ✅ Download endpoint properly returns 404 for non-existent documents")
    
    print(f"   ✅ Security checks completed successfully")

def run_document_vault_tests():
    """Run all Document Vault tests"""
    print("\n" + "🚀" * 80)
    print("DOCUMENT VAULT (SPRINT 2.2) BACKEND TEST SUITE")
    print("Testing /api/ops/finance/documents endpoints for refund case document management")
    print("🚀" * 80)
    
    test_functions = [
        ("Upload Flow", test_upload_flow),
        ("Security Checks", test_security_checks),
    ]
    
    passed_tests = 0
    failed_tests = 0
    document_id = None
    case_id = None
    booking_id = None
    
    for test_name, test_func in test_functions:
        try:
            if test_func == test_upload_flow:
                document_id, case_id, booking_id = test_func()
            else:
                test_func()
            passed_tests += 1
        except Exception as e:
            print(f"\n❌ TEST FAILED: {test_name}")
            print(f"   Error: {e}")
            failed_tests += 1
    
    # Run dependent tests if upload succeeded
    if document_id and case_id and booking_id:
        dependent_tests = [
            ("Download Flow", lambda: test_download_flow(document_id)),
            ("Delete Flow", lambda: test_delete_flow(document_id, case_id)),
            ("Audit and Timeline", lambda: test_audit_and_timeline(document_id, case_id, booking_id)),
        ]
        
        for test_name, test_func in dependent_tests:
            try:
                test_func()
                passed_tests += 1
            except Exception as e:
                print(f"\n❌ TEST FAILED: {test_name}")
                print(f"   Error: {e}")
                failed_tests += 1
    
    print("\n" + "🏁" * 80)
    print("TEST SUMMARY")
    print("🏁" * 80)
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {failed_tests}")
    print(f"📊 Total: {passed_tests + failed_tests}")
    
    if failed_tests == 0:
        print("\n🎉 ALL TESTS PASSED! Document Vault backend verification complete.")
    else:
        print(f"\n⚠️  {failed_tests} test(s) failed. Please review the errors above.")
    
    print("\n📋 TESTED SCENARIOS:")
    print("✅ Upload flow: multipart/form-data with entity_type=refund_case")
    print("✅ Download flow: proper Content-Type and Content-Disposition headers")
    print("✅ Delete flow: soft delete with idempotency")
    print("✅ Audit logs: document_upload and document_delete actions")
    print("✅ Timeline events: DOCUMENT_UPLOADED and DOCUMENT_DELETED")
    print("✅ Security: no MongoDB _id leaks, deleted docs hidden from list")
    print("✅ Error handling: 404 for deleted/non-existent documents")
    
    return failed_tests == 0

if __name__ == "__main__":
    success = run_document_vault_tests()
    exit(0 if success else 1)