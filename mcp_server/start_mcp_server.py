# #!/usr/bin/env python3
# """
# Principal-based MCP Server (NO HTTP calls)

# This MCP server ONLY hosts Principal-based tools that receive context from FastAPI
# and access the database directly. No circular HTTP requests.
# """

# import os
# import sys
# import logging
# from fastmcp import FastMCP

# # Add project root to path for imports
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# # Import modular tool system
# try:
#     from .tools.system_tools import register_all_tools
#     from .middleware.principal_injection import principal_injection_middleware
# except ImportError:
#     from tools.system_tools import register_all_tools
#     from middleware.principal_injection import principal_injection_middleware

# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# # Create FastMCP server for Principal-based tools ONLY
# mcp = FastMCP("Principal-based MCP Server")

# # Register ALL Principal-based tools (NO HTTP calls)
# logger.info("🔑 Registering all Principal-based tools (NO HTTP calls to backend)")
# register_all_tools(mcp)

# # Add Principal injection middleware
# logger.info("✅ Principal injection middleware configured (will extract JWT from headers in tools)")

# if __name__ == "__main__":
#     # Load environment variables
#     from dotenv import load_dotenv
#     load_dotenv(".env")
    
#     host = os.getenv("MCP_HOST", "0.0.0.0")
#     port = int(os.getenv("MCP_PORT", "8001"))
#     path = os.getenv("MCP_PATH", "/mcp/")
#     log_level = os.getenv("MCP_LOG_LEVEL", "info")
    
#     logger.info(f"🚀 Starting Principal-based MCP server on {host}:{port}")
#     logger.info("🔑 Authentication: Principal-based (JWT → Principal → Database)")
#     logger.info("🚫 NO HTTP calls to backend API")
#     logger.info("✅ Tools: Principal-based with direct database access")
    
#     mcp.run(
#         transport="streamable-http",
#         host=host,
#         port=port,
#         path=path,
#         log_level=log_level
#     )