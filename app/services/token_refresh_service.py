#!/usr/bin/env python3
"""
Token Refresh Service for handling MCP authentication failures and token refreshing.

This service provides centralized token refresh logic for MCP authentication
with retry mechanisms and error handling.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from app.schemas.principal import Principal
from app.middleware.auth_middleware import clerk_auth
from app.services.clerk_service import clerk_service

logger = logging.getLogger(__name__)


class TokenRefreshService:
    """
    Service for handling token refresh operations for MCP authentication.
    
    Provides automatic refresh on authentication failures with retry logic
    and exponential backoff for resilient authentication.
    """
    
    def __init__(self):
        """Initialize the token refresh service."""
        self.max_retries = 2
        self.base_delay = 1.0  # seconds
        self.max_delay = 10.0  # seconds
        
    async def refresh_principal_token(self, principal: Principal) -> Optional[Principal]:
        """
        Refresh token for principal if expired or expiring soon.
        
        Args:
            principal: Principal object with potentially expired token
            
        Returns:
            Principal: Updated principal with refreshed token or None if refresh failed
        """
        try:
            logger.info(f"[TOKEN_REFRESH] Attempting to refresh token for {principal.email}")
            
            # Check if token actually needs refresh
            if not self.should_refresh_token(principal):
                logger.debug(f"[TOKEN_REFRESH] Token for {principal.email} does not need refresh")
                return principal
            
            # Determine token type and refresh accordingly
            if principal.api_token and principal.api_token.startswith('ai_'):
                # API token refresh - API tokens don't expire in the traditional sense
                # but we can validate and potentially re-issue them
                return await self._refresh_api_token(principal)
            else:
                # JWT token refresh using refresh token
                return await self._refresh_jwt_token(principal)
                
        except Exception as e:
            logger.error(f"[TOKEN_REFRESH] Failed to refresh token for {principal.email}: {e}")
            return None
    
    async def handle_mcp_auth_failure(self, principal: Principal, error_code: int) -> Optional[Principal]:
        """
        Handle MCP authentication failures and attempt recovery.
        
        Args:
            principal: Principal object with failed authentication
            error_code: HTTP error code that triggered the failure
            
        Returns:
            Principal: Updated principal with refreshed token or None if recovery failed
        """
        try:
            logger.warning(f"[TOKEN_REFRESH] Handling auth failure (code {error_code}) for {principal.email}")
            
            # Only attempt refresh for specific error codes
            if error_code not in [401, 403]:
                logger.debug(f"[TOKEN_REFRESH] Error code {error_code} does not indicate token issue")
                return None
            
            # Attempt token refresh with retry logic
            for attempt in range(self.max_retries):
                try:
                    logger.info(f"[TOKEN_REFRESH] Refresh attempt {attempt + 1}/{self.max_retries} for {principal.email}")
                    
                    refreshed_principal = await self.refresh_principal_token(principal)
                    if refreshed_principal and refreshed_principal.is_token_valid():
                        logger.info(f"[TOKEN_REFRESH] ✅ Successfully refreshed token for {principal.email}")
                        return refreshed_principal
                    
                    # Wait before retry with exponential backoff
                    if attempt < self.max_retries - 1:
                        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                        logger.info(f"[TOKEN_REFRESH] Waiting {delay}s before retry {attempt + 2}")
                        await asyncio.sleep(delay)
                        
                except Exception as e:
                    logger.error(f"[TOKEN_REFRESH] Refresh attempt {attempt + 1} failed: {e}")
                    if attempt == self.max_retries - 1:
                        raise
            
            logger.error(f"[TOKEN_REFRESH] ❌ All refresh attempts failed for {principal.email}")
            return None
            
        except Exception as e:
            logger.error(f"[TOKEN_REFRESH] Error handling auth failure for {principal.email}: {e}")
            return None
    
    def should_refresh_token(self, principal: Principal) -> bool:
        """
        Check if token should be refreshed proactively.
        
        Args:
            principal: Principal to check
            
        Returns:
            bool: True if token should be refreshed
        """
        try:
            # If token is already expired, definitely refresh
            if principal.is_token_expired():
                logger.debug(f"[TOKEN_REFRESH] Token for {principal.email} is expired")
                return True
            
            # Check if token expires within the next 5 minutes (proactive refresh)
            time_until_expiry = principal.token_expires_at - datetime.now(timezone.utc)
            if time_until_expiry.total_seconds() < 300:  # 5 minutes
                logger.debug(f"[TOKEN_REFRESH] Token for {principal.email} expires soon ({time_until_expiry})")
                return True
            
            # Check if this is an API token that may need validation
            if principal.api_token and principal.api_token.startswith('ai_'):
                # For API tokens, we could implement periodic validation
                # For now, only refresh if explicitly expired
                return False
            
            logger.debug(f"[TOKEN_REFRESH] Token for {principal.email} does not need refresh")
            return False
            
        except Exception as e:
            logger.error(f"[TOKEN_REFRESH] Error checking if token should be refreshed: {e}")
            return False
    
    async def _refresh_api_token(self, principal: Principal) -> Optional[Principal]:
        """
        Refresh API token for principal.
        
        Args:
            principal: Principal with API token
            
        Returns:
            Principal: Updated principal or None if refresh failed
        """
        try:
            logger.info(f"[TOKEN_REFRESH] Refreshing API token for {principal.email}")
            
            # API tokens don't typically expire, but we can validate them
            # against the database and potentially re-issue
            
            # Validate current API token using auth middleware
            validated_token = clerk_auth.validate_token_for_mcp(principal.api_token)
            if validated_token:
                # Token is still valid, update timestamps
                updated_principal = principal.model_copy(update={
                    'last_used_at': datetime.now(timezone.utc),
                    'token_expires_at': datetime.now(timezone.utc) + timedelta(hours=24)  # Extend validity
                })
                logger.info(f"[TOKEN_REFRESH] ✅ API token validated and extended for {principal.email}")
                return updated_principal
            else:
                logger.error(f"[TOKEN_REFRESH] ❌ API token validation failed for {principal.email}")
                return None
                
        except Exception as e:
            logger.error(f"[TOKEN_REFRESH] Error refreshing API token for {principal.email}: {e}")
            return None
    
    async def _refresh_jwt_token(self, principal: Principal) -> Optional[Principal]:
        """
        Refresh JWT token using refresh token.
        
        Args:
            principal: Principal with JWT token
            
        Returns:
            Principal: Updated principal or None if refresh failed
        """
        try:
            logger.info(f"[TOKEN_REFRESH] Refreshing JWT token for {principal.email}")
            
            # Check if we have a refresh token in jwt_payload
            refresh_token = principal.jwt_payload.get('refresh_token')
            if not refresh_token:
                logger.error(f"[TOKEN_REFRESH] No refresh token available for {principal.email}")
                return None
            
            # Attempt to refresh using Clerk service
            try:
                # Use Clerk to refresh the token
                new_token_data = await clerk_service.refresh_token(refresh_token)
                if not new_token_data:
                    logger.error(f"[TOKEN_REFRESH] Clerk token refresh failed for {principal.email}")
                    return None
                
                # Update principal with new token data
                updated_principal = principal.model_copy(update={
                    'token_issued_at': datetime.now(timezone.utc),
                    'token_expires_at': new_token_data.get('expires_at', datetime.now(timezone.utc) + timedelta(hours=1)),
                    'last_used_at': datetime.now(timezone.utc),
                    'jwt_payload': {
                        **principal.jwt_payload,
                        'raw_token': new_token_data.get('token'),
                        'refresh_token': new_token_data.get('refresh_token', refresh_token)
                    }
                })
                
                logger.info(f"[TOKEN_REFRESH] ✅ JWT token refreshed for {principal.email}")
                return updated_principal
                
            except Exception as e:
                logger.error(f"[TOKEN_REFRESH] Clerk token refresh failed for {principal.email}: {e}")
                
                # Fallback: Create new token using auth middleware
                try:
                    new_access_token = clerk_auth.create_access_token(
                        data={"sub": principal.user_id, "email": principal.email},
                        expires_delta=timedelta(hours=1)
                    )
                    
                    updated_principal = principal.model_copy(update={
                        'token_issued_at': datetime.now(timezone.utc),
                        'token_expires_at': datetime.now(timezone.utc) + timedelta(hours=1),
                        'last_used_at': datetime.now(timezone.utc),
                        'jwt_payload': {
                            **principal.jwt_payload,
                            'raw_token': new_access_token
                        }
                    })
                    
                    logger.info(f"[TOKEN_REFRESH] ✅ Created new JWT token for {principal.email} (fallback)")
                    return updated_principal
                    
                except Exception as fallback_e:
                    logger.error(f"[TOKEN_REFRESH] Fallback token creation failed: {fallback_e}")
                    return None
                
        except Exception as e:
            logger.error(f"[TOKEN_REFRESH] Error refreshing JWT token for {principal.email}: {e}")
            return None


# Global token refresh service instance
token_refresh_service = TokenRefreshService()