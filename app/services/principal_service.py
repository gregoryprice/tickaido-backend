#!/usr/bin/env python3
"""
Principal Service for secure authentication and authorization

This service replaces raw JWT token handling with Principal objects,
providing caching, organization context, and secure authentication.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import redis.asyncio as redis
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.models.organization import Organization
from app.models.user import User
from app.schemas.principal import Principal, SessionType
from app.services.clerk_service import clerk_service

logger = logging.getLogger(__name__)


class PrincipalExtractionError(Exception):
    """Custom exception for Principal extraction errors"""
    pass


class PrincipalService:
    """
    Service for creating and managing Principal objects with caching.
    
    This service handles:
    - JWT token validation and Principal extraction
    - Redis caching for performance (15-minute TTL)
    - Organization context loading
    - Permission mapping and caching
    """
    
    def __init__(self):
        self.settings = get_settings()
        self._redis_client: Optional[redis.Redis] = None
        
        # Cache configuration
        self.principal_cache_ttl = 900  # 15 minutes in seconds
        self.permission_cache_ttl = 300  # 5 minutes for permissions
        
        # Permission mappings - could be loaded from database/config
        self.default_permissions = self._load_permission_mappings()
    
    def _load_permission_mappings(self) -> Dict[str, List[str]]:
        """Load role-to-permissions mappings"""
        # This should ideally be loaded from database or config file
        return {
            "admin": ["*"],
            "member": ["create.ticket", "edit.ticket", "delete.ticket", "view.ticket", "get_system_health"],
        }
    
    async def get_redis_client(self) -> Optional[redis.Redis]:
        """Get or create Redis client for caching."""
        if self._redis_client is None or self._redis_client.closed:
            try:
                self._redis_client = redis.from_url(
                    str(self.settings.redis_url),
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
                
                # Test connection
                await self._redis_client.ping()
                logger.debug("Redis client connected successfully")
                
            except Exception as e:
                logger.warning(f"Redis connection failed, caching disabled: {e}")
                self._redis_client = None
        
        return self._redis_client
    
    async def extract_principal(
        self,
        token: str,
        db: AsyncSession,
        session_type: SessionType = SessionType.WEB
    ) -> Principal:
        """
        Extract Principal from JWT token with caching and full context loading.
        
        Args:
            token: JWT token string
            db: Database session for loading user/org data
            session_type: Type of session (web, api, mcp, integration)
            
        Returns:
            Principal object with full context
            
        Raises:
            PrincipalExtractionError: If token is invalid or user not found
        """
        try:
            # Check cache first
            cached_principal = await self._get_cached_principal(token)
            if cached_principal and not cached_principal.is_token_expired():
                logger.debug(f"Principal cache hit for user {cached_principal.user_id}")
                return cached_principal.update_last_used()
            
            # Validate token and extract user
            if token.startswith("ai_"):
                # API token - extract from database
                user = await self._extract_from_api_token(token, db)
                jwt_payload = {}  # No JWT for API tokens
            else:
                # JWT token - validate with Clerk or internal JWT
                user, jwt_payload = await self._extract_from_jwt_token(token, db)
            
            if not user:
                raise PrincipalExtractionError("User not found or inactive")
            
            # Load organization data
            organization = await self._load_organization(db, user.organization_id)
            
            # Build Principal with full context
            principal = await self._build_principal(
                user=user,
                organization=organization,
                jwt_payload=jwt_payload,
                session_type=session_type
            )
            
            # Cache the Principal
            await self._cache_principal(token, principal)
            
            logger.debug(f"Principal extracted for user {user.email}, org {organization.name if organization else 'None'}")
            return principal
            
        except Exception as e:
            logger.error(f"Principal extraction failed: {e}")
            raise PrincipalExtractionError(f"Failed to extract principal: {str(e)}")
    
    async def _get_cached_principal(self, token: str) -> Optional[Principal]:
        """Get Principal from cache"""
        redis_client = await self.get_redis_client()
        if not redis_client:
            return None
        
        try:
            # Use token hash for cache key to avoid storing full token
            import hashlib
            cache_key = f"principal:{hashlib.sha256(token.encode()).hexdigest()[:16]}"
            
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                principal_data = json.loads(cached_data)
                return Principal.from_dict(principal_data)
                
        except Exception as e:
            logger.debug(f"Cache retrieval failed: {e}")
        
        return None
    
    async def _cache_principal(self, token: str, principal: Principal) -> None:
        """Cache Principal for performance"""
        redis_client = await self.get_redis_client()
        if not redis_client:
            return
        
        try:
            import hashlib
            cache_key = f"principal:{hashlib.sha256(token.encode()).hexdigest()[:16]}"
            
            # Convert to cache-friendly format
            cache_data = json.dumps(principal.to_cache_dict())
            
            await redis_client.setex(
                cache_key,
                self.principal_cache_ttl,
                cache_data
            )
            
            logger.debug(f"Principal cached for user {principal.user_id}")
            
        except Exception as e:
            logger.debug(f"Cache storage failed: {e}")
    
    async def _extract_from_api_token(self, token: str, db: AsyncSession) -> Optional[User]:
        """Extract user from API token"""
        try:
            # Parse environment-specific token format: ai_env_token
            parts = token.split('_', 2)
            if len(parts) != 3 or parts[0] != 'ai':
                return None
            
            env_prefix, raw_token = parts[1], parts[2]
            
            # Validate environment
            expected_env = self.settings.environment[:3]
            if env_prefix != expected_env:
                logger.warning(f"Token environment mismatch: expected {expected_env}, got {env_prefix}")
                return None
            
            # Hash token for lookup
            import hashlib
            token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
            
            # Find user by API token
            from app.models.api_token import APIToken
            
            result = await db.execute(
                select(APIToken, User)
                .join(User, APIToken.user_id == User.id)
                .where(
                    APIToken.token_hash == token_hash,
                    APIToken.is_active == True,
                    APIToken.expires_at > datetime.now(timezone.utc),
                    User.is_active == True
                )
            )
            
            token_data = result.first()
            if not token_data:
                return None
            
            api_token, user = token_data
            
            # Update last used
            api_token.update_last_used()
            await db.commit()
            
            return user
            
        except Exception as e:
            logger.error(f"API token extraction failed: {e}")
            return None
    
    async def _extract_from_jwt_token(self, token: str, db: AsyncSession) -> tuple[Optional[User], Dict[str, Any]]:
        """Extract user from JWT token"""
        try:
            # First try internal JWT validation
            try:
                jwt_payload = self._verify_internal_jwt(token)
                user = await self._load_user_by_id(db, jwt_payload.get('sub'))
                if user:
                    return user, jwt_payload
            except JWTError:
                pass  # Fall through to Clerk validation
            
            # Try Clerk validation
            clerk_user = await clerk_service.verify_token(token)
            if not clerk_user:
                return None, {}
            
            # Sync local user from Clerk data
            user = await self._sync_user_from_clerk(db, clerk_user)
            return user, clerk_user
            
        except Exception as e:
            logger.error(f"JWT token extraction failed: {e}")
            return None, {}
    
    def _verify_internal_jwt(self, token: str) -> Dict[str, Any]:
        """Verify internal JWT token"""
        return jwt.decode(
            token,
            self.settings.secret_key,
            algorithms=["HS256"]
        )
    
    async def _load_user_by_id(self, db: AsyncSession, user_id: str) -> Optional[User]:
        """Load user by ID"""
        if not user_id:
            return None
            
        result = await db.execute(
            select(User).where(
                User.id == user_id,
                User.is_active == True,
                User.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()
    
    async def _sync_user_from_clerk(self, db: AsyncSession, clerk_user: Dict[str, Any]) -> Optional[User]:
        """Sync user from Clerk data (simplified from auth_middleware)"""
        try:
            # Look for existing user
            result = await db.execute(
                select(User).where(
                    (User.clerk_id == clerk_user['clerk_id']) |
                    (User.email == clerk_user['email'])
                )
            )
            user = result.scalar_one_or_none()
            
            if user:
                # Update existing user
                user.clerk_id = clerk_user['clerk_id']
                user.email = clerk_user['email']
                if clerk_user.get('full_name'):
                    user.full_name = clerk_user['full_name']
                user.is_verified = True
                
                # Update organization if provided
                if clerk_user.get('org_id'):
                    org_id = await self._sync_organization_from_clerk(db, clerk_user)
                    if org_id:
                        user.organization_id = org_id
                
                await db.commit()
                await db.refresh(user)
                return user
            else:
                # Would create new user here, but simplified for now
                logger.warning(f"User not found for Clerk user {clerk_user.get('email')}")
                return None
                
        except Exception as e:
            logger.error(f"User sync failed: {e}")
            return None
    
    async def _sync_organization_from_clerk(self, db: AsyncSession, clerk_user: Dict[str, Any]) -> Optional[str]:
        """Sync organization from Clerk data"""
        org_clerk_id = clerk_user.get('org_id')
        if not org_clerk_id:
            return None
        
        try:
            result = await db.execute(
                select(Organization).where(Organization.clerk_organization_id == org_clerk_id)
            )
            org = result.scalar_one_or_none()
            
            if org:
                return org.id
            else:
                # Would create new org here, but simplified for now
                return None
                
        except Exception as e:
            logger.error(f"Organization sync failed: {e}")
            return None
    
    async def _load_organization(self, db: AsyncSession, org_id: Optional[str]) -> Optional[Organization]:
        """Load organization data for context."""
        if not org_id:
            return None
        
        try:
            result = await db.execute(
                select(Organization).where(
                    Organization.id == org_id,
                    Organization.is_enabled == True
                )
            )
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Failed to load organization {org_id}: {e}")
            return None
    
    async def _build_principal(
        self,
        user: User,
        organization: Optional[Organization],
        jwt_payload: Dict[str, Any],
        session_type: SessionType
    ) -> Principal:
        """Build Principal object with full context"""
        
        # Extract roles from user and organization context
        roles = []
        if user.organization_role:
            roles.append(user.organization_role.value if hasattr(user.organization_role, 'value') else str(user.organization_role))
        
        # Add roles from JWT if present
        if 'roles' in jwt_payload:
            roles.extend(jwt_payload['roles'])
        elif 'org_role' in jwt_payload:
            roles.append(jwt_payload['org_role'])
        
        # Ensure default role
        if not roles:
            roles = ["user"]
        
        # Build permissions based on roles
        permissions = []
        for role in roles:
            role_perms = self.default_permissions.get(role, [])
            permissions.extend(role_perms)
        
        # Remove duplicates
        permissions = list(set(permissions))
        
        # Extract scopes
        scopes = jwt_payload.get('scopes', ['basic'])
        
        # Parse token timestamps
        issued_at = datetime.now(timezone.utc)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)  # Default 1 hour
        
        if 'iat' in jwt_payload:
            issued_at = datetime.fromtimestamp(jwt_payload['iat'], tz=timezone.utc)
        if 'exp' in jwt_payload:
            expires_at = datetime.fromtimestamp(jwt_payload['exp'], tz=timezone.utc)
        
        return Principal(
            user_id=str(user.id),
            organization_id=str(user.organization_id) if user.organization_id else "",
            email=user.email,
            full_name=user.full_name,
            roles=roles,
            permissions=permissions,
            scopes=scopes,
            session_id=jwt_payload.get('jti'),  # JWT ID as session ID
            session_type=session_type,
            token_issued_at=issued_at,
            token_expires_at=expires_at,
            jwt_payload=jwt_payload,
            organization_name=organization.name if organization else None,
            organization_plan=organization.plan if organization else None,
            organization_role=str(user.organization_role) if user.organization_role else None
        )
    
    async def refresh_principal_cache(self, token: str) -> None:
        """Force refresh of principal cache"""
        redis_client = await self.get_redis_client()
        if not redis_client:
            return
        
        try:
            import hashlib
            cache_key = f"principal:{hashlib.sha256(token.encode()).hexdigest()[:16]}"
            await redis_client.delete(cache_key)
            logger.debug("Principal cache invalidated")
        except Exception as e:
            logger.debug(f"Cache invalidation failed: {e}")
    
    async def get_principal_by_user_id(
        self,
        user_id: str,
        db: AsyncSession
    ) -> Optional[Principal]:
        """Get Principal directly by user ID (for system operations)"""
        try:
            # Load user
            user = await self._load_user_by_id(db, user_id)
            if not user:
                return None
            
            # Load organization
            organization = await self._load_organization(db, user.organization_id)
            
            # Build Principal without JWT context
            return await self._build_principal(
                user=user,
                organization=organization,
                jwt_payload={},  # No JWT context for direct user lookup
                session_type=SessionType.API
            )
            
        except Exception as e:
            logger.error(f"Failed to get principal for user {user_id}: {e}")
            return None
    
    async def get_principal_from_request(
        self,
        request: Any,  # FastAPI Request object
        current_user: Any,  # User object from auth middleware
        db: AsyncSession
    ) -> Optional[Principal]:
        """
        Extract Principal from request with auth token (handles both API keys and JWT).
        
        Args:
            request: FastAPI Request object containing headers
            current_user: Authenticated user from middleware
            db: Database session
            
        Returns:
            Principal with embedded auth token for MCP tool calls
        """
        try:
            # Extract the authorization header
            auth_header = request.headers.get("authorization", "")
            token = None
            session_type = SessionType.API
            
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]  # Remove "Bearer " prefix
                
                # Determine if this is a JWT token or API key
                # JWT tokens typically have 3 parts separated by dots
                if token and token.count('.') == 2:
                    session_type = SessionType.JWT
                    logger.debug(f"[PRINCIPAL_SERVICE] Detected JWT token for user {current_user.id}")
                else:
                    session_type = SessionType.API
                    logger.debug(f"[PRINCIPAL_SERVICE] Detected API key for user {current_user.id}")
            
            if not token:
                logger.warning(f"[PRINCIPAL_SERVICE] No auth token found in request for user {current_user.id}")
                return None
            
            # Load organization
            organization = await self._load_organization(db, current_user.organization_id)
            
            # Create JWT payload with the raw token for MCP tool calls
            jwt_payload = {
                "token": token,
                "sub": str(current_user.id),
                "organization_id": str(current_user.organization_id) if current_user.organization_id else None
            }
            
            # Build Principal with auth context
            principal = await self._build_principal(
                user=current_user,
                organization=organization,
                jwt_payload=jwt_payload,
                session_type=session_type
            )
            
            # Set the API token field if this is an API key session
            if principal and session_type == SessionType.API and token:
                # Update the principal with api_token field
                principal = principal.model_copy(update={'api_token': token})
                logger.debug(f"[PRINCIPAL_SERVICE] Set api_token field for user {current_user.id}")
            
            return principal
            
        except Exception as e:
            logger.error(f"Failed to get principal from request for user {current_user.id}: {e}")
            return None
    
    async def close(self) -> None:
        """Close Redis connection"""
        if self._redis_client:
            await self._redis_client.close()
            self._redis_client = None
            logger.debug("Redis client closed")


# Global service instance
principal_service = PrincipalService()