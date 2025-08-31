#!/usr/bin/env python3
"""
MCP Server for AI Ticket Creator Tools

This server provides Model Context Protocol (MCP) tools for customer support operations
including ticket creation, file analysis, third-party integrations, and knowledge base search.

The server uses FastMCP to provide tools that can be used by AI agents
for customer support operations.

For more information on FastMCP, see: https://fastmcp.tadata.com/
"""

import os
import logging
import json
from datetime import datetime
from typing import Dict, Any
import httpx
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import Response

# Import centralized logging configuration
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

# Initialize FastMCP
mcp = FastMCP("AI Ticket Creator Tools")

# Backend URL
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

def log_tool_call(tool_name: str, arguments: Dict[str, Any], response: str, execution_time_ms: float, status: str = "success"):
    """
    Log tool call details including request and response.
    
    Args:
        tool_name: Name of the tool being called
        arguments: Arguments passed to the tool
        response: Response from the tool
        execution_time_ms: Execution time in milliseconds
        status: Status of the call (success/error)
    """
    call_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    
    # Log the tool call request
    request_log = {
        "call_id": call_id,
        "tool_name": tool_name,
        "arguments": arguments,
        "timestamp": datetime.now().isoformat(),
        "status": status
    }
    
    tool_logger.info(f"🔧 MCP TOOL REQUEST #{call_id}: {tool_name}")
    tool_logger.info(f"📤 Request Body: {json.dumps(request_log, indent=2)}")
    
    # Log the response
    response_log = {
        "call_id": call_id,
        "tool_name": tool_name,
        "status": status,
        "execution_time_ms": round(execution_time_ms, 2),
        "timestamp": datetime.now().isoformat()
    }
    
    # Truncate response if it's too long for logging
    response_str = str(response)
    if len(response_str) > 1000:
        response_str = response_str[:1000] + "... [truncated]"
    
    response_log["response_preview"] = response_str
    
    if status == "success":
        tool_logger.info(f"✅ MCP TOOL RESPONSE #{call_id}: {tool_name} ({execution_time_ms:.2f}ms)")
    else:
        tool_logger.error(f"❌ MCP TOOL ERROR #{call_id}: {tool_name} ({execution_time_ms:.2f}ms)")
    
    tool_logger.info(f"📥 Response Body: {json.dumps(response_log, indent=2)}")

# =============================================================================
# TICKET MANAGEMENT TOOLS
# =============================================================================

@mcp.tool()
async def create_ticket(
    title: str,
    description: str,
    category: str = "general",
    priority: str = "medium",
    attachments: str = "",
    integration: str = ""
) -> str:
    """
    Create a support ticket with specified details and optional routing to integrations.
    
    Args:
        title: Ticket title/subject (required)
        description: Detailed description of the issue (required)
        category: Issue category (technical, billing, feature_request, bug, user_access, general)
        priority: Priority level (low, medium, high, critical)
        attachments: Comma-separated list of attachment IDs or file paths
        integration: Target integration for routing (jira, salesforce, zendesk, github)
    
    Returns:
        JSON string containing ticket creation results with ticket ID and integration details
    """
    start_time = datetime.now()
    arguments = {
        "title": title, "description": description, "category": category,
        "priority": priority, "attachments": attachments, "integration": integration
    }
    
    try:
        # Build the request data
        ticket_data = {
            "title": title,
            "description": description,
            "category": category,
            "priority": priority,
            "status": "open",
            "ai_generated": True
        }
        
        # Add attachments if provided
        if attachments:
            attachment_list = [att.strip() for att in attachments.split(",") if att.strip()]
            ticket_data["attachments"] = attachment_list
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BACKEND_URL}/api/v1/tickets",
                json=ticket_data,
                timeout=30.0
            )
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            if response.status_code in [200, 201]:
                result_data = response.json()
                
                # If integration specified, route to integration
                if integration and integration.lower() != "none":
                    integration_result = await route_to_integration(integration, result_data.get("id"))
                    result_data["integration_result"] = integration_result
                
                log_tool_call("create_ticket", arguments, json.dumps(result_data), execution_time, "success")
                return json.dumps(result_data, indent=2)
            else:
                error_msg = f"Error: HTTP {response.status_code} - {response.text}"
                log_tool_call("create_ticket", arguments, error_msg, execution_time, "error")
                return error_msg
                
    except httpx.ConnectError as e:
        error_msg = f"Error: Cannot connect to backend server. Please ensure the server is running on {BACKEND_URL}"
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        log_tool_call("create_ticket", arguments, error_msg, execution_time, "error")
        return error_msg
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        log_tool_call("create_ticket", arguments, error_msg, execution_time, "error")
        return error_msg

