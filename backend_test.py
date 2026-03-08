#!/usr/bin/env python3
"""Backend testing for demo seed utility validation"""

import os
import sys
import subprocess
import json
import requests
import time
from typing import Dict, Any, List
from pymongo import MongoClient

# Configuration
BACKEND_URL = "https://meter-demo.preview.emergentagent.com/api"
TEST_AGENCY_NAME = "Demo Travel"
EXPECTED_COUNTS = {
    "tours": 5,
    "hotels": 5, 
    "customers": 20,
    "reservations": 30,
    "availability": 10
}

class DemoSeedTester:
    def __init__(self):
        self.backend_url = BACKEND_URL
        self.agency_name = TEST_AGENCY_NAME
        self.demo_credentials = None
        self.mongo_client = None
        self.db = None
        
    def setup_mongo_connection(self):
        """Setup MongoDB connection for direct validation"""
        try:
            mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
            db_name = os.environ.get("DB_NAME", "test_database")
            
            self.mongo_client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
            self.db = self.mongo_client[db_name]
            print(f"✓ Connected to MongoDB: {mongo_url}")
            return True
        except Exception as e:
            print(f"✗ MongoDB connection failed: {e}")
            return False
    
    def cleanup_mongo_connection(self):
        """Cleanup MongoDB connection"""
        if self.mongo_client:
            self.mongo_client.close()
    
    def run_seed_script(self, reset=False):
        """Run the demo seed script with specified options"""
        print(f"\n{'='*60}")
        print(f"RUNNING SEED SCRIPT: --agency '{self.agency_name}' {'--reset' if reset else '(no reset)'}")
        print(f"{'='*60}")
        
        cmd = ["python", "/app/backend/seed_demo_data.py", "--agency", self.agency_name]
        if reset:
            cmd.append("--reset")
        
        try:
            # Change to backend directory
            original_cwd = os.getcwd()
            os.chdir("/app/backend")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            # Restore original directory
            os.chdir(original_cwd)
            
            print("STDOUT:")
            print(result.stdout)
            
            if result.stderr:
                print("STDERR:")  
                print(result.stderr)
                
            if result.returncode != 0:
                print(f"✗ Script failed with return code: {result.returncode}")
                return None
            
            # Parse demo credentials from output
            self.demo_credentials = self.parse_demo_credentials(result.stdout)
            
            print(f"✓ Seed script completed successfully")
            return result.stdout
            
        except subprocess.TimeoutExpired:
            print("✗ Script timed out after 60 seconds")
            return None
        except Exception as e:
            print(f"✗ Script execution failed: {e}")
            return None
    
    def parse_demo_credentials(self, output: str) -> Dict[str, str]:
        """Parse demo credentials from script output"""
        credentials = {}
        lines = output.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith("Agency:"):
                credentials["agency"] = line.replace("Agency:", "").strip()
            elif line.startswith("Email:"):
                credentials["email"] = line.replace("Email:", "").strip()  
            elif line.startswith("Temporary password:"):
                credentials["password"] = line.replace("Temporary password:", "").strip()
        
        return credentials
    
    def validate_terminal_output(self, output: str) -> bool:
        """Validate expected terminal output from seed script"""
        print(f"\n{'='*60}")
        print("VALIDATING TERMINAL OUTPUT")
        print(f"{'='*60}")
        
        required_outputs = [
            f"Demo agency created: {self.agency_name}",
            f"Tours created: {EXPECTED_COUNTS['tours']}",
            f"Hotels created: {EXPECTED_COUNTS['hotels']}",
            f"Customers created: {EXPECTED_COUNTS['customers']}",
            f"Reservations created: {EXPECTED_COUNTS['reservations']}",
            f"Availability created: {EXPECTED_COUNTS['availability']}",
            "Seed completed successfully",
            "Demo user credentials",
            f"Agency: {self.agency_name}",
            "Email:",
            "Temporary password:"
        ]
        
        missing_outputs = []
        for required in required_outputs:
            if required not in output:
                missing_outputs.append(required)
        
        if missing_outputs:
            print("✗ Missing required outputs:")
            for missing in missing_outputs:
                print(f"  - {missing}")
            return False
        else:
            print("✓ All required terminal outputs present")
            return True
    
    def validate_mongo_counts(self, expected_tenant_counts: Dict[str, int]) -> bool:
        """Validate record counts in MongoDB for the demo tenant"""
        print(f"\n{'='*60}")
        print("VALIDATING MONGODB RECORD COUNTS")
        print(f"{'='*60}")
        
        if self.db is None:
            print("✗ MongoDB connection not available")
            return False
        
        # Get demo tenant info
        demo_org_query = {"name": self.agency_name}
        demo_org = self.db.organizations.find_one(demo_org_query)
        
        if not demo_org:
            print(f"✗ Demo organization '{self.agency_name}' not found")
            return False
        
        org_id = demo_org["_id"] 
        
        demo_tenant = self.db.tenants.find_one({"organization_id": org_id})
        if not demo_tenant:
            print(f"✗ Demo tenant for org '{org_id}' not found")
            return False
        
        tenant_id = demo_tenant["_id"]
        
        print(f"✓ Found demo org: {org_id}")
        print(f"✓ Found demo tenant: {tenant_id}")
        
        # Count records by collection
        counts = {}
        
        # Organization-scoped collections
        counts["agencies"] = self.db.agencies.count_documents({"organization_id": org_id})
        counts["tours"] = self.db.tours.count_documents({"organization_id": org_id})
        counts["hotels"] = self.db.hotels.count_documents({"organization_id": org_id})
        counts["customers"] = self.db.customers.count_documents({"organization_id": org_id})
        counts["reservations"] = self.db.reservations.count_documents({"organization_id": org_id})
        counts["users"] = self.db.users.count_documents({"organization_id": org_id})
        
        # Tenant-scoped collections  
        counts["hotel_inventory_snapshots"] = self.db.hotel_inventory_snapshots.count_documents({"tenant_id": tenant_id})
        
        print(f"\nMongoDB Record Counts:")
        for collection, count in counts.items():
            print(f"  {collection}: {count}")
        
        # Validate expected counts
        validation_errors = []
        
        if counts["agencies"] != 1:
            validation_errors.append(f"Expected 1 agency, got {counts['agencies']}")
        if counts["users"] != 1:
            validation_errors.append(f"Expected 1 user, got {counts['users']}")
        if counts["tours"] != expected_tenant_counts.get("tours", 5):
            validation_errors.append(f"Expected {expected_tenant_counts.get('tours', 5)} tours, got {counts['tours']}")
        if counts["hotels"] != expected_tenant_counts.get("hotels", 5):
            validation_errors.append(f"Expected {expected_tenant_counts.get('hotels', 5)} hotels, got {counts['hotels']}")
        if counts["customers"] != expected_tenant_counts.get("customers", 20):
            validation_errors.append(f"Expected {expected_tenant_counts.get('customers', 20)} customers, got {counts['customers']}")
        if counts["reservations"] != expected_tenant_counts.get("reservations", 30):
            validation_errors.append(f"Expected {expected_tenant_counts.get('reservations', 30)} reservations, got {counts['reservations']}")
        if counts["hotel_inventory_snapshots"] != expected_tenant_counts.get("availability", 10):
            validation_errors.append(f"Expected {expected_tenant_counts.get('availability', 10)} availability records, got {counts['hotel_inventory_snapshots']}")
        
        if validation_errors:
            print("\n✗ Record count validation failed:")
            for error in validation_errors:
                print(f"  - {error}")
            return False
        else:
            print("\n✓ All record counts match expectations")
            return True
    
    def test_login_with_demo_credentials(self) -> bool:
        """Test login functionality using demo credentials"""
        print(f"\n{'='*60}")
        print("TESTING LOGIN WITH DEMO CREDENTIALS")
        print(f"{'='*60}")
        
        if not self.demo_credentials:
            print("✗ Demo credentials not available")
            return False
        
        login_url = f"{self.backend_url}/auth/login"
        login_data = {
            "email": self.demo_credentials["email"],
            "password": self.demo_credentials["password"]
        }
        
        try:
            print(f"Attempting login to: {login_url}")
            print(f"Email: {login_data['email']}")
            
            response = requests.post(login_url, json=login_data, timeout=30)
            
            print(f"Response status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"✗ Login failed with status {response.status_code}")
                print(f"Response: {response.text}")
                return False
            
            response_data = response.json()
            
            # Validate response structure
            required_fields = ["access_token", "user", "tenant_id"]
            missing_fields = [field for field in required_fields if field not in response_data]
            
            if missing_fields:
                print(f"✗ Missing fields in login response: {missing_fields}")
                return False
            
            # Check token is non-empty
            if not response_data.get("access_token"):
                print("✗ Empty access_token in response")
                return False
                
            # Check tenant_id is returned
            if not response_data.get("tenant_id"):
                print("✗ tenant_id not returned in login response")
                return False
            
            print("✓ Login successful")
            print(f"✓ Access token received (length: {len(response_data['access_token'])})")
            print(f"✓ Tenant ID: {response_data['tenant_id']}")
            print(f"✓ User email: {response_data.get('user', {}).get('email')}")
            
            return True
            
        except requests.RequestException as e:
            print(f"✗ Login request failed: {e}")
            return False
        except Exception as e:
            print(f"✗ Unexpected error during login: {e}")
            return False
    
    def test_reset_scope(self) -> bool:
        """Test that --reset only affects the demo agency/tenant, not global data"""
        print(f"\n{'='*60}")
        print("TESTING RESET SCOPE (TENANT ISOLATION)")
        print(f"{'='*60}")
        
        if self.db is None:
            print("✗ MongoDB connection not available")
            return False
        
        # Count total records before reset
        total_before = {
            "organizations": self.db.organizations.count_documents({}),
            "tenants": self.db.tenants.count_documents({}),
            "agencies": self.db.agencies.count_documents({}),
            "users": self.db.users.count_documents({})
        }
        
        print(f"Total records before reset: {total_before}")
        
        # Run seed with reset
        output = self.run_seed_script(reset=True)
        if not output:
            print("✗ Reset seed script failed")
            return False
        
        # Count total records after reset
        total_after = {
            "organizations": self.db.organizations.count_documents({}),
            "tenants": self.db.tenants.count_documents({}),
            "agencies": self.db.agencies.count_documents({}),
            "users": self.db.users.count_documents({})
        }
        
        print(f"Total records after reset: {total_after}")
        
        # For a proper demo tenant, we expect:
        # - Same or +1 organizations (demo org created/updated)
        # - Same or +1 tenants (demo tenant created/updated)
        # - Same or +1 agencies (demo agency created/updated)
        # - Same or +1 users (demo user created/updated)
        
        validation_errors = []
        
        for collection in ["organizations", "tenants", "agencies", "users"]:
            diff = total_after[collection] - total_before[collection]
            if diff < 0:
                validation_errors.append(f"{collection} count decreased by {abs(diff)} - reset may have affected global data")
            elif diff > 1:
                validation_errors.append(f"{collection} count increased by {diff} - unexpected data creation")
        
        if validation_errors:
            print("\n✗ Reset scope validation failed:")
            for error in validation_errors:
                print(f"  - {error}")
            return False
        else:
            print("\n✓ Reset appears properly scoped to demo tenant")
            return True
    
    def run_all_tests(self):
        """Run all demo seed utility tests"""
        print(f"\n{'='*80}")
        print("DEMO SEED UTILITY TESTING")
        print(f"{'='*80}")
        
        test_results = {}
        
        # Setup
        if not self.setup_mongo_connection():
            return {"error": "MongoDB connection failed"}
        
        try:
            # Test 1: Run seed script with --reset
            print(f"\n🔹 TEST 1: Run seed script with --reset")
            output_with_reset = self.run_seed_script(reset=True)
            test_results["seed_with_reset"] = output_with_reset is not None
            
            if not test_results["seed_with_reset"]:
                return test_results
            
            # Test 2: Validate terminal output
            print(f"\n🔹 TEST 2: Validate terminal output")
            test_results["terminal_output"] = self.validate_terminal_output(output_with_reset)
            
            # Test 3: Validate MongoDB counts
            print(f"\n🔹 TEST 3: Validate MongoDB record counts")
            test_results["mongo_counts_first"] = self.validate_mongo_counts(EXPECTED_COUNTS)
            
            # Test 4: Test login with demo credentials
            print(f"\n🔹 TEST 4: Test login with demo credentials")
            test_results["login_test"] = self.test_login_with_demo_credentials()
            
            # Test 5: Run seed script again WITHOUT --reset (idempotency test)
            print(f"\n🔹 TEST 5: Run seed script without --reset (idempotency)")
            output_without_reset = self.run_seed_script(reset=False)
            test_results["seed_without_reset"] = output_without_reset is not None
            
            # Test 6: Validate counts remain the same (idempotency)
            print(f"\n🔹 TEST 6: Validate idempotency - counts should remain same")
            test_results["idempotency_counts"] = self.validate_mongo_counts(EXPECTED_COUNTS)
            
            # Test 7: Test reset scope isolation
            print(f"\n🔹 TEST 7: Test reset scope isolation")
            test_results["reset_scope"] = self.test_reset_scope()
            
        finally:
            self.cleanup_mongo_connection()
        
        return test_results

def main():
    """Main test execution"""
    tester = DemoSeedTester()
    results = tester.run_all_tests()
    
    # Print summary
    print(f"\n{'='*80}")
    print("TEST RESULTS SUMMARY")
    print(f"{'='*80}")
    
    total_tests = len([k for k in results.keys() if k != "error"])
    passed_tests = len([k for k, v in results.items() if v is True])
    
    for test_name, result in results.items():
        if test_name == "error":
            print(f"❌ SETUP ERROR: {result}")
            return False
        
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
    
    success = passed_tests == total_tests
    if success:
        print("🎉 ALL TESTS PASSED - Demo seed utility working correctly!")
    else:
        print("⚠️  SOME TESTS FAILED - Issues detected with demo seed utility")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)