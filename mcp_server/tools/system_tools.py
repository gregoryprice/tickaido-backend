"""
System Tools for MCP Server

This module contains system-related MCP tools including:
- Health checks and monitoring
- System status reporting
"""

import json
from datetime import datetime
import logging
from typing import Any, Optional
from fastmcp import FastMCP
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response

logger = logging.getLogger(__name__)
try:
    from . import BACKEND_URL, log_tool_call
    from .http_client import get_http_client
except ImportError:
    # Import path for when run directly
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from tools import BACKEND_URL, log_tool_call
    from tools.http_client import get_http_client

# Get MCP instance from parent module - will be set by register_all_system_tools
mcp = None

# =============================================================================
# SYSTEM MONITORING TOOLS
# =============================================================================

def register_get_system_health():
    @mcp.tool()
    async def get_system_health(context: Optional[Any] = None) -> str:
        """
        Check the overall health and status of the backend system.
        
        Returns:
            JSON string containing system health information
        """
        start_time = datetime.now()
        arguments = {}
        
        try:
            # Extract user context from middleware (optional for system health)
            user_context = getattr(context, 'user_context', None) if context else None
            user_token = getattr(context, 'user_token', None) if context else None
            
            if user_context:
                logger.info(f"[MCP_TOOL] System health check requested by user {user_context.user_id}")
            else:
                logger.info("[MCP_TOOL] System health check requested (no user context)")
            
            # Use http_client for backend calls
            http_client = await get_http_client()
            
            # System health endpoint may not require authentication, but pass token if available
            auth_headers = {"Authorization": f"Bearer {user_token}"} if user_token else {}
            
            response = await http_client.make_request(
                method="GET",
                endpoint="/health",
                auth_headers=auth_headers
            )
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            if response.status_code == 200:
                log_tool_call("get_system_health", arguments, response.text, execution_time, "success")
                return response.text
            else:
                error_msg = f"Error: HTTP {response.status_code} - {response.text}"
                log_tool_call("get_system_health", arguments, error_msg, execution_time, "error")
                return error_msg
                
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            log_tool_call("get_system_health", arguments, error_msg, execution_time, "error")
            return error_msg

# =============================================================================
# HEALTH ENDPOINT HANDLER
# =============================================================================

def register_health_endpoint():
    """Register the custom health check endpoint"""
    @mcp.custom_route("/health", methods=["GET"])
    async def health_check(request: StarletteRequest) -> Response:
        """
        Health check endpoint for the MCP server.
        
        Returns:
            JSON response with server status and basic information
        """
        try:
            health_status = {
                "status": "healthy",
                "server": "AI Ticket Creator MCP Tools",
                "version": "1.0.0",
                "transport": "streamable-http",
                "backend_url": BACKEND_URL,
                "timestamp": datetime.now().isoformat(),
                "tools_available": 11,  # Number of tools defined above
                "message": "MCP server is running and ready to handle requests"
            }
            
            return Response(
                content=json.dumps(health_status, indent=2),
                media_type="application/json",
                status_code=200
            )
        except Exception as e:
            error_status = {
                "status": "error",
                "server": "AI Ticket Creator MCP Tools",
                "version": "1.0.0",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
            return Response(
                content=json.dumps(error_status, indent=2),
                media_type="application/json",
                status_code=500
            )

# =============================================================================
# TOOL REGISTRATION
# =============================================================================

def register_all_system_tools(mcp_instance: FastMCP):
    """Register all system tools (includes health checks)"""
    global mcp
    mcp = mcp_instance
    
    # Register system-specific tools
    register_get_system_health()
    register_health_endpoint()
    
    logger.info("System tools registered")


def register_all_tools(mcp_instance: FastMCP):
    """Register ALL MCP tools from all modules"""
    logger.info("🔧 Registering all MCP tool modules")
    
    # Register ticket tools (Principal-based, NO HTTP calls)
    try:
        from .ticket_tools import register_all_ticket_tools
        register_all_ticket_tools(mcp_instance)
        logger.info("✅ Ticket tools registered (Principal-based)")
    except ImportError as e:
        logger.error(f"❌ Failed to import ticket tools: {e}")
    
    # Register integration tools (Principal-based)
    try:
        from .integration_tools import register_all_integration_tools
        register_all_integration_tools(mcp_instance)
        logger.info("✅ Integration tools registered (Principal-based)")
    except ImportError as e:
        logger.error(f"❌ Failed to import integration tools: {e}")
    
    # Register system tools
    register_all_system_tools(mcp_instance)
    logger.info("✅ System tools registered")
    
    logger.info("🎉 All MCP tool modules registered successfully")