@mcp.tool()
async def update_ticket(
    ticket_id: str,
    title: str = "",
    description: str = "",
    status: str = "",
    priority: str = "",
    category: str = ""
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
        
        async with httpx.AsyncClient() as client:
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
        error_msg = f"Error: {str(e)}"
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        log_tool_call("update_ticket", arguments, error_msg, execution_time, "error")
        return error_msg

@mcp.tool()
async def search_tickets(
    query: str = "",
    status: str = "",
    category: str = "",
    priority: str = "",
    page: int = 1,
    page_size: int = 10
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
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BACKEND_URL}/api/v1/tickets",
                params=params,
                timeout=30.0
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

# =============================================================================
# FILE ANALYSIS TOOLS
# =============================================================================

@mcp.tool()
async def analyze_file(
    file_path: str,
    file_type: str,
    analysis_type: str = "auto"
) -> str:
    """
    Analyze uploaded file and extract relevant information.
    Supports transcription, OCR, and metadata extraction.
    
    Args:
        file_path: Path to the uploaded file (required)
        file_type: MIME type of the file (required)
        analysis_type: Type of analysis (auto, transcription, ocr, metadata)
    
    Returns:
        JSON string containing analysis results with extracted text and confidence scores
    """
    start_time = datetime.now()
    arguments = {"file_path": file_path, "file_type": file_type, "analysis_type": analysis_type}
    
    try:
        # Route to appropriate analysis based on file type
        if file_type.startswith("audio/") or file_type.startswith("video/"):
            analysis_result = await transcribe_audio(file_path, file_type)
        elif file_type.startswith("image/"):
            analysis_result = await extract_text_from_image(file_path, file_type)
        else:
            # Handle document files with metadata extraction
            analysis_result = await extract_file_metadata(file_path, file_type)
        
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        log_tool_call("analyze_file", arguments, analysis_result, execution_time, "success")
        return analysis_result
        
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        log_tool_call("analyze_file", arguments, error_msg, execution_time, "error")
        return error_msg

@mcp.tool()
async def transcribe_audio(file_path: str, file_type: str) -> str:
    """
    Transcribe audio or video file to text.
    
    Args:
        file_path: Path to the audio/video file
        file_type: MIME type of the file
    
    Returns:
        JSON string containing transcription results
    """
    start_time = datetime.now()
    arguments = {"file_path": file_path, "file_type": file_type}
    
    try:
        async with httpx.AsyncClient() as client:
            # Call backend transcription service
            response = await client.post(
                f"{BACKEND_URL}/api/v1/files/transcribe",
                json={"file_path": file_path, "file_type": file_type},
                timeout=120.0  # Longer timeout for transcription
            )
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            if response.status_code == 200:
                result = response.json()
                result.update({
                    "analysis_type": "transcription",
                    "file_path": file_path,
                    "file_type": file_type
                })
                
                result_json = json.dumps(result, indent=2)
                log_tool_call("transcribe_audio", arguments, result_json, execution_time, "success")
                return result_json
            else:
                error_msg = f"Error: HTTP {response.status_code} - {response.text}"
                log_tool_call("transcribe_audio", arguments, error_msg, execution_time, "error")
                return error_msg
                
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        log_tool_call("transcribe_audio", arguments, error_msg, execution_time, "error")
        return error_msg

@mcp.tool()
async def extract_text_from_image(file_path: str, file_type: str) -> str:
    """
    Extract text from image file using OCR.
    
    Args:
        file_path: Path to the image file
        file_type: MIME type of the file
    
    Returns:
        JSON string containing OCR results
    """
    start_time = datetime.now()
    arguments = {"file_path": file_path, "file_type": file_type}
    
    try:
        async with httpx.AsyncClient() as client:
            # Call backend OCR service
            response = await client.post(
                f"{BACKEND_URL}/api/v1/files/ocr",
                json={"file_path": file_path, "file_type": file_type},
                timeout=60.0  # Timeout for OCR
            )
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            if response.status_code == 200:
                result = response.json()
                result.update({
                    "analysis_type": "ocr",
                    "file_path": file_path,
                    "file_type": file_type
                })
                
                result_json = json.dumps(result, indent=2)
                log_tool_call("extract_text_from_image", arguments, result_json, execution_time, "success")
                return result_json
            else:
                error_msg = f"Error: HTTP {response.status_code} - {response.text}"
                log_tool_call("extract_text_from_image", arguments, error_msg, execution_time, "error")
                return error_msg
                
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        log_tool_call("extract_text_from_image", arguments, error_msg, execution_time, "error")
        return error_msg

async def extract_file_metadata(file_path: str, file_type: str) -> str:
    """Extract basic metadata from file"""
    try:
        result = {
            "analysis_type": "metadata",
            "file_path": file_path,
            "file_type": file_type,
            "extracted_text": "",
            "metadata": {
                "file_size": "unknown",
                "last_modified": "unknown"
            },
            "confidence": 1.0
        }
        
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

# =============================================================================
# INTEGRATION TOOLS
# =============================================================================

async def route_to_integration(integration: str, ticket_id: str) -> Dict[str, Any]:
    """Route ticket to specified integration"""
    try:
        if integration.lower() == "jira":
            return await create_jira_ticket(ticket_id)
        elif integration.lower() == "salesforce":
            return await create_salesforce_case(ticket_id)
        elif integration.lower() == "github":
            return await create_github_issue(ticket_id)
        else:
            return {"error": f"Unknown integration: {integration}"}
    except Exception as e:
        return {"error": str(e)}

async def create_jira_ticket(ticket_id: str) -> Dict[str, Any]:
    """Create ticket in Jira (placeholder implementation)"""
    return {
        "integration": "jira",
        "status": "created",
        "external_id": f"SUPPORT-{ticket_id}",
        "url": f"https://example.atlassian.net/browse/SUPPORT-{ticket_id}"
    }

async def create_salesforce_case(ticket_id: str) -> Dict[str, Any]:
    """Create case in Salesforce (placeholder implementation)"""
    return {
        "integration": "salesforce",
        "status": "created",
        "external_id": f"5003000000{ticket_id}",
        "url": f"https://example.salesforce.com/5003000000{ticket_id}"
    }

async def create_github_issue(ticket_id: str) -> Dict[str, Any]:
    """Create issue in GitHub (placeholder implementation)"""
    return {
        "integration": "github",
        "status": "created",
        "external_id": f"#{ticket_id}",
        "url": f"https://github.com/example/repo/issues/{ticket_id}"
    }

# =============================================================================
# KNOWLEDGE BASE TOOLS
# =============================================================================

@mcp.tool()
async def search_knowledge_base(
    query: str,
    max_results: int = 5,
    category: str = ""
) -> str:
    """
    Search knowledge base for existing solutions and documentation.
    
    Args:
        query: Search query for knowledge base
        max_results: Maximum number of results to return (default: 5)
        category: Filter by category (optional)
    
    Returns:
        JSON string containing knowledge base search results
    """
    start_time = datetime.now()
    arguments = {"query": query, "max_results": max_results, "category": category}
    
    try:
        # Placeholder implementation - would integrate with actual knowledge base
        results = {
            "query": query,
            "results": [
                {
                    "id": "kb-001",
                    "title": "Common Login Issues and Solutions",
                    "summary": "Troubleshooting guide for user authentication problems",
                    "category": "user_access",
                    "relevance_score": 0.95,
                    "url": "/kb/login-issues"
                },
                {
                    "id": "kb-002", 
                    "title": "File Upload Best Practices",
                    "summary": "Guidelines for uploading files through the Chrome extension",
                    "category": "technical",
                    "relevance_score": 0.87,
                    "url": "/kb/file-upload"
                }
            ],
            "total_results": 2,
            "search_time_ms": 45
        }
        
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        result_json = json.dumps(results, indent=2)
        log_tool_call("search_knowledge_base", arguments, result_json, execution_time, "success")
        return result_json
        
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        log_tool_call("search_knowledge_base", arguments, error_msg, execution_time, "error")
        return error_msg

@mcp.tool()
async def categorize_issue(
    description: str,
    attachments: str = ""
) -> str:
    """
    Auto-categorize support issue based on content analysis.
    
    Args:
        description: Issue description to analyze
        attachments: Comma-separated list of attachment analysis results (optional)
    
    Returns:
        JSON string containing categorization results with confidence scores
    """
    start_time = datetime.now()
    arguments = {"description": description, "attachments": attachments}
    
    try:
        # Simple rule-based categorization (would be enhanced with ML)
        description_lower = description.lower()
        
        if any(word in description_lower for word in ["login", "password", "authentication", "access"]):
            category, priority = "user_access", "high"
        elif any(word in description_lower for word in ["bug", "error", "crash", "broken"]):
            category, priority = "bug", "high"
        elif any(word in description_lower for word in ["feature", "enhancement", "request"]):
            category, priority = "feature_request", "medium"
        elif any(word in description_lower for word in ["billing", "payment", "invoice"]):
            category, priority = "billing", "medium"
        else:
            category, priority = "general", "medium"
        
        # Determine urgency based on keywords
        if any(word in description_lower for word in ["urgent", "critical", "down", "broken"]):
            urgency = "critical"
        elif any(word in description_lower for word in ["important", "asap", "soon"]):
            urgency = "high"
        else:
            urgency = "medium"
        
        result = {
            "category": category,
            "priority": priority,
            "urgency": urgency,
            "department": "support" if category == "general" else "engineering",
            "confidence": 0.85,
            "analysis": {
                "keywords_found": [word for word in ["login", "bug", "feature", "billing"] if word in description_lower],
                "description_length": len(description),
                "has_attachments": bool(attachments.strip())
            }
        }
        
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        result_json = json.dumps(result, indent=2)
        log_tool_call("categorize_issue", arguments, result_json, execution_time, "success")
        return result_json
        
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        log_tool_call("categorize_issue", arguments, error_msg, execution_time, "error")
        return error_msg

# =============================================================================
# SYSTEM TOOLS
# =============================================================================

@mcp.tool()
async def get_system_health() -> str:
    """
    Check the overall health and status of the backend system.
    
    Returns:
        JSON string containing system health information
    """
    start_time = datetime.now()
    arguments = {}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BACKEND_URL}/health",
                timeout=30.0
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

# Add custom health endpoint
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> Response:
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
            "tools_available": 12,  # Number of tools defined above
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

if __name__ == "__main__":
    # Run the server with HTTP transport for Docker deployment
    import os
    from dotenv import load_dotenv
    
    # Load environment variables from .env file
    load_dotenv(".env")
    
    # Get configuration from environment variables
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8001"))
    path = os.getenv("MCP_PATH", "/mcp/")
    log_level = os.getenv("MCP_LOG_LEVEL", "info")
    
    logger.info("Starting MCP server with HTTP transport", extra={
        "host": host,
        "port": port,
        "path": path
    })
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