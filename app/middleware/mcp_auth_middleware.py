#!/usr/bin/env python3
"""
Middleware for MCP authentication validation

This module provides validation specifically for MCP tool execution,
ensuring tokens are suitable for tool-based operations with enhanced security.
"""

import logging
from typing import Optional
from datetime import datetime, timezone
from app.services.auth_provider import decode_jwt_token

logger = logging.getLogger(__name__)


class MCPAuthValidator:
    """Validates authentication for MCP tool execution"""
    
    @staticmethod
    def validate_token_for_mcp(token: str) -> bool:
        """Validate JWT token is suitable for MCP tool usage"""
        try:
            payload = decode_jwt_token(token)
            
            # Check expiry
            exp = payload.get("exp", 0)
            if datetime.fromtimestamp(exp, tz=timezone.utc) <= datetime.now(timezone.utc):
                logger.warning("Token expired for MCP usage")
                return False
            
            # Check required claims
            if not payload.get("sub"):  # user_id
                logger.warning("Token missing user ID for MCP usage")
                return False
            
            # Check token type
            token_type = payload.get("type", "")
            if token_type != "access":
                logger.warning(f"Invalid token type for MCP usage: {token_type}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Token validation failed for MCP: {e}")
            return False
    
    @staticmethod
    def sanitize_token_for_logging(token: str) -> str:
        """Sanitize token for safe logging"""
        if not token:
            return "[NO_TOKEN]"
        if len(token) < 10:
            return "[INVALID_TOKEN]"
        return f"{token[:8]}...{token[-4:]}"
    
    @staticmethod
    def extract_user_id_from_token(token: str) -> Optional[str]:
        """Extract user ID from token for MCP context"""
        try:
            payload = decode_jwt_token(token)
            return payload.get("sub")
        except Exception as e:
            logger.error(f"Failed to extract user ID from token: {e}")
            return None
    
    @staticmethod
    def get_token_expiry(token: str) -> Optional[datetime]:
        """Get token expiry time for validation"""
        try:
            payload = decode_jwt_token(token)
            exp = payload.get("exp", 0)
            return datetime.fromtimestamp(exp, tz=timezone.utc)
        except Exception as e:
            logger.error(f"Failed to get token expiry: {e}")
            return None
    
    @classmethod
    def validate_token_for_user(cls, token: str, expected_user_id: str) -> bool:
        """Validate token belongs to expected user"""
        try:
            actual_user_id = cls.extract_user_id_from_token(token)
            if actual_user_id != expected_user_id:
                logger.warning(f"Token user mismatch: expected {expected_user_id}, got {actual_user_id}")
                return False
            return cls.validate_token_for_mcp(token)
        except Exception as e:
            logger.error(f"Token-user validation failed: {e}")
            return False


# Global validator instance
mcp_auth_validator = MCPAuthValidator()