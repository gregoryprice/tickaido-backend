#!/usr/bin/env python3
"""
Unit Tests for FastMCP Server

Tests the FastMCP server functionality including:
- Token-based authentication
- API-based tool implementations
- Error handling and logging
"""

import pytest
import json
from unittest.mock import patch, AsyncMock
import httpx


class TestFastMCPServer:
    """Test FastMCP server with token authentication."""
    
    def test_development_tokens_configured(self):
        """Test that development tokens are properly configured."""
        from mcp_server.auth_server import DEVELOPMENT_TOKENS
        
        # Check that required tokens are present
        assert "dev-alice-token" in DEVELOPMENT_TOKENS
        assert "ai_dev_MwUVUygQboY9yIeXQ539PYTJfv9Y7yeexWL4TrELMB8" in DEVELOPMENT_TOKENS
        
        # Check Alice token structure
        alice_token = DEVELOPMENT_TOKENS["dev-alice-token"]
        assert alice_token["user_id"] == "alice"
        assert alice_token["organization_id"] == "dev-org"
        assert "read:tickets" in alice_token["scopes"]
        
        # Check AI dev token structure
        ai_token = DEVELOPMENT_TOKENS["ai_dev_MwUVUygQboY9yIeXQ539PYTJfv9Y7yeexWL4TrELMB8"]
        assert ai_token["user_id"] == "9cdd4c6c-a65d-464b-b3ba-64e6781fba2b"
        assert ai_token["organization_id"] == "20a8aae5-ec85-42a9-b025-45ee32a2f9a1"
        assert "read:tickets" in ai_token["scopes"]
        assert "write:tickets" in ai_token["scopes"]
    
    def test_token_verifier_configuration(self):
        """Test that token verifier is properly configured."""
        from mcp_server.auth_server import token_verifier
        
        # Check that verifier has the required tokens
        assert hasattr(token_verifier, 'tokens')
        # Static token verifier should have proper configuration
        assert token_verifier is not None
    
    @pytest.mark.asyncio
    async def test_list_tickets_tool_success(self):
        """Test list_tickets tool with successful API call."""
        # Mock httpx response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = '{"success": true, "tickets": [], "total": 0}'
        
        # Mock context object
        mock_context = AsyncMock()
        mock_context.session.auth_context = {
            "user_id": "test-user",
            "organization_id": "test-org"
        }
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            # Import and call the tool
            from mcp_server.auth_server import list_tickets
            result = await list_tickets(mock_context, page=1, page_size=10)
            
            # Verify result
            assert result == '{"success": true, "tickets": [], "total": 0}'
            
            # Verify API call was made correctly
            mock_client.get.assert_called_once()
            call_args = mock_client.get.call_args
            
            assert "api/v1/tickets" in call_args[0][0]
            assert call_args[1]["headers"]["X-User-ID"] == "test-user"
            assert call_args[1]["headers"]["X-Organization-ID"] == "test-org"
            assert call_args[1]["params"]["page"] == 1
            assert call_args[1]["params"]["page_size"] == 10
    
    @pytest.mark.asyncio
    async def test_list_tickets_tool_api_failure(self):
        """Test list_tickets tool with API failure."""
        # Mock httpx response
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        # Mock context object
        mock_context = AsyncMock()
        mock_context.session.auth_context = {
            "user_id": "test-user",
            "organization_id": "test-org"
        }
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            # Import and call the tool
            from mcp_server.auth_server import list_tickets
            result = await list_tickets(mock_context)
            
            # Verify error response
            error_data = json.loads(result)
            assert error_data["error"] == "Failed to retrieve tickets"
            assert error_data["status_code"] == 500
    
    @pytest.mark.asyncio
    async def test_create_ticket_tool_success(self):
        """Test create_ticket tool with successful API call."""
        # Mock httpx response
        mock_response = AsyncMock()
        mock_response.status_code = 201
        mock_response.text = '{"success": true, "ticket_id": "123", "title": "Test Ticket"}'
        
        # Mock context object
        mock_context = AsyncMock()
        mock_context.session.auth_context = {
            "user_id": "test-user",
            "organization_id": "test-org"
        }
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            # Import and call the tool
            from mcp_server.auth_server import create_ticket
            result = await create_ticket(
                mock_context, 
                title="Test Ticket", 
                description="Test description",
                category="bug",
                priority="high"
            )
            
            # Verify result
            assert result == '{"success": true, "ticket_id": "123", "title": "Test Ticket"}'
            
            # Verify API call was made correctly
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            
            assert "api/v1/tickets/ai-create" in call_args[0][0]
            assert call_args[1]["headers"]["X-User-ID"] == "test-user"
            assert call_args[1]["headers"]["X-Organization-ID"] == "test-org"
            
            # Verify request data
            request_data = call_args[1]["json"]
            assert request_data["title"] == "Test Ticket"
            assert request_data["description"] == "Test description"
            assert request_data["category"] == "bug"
            assert request_data["priority"] == "high"
    
    @pytest.mark.asyncio
    async def test_create_ticket_tool_validation_error(self):
        """Test create_ticket tool with validation error."""
        # Mock context object
        mock_context = AsyncMock()
        mock_context.session.auth_context = {
            "user_id": "test-user",
            "organization_id": "test-org"
        }
        
        # Import and call the tool with empty title
        from mcp_server.auth_server import create_ticket
        result = await create_ticket(mock_context, title="", description="Test description")
        
        # Verify validation error
        error_data = json.loads(result)
        assert error_data["error"] == "Title is required"
    
    @pytest.mark.asyncio
    async def test_search_tickets_tool_success(self):
        """Test search_tickets tool with successful API call."""
        # Mock httpx response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = '{"success": true, "results": [], "query": "test"}'
        
        # Mock context object
        mock_context = AsyncMock()
        mock_context.session.auth_context = {
            "user_id": "test-user",
            "organization_id": "test-org"
        }
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            # Import and call the tool
            from mcp_server.auth_server import search_tickets
            result = await search_tickets(
                mock_context,
                query="test search",
                status="open",
                page=1,
                page_size=20
            )
            
            # Verify result
            assert result == '{"success": true, "results": [], "query": "test"}'
            
            # Verify API call was made correctly
            mock_client.get.assert_called_once()
            call_args = mock_client.get.call_args
            
            assert "api/v1/tickets/search" in call_args[0][0]
            assert call_args[1]["params"]["query"] == "test search"
            assert call_args[1]["params"]["status"] == "open"
            assert call_args[1]["params"]["page_size"] == 20
    
    @pytest.mark.asyncio
    async def test_get_ticket_tool_success(self):
        """Test get_ticket tool with successful API call."""
        # Mock httpx response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = '{"success": true, "ticket": {"id": "123", "title": "Test"}}'
        
        # Mock context object
        mock_context = AsyncMock()
        mock_context.session.auth_context = {
            "user_id": "test-user",
            "organization_id": "test-org"
        }
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            # Import and call the tool
            from mcp_server.auth_server import get_ticket
            result = await get_ticket(mock_context, ticket_id="123")
            
            # Verify result
            assert result == '{"success": true, "ticket": {"id": "123", "title": "Test"}}'
    
    @pytest.mark.asyncio
    async def test_get_ticket_not_found(self):
        """Test get_ticket tool with ticket not found."""
        # Mock httpx response
        mock_response = AsyncMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        
        # Mock context object
        mock_context = AsyncMock()
        mock_context.session.auth_context = {
            "user_id": "test-user",
            "organization_id": "test-org"
        }
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            # Import and call the tool
            from mcp_server.auth_server import get_ticket
            result = await get_ticket(mock_context, ticket_id="nonexistent")
            
            # Verify result
            error_data = json.loads(result)
            assert error_data["error"] == "Ticket not found"
            assert error_data["ticket_id"] == "nonexistent"
    
    @pytest.mark.asyncio
    async def test_get_system_health_success(self):
        """Test get_system_health tool with successful API call."""
        # Mock httpx response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = '{"status": "healthy", "timestamp": "2023-01-01T00:00:00Z"}'
        
        # Mock context object
        mock_context = AsyncMock()
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            # Import and call the tool
            from mcp_server.auth_server import get_system_health
            result = await get_system_health(mock_context)
            
            # Verify result
            health_data = json.loads(result)
            assert health_data["status"] == "healthy"
            assert health_data["mcp_server"] == "operational"
    
    @pytest.mark.asyncio
    async def test_tool_exception_handling(self):
        """Test that tools handle exceptions properly."""
        # Mock context object
        mock_context = AsyncMock()
        mock_context.session.auth_context = {
            "user_id": "test-user",
            "organization_id": "test-org"
        }
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_class.side_effect = Exception("Network error")
            
            # Import and call the tool
            from mcp_server.auth_server import list_tickets
            result = await list_tickets(mock_context)
            
            # Verify error handling
            error_data = json.loads(result)
            assert error_data["error"] == "Tool execution failed"
            assert "Network error" in error_data["message"]