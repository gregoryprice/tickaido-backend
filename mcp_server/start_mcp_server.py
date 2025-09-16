"""
JWT Token-based MCP Server for AI Ticket Creator Tools
Implements MCP March 2025 specification with JWT token verification
"""

import os
import logging
from fastmcp import FastMCP

# Import centralized logging configuration
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # Try relative imports first (when used as module)
    from .tools.ticket_tools import register_all_ticket_tools
    from .tools.integration_tools import register_all_integration_tools  
    from .tools.system_tools import register_all_system_tools
except ImportError:
    # Fall back to absolute imports (when run directly)
    from tools.ticket_tools import register_all_ticket_tools
    from tools.integration_tools import register_all_integration_tools
    from tools.system_tools import register_all_system_tools

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create a dedicated logger for tool calls
tool_logger = logging.getLogger("mcp_tool_calls")
tool_logger.setLevel(logging.INFO)

# Create console handler for tool logging if it doesn't exist
if not tool_logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('🔧 MCP TOOL: %(message)s')
    console_handler.setFormatter(formatter)
    tool_logger.addHandler(console_handler)
    tool_logger.propagate = False

# Initialize FastMCP server
mcp = FastMCP("AI Ticket Creator Tools")

# Configure JWT authentication - disabled for now (auth module not available)
logger.warning("🚨 AUTHENTICATION DISABLED - AUTH MODULE NOT AVAILABLE 🚨")

# Register all MCP tools
register_all_ticket_tools(mcp)
register_all_integration_tools(mcp)
register_all_system_tools(mcp)

if __name__ == "__main__":
    # Load environment variables from .env file  
    from dotenv import load_dotenv
    load_dotenv(".env")
    
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8001"))
    path = os.getenv("MCP_PATH", "/mcp/")
    log_level = os.getenv("MCP_LOG_LEVEL", "info")
    
    logger.info(f"Starting JWT token-based MCP server on {host}:{port}")
    logger.info("MCP server configuration", extra={
        "log_level": log_level,
        "backend_url": os.getenv('BACKEND_URL', 'http://localhost:8000')
    })
    
    mcp.run(
        transport="streamable-http",
        host=host,
        port=port,
        path=path,
        log_level=log_level
    )