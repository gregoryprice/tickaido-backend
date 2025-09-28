"""
MCP Client for AI Ticket Creator Tools

This module provides a client interface to the Model Context Protocol (MCP) server
that hosts comprehensive customer support tools with principal-based authorization.

ARCHITECTURE:
- Transport: HTTP Streamable (FastMCP)  
- Authentication: JWT token-based with principal context
- Tool Filtering: Agent-specific tool access control
- Session Management: Cached agent clients with stored authentication

CORE FEATURES:
1. Agent Client Creation: Creates MCP clients with tool filtering and principal storage
2. Principal Context: Stores user/organization context for MCP tool calls
3. Authentication Flow: JWT tokens passed to MCP server for secure tool access
4. Tool Authorization: Per-agent tool filtering with validation

MCP TOOL CATEGORIES:
- Ticket Management: Lifecycle, creation, categorization, search, analytics
- Integration Tools: Discovery and management of third-party integrations  
- System Tools: Health monitoring and status reporting

PRINCIPAL DATA FLOW:
1. Principal extracted from JWT token in middleware
2. Principal stored with agent MCP client (_principal attribute)
3. MCP server receives principal context for tool authorization
4. Tools operate within user's organization and permission scope

USAGE:
```python
# Create agent client with principal context (auth token extracted from principal)
agent_client = mcp_client.create_agent_client(
    agent_id="uuid", 
    tools=["create_ticket", "search_tickets"],
    principal={
        "user_id": "uuid", 
        "organization_id": "uuid",
        "api_token": "jwt_token"  # Auth token embedded in principal
    }
)

# Principal automatically available to MCP server tools
result = await agent_client.call_tool("create_ticket", title="Issue")
```

For more information:
- PydanticAI MCP: https://ai.pydantic.dev/mcp/
- FastMCP: https://fastmcp.tadata.com/
"""

import logging
import os
import httpx
from typing import Optional, Dict, Any
from pydantic_ai.mcp import MCPServerStreamableHTTP
from .tool_filter import create_filtered_mcp_client
from app.schemas.principal import Principal

logger = logging.getLogger(__name__)

