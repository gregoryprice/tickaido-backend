#!/usr/bin/env python3
"""
Test script to reproduce the authorization flow issue with MCP server.
This script will:
1. Login with admin@company.com
2. Get an agent from List Agents endpoint
3. Create a new thread
4. Send a message asking about available tools
5. Monitor the authorization flow
"""

import requests
import json
import sys
import time
from typing import Optional, Dict, Any

BASE_URL = "http://localhost:8000"

class AuthFlowTester:
    def __init__(self):
        self.session = requests.Session()
        self.access_token: Optional[str] = None
        self.agent_id: Optional[str] = None
        self.thread_id: Optional[str] = None
    
    def login(self, email: str, password: str) -> bool:
        """Login and get access token"""
        print(f"🔐 Logging in with {email}...")
        
        login_data = {
            "email": email,
            "password": password
        }
        
        try:
            response = self.session.post(
                f"{BASE_URL}/api/v1/auth/login",
                json=login_data,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"Login response status: {response.status_code}")
            print(f"Login response: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                if self.access_token:
                    # Set authorization header for subsequent requests
                    self.session.headers.update({
                        "Authorization": f"Bearer {self.access_token}"
                    })
                    print("✅ Login successful!")
                    return True
                else:
                    print("❌ No access token in response")
                    return False
            else:
                print(f"❌ Login failed with status {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
    
    def get_agents(self) -> bool:
        """Get list of agents"""
        print("🤖 Getting list of agents...")
        
        try:
            response = self.session.get(
                f"{BASE_URL}/api/v1/agents?page=1&limit=20"
            )
            
            print(f"Agents response status: {response.status_code}")
            print(f"Agents response: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                agents = data.get("agents", [])
                if agents:
                    self.agent_id = agents[0]["id"]
                    print(f"✅ Got agent ID: {self.agent_id}")
                    return True
                else:
                    print("❌ No agents found")
                    return False
            else:
                print(f"❌ Failed to get agents: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error getting agents: {e}")
            return False
    
    def create_thread(self) -> bool:
        """Create a new thread"""
        print(f"💬 Creating new thread for agent {self.agent_id}...")
        
        try:
            response = self.session.post(
                f"{BASE_URL}/api/v1/chat/{self.agent_id}/threads",
                json={},
                headers={"Content-Type": "application/json"}
            )
            
            print(f"Create thread response status: {response.status_code}")
            print(f"Create thread response: {response.text}")
            
            if response.status_code == 200 or response.status_code == 201:
                data = response.json()
                self.thread_id = data.get("id")
                if self.thread_id:
                    print(f"✅ Created thread ID: {self.thread_id}")
                    return True
                else:
                    print("❌ No thread ID in response")
                    return False
            else:
                print(f"❌ Failed to create thread: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error creating thread: {e}")
            return False
    
    def send_message(self, message: str) -> bool:
        """Send a message to the thread"""
        print(f"📨 Sending message to thread {self.thread_id}...")
        
        try:
            message_data = {
                "content": message,
                "role": "user"
            }
            
            response = self.session.post(
                f"{BASE_URL}/api/v1/chat/{self.agent_id}/threads/{self.thread_id}/messages",
                json=message_data,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"Send message response status: {response.status_code}")
            print(f"Send message response: {response.text}")
            
            if response.status_code == 200 or response.status_code == 201:
                print("✅ Message sent successfully!")
                return True
            else:
                print(f"❌ Failed to send message: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error sending message: {e}")
            return False
    
    def run_test(self):
        """Run the complete test flow"""
        print("🚀 Starting auth flow test...")
        print("=" * 50)
        
        # Step 1: Login
        if not self.login("admin@company.com", "SecurePass123"):
            print("❌ Test failed at login step")
            return False
        
        print("=" * 50)
        
        # Step 2: Get agents
        if not self.get_agents():
            print("❌ Test failed at get agents step")
            return False
        
        print("=" * 50)
        
        # Step 3: Create thread
        if not self.create_thread():
            print("❌ Test failed at create thread step")
            return False
        
        print("=" * 50)
        
        # Step 4: Send message
        message = "What are all the tools you can call?"
        if not self.send_message(message):
            print("❌ Test failed at send message step")
            return False
        
        print("=" * 50)
        print("✅ Auth flow test completed!")
        print(f"Access Token: {self.access_token}")
        print(f"Agent ID: {self.agent_id}")
        print(f"Thread ID: {self.thread_id}")
        
        return True

if __name__ == "__main__":
    tester = AuthFlowTester()
    
    print("Starting in 3 seconds to allow monitoring docker logs...")
    time.sleep(3)
    
    success = tester.run_test()
    
    if not success:
        sys.exit(1)
    
    print("\n🔍 Now check docker logs for authorization issues:")
    print("docker logs support-extension-app-1")
    print("docker logs support-extension-mcp-server-1")