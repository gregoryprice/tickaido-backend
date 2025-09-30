#!/usr/bin/env python3
"""
FastMCP Server with Token Authentication

Official FastMCP 2.0 server implementation with token-based authentication.
This replaces the custom MCP server with proper authentication and API-based tools.

ARCHITECTURE:
- Uses official FastMCP server with StaticTokenVerifier
- Token-based authentication for development and production
- API-based tools that call backend endpoints instead of direct DB access
- Comprehensive logging with FastMCP context logging

AUTHENTICATION FLOW:
1. Client sends JWT token in Authorization header
2. StaticTokenVerifier validates token and extracts claims
3. Tools receive authenticated context with user/org information
4. Tools make authenticated API calls to backend services
"""

import os
import sys
import json
import logging
import httpx
from dotenv import load_dotenv
from typing import Dict, Any, Optional
from fastmcp import FastMCP, Context
from fastmcp.server.middleware.logging import LoggingMiddleware
from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware
from fastmcp.server.auth.auth import TokenVerifier, AccessToken
from fastmcp.server.dependencies import get_http_request, get_http_headers
from starlette.requests import Request
from fastmcp.server.dependencies import get_access_token, AccessToken
from fastmcp.server.dependencies import get_context
#from fastmcp.server.auth.providers.jwt import JWTVerifiern

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)


class SimpleTokenVerifier(TokenVerifier):
    async def verify_token(self, token: str) -> AccessToken | None:
        return AccessToken(
            token=token,
            client_id="greg.price1@gmail.com",
            scopes=["*"],
            expires_at=None,
            resource="http://localhost:8000/mcp/tools",
        )

# Configure token-based authentication with simple static tokens
# These are development tokens for testing FastMCP implementation
# DEVELOPMENT_TOKENS = {
#     # Simple development token for Alice
#     "dev-alice-token": {
#         "client_id": "alice@dev.com",
#         "scopes": ["read:tickets", "write:tickets", "admin:all"],
#         "user_id": "alice",
#         "organization_id": "dev-org",
#         "email": "alice@dev.com",
#         "api_key": "ai_dev_MwUVUygQboY9yIeXQ539PYTJfv9Y7yeexWL4TrELMB8"
#     },
#     # Simple development token for AI testing
#     "ai-dev-token-123": {
#         "client_id": "greg.price1@gmail.com", 
#         "scopes": ["*"],
#         "user_id": "9cdd4c6c-a65d-464b-b3ba-64e6781fba2b",
#         "organization_id": "20a8aae5-ec85-42a9-b025-45ee32a2f9a1",
#         "email": "greg.price1@gmail.com"
#     }
# }

# verifier = JWTVerifier(
#     jwks_uri="https://auth.yourcompany.com/.well-known/jwks.json",
#     issuer="https://auth.tickaido.com",
#     audience="mcp-production-api"
# )

mcp = FastMCP("TickAido MCP Server", auth=SimpleTokenVerifier())
mcp.add_middleware(LoggingMiddleware())
mcp.add_middleware(ErrorHandlingMiddleware(include_traceback=True))

# API base URL for backend calls
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

logger.info("✅ FastMCP server initialized with token authentication")
# logger.info(f"✅ Configured {len(DEVELOPMENT_TOKENS)} development tokens")
logger.info(f"✅ API base URL: {API_BASE_URL}")

# Add health check endpoint for Docker health checks
from starlette.requests import Request
from starlette.responses import JSONResponse

@mcp.custom_route("/health", ["GET"])
async def health_check(request: Request):
    """Health check endpoint for Docker containers."""
    return JSONResponse({
        "status": "healthy",
        "server": "TickAido MCP Server",
        "version": "2.0",
        "transport": "HTTP"      
    })


