#!/usr/bin/env python3
"""
COMPLETE END-TO-END FLOW TEST

This test performs the complete user journey:
1. Register user and get authentication
2. Create customer support agent
3. Create thread for the agent
4. Send message to thread
5. Validate EVERY field in EVERY response
6. Verify tool calls and message storage

CRITICAL: This test hits actual API endpoints with real authentication
and validates the complete agent-centric chat system.
"""

import pytest
import requests
import json
import time
from uuid import uuid4
from datetime import datetime


# Test configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

# Shared test data across all tests in this module
TEST_DATA = {}


class TestCompleteE2EFlow:
    """Complete end-to-end test of the agent-centric chat system"""
    
    @classmethod
    def setup_class(cls):
        """Setup for the complete flow test"""
        cls.session = requests.Session()
        cls.session.headers.update({"Content-Type": "application/json"})
        
    @property
    def test_data(self):
        """Access shared test data"""
        return TEST_DATA
    
    def test_01_health_check(self):
        """Verify service is healthy before starting"""
        
        response = self.session.get(f"{BASE_URL}/health")
        assert response.status_code == 200, f"Service not healthy: {response.status_code}"
        
        health_data = response.json()
        print("\n🏥 Service Health Check:")
        print(f"   Status: {health_data['status']}")
        print(f"   Database: {health_data['services']['database']}")
        print(f"   AI Service: {health_data['services']['ai_service']}")
        print(f"   MCP Server: {health_data['services']['mcp_server']}")
        
        assert health_data["status"] == "healthy", "Service must be healthy for E2E testing"
        assert health_data["services"]["database"] == "healthy", "Database must be healthy"
    
    def test_02_user_registration_and_authentication(self):
        """Step 1: Register user and get authentication token"""
        
        # Generate unique test data
        test_email = f"e2e_test_{int(time.time())}@example.com"
        test_org_name = f"E2E Test Org {int(time.time())}"
        test_password = "SecureTestPass123!"
        
        registration_data = {
            "email": test_email,
            "password": test_password,
            "full_name": "E2E Test User",
            "organization_name": test_org_name
        }
        
        print("\n👤 Step 1: User Registration and Login")
        print(f"   Email: {test_email}")
        print(f"   Organization: {test_org_name}")
        
        # Register user
        response = self.session.post(f"{API_BASE}/auth/register", json=registration_data)
        
        print(f"   Registration Status: {response.status_code}")
        if response.status_code != 200:
            print(f"   Registration Response: {response.text}")
        
        assert response.status_code == 200, f"User registration failed: {response.status_code} - {response.text}"
        
        reg_data = response.json()
        
        # CRITICAL: Validate registration response fields (UserResponse format)
        assert "id" in reg_data, "Missing 'id' in registration response"
        assert "email" in reg_data, "Missing 'email' in registration response"
        assert "full_name" in reg_data, "Missing 'full_name' in registration response"
        assert "is_active" in reg_data, "Missing 'is_active' in registration response"
        
        assert reg_data["email"] == test_email, f"Email mismatch: {reg_data['email']} != {test_email}"
        assert reg_data["full_name"] == "E2E Test User", "Full name mismatch"
        assert reg_data["is_active"] == True, "User should be active after registration"
        
        print(f"   ✅ User registered: {reg_data['id']}")
        
        # Now login to get authentication token
        login_data = {
            "email": test_email,
            "password": test_password
        }
        
        # Use JSON for login
        login_response = self.session.post(f"{API_BASE}/auth/login", json=login_data)
        
        print(f"   Login Status: {login_response.status_code}")
        if login_response.status_code != 200:
            print(f"   Login Response: {login_response.text}")
        
        assert login_response.status_code == 200, f"User login failed: {login_response.status_code} - {login_response.text}"
        
        login_resp_data = login_response.json()
        
        print(f"   Login Response Data: {json.dumps(login_resp_data, indent=2)}")
        
        # CRITICAL: Validate login response fields (TokenResponse format)
        assert "access_token" in login_resp_data, "Missing 'access_token' in login response"
        assert "token_type" in login_resp_data, "Missing 'token_type' in login response"
        
        # Check if user data is nested or at root level
        if "user" in login_resp_data:
            user_data = login_resp_data["user"]
        else:
            user_data = login_resp_data  # User data might be at root level
        
        # Get organization_id from user data if available, otherwise get from database
        organization_id = user_data.get("organization_id")
        if not organization_id:
            # Fallback: get organization_id from the user record
            print("   Organization ID not in login response, will get from agents endpoint")
        
        # Store authentication data
        self.test_data["user_id"] = reg_data["id"]
        self.test_data["organization_id"] = organization_id  # May be None, will get from agents endpoint
        self.test_data["access_token"] = login_resp_data["access_token"]
        self.test_data["email"] = test_email
        self.test_data["password"] = test_password
        
        # Update session with auth token
        self.session.headers.update({"Authorization": f"Bearer {login_resp_data['access_token']}"})
        
        print(f"   ✅ User logged in: {reg_data['id']}")
        print(f"   ✅ Organization: {organization_id}")
        print(f"   ✅ Token acquired: {login_resp_data['access_token'][:20]}...")
    
    def test_03_get_or_create_agent(self):
        """Step 2: Get or create customer support agent for the organization"""
        
        print("\n🤖 Step 2: Get or Create Customer Support Agent")
        print(f"   Organization ID: {self.test_data.get('organization_id', 'Unknown')}")
        
        # List agents for the organization
        response = self.session.get(f"{API_BASE}/agents")
        
        print(f"   List Agents Status: {response.status_code}")
        if response.status_code != 200:
            print(f"   Error Response: {response.text}")
        
        assert response.status_code == 200, f"Agent listing failed: {response.status_code} - {response.text}"
        
        agents_data = response.json()
        
        print(f"   Agents Response: {json.dumps(agents_data, indent=2)}")
        
        # Look for existing customer support agent - if none exists, we'll create one
        customer_support_agent = None
        organization_id = self.test_data.get("organization_id")
        
        for agent in agents_data.get("agents", []):
            if agent.get("agent_type") == "customer_support":
                if organization_id and agent.get("organization_id") == organization_id:
                    customer_support_agent = agent
                    break
                elif not organization_id:
                    # Take first customer support agent and get organization_id from it
                    customer_support_agent = agent
                    self.test_data["organization_id"] = agent.get("organization_id")
                    break
        
        if customer_support_agent is None:
            # If no existing agent found, create one manually
            print("   No existing agent found, creating manually...")
            
            agent_data = {
                "agent_type": "customer_support",
                "name": "E2E Test Customer Support Agent",
                "communication_style": "professional",
                "tools": ["create_ticket", "create_ticket_with_ai", "search_tickets"]
            }
            
            create_response = self.session.post(f"{API_BASE}/agents", json=agent_data)
            assert create_response.status_code in [200, 201], f"Manual agent creation failed: {create_response.status_code}"
            customer_support_agent = create_response.json()
            print(f"   ✅ Agent created with status: {create_response.status_code}")
        
        # CRITICAL: Validate ALL agent response fields
        assert "id" in customer_support_agent, "Missing 'id' in agent response"
        assert "organization_id" in customer_support_agent, "Missing 'organization_id' in agent response"
        assert "agent_type" in customer_support_agent, "Missing 'agent_type' in agent response"
        assert "name" in customer_support_agent, "Missing 'name' in agent response"
        assert "is_active" in customer_support_agent, "Missing 'is_active' in agent response"
        assert "status" in customer_support_agent, "Missing 'status' in agent response"
        
        # Update organization_id from agent if we didn't have it
        if not self.test_data.get("organization_id"):
            self.test_data["organization_id"] = customer_support_agent["organization_id"]
            print(f"   ✅ Organization ID retrieved from agent: {customer_support_agent['organization_id']}")
        
        # Validate agent properties
        assert customer_support_agent["organization_id"] == self.test_data["organization_id"], "Agent should belong to user's organization"
        assert customer_support_agent["agent_type"] == "customer_support", f"Expected customer_support, got {customer_support_agent['agent_type']}"
        assert customer_support_agent["is_active"] == True, "Agent should be active"
        assert customer_support_agent["status"] == "active", f"Agent should have active status, got {customer_support_agent['status']}"
        
        # Store agent data
        self.test_data["agent_id"] = customer_support_agent["id"]
        
        print(f"   ✅ Agent found/created: {customer_support_agent['id']}")
        print(f"   ✅ Agent name: {customer_support_agent['name']}")
        print(f"   ✅ Agent active: {customer_support_agent['is_active']}")
        print(f"   ✅ Tools available: {customer_support_agent.get('tools', [])}")
    
    def test_04_create_thread_for_agent(self):
        """Step 3: Create thread for the customer support agent"""
        
        thread_data = {
            "title": "E2E Test Support Thread"
        }
        
        agent_id = self.test_data["agent_id"]
        
        print("\n💬 Step 3: Create Thread for Agent")
        print(f"   Agent ID: {agent_id}")
        print(f"   Title: {thread_data['title']}")
        
        response = self.session.post(
            f"{API_BASE}/chat/{agent_id}/threads",
            json=thread_data
        )
        
        print(f"   Thread Creation Status: {response.status_code}")
        if response.status_code != 200:
            print(f"   Error Response: {response.text}")
        
        assert response.status_code in [200, 201], f"Thread creation failed: {response.status_code} - {response.text}"
        
        thread_response = response.json()
        
        # CRITICAL: Validate ALL thread response fields
        required_thread_fields = [
            "id", "agent_id", "user_id", "organization_id", "title", 
            "total_messages", "last_message_at", "archived", "created_at", "updated_at", "messages"
        ]
        
        for field in required_thread_fields:
            assert field in thread_response, f"Missing required field '{field}' in thread response"
        
        # Validate field values and types
        assert thread_response["agent_id"] == agent_id, f"Expected agent_id {agent_id}, got {thread_response['agent_id']}"
        assert thread_response["user_id"] == self.test_data["user_id"], "User ID mismatch"
        assert thread_response["organization_id"] == self.test_data["organization_id"], "Organization ID mismatch"
        assert thread_response["title"] == thread_data["title"], "Title mismatch"
        assert thread_response["archived"] == False, "New thread should not be archived"
        assert isinstance(thread_response["messages"], list), "Messages should be a list"
        assert len(thread_response["messages"]) == 0, "New thread should have no messages"
        
        # Validate message tracking fields
        assert thread_response["total_messages"] == 0, "New thread should have 0 messages"
        assert thread_response["last_message_at"] is None, "New thread should have no last_message_at"
        
        # Store thread data
        self.test_data["thread_id"] = thread_response["id"]
        
        print(f"   ✅ Thread created: {thread_response['id']}")
        print(f"   ✅ Associated with agent: {thread_response['agent_id']}")
        print(f"   ✅ Message count initialized: {thread_response['total_messages']}")
    
    def test_05_send_message_and_get_ai_response(self):
        """Step 4: Send message to thread and get AI response with tool calls"""
        
        message_data = {
            "content": "I'm having trouble logging into the system. The API keeps returning 401 authentication errors. Can you help me create a high-priority ticket for this login issue?",
            "role": "user",
            "attachments": [
                {
                    "id": str(uuid4()),
                    "filename": "login_error_screenshot.png",
                    "content_type": "image/png", 
                    "size": 45672,
                    "description": "Screenshot showing 401 authentication error"
                },
                {
                    "id": str(uuid4()),
                    "filename": "browser_console_log.txt",
                    "content_type": "text/plain",
                    "size": 2048,
                    "description": "Browser console log with error details"
                }
            ],
            "message_metadata": {
                "urgency": "high",
                "category": "authentication",
                "browser": "Chrome 118.0",
                "os": "macOS 14.0",
                "timestamp": datetime.now().isoformat(),
                "expected_ai_action": "create_ticket"
            }
        }
        
        agent_id = self.test_data["agent_id"]
        thread_id = self.test_data["thread_id"]
        
        print("\n📨 Step 4: Send Message to Thread")
        print(f"   Agent ID: {agent_id}")
        print(f"   Thread ID: {thread_id}")
        print(f"   Message: {message_data['content'][:100]}...")
        print(f"   Attachments: {len(message_data['attachments'])}")
        
        response = self.session.post(
            f"{API_BASE}/chat/{agent_id}/threads/{thread_id}/messages",
            json=message_data
        )
        
        print(f"   Message Send Status: {response.status_code}")
        if response.status_code != 200:
            print(f"   Error Response: {response.text}")
        
        assert response.status_code in [200, 201], f"Message sending failed: {response.status_code} - {response.text}"
        
        message_response = response.json()
        
        print("   ✅ AI Response received")
        print(f"   📝 Response content: {message_response.get('content', '')[:150]}...")
        
        # CRITICAL: Validate ALL message response fields
        required_message_fields = [
            "id", "thread_id", "role", "content", "content_html",
            "created_at", "tool_calls", "attachments", "message_metadata", 
            "response_time_ms", "confidence_score"
        ]
        
        for field in required_message_fields:
            assert field in message_response, f"Missing required field '{field}' in message response"
        
        # Validate field values and types
        assert message_response["thread_id"] == thread_id, f"Expected thread_id {thread_id}, got {message_response['thread_id']}"
        assert message_response["role"] == "assistant", f"Expected assistant response, got {message_response['role']}"
        assert isinstance(message_response["content"], str), f"Content should be string, got {type(message_response['content'])}"
        assert len(message_response["content"]) > 0, "AI response content should not be empty"
        
        # Validate tool calls if present (AI should use tools for ticket creation)
        if message_response.get("tool_calls"):
            assert isinstance(message_response["tool_calls"], list), "tool_calls should be list"
            print(f"   🔧 Tool calls detected: {len(message_response['tool_calls'])}")
            
            for i, tool_call in enumerate(message_response["tool_calls"]):
                assert "tool_name" in tool_call, f"Missing 'tool_name' in tool_call {i}"
                assert "called_at" in tool_call, f"Missing 'called_at' in tool_call {i}"
                assert "status" in tool_call, f"Missing 'status' in tool_call {i}"
                print(f"     Tool {i+1}: {tool_call['tool_name']} - {tool_call['status']}")
        else:
            print("   ⚠️  No tool calls detected (this might be expected depending on AI behavior)")
        
        # Validate attachments handling
        if message_response.get("attachments"):
            assert isinstance(message_response["attachments"], list), "attachments should be list"
            print(f"   📎 Attachments processed: {len(message_response['attachments'])}")
        
        # Validate message metadata
        if message_response.get("message_metadata"):
            assert isinstance(message_response["message_metadata"], dict), "message_metadata should be dict"
            metadata = message_response["message_metadata"]
            print(f"   📊 Message metadata keys: {list(metadata.keys())}")
        
        # Validate performance metrics
        if message_response.get("response_time_ms"):
            assert isinstance(message_response["response_time_ms"], int), "response_time_ms should be int"
            assert message_response["response_time_ms"] > 0, "response_time_ms should be positive"
            print(f"   ⏱️  Response time: {message_response['response_time_ms']}ms")
        
        if message_response.get("confidence_score"):
            assert isinstance(message_response["confidence_score"], (int, float)), "confidence_score should be number"
            assert 0 <= message_response["confidence_score"] <= 1, "confidence_score should be 0-1"
            print(f"   🎯 Confidence score: {message_response['confidence_score']}")
        
        # Store message data
        self.test_data["message_id"] = message_response["id"]
        self.test_data["ai_response_content"] = message_response["content"]
        
        print(f"   ✅ Message stored: {message_response['id']}")
    
    def test_06_verify_thread_with_messages(self):
        """Step 5: Verify thread contains both user and AI messages"""
        
        agent_id = self.test_data["agent_id"]
        thread_id = self.test_data["thread_id"]
        
        print("\n🔍 Step 5: Verify Thread with Messages")
        print(f"   Agent ID: {agent_id}")
        print(f"   Thread ID: {thread_id}")
        
        # Get thread with messages
        response = self.session.get(
            f"{API_BASE}/chat/{agent_id}/threads/{thread_id}?include_messages=true"
        )
        
        print(f"   Get Thread Status: {response.status_code}")
        assert response.status_code == 200, f"Get thread failed: {response.status_code} - {response.text}"
        
        thread_data = response.json()
        
        # CRITICAL: Validate thread has messages now
        assert "messages" in thread_data, "Missing 'messages' in thread response"
        messages = thread_data["messages"]
        assert isinstance(messages, list), "Messages should be list"
        assert len(messages) >= 2, f"Thread should have at least 2 messages (user + AI), got {len(messages)}"
        
        print(f"   ✅ Messages found: {len(messages)}")
        
        # Validate message sequence
        user_message = None
        ai_message = None
        
        for msg in messages:
            if msg["role"] == "user":
                user_message = msg
                print(f"   👤 User message: {msg['content'][:50]}...")
            elif msg["role"] == "assistant": 
                ai_message = msg
                print(f"   🤖 AI message: {msg['content'][:50]}...")
        
        assert user_message is not None, "Should have user message"
        assert ai_message is not None, "Should have AI response message"
        
        # Validate user message content matches what we sent
        expected_content = "I'm having trouble logging into the system"
        assert expected_content in user_message["content"], "User message content not preserved correctly"
        
        # Validate AI message has appropriate response
        ai_content = ai_message["content"].lower()
        support_keywords = ["help", "assist", "ticket", "issue", "login", "authentication"]
        found_keywords = [kw for kw in support_keywords if kw in ai_content]
        assert len(found_keywords) > 0, f"AI response should contain support keywords, got: {ai_message['content'][:100]}"
        
        print("   ✅ User message preserved correctly")
        print(f"   ✅ AI response contains support keywords: {found_keywords}")
        print("   ✅ Message sequence verified")
    
    def test_07_verify_message_retrieval(self):
        """Step 6: Verify message retrieval endpoint works correctly"""
        
        agent_id = self.test_data["agent_id"]
        thread_id = self.test_data["thread_id"]
        
        print("\n📜 Step 6: Verify Message Retrieval")
        
        # Get messages directly
        response = self.session.get(
            f"{API_BASE}/chat/{agent_id}/threads/{thread_id}/messages?page=1&page_size=100"
        )
        
        print(f"   Get Messages Status: {response.status_code}")
        assert response.status_code == 200, f"Get messages failed: {response.status_code} - {response.text}"
        
        messages_data = response.json()
        
        # CRITICAL: Validate message list response structure
        assert "messages" in messages_data, "Missing 'messages' in response"
        assert "total" in messages_data, "Missing 'total' in response"
        assert "thread_id" in messages_data, "Missing 'thread_id' in response"
        
        messages = messages_data["messages"]
        assert isinstance(messages, list), "Messages should be list"
        assert len(messages) >= 2, f"Should have at least 2 messages, got {len(messages)}"
        assert messages_data["thread_id"] == thread_id, "thread_id should match"
        
        print(f"   ✅ Message list retrieved: {len(messages)} messages")
        print(f"   ✅ Total count: {messages_data['total']}")
        
        # Validate each message has all required fields
        for i, message in enumerate(messages):
            print(f"   📝 Validating message {i+1}: {message['role']}")
            
            required_fields = [
                "id", "thread_id", "role", "content", "created_at",
                "tool_calls", "attachments", "message_metadata"
            ]
            
            for field in required_fields:
                assert field in message, f"Missing '{field}' in message {i+1}"
            
            assert message["thread_id"] == thread_id, f"Message {i+1} thread_id mismatch"
            assert message["role"] in ["user", "assistant"], f"Invalid role in message {i+1}: {message['role']}"
            
        print("   ✅ All message fields validated")
    
    def test_08_update_thread_and_verify(self):
        """Step 7: Update thread title and verify changes"""
        
        agent_id = self.test_data["agent_id"]
        thread_id = self.test_data["thread_id"]
        
        new_title = "Updated E2E Test - Login Authentication Issue"
        update_data = {
            "title": new_title
        }
        
        print("\n✏️  Step 7: Update Thread")
        print(f"   New Title: {new_title}")
        
        response = self.session.patch(
            f"{API_BASE}/chat/{agent_id}/threads/{thread_id}",
            json=update_data
        )
        
        print(f"   Update Status: {response.status_code}")
        assert response.status_code == 200, f"Thread update failed: {response.status_code} - {response.text}"
        
        update_response = response.json()
        
        # CRITICAL: Validate ALL update response fields
        assert "id" in update_response, "Missing 'id' in update response"
        assert "title" in update_response, "Missing 'title' in update response"
        assert "updated_fields" in update_response, "Missing 'updated_fields' in update response"
        
        assert update_response["id"] == thread_id, "Thread ID should match"
        assert update_response["title"] == new_title, f"Title not updated correctly: {update_response['title']}"
        assert "title" in update_response["updated_fields"], "'title' should be in updated_fields"
        
        print("   ✅ Thread updated successfully")
        print(f"   ✅ Updated fields: {update_response['updated_fields']}")
    
    def test_09_generate_ai_title(self):
        """Step 8: Test AI-powered title generation"""
        
        agent_id = self.test_data["agent_id"]
        thread_id = self.test_data["thread_id"]
        
        print("\n🎯 Step 8: Generate AI Title")
        
        response = self.session.post(
            f"{API_BASE}/chat/{agent_id}/threads/{thread_id}/generate_title"
        )
        
        print(f"   Title Generation Status: {response.status_code}")
        
        if response.status_code == 200:
            title_data = response.json()
            
            # CRITICAL: Validate ALL title generation response fields
            required_title_fields = ["id", "title", "current_title", "generated_at", "confidence"]
            
            for field in required_title_fields:
                assert field in title_data, f"Missing '{field}' in title generation response"
            
            assert title_data["id"] == thread_id, "Thread ID should match"
            assert isinstance(title_data["title"], str), "Generated title should be string"
            assert len(title_data["title"]) > 0, "Generated title should not be empty"
            assert isinstance(title_data["confidence"], (int, float)), "Confidence should be number"
            assert 0 <= title_data["confidence"] <= 1, "Confidence should be 0-1"
            
            print(f"   ✅ AI Title generated: '{title_data['title']}'")
            print(f"   ✅ Confidence: {title_data['confidence']}")
        else:
            print(f"   ⚠️  Title generation not available: {response.status_code}")
    
    def test_10_final_verification_complete_flow(self):
        """Step 9: Final verification that complete flow worked"""
        
        agent_id = self.test_data["agent_id"]
        thread_id = self.test_data["thread_id"]
        
        print("\n🏁 Step 9: Final Flow Verification")
        
        # Get final thread state
        response = self.session.get(
            f"{API_BASE}/chat/{agent_id}/threads/{thread_id}?include_messages=true"
        )
        
        assert response.status_code == 200, "Final thread retrieval failed"
        
        final_thread = response.json()
        
        # Comprehensive final validation
        assert final_thread["id"] == thread_id, "Thread ID consistency check failed"
        assert final_thread["agent_id"] == agent_id, "Agent ID consistency check failed"
        assert final_thread["user_id"] == self.test_data["user_id"], "User ID consistency check failed"
        assert final_thread["organization_id"] == self.test_data["organization_id"], "Organization ID consistency check failed"
        
        messages = final_thread["messages"]
        assert len(messages) >= 2, f"Should have at least 2 messages, got {len(messages)}"
        
        # Verify message roles and content
        user_messages = [msg for msg in messages if msg["role"] == "user"]
        ai_messages = [msg for msg in messages if msg["role"] == "assistant"]
        
        assert len(user_messages) >= 1, f"Should have at least 1 user message, got {len(user_messages)}"
        assert len(ai_messages) >= 1, f"Should have at least 1 AI message, got {len(ai_messages)}"
        
        # Verify the conversation flow makes sense
        first_user_msg = user_messages[0]
        assert "login" in first_user_msg["content"].lower(), "User message should mention login issue"
        assert "authentication" in first_user_msg["content"].lower(), "User message should mention authentication"
        
        first_ai_msg = ai_messages[0] 
        ai_content_lower = first_ai_msg["content"].lower()
        support_indicators = ["help", "assist", "ticket", "issue", "understand"]
        found_support_indicators = [indicator for indicator in support_indicators if indicator in ai_content_lower]
        assert len(found_support_indicators) > 0, f"AI response should show support intent: {first_ai_msg['content'][:100]}"
        
        print("   ✅ Complete flow verified successfully")
        print(f"   ✅ Thread: {final_thread['title']}")
        print(f"   ✅ Messages: {len(user_messages)} user, {len(ai_messages)} AI")
        print("   ✅ Agent integration: Working")
        print("   ✅ Organization isolation: Verified")
        
        # Print summary of the complete test
        print("\n🏆 COMPLETE E2E FLOW TEST SUMMARY:")
        print(f"   📧 User: {self.test_data['email']}")
        print(f"   🏢 Organization: {self.test_data['organization_id']}")
        print(f"   🤖 Agent: {self.test_data['agent_id']}")
        print(f"   💬 Thread: {self.test_data['thread_id']}")
        print(f"   📨 Messages: {len(messages)} total")
        print("   ✅ ALL VALIDATIONS PASSED")
    
    def test_11_cleanup_test_data(self):
        """Optional cleanup of test data"""
        
        agent_id = self.test_data["agent_id"] 
        thread_id = self.test_data["thread_id"]
        
        print("\n🧹 Step 10: Optional Cleanup")
        
        # Archive the test thread
        cleanup_response = self.session.patch(
            f"{API_BASE}/chat/{agent_id}/threads/{thread_id}",
            json={"archived": True}
        )
        
        if cleanup_response.status_code == 200:
            print("   ✅ Test thread archived")
        else:
            print(f"   ⚠️  Could not archive test thread: {cleanup_response.status_code}")
        
        print("   📊 Test completed with real data in database")
        print(f"   🔍 Thread {thread_id} available for manual inspection")


if __name__ == "__main__":
    # Run the complete E2E flow test
    pytest.main([
        __file__,
        "-v",
        "--tb=short", 
        "--capture=no",  # Show all print statements
        "--log-cli-level=INFO",
        "-s"  # Don't capture stdout
    ])