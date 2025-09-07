"""
JWT Token Verifier for MCP Server
Validates JWT tokens issued by the core application for MCP tool authentication
"""

import os
import logging
import hashlib
from datetime import datetime, timezone
from dataclasses import dataclass
from jose import JWTError, jwt

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Authentication error for token validation failures"""
    pass


@dataclass(frozen=True)
class MCPUserContext:
    """Immutable user context extracted from JWT token"""
    user_id: str
    organization_id: str = ""  # For organization isolation
    token_hash: str = ""       # For correlation and logging
    expires_at: datetime = None
    scopes: frozenset = None
    
    def __post_init__(self):
        if self.scopes is None:
            object.__setattr__(self, 'scopes', frozenset(["mcp:tools"]))


class JWTTokenVerifier:
    """JWT token verifier for MCP server authentication"""
    
    def __init__(self, secret_key: str = None, algorithm: str = "HS256"):
        """
        Initialize JWT token verifier
        
        Args:
            secret_key: JWT secret key (defaults to JWT_SECRET_KEY env var)
            algorithm: JWT algorithm (defaults to HS256)
        """
        self.secret_key = secret_key or os.getenv("JWT_SECRET_KEY")
        if not self.secret_key:
            raise ValueError("JWT_SECRET_KEY must be provided or set in environment")
            
        self.algorithm = algorithm
        
    def _create_token_hash(self, token: str) -> str:
        """Create SHA-256 hash of token for secure correlation"""
        return hashlib.sha256(token.encode('utf-8')).hexdigest()[:16]  # First 16 chars for logging
    
    def verify_token(self, token: str) -> MCPUserContext:
        """
        Verify JWT token and return user context
        
        Args:
            token: JWT token string to verify
            
        Returns:
            MCPUserContext: User context with validated claims
            
        Raises:
            AuthenticationError: If token is invalid, expired, or malformed
        """
        try:
            # Decode JWT using same algorithm as core app
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token expired")
        except JWTError as e:
            raise AuthenticationError(f"Token validation failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during token verification: {e}")
            raise AuthenticationError("Token validation failed")
        
        # Validate required claims (same validation as core app)
        if payload.get("type") != "access":
            raise AuthenticationError("Invalid token type")
        
        user_id = payload.get("sub")  # Subject (user ID) claim
        if not user_id:
            raise AuthenticationError("Token missing user ID")
        
        exp = payload.get("exp")      # Expiry claim
        if not exp:
            raise AuthenticationError("Token missing expiry")
        
        # Check token expiry (redundant but explicit check)
        expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
        if expires_at <= datetime.now(timezone.utc):
            raise AuthenticationError("Token expired")
        
        # Extract optional organization ID for isolation
        organization_id = payload.get("org_id", "")
        
        # Create secure token hash for logging/correlation
        token_hash = self._create_token_hash(token)
        
        logger.debug(f"Token verified for user {user_id}, expires at {expires_at}")
        
        return MCPUserContext(
            user_id=user_id,
            organization_id=organization_id,
            token_hash=token_hash,
            expires_at=expires_at,
            scopes=frozenset(["mcp:tools"])  # Basic MCP access scope
        )


# Global token verifier instance (will be initialized by MCP server)
_token_verifier: JWTTokenVerifier = None


def get_token_verifier() -> JWTTokenVerifier:
    """Get global token verifier instance"""
    global _token_verifier
    if _token_verifier is None:
        _token_verifier = JWTTokenVerifier()
    return _token_verifier