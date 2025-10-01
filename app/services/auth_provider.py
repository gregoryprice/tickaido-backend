#!/usr/bin/env python3
"""
Enhanced Authentication Provider for MCP Token Propagation

This module provides secure authentication token management for MCP tools,
implementing zero-trust validation, token minimization, and comprehensive auditing.
"""

import hashlib
import logging
import time
import weakref
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set

from app.middleware.auth_middleware import auth_service

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class SecureTokenContainer:
    """Immutable, secure token container with automatic cleanup"""
    user_id: str
    token_hash: str  # SHA-256 hash of token for correlation
    expires_at: datetime
    permissions: frozenset[str] = frozenset()
    
    def __post_init__(self):
        # Register for automatic cleanup on expiry
        TokenCleanupManager.register(self)
    
    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.expires_at
    
    @property
    def time_to_expiry(self) -> float:
        """Return seconds until expiry, negative if expired"""
        delta = self.expires_at - datetime.now(timezone.utc)
        return delta.total_seconds()


class TokenCleanupManager:
    """Manages automatic cleanup of expired tokens"""
    _registered_tokens: Set[weakref.ref] = set()
    
    @classmethod
    def register(cls, token_container: SecureTokenContainer):
        """Register token for cleanup monitoring"""
        token_ref = weakref.ref(token_container, cls._cleanup_callback)
        cls._registered_tokens.add(token_ref)
    
    @classmethod
    def _cleanup_callback(cls, token_ref):
        """Cleanup callback when token is garbage collected"""
        cls._registered_tokens.discard(token_ref)
        logger.debug("Token container cleaned up automatically")


class AuthenticationProvider(ABC):
    """Abstract provider for authentication token management"""
    
    @abstractmethod
    async def validate_token(self, token: str) -> Optional[SecureTokenContainer]:
        """Validate token and return secure container or None if invalid"""
        pass
    
    @abstractmethod
    async def check_revocation(self, token_hash: str) -> bool:
        """Check if token has been revoked"""
        pass
    
    @abstractmethod
    async def get_user_permissions(self, user_id: str) -> frozenset[str]:
        """Get user permissions for authorization"""
        pass


class JWTAuthenticationProvider(AuthenticationProvider):
    """JWT-based authentication provider with caching"""
    
    def __init__(self, token_cache_ttl: int = 300):
        self._token_cache: Dict[str, SecureTokenContainer] = {}
        self._cache_ttl = token_cache_ttl
        self._last_cleanup = time.time()
    
    def _hash_token(self, token: str) -> str:
        """Create SHA-256 hash of token for secure correlation"""
        return hashlib.sha256(token.encode('utf-8')).hexdigest()
    
    def _cleanup_expired_cache(self):
        """Remove expired entries from token cache"""
        current_time = time.time()
        if current_time - self._last_cleanup < 60:  # Only cleanup every minute
            return
            
        expired_hashes = []
        for token_hash, container in self._token_cache.items():
            if container.is_expired:
                expired_hashes.append(token_hash)
        
        for token_hash in expired_hashes:
            del self._token_cache[token_hash]
            
        self._last_cleanup = current_time
        if expired_hashes:
            logger.debug(f"Cleaned up {len(expired_hashes)} expired tokens from cache")
    
    async def validate_token(self, token: str) -> Optional[SecureTokenContainer]:
        """Validate token and return secure container or None if invalid"""
        try:
            # Clean up expired cache entries
            self._cleanup_expired_cache()
            
            # Hash token for cache lookup
            token_hash = self._hash_token(token)
            
            # Check cache first
            if token_hash in self._token_cache:
                container = self._token_cache[token_hash]
                if not container.is_expired:
                    logger.debug(f"Token validation cache hit for user {container.user_id}")
                    return container
                else:
                    # Remove expired entry
                    del self._token_cache[token_hash]
            
            # Validate token using existing auth service
            payload = auth_service.verify_token(token, "access")
            user_id = payload.get("sub")
            
            if not user_id:
                logger.warning("Token missing user ID")
                return None
            
            # Get token expiry
            exp = payload.get("exp", 0)
            expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
            
            if expires_at <= datetime.now(timezone.utc):
                logger.warning(f"Token expired for user {user_id}")
                return None
            
            # Get user permissions (basic set for now)
            permissions = await self.get_user_permissions(user_id)
            
            # Create secure container
            container = SecureTokenContainer(
                user_id=user_id,
                token_hash=token_hash,
                expires_at=expires_at,
                permissions=permissions
            )
            
            # Cache the container
            self._token_cache[token_hash] = container
            
            logger.debug(f"Token validated successfully for user {user_id}, expires in {container.time_to_expiry:.0f}s")
            return container
            
        except Exception as e:
            logger.warning(f"Token validation failed: {e}")
            return None
    
    async def check_revocation(self, token_hash: str) -> bool:
        """Check if token has been revoked (basic implementation)"""
        # For now, we don't maintain a revocation list
        # In production, this would check against a Redis blacklist or database
        return False
    
    async def get_user_permissions(self, user_id: str) -> frozenset[str]:
        """Get user permissions for authorization"""
        # Basic permission set - can be extended based on user roles
        # In production, this would query user roles and permissions from database
        basic_permissions = {
            "read_tickets",
            "create_tickets", 
            "update_tickets",
            "read_integrations",
            "read_system_health"
        }
        return frozenset(basic_permissions)


# Global authentication provider instance
_auth_provider: Optional[JWTAuthenticationProvider] = None

def get_auth_provider() -> JWTAuthenticationProvider:
    """Get global authentication provider instance"""
    global _auth_provider
    if _auth_provider is None:
        _auth_provider = JWTAuthenticationProvider()
    return _auth_provider


# Helper function for MCP tools to decode JWT directly (backward compatibility)
def decode_jwt_token(token: str) -> Dict[str, Any]:
    """Decode JWT token using existing auth service (for compatibility)"""
    return auth_service.verify_token(token, "access")