@mcp.tool
async def list_tickets(
    ctx: Context,
    page: int = 1,
    page_size: int = 10,
    status: str = "",
    category: str = "",
    priority: str = "",
    urgency: str = "",
    department: str = "",
    created_by: str = "",
    assigned_to: str = "",
    search: str = "",
    sort_by: str = "created_at",
    sort_order: str = "desc"
) -> str:
    """
    List and retrieve tickets with advanced filtering and pagination.
    
    Retrieves tickets from the authenticated user's organization with support for:
    - Pagination (page, page_size)
    - Status filtering (open, in_progress, resolved, closed, cancelled)  
    - Category filtering (technical, billing, feature_request, bug, user_access, general, integration, performance, security)
    - Priority filtering (low, medium, high, critical)
    - Urgency filtering (low, medium, high, critical)
    - Department filtering
    - User filtering (created_by, assigned_to)
    - Text search across title and description
    - Sorting (created_at, updated_at, priority, status)
    
    Use this tool when the user wants to see their tickets or search for specific tickets.
    """
    # Get the HTTP request and headers using FastMCP dependencies
    request = get_http_request()
    headers = get_http_headers()
    
    # Get context and access token (same pattern as add tool)
    ctx: Context | None = get_context()
    token: AccessToken | None = get_access_token()
    
    logger.info(f"🔍 [TRACE] request: {request}")
    logger.info(f"🔍 [TRACE] headers: {headers}")
    logger.info(f"🔍 [TRACE] token: {token}")
    logger.info(f"🔍 [TRACE] list_tickets params: page={page}, page_size={page_size}, status={status}")
    
    # Check for authentication token
    if not token or not token.token:
        error_msg = "Authentication required: No valid token provided"
        logger.error(error_msg)
        return json.dumps({
            "error": "Authentication required",
            "message": "No valid token provided"
        })
    
    try:
        # Build API request parameters
        params = {
            "page": page,
            "page_size": min(page_size, 50)  # Limit page size to 50 max
        }
        
        # Add optional filters
        if status:
            params["status"] = status
        if category:
            params["category"] = category  
        if priority:
            params["priority"] = priority
        if urgency:
            params["urgency"] = urgency
        if department:
            params["department"] = department
        if created_by:
            params["created_by"] = created_by
        if assigned_to:
            params["assigned_to"] = assigned_to
        if search:
            params["search"] = search
        if sort_by:
            params["sort_by"] = sort_by
        if sort_order:
            params["sort_order"] = sort_order
        
        # Make API call to backend
        api_headers = {
            "Authorization": f"Bearer {token.token}"
        }
        
        logging.debug(f"Making API call with params: {params}")
        
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(
                f"{API_BASE_URL}/api/v1/tickets/",
                headers=api_headers,
                params=params
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully retrieved tickets ")
                logger.info(f"✅ Retrieved tickets: {response.status_code}")
                logger.info(f"✅ Retrieved tickets: {response.json()}")
                logger.info(f"✅ Retrieved tickets: {response.text}")
                return response.text
            else:
                error_msg = f"API call failed: HTTP {response.status_code} - {response.text}"
                logger.error(error_msg)
                return json.dumps({
                    "error": "Failed to retrieve tickets",
                    "status_code": response.status_code,
                    "message": response.text
                })
                
    except Exception as e:
        error_msg = f"Tool execution failed: {str(e)}"
        logger.error(error_msg)
        logger.error(f"❌ list_tickets failed: {e}")
        return json.dumps({
            "error": "Tool execution failed",
            "message": str(e)
        })


@mcp.tool
async def create_ticket(
    ctx: Context,
    title: str,
    description: str,
    category: str = "general",
    priority: str = "",
    urgency: str = "medium",
    department: str = "",
    assigned_to_id: str = "",
    integration_id: str = "",
    create_externally: bool = False,
    custom_fields: str = "",
    file_ids: str = ""
) -> str:
    """
    Create a new bug or feature request ticket.
    
    Calls POST /api/v1/tickets with fields matching TicketCreateRequest, including
    attachments in the initial request payload.
    
    Parameters:
    - title: Ticket title/subject (required)
    - description: Detailed description (required)
    - category: one of [technical, billing, feature_request, bug, user_access, general, integration, performance, security]
    - priority: one of [low, medium, high, critical] (optional)
    - urgency: one of [low, medium, high, critical] (default: medium)
    - department: Target department (optional)
    - assigned_to_id: User ID to assign (UUID string, optional)
    - integration_id: Integration ID for external creation (UUID string, optional)
    - create_externally: If true and integration_id set, create externally too
    - custom_fields: JSON string of custom fields (optional)
    - file_ids: Comma-separated UUIDs to attach to the ticket during creation (optional)
    """
    # Get the HTTP request, headers, and authentication
    request = get_http_request()
    headers = get_http_headers()
    ctx: Context | None = get_context()
    token: AccessToken | None = get_access_token()
    
    logger.info(f"🔍 [TRACE] create_ticket: title='{(title or '')[:50]}' category={category} priority={priority} urgency={urgency}")

    if file_ids:
        logger.info(f"🔍 [TRACE] create_ticket: file_ids='{file_ids}'")
    
    # Check for authentication token
    if not token or not token.token:
        error_msg = "Authentication required: No valid token provided"
        logger.error(error_msg)
        return json.dumps({
            "error": "Authentication required",
            "message": "No valid token provided"
        })
    
    try:
        # Validate required
        if not title or not title.strip():
            return json.dumps({"error": "Title is required"})
        if not description or not description.strip():
            return json.dumps({"error": "Description is required"})
        
        # Build create payload
        payload: Dict[str, Any] = {
            "title": title.strip(),
            "description": description.strip(),
            "category": (category or "general").strip() or "general",
            "urgency": (urgency or "medium").strip() or "medium",
            "create_externally": bool(create_externally)
        }
        
        if priority and priority.strip():
            payload["priority"] = priority.strip()
        if department and department.strip():
            payload["department"] = department.strip()
        if assigned_to_id and assigned_to_id.strip():
            payload["assigned_to_id"] = assigned_to_id.strip()
        if integration_id and integration_id.strip():
            payload["integration_id"] = integration_id.strip()
        
        # Parse custom_fields JSON if provided
        if custom_fields and custom_fields.strip():
            try:
                parsed = json.loads(custom_fields)
                if isinstance(parsed, dict):
                    payload["custom_fields"] = parsed
            except Exception as e:
                logger.warning(f"Invalid custom_fields JSON ignored: {e}")
        
        # Handle file attachments - include in initial request
        if file_ids and file_ids.strip():
            file_ids_list = [fid.strip() for fid in file_ids.split(",") if fid.strip()]
            logger.info(f"🔍 [TRACE] Processing file_ids: {file_ids} -> parsed as: {file_ids_list}")
            # Convert to FileAttachment format expected by API
            attachments = [{"file_id": fid} for fid in file_ids_list]
            payload["attachments"] = attachments
            logger.info(f"🔍 [TRACE] Added attachments to payload: {attachments}")
        else:
            logger.info(f"🔍 [TRACE] No file_ids provided (file_ids='{file_ids}')")
        
        # Prepare headers
        api_headers = {
            "Authorization": f"Bearer {token.token}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            # Log the actual request payload being sent
            logger.info(f"🔍 [TRACE] create_ticket request payload: {json.dumps(payload, indent=2)}")
            logger.info(f"🔍 [TRACE] create_ticket request URL: {API_BASE_URL}/api/v1/tickets/")
            
            # Create the ticket
            create_resp = await client.post(
                f"{API_BASE_URL}/api/v1/tickets/",
                headers=api_headers,
                json=payload
            )
            
            if create_resp.status_code not in [200, 201]:
                error_msg = f"API call failed: HTTP {create_resp.status_code} - {create_resp.text}"
                logger.error(error_msg)
                return json.dumps({
                    "error": "Failed to create ticket",
                    "status_code": create_resp.status_code,
                    "message": create_resp.text
                })
            
            # Return the create response JSON (with attachments included if provided)
            return create_resp.text
        
    except Exception as e:
        error_msg = f"Create ticket failed: {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "error": "Tool execution failed",
            "message": str(e)
        })


