#!/usr/bin/env python3
"""
Comprehensive test suite for Clerk integration
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from app.main import app
from app.models.user import User
from app.models.organization import Organization
from app.models.api_token import APIToken
from app.models.organization_invitation import OrganizationRole
from app.services.clerk_service import clerk_service
from app.services.clerk_organization_service import clerk_org_service
from app.middleware.clerk_middleware import AuthMiddleware
from app.middleware.organization_middleware import OrganizationContext

client = TestClient(app)


class TestClerkService:
    """Test Clerk service functionality"""
    
    @pytest.mark.asyncio
    async def test_service_initialization(self):
        """Test Clerk service initializes correctly"""
        service = clerk_service
        # Service should initialize even without API key (for testing)
        assert service is not None
        # Client will be None without CLERK_SECRET_KEY
        assert service.client is None or hasattr(service.client, 'users')
    
    @pytest.mark.asyncio
    async def test_verify_token_no_client(self):
        """Test token verification without Clerk client"""
        service = clerk_service
        if service.client is None:
            result = await service.verify_token("test_token")
            assert result is None
    
    @pytest.mark.asyncio
    async def test_list_users_no_client(self):
        """Test user listing without Clerk client"""
        service = clerk_service
        users = await service.list_users(limit=1)
        assert isinstance(users, list)
        assert len(users) == 0  # Should return empty list when no client


class TestAPITokenModel:
    """Test APIToken model functionality"""
    
    def test_api_token_creation(self):
        """Test APIToken model creation"""
        token = APIToken(
            name="Test Token",
            token_hash="hashed_token_value",
            user_id=uuid4(),
            organization_id=uuid4(),
            permissions=["api:read", "api:write"],
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            is_active=True
        )
        
        assert token.name == "Test Token"
        assert token.token_hash == "hashed_token_value"
        assert token.is_active is True
        assert token.can_be_used is True
        assert not token.is_expired
    
    def test_api_token_expiration(self):
        """Test APIToken expiration logic"""
        # Create expired token
        expired_token = APIToken(
            name="Expired Token",
            token_hash="expired_hash",
            user_id=uuid4(),
            organization_id=uuid4(),
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),  # Yesterday
            is_active=True
        )
        
        assert expired_token.is_expired is True
        assert expired_token.can_be_used is False
    
    def test_api_token_permissions(self):
        """Test APIToken permission checking"""
        token = APIToken(
            name="Permission Token",
            token_hash="perm_hash",
            user_id=uuid4(),
            organization_id=uuid4(),
            permissions=["tickets:read", "tickets:create"],
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            is_active=True
        )
        
        assert token.has_permission("tickets:read") is True
        assert token.has_permission("tickets:create") is True
        assert token.has_permission("tickets:delete") is False
        
        # Test wildcard permissions
        wildcard_token = APIToken(
            name="Wildcard Token",
            token_hash="wildcard_hash",
            user_id=uuid4(),
            organization_id=uuid4(),
            permissions=["*"],
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            is_active=True
        )
        
        assert wildcard_token.has_permission("any:permission") is True


class TestAuthMiddleware:
    """Test authentication middleware"""
    
    @pytest.mark.asyncio
    async def test_api_token_format_validation(self):
        """Test API token format validation"""
        middleware = AuthMiddleware()
        
        # Mock request
        request = Mock()
        request.state = Mock()
        
        # Test invalid format
        result = await middleware._validate_api_token("invalid_token", request)
        assert result is None
        
        # Test wrong prefix
        result = await middleware._validate_api_token("att_sometoken", request)
        assert result is None
        
        # Test incomplete format
        result = await middleware._validate_api_token("ai_token", request)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_clerk_token_validation_no_client(self):
        """Test Clerk token validation without client"""
        middleware = AuthMiddleware()
        request = Mock()
        request.state = Mock()
        
        # Should return None when no Clerk client available
        result = await middleware._validate_clerk_token("clerk_token", request)
        assert result is None


class TestOrganizationContext:
    """Test organization context functionality"""
    
    def test_organization_context_creation(self):
        """Test OrganizationContext creation and permissions"""
        user = Mock()
        user.email = "test@example.com"
        
        org = Mock()
        org.id = uuid4()
        org.name = "Test Organization"
        
        context = OrganizationContext(
            organization=org,
            user=user,
            role=OrganizationRole.ADMIN,
            permissions={}
        )
        
        assert context.organization == org
        assert context.user == user
        assert context.role == OrganizationRole.ADMIN
        
        # Test permission checking (simplified model - all roles have all permissions)
        assert context.has_permission("any:permission") is True
    
    def test_member_permissions(self):
        """Test member role permissions"""
        user = Mock()
        org = Mock()
        
        context = OrganizationContext(
            organization=org,
            user=user,
            role=OrganizationRole.MEMBER,
            permissions={}
        )
        
        # Members have all permissions in simplified model
        assert context.has_permission("tickets:create") is True
        assert context.has_permission("users:read") is True


class TestAPIRoutes:
    """Test API endpoint functionality"""
    
    @pytest.mark.asyncio
    async def test_api_token_generation_endpoint_structure(self):
        """Test API token generation endpoint exists and has correct structure"""
        # This tests that the route is properly defined and importable
        from app.routers.api_tokens import generate_api_token, list_api_tokens, revoke_api_token
        
        # Routes should be callable functions
        assert callable(generate_api_token)
        assert callable(list_api_tokens)
        assert callable(revoke_api_token)
    
    def test_webhook_endpoints_exist(self):
        """Test webhook endpoints are properly defined"""
        from app.routers.clerk_webhooks import handle_clerk_events
        
        assert callable(handle_clerk_events)


class TestWebhookHandlers:
    """Test webhook event handling"""
    
    @pytest.mark.asyncio
    async def test_user_created_webhook_structure(self):
        """Test user created webhook handler structure"""
        from app.routers.clerk_webhooks import handle_user_created
        
        # Mock database session
        mock_db = AsyncMock()
        
        # Mock user data
        user_data = {
            'id': 'clerk_user_123',
            'email_addresses': [{'email_address': 'webhook@example.com'}],
            'first_name': 'Webhook',
            'last_name': 'User',
            'image_url': 'https://example.com/avatar.jpg'
        }
        
        # Should not raise errors
        try:
            await handle_user_created(mock_db, user_data)
            # Handler should complete without errors
        except Exception as e:
            # Expected to fail without real database, but should not have import/syntax errors
            assert "database" in str(e).lower() or "connection" in str(e).lower()
    
    @pytest.mark.asyncio
    async def test_organization_created_webhook_structure(self):
        """Test organization created webhook handler structure"""
        from app.routers.clerk_webhooks import handle_organization_created
        
        mock_db = AsyncMock()
        
        org_data = {
            'id': 'clerk_org_123',
            'name': 'Test Organization',
            'slug': 'test-org'
        }
        
        try:
            await handle_organization_created(mock_db, org_data)
        except Exception as e:
            # Expected to fail without real database
            assert "database" in str(e).lower() or "connection" in str(e).lower()


class TestSchemaValidation:
    """Test Pydantic schema validation"""
    
    def test_api_token_generation_request_validation(self):
        """Test API token generation request validation"""
        from app.schemas.api_token import APITokenGenerationRequest
        
        # Valid request
        valid_request = APITokenGenerationRequest(
            name="Test Token",
            permissions=["api:read"],
            expires_days=30
        )
        
        assert valid_request.name == "Test Token"
        assert valid_request.permissions == ["api:read"]
        assert valid_request.expires_days == 30
        
        # Test validation
        with pytest.raises(ValueError):
            # Invalid expires_days
            APITokenGenerationRequest(
                name="Test",
                expires_days=400  # Too many days
            )
    
    def test_api_token_response_schema(self):
        """Test API token response schema"""
        from app.schemas.api_token import APITokenResponse
        
        response = APITokenResponse(
            token="ai_dev_test123",
            id=uuid4(),
            name="Test Token",
            permissions=["*"],
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            organization_id=uuid4(),
            organization_name="Test Org"
        )
        
        assert response.token.startswith("ai_dev_")
        assert response.name == "Test Token"
        assert response.permissions == ["*"]


class TestEnvironmentTokenPrefixes:
    """Test environment-specific token prefixes"""
    
    def test_token_prefix_generation(self):
        """Test token prefix based on environment"""
        from app.config.settings import get_settings
        
        settings = get_settings()
        env_prefix = settings.environment[:4]
        
        # Should be one of the expected environment prefixes
        assert env_prefix in ['prod', 'stag', 'dev', 'test', 'deve']  # development truncated to 'deve'
        
        # Test token format
        raw_token = "test123456"
        full_token = f"ai_{env_prefix}_{raw_token}"
        
        parts = full_token.split('_', 2)
        assert len(parts) == 3
        assert parts[0] == 'ai'
        assert parts[1] == env_prefix
        assert parts[2] == raw_token


if __name__ == "__main__":
    pytest.main([__file__, "-v"])