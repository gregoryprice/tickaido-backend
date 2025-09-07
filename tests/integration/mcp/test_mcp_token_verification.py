"""
Unit tests for MCP JWT token verification
"""

import pytest
from datetime import timedelta
from mcp_server.auth.token_verifier import JWTTokenVerifier, AuthenticationError
from app.middleware.auth_middleware import auth_service


def create_test_token(user_id: str, expires_minutes: int = 30, token_type: str = "access") -> str:
    """Create a test JWT token using the auth service"""
    data = {"sub": user_id}
    if expires_minutes > 0:
        expires_delta = timedelta(minutes=expires_minutes)
    else:
        expires_delta = timedelta(minutes=expires_minutes)  # Negative for expired token
    
    return auth_service.create_access_token(data, expires_delta)


@pytest.mark.asyncio
async def test_jwt_token_verifier_valid_token():
    """Valid JWT token returns user context"""
    # Use the same secret key as the auth service for testing
    verifier = JWTTokenVerifier(secret_key="test-secret-key-for-validation")
    
    # Create a valid test token
    user_id = "test-user-123"
    # Note: For this test to work, we need to use the same secret key
    # In practice, this would use the auth_service to create tokens
    from jose import jwt
    from datetime import datetime, timezone, timedelta
    
    payload = {
        "sub": user_id,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
        "iat": datetime.now(timezone.utc)
    }
    token = jwt.encode(payload, "test-secret-key-for-validation", algorithm="HS256")
    
    # Verify the token
    context = verifier.verify_token(token)
    
    assert context.user_id == user_id
    assert context.expires_at > datetime.now(timezone.utc)
    assert "mcp:tools" in context.scopes


@pytest.mark.asyncio  
async def test_jwt_token_verifier_expired_token():
    """Expired token raises AuthenticationError"""
    verifier = JWTTokenVerifier(secret_key="test-secret-key-for-validation")
    
    # Create an expired token
    from jose import jwt
    from datetime import datetime, timezone, timedelta
    
    payload = {
        "sub": "test-user",
        "type": "access", 
        "exp": datetime.now(timezone.utc) - timedelta(minutes=30),  # Expired
        "iat": datetime.now(timezone.utc) - timedelta(minutes=60)
    }
    expired_token = jwt.encode(payload, "test-secret-key-for-validation", algorithm="HS256")
    
    # Should raise AuthenticationError
    with pytest.raises(AuthenticationError, match="Token expired"):
        verifier.verify_token(expired_token)


@pytest.mark.asyncio
async def test_jwt_token_verifier_invalid_type():
    """Invalid token type raises AuthenticationError"""
    verifier = JWTTokenVerifier(secret_key="test-secret-key-for-validation")
    
    # Create a refresh token instead of access token
    from jose import jwt
    from datetime import datetime, timezone, timedelta
    
    payload = {
        "sub": "test-user",
        "type": "refresh",  # Wrong type
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
        "iat": datetime.now(timezone.utc)
    }
    refresh_token = jwt.encode(payload, "test-secret-key-for-validation", algorithm="HS256")
    
    # Should raise AuthenticationError
    with pytest.raises(AuthenticationError, match="Invalid token type"):
        verifier.verify_token(refresh_token)


@pytest.mark.asyncio
async def test_jwt_token_verifier_missing_claims():
    """Token missing required claims raises AuthenticationError"""
    verifier = JWTTokenVerifier(secret_key="test-secret-key-for-validation")
    
    # Create a token missing the "sub" claim
    from jose import jwt
    from datetime import datetime, timezone, timedelta
    
    payload = {
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
        "iat": datetime.now(timezone.utc)
        # Missing "sub" claim
    }
    invalid_token = jwt.encode(payload, "test-secret-key-for-validation", algorithm="HS256")
    
    # Should raise AuthenticationError
    with pytest.raises(AuthenticationError, match="Token missing user ID"):
        verifier.verify_token(invalid_token)


def test_jwt_token_verifier_initialization():
    """Token verifier initializes correctly with secret key"""
    verifier = JWTTokenVerifier(secret_key="test-secret")
    assert verifier.secret_key == "test-secret"
    assert verifier.algorithm == "HS256"


def test_jwt_token_verifier_initialization_from_env():
    """Token verifier initializes from environment variable"""
    import os
    original_key = os.environ.get("JWT_SECRET_KEY")
    
    try:
        os.environ["JWT_SECRET_KEY"] = "env-test-secret"
        verifier = JWTTokenVerifier()
        assert verifier.secret_key == "env-test-secret"
    finally:
        # Restore original environment
        if original_key:
            os.environ["JWT_SECRET_KEY"] = original_key
        else:
            os.environ.pop("JWT_SECRET_KEY", None)