@mcp.tool
async def search_tickets(
    ctx: Context,
    search: str,
    status: str = "",
    category: str = "",
    priority: str = "",
    urgency: str = "",
    department: str = "",
    created_by: str = "",
    assigned_to: str = "",
    sort_by: str = "created_at",
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 10
) -> str:
    """
    Search tickets by text query with advanced filtering and pagination.
    
    Performs full-text search across ticket titles and descriptions with support for:
    - Text search across title and description fields
    - Status filtering (open, in_progress, resolved, closed, cancelled)
    - Category filtering (technical, billing, feature_request, bug, user_access, general, integration, performance, security)
    - Priority filtering (low, medium, high, critical)
    - Urgency filtering (low, medium, high, critical)
    - Department filtering
    - User filtering (created_by, assigned_to)
    - Sorting (created_at, updated_at, priority, status)
    - Pagination (page, page_size)
    
    Use this tool when the user wants to find tickets matching specific terms or keywords.
    """
    # Get the HTTP request, headers, and authentication
    request = get_http_request()
    headers = get_http_headers()
    ctx: Context | None = get_context()
    token: AccessToken | None = get_access_token()
    
    logger.info(f"🔍 [TRACE] search_tickets: search='{search[:30]}...', page={page}")
    
    # Check for authentication token
    if not token or not token.token:
        error_msg = "Authentication required: No valid token provided"
        logger.error(error_msg)
        return json.dumps({
            "error": "Authentication required",
            "message": "No valid token provided"
        })
    
    try:
        # Build search parameters
        params = {
            "search": search,
            "page": page,
            "page_size": min(page_size, 50)
        }
        
        # Add optional filters
        if status:
            params["status"] = status
        if category:
            params["category"] = category
        if priority:
            params["priority"] = priority
        if urgency:
            params["urgency"] = urgency
        if department:
            params["department"] = department
        if created_by:
            params["created_by"] = created_by
        if assigned_to:
            params["assigned_to"] = assigned_to
        if sort_by:
            params["sort_by"] = sort_by
        if sort_order:
            params["sort_order"] = sort_order
        
        # Make authenticated API call
        api_headers = {
            "Authorization": f"Bearer {token.token}"
        }
        
        logger.info(f"Making search API call with params: {params}")
        
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(
                f"{API_BASE_URL}/api/v1/tickets/search/",
                headers=api_headers,
                params=params
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Search completed: {response.status_code}")
                return response.text
            else:
                error_msg = f"Search API call failed: HTTP {response.status_code} - {response.text}"
                logger.error(error_msg)
                return json.dumps({
                    "error": "Failed to search tickets",
                    "status_code": response.status_code,
                    "message": response.text
                })
                
    except Exception as e:
        error_msg = f"Search failed: {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "error": "Search execution failed",
            "message": str(e)
        })


