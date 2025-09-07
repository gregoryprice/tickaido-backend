"""
Unit tests for AuthenticatedMCPClient

Tests the JWT authentication functionality for MCP client integration,
ensuring that authentication headers are properly injected into all
MCP server requests.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import httpx

from mcp_client.authenticated_client import AuthenticatedMCPClient, AuthenticatedHTTPXClient


class TestAuthenticatedHTTPXClient:
    """Test the custom HTTPX client with authentication support"""
    
    def test_auth_header_injection_with_token(self):
        """Test that JWT tokens are properly injected into headers"""
        auth_token = "test-jwt-token-12345"
        client = AuthenticatedHTTPXClient(auth_token=auth_token)
        
        headers = client._get_auth_headers()
        
        assert "Authorization" in headers
        assert headers["Authorization"] == f"Bearer {auth_token}"
        
    def test_auth_header_injection_without_token(self):
        """Test that no auth headers are added when no token provided"""
        client = AuthenticatedHTTPXClient(auth_token=None)
        
        headers = client._get_auth_headers()
        
        assert "Authorization" not in headers
        assert headers == {}
        
    def test_client_initialization_with_token(self):
        """Test client initialization includes auth headers in default headers"""
        auth_token = "test-jwt-token-67890"
        client = AuthenticatedHTTPXClient(auth_token=auth_token)
        
        assert client.auth_token == auth_token
        # Should have Authorization header in default headers
        assert "Authorization" in client.headers
        assert client.headers["Authorization"] == f"Bearer {auth_token}"
        
    def test_client_initialization_without_token(self):
        """Test client initialization without token"""
        client = AuthenticatedHTTPXClient(auth_token=None)
        
        assert client.auth_token is None
        # Should not have Authorization header in default headers
        assert "Authorization" not in client.headers

    @pytest.mark.asyncio
    async def test_request_override_merges_headers(self):
        """Test that request method properly merges auth headers with existing headers"""
        auth_token = "test-merge-token"
        
        with patch('httpx.AsyncClient.request', new_callable=AsyncMock) as mock_request:
            # Mock the parent request method
            mock_response = Mock(spec=httpx.Response)
            mock_request.return_value = mock_response
            
            client = AuthenticatedHTTPXClient(auth_token=auth_token)
            
            # Make request with custom headers
            custom_headers = {"Content-Type": "application/json", "X-Custom": "value"}
            await client.request("POST", "https://test.com", headers=custom_headers)
            
            # Verify that the parent request was called with merged headers
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            
            # Check that both auth and custom headers are present
            merged_headers = call_args[1]['headers']
            assert merged_headers["Authorization"] == f"Bearer {auth_token}"
            assert merged_headers["Content-Type"] == "application/json"
            assert merged_headers["X-Custom"] == "value"

    @pytest.mark.asyncio 
    async def test_request_override_without_auth_token(self):
        """Test that request method works normally without auth token"""
        with patch('httpx.AsyncClient.request', new_callable=AsyncMock) as mock_request:
            mock_response = Mock(spec=httpx.Response)
            mock_request.return_value = mock_response
            
            client = AuthenticatedHTTPXClient(auth_token=None)
            
            custom_headers = {"Content-Type": "application/json"}
            await client.request("GET", "https://test.com", headers=custom_headers)
            
            # Verify no Authorization header added
            call_args = mock_request.call_args
            merged_headers = call_args[1]['headers']
            assert "Authorization" not in merged_headers
            assert merged_headers["Content-Type"] == "application/json"


class TestAuthenticatedMCPClient:
    """Test the AuthenticatedMCPClient wrapper"""
    
    def test_authenticated_client_creation_with_token(self):
        """Test creating authenticated MCP client with JWT token"""
        url = "http://test-mcp-server:8001/mcp/"
        auth_token = "test-auth-token"
        
        with patch('mcp_client.authenticated_client.AuthenticatedHTTPXClient') as mock_http_client:
            with patch('pydantic_ai.mcp.MCPServerStreamableHTTP.__init__', return_value=None) as mock_parent_init:
                
                client = AuthenticatedMCPClient(url, auth_token=auth_token)
                
                # Verify HTTP client was created with auth token
                mock_http_client.assert_called_once_with(auth_token=auth_token)
                
                # Verify parent constructor was called with http_client
                mock_parent_init.assert_called_once()
                call_args = mock_parent_init.call_args
                assert call_args[0][0] == url  # URL argument
                assert 'http_client' in call_args[1]  # http_client in kwargs
                
                # Verify client properties
                assert client.auth_token == auth_token
                assert client._is_authenticated is True
                
    def test_authenticated_client_creation_without_token(self):
        """Test creating MCP client without authentication token"""
        url = "http://test-mcp-server:8001/mcp/"
        
        with patch('pydantic_ai.mcp.MCPServerStreamableHTTP.__init__', return_value=None) as mock_parent_init:
            
            client = AuthenticatedMCPClient(url, auth_token=None)
            
            # Verify parent constructor was called without http_client
            mock_parent_init.assert_called_once()
            call_args = mock_parent_init.call_args
            assert call_args[0][0] == url  # URL argument
            assert 'http_client' not in call_args[1]  # No http_client in kwargs
            
            # Verify client properties
            assert client.auth_token is None
            assert client._is_authenticated is False

    def test_get_auth_info_with_token(self):
        """Test getting authentication information with token"""
        url = "http://test-mcp-server:8001/mcp/"
        auth_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.signature"
        
        with patch('pydantic_ai.mcp.MCPServerStreamableHTTP.__init__', return_value=None):
            client = AuthenticatedMCPClient(url, auth_token=auth_token)
            
            auth_info = client.get_auth_info()
            
            assert auth_info["is_authenticated"] is True
            assert auth_info["has_token"] is True
            assert "token_preview" in auth_info
            # Should show first 8 and last 4 characters
            assert auth_info["token_preview"] == "eyJhbGci...ture"

    def test_get_auth_info_without_token(self):
        """Test getting authentication information without token"""
        url = "http://test-mcp-server:8001/mcp/"
        
        with patch('pydantic_ai.mcp.MCPServerStreamableHTTP.__init__', return_value=None):
            client = AuthenticatedMCPClient(url, auth_token=None)
            
            auth_info = client.get_auth_info()
            
            assert auth_info["is_authenticated"] is False
            assert auth_info["has_token"] is False
            assert "token_preview" not in auth_info

    def test_get_auth_info_with_short_token(self):
        """Test getting authentication information with short token"""
        url = "http://test-mcp-server:8001/mcp/"
        auth_token = "short"
        
        with patch('pydantic_ai.mcp.MCPServerStreamableHTTP.__init__', return_value=None):
            client = AuthenticatedMCPClient(url, auth_token=auth_token)
            
            auth_info = client.get_auth_info()
            
            assert auth_info["token_preview"] == "[SHORT_TOKEN]"

    def test_update_auth_token(self):
        """Test updating authentication token"""
        url = "http://test-mcp-server:8001/mcp/"
        initial_token = "initial-token"
        new_token = "updated-token"
        
        with patch('pydantic_ai.mcp.MCPServerStreamableHTTP.__init__', return_value=None):
            client = AuthenticatedMCPClient(url, auth_token=initial_token)
            
            # Update token
            client.update_auth_token(new_token)
            
            assert client.auth_token == new_token
            assert client._is_authenticated is True

    def test_update_auth_token_to_none(self):
        """Test removing authentication token"""
        url = "http://test-mcp-server:8001/mcp/"
        initial_token = "initial-token"
        
        with patch('pydantic_ai.mcp.MCPServerStreamableHTTP.__init__', return_value=None):
            client = AuthenticatedMCPClient(url, auth_token=initial_token)
            
            # Remove token
            client.update_auth_token(None)
            
            assert client.auth_token is None
            assert client._is_authenticated is False

    def test_repr_authenticated(self):
        """Test string representation of authenticated client"""
        url = "http://test-mcp-server:8001/mcp/"
        auth_token = "test-token"
        
        with patch('pydantic_ai.mcp.MCPServerStreamableHTTP.__init__', return_value=None):
            client = AuthenticatedMCPClient(url, auth_token=auth_token)
            
            assert repr(client) == "AuthenticatedMCPClient(authenticated)"

    def test_repr_non_authenticated(self):
        """Test string representation of non-authenticated client"""
        url = "http://test-mcp-server:8001/mcp/"
        
        with patch('pydantic_ai.mcp.MCPServerStreamableHTTP.__init__', return_value=None):
            client = AuthenticatedMCPClient(url, auth_token=None)
            
            assert repr(client) == "AuthenticatedMCPClient(non-authenticated)"


@pytest.mark.integration
class TestAuthenticatedMCPClientIntegration:
    """Integration tests for AuthenticatedMCPClient with real HTTP behavior"""
    
    @pytest.mark.asyncio
    async def test_auth_headers_in_real_request(self):
        """Test that authentication headers are actually sent in real HTTP requests"""
        url = "http://test-server/mcp/"
        auth_token = "real-test-token"
        
        # Mock the actual HTTP transport to verify headers
        with patch('httpx.AsyncClient') as MockClient:
            mock_client_instance = MockClient.return_value.__aenter__.return_value
            mock_response = Mock()
            mock_client_instance.request = AsyncMock(return_value=mock_response)
            
            # Create client with authentication
            http_client = AuthenticatedHTTPXClient(auth_token=auth_token)
            
            # Make a request
            await http_client.request("POST", url, json={"test": "data"})
            
            # Verify the request was made with proper auth headers
            mock_client_instance.request.assert_called_once()
            call_args = mock_client_instance.request.call_args
            
            headers = call_args[1]["headers"]
            assert "Authorization" in headers
            assert headers["Authorization"] == f"Bearer {auth_token}"