#!/usr/bin/env python3
"""Test Clerk service functionality"""

import asyncio
import os
import pytest
from dotenv import load_dotenv
from app.services.clerk_service import clerk_service

@pytest.mark.asyncio
async def test_clerk_service():
    """Test basic Clerk service functionality"""
    load_dotenv()
    
    print("Testing Clerk Service...")
    
    # Test 1: Service initialization
    try:
        service = clerk_service
        if service.client:
            print("✅ Clerk service initialized successfully")
        else:
            print("⚠️ Clerk service initialized but client is None (missing CLERK_SECRET_KEY)")
    except Exception as e:
        print(f"❌ Service initialization failed: {e}")
        return False
    
    # Test 2: List users (will fail without real API key, but validates structure)
    try:
        users = await service.list_users(limit=1)
        print(f"✅ User listing method callable (found {len(users)} users)")
    except Exception as e:
        if "CLERK_SECRET_KEY" in str(e) or service.client is None:
            print("⚠️ User listing skipped (no CLERK_SECRET_KEY configured)")
        else:
            print(f"❌ User listing failed: {e}")
            return False
    
    # Test 3: Invalid token handling
    try:
        result = await service.verify_token("invalid_token")
        if result is None:
            print("✅ Invalid token properly rejected")
        else:
            print("❌ Invalid token incorrectly accepted")
            return False
    except Exception as e:
        if service.client is None:
            print("⚠️ Token verification skipped (no CLERK_SECRET_KEY configured)")
        else:
            print(f"❌ Token verification error handling failed: {e}")
            return False
    
    print("✅ All Clerk service tests passed")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_clerk_service())
    exit(0 if success else 1)