@mcp.tool
async def get_ticket(
    ctx: Context,
    ticket_id: str
) -> str:
    """
    Get a specific ticket by ID.
    
    Retrieves detailed information for a single ticket including:
    - Basic ticket information (title, description, status, priority, etc.)
    - User assignment and ownership details
    - Timestamps (created, updated, resolved dates)
    - SLA information and escalation details
    - Custom fields and metadata
    
    Use this tool when the user wants to view details of a specific ticket.
    """
    # Get the HTTP request, headers, and authentication
    request = get_http_request()
    headers = get_http_headers()
    ctx: Context | None = get_context()
    token: AccessToken | None = get_access_token()
    
    logger.info(f"🔍 [TRACE] get_ticket: ticket_id={ticket_id}")
    
    # Check for authentication token
    if not token or not token.token:
        error_msg = "Authentication required: No valid token provided"
        logger.error(error_msg)
        return json.dumps({
            "error": "Authentication required",
            "message": "No valid token provided"
        })
    
    try:
        # Make authenticated API call
        api_headers = {
            "Authorization": f"Bearer {token.token}"
        }
        
        logger.info(f"Getting ticket {ticket_id}")
        
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(
                f"{API_BASE_URL}/api/v1/tickets/{ticket_id}/",
                headers=api_headers
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Retrieved ticket {ticket_id}")
                return response.text
            elif response.status_code == 404:
                logger.info(f"Ticket {ticket_id} not found")
                return json.dumps({
                    "error": "Ticket not found",
                    "ticket_id": ticket_id
                })
            else:
                error_msg = f"API call failed: HTTP {response.status_code} - {response.text}"
                logger.error(error_msg)
                return json.dumps({
                    "error": "Failed to retrieve ticket",
                    "status_code": response.status_code,
                    "ticket_id": ticket_id,
                    "message": response.text
                })
                
    except Exception as e:
        error_msg = f"Get ticket failed: {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "error": "Get ticket execution failed",
            "message": str(e),
            "ticket_id": ticket_id
        })


