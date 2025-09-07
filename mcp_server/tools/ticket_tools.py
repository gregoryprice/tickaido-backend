#!/usr/bin/env python3
"""
Ticket Management Tools for MCP Server

This module contains all ticket-related MCP tools including:
- Ticket creation (standard and AI-powered)
- Ticket retrieval, updating, and deletion
- Status and assignment management
- Ticket statistics and listing
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Optional
import httpx
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
    from tools import BACKEND_URL, log_tool_call
    from tools.http_client import get_http_client

# Get MCP instance from parent module - will be set by register_all_ticket_tools
mcp = None


# =============================================================================
# TICKET CREATION TOOLS
# =============================================================================

async def _create_ticket_raw(
    title: str,
    description: str,
    category: str = "general",
    priority: str = "medium",
    urgency: str = "medium",
    department: str = "",
    assigned_to_id: str = "",
    integration: str = "",
    create_externally: str = "false",
    custom_fields: str = "{}",
    file_ids: str = ""
) -> str:
    """Raw function for create_ticket - used for testing (legacy, non-authenticated)"""
    start_time = datetime.now()
    arguments = {
        "title": title, "description": description, "category": category, "priority": priority,
        "urgency": urgency, "department": department, "assigned_to_id": assigned_to_id,
        "integration": integration, "create_externally": create_externally,
        "custom_fields": custom_fields, "file_ids": file_ids
    }
    
    try:
        # Build the request data according to API schema
        ticket_data = {
            "title": title,
            "description": description,
            "category": category,
            "priority": priority,
            "urgency": urgency
        }
        
        # Add optional fields
        if department:
            ticket_data["department"] = department
        if assigned_to_id:
            try:
                # Validate UUID format
                import uuid
                uuid.UUID(assigned_to_id)
                ticket_data["assigned_to_id"] = assigned_to_id
            except ValueError:
                pass  # Skip invalid UUID
        if integration:
            ticket_data["integration"] = integration
        if create_externally.lower() == "true":
            ticket_data["create_externally"] = True
        
        # Handle custom fields JSON
        if custom_fields and custom_fields != "{}":
            try:
                ticket_data["custom_fields"] = json.loads(custom_fields)
            except json.JSONDecodeError:
                pass  # Skip invalid JSON
        
        # Handle file IDs
        if file_ids:
            file_id_list = []
            for file_id in file_ids.split(","):
                file_id = file_id.strip()
                if file_id:
                    try:
                        # Validate UUID format
                        import uuid
                        uuid.UUID(file_id)
                        file_id_list.append(file_id)
                    except ValueError:
                        pass  # Skip invalid UUID
            if file_id_list:
                ticket_data["file_ids"] = file_id_list
        
        # Use original httpx client for legacy testing function
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.post(
                f"{BACKEND_URL}/api/v1/tickets",
                json=ticket_data,
                timeout=30.0
            )
        
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        if response.status_code in [200, 201]:
            result_data = response.json()
            log_tool_call("create_ticket", arguments, json.dumps(result_data), execution_time, "success")
            return json.dumps(result_data, indent=2)
        else:
            error_msg = f"Error: HTTP {response.status_code} - {response.text}"
            log_tool_call("create_ticket", arguments, error_msg, execution_time, "error")
            return error_msg
                
    except httpx.ConnectError:
        error_msg = f"Error: Cannot connect to backend server. Please ensure the server is running on {BACKEND_URL}"
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        log_tool_call("create_ticket", arguments, error_msg, execution_time, "error")
        return error_msg
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        log_tool_call("create_ticket", arguments, error_msg, execution_time, "error")
        return error_msg

def register_create_ticket():
    @mcp.tool()
    async def create_ticket(
        title: str,
        description: str,
        category: str = "general",
        priority: str = "medium",
        urgency: str = "medium",
        department: str = "",
        assigned_to_id: str = "",
        integration: str = "",
        create_externally: str = "false",
        custom_fields: str = "{}",
        file_ids: str = "",
        context: Optional[Any] = None
    ) -> str:
        """
        Create a support ticket with specified details and optional routing to integrations.
        
        Args:
            title: Ticket title/subject (required)
            description: Detailed description of the issue (required)
            category: Issue category (technical, billing, feature_request, bug, user_access, general)
            priority: Priority level (low, medium, high, critical)
            urgency: Urgency level (low, medium, high, critical)
            department: Department to route ticket to (optional)
            assigned_to_id: UUID of user to assign ticket to (optional)
            integration: Integration name to use (jira, servicenow, salesforce, zendesk, etc.)
            create_externally: Whether to create in external system (true/false)
            custom_fields: JSON string of custom field mappings (optional)
            file_ids: Comma-separated list of file UUIDs to attach (optional)
        
        Returns:
            JSON string containing ticket creation results with ticket ID and integration details
        """
        start_time = datetime.now()
        arguments = {
            "title": title, "description": description, "category": category, "priority": priority,
            "urgency": urgency, "department": department, "assigned_to_id": assigned_to_id,
            "integration": integration, "create_externally": create_externally,
            "custom_fields": custom_fields, "file_ids": file_ids
        }
        
        try:
            # Build the request data according to API schema
            ticket_data = {
                "title": title,
                "description": description,
                "category": category,
                "priority": priority,
                "urgency": urgency
            }
            
            # Add optional fields
            if department:
                ticket_data["department"] = department
            if assigned_to_id:
                try:
                    # Validate UUID format
                    import uuid
                    uuid.UUID(assigned_to_id)
                    ticket_data["assigned_to_id"] = assigned_to_id
                except ValueError:
                    pass  # Skip invalid UUID
            if integration:
                ticket_data["integration"] = integration
            if create_externally.lower() == "true":
                ticket_data["create_externally"] = True
            
            # Handle custom fields JSON
            if custom_fields and custom_fields != "{}":
                try:
                    ticket_data["custom_fields"] = json.loads(custom_fields)
                except json.JSONDecodeError:
                    pass  # Skip invalid JSON
            
            # Handle file IDs
            if file_ids:
                file_id_list = []
                for file_id in file_ids.split(","):
                    file_id = file_id.strip()
                    if file_id:
                        try:
                            # Validate UUID format
                            import uuid
                            uuid.UUID(file_id)
                            file_id_list.append(file_id)
                        except ValueError:
                            pass  # Skip invalid UUID
                if file_id_list:
                    ticket_data["file_ids"] = file_id_list
            
            # Use http_client for backend calls (middleware handles auth)
            http_client = await get_http_client()
            response = await http_client.make_request(
                method="POST",
                endpoint="/api/v1/tickets",
                json=ticket_data
            )
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            if response.status_code in [200, 201]:
                result_data = response.json()
                log_tool_call("create_ticket", arguments, json.dumps(result_data), execution_time, "success")
                return json.dumps(result_data, indent=2)
            else:
                error_msg = f"Error: HTTP {response.status_code} - {response.text}"
                log_tool_call("create_ticket", arguments, error_msg, execution_time, "error")
                return error_msg
                
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            log_tool_call("create_ticket", arguments, error_msg, execution_time, "error")
            return error_msg

def register_create_ticket_with_ai():
    @mcp.tool()
    async def create_ticket_with_ai(
        title: str,
        description: str,
        integration: str = "",
        create_externally: str = "false",
        custom_fields: str = "{}",
        file_ids: str = "",
        context: Optional[Any] = None
    ) -> str:
        """
        Create a support ticket using AI categorization and processing.
        
        Args:
            title: Ticket title/subject (required)
            description: Detailed description of the issue (required)
            integration: Integration name to use (jira, servicenow, salesforce, zendesk, etc.)
            create_externally: Whether to create in external system (true/false)
            custom_fields: JSON string of custom field mappings (optional)
            file_ids: Comma-separated list of file UUIDs to attach (optional)
        
        Returns:
            JSON string containing AI-processed ticket creation results
        """
        start_time = datetime.now()
        arguments = {
            "title": title, "description": description, "integration": integration,
            "create_externally": create_externally, "custom_fields": custom_fields, "file_ids": file_ids
        }
        
        try:
            # Extract user context from middleware (set by TokenAuthMiddleware)
            user_context = getattr(context, 'user_context', None) if context else None
            user_token = getattr(context, 'user_token', None) if context else None
            
            if not user_context:
                return "Authentication required: MCP tools need user context. Please call through authenticated AI chat session."
            
            logger.info(f"[MCP_TOOL] Authenticated create_ticket_with_ai for user {user_context.user_id}")
            
            # Build the request data according to API schema
            ticket_data = {
                "title": title,
                "description": description
            }
            
            # Add optional fields
            if integration:
                ticket_data["integration"] = integration
            if create_externally.lower() == "true":
                ticket_data["create_externally"] = True
            
            # Handle custom fields JSON
            if custom_fields and custom_fields != "{}":
                try:
                    ticket_data["custom_fields"] = json.loads(custom_fields)
                except json.JSONDecodeError:
                    pass  # Skip invalid JSON
            
            # Handle file IDs
            if file_ids:
                file_id_list = []
                for file_id in file_ids.split(","):
                    file_id = file_id.strip()
                    if file_id:
                        try:
                            # Validate UUID format
                            import uuid
                            uuid.UUID(file_id)
                            file_id_list.append(file_id)
                        except ValueError:
                            pass  # Skip invalid UUID
                if file_id_list:
                    ticket_data["file_ids"] = file_id_list
            
            # Use http_client for authenticated backend calls
            http_client = await get_http_client()
            
            # Build authentication headers from user token
            auth_headers = {"Authorization": f"Bearer {user_token}"} if user_token else {}
            
            if not user_token:
                logger.warning("[MCP_TOOL] No user token available for backend authentication")
                return "Authentication error: Missing user token for backend API calls"
            
            response = await http_client.make_request(
                method="POST",
                endpoint="/api/v1/tickets/ai-create",
                auth_headers=auth_headers,
                json=ticket_data
            )
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            if response.status_code in [200, 201]:
                log_tool_call("create_ticket_with_ai", arguments, response.text, execution_time, "success")
                return response.text
            else:
                error_msg = f"Error: HTTP {response.status_code} - {response.text}"
                log_tool_call("create_ticket_with_ai", arguments, error_msg, execution_time, "error")
                return error_msg
                
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            log_tool_call("create_ticket_with_ai", arguments, error_msg, execution_time, "error")
            return error_msg

# =============================================================================
# TICKET RETRIEVAL AND MANAGEMENT TOOLS
# =============================================================================

def register_get_ticket():
    @mcp.tool()
    async def get_ticket(ticket_id: str, context: Optional[Any] = None) -> str:
        """
        Retrieve a specific ticket by ID.
        
        Args:
            ticket_id: ID of the ticket to retrieve (required)
        
        Returns:
            JSON string containing ticket details
        """
        start_time = datetime.now()
        arguments = {"ticket_id": ticket_id}
        
        try:
            # Use http_client for backend calls (middleware handles auth)
            http_client = await get_http_client()
            response = await http_client.make_request(
                method="GET",
                endpoint=f"/api/v1/tickets/{ticket_id}"
            )
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            if response.status_code == 200:
                log_tool_call("get_ticket", arguments, response.text, execution_time, "success")
                return response.text
            else:
                error_msg = f"Error: HTTP {response.status_code} - {response.text}"
                log_tool_call("get_ticket", arguments, error_msg, execution_time, "error")
                return error_msg
                
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            log_tool_call("get_ticket", arguments, error_msg, execution_time, "error")
            return error_msg

async def _update_ticket_raw(
    ticket_id: str,
    title: str = "",
    description: str = "",
    status: str = "",
    priority: str = "",
    category: str = ""
) -> str:
    """Raw function for updating tickets (for testing)"""
    start_time = datetime.now()
    arguments = {
        "ticket_id": ticket_id, "title": title, "description": description,
        "status": status, "priority": priority, "category": category
    }
    
    try:
        # Build update data with only provided fields
        update_data = {}
        if title: update_data["title"] = title
        if description: update_data["description"] = description
        if status: update_data["status"] = status
        if priority: update_data["priority"] = priority
        if category: update_data["category"] = category
        
        if not update_data:
            error_msg = "Error: At least one field must be provided for update"
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            log_tool_call("update_ticket", arguments, error_msg, execution_time, "error")
            return error_msg
        
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.put(
                f"{BACKEND_URL}/api/v1/tickets/{ticket_id}",
                json=update_data,
                timeout=30.0
            )
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            if response.status_code == 200:
                log_tool_call("update_ticket", arguments, response.text, execution_time, "success")
                return response.text
            else:
                error_msg = f"Error: HTTP {response.status_code} - {response.text}"
                log_tool_call("update_ticket", arguments, error_msg, execution_time, "error")
                return error_msg
                
    except Exception as e:
        error_msg = f"Error: Cannot connect to backend server: {str(e)}"
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        log_tool_call("update_ticket", arguments, error_msg, execution_time, "error")
        return error_msg

def register_update_ticket():
    @mcp.tool()
    async def update_ticket(
        ticket_id: str,
        title: str = "",
        description: str = "",
        status: str = "",
        priority: str = "",
        category: str = "",
        context: Optional[Any] = None
    ) -> str:
        """
        Update an existing support ticket with new information.
        
        Args:
            ticket_id: ID of the ticket to update (required)
            title: New ticket title (optional)
            description: Updated description (optional)
            status: New status (open, in_progress, resolved, closed) (optional)
            priority: New priority level (low, medium, high, critical) (optional)
            category: New category (optional)
        
        Returns:
            JSON string containing updated ticket information
        """
        start_time = datetime.now()
        arguments = {
            "ticket_id": ticket_id, "title": title, "description": description,
            "status": status, "priority": priority, "category": category
        }
        
        try:
            # Build update data with only provided fields
            update_data = {}
            if title: update_data["title"] = title
            if description: update_data["description"] = description
            if status: update_data["status"] = status
            if priority: update_data["priority"] = priority
            if category: update_data["category"] = category
            
            if not update_data:
                error_msg = "Error: At least one field must be provided for update"
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                log_tool_call("update_ticket", arguments, error_msg, execution_time, "error")
                return error_msg
            
            # Use http_client for backend calls (middleware handles auth)
            http_client = await get_http_client()
            response = await http_client.make_request(
                method="PUT",
                endpoint=f"/api/v1/tickets/{ticket_id}",
                json=update_data
            )
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            if response.status_code == 200:
                log_tool_call("update_ticket", arguments, response.text, execution_time, "success")
                return response.text
            else:
                error_msg = f"Error: HTTP {response.status_code} - {response.text}"
                log_tool_call("update_ticket", arguments, error_msg, execution_time, "error")
                return error_msg
                
        except Exception as e:
            error_msg = f"Error: Cannot connect to backend server: {str(e)}"
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            log_tool_call("update_ticket", arguments, error_msg, execution_time, "error")
            return error_msg

def register_delete_ticket():
    @mcp.tool()
    async def delete_ticket(ticket_id: str, context: Optional[Any] = None) -> str:
        """
        Delete a specific ticket by ID.
        
        Args:
            ticket_id: ID of the ticket to delete (required)
        
        Returns:
            JSON string containing deletion confirmation
        """
        start_time = datetime.now()
        arguments = {"ticket_id": ticket_id}
        
        try:
            # Use http_client for backend calls (middleware handles auth)
            http_client = await get_http_client()
            response = await http_client.make_request(
                method="DELETE",
                endpoint=f"/api/v1/tickets/{ticket_id}"
            )
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            if response.status_code == 200:
                log_tool_call("delete_ticket", arguments, response.text, execution_time, "success")
                return response.text
            else:
                error_msg = f"Error: HTTP {response.status_code} - {response.text}"
                log_tool_call("delete_ticket", arguments, error_msg, execution_time, "error")
                return error_msg
                
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            log_tool_call("delete_ticket", arguments, error_msg, execution_time, "error")
            return error_msg

# =============================================================================
# TICKET STATUS AND ASSIGNMENT TOOLS
# =============================================================================

def register_update_ticket_status():
    @mcp.tool()
    async def update_ticket_status(ticket_id: str, status: str, context: Optional[Any] = None) -> str:
        """
        Update the status of a specific ticket.
        
        Args:
            ticket_id: ID of the ticket to update (required)
            status: New status (open, in_progress, resolved, closed) (required)
        
        Returns:
            JSON string containing updated ticket information
        """
        start_time = datetime.now()
        arguments = {"ticket_id": ticket_id, "status": status}
        
        try:
            # Use http_client for backend calls (middleware handles auth)
            http_client = await get_http_client()
            response = await http_client.make_request(
                method="PATCH",
                endpoint=f"/api/v1/tickets/{ticket_id}/status",
                json={"status": status}
            )
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            if response.status_code == 200:
                log_tool_call("update_ticket_status", arguments, response.text, execution_time, "success")
                return response.text
            else:
                error_msg = f"Error: HTTP {response.status_code} - {response.text}"
                log_tool_call("update_ticket_status", arguments, error_msg, execution_time, "error")
                return error_msg
                
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            log_tool_call("update_ticket_status", arguments, error_msg, execution_time, "error")
            return error_msg

def register_assign_ticket():
    @mcp.tool()
    async def assign_ticket(ticket_id: str, assigned_to: str, context: Optional[Any] = None) -> str:
        """
        Assign a ticket to a specific user or team.
        
        Args:
            ticket_id: ID of the ticket to assign (required)
            assigned_to: User ID or team name to assign the ticket to (required)
        
        Returns:
            JSON string containing updated ticket assignment information
        """
        start_time = datetime.now()
        arguments = {"ticket_id": ticket_id, "assigned_to": assigned_to}
        
        try:
            # Use http_client for backend calls (middleware handles auth)
            http_client = await get_http_client()
            response = await http_client.make_request(
                method="PATCH",
                endpoint=f"/api/v1/tickets/{ticket_id}/assign",
                json={"assigned_to": assigned_to}
            )
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            if response.status_code == 200:
                log_tool_call("assign_ticket", arguments, response.text, execution_time, "success")
                return response.text
            else:
                error_msg = f"Error: HTTP {response.status_code} - {response.text}"
                log_tool_call("assign_ticket", arguments, error_msg, execution_time, "error")
                return error_msg
                
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            log_tool_call("assign_ticket", arguments, error_msg, execution_time, "error")
            return error_msg

# =============================================================================
# TICKET LISTING AND STATISTICS TOOLS
# =============================================================================

def register_search_tickets():
    @mcp.tool()
    async def search_tickets(
        query: str = "",
        status: str = "",
        category: str = "",
        priority: str = "",
        page: int = 1,
        page_size: int = 10,
        context: Optional[Any] = None
    ) -> str:
        """
        Search for tickets based on various criteria.
        
        Args:
            query: Search query for title and description (optional)
            status: Filter by status (open, in_progress, resolved, closed) (optional)
            category: Filter by category (optional)
            priority: Filter by priority (optional)
            page: Page number for pagination (default: 1)
            page_size: Number of results per page (default: 10, max: 50)
        
        Returns:
            JSON string containing search results with pagination information
        """
        start_time = datetime.now()
        arguments = {
            "query": query, "status": status, "category": category,
            "priority": priority, "page": page, "page_size": page_size
        }
        
        try:
            # Validate page_size parameter
            if not isinstance(page_size, int) or page_size < 1 or page_size > 50:
                page_size = min(50, max(1, page_size))
            
            # Build query parameters
            params = {"page": page, "page_size": page_size}
            if query: params["q"] = query
            if status: params["status"] = status
            if category: params["category"] = category
            if priority: params["priority"] = priority
            
            # Use http_client for backend calls (middleware handles auth)
            http_client = await get_http_client()
            response = await http_client.make_request(
                method="GET",
                endpoint="/api/v1/tickets",
                params=params
            )
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            if response.status_code == 200:
                log_tool_call("search_tickets", arguments, response.text, execution_time, "success")
                return response.text
            else:
                error_msg = f"Error: HTTP {response.status_code} - {response.text}"
                log_tool_call("search_tickets", arguments, error_msg, execution_time, "error")
                return error_msg
                
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            log_tool_call("search_tickets", arguments, error_msg, execution_time, "error")
            return error_msg

def register_list_tickets():
    @mcp.tool()
    async def list_tickets(
        page: int = 1,
        page_size: int = 10,
        status: str = "",
        category: str = "",
        priority: str = "",
        context: Optional[Any] = None
    ) -> str:
        """
        List tickets with optional filtering and pagination.
        
        Args:
            page: Page number for pagination (default: 1)
            page_size: Number of results per page (default: 10, max: 50)
            status: Filter by status (open, in_progress, resolved, closed) (optional)
            category: Filter by category (optional)
            priority: Filter by priority (optional)
        
        Returns:
            JSON string containing paginated ticket list
        """
        start_time = datetime.now()
        arguments = {
            "query": "", "status": status, "category": category,
            "priority": priority, "page": page, "page_size": page_size
        }
        
        logger.info("[MCP_TOOL] list_tickets called in MCP server container")
        
        try:
            # Extract user context from middleware (set by TokenAuthMiddleware)
            user_context = getattr(context, 'user_context', None) if context else None
            user_token = getattr(context, 'user_token', None) if context else None
            
            if not user_context:
                return "Authentication required: MCP tools need user context. Please call through authenticated AI chat session."
            
            logger.info(f"[MCP_TOOL] Authenticated list_tickets for user {user_context.user_id}")
            
            # Validate page_size parameter
            if not isinstance(page_size, int) or page_size < 1 or page_size > 50:
                page_size = min(50, max(1, page_size))
            
            # Build query parameters
            params = {"page": page, "page_size": page_size}
            if status: params["status"] = status
            if category: params["category"] = category
            if priority: params["priority"] = priority
            
            # Use http_client for authenticated backend calls
            http_client = await get_http_client()
            
            # Build authentication headers from user token
            auth_headers = {"Authorization": f"Bearer {user_token}"} if user_token else {}
            
            if not user_token:
                logger.warning("[MCP_TOOL] No user token available for backend authentication")
                return "Authentication error: Missing user token for backend API calls"
            
            response = await http_client.make_request(
                method="GET",
                endpoint="/api/v1/tickets",
                auth_headers=auth_headers,
                params=params
            )
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            if response.status_code == 200:
                log_tool_call("list_tickets", arguments, response.text, execution_time, "success")
                return response.text
            elif response.status_code == 401:
                # Handle authentication required gracefully
                helpful_msg = "Authentication required: MCP tools need user context. Please call through authenticated AI chat session."
                log_tool_call("list_tickets", arguments, helpful_msg, execution_time, "auth_required")
                return helpful_msg
            else:
                error_msg = f"Error: HTTP {response.status_code} - {response.text}"
                log_tool_call("list_tickets", arguments, error_msg, execution_time, "error")
                return error_msg
                
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            log_tool_call("list_tickets", arguments, error_msg, execution_time, "error")
            return error_msg

def register_get_ticket_stats():
    @mcp.tool()
    async def get_ticket_stats(context: Optional[Any] = None) -> str:
        """
        Retrieve ticket statistics and overview information.
        
        Returns:
            JSON string containing comprehensive ticket statistics
        """
        start_time = datetime.now()
        arguments = {}
        
        try:
            # Extract user context from middleware (set by TokenAuthMiddleware)
            user_context = getattr(context, 'user_context', None) if context else None
            user_token = getattr(context, 'user_token', None) if context else None
            
            if not user_context:
                return "Authentication required: MCP tools need user context. Please call through authenticated AI chat session."
            
            logger.info(f"[MCP_TOOL] Authenticated get_ticket_stats for user {user_context.user_id}")
            
            # Use http_client for authenticated backend calls
            http_client = await get_http_client()
            
            # Build authentication headers from user token
            auth_headers = {"Authorization": f"Bearer {user_token}"} if user_token else {}
            
            if not user_token:
                logger.warning("[MCP_TOOL] No user token available for backend authentication")
                return "Authentication error: Missing user token for backend API calls"
            
            response = await http_client.make_request(
                method="GET",
                endpoint="/api/v1/tickets/stats/overview",
                auth_headers=auth_headers
            )
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            if response.status_code == 200:
                log_tool_call("get_ticket_stats", arguments, response.text, execution_time, "success")
                return response.text
            elif response.status_code == 401:
                # Handle authentication required gracefully
                helpful_msg = "Authentication required: MCP tools need user context. Please call through authenticated AI chat session."
                log_tool_call("get_ticket_stats", arguments, helpful_msg, execution_time, "auth_required")
                return helpful_msg
            else:
                error_msg = f"Error: HTTP {response.status_code} - {response.text}"
                log_tool_call("get_ticket_stats", arguments, error_msg, execution_time, "error")
                return error_msg
                
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            log_tool_call("get_ticket_stats", arguments, error_msg, execution_time, "error")
            return error_msg

# =============================================================================
# TOOL REGISTRATION
# =============================================================================

def register_all_ticket_tools(mcp_instance: FastMCP):
    """Register all ticket management tools"""
    global mcp
    mcp = mcp_instance
    
    # Register tools using original registration pattern
    register_create_ticket()
    register_create_ticket_with_ai()
    register_get_ticket()
    register_update_ticket()
    register_delete_ticket()
    register_update_ticket_status()
    register_assign_ticket()
    register_search_tickets()
    register_list_tickets()
    register_get_ticket_stats()
    
    logger.info("Ticket tools registered")