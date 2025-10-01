"""
Enhanced MCP Service with JWT Token Authentication
Provides MCP tools with user JWT token authentication for backend API calls
"""

import logging
from typing import Dict

import httpx
from pydantic_ai.tools import Tool

logger = logging.getLogger(__name__)

class AuthenticatedMCPService:
    """MCP service that provides tools with JWT token authentication"""
    
    def __init__(self):
        self.backend_url = "http://app:8000"
    
    def create_authenticated_mcp_tools(self, user_jwt_token: str) -> Dict[str, Tool]:
        """Create MCP tools with JWT token authentication"""
        
        async def list_tickets_with_auth(
            page: int = 1,
            page_size: int = 10,
            status: str = "",
            category: str = "",
            priority: str = ""
        ) -> str:
            """List tickets with JWT token authentication"""
            
            try:
                # Build query parameters
                params = {"page": page, "page_size": page_size}
                if status: params["status"] = status
                if category: params["category"] = category  
                if priority: params["priority"] = priority
                
                # Direct backend API call with JWT Authorization header
                headers = {"Authorization": f"Bearer {user_jwt_token}"}
                
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{self.backend_url}/api/v1/tickets",
                        params=params,
                        headers=headers
                    )
                
                if response.status_code == 200:
                    logger.info("[ENHANCED_MCP] list_tickets successful with JWT auth")
                    return response.text
                else:
                    error_msg = f"Error listing tickets: HTTP {response.status_code} - {response.text}"
                    logger.error(f"[ENHANCED_MCP] {error_msg}")
                    return error_msg
                    
            except Exception as e:
                error_msg = f"Error listing tickets: {str(e)}"
                logger.error(f"[ENHANCED_MCP] {error_msg}")
                return error_msg
        
        async def get_ticket_stats_with_auth() -> str:
            """Get ticket statistics with JWT token authentication"""
            
            try:
                # Direct backend API call with JWT Authorization header
                headers = {"Authorization": f"Bearer {user_jwt_token}"}
                
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{self.backend_url}/api/v1/tickets/stats/overview",
                        headers=headers
                    )
                
                if response.status_code == 200:
                    logger.info("[ENHANCED_MCP] get_ticket_stats successful with JWT auth")
                    return response.text
                else:
                    error_msg = f"Error getting ticket stats: HTTP {response.status_code} - {response.text}"
                    logger.error(f"[ENHANCED_MCP] {error_msg}")
                    return error_msg
                    
            except Exception as e:
                error_msg = f"Error getting ticket stats: {str(e)}"
                logger.error(f"[ENHANCED_MCP] {error_msg}")
                return error_msg
        
        async def create_ticket_with_auth(
            title: str,
            description: str,
            category: str = "general",
            priority: str = "medium"
        ) -> str:
            """Create ticket with JWT token authentication"""
            
            try:
                # Direct backend API call with JWT Authorization header
                headers = {"Authorization": f"Bearer {user_jwt_token}"}
                ticket_data = {
                    "title": title,
                    "description": description,
                    "category": category,
                    "priority": priority
                }
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.backend_url}/api/v1/tickets/ai-create",
                        headers=headers,
                        json=ticket_data
                    )
                
                if response.status_code in [200, 201]:
                    logger.info("[ENHANCED_MCP] create_ticket successful with JWT auth")
                    return response.text
                else:
                    error_msg = f"Error creating ticket: HTTP {response.status_code} - {response.text}"
                    logger.error(f"[ENHANCED_MCP] {error_msg}")
                    return error_msg
                    
            except Exception as e:
                error_msg = f"Error creating ticket: {str(e)}"
                logger.error(f"[ENHANCED_MCP] {error_msg}")
                return error_msg
        
        # Return simplified tools with JWT authentication
        return {
            "list_tickets": Tool(list_tickets_with_auth, name="list_tickets"),
            "get_ticket_stats": Tool(get_ticket_stats_with_auth, name="get_ticket_stats"),
            "create_ticket": Tool(create_ticket_with_auth, name="create_ticket")
        }

# Global service instance
enhanced_mcp_service = AuthenticatedMCPService()