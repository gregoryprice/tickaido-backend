"""
FastMCP Authentication Middleware for JWT Token Verification
Validates JWT tokens for MCP tool calls and provides user context
"""

import logging
from typing import Optional
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.exceptions import ToolError

from .token_verifier import JWTTokenVerifier, AuthenticationError

logger = logging.getLogger(__name__)


class TokenAuthMiddleware(Middleware):
    """FastMCP middleware for JWT token authentication"""
    
    def __init__(self, token_verifier: JWTTokenVerifier = None):
        """
        Initialize token authentication middleware
        
        Args:
            token_verifier: JWT token verifier instance
        """
        self.token_verifier = token_verifier or JWTTokenVerifier()
    
    def _extract_auth_header(self, context: MiddlewareContext) -> Optional[str]:
        """
        Extract Authorization header from middleware context
        
        Args:
            context: FastMCP middleware context
            
        Returns:
            Authorization header value or None
        """
        try:
            # Extract authorization header from FastMCP context
            # This accesses the HTTP request through the context
            if hasattr(context, 'request') and context.request:
                headers = getattr(context.request, 'headers', {})
                return headers.get('authorization') or headers.get('Authorization')
            
            # Fallback: try to get from context attributes
            if hasattr(context, 'headers'):
                return context.headers.get('authorization') or context.headers.get('Authorization')
                
            return None
            
        except Exception as e:
            logger.debug(f"Could not extract authorization header: {e}")
            return None
    
    def _sanitize_token_for_logging(self, token: str) -> str:
        """
        Sanitize token for safe logging (show first 8 and last 4 characters)
        
        Args:
            token: JWT token string
            
        Returns:
            Sanitized token string for logging
        """
        if not token or len(token) < 12:
            return "[INVALID_TOKEN]"
        return f"{token[:8]}...{token[-4:]}"
    
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        """
        Authenticate tool calls with JWT token verification
        
        Args:
            context: FastMCP middleware context
            call_next: Next middleware function
            
        Returns:
            Result from next middleware/tool call
            
        Raises:
            ToolError: If authentication fails
        """
        try:
            # Extract Authorization header
            auth_header = self._extract_auth_header(context)
            
            if not auth_header:
                logger.warning("MCP tool call missing Authorization header")
                raise ToolError("Authorization required: Bearer token missing")
            
            if not auth_header.startswith("Bearer "):
                logger.warning(f"Invalid authorization header format: {auth_header[:20]}...")
                raise ToolError("Authorization required: Invalid Bearer token format")
            
            # Extract token (remove "Bearer " prefix)
            token = auth_header[7:]
            token_sanitized = self._sanitize_token_for_logging(token)
            
            logger.debug(f"Verifying JWT token: {token_sanitized}")
            
            # Verify token using JWT token verifier
            try:
                user_context = self.token_verifier.verify_token(token)
                logger.info(f"MCP tool authenticated for user {user_context.user_id} "
                           f"(token: {user_context.token_hash})")
                
            except AuthenticationError as e:
                logger.warning(f"MCP authentication failed: {e}")
                raise ToolError(f"Authentication failed: {str(e)}")
            
            # Store user context and original token in middleware context
            # This allows tools to access user information and make authenticated backend calls
            context.user_context = user_context
            context.user_token = token  # Original token for backend API authentication
            
            logger.debug(f"MCP user context set for user {user_context.user_id}")
            
            # Continue to next middleware/tool
            return await call_next(context)
            
        except ToolError:
            # Re-raise ToolError as-is (proper MCP protocol error)
            raise
        except Exception as e:
            logger.error(f"Unexpected error in MCP authentication middleware: {e}")
            raise ToolError("Authentication system error")


def create_token_auth_middleware(secret_key: str = None) -> TokenAuthMiddleware:
    """
    Create token authentication middleware with specified secret key
    
    Args:
        secret_key: JWT secret key (defaults to environment variable)
        
    Returns:
        Configured TokenAuthMiddleware instance
    """
    token_verifier = JWTTokenVerifier(secret_key=secret_key)
    return TokenAuthMiddleware(token_verifier)