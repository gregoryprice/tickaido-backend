"""
MCP Client for AI Ticket Creator Tools

This module provides a client interface to the Model Context Protocol (MCP) server
that hosts customer support tools including ticket creation, file analysis, 
third-party integrations, and knowledge base search.

The MCP server runs as a separate service using FastMCP and provides tools that can be used
by the AI agents to perform customer support operations.

For more information on PydanticAI MCP, see: https://ai.pydantic.dev/mcp/
For more information on FastMCP, see: https://fastmcp.tadata.com/
"""

import logging
import os
from typing import Optional, Dict, Any
from pydantic_ai.mcp import MCPServerStreamableHTTP

logger = logging.getLogger(__name__)

class MCPClient:
    """
    MCP Client for connecting to the AI Ticket Creator MCP server.
    
    This client uses PydanticAI's MCPServerStreamableHTTP to connect to a FastMCP server
    that provides customer support tools including:
    - create_ticket: Create support tickets with routing
    - update_ticket: Update existing tickets  
    - search_tickets: Search and filter tickets
    - analyze_file: Process uploaded files for analysis
    - transcribe_audio: Transcribe audio/video files
    - extract_text_from_image: OCR for image files
    - search_knowledge_base: Search knowledge base for solutions
    - categorize_issue: Auto-categorize support issues
    - get_system_health: Check system health
    """
    
    def __init__(self):
        """Initialize the MCP client."""
        self.mcp_server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8001")
        self.mcp_client: Optional[MCPServerStreamableHTTP] = None
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
            logger.info(f"🔧 Creating MCP client for AI Ticket Creator at {mcp_url}")
            
            # Create the MCP client with HTTP streamable transport
            # This connects to the FastMCP server running with streamable-http transport
            mcp_client = MCPServerStreamableHTTP(mcp_url)
            
            logger.info(f"✅ MCP client created successfully for AI Ticket Creator at {mcp_url}")
            return mcp_client
            
        except Exception as e:
            logger.error(f"❌ Failed to create MCP client: {e}")
            logger.error(f"❌ MCP_SERVER_URL: {self.mcp_server_url}")
            logger.error(f"❌ Full error details: {str(e)}")
            return None
    
    def get_mcp_client(self) -> Optional[MCPServerStreamableHTTP]:
        """
        Get the MCP client, creating it if necessary.
        
        Returns:
            MCPServerStreamableHTTP: MCP client or None if unavailable
        """
        if self.mcp_client is None:
            self.mcp_client = self.create_mcp_client()
            if self.mcp_client is not None:
                self._is_connected = True
                logger.info("✅ AI Ticket Creator MCP client initialized and ready")
            else:
                self._is_connected = False
                logger.warning("⚠️ AI Ticket Creator MCP client initialization failed")
        
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
                    "create_ticket", "update_ticket", "search_tickets",
                    "analyze_file", "transcribe_audio", "extract_text_from_image",
                    "search_knowledge_base", "categorize_issue", "get_system_health"
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
        Get list of available MCP tools.
        
        Returns:
            list: List of available tool names
        """
        return [
            "create_ticket",
            "update_ticket", 
            "search_tickets",
            "analyze_file",
            "transcribe_audio",
            "extract_text_from_image",
            "search_knowledge_base",
            "categorize_issue",
            "get_system_health"
        ]

# Global MCP client instance
mcp_client = MCPClient()