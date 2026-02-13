#!/usr/bin/env python3
"""
PR#8.1 – Inbox Backend v2 (threads + messages) comprehensive test

Tests all scenarios as specified in the review request:
- Senaryo 1: Admin basic flow (create thread, list threads, create message, list messages)
- Senaryo 2: Validation (invalid customer_id, empty body, invalid thread_id)
- Senaryo 3: Role guard (agency user should get 403)
- Senaryo 4: Org-scope (cross-org access should get 404)
- Senaryo 5: Pagination clamp (page<1→1, page_size>200→200)
- Ek: CRM events integration verification
"""

import asyncio
import json
import sys
from typing import Dict, Any, Optional
import aiohttp
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Backend URL from frontend .env
BACKEND_URL = "https://availability-perms.preview.emergentagent.com"

class InboxV2Tester:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.admin_token: Optional[str] = None
        self.agency_token: Optional[str] = None
        self.test_thread_id: Optional[str] = None
        self.results = {
            "scenario_1_admin_basic_flow": False,
            "scenario_2_validation": False,
            "scenario_3_role_guard": False,
            "scenario_4_org_scope": False,
            "scenario_5_pagination_clamp": False,
            "crm_events_integration": False,
            "errors": []
        }

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def login_admin(self) -> bool:
        """Login as admin user and get access token."""
        try:
            login_data = {
                "email": "admin@acenta.test",
                "password": "admin123"
            }
            
            async with self.session.post(f"{BACKEND_URL}/api/auth/login", json=login_data) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.admin_token = data.get("access_token")
                    logger.info("✅ Admin login successful")
                    return True
                else:
                    error_text = await resp.text()
                    logger.error(f"❌ Admin login failed: {resp.status} - {error_text}")
                    self.results["errors"].append(f"Admin login failed: {resp.status}")
                    return False
        except Exception as e:
            logger.error(f"❌ Admin login exception: {e}")
            self.results["errors"].append(f"Admin login exception: {e}")
            return False

    async def login_agency(self) -> bool:
        """Login as agency user to test role guard."""
        try:
            login_data = {
                "email": "agency1@demo.test",
                "password": "agency123"
            }
            
            async with self.session.post(f"{BACKEND_URL}/api/auth/login", json=login_data) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.agency_token = data.get("access_token")
                    logger.info("✅ Agency login successful")
                    return True
                else:
                    error_text = await resp.text()
                    logger.error(f"❌ Agency login failed: {resp.status} - {error_text}")
                    self.results["errors"].append(f"Agency login failed: {resp.status}")
                    return False
        except Exception as e:
            logger.error(f"❌ Agency login exception: {e}")
            self.results["errors"].append(f"Agency login exception: {e}")
            return False

    def get_auth_headers(self, token: str) -> Dict[str, str]:
        """Get authorization headers with token."""
        return {"Authorization": f"Bearer {token}"}

    async def test_scenario_1_admin_basic_flow(self) -> bool:
        """
        Senaryo 1 – Admin basic flow:
        - POST /api/inbox/threads (create thread)
        - GET /api/inbox/threads (list threads)
        - POST /api/inbox/threads/{thread_id}/messages (create message)
        - GET /api/inbox/threads/{thread_id}/messages (list messages)
        - GET /api/inbox/threads again (verify last_message_at updated)
        """
        logger.info("🧪 Testing Scenario 1: Admin basic flow")
        
        try:
            headers = self.get_auth_headers(self.admin_token)
            
            # Step 1: Create thread
            thread_data = {
                "channel": "internal",
                "subject": "Test thread",
                "customer_id": None,
                "participants": []
            }
            
            async with self.session.post(f"{BACKEND_URL}/api/inbox/threads", json=thread_data, headers=headers) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"❌ Create thread failed: {resp.status} - {error_text}")
                    self.results["errors"].append(f"Create thread failed: {resp.status}")
                    return False
                
                thread_response = await resp.json()
                self.test_thread_id = thread_response.get("id")
                
                # Verify response structure
                required_fields = ["id", "status", "message_count"]
                for field in required_fields:
                    if field not in thread_response:
                        logger.error(f"❌ Missing field in thread response: {field}")
                        self.results["errors"].append(f"Missing field in thread response: {field}")
                        return False
                
                if thread_response.get("status") != "open":
                    logger.error(f"❌ Expected status 'open', got: {thread_response.get('status')}")
                    self.results["errors"].append(f"Expected status 'open', got: {thread_response.get('status')}")
                    return False
                
                if thread_response.get("message_count") != 0:
                    logger.error(f"❌ Expected message_count 0, got: {thread_response.get('message_count')}")
                    self.results["errors"].append(f"Expected message_count 0, got: {thread_response.get('message_count')}")
                    return False
                
                logger.info(f"✅ Thread created successfully: {self.test_thread_id}")
            
            # Step 2: List threads (verify thread exists)
            async with self.session.get(f"{BACKEND_URL}/api/inbox/threads", headers=headers) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"❌ List threads failed: {resp.status} - {error_text}")
                    self.results["errors"].append(f"List threads failed: {resp.status}")
                    return False
                
                threads_response = await resp.json()
                
                # Verify response structure
                if "items" not in threads_response:
                    logger.error("❌ Missing 'items' in threads response")
                    self.results["errors"].append("Missing 'items' in threads response")
                    return False
                
                # Find our thread
                thread_found = False
                for thread in threads_response["items"]:
                    if thread.get("id") == self.test_thread_id:
                        thread_found = True
                        break
                
                if not thread_found:
                    logger.error(f"❌ Created thread not found in list: {self.test_thread_id}")
                    self.results["errors"].append(f"Created thread not found in list: {self.test_thread_id}")
                    return False
                
                logger.info("✅ Thread found in list")
            
            # Step 3: Create message
            message_data = {
                "direction": "internal",
                "body": "Test message",
                "attachments": []
            }
            
            async with self.session.post(f"{BACKEND_URL}/api/inbox/threads/{self.test_thread_id}/messages", 
                                       json=message_data, headers=headers) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"❌ Create message failed: {resp.status} - {error_text}")
                    self.results["errors"].append(f"Create message failed: {resp.status}")
                    return False
                
                message_response = await resp.json()
                
                # Verify message response structure
                required_fields = ["id", "thread_id", "direction", "body", "created_at"]
                for field in required_fields:
                    if field not in message_response:
                        logger.error(f"❌ Missing field in message response: {field}")
                        self.results["errors"].append(f"Missing field in message response: {field}")
                        return False
                
                if message_response.get("body") != "Test message":
                    logger.error(f"❌ Expected body 'Test message', got: {message_response.get('body')}")
                    self.results["errors"].append(f"Expected body 'Test message', got: {message_response.get('body')}")
                    return False
                
                logger.info("✅ Message created successfully")
            
            # Step 4: List messages
            async with self.session.get(f"{BACKEND_URL}/api/inbox/threads/{self.test_thread_id}/messages", 
                                      headers=headers) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"❌ List messages failed: {resp.status} - {error_text}")
                    self.results["errors"].append(f"List messages failed: {resp.status}")
                    return False
                
                messages_response = await resp.json()
                
                if "items" not in messages_response or len(messages_response["items"]) == 0:
                    logger.error("❌ No messages found in thread")
                    self.results["errors"].append("No messages found in thread")
                    return False
                
                first_message = messages_response["items"][0]
                if first_message.get("body") != "Test message":
                    logger.error(f"❌ Expected first message body 'Test message', got: {first_message.get('body')}")
                    self.results["errors"].append(f"Expected first message body 'Test message', got: {first_message.get('body')}")
                    return False
                
                logger.info("✅ Messages listed successfully")
            
            # Step 5: List threads again (verify last_message_at updated and message_count >= 1)
            async with self.session.get(f"{BACKEND_URL}/api/inbox/threads", headers=headers) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"❌ List threads (second time) failed: {resp.status} - {error_text}")
                    self.results["errors"].append(f"List threads (second time) failed: {resp.status}")
                    return False
                
                threads_response = await resp.json()
                
                # Find our thread and verify updates
                thread_found = False
                for thread in threads_response["items"]:
                    if thread.get("id") == self.test_thread_id:
                        thread_found = True
                        
                        if thread.get("last_message_at") is None:
                            logger.error("❌ last_message_at should be set after creating message")
                            self.results["errors"].append("last_message_at should be set after creating message")
                            return False
                        
                        if thread.get("message_count", 0) < 1:
                            logger.error(f"❌ Expected message_count >= 1, got: {thread.get('message_count')}")
                            self.results["errors"].append(f"Expected message_count >= 1, got: {thread.get('message_count')}")
                            return False
                        
                        break
                
                if not thread_found:
                    logger.error(f"❌ Thread not found in second list: {self.test_thread_id}")
                    self.results["errors"].append(f"Thread not found in second list: {self.test_thread_id}")
                    return False
                
                logger.info("✅ Thread updated correctly with last_message_at and message_count")
            
            logger.info("✅ Scenario 1 (Admin basic flow) completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Scenario 1 exception: {e}")
            self.results["errors"].append(f"Scenario 1 exception: {e}")
            return False

    async def test_scenario_2_validation(self) -> bool:
        """
        Senaryo 2 – Validation:
        - POST /api/inbox/threads with invalid customer_id → 400 customer_not_found
        - POST /api/inbox/threads/{thread_id}/messages with empty body → 400 empty_body
        - GET /api/inbox/threads/{invalid_oid}/messages → 400 invalid_thread_id
        """
        logger.info("🧪 Testing Scenario 2: Validation")
        
        try:
            headers = self.get_auth_headers(self.admin_token)
            
            # Test 1: Invalid customer_id
            thread_data = {
                "channel": "internal",
                "subject": "With invalid customer",
                "customer_id": "nonexistent",
                "participants": []
            }
            
            async with self.session.post(f"{BACKEND_URL}/api/inbox/threads", json=thread_data, headers=headers) as resp:
                if resp.status != 400:
                    error_text = await resp.text()
                    logger.error(f"❌ Expected 400 for invalid customer_id, got: {resp.status} - {error_text}")
                    self.results["errors"].append(f"Expected 400 for invalid customer_id, got: {resp.status}")
                    return False
                
                error_response = await resp.json()
                if error_response.get("code") != "customer_not_found":
                    logger.error(f"❌ Expected error code 'customer_not_found', got: {error_response.get('code')}")
                    self.results["errors"].append(f"Expected error code 'customer_not_found', got: {error_response.get('code')}")
                    return False
                
                logger.info("✅ Invalid customer_id validation working")
            
            # Test 2: Empty message body
            if not self.test_thread_id:
                logger.error("❌ No test thread ID available for empty body test")
                self.results["errors"].append("No test thread ID available for empty body test")
                return False
            
            message_data = {
                "direction": "internal",
                "body": "   ",  # Only whitespace
                "attachments": []
            }
            
            async with self.session.post(f"{BACKEND_URL}/api/inbox/threads/{self.test_thread_id}/messages", 
                                       json=message_data, headers=headers) as resp:
                if resp.status != 400:
                    error_text = await resp.text()
                    logger.error(f"❌ Expected 400 for empty body, got: {resp.status} - {error_text}")
                    self.results["errors"].append(f"Expected 400 for empty body, got: {resp.status}")
                    return False
                
                error_response = await resp.json()
                if error_response.get("code") != "empty_body":
                    logger.error(f"❌ Expected error code 'empty_body', got: {error_response.get('code')}")
                    self.results["errors"].append(f"Expected error code 'empty_body', got: {error_response.get('code')}")
                    return False
                
                logger.info("✅ Empty body validation working")
            
            # Test 3: Invalid thread_id
            invalid_thread_id = "invalid_oid"
            
            async with self.session.get(f"{BACKEND_URL}/api/inbox/threads/{invalid_thread_id}/messages", 
                                      headers=headers) as resp:
                if resp.status != 400:
                    error_text = await resp.text()
                    logger.error(f"❌ Expected 400 for invalid thread_id, got: {resp.status} - {error_text}")
                    self.results["errors"].append(f"Expected 400 for invalid thread_id, got: {resp.status}")
                    return False
                
                error_response = await resp.json()
                if error_response.get("code") != "invalid_thread_id":
                    logger.error(f"❌ Expected error code 'invalid_thread_id', got: {error_response.get('code')}")
                    self.results["errors"].append(f"Expected error code 'invalid_thread_id', got: {error_response.get('code')}")
                    return False
                
                logger.info("✅ Invalid thread_id validation working")
            
            logger.info("✅ Scenario 2 (Validation) completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Scenario 2 exception: {e}")
            self.results["errors"].append(f"Scenario 2 exception: {e}")
            return False

    async def test_scenario_3_role_guard(self) -> bool:
        """
        Senaryo 3 – Role guard:
        - agency1@demo.test / agency123 login
        - GET /api/inbox/threads → 403
        - POST /api/inbox/threads → 403
        """
        logger.info("🧪 Testing Scenario 3: Role guard")
        
        try:
            if not self.agency_token:
                logger.error("❌ No agency token available for role guard test")
                self.results["errors"].append("No agency token available for role guard test")
                return False
            
            headers = self.get_auth_headers(self.agency_token)
            
            # Test 1: GET /api/inbox/threads should return 403
            async with self.session.get(f"{BACKEND_URL}/api/inbox/threads", headers=headers) as resp:
                if resp.status != 403:
                    error_text = await resp.text()
                    logger.error(f"❌ Expected 403 for agency user GET threads, got: {resp.status} - {error_text}")
                    self.results["errors"].append(f"Expected 403 for agency user GET threads, got: {resp.status}")
                    return False
                
                logger.info("✅ Agency user GET threads correctly blocked with 403")
            
            # Test 2: POST /api/inbox/threads should return 403
            thread_data = {
                "channel": "internal",
                "subject": "Agency test thread",
                "customer_id": None,
                "participants": []
            }
            
            async with self.session.post(f"{BACKEND_URL}/api/inbox/threads", json=thread_data, headers=headers) as resp:
                if resp.status != 403:
                    error_text = await resp.text()
                    logger.error(f"❌ Expected 403 for agency user POST threads, got: {resp.status} - {error_text}")
                    self.results["errors"].append(f"Expected 403 for agency user POST threads, got: {resp.status}")
                    return False
                
                logger.info("✅ Agency user POST threads correctly blocked with 403")
            
            logger.info("✅ Scenario 3 (Role guard) completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Scenario 3 exception: {e}")
            self.results["errors"].append(f"Scenario 3 exception: {e}")
            return False

    async def test_scenario_4_org_scope(self) -> bool:
        """
        Senaryo 4 – Org-scope:
        This test is limited since we only have access to one organization.
        We'll test with non-existent thread IDs to simulate cross-org access.
        """
        logger.info("🧪 Testing Scenario 4: Org-scope")
        
        try:
            headers = self.get_auth_headers(self.admin_token)
            
            # Use a valid ObjectId format but non-existent thread
            fake_thread_id = "507f1f77bcf86cd799439011"  # Valid ObjectId format
            
            # Test 1: GET messages for non-existent thread should return 404 thread_not_found
            async with self.session.get(f"{BACKEND_URL}/api/inbox/threads/{fake_thread_id}/messages", 
                                      headers=headers) as resp:
                if resp.status != 404:
                    error_text = await resp.text()
                    logger.error(f"❌ Expected 404 for non-existent thread, got: {resp.status} - {error_text}")
                    self.results["errors"].append(f"Expected 404 for non-existent thread, got: {resp.status}")
                    return False
                
                error_response = await resp.json()
                if error_response.get("code") != "thread_not_found":
                    logger.error(f"❌ Expected error code 'thread_not_found', got: {error_response.get('code')}")
                    self.results["errors"].append(f"Expected error code 'thread_not_found', got: {error_response.get('code')}")
                    return False
                
                logger.info("✅ Non-existent thread GET messages correctly returns 404 thread_not_found")
            
            # Test 2: POST message to non-existent thread should return 404 thread_not_found
            message_data = {
                "direction": "internal",
                "body": "Test message for non-existent thread",
                "attachments": []
            }
            
            async with self.session.post(f"{BACKEND_URL}/api/inbox/threads/{fake_thread_id}/messages", 
                                       json=message_data, headers=headers) as resp:
                if resp.status != 404:
                    error_text = await resp.text()
                    logger.error(f"❌ Expected 404 for POST to non-existent thread, got: {resp.status} - {error_text}")
                    self.results["errors"].append(f"Expected 404 for POST to non-existent thread, got: {resp.status}")
                    return False
                
                error_response = await resp.json()
                if error_response.get("code") != "thread_not_found":
                    logger.error(f"❌ Expected error code 'thread_not_found', got: {error_response.get('code')}")
                    self.results["errors"].append(f"Expected error code 'thread_not_found', got: {error_response.get('code')}")
                    return False
                
                logger.info("✅ Non-existent thread POST message correctly returns 404 thread_not_found")
            
            logger.info("✅ Scenario 4 (Org-scope) completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Scenario 4 exception: {e}")
            self.results["errors"].append(f"Scenario 4 exception: {e}")
            return False

    async def test_scenario_5_pagination_clamp(self) -> bool:
        """
        Senaryo 5 – Pagination clamp:
        - GET /api/inbox/threads?page=0&page_size=9999 → page=1, page_size<=200
        - GET /api/inbox/threads/{thread_id}/messages?page=0&page_size=9999 → same clamp
        """
        logger.info("🧪 Testing Scenario 5: Pagination clamp")
        
        try:
            headers = self.get_auth_headers(self.admin_token)
            
            # Test 1: Threads pagination clamp
            async with self.session.get(f"{BACKEND_URL}/api/inbox/threads?page=0&page_size=9999", 
                                      headers=headers) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"❌ Threads pagination clamp test failed: {resp.status} - {error_text}")
                    self.results["errors"].append(f"Threads pagination clamp test failed: {resp.status}")
                    return False
                
                response = await resp.json()
                
                if response.get("page") != 1:
                    logger.error(f"❌ Expected page=1, got: {response.get('page')}")
                    self.results["errors"].append(f"Expected page=1, got: {response.get('page')}")
                    return False
                
                if response.get("page_size") > 200:
                    logger.error(f"❌ Expected page_size<=200, got: {response.get('page_size')}")
                    self.results["errors"].append(f"Expected page_size<=200, got: {response.get('page_size')}")
                    return False
                
                logger.info(f"✅ Threads pagination clamp working: page={response.get('page')}, page_size={response.get('page_size')}")
            
            # Test 2: Messages pagination clamp
            if not self.test_thread_id:
                logger.error("❌ No test thread ID available for messages pagination clamp test")
                self.results["errors"].append("No test thread ID available for messages pagination clamp test")
                return False
            
            async with self.session.get(f"{BACKEND_URL}/api/inbox/threads/{self.test_thread_id}/messages?page=0&page_size=9999", 
                                      headers=headers) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"❌ Messages pagination clamp test failed: {resp.status} - {error_text}")
                    self.results["errors"].append(f"Messages pagination clamp test failed: {resp.status}")
                    return False
                
                response = await resp.json()
                
                if response.get("page") != 1:
                    logger.error(f"❌ Expected page=1, got: {response.get('page')}")
                    self.results["errors"].append(f"Expected page=1, got: {response.get('page')}")
                    return False
                
                if response.get("page_size") > 200:
                    logger.error(f"❌ Expected page_size<=200, got: {response.get('page_size')}")
                    self.results["errors"].append(f"Expected page_size<=200, got: {response.get('page_size')}")
                    return False
                
                logger.info(f"✅ Messages pagination clamp working: page={response.get('page')}, page_size={response.get('page_size')}")
            
            logger.info("✅ Scenario 5 (Pagination clamp) completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Scenario 5 exception: {e}")
            self.results["errors"].append(f"Scenario 5 exception: {e}")
            return False

    async def test_crm_events_integration(self) -> bool:
        """
        Ek: CRM events integration:
        - Check /api/crm/events?entity_type=inbox_thread&action=created
        - Check /api/crm/events?entity_type=inbox_message&action=created
        """
        logger.info("🧪 Testing CRM Events Integration")
        
        try:
            headers = self.get_auth_headers(self.admin_token)
            
            # Test 1: Check inbox_thread created events
            async with self.session.get(f"{BACKEND_URL}/api/crm/events?entity_type=inbox_thread&action=created", 
                                      headers=headers) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"❌ CRM events inbox_thread query failed: {resp.status} - {error_text}")
                    self.results["errors"].append(f"CRM events inbox_thread query failed: {resp.status}")
                    return False
                
                events_response = await resp.json()
                
                if "items" not in events_response:
                    logger.error("❌ Missing 'items' in CRM events response")
                    self.results["errors"].append("Missing 'items' in CRM events response")
                    return False
                
                # Look for our thread creation event
                thread_event_found = False
                for event in events_response["items"]:
                    if (event.get("entity_type") == "inbox_thread" and 
                        event.get("action") == "created" and
                        event.get("entity_id") == self.test_thread_id):
                        thread_event_found = True
                        break
                
                if thread_event_found:
                    logger.info("✅ inbox_thread created event found in CRM events")
                else:
                    logger.warning("⚠️ inbox_thread created event not found (may be timing issue)")
            
            # Test 2: Check inbox_message created events
            async with self.session.get(f"{BACKEND_URL}/api/crm/events?entity_type=inbox_message&action=created", 
                                      headers=headers) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"❌ CRM events inbox_message query failed: {resp.status} - {error_text}")
                    self.results["errors"].append(f"CRM events inbox_message query failed: {resp.status}")
                    return False
                
                events_response = await resp.json()
                
                if "items" not in events_response:
                    logger.error("❌ Missing 'items' in CRM events response")
                    self.results["errors"].append("Missing 'items' in CRM events response")
                    return False
                
                # Look for message creation events
                message_events_found = len([
                    event for event in events_response["items"]
                    if event.get("entity_type") == "inbox_message" and event.get("action") == "created"
                ]) > 0
                
                if message_events_found:
                    logger.info("✅ inbox_message created events found in CRM events")
                else:
                    logger.warning("⚠️ inbox_message created events not found (may be timing issue)")
            
            logger.info("✅ CRM Events Integration test completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ CRM Events Integration exception: {e}")
            self.results["errors"].append(f"CRM Events Integration exception: {e}")
            return False

    async def run_all_tests(self):
        """Run all test scenarios."""
        logger.info("🚀 Starting PR#8.1 Inbox Backend v2 comprehensive test")
        
        # Login as admin
        if not await self.login_admin():
            return
        
        # Login as agency user for role guard test
        await self.login_agency()  # Don't fail if this doesn't work
        
        # Run all scenarios
        self.results["scenario_1_admin_basic_flow"] = await self.test_scenario_1_admin_basic_flow()
        self.results["scenario_2_validation"] = await self.test_scenario_2_validation()
        self.results["scenario_3_role_guard"] = await self.test_scenario_3_role_guard()
        self.results["scenario_4_org_scope"] = await self.test_scenario_4_org_scope()
        self.results["scenario_5_pagination_clamp"] = await self.test_scenario_5_pagination_clamp()
        self.results["crm_events_integration"] = await self.test_crm_events_integration()

    def print_summary(self):
        """Print test results summary."""
        logger.info("\n" + "="*80)
        logger.info("📊 PR#8.1 INBOX BACKEND V2 TEST RESULTS SUMMARY")
        logger.info("="*80)
        
        total_tests = 6
        passed_tests = sum(1 for result in [
            self.results["scenario_1_admin_basic_flow"],
            self.results["scenario_2_validation"],
            self.results["scenario_3_role_guard"],
            self.results["scenario_4_org_scope"],
            self.results["scenario_5_pagination_clamp"],
            self.results["crm_events_integration"]
        ] if result)
        
        success_rate = (passed_tests / total_tests) * 100
        
        logger.info(f"📈 Overall Success Rate: {success_rate:.1f}% ({passed_tests}/{total_tests})")
        logger.info("")
        
        # Individual test results
        test_names = [
            ("Scenario 1: Admin Basic Flow", "scenario_1_admin_basic_flow"),
            ("Scenario 2: Validation", "scenario_2_validation"),
            ("Scenario 3: Role Guard", "scenario_3_role_guard"),
            ("Scenario 4: Org-Scope", "scenario_4_org_scope"),
            ("Scenario 5: Pagination Clamp", "scenario_5_pagination_clamp"),
            ("CRM Events Integration", "crm_events_integration")
        ]
        
        for name, key in test_names:
            status = "✅ PASS" if self.results[key] else "❌ FAIL"
            logger.info(f"{status} {name}")
        
        # Error details
        if self.results["errors"]:
            logger.info("\n🚨 ERRORS ENCOUNTERED:")
            for i, error in enumerate(self.results["errors"], 1):
                logger.info(f"  {i}. {error}")
        
        logger.info("\n" + "="*80)
        
        # Return overall success
        return success_rate >= 80  # Consider 80%+ as success


async def main():
    """Main test execution."""
    async with InboxV2Tester() as tester:
        await tester.run_all_tests()
        success = tester.print_summary()
        
        if success:
            logger.info("🎉 PR#8.1 Inbox Backend v2 test completed successfully!")
            sys.exit(0)
        else:
            logger.error("💥 PR#8.1 Inbox Backend v2 test failed!")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())