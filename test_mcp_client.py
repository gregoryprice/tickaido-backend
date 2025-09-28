#!/usr/bin/env python3
"""
Test script for MCP server interaction using pydantic_ai

This script tests the MCP server tools including:
- Basic math operations (add tool)
- System health check
- Available tools listing
- Ticket operations (create, list, search)

Usage:
    poetry run python test_mcp_client.py
"""

import asyncio
import logging
import os
from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP
from datetime import datetime, timezone, timedelta
from app.schemas.principal import Principal
from app.middleware.auth_middleware import clerk_auth

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MCP Server configuration
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8001/mcp")

def create_test_principal() -> Principal:
    """Create a test principal with dynamic token for testing"""
    try:
        # Create a test access token dynamically
        token_data = {
            "sub": "test-user-123",
            "email": "test@example.com",
            "organization_id": "test-org-456"
        }
        
        access_token = clerk_auth.create_access_token(
            data=token_data,
            expires_delta=timedelta(hours=1)
        )
        
        # Create test principal
        principal = Principal(
            user_id="test-user-123",
            organization_id="test-org-456", 
            email="test@example.com",
            full_name="Test User",
            api_token=access_token,
            roles=["user"],
            permissions=["ticket.create", "ticket.read"],
            token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        return principal
        
    except Exception as e:
        logger.error(f"Failed to create test principal: {e}")
        # Fallback to API token format
        api_token = "ai_dev_MwUVUygQboY9yIeXQ539PYTJfv9Y7yeexWL4TrELMB8"
        return Principal(
            user_id="test-user-123",
            organization_id="test-org-456",
            email="test@example.com",
            full_name="Test User",
            api_token=api_token,
            roles=["user"],
            permissions=["ticket.create", "ticket.read"],
            token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )

async def test_basic_math():
    """Test basic math operations with MCP server using dynamic authentication"""
    logger.info("🧮 Testing basic math operations...")
    
    try:
        # Create test principal with dynamic token
        principal = create_test_principal()
        
        # Get headers from principal
        headers = principal.get_headers_for_mcp()
        logger.info(f"Using dynamic auth headers: {list(headers.keys())}")
        
        server = MCPServerStreamableHTTP(MCP_SERVER_URL, headers=headers)
        agent = Agent('openai:gpt-4o-mini', toolsets=[server])
        
        async with agent:
            result = await agent.run('What is 7 plus 5?')
            logger.info(f"✅ Math result: {result.output}")
            return True
            
    except Exception as e:
        logger.error(f"❌ Math test failed: {e}")
        return False

async def test_system_health():
    """Test system health check"""
    logger.info("🏥 Testing system health check...")
    
    try:
        server = MCPServerStreamableHTTP(MCP_SERVER_URL)
        agent = Agent('openai:gpt-4o-mini', toolsets=[server])
        
        async with agent:
            result = await agent.run('Check the system health status.')
            logger.info(f"✅ Health check result: {result.output}")
            return True
            
    except Exception as e:
        logger.error(f"❌ Health check test failed: {e}")
        return False

async def test_available_tools():
    """Test listing available tools"""
    logger.info("🔧 Testing available tools listing...")
    
    try:
        server = MCPServerStreamableHTTP(MCP_SERVER_URL)
        agent = Agent('openai:gpt-4o-mini', toolsets=[server])
        
        async with agent:
            result = await agent.run('What tools can you call? List all available tools.')
            logger.info(f"✅ Available tools: {result.output}")
            return True
            
    except Exception as e:
        logger.error(f"❌ Available tools test failed: {e}")
        return False


async def test_list_tickets():
    """Test listing tickets with dynamic authentication"""
    logger.info("🎫 Testing list tickets...")
    
    try:
        # Create test principal with dynamic token
        principal = create_test_principal()
        headers = principal.get_headers_for_mcp()
        
        server = MCPServerStreamableHTTP(MCP_SERVER_URL, headers=headers)
        agent = Agent('openai:gpt-4o-mini', toolsets=[server])
        
        async with agent:
            result = await agent.run('List my current tickets, show me the first 5 tickets.')
            logger.info(f"✅ List tickets result: {result.output}")
            return True
            
    except Exception as e:
        logger.error(f"❌ List tickets test failed: {e}")
        return False
    

async def test_create_ticket():
    """Test creating a ticket with dynamic authentication"""
    logger.info("🆕 Testing create ticket...")

    try:
        # Create test principal with dynamic token
        principal = create_test_principal()
        headers = principal.get_headers_for_mcp()
        
        server = MCPServerStreamableHTTP(MCP_SERVER_URL, headers=headers)
        agent = Agent('openai:gpt-4o-mini', toolsets=[server])

        async with agent:
            prompt = (
                'Create a new support ticket titled "MCP Client Create Test" '
                'with description "Validating ticket creation from automated test." '
                'Set the priority to "medium" and confirm creation.'
            )
            result = await agent.run(prompt)
            logger.info(f"✅ Create ticket result: {result.output}")
            return True

    except Exception as e:
        logger.error(f"❌ Create ticket test failed: {e}")
        return False


async def test_ticket_operations():
    """Test ticket-related operations"""
    logger.info("🎫 Testing ticket operations...")
    
    try:
        server = MCPServerStreamableHTTP(MCP_SERVER_URL)
        agent = Agent('openai:gpt-4o-mini', toolsets=[server])
        
        async with agent:
            # Test listing tickets
            result = await agent.run('List my current tickets, show me the first 5 tickets.')
            logger.info(f"✅ List tickets result: {result.output}")
            
            # Test creating a ticket
            result = await agent.run('Create a new support ticket with title "Test MCP Integration" and description "Testing MCP server integration from pydantic_ai client".')
            logger.info(f"✅ Create ticket result: {result.output}")
            
            # Test searching tickets
            result = await agent.run('Search for tickets containing the word "integration".')
            logger.info(f"✅ Search tickets result: {result.output}")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Ticket operations test failed: {e}")
        return False

async def test_complex_interaction():
    """Test a complex multi-step interaction"""
    logger.info("🎯 Testing complex multi-step interaction...")
    
    try:
        server = MCPServerStreamableHTTP(MCP_SERVER_URL)
        agent = Agent('openai:gpt-4o-mini', toolsets=[server])
        
        async with agent:
            result = await agent.run("""
            Help me with the following tasks:
            1. First, check if the system is healthy
            2. Then, list my tickets to see what I currently have
            3. Create a new ticket for "Email notification not working" with priority "high"
            4. Search for any tickets related to "email" or "notification"
            
            Please execute these tasks in order and provide a summary.
            """)
            logger.info(f"✅ Complex interaction result: {result.output}")
            return True
            
    except Exception as e:
        logger.error(f"❌ Complex interaction test failed: {e}")
        return False

async def run_all_tests():
    """Run all MCP server tests"""
    logger.info("🚀 Starting MCP server tests...")
    logger.info(f"📡 MCP Server URL: {MCP_SERVER_URL}")
    
    tests = [
        #("Basic Math", test_basic_math)
        # ("System Health", test_system_health),
        # ("Available Tools", test_available_tools)
        # ("Ticket Operations", test_ticket_operations),
        # ("Complex Interaction", test_complex_interaction)
        ("Create Ticket", test_create_ticket)
        #("List Tickets", test_list_tickets)
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running {test_name} Test")
        logger.info(f"{'='*50}")
        
        success = await test_func()
        results.append((test_name, success))
        
        if success:
            logger.info(f"✅ {test_name} test passed")
        else:
            logger.error(f"❌ {test_name} test failed")
    
    # Print summary
    logger.info(f"\n{'='*50}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*50}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        logger.info(f"{test_name:20} {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! MCP server is working correctly.")
    else:
        logger.warning(f"⚠️  {total - passed} tests failed. Check the logs above for details.")
    
    return passed == total

async def main():
    """Main test runner"""
    try:
        success = await run_all_tests()
        exit_code = 0 if success else 1
        
        logger.info(f"\n🏁 Test run completed with exit code: {exit_code}")
        return exit_code
        
    except KeyboardInterrupt:
        logger.info("🛑 Tests interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"💥 Unexpected error during test run: {e}")
        return 1

if __name__ == "__main__":
    import sys
    
    logger.info("🧪 MCP Server Test Suite")
    logger.info("=======================")
    
    # Check if OpenAI API key is set
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        logger.error("❌ OPENAI_API_KEY not found in environment or .env file")
        logger.info("Please add OPENAI_API_KEY=your_key_here to your .env file")
        sys.exit(1)
    else:
        logger.info(f"✅ OpenAI API key loaded from environment (key ends with: ...{openai_key[-8:]})")
    
    # Run the tests
    exit_code = asyncio.run(main())
    sys.exit(exit_code)