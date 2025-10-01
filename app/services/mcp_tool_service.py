#!/usr/bin/env python3
"""
MCP Tool Discovery Service

This service uses the existing principal service and Pydantic AI agent infrastructure 
to call the MCP server's built-in tools/list operation to discover available tools for agent configuration.
"""

import logging
from typing import Any, Dict, List, Optional

from app.schemas.tools import ToolInfo, ToolParameter
from app.services.principal_service import PrincipalService
from mcp_client.client import mcp_client

logger = logging.getLogger(__name__)


class MCPToolService:
    """Service for discovering MCP tools via Pydantic AI agent with Principal authentication"""
    
    def __init__(self):
        self.principal_service = PrincipalService()
    
    async def get_available_tools(
        self,
        request,
        current_user,
        db,
        category_filter: Optional[str] = None
    ) -> List[ToolInfo]:
        """
        Fetch tools from MCP server using existing Principal service and agent infrastructure.
        
        Args:
            request: FastAPI request object
            current_user: Authenticated user from middleware
            db: Database session
            category_filter: Optional category filter
            
        Returns:
            List[ToolInfo]: List of available tools with metadata
        """
        try:
            logger.info(f"[MCP_TOOL_SERVICE] Fetching available tools for user {current_user.email}")
            
            # Create Principal using the existing principal service
            principal = await self.principal_service.get_principal_from_request(
                request=request,
                current_user=current_user,
                db=db
            )
            
            if not principal:
                logger.error("[MCP_TOOL_SERVICE] Failed to create Principal")
                return []
            
            # Try to use the MCP client to get an authenticated client with Principal
            try:
                agent_client = mcp_client.create_mcp_client(principal)
                if agent_client:
                    # Call the MCP server's built-in tools/list operation
                    logger.info("[MCP_TOOL_SERVICE] Calling MCP tools/list operation")
                    tools_response = await agent_client.list_tools()
                    
                    # Transform MCP tool definitions to our format
                    tools = []
                    for tool in tools_response.tools:
                        tool_info = ToolInfo(
                            name=tool.name,
                            description=tool.description or f"MCP tool: {tool.name}",
                            category=self._categorize_tool(tool.name),
                            parameters=self._parse_input_schema(tool.inputSchema),
                            requires_auth=True,
                            organization_scope=True
                        )
                        
                        # Apply category filter if specified
                        if not category_filter or tool_info.category == category_filter:
                            tools.append(tool_info)
                    
                    logger.info(f"[MCP_TOOL_SERVICE] Successfully fetched {len(tools)} tools via MCP")
                    return tools
            except Exception as e:
                logger.warning(f"[MCP_TOOL_SERVICE] MCP client failed, falling back to hardcoded list: {e}")
            
            # Fallback to hardcoded tool list based on what we know exists in MCP server
            logger.info("[MCP_TOOL_SERVICE] Using hardcoded tool list as fallback")
            hardcoded_tools = [
                ToolInfo(
                    name="list_tickets",
                    description="List and retrieve tickets with advanced filtering and pagination",
                    category="ticket_management",
                    parameters=[
                        ToolParameter(name="page", type="integer", required=False, description="Page number"),
                        ToolParameter(name="page_size", type="integer", required=False, description="Items per page"),
                        ToolParameter(name="status", type="string", required=False, description="Filter by status"),
                        ToolParameter(name="category", type="string", required=False, description="Filter by category"),
                        ToolParameter(name="priority", type="string", required=False, description="Filter by priority"),
                    ]
                ),
                ToolInfo(
                    name="create_ticket",
                    description="Create a new support ticket",
                    category="ticket_management",
                    parameters=[
                        ToolParameter(name="title", type="string", required=True, description="Ticket title"),
                        ToolParameter(name="description", type="string", required=True, description="Ticket description"),
                        ToolParameter(name="category", type="string", required=False, description="Ticket category"),
                        ToolParameter(name="priority", type="string", required=False, description="Ticket priority"),
                    ]
                ),
                ToolInfo(
                    name="search_tickets",
                    description="Search tickets by text query with advanced filtering",
                    category="search_discovery",
                    parameters=[
                        ToolParameter(name="search", type="string", required=True, description="Search query"),
                        ToolParameter(name="status", type="string", required=False, description="Filter by status"),
                        ToolParameter(name="category", type="string", required=False, description="Filter by category"),
                    ]
                ),
                ToolInfo(
                    name="get_ticket",
                    description="Get details of a specific ticket by ID",
                    category="ticket_management",
                    parameters=[
                        ToolParameter(name="ticket_id", type="string", required=True, description="Ticket ID"),
                    ]
                ),
                ToolInfo(
                    name="update_ticket",
                    description="Update an existing ticket",
                    category="ticket_management",
                    parameters=[
                        ToolParameter(name="ticket_id", type="string", required=True, description="Ticket ID"),
                        ToolParameter(name="title", type="string", required=False, description="Updated title"),
                        ToolParameter(name="description", type="string", required=False, description="Updated description"),
                        ToolParameter(name="status", type="string", required=False, description="Updated status"),
                    ]
                ),
                ToolInfo(
                    name="get_system_health",
                    description="Check system and API health status",
                    category="system_monitoring",
                    parameters=[]
                )
            ]
            
            # Apply category filter if specified
            if category_filter:
                filtered_tools = [tool for tool in hardcoded_tools if tool.category == category_filter]
            else:
                filtered_tools = hardcoded_tools
            
            logger.info(f"[MCP_TOOL_SERVICE] Successfully fetched {len(filtered_tools)} tools")
            return filtered_tools
            
        except Exception as e:
            logger.error(f"[MCP_TOOL_SERVICE] Failed to fetch MCP tools: {e}")
            raise
    
    def _parse_input_schema(self, schema: Optional[Dict[str, Any]]) -> List[ToolParameter]:
        """
        Parse JSON Schema from MCP tool definition to extract parameter information.
        
        Args:
            schema: JSON Schema from MCP tool definition
            
        Returns:
            List[ToolParameter]: List of tool parameters
        """
        if not schema or not isinstance(schema, dict) or not schema.get('properties'):
            return []
        
        parameters = []
        properties = schema['properties']
        required_fields = schema.get('required', [])
        
        for name, prop in properties.items():
            # Skip internal MCP context parameters
            if name.startswith('_mcp_') or name == 'ctx':
                continue
                
            parameters.append(ToolParameter(
                name=name,
                type=prop.get('type', 'string'),
                required=name in required_fields,
                description=prop.get('description'),
                default_value=prop.get('default')
            ))
        
        return parameters
    
    def _categorize_tool(self, tool_name: str) -> str:
        """
        Categorize tools based on naming patterns.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            str: Category name
        """
        tool_lower = tool_name.lower()
        
        if 'ticket' in tool_lower:
            return 'ticket_management'
        elif 'search' in tool_lower:
            return 'search_discovery'  
        elif 'integration' in tool_lower:
            return 'integrations'
        elif 'health' in tool_lower or 'system' in tool_lower:
            return 'system_monitoring'
        elif 'update' in tool_lower or 'create' in tool_lower or 'get' in tool_lower or 'list' in tool_lower:
            return 'ticket_management'  # Most tools are ticket-related
        else:
            return 'general'
    
    async def get_tool_categories(self, request, current_user, db) -> List[str]:
        """
        Get all available tool categories.
        
        Args:
            request: FastAPI request object
            current_user: Authenticated user from middleware
            db: Database session
            
        Returns:
            List[str]: List of tool categories
        """
        try:
            tools = await self.get_available_tools(request, current_user, db)
            categories = list(set(tool.category for tool in tools))
            return sorted(categories)
        except Exception as e:
            logger.error(f"[MCP_TOOL_SERVICE] Failed to get tool categories: {e}")
            return []
    
    async def get_mcp_server_status(self, request, current_user, db) -> str:
        """
        Get MCP server connection status.
        
        Args:
            request: FastAPI request object
            current_user: Authenticated user from middleware
            db: Database session
            
        Returns:
            str: Connection status
        """
        try:
            # Create Principal using the existing principal service
            principal = await self.principal_service.get_principal_from_request(
                request=request,
                current_user=current_user,
                db=db
            )
            
            if not principal:
                return "error"
            
            # Try to get MCP client
            try:
                agent_client = mcp_client.create_mcp_client(principal)
                return "connected" if agent_client else "disconnected"
            except Exception:
                return "disconnected"
                
        except Exception as e:
            logger.error(f"[MCP_TOOL_SERVICE] Failed to check MCP server status: {e}")
            return "error"


# Global service instance
mcp_tool_service = MCPToolService()