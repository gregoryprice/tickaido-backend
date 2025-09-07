#!/usr/bin/env python3
"""
MCP Tools Package

This package contains organized MCP tools for the AI Ticket Creator backend.
Tools are grouped by functionality for better maintainability and organization.
"""

# Common imports and utilities for all tools
import os
import logging
import json
from datetime import datetime
from typing import Dict, Any

# Backend URL configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


# Tool logging utility
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
    tool_logger = logging.getLogger("mcp_tool_calls")
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

# Export tools from submodules
# Note: Individual tool modules handle their own registrations