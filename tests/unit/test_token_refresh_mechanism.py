#!/usr/bin/env python3
"""
Comprehensive tests for token refresh mechanisms.

Tests all token refresh scenarios including:
- Automatic token refresh on expiry
- 401/403 response handling
- Retry logic with exponential backoff
- API token vs JWT token refresh paths
- Failed refresh scenarios
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, AsyncMock
from app.services.token_refresh_service import TokenRefreshService, token_refresh_service
from app.schemas.principal import Principal
from app.middleware.auth_middleware import clerk_auth


class TestTokenRefreshService:
    """Test suite for TokenRefreshService."""
    
    def create_test_principal(self, api_token=None, expires_in_minutes=60, expired=False, refresh_token=None) -> Principal:
        """Create a test principal for refresh testing."""
        if not api_token:
            api_token = "ai_dev_test_token_123"
        
        expires_at = datetime.now(timezone.utc)
        if expired:
            expires_at -= timedelta(hours=1)  # Already expired
        else:
            expires_at += timedelta(minutes=expires_in_minutes)
        
        jwt_payload = {}
        if refresh_token:
            jwt_payload['refresh_token'] = refresh_token
            jwt_payload['raw_token'] = api_token
        
        return Principal(
            user_id="test-user-123",
            organization_id="test-org-456",
            email="test@example.com",
            full_name="Test User",
            api_token=api_token if not refresh_token else None,
            refresh_token=refresh_token,
            jwt_payload=jwt_payload,
            roles=["user"],
            permissions=["ticket.create", "ticket.read"],
            token_issued_at=datetime.now(timezone.utc),
            token_expires_at=expires_at
        )
    
    def test_should_refresh_token_expired(self):
        """Test should_refresh_token for expired tokens."""
        service = TokenRefreshService()
        
        # Expired token should be refreshed
        expired_principal = self.create_test_principal(expired=True)
        assert service.should_refresh_token(expired_principal) is True
    
    def test_should_refresh_token_expiring_soon(self):
        """Test should_refresh_token for tokens expiring soon."""
        service = TokenRefreshService()
        
        # Token expiring in 2 minutes should be refreshed (threshold is 5 minutes)
        expiring_principal = self.create_test_principal(expires_in_minutes=2)
        assert service.should_refresh_token(expiring_principal) is True
    
    def test_should_refresh_token_valid(self):
        """Test should_refresh_token for valid tokens."""
        service = TokenRefreshService()
        
        # Token expiring in 30 minutes should not be refreshed
        valid_principal = self.create_test_principal(expires_in_minutes=30)
        assert service.should_refresh_token(valid_principal) is False
    
    def test_should_refresh_token_api_token(self):
        """Test should_refresh_token for API tokens."""
        service = TokenRefreshService()
        
        # API tokens with long expiry should not be refreshed unless expired
        api_principal = self.create_test_principal(api_token="ai_dev_longterm", expires_in_minutes=1440)
        assert service.should_refresh_token(api_principal) is False
        
        # Expired API token should be refreshed
        expired_api_principal = self.create_test_principal(api_token="ai_dev_expired", expired=True)
        assert service.should_refresh_token(expired_api_principal) is True
    
    @pytest.mark.asyncio
    async def test_refresh_api_token_success(self):
        """Test successful API token refresh."""
        service = TokenRefreshService()
        principal = self.create_test_principal(api_token="ai_dev_test")
        
        with patch.object(clerk_auth, 'validate_token_for_mcp') as mock_validate:
            mock_validate.return_value = "ai_dev_test"  # Token is valid
            
            result = await service._refresh_api_token(principal)
            
            assert result is not None
            assert result.api_token == principal.api_token
            assert result.last_used_at is not None
            assert result.token_expires_at > datetime.now(timezone.utc)
            mock_validate.assert_called_once_with("ai_dev_test")
    
    @pytest.mark.asyncio
    async def test_refresh_api_token_failed(self):
        """Test failed API token refresh."""
        service = TokenRefreshService()
        principal = self.create_test_principal(api_token="ai_dev_invalid")
        
        with patch.object(clerk_auth, 'validate_token_for_mcp') as mock_validate:
            mock_validate.return_value = None  # Token is invalid
            
            result = await service._refresh_api_token(principal)
            
            assert result is None
            mock_validate.assert_called_once_with("ai_dev_invalid")
    
    @pytest.mark.asyncio  
    async def test_refresh_jwt_token_success_with_clerk(self):
        \"\"\"Test successful JWT token refresh using Clerk.\"\"\"
        service = TokenRefreshService()
        principal = self.create_test_principal(
            api_token="jwt_token_123",
            refresh_token="refresh_token_456"
        )
        
        with patch('app.services.clerk_service.clerk_service') as mock_clerk:
            # Mock successful token refresh
            new_token_data = {
                'token': 'new_jwt_token_789',
                'refresh_token': 'new_refresh_token_012', 
                'expires_at': datetime.now(timezone.utc) + timedelta(hours=1)
            }
            mock_clerk.refresh_token.return_value = new_token_data
            
            result = await service._refresh_jwt_token(principal)
            
            assert result is not None
            assert result.jwt_payload['raw_token'] == 'new_jwt_token_789'
            assert result.jwt_payload['refresh_token'] == 'new_refresh_token_012'
            assert result.token_expires_at == new_token_data['expires_at']
            mock_clerk.refresh_token.assert_called_once_with("refresh_token_456")
    
    @pytest.mark.asyncio
    async def test_refresh_jwt_token_fallback_to_auth_middleware(self):
        \"\"\"Test JWT token refresh fallback to auth middleware.\"\"\"
        service = TokenRefreshService()
        principal = self.create_test_principal(
            api_token="jwt_token_123", 
            refresh_token="refresh_token_456"
        )
        
        with patch('app.services.clerk_service.clerk_service') as mock_clerk:
            with patch.object(clerk_auth, 'create_access_token') as mock_create_token:
                # Mock Clerk refresh failure
                mock_clerk.refresh_token.return_value = None
                
                # Mock auth middleware fallback success
                mock_create_token.return_value = "new_fallback_token"
                
                result = await service._refresh_jwt_token(principal)
                
                assert result is not None
                assert result.jwt_payload['raw_token'] == "new_fallback_token"
                assert result.token_expires_at > datetime.now(timezone.utc)
                
                # Verify fallback was called
                mock_create_token.assert_called_once()
                call_args = mock_create_token.call_args[1]
                assert call_args['data']['sub'] == principal.user_id
                assert call_args['data']['email'] == principal.email
    
    @pytest.mark.asyncio
    async def test_refresh_jwt_token_no_refresh_token(self):
        \"\"\"Test JWT token refresh without refresh token.\"\"\"
        service = TokenRefreshService()
        principal = self.create_test_principal(api_token="jwt_token_only")  # No refresh token
        
        result = await service._refresh_jwt_token(principal)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_refresh_principal_token_api_token(self):
        \"\"\"Test refresh_principal_token for API tokens.\"\"\"
        service = TokenRefreshService()
        principal = self.create_test_principal(api_token="ai_dev_test", expired=True)
        
        with patch.object(service, '_refresh_api_token') as mock_refresh_api:
            mock_refresh_api.return_value = principal.model_copy(update={'last_used_at': datetime.now(timezone.utc)})
            
            result = await service.refresh_principal_token(principal)
            
            assert result is not None
            mock_refresh_api.assert_called_once_with(principal)
    
    @pytest.mark.asyncio
    async def test_refresh_principal_token_jwt_token(self):
        \"\"\"Test refresh_principal_token for JWT tokens.\"\"\"
        service = TokenRefreshService()
        principal = self.create_test_principal(
            api_token=None,
            refresh_token="refresh_123",
            expired=True
        )
        
        with patch.object(service, '_refresh_jwt_token') as mock_refresh_jwt:
            mock_refresh_jwt.return_value = principal.model_copy(update={'last_used_at': datetime.now(timezone.utc)})
            
            result = await service.refresh_principal_token(principal)
            
            assert result is not None
            mock_refresh_jwt.assert_called_once_with(principal)
    
    @pytest.mark.asyncio
    async def test_refresh_principal_token_no_refresh_needed(self):
        \"\"\"Test refresh_principal_token when no refresh is needed.\"\"\"
        service = TokenRefreshService()
        principal = self.create_test_principal(expires_in_minutes=30)  # Valid for 30 minutes
        
        with patch.object(service, 'should_refresh_token') as mock_should_refresh:
            mock_should_refresh.return_value = False
            
            result = await service.refresh_principal_token(principal)
            
            assert result == principal  # Same principal returned
            mock_should_refresh.assert_called_once_with(principal)
    
    @pytest.mark.asyncio
    async def test_handle_mcp_auth_failure_401(self):
        \"\"\"Test handling 401 authentication failure.\"\"\"
        service = TokenRefreshService()
        principal = self.create_test_principal(expired=True)
        
        with patch.object(service, 'refresh_principal_token') as mock_refresh:
            refreshed_principal = self.create_test_principal(api_token="new_token")
            mock_refresh.return_value = refreshed_principal
            
            result = await service.handle_mcp_auth_failure(principal, 401)
            
            assert result is not None
            assert result == refreshed_principal
            mock_refresh.assert_called()
    
    @pytest.mark.asyncio
    async def test_handle_mcp_auth_failure_403(self):
        \"\"\"Test handling 403 forbidden failure.\"\"\"
        service = TokenRefreshService()
        principal = self.create_test_principal(expired=True)
        
        with patch.object(service, 'refresh_principal_token') as mock_refresh:
            refreshed_principal = self.create_test_principal(api_token="new_token")
            mock_refresh.return_value = refreshed_principal
            
            result = await service.handle_mcp_auth_failure(principal, 403)
            
            assert result is not None
            assert result == refreshed_principal
    
    @pytest.mark.asyncio
    async def test_handle_mcp_auth_failure_other_error_codes(self):
        \"\"\"Test handling non-auth error codes.\"\"\"
        service = TokenRefreshService()
        principal = self.create_test_principal()
        
        # 500 error should not trigger refresh
        result = await service.handle_mcp_auth_failure(principal, 500)
        assert result is None
        
        # 404 error should not trigger refresh
        result = await service.handle_mcp_auth_failure(principal, 404)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_handle_mcp_auth_failure_with_retries(self):
        \"\"\"Test auth failure handling with retry logic.\"\"\"
        service = TokenRefreshService()
        service.max_retries = 2
        service.base_delay = 0.01  # Fast retries for testing
        
        principal = self.create_test_principal(expired=True)
        
        with patch.object(service, 'refresh_principal_token') as mock_refresh:
            # First call fails, second succeeds
            mock_refresh.side_effect = [
                None,  # First attempt fails
                self.create_test_principal(api_token="success_token")  # Second succeeds
            ]
            
            result = await service.handle_mcp_auth_failure(principal, 401)
            
            assert result is not None
            assert result.api_token == "success_token"
            assert mock_refresh.call_count == 2
    
    @pytest.mark.asyncio
    async def test_handle_mcp_auth_failure_all_retries_fail(self):
        \"\"\"Test auth failure handling when all retries fail.\"\"\"
        service = TokenRefreshService()
        service.max_retries = 2
        service.base_delay = 0.01  # Fast retries for testing
        
        principal = self.create_test_principal(expired=True)
        
        with patch.object(service, 'refresh_principal_token') as mock_refresh:
            mock_refresh.return_value = None  # All attempts fail
            
            result = await service.handle_mcp_auth_failure(principal, 401)
            
            assert result is None
            assert mock_refresh.call_count == 2
    
    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        \"\"\"Test exponential backoff in retry logic.\"\"\"
        service = TokenRefreshService()
        service.max_retries = 3
        service.base_delay = 0.1  # 100ms base delay
        service.max_delay = 0.5   # 500ms max delay
        
        principal = self.create_test_principal(expired=True)
        
        with patch.object(service, 'refresh_principal_token') as mock_refresh:
            with patch('asyncio.sleep') as mock_sleep:
                mock_refresh.return_value = None  # All attempts fail
                
                await service.handle_mcp_auth_failure(principal, 401)
                
                # Verify exponential backoff: 0.1s, 0.2s (no third sleep since no more retries)
                assert mock_sleep.call_count == 2
                sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
                assert sleep_calls[0] == 0.1  # First retry delay
                assert sleep_calls[1] == 0.2  # Second retry delay (doubled)


class TestPrincipalRefreshIntegration:
    \"\"\"Test Principal refresh integration methods.\"\"\"
    
    def create_test_principal(self, expires_in_minutes=60, expired=False) -> Principal:
        \"\"\"Create a test principal.\"\"\"
        expires_at = datetime.now(timezone.utc)
        if expired:
            expires_at -= timedelta(hours=1)
        else:
            expires_at += timedelta(minutes=expires_in_minutes)
        
        return Principal(
            user_id="test-user",
            organization_id="test-org",
            email="test@example.com",
            api_token="ai_dev_test_token",
            token_expires_at=expires_at
        )
    
    @pytest.mark.asyncio
    async def test_principal_refresh_if_needed_refresh_required(self):
        \"\"\"Test Principal.refresh_if_needed when refresh is required.\"\"\"
        principal = self.create_test_principal(expired=True)
        
        with patch('app.services.token_refresh_service.token_refresh_service') as mock_service:
            refreshed_principal = self.create_test_principal()
            mock_service.should_refresh_token.return_value = True
            mock_service.refresh_principal_token.return_value = refreshed_principal
            
            result = await principal.refresh_if_needed()
            
            assert result == refreshed_principal
            mock_service.should_refresh_token.assert_called_once_with(principal)
            mock_service.refresh_principal_token.assert_called_once_with(principal)
    
    @pytest.mark.asyncio
    async def test_principal_refresh_if_needed_no_refresh_needed(self):
        \"\"\"Test Principal.refresh_if_needed when no refresh is needed.\"\"\"
        principal = self.create_test_principal(expires_in_minutes=30)
        
        with patch('app.services.token_refresh_service.token_refresh_service') as mock_service:
            mock_service.should_refresh_token.return_value = False
            
            result = await principal.refresh_if_needed()
            
            assert result == principal
            mock_service.should_refresh_token.assert_called_once_with(principal)
            mock_service.refresh_principal_token.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_principal_refresh_if_needed_refresh_fails(self):
        \"\"\"Test Principal.refresh_if_needed when refresh fails gracefully.\"\"\"
        principal = self.create_test_principal(expired=True)
        
        with patch('app.services.token_refresh_service.token_refresh_service') as mock_service:
            mock_service.should_refresh_token.return_value = True
            mock_service.refresh_principal_token.return_value = None  # Refresh fails
            
            result = await principal.refresh_if_needed()
            
            assert result == principal  # Returns self when refresh fails
    
    def test_principal_refresh_callback_support(self):
        \"\"\"Test Principal refresh callback functionality.\"\"\"
        principal = self.create_test_principal()
        
        # Add callback
        def mock_callback(old_principal, new_principal):
            pass
        
        principal_with_callback = principal.with_refresh_callback(mock_callback)
        
        # Verify callback is stored
        callback = principal_with_callback.get_refresh_callback()
        assert callback == mock_callback
    
    def test_principal_get_auth_token_priority(self):
        \"\"\"Test Principal.get_auth_token priority order.\"\"\"
        # API token should take priority
        principal_with_api = Principal(
            user_id="test-user",
            organization_id="test-org",
            email="test@example.com",
            api_token="api_token_123",
            jwt_payload={"raw_token": "jwt_token_456"},
            refresh_token="refresh_token_789"
        )
        
        assert principal_with_api.get_auth_token() == "api_token_123"
        
        # JWT token should be second priority
        principal_with_jwt = Principal(
            user_id="test-user",
            organization_id="test-org",
            email="test@example.com",
            jwt_payload={"raw_token": "jwt_token_456"},
            refresh_token="refresh_token_789"
        )
        
        assert principal_with_jwt.get_auth_token() == "jwt_token_456"
        
        # Refresh token should be last resort
        principal_with_refresh = Principal(
            user_id="test-user",
            organization_id="test-org",
            email="test@example.com",
            refresh_token="refresh_token_789"
        )
        
        assert principal_with_refresh.get_auth_token() == "refresh_token_789"


@pytest.mark.integration
class TestTokenRefreshIntegration:
    \"\"\"Integration tests for token refresh functionality.\"\"\"
    
    @pytest.mark.asyncio
    async def test_full_token_refresh_flow(self):
        \"\"\"Test complete token refresh flow integration.\"\"\"
        # This test would require actual auth services to be running
        # For now, test the flow with mocks
        
        expired_principal = Principal(
            user_id="test-user",
            organization_id="test-org", 
            email="test@example.com",
            api_token="ai_dev_expired_token",
            token_expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        
        with patch('app.services.token_refresh_service.clerk_auth') as mock_auth:
            mock_auth.validate_token_for_mcp.return_value = "ai_dev_refreshed_token"
            
            # Test refresh through global service
            result = await token_refresh_service.refresh_principal_token(expired_principal)
            
            assert result is not None
            assert result.api_token == expired_principal.api_token  # API token doesn't change, just gets validated
            assert result.token_expires_at > datetime.now(timezone.utc)
            assert result.last_used_at is not None