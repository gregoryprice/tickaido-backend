"""
Integration tests for MCP authentication flow
"""

import pytest
from unittest.mock import Mock
from fastmcp.exceptions import ToolError
from mcp_server.auth.middleware import TokenAuthMiddleware
from mcp_server.auth.token_verifier import JWTTokenVerifier


class MockMiddlewareContext:
    """Mock middleware context for testing"""
    
    def __init__(self, headers: dict = None):
        self.headers = headers or {}
        self.request = Mock()
        self.request.headers = headers or {}
        self.user_context = None
        self.user_token = None


@pytest.mark.asyncio
async def test_token_auth_middleware_valid_token():
    """Token auth middleware works with valid JWT token"""
    
    # Create test token
    from jose import jwt
    from datetime import datetime, timezone, timedelta
    
    secret_key = "test-secret-key-middleware"
    payload = {
        "sub": "test-user-123",
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
        "iat": datetime.now(timezone.utc)
    }
    token = jwt.encode(payload, secret_key, algorithm="HS256")
    
    # Create middleware with test secret
    verifier = JWTTokenVerifier(secret_key=secret_key)
    middleware = TokenAuthMiddleware(token_verifier=verifier)
    
    # Create mock context with valid Authorization header
    context = MockMiddlewareContext(headers={"Authorization": f"Bearer {token}"})
    
    # Mock call_next function
    async def mock_call_next(ctx):
        return "tool_result"
    
    # Test middleware authentication
    result = await middleware.on_call_tool(context, mock_call_next)
    
    # Verify authentication succeeded
    assert result == "tool_result"
    assert context.user_context is not None
    assert context.user_context.user_id == "test-user-123"
    assert context.user_token == token


@pytest.mark.asyncio
async def test_token_auth_middleware_missing_auth():
    """Missing Authorization header raises ToolError"""
    
    verifier = JWTTokenVerifier(secret_key="test-secret")
    middleware = TokenAuthMiddleware(token_verifier=verifier)
    
    # Create context without Authorization header
    context = MockMiddlewareContext()
    
    async def mock_call_next(ctx):
        return "tool_result"
    
    # Should raise ToolError for missing auth
    with pytest.raises(ToolError, match="Authorization required"):
        await middleware.on_call_tool(context, mock_call_next)


@pytest.mark.asyncio
async def test_token_auth_middleware_invalid_token():
    """Invalid JWT token raises ToolError"""
    
    verifier = JWTTokenVerifier(secret_key="test-secret")
    middleware = TokenAuthMiddleware(token_verifier=verifier)
    
    # Create context with invalid token
    context = MockMiddlewareContext(headers={"Authorization": "Bearer invalid-token"})
    
    async def mock_call_next(ctx):
        return "tool_result"
    
    # Should raise ToolError for invalid token
    with pytest.raises(ToolError, match="Authentication failed"):
        await middleware.on_call_tool(context, mock_call_next)


@pytest.mark.asyncio
async def test_token_auth_middleware_expired_token():
    """Expired JWT token raises ToolError"""
    
    secret_key = "test-secret-expired"
    
    # Create expired token
    from jose import jwt
    from datetime import datetime, timezone, timedelta
    
    payload = {
        "sub": "test-user",
        "type": "access",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=30),  # Expired
        "iat": datetime.now(timezone.utc) - timedelta(minutes=60)
    }
    expired_token = jwt.encode(payload, secret_key, algorithm="HS256")
    
    verifier = JWTTokenVerifier(secret_key=secret_key)
    middleware = TokenAuthMiddleware(token_verifier=verifier)
    
    # Create context with expired token
    context = MockMiddlewareContext(headers={"Authorization": f"Bearer {expired_token}"})
    
    async def mock_call_next(ctx):
        return "tool_result"
    
    # Should raise ToolError for expired token
    with pytest.raises(ToolError, match="Authentication failed"):
        await middleware.on_call_tool(context, mock_call_next)


def test_middleware_token_sanitization():
    """Test token sanitization for logging"""
    verifier = JWTTokenVerifier(secret_key="test-secret")
    middleware = TokenAuthMiddleware(token_verifier=verifier)
    
    # Test valid token sanitization
    long_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxNjg5OTQ4NDAwfQ.signature"
    sanitized = middleware._sanitize_token_for_logging(long_token)
    assert sanitized == "eyJ0eXAi...ture"
    
    # Test short/invalid token
    short_token = "abc123"
    sanitized = middleware._sanitize_token_for_logging(short_token)
    assert sanitized == "[INVALID_TOKEN]"
    
    # Test empty token
    empty_sanitized = middleware._sanitize_token_for_logging("")
    assert empty_sanitized == "[INVALID_TOKEN]"