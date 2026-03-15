#!/usr/bin/env python3
"""
Syroce Backend Contract/Agreement Management Flow Test
=====================================================

Test için backend kontrat/sözleşme yönetimi akışını test eder.

Base URL: https://redis-accounting-fix.preview.emergentagent.com
Test credentials: admin@acenta.test / admin123

Test cases:
1. Admin login successful
2. Agency creation with contract fields
3. Agency retrieval with contract fields (both trailing slash variants)
4. Contract update functionality
5. User limit enforcement
6. Test cleanup
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import aiohttp


BASE_URL = "https://redis-accounting-fix.preview.emergentagent.com"
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "admin123"

class TestResults:
    def __init__(self):
        self.results: List[Dict[str, Any]] = []
        self.created_agencies: List[str] = []
        
    def add_result(self, test_name: str, passed: bool, details: Dict[str, Any] = None):
        self.results.append({
            "test": test_name,
            "passed": passed,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat()
        })
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if details and not passed:
            print(f"  Details: {details}")


async def make_request(session: aiohttp.ClientSession, method: str, url: str, 
                      headers: Optional[Dict[str, str]] = None, 
                      json_data: Optional[Dict[str, Any]] = None,
                      expected_status: int = 200) -> Dict[str, Any]:
    """Make HTTP request and return response data with status validation."""
    try:
        async with session.request(method, url, headers=headers, json=json_data) as response:
            response_data = {}
            try:
                response_data = await response.json()
            except:
                response_data = {"text": await response.text()}
            
            return {
                "status": response.status,
                "data": response_data,
                "success": response.status == expected_status,
                "headers": dict(response.headers)
            }
    except Exception as e:
        return {
            "status": 0,
            "data": {"error": str(e)},
            "success": False,
            "headers": {}
        }


async def test_admin_login(session: aiohttp.ClientSession, results: TestResults) -> Optional[str]:
    """Test admin login and return access token."""
    login_data = {
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    }
    
    response = await make_request(
        session, "POST", f"{BASE_URL}/api/auth/login", 
        json_data=login_data, expected_status=200
    )
    
    if response["success"] and "access_token" in response["data"]:
        token = response["data"]["access_token"]
        user_roles = response["data"].get("user", {}).get("roles", [])
        results.add_result("POST /api/auth/login admin authentication", True, {
            "token_length": len(token),
            "user_roles": user_roles,
            "has_super_admin": "super_admin" in user_roles
        })
        return token
    else:
        results.add_result("POST /api/auth/login admin authentication", False, {
            "status": response["status"],
            "error": response["data"]
        })
        return None


async def test_agency_creation_with_contract(session: aiohttp.ClientSession, 
                                           token: str, results: TestResults) -> Optional[str]:
    """Test agency creation with contract fields."""
    headers = {"Authorization": f"Bearer {token}"}
    
    # Prepare test agency data with contract fields
    today = datetime.now()
    contract_start = today.strftime("%Y-%m-%d")
    contract_end = (today + timedelta(days=365)).strftime("%Y-%m-%d")
    
    agency_data = {
        "name": f"Test Contract Agency {datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "contract_start_date": contract_start,
        "contract_end_date": contract_end,
        "payment_status": "paid",
        "package_type": "Professional",
        "user_limit": 1  # Set to 1 for testing user limit enforcement
    }
    
    response = await make_request(
        session, "POST", f"{BASE_URL}/api/admin/agencies",
        headers=headers, json_data=agency_data, expected_status=200
    )
    
    if response["success"]:
        agency_data = response["data"]
        agency_id = agency_data.get("id")
        results.created_agencies.append(agency_id)
        
        # Verify all contract fields are saved
        expected_fields = ["contract_start_date", "contract_end_date", "payment_status", 
                          "package_type", "user_limit", "contract_summary"]
        missing_fields = [field for field in expected_fields if field not in agency_data]
        
        results.add_result("POST /api/admin/agencies with contract fields", 
                          len(missing_fields) == 0, {
            "agency_id": agency_id,
            "agency_name": agency_data.get("name"),
            "contract_fields_present": expected_fields,
            "missing_fields": missing_fields,
            "contract_summary": agency_data.get("contract_summary", {})
        })
        return agency_id
    else:
        results.add_result("POST /api/admin/agencies with contract fields", False, {
            "status": response["status"],
            "error": response["data"]
        })
        return None


async def test_agency_retrieval_trailing_slash(session: aiohttp.ClientSession, 
                                             token: str, results: TestResults,
                                             agency_id: str):
    """Test both /api/admin/agencies and /api/admin/agencies/ endpoints."""
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test without trailing slash
    response_no_slash = await make_request(
        session, "GET", f"{BASE_URL}/api/admin/agencies",
        headers=headers, expected_status=200
    )
    
    # Test with trailing slash
    response_with_slash = await make_request(
        session, "GET", f"{BASE_URL}/api/admin/agencies/",
        headers=headers, expected_status=200
    )
    
    # Verify both endpoints return same contract fields for created agency
    no_slash_success = False
    with_slash_success = False
    contract_fields_match = False
    
    if response_no_slash["success"]:
        agencies = response_no_slash["data"]
        test_agency = next((a for a in agencies if a.get("id") == agency_id), None)
        if test_agency:
            required_fields = ["contract_start_date", "contract_end_date", "payment_status", 
                             "package_type", "user_limit", "contract_summary"]
            no_slash_success = all(field in test_agency for field in required_fields)
    
    if response_with_slash["success"]:
        agencies = response_with_slash["data"]
        test_agency = next((a for a in agencies if a.get("id") == agency_id), None)
        if test_agency:
            required_fields = ["contract_start_date", "contract_end_date", "payment_status", 
                             "package_type", "user_limit", "contract_summary"]
            with_slash_success = all(field in test_agency for field in required_fields)
    
    # Check if both responses have same structure
    if no_slash_success and with_slash_success:
        contract_fields_match = True
    
    results.add_result("GET /api/admin/agencies (no trailing slash)", no_slash_success, {
        "status": response_no_slash["status"],
        "agencies_count": len(response_no_slash.get("data", [])) if response_no_slash["success"] else 0
    })
    
    results.add_result("GET /api/admin/agencies/ (with trailing slash)", with_slash_success, {
        "status": response_with_slash["status"], 
        "agencies_count": len(response_with_slash.get("data", [])) if response_with_slash["success"] else 0
    })
    
    results.add_result("Trailing slash endpoints return same contract data", 
                      contract_fields_match, {
        "both_endpoints_working": no_slash_success and with_slash_success
    })


async def test_contract_update(session: aiohttp.ClientSession, token: str, 
                             results: TestResults, agency_id: str):
    """Test contract information update via PUT."""
    headers = {"Authorization": f"Bearer {token}"}
    
    # Update contract information
    update_data = {
        "payment_status": "pending",
        "package_type": "Enterprise",
        "user_limit": 5
    }
    
    response = await make_request(
        session, "PUT", f"{BASE_URL}/api/admin/agencies/{agency_id}",
        headers=headers, json_data=update_data, expected_status=200
    )
    
    if response["success"]:
        updated_agency = response["data"]
        # Verify updates were applied
        updates_correct = (
            updated_agency.get("payment_status") == "pending" and
            updated_agency.get("package_type") == "Enterprise" and
            updated_agency.get("user_limit") == 5
        )
        
        results.add_result("PUT /api/admin/agencies/{agency_id} contract update", 
                          updates_correct, {
            "agency_id": agency_id,
            "updated_payment_status": updated_agency.get("payment_status"),
            "updated_package_type": updated_agency.get("package_type"),
            "updated_user_limit": updated_agency.get("user_limit")
        })
        return updates_correct
    else:
        results.add_result("PUT /api/admin/agencies/{agency_id} contract update", False, {
            "status": response["status"],
            "error": response["data"]
        })
        return False


async def test_user_limit_enforcement(session: aiohttp.ClientSession, token: str, 
                                    results: TestResults, agency_id: str):
    """Test user limit enforcement (create agency with limit=1, try to add 2 users)."""
    headers = {"Authorization": f"Bearer {token}"}
    
    # First, create a new agency with user_limit=1 specifically for this test
    today = datetime.now()
    test_agency_data = {
        "name": f"User Limit Test Agency {datetime.now().strftime('%H%M%S')}",
        "contract_start_date": today.strftime("%Y-%m-%d"),
        "contract_end_date": (today + timedelta(days=30)).strftime("%Y-%m-%d"),
        "payment_status": "paid",
        "package_type": "Basic",
        "user_limit": 1
    }
    
    agency_response = await make_request(
        session, "POST", f"{BASE_URL}/api/admin/agencies",
        headers=headers, json_data=test_agency_data, expected_status=200
    )
    
    if not agency_response["success"]:
        results.add_result("User limit enforcement setup", False, {
            "error": "Could not create test agency for user limit test"
        })
        return
    
    limit_test_agency_id = agency_response["data"]["id"]
    results.created_agencies.append(limit_test_agency_id)
    
    # Try to create first user (should succeed)
    first_user_data = {
        "email": f"testuser1_{datetime.now().strftime('%H%M%S')}@example.com",
        "name": "Test User 1",
        "password": "testpass123",
        "agency_id": limit_test_agency_id,
        "role": "agency_admin"
    }
    
    first_user_response = await make_request(
        session, "POST", f"{BASE_URL}/api/admin/all-users",
        headers=headers, json_data=first_user_data, expected_status=200
    )
    
    first_user_success = first_user_response["success"]
    results.add_result("First user creation within limit", first_user_success, {
        "agency_id": limit_test_agency_id,
        "user_email": first_user_data["email"],
        "status": first_user_response["status"]
    })
    
    if first_user_success:
        # Try to create second user (should fail with 409)
        second_user_data = {
            "email": f"testuser2_{datetime.now().strftime('%H%M%S')}@example.com",
            "name": "Test User 2",
            "password": "testpass123",
            "agency_id": limit_test_agency_id,
            "role": "agency_agent"
        }
        
        second_user_response = await make_request(
            session, "POST", f"{BASE_URL}/api/admin/all-users",
            headers=headers, json_data=second_user_data, expected_status=409
        )
        
        limit_enforced = (second_user_response["status"] == 409 and 
                         "agency_user_limit_reached" in str(second_user_response["data"]))
        
        results.add_result("User limit enforcement (409 on exceed)", limit_enforced, {
            "agency_id": limit_test_agency_id,
            "expected_status": 409,
            "actual_status": second_user_response["status"],
            "error_contains_limit_message": "agency_user_limit_reached" in str(second_user_response["data"]),
            "response": second_user_response["data"]
        })


async def test_cleanup_agencies(session: aiohttp.ClientSession, token: str, 
                              results: TestResults):
    """Clean up test agencies by setting status=disabled."""
    headers = {"Authorization": f"Bearer {token}"}
    
    cleanup_success_count = 0
    cleanup_total = len(results.created_agencies)
    
    for agency_id in results.created_agencies:
        cleanup_data = {"status": "disabled"}
        
        response = await make_request(
            session, "PUT", f"{BASE_URL}/api/admin/agencies/{agency_id}",
            headers=headers, json_data=cleanup_data, expected_status=200
        )
        
        if response["success"]:
            cleanup_success_count += 1
    
    results.add_result("Test cleanup (disable created agencies)", 
                      cleanup_success_count == cleanup_total, {
        "agencies_to_cleanup": cleanup_total,
        "agencies_cleaned": cleanup_success_count,
        "agency_ids": results.created_agencies
    })


async def run_syroce_contract_tests():
    """Run all Syroce contract management tests."""
    results = TestResults()
    
    print("=" * 70)
    print("SYROCE BACKEND CONTRACT MANAGEMENT FLOW TEST")
    print("=" * 70)
    print(f"Base URL: {BASE_URL}")
    print(f"Admin credentials: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    print(f"Test started: {datetime.utcnow().isoformat()}Z")
    print()
    
    async with aiohttp.ClientSession() as session:
        # 1. Admin login
        token = await test_admin_login(session, results)
        if not token:
            print("❌ CRITICAL: Admin login failed, cannot continue tests")
            return results
        
        # 2. Agency creation with contract fields
        agency_id = await test_agency_creation_with_contract(session, token, results)
        if not agency_id:
            print("❌ CRITICAL: Agency creation failed, cannot continue tests")
            return results
        
        # 3. Test trailing slash difference
        await test_agency_retrieval_trailing_slash(session, token, results, agency_id)
        
        # 4. Test contract updates
        await test_contract_update(session, token, results, agency_id)
        
        # 5. Test user limit enforcement
        await test_user_limit_enforcement(session, token, results, agency_id)
        
        # 6. Cleanup
        await test_cleanup_agencies(session, token, results)
    
    return results


def print_test_summary(results: TestResults):
    """Print comprehensive test summary."""
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for r in results.results if r["passed"])
    total = len(results.results)
    
    print(f"Tests passed: {passed}/{total} ({(passed/total*100):.1f}%)")
    print()
    
    print("DETAILED RESULTS:")
    for i, result in enumerate(results.results, 1):
        status = "✅" if result["passed"] else "❌"
        print(f"{i:2d}. {status} {result['test']}")
        if not result["passed"] and result["details"]:
            for key, value in result["details"].items():
                print(f"     {key}: {value}")
    
    print()
    print("KEY VALIDATION POINTS:")
    
    # Check specific validation requirements from Turkish request
    login_passed = any(r["passed"] for r in results.results if "login" in r["test"].lower())
    contract_create_passed = any(r["passed"] for r in results.results if "contract fields" in r["test"])
    trailing_slash_passed = any(r["passed"] for r in results.results if "trailing slash" in r["test"])
    update_passed = any(r["passed"] for r in results.results if "contract update" in r["test"])
    limit_enforce_passed = any(r["passed"] for r in results.results if "limit enforcement" in r["test"])
    
    validation_points = [
        ("Admin login successful", login_passed),
        ("Agency creation with contract fields", contract_create_passed),
        ("Trailing slash endpoints consistent", trailing_slash_passed),
        ("Contract update working", update_passed),
        ("User limit enforcement working", limit_enforce_passed),
    ]
    
    for desc, passed in validation_points:
        status = "✅" if passed else "❌"
        print(f"  {status} {desc}")
    
    all_critical_passed = all(passed for _, passed in validation_points)
    print(f"\nOVERALL RESULT: {'✅ ALL CRITICAL TESTS PASSED' if all_critical_passed else '❌ SOME CRITICAL TESTS FAILED'}")


if __name__ == "__main__":
    async def main():
        try:
            results = await run_syroce_contract_tests()
            print_test_summary(results)
            
            # Return appropriate exit code
            passed = sum(1 for r in results.results if r["passed"])
            total = len(results.results)
            
            if passed == total:
                sys.exit(0)  # All tests passed
            else:
                sys.exit(1)  # Some tests failed
                
        except KeyboardInterrupt:
            print("\n❌ Test interrupted by user")
            sys.exit(2)
        except Exception as e:
            print(f"\n❌ Test error: {e}")
            sys.exit(3)
    
    asyncio.run(main())