@mcp.tool
async def get_system_health(ctx: Context) -> str:
    """Get system health status with API call."""
    logger.info("Checking system health")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{API_BASE_URL}/health")
            
            if response.status_code == 200:
                logger.info("System health check successful")
                return json.dumps({
                    "status": "healthy",
                    "api_status": response.text,
                    "mcp_server": "operational"
                })
            else:
                logger.warning(f"API health check returned {response.status_code}")
                return json.dumps({
                    "status": "degraded", 
                    "api_status_code": response.status_code,
                    "mcp_server": "operational"
                })
                
    except Exception as e:
        error_msg = f"Health check failed: {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "status": "error",
            "message": str(e),
            "mcp_server": "operational"
        })


@mcp.tool
async def update_ticket(
    ctx: Context,
    ticket_id: str,
    title: str = "",
    description: str = "",
    status: str = "",
    priority: str = "",
    category: str = "",
    urgency: str = "",
    department: str = "",
    assigned_to_id: str = "",
    internal_notes: str = "",
    resolution_summary: str = "",
    custom_fields: str = "",
    file_ids: str = "",
    use_patch: bool = True
) -> str:
    """
    Update an existing ticket.
    
    Uses PATCH /api/v1/tickets/{ticket_id} by default (partial updates) or 
    PUT /api/v1/tickets/{ticket_id} if use_patch=False (full replacement).
    
    Parameters:
    - ticket_id: UUID of the ticket to update (required)
    - title: Update ticket title (optional)
    - description: Update ticket description (optional)
    - status: Update status - one of [new, open, in_progress, pending, resolved, closed, cancelled] (optional)
    - priority: Update priority - one of [low, medium, high, critical] (optional)
    - category: Update category - one of [technical, billing, feature_request, bug, user_access, general, integration, performance, security] (optional)
    - urgency: Update urgency - one of [low, medium, high, critical] (optional)
    - department: Update department (optional)
    - assigned_to_id: User ID to assign (UUID string, optional, empty string to unassign)
    - internal_notes: Add internal notes (optional)
    - resolution_summary: Resolution summary (optional)
    - custom_fields: JSON string of custom fields to update (optional)
    - file_ids: Comma-separated UUIDs to update ticket attachments (optional)
    - use_patch: If true (default), use PATCH for partial updates; if false, use PUT for full replacement
    """
    # Get authentication
    token: AccessToken | None = get_access_token()
    
    logger.info(f"🔍 [TRACE] update_ticket: ticket_id={ticket_id} use_patch={use_patch}")
    
    # Check for authentication token
    if not token or not token.token:
        error_msg = "Authentication required: No valid token provided"
        logger.error(error_msg)
        return json.dumps({
            "error": "Authentication required",
            "message": "No valid token provided"
        })
    
    try:
        # Validate ticket_id
        if not ticket_id or not ticket_id.strip():
            return json.dumps({"error": "ticket_id is required"})
        
        ticket_id = ticket_id.strip()
        
        # Build update payload - only include fields that are provided
        payload: Dict[str, Any] = {}
        
        if title and title.strip():
            payload["title"] = title.strip()
        if description and description.strip():
            payload["description"] = description.strip()
        if status and status.strip():
            payload["status"] = status.strip()
        if priority and priority.strip():
            payload["priority"] = priority.strip()
        if category and category.strip():
            payload["category"] = category.strip()
        if urgency and urgency.strip():
            payload["urgency"] = urgency.strip()
        if department and department.strip():
            payload["department"] = department.strip()
        if assigned_to_id is not None:  # Allow empty string to unassign
            if assigned_to_id.strip():
                payload["assigned_to_id"] = assigned_to_id.strip()
            else:
                payload["assigned_to_id"] = None  # Unassign
        if internal_notes and internal_notes.strip():
            payload["internal_notes"] = internal_notes.strip()
        if resolution_summary and resolution_summary.strip():
            payload["resolution_summary"] = resolution_summary.strip()
        
        # Parse custom_fields JSON if provided
        if custom_fields and custom_fields.strip():
            try:
                parsed = json.loads(custom_fields)
                if isinstance(parsed, dict):
                    payload["custom_fields"] = parsed
            except Exception as e:
                logger.warning(f"Invalid custom_fields JSON ignored: {e}")
        
        # Handle file attachments
        if file_ids is not None:  # Allow empty string to clear attachments
            file_ids_list = []
            if file_ids.strip():
                file_ids_list = [fid.strip() for fid in file_ids.split(",") if fid.strip()]
            
            # Convert to FileAttachment format
            attachments = [{"file_id": fid} for fid in file_ids_list]
            payload["attachments"] = attachments
        
        # Check if we have any updates
        if not payload:
            return json.dumps({"error": "At least one field must be provided for update"})
        
        # Prepare headers
        api_headers = {
            "Authorization": f"Bearer {token.token}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            # Choose endpoint based on use_patch
            method = "PATCH" if use_patch else "PUT"
            
            if use_patch:
                # Use PATCH for partial updates
                response = await client.patch(
                    f"{API_BASE_URL}/api/v1/tickets/{ticket_id}",
                    headers=api_headers,
                    json=payload
                )
            else:
                # Use PUT for full replacement
                response = await client.put(
                    f"{API_BASE_URL}/api/v1/tickets/{ticket_id}",
                    headers=api_headers,
                    json=payload
                )
            
            if response.status_code not in [200, 201]:
                error_msg = f"API call failed: HTTP {response.status_code} - {response.text}"
                logger.error(error_msg)
                return json.dumps({
                    "error": f"Failed to update ticket with {method}",
                    "status_code": response.status_code,
                    "message": response.text
                })
            
            # Return the updated ticket
            return response.text
        
    except Exception as e:
        error_msg = f"Update ticket failed: {str(e)}"
        logger.error(error_msg)
        return json.dumps({
            "error": "Tool execution failed",
            "message": str(e)
        })


# Log successful tool registration
# Available tools: list_tickets, create_ticket, search_tickets, get_ticket, update_ticket, get_system_health
logger.info(f"✅ Registered 6 FastMCP tools")
logger.info("✅ All tools use API-based calls (no direct database access)")
logger.info("✅ Authentication context available to all tools")

if __name__ == "__main__":
    # Load environment variables
    load_dotenv(".env")
    
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8001"))
    log_level = os.getenv("MCP_LOG_LEVEL", "INFO")
    
    logger.info(f"🚀 Starting FastMCP server on {host}:{port}")
    logger.info(f"📊 Logging Level: {log_level}")
    
    # Configure FastMCP logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the FastMCP server with HTTP transport
    import asyncio
    asyncio.run(mcp.run_http_async(
        host=host,
        port=port,
        log_level=log_level,
        transport="http"
    ))