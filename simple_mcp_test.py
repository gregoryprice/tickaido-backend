#!/usr/bin/env python3
"""
Simple MCP Server Test Script

Tests the basic MCP server connectivity and the 'add' tool as requested.
This is the minimal version based on your example.

Usage:
    poetry run python simple_mcp_test.py
"""

import asyncio
import logging
import os
from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Test the MCP server with the add tool"""
    logger.info("🚀 Testing MCP server connection...")
    
    # MCP Server URL (adjust if your server runs on a different port)
    server_url = 'http://localhost:8001/mcp'
    
    try:
        # Create MCP server connection
        server = MCPServerStreamableHTTP(server_url)
        agent = Agent('openai:gpt-4o-mini', toolsets=[server])  # Using gpt-4o-mini for cost efficiency
        
        logger.info(f"📡 Connecting to MCP server at: {server_url}")
        
        async with agent:
            # Test the add tool as in your example
            logger.info("🧮 Testing: What is 7 plus 5?")
            result = await agent.run('What is 7 plus 5?')
            print(f"✅ Result: {result.output}")
            
            # Test another calculation
            logger.info("🧮 Testing: What is 15 plus 25?")
            result = await agent.run('What is 15 plus 25?')
            print(f"✅ Result: {result.output}")
            
            # Test listing available tools
            logger.info("🔧 Testing: What tools are available?")
            result = await agent.run('What tools can you call? List all available tools.')
            print(f"✅ Available tools: {result.output}")
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        logger.error("Make sure:")
        logger.error("1. MCP server is running on http://localhost:8001")
        logger.error("2. OPENAI_API_KEY is set in your environment")
        logger.error("3. Dependencies are installed: poetry install")
        raise

if __name__ == "__main__":
    # Check if OpenAI API key is set
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        print("❌ Error: OPENAI_API_KEY not found in environment or .env file")
        print("Please add OPENAI_API_KEY=your_key_here to your .env file")
        exit(1)
    else:
        print(f"✅ OpenAI API key loaded from .env file (key ends with: ...{openai_key[-8:]})")
    
    print("🧪 Simple MCP Server Test")
    print("========================")
    asyncio.run(main())
    print("✅ Test completed!")