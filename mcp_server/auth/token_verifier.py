"""
JWT Token verification for MCP server authentication
"""

import os
from datetime import datetime, timezone
from typing import Optional, List
from jose import jwt, JWTError
from pydantic import BaseModel


class AuthenticationError(Exception):
    """Raised when token authentication fails"""
    pass


class UserContext(BaseModel):
    """User context extracted from JWT token"""
    user_id: str
    expires_at: datetime
    scopes: List[str] = ["mcp:tools"]
    
    class Config:
        arbitrary_types_allowed = True


class JWTTokenVerifier:
    """JWT token verifier for MCP authentication"""
    
    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = secret_key or os.getenv("JWT_SECRET_KEY")
        if not self.secret_key:
            raise ValueError("JWT_SECRET_KEY must be provided or set as environment variable")
        self.algorithm = "HS256"
    
    def verify_token(self, token: str) -> UserContext:
        """Verify JWT token and return user context"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Validate required claims
            user_id = payload.get("sub")
            if not user_id:
                raise AuthenticationError("Token missing user ID")
            
            token_type = payload.get("type")
            if token_type != "access":
                raise AuthenticationError("Invalid token type")
            
            # Check expiration
            exp = payload.get("exp")
            if exp:
                exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
                if exp_datetime <= datetime.now(timezone.utc):
                    raise AuthenticationError("Token expired")
            else:
                raise AuthenticationError("Token missing expiration")
            
            return UserContext(
                user_id=user_id,
                expires_at=exp_datetime,
                scopes=["mcp:tools"]
            )
            
        except JWTError as e:
            error_str = str(e)
            if "Signature has expired" in error_str:
                raise AuthenticationError("Token expired")
            else:
                raise AuthenticationError(f"Invalid token: {error_str}")
        except Exception as e:
            raise AuthenticationError(f"Token verification failed: {str(e)}")