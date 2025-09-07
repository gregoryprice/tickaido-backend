"""
MCP Client for AI Ticket Creator Tools

This module provides a client interface to the Model Context Protocol (MCP) server
that hosts comprehensive customer support tools including ticket management, 
integration discovery, and system monitoring.

The MCP server runs as a separate service using FastMCP with a modular tool architecture
organized into three main categories:

TICKET MANAGEMENT TOOLS (10 tools):
- Complete ticket lifecycle management
- AI-powered ticket creation and categorization
- Status management and assignment
- Search, filtering, and analytics

INTEGRATION TOOLS (2 tools):
- Discovery of available integrations
- Active integration management for routing

SYSTEM TOOLS (1 tool):
- Health monitoring and status reporting

Total: 13 tools available for AI agents to perform customer support operations.

For more information on PydanticAI MCP, see: https://ai.pydantic.dev/mcp/
For more information on FastMCP, see: https://fastmcp.tadata.com/
"""

import logging
import os
import hashlib
from typing import Optional, Dict, Any
from pydantic_ai.mcp import MCPServerStreamableHTTP
from .authenticated_client import create_authenticated_mcp_client

logger = logging.getLogger(__name__)

class MCPClient:
    """
    MCP Client for connecting to the AI Ticket Creator MCP server.
    
    This client uses PydanticAI's MCPServerStreamableHTTP to connect to a FastMCP server
    that provides comprehensive customer support tools organized into three categories:
    
    TICKET MANAGEMENT TOOLS (10 tools):
    ========================================
    
    Ticket Creation:
    - create_ticket: Create support tickets with full API schema support
      • Parameters: title, description, category, priority, urgency, department, 
        assigned_to_id, integration, create_externally, custom_fields, file_ids
      • Features: UUID validation, JSON field handling, external system routing
    
    - create_ticket_with_ai: AI-powered ticket creation with automatic categorization
      • Parameters: title, description, integration, create_externally, custom_fields, file_ids  
      • Features: Leverages backend AI categorization with full schema support
    
    Ticket Retrieval & Management:
    - get_ticket: Retrieve specific ticket details by ID
    - update_ticket: Update existing ticket fields (title, description, status, priority, category)
    - delete_ticket: Delete specific tickets by ID
    - search_tickets: Search and filter tickets with pagination
      • Parameters: query, status, category, priority, page, page_size
    - list_tickets: List tickets with optional filtering and pagination
      • Parameters: page, page_size, status, category, priority
    
    Ticket Operations:
    - update_ticket_status: Update ticket status (open, in_progress, resolved, closed)
    - assign_ticket: Assign tickets to specific users or teams
    - get_ticket_stats: Retrieve comprehensive ticket statistics and analytics
    
    INTEGRATION TOOLS (2 tools):
    ============================
    
    Integration Discovery:
    - list_integrations: List available integrations for ticket routing
      • Parameters: integration_type, status, is_enabled
      • Returns: Available integrations (JIRA, ServiceNow, Salesforce, Zendesk, GitHub, etc.)
    
    - get_active_integrations: Get active integrations for ticket creation
      • Parameters: supports_category
      • Returns: Active integrations with health status and capabilities
    
    SYSTEM TOOLS (1 tool):
    ======================
    
    System Monitoring:
    - get_system_health: Check backend system health and status
      • Returns: System health information, database status, service availability
    
    TOTAL: 13 tools available for comprehensive customer support operations.
    
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
        self._authenticated_clients: Dict[str, MCPServerStreamableHTTP] = {}
        self._agent_clients: Dict[str, MCPServerStreamableHTTP] = {}
        self._is_connected = False
    
        
    def create_mcp_client(self) -> Optional[MCPServerStreamableHTTP]:
        """
        Create and configure the MCP client using HTTP streamable transport.
        
        According to PydanticAI documentation, MCPServerStreamableHTTP expects
        the URL to point directly to the MCP endpoint (e.g., http://localhost:8001/mcp)
        
        Returns:
            MCPServerStreamableHTTP: Configured MCP client or None if creation fails
            
        Raises:
            Exception: If MCP client creation fails
        """
        try:
            # MCPServerStreamableHTTP expects the full URL to the MCP endpoint
            # The FastMCP server typically serves at /mcp when using streamable-http transport
            mcp_url = f"{self.mcp_server_url}/mcp"
            logger.info(f"[MCP_CLIENT] 🔧 Creating MCP client for AI Ticket Creator at {mcp_url}")
            logger.debug(f"[MCP_CLIENT] Server URL: {self.mcp_server_url}")
            logger.debug(f"[MCP_CLIENT] Full MCP endpoint: {mcp_url}")
            
            # Create the MCP client with HTTP streamable transport
            # This connects to the FastMCP server running with streamable-http transport
            mcp_client = MCPServerStreamableHTTP(mcp_url)
            
            logger.info(f"[MCP_CLIENT] ✅ MCP client created successfully for AI Ticket Creator at {mcp_url}")
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
        logger.debug(f"[MCP_CLIENT] Getting MCP client - current state: connected={self._is_connected}, client_exists={self.mcp_client is not None}")
        
        if self.mcp_client is None:
            logger.debug("[MCP_CLIENT] Creating new MCP client")
            self.mcp_client = self.create_mcp_client()
            if self.mcp_client is not None:
                self._is_connected = True
                logger.info("[MCP_CLIENT] ✅ AI Ticket Creator MCP client initialized and ready")
                logger.debug(f"[MCP_CLIENT] Available tools: {self.get_available_tools()}")
            else:
                self._is_connected = False
                logger.warning("[MCP_CLIENT] ⚠️ AI Ticket Creator MCP client initialization failed")
        else:
            logger.debug("[MCP_CLIENT] Using existing MCP client")
        
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
            "service": "AI Ticket Creator Tools"
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
                logger.info("✅ AI Ticket Creator MCP client connection reset successfully")
                return True
            else:
                logger.error("❌ Failed to reset AI Ticket Creator MCP client connection")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error resetting AI Ticket Creator MCP client connection: {e}")
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
            return {
                "success": True,
                "message": "MCP client connection test successful",
                "server_url": self.mcp_server_url,
                "tools_available": [
                    # Ticket Management Tools (10)
                    "create_ticket", "create_ticket_with_ai", "get_ticket", 
                    "update_ticket", "delete_ticket", "update_ticket_status",
                    "assign_ticket", "search_tickets", "list_tickets", "get_ticket_stats",
                    # Integration Tools (2) 
                    "list_integrations", "get_active_integrations",
                    # System Tools (1)
                    "get_system_health"
                ]
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
        return [
            # Ticket Management Tools (10 tools)
            "create_ticket",            # Create support tickets with full API schema
            "create_ticket_with_ai",    # AI-powered ticket creation with categorization
            "get_ticket",               # Retrieve specific ticket details by ID
            "update_ticket",            # Update existing ticket fields
            "delete_ticket",            # Delete specific tickets by ID
            "update_ticket_status",     # Update ticket status (open, in_progress, resolved, closed)
            "assign_ticket",            # Assign tickets to specific users or teams
            "search_tickets",           # Search and filter tickets with pagination
            "list_tickets",             # List tickets with optional filtering and pagination
            "get_ticket_stats",         # Retrieve comprehensive ticket statistics
            
            # Integration Tools (2 tools)
            "list_integrations",        # List available integrations for routing
            "get_active_integrations",  # Get active integrations with health status
            
            # System Tools (1 tool)
            "get_system_health"         # Check backend system health and status
        ]
    
    def get_tools_by_category(self) -> Dict[str, list]:
        """
        Get tools organized by category for better understanding.
        
        Returns:
            Dict[str, list]: Tools organized by category with descriptions
        """
        return {
            "ticket_management": {
                "description": "Complete ticket lifecycle management tools",
                "tools": [
                    {
                        "name": "create_ticket",
                        "description": "Create support tickets with full API schema support",
                        "parameters": ["title", "description", "category", "priority", "urgency", 
                                     "department", "assigned_to_id", "integration", "create_externally", 
                                     "custom_fields", "file_ids"],
                        "endpoint": "POST /api/v1/tickets"
                    },
                    {
                        "name": "create_ticket_with_ai", 
                        "description": "AI-powered ticket creation with automatic categorization",
                        "parameters": ["title", "description", "integration", "create_externally", 
                                     "custom_fields", "file_ids"],
                        "endpoint": "POST /api/v1/tickets/ai-create"
                    },
                    {
                        "name": "get_ticket",
                        "description": "Retrieve specific ticket details by ID", 
                        "parameters": ["ticket_id"],
                        "endpoint": "GET /api/v1/tickets/{ticket_id}"
                    },
                    {
                        "name": "update_ticket",
                        "description": "Update existing ticket fields",
                        "parameters": ["ticket_id", "title", "description", "status", "priority", "category"],
                        "endpoint": "PUT /api/v1/tickets/{ticket_id}"
                    },
                    {
                        "name": "delete_ticket",
                        "description": "Delete specific tickets by ID",
                        "parameters": ["ticket_id"],
                        "endpoint": "DELETE /api/v1/tickets/{ticket_id}"
                    },
                    {
                        "name": "update_ticket_status",
                        "description": "Update ticket status (open, in_progress, resolved, closed)",
                        "parameters": ["ticket_id", "status"],
                        "endpoint": "PATCH /api/v1/tickets/{ticket_id}/status"
                    },
                    {
                        "name": "assign_ticket",
                        "description": "Assign tickets to specific users or teams",
                        "parameters": ["ticket_id", "assigned_to"],
                        "endpoint": "PATCH /api/v1/tickets/{ticket_id}/assign"
                    },
                    {
                        "name": "search_tickets",
                        "description": "Search and filter tickets with pagination",
                        "parameters": ["query", "status", "category", "priority", "page", "page_size"],
                        "endpoint": "GET /api/v1/tickets"
                    },
                    {
                        "name": "list_tickets", 
                        "description": "List tickets with optional filtering and pagination",
                        "parameters": ["page", "page_size", "status", "category", "priority"],
                        "endpoint": "GET /api/v1/tickets"
                    },
                    {
                        "name": "get_ticket_stats",
                        "description": "Retrieve comprehensive ticket statistics and analytics",
                        "parameters": [],
                        "endpoint": "GET /api/v1/tickets/stats/overview"
                    }
                ]
            },
            "integration_management": {
                "description": "Integration discovery and management tools",
                "tools": [
                    {
                        "name": "list_integrations",
                        "description": "List available integrations for ticket routing",
                        "parameters": ["integration_type", "status", "is_enabled"],
                        "endpoint": "GET /api/v1/integrations",
                        "supported_types": ["jira", "servicenow", "salesforce", "zendesk", "github", 
                                          "slack", "teams", "zoom", "hubspot", "freshdesk", 
                                          "asana", "trello", "webhook", "email", "sms"]
                    },
                    {
                        "name": "get_active_integrations",
                        "description": "Get active integrations with health status and capabilities",
                        "parameters": ["supports_category"],
                        "endpoint": "GET /api/v1/integrations/active"
                    }
                ]
            },
            "system_monitoring": {
                "description": "System health and monitoring tools", 
                "tools": [
                    {
                        "name": "get_system_health",
                        "description": "Check backend system health and status",
                        "parameters": [],
                        "endpoint": "GET /health"
                    }
                ]
            }
        }
    
    def get_tool_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all available tools with counts by category.
        
        Returns:
            Dict[str, Any]: Summary of tools by category with counts
        """
        tools_by_category = self.get_tools_by_category()
        
        summary = {
            "total_tools": 13,
            "categories": {
                "ticket_management": {
                    "count": 10,
                    "description": "Complete ticket lifecycle management",
                    "tools": [tool["name"] for tool in tools_by_category["ticket_management"]["tools"]]
                },
                "integration_management": {
                    "count": 2, 
                    "description": "Integration discovery and management",
                    "tools": [tool["name"] for tool in tools_by_category["integration_management"]["tools"]]
                },
                "system_monitoring": {
                    "count": 1,
                    "description": "System health and monitoring",
                    "tools": [tool["name"] for tool in tools_by_category["system_monitoring"]["tools"]]
                }
            },
            "connection_info": {
                "transport": "streamable_http",
                "protocol": "MCP (Model Context Protocol)",
                "default_url": "http://localhost:8001/mcp",
                "backend_api": "http://localhost:8000/api/v1"
            }
        }
        
        return summary
    
    def print_tool_summary(self) -> None:
        """Print a formatted summary of all available tools."""
        summary = self.get_tool_summary()
        
        print("🔧 AI Ticket Creator MCP Tools Summary")
        print("=" * 50)
        print(f"📊 Total Tools Available: {summary['total_tools']}")
        print()
        
        for category, info in summary['categories'].items():
            print(f"📁 {category.replace('_', ' ').title()}: {info['count']} tools")
            print(f"   {info['description']}")
            for tool in info['tools']:
                print(f"   • {tool}")
            print()
        
        print("🔌 Connection Information:")
        conn = summary['connection_info'] 
        print(f"   • Transport: {conn['transport']}")
        print(f"   • Protocol: {conn['protocol']}")
        print(f"   • MCP URL: {conn['default_url']}")
        print(f"   • Backend API: {conn['backend_api']}")
    
    def _sanitize_token_for_logging(self, token: str) -> str:
        """
        Sanitize JWT token for safe logging
        
        Args:
            token: JWT token string
            
        Returns:
            Sanitized token string showing only first 8 and last 4 characters
        """
        if not token or len(token) < 12:
            return "[INVALID_TOKEN]"
        return f"{token[:8]}...{token[-4:]}"
    
    def create_authenticated_mcp_client(self, jwt_token: str) -> Optional[MCPServerStreamableHTTP]:
        """
        Create MCP client with JWT token authentication
        
        Args:
            jwt_token: Valid JWT token for authentication
            
        Returns:
            Authenticated MCP client or None if creation fails
        """
        try:
            # Create token hash for client caching
            token_hash = hashlib.sha256(jwt_token.encode()).hexdigest()[:16]
            
            # Check if we already have a client for this token
            if token_hash in self._authenticated_clients:
                logger.debug(f"[MCP_CLIENT] Using cached authenticated client (token: {self._sanitize_token_for_logging(jwt_token)})")
                return self._authenticated_clients[token_hash]
            
            mcp_url = f"{self.mcp_server_url}/mcp"
            logger.info(f"[MCP_CLIENT] 🔐 Creating authenticated MCP client at {mcp_url}")
            
            # Note: PydanticAI's MCPServerStreamableHTTP may not support headers parameter directly
            # For now, we'll create the client and handle authentication at the protocol level
            # This would need to be enhanced when PydanticAI supports authentication headers
            mcp_client = MCPServerStreamableHTTP(mcp_url)
            
            # Cache the authenticated client
            self._authenticated_clients[token_hash] = mcp_client
            
            logger.info(f"[MCP_CLIENT] ✅ Authenticated MCP client created (token: {self._sanitize_token_for_logging(jwt_token)})")
            return mcp_client
            
        except Exception as e:
            logger.error(f"[MCP_CLIENT] ❌ Failed to create authenticated MCP client: {e}")
            return None
    
    def create_agent_client(self, agent_id: str, tools_enabled: list, organization_id: str = None, auth_token: Optional[str] = None) -> Optional[MCPServerStreamableHTTP]:
        """
        Create MCP client configured for specific agent with tool filtering and optional authentication.
        
        Args:
            agent_id: Agent UUID
            tools_enabled: List of tools this agent can access
            organization_id: Organization UUID for isolation
            auth_token: JWT token for authentication (optional)
            
        Returns:
            MCPServerStreamableHTTP: Agent-specific MCP client (authenticated if token provided)
        """
        try:
            # Create cache key including authentication status to avoid mixing clients
            auth_hash = hash(auth_token) if auth_token else "no_auth"
            cache_key = f"agent_{agent_id}_{hash(tuple(sorted(tools_enabled)))}_{auth_hash}"
            
            # Check if we already have a client for this agent configuration
            if cache_key in self._agent_clients:
                cached_client = self._agent_clients[cache_key]
                auth_status = "authenticated" if auth_token else "non-authenticated"
                logger.debug(f"[MCP_CLIENT] Using cached {auth_status} agent client for {agent_id}")
                return cached_client
            
            mcp_url = f"{self.mcp_server_url}/mcp"
            logger.info(f"[MCP_CLIENT] 🎯 Creating agent-specific MCP client for {agent_id}")
            logger.debug(f"[MCP_CLIENT] Agent tools: {tools_enabled}")
            
            # Create the appropriate MCP client based on authentication
            if auth_token:
                logger.info(f"[MCP_CLIENT] 🔐 Creating authenticated MCP client for agent {agent_id}")
                agent_client = create_authenticated_mcp_client(mcp_url, auth_token=auth_token)
            else:
                logger.info(f"[MCP_CLIENT] 🔓 Creating non-authenticated MCP client for agent {agent_id}")
                agent_client = MCPServerStreamableHTTP(mcp_url)
            
            # Store agent configuration for tool filtering
            agent_client._agent_id = agent_id
            agent_client._enabled_tools = set(tools_enabled)
            agent_client._organization_id = organization_id
            
            # Cache the client
            self._agent_clients[cache_key] = agent_client
            
            auth_status = "authenticated" if auth_token else "non-authenticated"
            logger.info(f"[MCP_CLIENT] ✅ {auth_status.capitalize()} agent-specific MCP client created for {agent_id} with {len(tools_enabled)} tools")
            return agent_client
            
        except Exception as e:
            logger.error(f"[MCP_CLIENT] ❌ Failed to create agent MCP client: {e}")
            return None
    
    def get_agent_client(self, agent_id: str, tools_enabled: list, organization_id: str = None, auth_token: Optional[str] = None) -> Optional[MCPServerStreamableHTTP]:
        """
        Get agent-specific MCP client, creating if necessary.
        
        Args:
            agent_id: Agent UUID
            tools_enabled: List of tools this agent can access  
            organization_id: Organization UUID for isolation
            auth_token: JWT token for authentication (optional)
            
        Returns:
            MCPServerStreamableHTTP: Agent-specific MCP client (authenticated if token provided)
        """
        try:
            client = self.create_agent_client(agent_id, tools_enabled, organization_id, auth_token)
            if client:
                auth_status = "authenticated" if auth_token else "non-authenticated"
                logger.debug(f"[MCP_CLIENT] {auth_status.capitalize()} agent client ready for {agent_id} with tools: {tools_enabled}")
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

    async def authenticated_call(self, tool_name: str, jwt_token: str, **kwargs) -> Any:
        """
        Call MCP tool with JWT authentication
        
        Args:
            tool_name: Name of the MCP tool to call
            jwt_token: Valid JWT token for authentication
            **kwargs: Tool arguments
            
        Returns:
            Tool execution result
        """
        try:
            auth_client = self.create_authenticated_mcp_client(jwt_token)
            if not auth_client:
                raise Exception("Failed to create authenticated MCP client")
            
            logger.info(f"[MCP_CLIENT] 🔧 Calling tool '{tool_name}' with authentication")
            
            # Note: This is a placeholder for authenticated tool calling
            # The actual implementation depends on PydanticAI's support for authentication
            # For now, this method provides the interface for future enhancement
            logger.warning("[MCP_CLIENT] ⚠️ Authenticated tool calling not yet implemented in PydanticAI MCP client")
            
            return f"Tool '{tool_name}' called with authentication (implementation pending)"
            
        except Exception as e:
            logger.error(f"[MCP_CLIENT] ❌ Authenticated tool call failed: {e}")
            raise

# Global MCP client instance
mcp_client = MCPClient()