#!/usr/bin/env python3
"""
Comprehensive tests for MCP authentication flows.

Tests all authentication scenarios including:
- Valid authentication with API tokens and JWT tokens
- Token validation and expiry scenarios
- Header format validation
- Principal integration
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, AsyncMock
from mcp_client.client import MCPClient, mcp_client
from app.schemas.principal import Principal
from app.middleware.auth_middleware import clerk_auth


class TestMCPAuthenticationFlow:
    """Test suite for MCP authentication flows."""
    
    def create_test_principal(self, api_token=None, expires_in_hours=1, expired=False) -> Principal:
        """Create a test principal for testing."""
        if not api_token:
            api_token = "ai_dev_test_token_123"
        
        expires_at = datetime.now(timezone.utc)
        if expired:
            expires_at -= timedelta(hours=1)  # Already expired
        else:
            expires_at += timedelta(hours=expires_in_hours)
        
        return Principal(
            user_id="test-user-123",
            organization_id="test-org-456",
            email="test@example.com",
            full_name="Test User",
            api_token=api_token,
            roles=["user"],
            permissions=["ticket.create", "ticket.read"],
            token_issued_at=datetime.now(timezone.utc),
            token_expires_at=expires_at
        )
    
    def test_principal_get_headers_for_mcp(self):
        """Test Principal's get_headers_for_mcp method."""
        principal = self.create_test_principal()
        headers = principal.get_headers_for_mcp()
        
        # Verify header format matches test_mcp_client.py
        assert "Authorization" in headers
        assert headers["Authorization"] == f"Bearer {principal.api_token}"
        assert "X-API-KEY" in headers
        assert headers["X-API-KEY"] == principal.api_token
        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"
    
    def test_principal_get_headers_for_mcp_no_token(self):
        """Test header generation when no token available."""
        principal = Principal(
            user_id="test-user",
            organization_id="test-org",
            email="test@example.com"
        )
        
        headers = principal.get_headers_for_mcp()
        assert headers == {"Content-Type": "application/json"}
    
    def test_principal_token_validation(self):
        """Test Principal token validation methods."""
        # Valid token
        valid_principal = self.create_test_principal()
        assert valid_principal.is_token_valid()
        assert not valid_principal.is_token_expired()
        
        # Expired token
        expired_principal = self.create_test_principal(expired=True)
        assert not expired_principal.is_token_valid()
        assert expired_principal.is_token_expired()
    
    def test_mcp_client_get_auth_headers_from_principal(self):
        """Test MCP Client's _get_auth_headers_from_principal method."""
        client = MCPClient()
        principal = self.create_test_principal()
        
        headers = client._get_auth_headers_from_principal(principal)
        
        assert headers is not None
        assert headers["Authorization"] == f"Bearer {principal.api_token}"
        assert headers["X-API-KEY"] == principal.api_token
        assert headers["Content-Type"] == "application/json"
    
    def test_mcp_client_get_auth_headers_no_token(self):
        """Test header extraction when principal has no token."""
        client = MCPClient()
        principal = Principal(
            user_id="test-user",
            organization_id="test-org",
            email="test@example.com"
        )
        
        headers = client._get_auth_headers_from_principal(principal)
        assert headers is None
    
    @patch('mcp_client.client.MCPServerStreamableHTTP')
    def test_create_authenticated_client_success(self, mock_mcp_server):
        """Test successful authenticated MCP client creation."""
        client = MCPClient()
        principal = self.create_test_principal()
        mcp_url = "http://test-server:8001/mcp/"
        
        # Mock the MCPServerStreamableHTTP constructor
        mock_instance = Mock()
        mock_mcp_server.return_value = mock_instance
        
        result = client._create_authenticated_client(principal, mcp_url)
        
        assert result is not None
        assert result == mock_instance
        assert hasattr(result, '_principal')
        assert result._principal == principal
        
        # Verify MCPServerStreamableHTTP was called with headers
        mock_mcp_server.assert_called_once()
        call_args = mock_mcp_server.call_args
        assert call_args[0][0] == mcp_url  # First positional arg is URL
        assert 'headers' in call_args[1]   # Headers passed as keyword arg
        
        headers = call_args[1]['headers']
        assert headers["Authorization"] == f"Bearer {principal.api_token}"
        assert headers["X-API-KEY"] == principal.api_token
    
    def test_create_authenticated_client_invalid_token(self):
        """Test authenticated client creation with invalid token."""
        client = MCPClient()
        principal = self.create_test_principal(expired=True)
        mcp_url = "http://test-server:8001/mcp/"
        
        result = client._create_authenticated_client(principal, mcp_url)
        assert result is None
    
    def test_create_agent_client_no_principal(self):
        """Test agent client creation without principal."""
        client = MCPClient()
        
        result = client.create_agent_client(
            agent_id="test-agent",
            tools=["create_ticket"],
            principal=None
        )
        
        assert result is None
    
    def test_create_agent_client_invalid_principal(self):
        """Test agent client creation with invalid principal."""
        client = MCPClient()
        principal = self.create_test_principal(expired=True)
        
        result = client.create_agent_client(
            agent_id="test-agent", 
            tools=["create_ticket"],
            principal=principal
        )
        
        assert result is None
    
    @patch('mcp_client.client.create_filtered_mcp_client')
    @patch('mcp_client.client.MCPServerStreamableHTTP')
    def test_create_agent_client_success(self, mock_mcp_server, mock_filter):
        """Test successful agent client creation with authentication."""
        client = MCPClient()
        principal = self.create_test_principal()
        tools = ["create_ticket", "list_tickets"]
        
        # Mock dependencies
        mock_base_client = Mock()
        mock_base_client._principal = principal
        mock_mcp_server.return_value = mock_base_client
        
        mock_filtered_client = Mock()
        mock_filter.return_value = mock_filtered_client
        
        result = client.create_agent_client(
            agent_id="test-agent",
            tools=tools,
            principal=principal
        )
        
        assert result is not None
        assert result == mock_filtered_client
        
        # Verify filtering was applied
        mock_filter.assert_called_once_with(mock_base_client, tools, "test-agent")
    
    def test_cache_key_generation(self):
        """Test cache key generation includes authentication context."""
        client = MCPClient()
        principal1 = self.create_test_principal(api_token="token1")
        principal2 = self.create_test_principal(api_token="token2")
        
        # Different principals should generate different cache keys
        key1 = f"{principal1.get_cache_hash()}_test-agent_{hash(tuple(sorted(['tool1'])))}"
        key2 = f"{principal2.get_cache_hash()}_test-agent_{hash(tuple(sorted(['tool1'])))}"
        
        assert key1 != key2
    
    def test_principal_cache_hash_consistency(self):
        """Test that Principal cache hash is consistent for same data."""
        principal1 = self.create_test_principal()
        principal2 = self.create_test_principal()  # Same data
        
        # Same principal data should generate same hash
        assert principal1.get_cache_hash() == principal2.get_cache_hash()
        
        # Different tokens should generate different hashes
        principal3 = self.create_test_principal(api_token="different-token")
        assert principal1.get_cache_hash() != principal3.get_cache_hash()
    
    @pytest.mark.asyncio
    async def test_auth_failure_handling(self):
        """Test authentication failure handling."""
        client = MCPClient()
        principal = self.create_test_principal()
        
        with patch('app.services.token_refresh_service.token_refresh_service') as mock_refresh_service:
            # Mock successful refresh
            refreshed_principal = self.create_test_principal(api_token="new-token")
            mock_refresh_service.handle_mcp_auth_failure.return_value = refreshed_principal
            
            result = await client._handle_auth_failure(principal, 401)
            
            assert result is not None
            assert result.api_token == "new-token"
            mock_refresh_service.handle_mcp_auth_failure.assert_called_once_with(principal, 401)
    
    @pytest.mark.asyncio  
    async def test_auth_failure_handling_failed_refresh(self):
        """Test authentication failure handling when refresh fails."""
        client = MCPClient()
        principal = self.create_test_principal()
        
        with patch('app.services.token_refresh_service.token_refresh_service') as mock_refresh_service:
            # Mock failed refresh
            mock_refresh_service.handle_mcp_auth_failure.return_value = None
            
            result = await client._handle_auth_failure(principal, 401)
            
            assert result is None
            mock_refresh_service.handle_mcp_auth_failure.assert_called_once_with(principal, 401)
    
    def test_cache_invalidation(self):
        """Test cache invalidation for expired principals."""
        client = MCPClient()
        principal = self.create_test_principal()
        
        # Add some mock cache entries
        cache_key1 = f"{principal.get_cache_hash()}_agent1_123"
        cache_key2 = f"{principal.get_cache_hash()}_agent2_456"
        cache_key3 = "different_hash_agent3_789"
        
        client._agent_clients[cache_key1] = Mock()
        client._agent_clients[cache_key2] = Mock()
        client._agent_clients[cache_key3] = Mock()
        
        # Invalidate cache for this principal
        client._invalidate_expired_cache(principal)
        
        # Only entries for this principal should be removed
        assert cache_key1 not in client._agent_clients
        assert cache_key2 not in client._agent_clients
        assert cache_key3 in client._agent_clients  # Different principal hash
    
    def test_api_token_format_validation(self):
        """Test validation of API token formats."""
        # Valid API token format
        valid_tokens = [
            "ai_dev_abcdef123456",
            "ai_san_xyz789",
            "ai_pro_production_token"
        ]
        
        for token in valid_tokens:
            principal = self.create_test_principal(api_token=token)
            headers = principal.get_headers_for_mcp()
            assert headers["Authorization"] == f"Bearer {token}"
            assert headers["X-API-KEY"] == token
    
    def test_jwt_token_support(self):
        """Test JWT token support in Principal."""
        # Create principal with JWT token in jwt_payload
        principal = Principal(
            user_id="test-user",
            organization_id="test-org",
            email="test@example.com",
            jwt_payload={"raw_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."}
        )
        
        # Should get JWT token from jwt_payload
        token = principal.get_auth_token()
        assert token == "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
        
        # Headers should use JWT token
        headers = principal.get_headers_for_mcp()
        assert headers["Authorization"] == f"Bearer {token}"
        assert headers["X-API-KEY"] == token


@pytest.mark.integration
class TestMCPAuthenticationIntegration:
    """Integration tests for MCP authentication."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_authentication_flow(self):
        """Test complete authentication flow from Principal to MCP client."""
        # This would require actual MCP server running
        # For now, just test the setup without actual network calls
        
        principal = Principal(
            user_id="test-user",
            organization_id="test-org", 
            email="test@example.com",
            api_token="ai_dev_test_token",
            roles=["user"],
            permissions=["ticket.create"],
            token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        # Test client creation (mocked)
        with patch('mcp_client.client.MCPServerStreamableHTTP') as mock_mcp:
            mock_instance = Mock()
            mock_mcp.return_value = mock_instance
            
            client = mcp_client.create_agent_client(
                agent_id="test-agent",
                tools=["create_ticket"],
                principal=principal
            )
            
            assert client is not None
            # Verify proper headers were used
            mock_mcp.assert_called()
            call_kwargs = mock_mcp.call_args[1]
            assert 'headers' in call_kwargs
            headers = call_kwargs['headers']
            assert headers["Authorization"] == "Bearer ai_dev_test_token"
            assert headers["X-API-KEY"] == "ai_dev_test_token"