"""
Authenticated MCP Client for JWT Token Support

This module provides a simple function to create MCPServerStreamableHTTP clients with
JWT authentication by configuring the httpx client properly to avoid TaskGroup issues.
"""

import logging
from typing import Optional, Dict, Any
import httpx
from pydantic_ai.mcp import MCPServerStreamableHTTP

logger = logging.getLogger(__name__)


def create_authenticated_mcp_client(url: str, auth_token: Optional[str] = None) -> MCPServerStreamableHTTP:
    """
    Create an MCP client with proper JWT authentication support.
    
    For now, this function returns a standard MCPServerStreamableHTTP client while
    we resolve the TaskGroup async lifecycle issues with custom HTTP clients.
    
    Args:
        url: MCP server URL
        auth_token: JWT token for authentication (optional)
        
    Returns:
        MCPServerStreamableHTTP: Standard MCP client (auth implementation pending)
    """
    try:
        logger.info(f"[AUTH_MCP_CLIENT] Creating standard MCP client for URL: {url} (auth implementation pending)")
        
        # Create standard MCP client for now to avoid TaskGroup issues
        mcp_client = MCPServerStreamableHTTP(url)
        
        # Add debugging attributes
        mcp_client._auth_token = auth_token
        mcp_client._is_authenticated = auth_token is not None
        
        # Log auth status for debugging
        if auth_token:
            logger.warning(f"[AUTH_MCP_CLIENT] 🚨 Auth token available but not yet transmitted due to TaskGroup issue")
        
        return mcp_client
            
    except Exception as e:
        logger.error(f"[AUTH_MCP_CLIENT] ❌ Failed to create MCP client: {e}")
        # Fallback to basic client
        logger.info(f"[AUTH_MCP_CLIENT] Falling back to basic MCP client")
        return MCPServerStreamableHTTP(url)


class AuthenticatedMCPClient(MCPServerStreamableHTTP):
    """
    Deprecated: Use create_authenticated_mcp_client() function instead.
    
    This class approach causes TaskGroup issues with PydanticAI.
    """
    
    def __init__(self, url: str, auth_token: Optional[str] = None, **kwargs):
        """This approach is deprecated - use create_authenticated_mcp_client() instead"""
        logger.warning("[AUTH_MCP_CLIENT] AuthenticatedMCPClient class is deprecated, use create_authenticated_mcp_client() function")
        self.auth_token = auth_token
        super().__init__(url, **kwargs)
        self._is_authenticated = auth_token is not None
        
    def get_auth_info(self) -> Dict[str, Any]:
        """
        Get authentication information for debugging
        
        Returns:
            Dict containing authentication status and sanitized token info
        """
        auth_info = {
            "is_authenticated": self._is_authenticated,
            "has_token": self.auth_token is not None
        }
        
        if self.auth_token:
            # Provide sanitized token info for debugging (first 8 and last 4 characters)
            token_length = len(self.auth_token)
            if token_length > 12:
                auth_info["token_preview"] = f"{self.auth_token[:8]}...{self.auth_token[-4:]}"
            else:
                auth_info["token_preview"] = "[SHORT_TOKEN]"
                
        return auth_info

    def update_auth_token(self, new_token: Optional[str]):
        """
        Update the authentication token (for token refresh scenarios)
        
        Args:
            new_token: New JWT token or None to remove authentication
        """
        self.auth_token = new_token
        self._is_authenticated = new_token is not None
        
        # Update the HTTP client if it exists and supports auth updates
        if hasattr(self, '_http_client') and hasattr(self._http_client, 'auth_token'):
            self._http_client.auth_token = new_token
            logger.info("[AUTH_MCP_CLIENT] Updated authentication token")
        else:
            logger.warning("[AUTH_MCP_CLIENT] Token update requested but HTTP client doesn't support dynamic auth updates")

    def __repr__(self) -> str:
        """String representation of the authenticated MCP client"""
        auth_status = "authenticated" if self._is_authenticated else "non-authenticated"
        return f"AuthenticatedMCPClient({auth_status})"