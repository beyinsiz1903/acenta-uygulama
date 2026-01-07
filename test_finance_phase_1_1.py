"""
Finance OS Phase 1.1 Backend Test
Tests: Seed data + Indexes + Collections
"""
import requests
import json

BASE_URL = "http://localhost:8001"

def test_phase_1_1():
    """Phase 1.1: Core Collections + Schema + Seed + Indexes"""
    
    print("\n" + "="*80)
    print("FINANCE OS PHASE 1.1 BACKEND TEST")
    print("="*80 + "\n")
    
    # Test 1: Health check
    print("1️⃣  Testing backend health...")
    r = requests.get(f"{BASE_URL}/api/health")
    assert r.status_code == 200, f"Health check failed: {r.status_code}"
    print("   ✅ Backend is healthy\n")
    
    # Test 2: Admin login
    print("2️⃣  Testing admin authentication...")
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"}
    )
    assert r.status_code == 200, f"Login failed: {r.status_code}"
    data = r.json()
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"   ✅ Admin login successful (role: {data.get('role')})\n")
    
    # Test 3: Check MongoDB collections exist
    print("3️⃣  Verifying Finance OS collections in MongoDB...")
    import pymongo
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    db = client["test_database"]
    
    required_collections = [
        "finance_accounts",
        "ledger_entries", 
        "ledger_postings",
        "credit_profiles",
        "account_balances",
        "payments"
    ]
    
    existing_collections = db.list_collection_names()
    for coll in required_collections:
        assert coll in existing_collections, f"Collection {coll} not found"
        print(f"   ✅ Collection '{coll}' exists")
    print()
    
    # Test 4: Check indexes
    print("4️⃣  Verifying Finance OS indexes...")
    
    # finance_accounts indexes
    accounts_indexes = db.finance_accounts.index_information()
    assert "uniq_account_code_per_org" in accounts_indexes, "Missing uniq_account_code_per_org index"
    assert "accounts_by_owner" in accounts_indexes, "Missing accounts_by_owner index"
    print("   ✅ finance_accounts indexes: uniq_account_code_per_org, accounts_by_owner")
    
    # ledger_entries indexes
    entries_indexes = db.ledger_entries.index_information()
    assert "entries_by_account_posted" in entries_indexes, "Missing entries_by_account_posted index"
    assert "entries_by_source" in entries_indexes, "Missing entries_by_source index"
    print("   ✅ ledger_entries indexes: entries_by_account_posted, entries_by_source")
    
    # ledger_postings indexes
    postings_indexes = db.ledger_postings.index_information()
    assert "uniq_posting_per_source_event" in postings_indexes, "Missing uniq_posting_per_source_event index"
    print("   ✅ ledger_postings indexes: uniq_posting_per_source_event (idempotency)")
    
    # credit_profiles indexes
    credit_indexes = db.credit_profiles.index_information()
    assert "uniq_credit_profile_per_agency" in credit_indexes, "Missing uniq_credit_profile_per_agency index"
    print("   ✅ credit_profiles indexes: uniq_credit_profile_per_agency")
    
    # account_balances indexes
    balance_indexes = db.account_balances.index_information()
    assert "uniq_balance_per_account_currency" in balance_indexes, "Missing uniq_balance_per_account_currency index"
    print("   ✅ account_balances indexes: uniq_balance_per_account_currency\n")
    
    # Test 5: Verify seed data - Platform account
    print("5️⃣  Verifying seed data - Platform account...")
    platform_account = db.finance_accounts.find_one({"type": "platform", "code": "PLATFORM_AR_EUR"})
    assert platform_account is not None, "Platform account not found"
    assert platform_account["currency"] == "EUR", "Platform account currency mismatch"
    assert platform_account["status"] == "active", "Platform account not active"
    print(f"   ✅ Platform account exists: {platform_account['code']} ({platform_account['name']})")
    print(f"      - Currency: {platform_account['currency']}")
    print(f"      - Status: {platform_account['status']}\n")
    
    # Test 6: Verify seed data - Agency accounts
    print("6️⃣  Verifying seed data - Agency accounts...")
    agency_accounts = list(db.finance_accounts.find({"type": "agency"}))
    assert len(agency_accounts) > 0, "No agency accounts found"
    print(f"   ✅ Found {len(agency_accounts)} agency account(s):")
    for acc in agency_accounts:
        print(f"      - {acc['code']}: {acc['name']} ({acc['currency']})")
    print()
    
    # Test 7: Verify seed data - Credit profiles
    print("7️⃣  Verifying seed data - Credit profiles...")
    credit_profiles = list(db.credit_profiles.find({}))
    assert len(credit_profiles) > 0, "No credit profiles found"
    print(f"   ✅ Found {len(credit_profiles)} credit profile(s):")
    for prof in credit_profiles:
        print(f"      - Agency: {prof['agency_id']}")
        print(f"        Limit: {prof['limit']} {prof['currency']}")
        print(f"        Soft limit: {prof.get('soft_limit', 'N/A')}")
        print(f"        Terms: {prof['payment_terms']}")
        print(f"        Status: {prof['status']}")
    print()
    
    # Test 8: Verify seed data - Account balances
    print("8️⃣  Verifying seed data - Account balances...")
    balances = list(db.account_balances.find({}))
    assert len(balances) > 0, "No account balances found"
    print(f"   ✅ Found {len(balances)} account balance(s):")
    for bal in balances:
        print(f"      - Account: {bal['account_id']}")
        print(f"        Balance: {bal['balance']} {bal['currency']}")
    print()
    
    print("="*80)
    print("✅ PHASE 1.1 TEST COMPLETE - ALL CHECKS PASSED")
    print("="*80)
    print("\n📊 Summary:")
    print(f"   - Collections: {len(required_collections)} created")
    print(f"   - Indexes: 10+ created (unique constraints + performance)")
    print(f"   - Platform account: 1 created (PLATFORM_AR_EUR)")
    print(f"   - Agency accounts: {len(agency_accounts)} created")
    print(f"   - Credit profiles: {len(credit_profiles)} created")
    print(f"   - Account balances: {len(balances)} initialized")
    print("\n🎯 Phase 1.1 deliverables:")
    print("   ✅ Pydantic schemas (schemas_finance.py)")
    print("   ✅ MongoDB indexes (indexes/finance_indexes.py)")
    print("   ✅ Seed data (platform + agency accounts + credit profiles)")
    print("   ✅ Collections initialized and indexed")
    print("\n🚀 Ready for Phase 1.2: Basic Finance APIs\n")


if __name__ == "__main__":
    test_phase_1_1()
