"""
MCP Integration Tools
"""

from datetime import datetime
import logging
from typing import Any, Optional
from fastmcp import FastMCP

logger = logging.getLogger(__name__)
try:
    from . import BACKEND_URL, log_tool_call
    from .http_client import get_http_client
except ImportError:
    # Import path for when run directly
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from tools import log_tool_call
    from tools.http_client import get_http_client

# Get MCP instance from parent module - will be set by register_all_integration_tools
mcp = None


def register_list_integrations():
    @mcp.tool()
    async def list_integrations(
        integration_type: str = "",
        status: str = "",
        is_enabled: str = "",
        context: Optional[Any] = None
    ) -> str:
        """
        List available integrations for ticket creation.
        """
        start_time = datetime.now()
        arguments = {"integration_type": integration_type, "status": status, "is_enabled": is_enabled}
        
        try:
            # Extract user context from middleware (set by TokenAuthMiddleware)
            user_context = getattr(context, 'user_context', None) if context else None
            user_token = getattr(context, 'user_token', None) if context else None
            
            if not user_context:
                return "Authentication required: MCP tools need user context. Please call through authenticated AI chat session."
            
            logger.info(f"[MCP_TOOL] Authenticated list_integrations for user {user_context.user_id}")
            
            # Build query parameters
            params = {}
            if integration_type:
                params["integration_type"] = integration_type
            if status:
                params["integration_status"] = status
            if is_enabled:
                params["is_enabled"] = is_enabled.lower() == "true"
            
            # Use http_client for authenticated backend calls
            http_client = await get_http_client()
            
            # Build authentication headers from user token
            auth_headers = {"Authorization": f"Bearer {user_token}"} if user_token else {}
            
            if not user_token:
                logger.warning("[MCP_TOOL] No user token available for backend authentication")
                return "Authentication error: Missing user token for backend API calls"
            
            response = await http_client.make_request(
                method="GET",
                endpoint="/api/v1/integrations/",
                auth_headers=auth_headers,
                params=params
            )
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            if response.status_code == 200:
                log_tool_call("list_integrations", arguments, response.text, execution_time, "success")
                return response.text
            else:
                error_msg = f"Error: HTTP {response.status_code} - {response.text}"
                log_tool_call("list_integrations", arguments, error_msg, execution_time, "error")
                return error_msg
                
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            log_tool_call("list_integrations", arguments, error_msg, execution_time, "error")
            return error_msg

def register_get_active_integrations():
    @mcp.tool()
    async def get_active_integrations(
        supports_category: str = "",
        context: Optional[Any] = None
    ) -> str:
        """
        Get active integrations that can be used for ticket creation.
        """
        start_time = datetime.now()
        arguments = {"supports_category": supports_category}
        
        try:
            # Extract user context from middleware (set by TokenAuthMiddleware)
            user_context = getattr(context, 'user_context', None) if context else None
            user_token = getattr(context, 'user_token', None) if context else None
            
            if not user_context:
                return "Authentication required: MCP tools need user context. Please call through authenticated AI chat session."
            
            logger.info(f"[MCP_TOOL] Authenticated get_active_integrations for user {user_context.user_id}")
            
            # Build query parameters
            params = {}
            if supports_category:
                params["supports_category"] = supports_category
            
            # Use http_client for authenticated backend calls
            http_client = await get_http_client()
            
            # Build authentication headers from user token
            auth_headers = {"Authorization": f"Bearer {user_token}"} if user_token else {}
            
            if not user_token:
                logger.warning("[MCP_TOOL] No user token available for backend authentication")
                return "Authentication error: Missing user token for backend API calls"
            
            response = await http_client.make_request(
                method="GET",
                endpoint="/api/v1/integrations/active",
                auth_headers=auth_headers,
                params=params
            )
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            if response.status_code == 200:
                log_tool_call("get_active_integrations", arguments, response.text, execution_time, "success")
                return response.text
            else:
                error_msg = f"Error: HTTP {response.status_code} - {response.text}"
                log_tool_call("get_active_integrations", arguments, error_msg, execution_time, "error")
                return error_msg
                
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            log_tool_call("get_active_integrations", arguments, error_msg, execution_time, "error")
            return error_msg

# =============================================================================
# TOOL REGISTRATION
# =============================================================================

def register_all_integration_tools(mcp_instance: FastMCP):
    """Register all integration tools"""
    global mcp
    mcp = mcp_instance
    
    # Register tools using original registration pattern
    register_list_integrations()
    register_get_active_integrations()
    
    logger.info("Integration tools registered")