#!/usr/bin/env python3
"""Test basic connection to Clerk API"""

import os
import asyncio
import pytest
from dotenv import load_dotenv
from clerk_backend_api import Clerk

@pytest.mark.asyncio
async def test_clerk_connection():
    """Test basic Clerk API connectivity"""
    load_dotenv()
    
    # Initialize Clerk client
    secret_key = os.getenv('CLERK_SECRET_KEY')
    if not secret_key:
        print("❌ CLERK_SECRET_KEY not found in environment")
        print("   Please add CLERK_SECRET_KEY to your .env file")
        return False
    
    try:
        client = Clerk(api_key=secret_key)
        print("✅ Clerk client initialized successfully")
        
        # Test API connectivity by listing users (should work even if empty)
        response = client.users.list(limit=1)
        print(f"✅ Clerk API connection successful")
        print(f"   API response received (found {len(response.data)} users)")
        return True
        
    except Exception as e:
        print(f"❌ Clerk API connection failed: {e}")
        print("   Check your CLERK_SECRET_KEY and internet connection")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_clerk_connection())
    exit(0 if success else 1)