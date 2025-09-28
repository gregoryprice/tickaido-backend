#!/usr/bin/env python3
"""
Unit Tests for FastMCP Client

Tests the FastMCP client wrapper functionality including:
- Client creation and authentication
- Tool calling interface
- Error handling and connectivity
"""

import pytest
from unittest.mock import patch, AsyncMock
from mcp_client.fast_client import FastMCPClientWrapper, create_fastmcp_client
from app.schemas.principal import Principal


class TestFastMCPClient:
    """Test FastMCP client wrapper functionality."""
    
    def test_client_creation(self):
        """Test FastMCP client creation with token."""
        client = FastMCPClientWrapper(token="test-token")
        assert client is not None
        assert client.token == "test-token"
        assert client.url == "http://mcp-server:8001"
    
    def test_client_custom_url(self):
        """Test FastMCP client creation with custom URL."""
        client = FastMCPClientWrapper(
            url="http://localhost:8001/mcp", 
            token="test-token"
        )
        assert client.url == "http://localhost:8001/mcp"
        assert client.token == "test-token"
    
    def test_client_authentication_headers(self):
        """Test that client sets proper Authorization headers."""
        client = FastMCPClientWrapper(token="test-token-123")
        headers = client.get_headers()
        assert headers["Authorization"] == "Bearer test-token-123"
    
    def test_client_unauthenticated(self):
        """Test unauthenticated client creation."""
        client = FastMCPClientWrapper()
        assert not client.is_authenticated()
        assert client.token is None
        assert client.get_headers() == {}
    
    def test_client_from_principal(self):
        """Test client creation from Principal object."""
        principal = Principal(
            user_id="test-user",
            email="test@example.com",
            organization_id="test-org",
            api_token="principal-token-456"
        )
        
        client = FastMCPClientWrapper.from_principal(principal)
        assert client.is_authenticated()
        assert client.token == "principal-token-456"
        assert client.get_headers()["Authorization"] == "Bearer principal-token-456"
    
    def test_client_from_principal_no_token(self):
        """Test client creation from Principal without token."""
        principal = Principal(
            user_id="test-user",
            email="test@example.com",
            organization_id="test-org"
        )
        
        client = FastMCPClientWrapper.from_principal(principal)
        assert not client.is_authenticated()
        assert client.token is None
    
    @pytest.mark.asyncio
    async def test_client_ping_success(self):
        """Test successful server ping."""
        client = FastMCPClientWrapper(token="test-token")
        
        with patch.object(client, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.ping = AsyncMock()
            mock_get_client.return_value = mock_client
            
            result = await client.ping()
            
            assert result is True
            mock_client.ping.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_client_ping_failure(self):
        """Test server ping failure."""
        client = FastMCPClientWrapper(token="test-token")
        
        with patch.object(client, '_get_client') as mock_get_client:
            mock_get_client.side_effect = Exception("Connection failed")
            
            result = await client.ping()
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_list_tools(self):
        """Test listing tools from server."""
        client = FastMCPClientWrapper(token="test-token")
        
        # Mock tool objects
        mock_tool1 = type('Tool', (), {'name': 'list_tickets', 'description': 'List tickets'})()
        mock_tool2 = type('Tool', (), {'name': 'create_ticket', 'description': 'Create ticket'})()
        
        with patch.object(client, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.list_tools.return_value = [mock_tool1, mock_tool2]
            mock_get_client.return_value = mock_client
            
            tools = await client.list_tools()
            
            assert len(tools) == 2
            assert tools[0]["name"] == "list_tickets"
            assert tools[1]["name"] == "create_ticket"
            mock_client.list_tools.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_call_tool_success(self):
        """Test successful tool calling."""
        client = FastMCPClientWrapper(token="test-token")
        
        # Mock result with content attribute
        mock_result = type('Result', (), {'content': '{"success": true, "tickets": []}'})()
        
        with patch.object(client, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.call_tool.return_value = mock_result
            mock_get_client.return_value = mock_client
            
            result = await client.call_tool("list_tickets", page=1, page_size=10)
            
            assert result == '{"success": true, "tickets": []}'
            mock_client.call_tool.assert_called_once_with("list_tickets", {"page": 1, "page_size": 10})
    
    @pytest.mark.asyncio
    async def test_call_tool_direct_result(self):
        """Test tool calling with direct result (no content attribute)."""
        client = FastMCPClientWrapper(token="test-token")
        
        with patch.object(client, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.call_tool.return_value = "Direct result"
            mock_get_client.return_value = mock_client
            
            result = await client.call_tool("get_health")
            
            assert result == "Direct result"
    
    @pytest.mark.asyncio
    async def test_call_tool_failure(self):
        """Test tool calling failure."""
        client = FastMCPClientWrapper(token="test-token")
        
        with patch.object(client, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.call_tool.side_effect = Exception("Tool execution failed")
            mock_get_client.return_value = mock_client
            
            result = await client.call_tool("broken_tool", param="value")
            
            # Should return error JSON
            import json
            error_data = json.loads(result)
            assert error_data["error"] == "Tool execution failed: Tool execution failed"
            assert error_data["tool_name"] == "broken_tool"
            assert error_data["parameters"] == {"param": "value"}
    
    @pytest.mark.asyncio
    async def test_close(self):
        """Test client cleanup."""
        client = FastMCPClientWrapper(token="test-token")
        
        # Create a mock client
        mock_client = AsyncMock()
        client._client = mock_client
        
        await client.close()
        
        # Client reference should be cleared
        assert client._client is None


class TestFastMCPClientFactory:
    """Test FastMCP client factory functions."""
    
    @pytest.mark.asyncio
    async def test_create_fastmcp_client(self):
        """Test factory function for creating FastMCP client."""
        client = await create_fastmcp_client("http://test:8001", "test-token")
        
        assert isinstance(client, FastMCPClientWrapper)
        assert client.url == "http://test:8001"
        assert client.token == "test-token"
    
    def test_get_fastmcp_client_for_principal(self):
        """Test getting FastMCP client for principal."""
        from mcp_client.fast_client import get_fastmcp_client_for_principal
        
        principal = Principal(
            user_id="test-user",
            email="test@example.com",
            organization_id="test-org",
            api_token="principal-token"
        )
        
        client = get_fastmcp_client_for_principal(principal)
        
        assert isinstance(client, FastMCPClientWrapper)
        assert client.token == "principal-token"
        assert client.is_authenticated()
    
    def test_get_fastmcp_client_no_principal(self):
        """Test getting FastMCP client without principal."""
        from mcp_client.fast_client import get_fastmcp_client_for_principal
        
        client = get_fastmcp_client_for_principal(None)
        
        assert isinstance(client, FastMCPClientWrapper)
        assert client.token is None
        assert not client.is_authenticated()