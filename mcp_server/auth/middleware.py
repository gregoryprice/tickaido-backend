"""
Authentication middleware for MCP server
"""

from typing import Any, Callable, Optional, Dict
import logging
from fastmcp.exceptions import ToolError
from .token_verifier import JWTTokenVerifier, AuthenticationError, UserContext


logger = logging.getLogger(__name__)


class TokenAuthMiddleware:
    """Token-based authentication middleware for MCP tools"""
    
    def __init__(self, token_verifier: JWTTokenVerifier):
        self.token_verifier = token_verifier
    
    async def on_call_tool(self, context: Any, call_next: Callable) -> Any:
        """Authenticate requests before calling tools"""
        try:
            # Extract Authorization header
            auth_header = self._get_auth_header(context)
            if not auth_header:
                raise ToolError("Authorization required")
            
            # Verify Bearer token format
            if not auth_header.startswith("Bearer "):
                raise ToolError("Invalid authorization format")
            
            token = auth_header[7:]  # Remove "Bearer " prefix
            
            # Log sanitized token for debugging
            sanitized_token = self._sanitize_token_for_logging(token)
            logger.debug(f"Authenticating token: {sanitized_token}")
            
            # Verify token
            try:
                user_context = self.token_verifier.verify_token(token)
                
                # Add authentication context to request
                context.user_context = user_context
                context.user_token = token
                
                logger.debug(f"Authentication successful for user: {user_context.user_id}")
                
            except AuthenticationError as e:
                logger.warning(f"Authentication failed: {str(e)}")
                raise ToolError("Authentication failed")
            
            # Proceed with authenticated request
            return await call_next(context)
            
        except ToolError:
            raise
        except Exception as e:
            logger.error(f"Authentication middleware error: {str(e)}")
            raise ToolError("Authentication error")
    
    def _get_auth_header(self, context: Any) -> Optional[str]:
        """Extract Authorization header from context"""
        if hasattr(context, 'headers') and context.headers:
            return context.headers.get("Authorization")
        elif hasattr(context, 'request') and hasattr(context.request, 'headers'):
            return context.request.headers.get("Authorization")
        return None
    
    def _sanitize_token_for_logging(self, token: str) -> str:
        """Sanitize token for safe logging"""
        if not token or len(token) < 10:
            return "[INVALID_TOKEN]"
        
        # Show first 8 and last 4 characters
        return f"{token[:8]}...{token[-4:]}"