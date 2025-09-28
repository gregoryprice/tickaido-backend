#!/usr/bin/env python3
"""
Principal-based Integration Tools for MCP Server

Integration tools that use Principal context for authorization.
"""

import json
import logging
import sys
import os
from datetime import datetime
from typing import Dict, Any, Optional

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.schemas.principal import Principal

logger = logging.getLogger(__name__)


def register_all_integration_tools(mcp):
    """Register Principal-based integration tools"""
    
    @mcp.tool()
    async def list_integrations(
        integration_type: str = "",
        status: str = "",
        is_enabled: str = "true",
        _mcp_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        List available integrations with Principal-based authorization.
        """
        try:
            # Extract Principal from MCP context
            if not _mcp_context or 'principal' not in _mcp_context:
                return json.dumps({
                    "error": "Principal context required",
                    "message": "MCP tools require Principal context from FastAPI"
                })
            
            principal_data = _mcp_context['principal']
            principal = Principal.from_dict(principal_data) if isinstance(principal_data, dict) else principal_data
            
            # Validate permission
            if not principal.can_access_tool("list_integrations"):
                return json.dumps({
                    "error": "Permission denied",
                    "message": f"User {principal.email} not authorized to list integrations"
                })
            
            # Mock integration data (would come from database in real implementation)
            integrations = [
                {
                    "integration_id": "jira-001",
                    "name": "JIRA Integration", 
                    "type": "ticket_management",
                    "status": "active",
                    "is_enabled": True,
                    "organization_id": principal.organization_id
                },
                {
                    "integration_id": "slack-001",
                    "name": "Slack Integration",
                    "type": "notification", 
                    "status": "active",
                    "is_enabled": True,
                    "organization_id": principal.organization_id
                }
            ]
            
            # Apply filters
            filtered_integrations = []
            for integration in integrations:
                if integration_type and integration["type"] != integration_type:
                    continue
                if status and integration["status"] != status:
                    continue
                if is_enabled.lower() == "false" and integration["is_enabled"]:
                    continue
                    
                filtered_integrations.append(integration)
            
            response = {
                "success": True,
                "integrations": filtered_integrations,
                "total": len(filtered_integrations),
                "organization_id": principal.organization_id
            }
            
            logger.info(f"✅ Principal MCP: Listed {len(filtered_integrations)} integrations for {principal.email}")
            return json.dumps(response, indent=2)
        
        except Exception as e:
            logger.error(f"❌ Principal MCP list_integrations failed: {e}")
            return json.dumps({"error": "Tool execution failed", "message": str(e)})
    
    @mcp.tool()
    async def get_active_integrations(
        supports_category: str = "",
        _mcp_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Get active integrations with Principal-based authorization.
        """
        try:
            # Extract Principal from MCP context
            if not _mcp_context or 'principal' not in _mcp_context:
                return json.dumps({
                    "error": "Principal context required",
                    "message": "MCP tools require Principal context from FastAPI"
                })
            
            principal_data = _mcp_context['principal']
            principal = Principal.from_dict(principal_data) if isinstance(principal_data, dict) else principal_data
            
            # Validate permission
            if not principal.can_access_tool("get_active_integrations"):
                return json.dumps({
                    "error": "Permission denied",
                    "message": f"User {principal.email} not authorized to get active integrations"
                })
            
            # Mock active integrations
            active_integrations = [
                {
                    "integration_id": "jira-001",
                    "name": "JIRA Integration",
                    "health_status": "healthy",
                    "capabilities": ["ticket_creation", "status_updates"],
                    "organization_id": principal.organization_id
                }
            ]
            
            response = {
                "success": True,
                "active_integrations": active_integrations,
                "total": len(active_integrations),
                "organization_id": principal.organization_id
            }
            
            logger.info(f"✅ Principal MCP: Listed {len(active_integrations)} active integrations for {principal.email}")
            return json.dumps(response, indent=2)
        
        except Exception as e:
            logger.error(f"❌ Principal MCP get_active_integrations failed: {e}")
            return json.dumps({"error": "Tool execution failed", "message": str(e)})
    
    logger.info("✅ Principal-based integration tools registered")