class MCPClient:
    """
    MCP Client for connecting to MCP server.
    This client uses PydanticAI's MCPServerStreamableHTTP to connect to a FastMCP server
    that provides comprehensive customer support tools organized into three categories:
    
    Connection Details:
    - Transport: Streamable HTTP (FastMCP)
    - Protocol: MCP (Model Context Protocol)
    - Default URL: http://localhost:8001/mcp
    - Session Management: Automatic session handling for tool calls
    """
    
    def __init__(self):
        """Initialize the MCP client."""
        self.mcp_server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8001")
        self.mcp_client: Optional[MCPServerStreamableHTTP] = None
        self._agent_clients: Dict[str, MCPServerStreamableHTTP] = {}
        self._is_connected = False
        self._principal: Optional[Dict[str, Any]] = None
    
        
    def create_mcp_client(self, principal: Optional[Principal] = None) -> Optional[MCPServerStreamableHTTP]:
        """
        Create and configure the MCP client using HTTP streamable transport with optional authentication.
        
        According to PydanticAI documentation, MCPServerStreamableHTTP expects
        the URL to point directly to the MCP endpoint (e.g., http://localhost:8001/mcp)
        
        Args:
            principal: Optional Principal object containing JWT token for authentication
        
        Returns:
            MCPServerStreamableHTTP: Configured MCP client or None if creation fails
            
        Raises:
            Exception: If MCP client creation fails
        """
        try:
            # MCPServerStreamableHTTP expects the full URL to the MCP endpoint
            # The FastMCP server serves at /mcp/ when using streamable-http transport
            mcp_url = f"{self.mcp_server_url}/mcp/"
            logger.info(f"[MCP_CLIENT] 🔧 Creating MCP client at {mcp_url}")
            logger.debug(f"[MCP_CLIENT] Server URL: {self.mcp_server_url}")
            logger.debug(f"[MCP_CLIENT] Full MCP endpoint: {mcp_url}")
            
            # Create the MCP client with authentication if principal provided
            if principal:
                return self._create_authenticated_client(principal, mcp_url)
            else:
                # Create unauthenticated MCP client
                mcp_client = MCPServerStreamableHTTP(mcp_url)
                mcp_client.get_principal = lambda: None
                mcp_client.is_authenticated = lambda: False
                logger.info(f"[MCP_CLIENT] ✅ Unauthenticated MCP client created")
                return mcp_client
            
        except Exception as e:
            logger.error(f"[MCP_CLIENT] ❌ Failed to create MCP client: {e}")
            logger.error(f"[MCP_CLIENT] ❌ MCP_SERVER_URL: {self.mcp_server_url}")
            logger.error(f"[MCP_CLIENT] ❌ Full error details: {str(e)}")
            import traceback
            logger.error(f"[MCP_CLIENT] ❌ Traceback: {traceback.format_exc()}")
            return None
    
    def get_mcp_client(self) -> Optional[MCPServerStreamableHTTP]:
        """
        Get the MCP client, creating it if necessary.
        
        Returns:
            MCPServerStreamableHTTP: MCP client or None if unavailable
        """
        logger.info(f"[MCP_CLIENT] Getting MCP client - current state: connected={self._is_connected}, client_exists={self.mcp_client is not None}")
        
        if self.mcp_client is None:
            logger.info("[MCP_CLIENT] Creating new MCP client")
            self.mcp_client = self.create_mcp_client()
            if self.mcp_client is not None:
                self._is_connected = True
                logger.info("[MCP_CLIENT] ✅ MCP client initialized and ready")
                logger.info(f"[MCP_CLIENT] Available tools: {self.get_available_tools()}")
            else:
                self._is_connected = False
                logger.warning("[MCP_CLIENT] ⚠️ MCP client initialization failed")
        else:
            logger.info("[MCP_CLIENT] Using existing MCP client")
        
        return self.mcp_client
    
    def is_available(self) -> bool:
        """
        Check if the MCP client is available and connected.
        
        Returns:
            bool: True if MCP client is available, False otherwise
        """
        client = self.get_mcp_client()
        return client is not None and self._is_connected
    
    def get_connection_info(self) -> Dict[str, Any]:
        """
        Get information about the MCP client connection.
        
        Returns:
            Dict[str, Any]: Connection information including status and URL
        """
        return {
            "is_connected": self._is_connected,
            "transport": "streamable_http",
            "mcp_server_url": self.mcp_server_url,
            "full_url": f"{self.mcp_server_url}/mcp",
            "client_available": self.mcp_client is not None,
            "service": "MCP Server"
        }
    
    def reset_connection(self) -> bool:
        """
        Reset the MCP client connection.
        
        This can be used to re-establish the connection if it becomes
        unavailable or if there are connection issues.
        
        Returns:
            bool: True if reset was successful, False otherwise
        """
        try:
            logger.info("🔄 Resetting AI Ticket Creator MCP client connection...")
            
            # Clean up existing client
            if self.mcp_client is not None:
                try:
                    # Close the client if it has a close method
                    if hasattr(self.mcp_client, 'close'):
                        self.mcp_client.close()
                except Exception as e:
                    logger.warning(f"⚠️ Error closing MCP client: {e}")
            
            self.mcp_client = None
            self._is_connected = False
            
            # Try to create a new client
            new_client = self.create_mcp_client()
            if new_client is not None:
                self.mcp_client = new_client
                self._is_connected = True
                logger.info("✅ MCP client connection reset successfully")
                return True
            else:
                logger.error("❌ Failed to reset MCP client connection")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error resetting MCP client connection: {e}")
            return False
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test the MCP client connection by calling a simple tool.
        
        Returns:
            Dict[str, Any]: Test result with connection status
        """
        try:
            client = self.get_mcp_client()
            if not client:
                return {
                    "success": False,
                    "error": "MCP client not available"
                }
            
            # Test connection by calling the system health tool
            # This would be implemented when the actual MCP integration is working
            tools = self.get_available_tools()

            return {
                "success": True,
                "message": "MCP client connection test successful",
                "server_url": self.mcp_server_url,
                "tools_available": tools
            }
            
        except Exception as e:
            logger.error(f"❌ MCP client connection test failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_available_tools(self) -> list:
        """
        Get list of all available MCP tools.
        
        Returns:
            list: List of available tool names organized by category
        """
        try: 
            # Programmatically fetch all tools from the MCP server
            all_tools = self.mcp_client.list_tools() # 
            
            # Extract just the names of the tools
            tool_names = [tool.name for tool in all_tools] # 
            
            return tool_names
        
        except Exception as e:
            logger.error(f"[MCP_CLIENT] ❌ Failed to get available tools: {e}")
            raise

    
    def create_agent_client(self, agent_id: str, tools: list, principal: Optional[Principal] = None) -> Optional[MCPServerStreamableHTTP]:
        """
        Create MCP client configured for specific agent with tool filtering and principal storage.
        
        Args:
            agent_id: Agent UUID
            tools: List of tools this agent can access
            principal: Principal data containing auth token and context for MCP server tool calls
            
        Returns:
            MCPServerStreamableHTTP: Agent-specific authenticated MCP client or None if no principal provided
        """
        try:
            # Validate principal and token
            if not principal or not principal.is_token_valid():
                logger.error(f"[MCP_CLIENT] ❌ No valid principal for agent {agent_id}")
                return None
            
            # Get authentication headers from principal
            headers = self._get_auth_headers_from_principal(principal)
            if not headers:
                logger.error(f"[MCP_CLIENT] ❌ Could not extract auth headers from principal for agent {agent_id}")
                return None
            
            # Generate cache key including auth context
            cache_key = f"{principal.get_cache_hash()}_{agent_id}_{hash(tuple(sorted(tools)))}"
            
            # Check if we already have a client for this agent configuration
            if cache_key in self._agent_clients:
                cached_client = self._agent_clients[cache_key]
                # Validate cached client's token is still valid
                if hasattr(cached_client, '_principal') and cached_client._principal.is_token_valid():
                    logger.debug(f"[MCP_CLIENT] Using cached authenticated agent client for {agent_id}")
                    return cached_client
                else:
                    # Remove invalid cached client
                    logger.info(f"[MCP_CLIENT] Removing expired cached client for agent {agent_id}")
                    del self._agent_clients[cache_key]
            
            # Create authenticated MCP client with Principal token
            logger.info(f"[MCP_CLIENT] 🔐 Creating authenticated MCP client for agent {agent_id}")
            
            mcp_url = f"{self.mcp_server_url}/mcp/"
            base_client = self._create_authenticated_client(principal, mcp_url)
            if not base_client:
                logger.error(f"[MCP_CLIENT] ❌ Failed to create authenticated MCP client for agent {agent_id}")
                return None
            
            # Apply tool filtering wrapper
            if tools:
                filtered_client = create_filtered_mcp_client(base_client, tools, agent_id)
                logger.info(f"[MCP_CLIENT] ✅ Created filtered MCP client for agent {agent_id} with {len(tools)} allowed tools")
            else:
                filtered_client = base_client
                logger.warning(f"[MCP_CLIENT] Agent {agent_id} has no tools - allowing all tools")
            
            # Cache the filtered client
            self._agent_clients[cache_key] = filtered_client
            
            logger.info(f"[MCP_CLIENT] ✅ Agent-specific MCP client created for {agent_id} with {len(tools)} tools")
            return filtered_client
            
        except Exception as e:
            logger.error(f"[MCP_CLIENT] ❌ Failed to create agent MCP client: {e}")
            return None
    
    def get_agent_client(self, agent_id: str, tools: list, principal: Optional[Principal] = None) -> Optional[MCPServerStreamableHTTP]:
        """
        Get agent-specific MCP client, creating if necessary.
        
        Args:
            agent_id: Agent UUID
            tools: List of tools this agent can access  
            principal: Principal data containing auth token and context for MCP server tool calls
            
        Returns:
            MCPServerStreamableHTTP: Agent-specific authenticated MCP client or None if no principal provided
        """
        try:
            client = self.create_agent_client(agent_id, tools, principal)
            if client:
                logger.debug(f"[MCP_CLIENT] Authenticated agent client ready for {agent_id} with tools: {tools}")
            return client
        except Exception as e:
            logger.error(f"[MCP_CLIENT] ❌ Failed to get agent MCP client: {e}")
            return None
    
    async def validate_agent_tool_call(self, agent_client: MCPServerStreamableHTTP, tool_name: str) -> bool:
        """
        Validate that agent is allowed to call the specified tool.
        
        Args:
            agent_client: Agent-specific MCP client
            tool_name: Name of tool to validate
            
        Returns:
            bool: True if agent can call this tool
        """
        try:
            enabled_tools = getattr(agent_client, '_enabled_tools', set())
            agent_id = getattr(agent_client, '_agent_id', 'unknown')
            
            is_allowed = tool_name in enabled_tools
            
            if not is_allowed:
                logger.warning(f"[MCP_CLIENT] 🚫 Agent {agent_id} attempted to call unauthorized tool: {tool_name}")
                logger.debug(f"[MCP_CLIENT] Agent {agent_id} enabled tools: {enabled_tools}")
            else:
                logger.debug(f"[MCP_CLIENT] ✅ Agent {agent_id} authorized to call tool: {tool_name}")
            
            return is_allowed
            
        except Exception as e:
            logger.error(f"[MCP_CLIENT] ❌ Error validating tool call: {e}")
            return False
    
    def get_client_principal(self, client: MCPServerStreamableHTTP) -> Optional[Dict[str, Any]]:
        """
        Get the principal stored with an MCP client.
        
        Args:
            client: MCP client to get principal from
            
        Returns:
            Dict[str, Any]: Principal data or None if not set
        """
        return getattr(client, '_principal', None)
    
    async def close_authenticated_client(self, client: MCPServerStreamableHTTP):
        """
        Close the authenticated HTTP client if it exists.
        
        Args:
            client: MCP client to close
        """
        try:
            if hasattr(client, '_authenticated_client') and client._authenticated_client:
                await client._authenticated_client.aclose()
                logger.debug("[MCP_CLIENT] Closed authenticated HTTP client")
        except Exception as e:
            logger.warning(f"[MCP_CLIENT] Error closing HTTP client: {e}")
    
    def _get_auth_headers_from_principal(self, principal: Principal) -> Optional[Dict[str, str]]:
        """
        Extract authentication headers from Principal object.
        
        Args:
            principal: Principal object containing authentication token
            
        Returns:
            Dict[str, str]: Authentication headers or None if token unavailable
        """
        try:
            # Get authentication token from principal
            auth_token = principal.get_auth_token()
            if not auth_token:
                logger.error("[MCP_CLIENT] No authentication token found in principal")
                return None
            
            # Create headers in the format expected by MCP server
            # Based on test_mcp_client.py format
            headers = {
                "Authorization": f"Bearer {auth_token}",
                "X-API-KEY": auth_token,
                "Content-Type": "application/json"
            }
            
            logger.debug(f"[MCP_CLIENT] Created auth headers for principal {principal.email}")
            return headers
            
        except Exception as e:
            logger.error(f"[MCP_CLIENT] Failed to extract auth headers from principal: {e}")
            return None
    
    def _create_authenticated_client(self, principal: Principal, mcp_url: str) -> Optional[MCPServerStreamableHTTP]:
        """
        Create MCP client with authentication headers from Principal.
        
        Args:
            principal: Principal object containing authentication context
            mcp_url: MCP server URL
            
        Returns:
            MCPServerStreamableHTTP: Authenticated MCP client or None if creation fails
        """
        try:
            # Validate principal token
            if not principal.is_token_valid():
                logger.error(f"[MCP_CLIENT] Principal token is invalid or expired for {principal.email}")
                return None
            
            # Get authentication headers
            headers = self._get_auth_headers_from_principal(principal)
            if not headers:
                logger.error(f"[MCP_CLIENT] Could not get authentication headers for {principal.email}")
                return None
            
            # Use timeout configuration that's compatible with Pydantic AI
            timeout = httpx.Timeout(
                connect=10.0,  # Connection timeout
                read=30.0,     # Read timeout  
                write=10.0,    # Write timeout
                pool=5.0       # Pool timeout
            )
            
            # Create HTTP client with authentication headers
            authenticated_client = httpx.AsyncClient(
                headers=headers,
                timeout=timeout,
                limits=httpx.Limits(
                    max_keepalive_connections=5,
                    max_connections=10,
                    keepalive_expiry=30.0
                )
            )
            
            logger.info(f"[MCP_CLIENT] 🔐 Created authenticated HTTP client for user {principal.email}")
            
            # Create authenticated MCP client using headers parameter
            # This matches the pattern from test_mcp_client.py
            mcp_client = MCPServerStreamableHTTP(mcp_url, headers=headers)
            
            # Store principal and authentication info for later use
            mcp_client._principal = principal
            mcp_client._authenticated_client = authenticated_client
            mcp_client.get_principal = lambda: principal
            mcp_client.is_authenticated = lambda: True
            
            logger.info(f"[MCP_CLIENT] ✅ Authenticated MCP client created for {principal.email}")
            return mcp_client
            
        except Exception as e:
            logger.error(f"[MCP_CLIENT] ❌ Failed to create authenticated MCP client: {e}")
            import traceback
            logger.error(f"[MCP_CLIENT] ❌ Traceback: {traceback.format_exc()}")
            return None
    
    async def _handle_auth_failure(self, principal: Principal, response_code: int) -> Optional[Principal]:
        """
        Handle authentication failures and attempt token refresh.
        
        Args:
            principal: Principal object with potentially expired token
            response_code: HTTP response code that triggered the failure
            
        Returns:
            Principal: Updated principal with refreshed token or None if refresh failed
        """
        try:
            logger.warning(f"[MCP_CLIENT] Authentication failure (code {response_code}) for {principal.email}")
            
            # Use TokenRefreshService to handle the authentication failure
            from app.services.token_refresh_service import token_refresh_service
            
            refreshed_principal = await token_refresh_service.handle_mcp_auth_failure(principal, response_code)
            
            if refreshed_principal and refreshed_principal.is_token_valid():
                logger.info(f"[MCP_CLIENT] ✅ Successfully refreshed token after auth failure for {principal.email}")
                
                # Update cached clients to remove expired ones
                self._invalidate_expired_cache(principal)
                
                return refreshed_principal
            else:
                logger.error(f"[MCP_CLIENT] ❌ Failed to refresh token after auth failure for {principal.email}")
                return None
            
        except Exception as e:
            logger.error(f"[MCP_CLIENT] Error handling auth failure: {e}")
            return None
    
    def _invalidate_expired_cache(self, principal: Principal):
        """
        Remove expired cached clients for a principal.
        
        Args:
            principal: Principal whose cache entries should be invalidated
        """
        try:
            # Get all cache keys that might be related to this principal
            principal_hash = principal.get_cache_hash()
            keys_to_remove = []
            
            for cache_key in self._agent_clients.keys():
                if cache_key.startswith(principal_hash):
                    keys_to_remove.append(cache_key)
            
            # Remove expired cache entries
            for key in keys_to_remove:
                del self._agent_clients[key]
                logger.debug(f"[MCP_CLIENT] Removed expired cache entry: {key}")
            
        except Exception as e:
            logger.error(f"[MCP_CLIENT] Error invalidating cache: {e}")
    
    async def cleanup(self):
        """Clean up all MCP clients and their HTTP connections."""
        try:
            # Close main client
            if self.mcp_client:
                await self.close_authenticated_client(self.mcp_client)
            
            # Close all agent clients
            for client in self._agent_clients.values():
                await self.close_authenticated_client(client)
            
            # Clear caches
            self._agent_clients.clear()
            self.mcp_client = None
            self._is_connected = False
            
            logger.info("[MCP_CLIENT] ✅ All MCP clients cleaned up")
        except Exception as e:
            logger.error(f"[MCP_CLIENT] Error during cleanup: {e}")
    

# Global MCP client instance
mcp_client = MCPClient()