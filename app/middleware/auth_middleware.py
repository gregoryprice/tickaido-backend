#!/usr/bin/env python3
"""
Authentication middleware for FastAPI with dual authentication support
"""

import logging
from typing import Optional
from datetime import datetime, timezone, timedelta
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from passlib.context import CryptContext
from jose import jwt, JWTError

from app.services.clerk_service import clerk_service
from app.models.user import User
from app.models.organization import Organization
from app.models.api_token import APIToken
from app.database import AsyncSessionLocal
from app.config.settings import get_settings

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)

# Password hashing context
pwd_context = CryptContext(
    schemes=["bcrypt"], 
    deprecated="auto",
    bcrypt__default_rounds=12,
    bcrypt__min_rounds=4,
    bcrypt__max_rounds=31
)


class AuthenticationError(Exception):
    """Custom authentication error"""
    pass


class AuthMiddleware:
    """Authentication middleware supporting both Clerk tokens and API tokens"""
    
    def __init__(self):
        """Initialize auth middleware with password context"""
        self.pwd_context = pwd_context
    
    def get_password_hash(self, password: str) -> str:
        """Hash password using bcrypt"""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    async def authenticate_user(self, email: str, password: str, db: AsyncSession) -> Optional[User]:
        """Authenticate user with email and password"""
        try:
            # Get user by email
            result = await db.execute(
                select(User).where(
                    and_(User.email == email, User.is_deleted == False)
                )
            )
            user = result.scalar_one_or_none()
            
            if not user:
                logger.debug(f"User not found: {email}")
                return None
            
            # Check if user has a password hash (Clerk users won't have one)
            if not user.password_hash:
                logger.debug(f"User {email} has no password hash - likely a Clerk user")
                return None
            
            # Verify password
            if not self.verify_password(password, user.password_hash):
                logger.debug(f"Password verification failed for {email}")
                return None
            
            # Check if user is active
            if not user.is_active:
                logger.debug(f"User {email} is not active")
                return None
            
            # Update last login
            user.last_login_at = datetime.now(timezone.utc)
            if user.login_count is None:
                user.login_count = 0
            user.login_count += 1
            await db.commit()
            
            logger.debug(f"User authenticated successfully: {email}")
            return user
            
        except Exception as e:
            logger.error(f"Error during user authentication: {e}")
            return None
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        from jose import jwt
        
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=30)  # Default 30 minutes
        
        to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
        
        settings = get_settings()
        encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm="HS256")
        return encoded_jwt
    
    def create_refresh_token(self, data: dict) -> str:
        """Create JWT refresh token"""
        from jose import jwt
        
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=7)  # 7 days for refresh token
        to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc), "type": "refresh"})
        
        settings = get_settings()
        encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm="HS256")
        return encoded_jwt
    
    def verify_token(self, token: str, token_type: str = "access") -> dict:
        """Verify and decode JWT token"""
        from jose import jwt, JWTError
        
        try:
            settings = get_settings()
            payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
            
            # Check token type if specified
            if token_type == "refresh":
                if payload.get("type") != "refresh":
                    raise JWTError("Invalid token type")
            
            return payload
        except JWTError as e:
            logger.debug(f"Token verification failed: {e}")
            raise e
    
    async def __call__(
        self,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
    ) -> Optional[User]:
        """Authenticate request using Clerk token or API token"""
        
        if not credentials:
            return None
        
        token = credentials.credentials
        
        # Check if it's an API token (starts with "ai_")
        if token.startswith("ai_"):
            return await self._validate_api_token(token, request)
        else:
            # Standard Clerk token validation
            return await self._validate_clerk_token(token, request)
    
    async def _validate_api_token(self, token: str, request: Request) -> Optional[User]:
        """Validate API token and return user with organization context"""
        
        try:
            # Parse environment-specific token format: ai_env_token
            parts = token.split('_', 2)
            if len(parts) != 3 or parts[0] != 'ai':
                return None
            
            env_prefix, raw_token = parts[1], parts[2]
            
            # Validate environment matches current environment
            settings = get_settings()
            expected_env = settings.environment[:3]  # pro, sta, dev
            if env_prefix != expected_env:
                logger.warning(f"Token environment mismatch: expected {expected_env}, got {env_prefix}")
                return None
            
            # Hash the raw token for database lookup using the same method as creation
            import hashlib
            token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
            
            async with AsyncSessionLocal() as db:
                # Find token by hash with organization and user data
                result = await db.execute(
                    select(APIToken, User, Organization)
                    .join(User, APIToken.user_id == User.id)
                    .join(Organization, APIToken.organization_id == Organization.id)
                    .where(
                        and_(
                            APIToken.token_hash == token_hash,
                            APIToken.is_active == True,
                            APIToken.expires_at > datetime.now(timezone.utc),
                            User.is_active == True,
                            Organization.is_enabled == True
                        )
                    )
                )
                
                token_data = result.first()
                
                if not token_data:
                    logger.debug("No matching API token found in database")
                    return None
                
                api_token, user, organization = token_data
                
                # Update last used timestamp
                api_token.update_last_used()
                await db.commit()
                
                # Set organization context in request state for later middleware
                request.state.api_token = api_token
                request.state.organization_id = organization.id
                request.state.organization = organization
                request.state.user_permissions = api_token.permissions or ["*"]
                
                logger.debug(f"API token authenticated: user={user.email}, org={organization.name}")
                return user
                
        except Exception as e:
            logger.error(f"API token validation failed: {e}")
            return None
    
    async def _validate_clerk_token(self, token: str, request: Request) -> Optional[User]:
        """Validate Clerk session token and return user"""
        
        try:
            # Verify with Clerk
            logger.debug("Calling clerk_service.verify_token")
            clerk_user = await clerk_service.verify_token(token)
            logger.debug(f"clerk_service.verify_token returned: {clerk_user}")
            
            if not clerk_user:
                logger.warning("Clerk service returned None")
                return None
            
            # Get or create local user record
            logger.debug("Syncing local user")
            user = await self._sync_local_user(clerk_user)
            logger.debug(f"_sync_local_user returned: {user}")
            
            if not user:
                logger.warning("Failed to sync local user")
                return None
            
            # Set user context in request state
            request.state.clerk_user = clerk_user
            request.state.auth_method = "clerk"
            
            # Set organization context if user has organization
            if user.organization_id:
                try:
                    async with AsyncSessionLocal() as db:
                        org_result = await db.execute(
                            select(Organization).where(Organization.id == user.organization_id)
                        )
                        organization = org_result.scalar_one_or_none()
                        if organization:
                            request.state.organization = organization
                            request.state.organization_id = organization.id
                            logger.debug(f"Set organization context: {organization.name}")
                except Exception as e:
                    logger.warning(f"Failed to set organization context: {e}")
            
            logger.debug(f"Clerk token authenticated: user={user.email}")
            return user
            
        except Exception as e:
            logger.error(f"Clerk token validation failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    async def _sync_local_user(self, clerk_user: dict) -> Optional[User]:
        """Sync Clerk user data with local database, including organization"""
        
        try:
            logger.debug(f"Syncing clerk_user: {clerk_user}")
            
            async with AsyncSessionLocal() as db:
                # First, handle organization sync if org info is available
                organization_id = None
                if clerk_user.get('org_id'):
                    organization_id = await self._sync_organization(clerk_user, db)
                    logger.debug(f"Synced organization_id: {organization_id}")
                
                # Look for existing user by Clerk ID or email
                logger.debug(f"Looking for existing user with clerk_id={clerk_user['clerk_id']} or email={clerk_user['email']}")
                
                result = await db.execute(
                    select(User).where(
                        (User.clerk_id == clerk_user['clerk_id']) |
                        (User.email == clerk_user['email'])
                    )
                )
                user = result.scalar_one_or_none()
                logger.debug(f"Found existing user: {user}")
                
                # Determine organization role from Clerk
                from app.models.organization_invitation import OrganizationRole
                org_role = OrganizationRole.MEMBER  # Default
                if clerk_user.get('org_role') == 'admin':
                    org_role = OrganizationRole.ADMIN
                
                if user:
                    # Update existing user
                    logger.debug("Updating existing user")
                    user.clerk_id = clerk_user['clerk_id']
                    user.email = clerk_user['email']
                    if clerk_user.get('full_name'):
                        user.full_name = clerk_user['full_name']
                    if clerk_user.get('image_url'):
                        user.avatar_url = clerk_user['image_url']
                    user.is_verified = True  # Clerk handles verification
                    
                    # Update organization association if Clerk provides org data
                    if organization_id:
                        user.organization_id = organization_id
                        user.organization_role = org_role
                        if not user.joined_organization_at:
                            user.joined_organization_at = datetime.now(timezone.utc)
                        logger.debug(f"Updated user organization: {organization_id}, role: {org_role}")
                    # Note: If Clerk doesn't provide org data, we preserve existing org assignment
                    
                    # Ensure defaults are set before recording login
                    if user.login_count is None:
                        user.login_count = 0
                    if user.failed_login_attempts is None:
                        user.failed_login_attempts = 0
                    
                    logger.debug(f"Recording login for existing user: login_count={user.login_count}")
                    user.record_login()
                else:
                    # Create new user (JIT provisioning)
                    logger.debug("Creating new user via JIT provisioning")
                    user = User(
                        clerk_id=clerk_user['clerk_id'],
                        email=clerk_user['email'],
                        full_name=clerk_user.get('full_name', ''),
                        avatar_url=clerk_user.get('image_url'),
                        is_verified=True,
                        is_active=True,
                        external_auth_provider='clerk',
                        external_auth_id=clerk_user['clerk_id'],
                        password_hash=None,  # No local password for Clerk users
                        login_count=0,  # Set default explicitly
                        failed_login_attempts=0,  # Set default explicitly
                        timezone="UTC",  # Set default explicitly  
                        language="en",  # Set default explicitly
                        organization_id=organization_id,  # Associate with organization from Clerk
                        organization_role=org_role if organization_id else None,  # Only set role if in org
                        joined_organization_at=datetime.now(timezone.utc) if organization_id else None
                    )
                    logger.debug(f"Creating new user with org: {organization_id}, role: {org_role if organization_id else None}")
                    logger.debug(f"Recording login for new user: login_count={user.login_count}")
                    user.record_login()
                    db.add(user)
                
                logger.debug("Committing database changes")
                await db.commit()
                await db.refresh(user)
                
                logger.debug(f"Successfully synced user: {user.id} - {user.email}, org: {user.organization_id}, role: {user.organization_role}")
                return user
                
        except Exception as e:
            logger.error(f"Failed to sync local user: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    async def _sync_organization(self, clerk_user: dict, db: AsyncSession) -> Optional[str]:
        """Sync organization from Clerk data with local database"""
        
        try:
            org_clerk_id = clerk_user.get('org_id')
            if not org_clerk_id:
                return None
            
            # Look for existing organization by Clerk ID
            result = await db.execute(
                select(Organization).where(Organization.clerk_organization_id == org_clerk_id)
            )
            org = result.scalar_one_or_none()
            
            if org:
                # Update existing organization
                logger.debug(f"Found existing organization: {org.name}")
                if clerk_user.get('org_slug'):
                    org.name = clerk_user['org_slug'].replace('-', ' ').title()
                org.is_enabled = True
                return org.id
            else:
                # Create new organization (JIT provisioning)
                logger.debug("Creating new organization via JIT provisioning")
                org_name = clerk_user.get('org_slug', 'Unknown Organization').replace('-', ' ').title()
                org = Organization(
                    clerk_organization_id=org_clerk_id,
                    name=org_name,
                    is_enabled=True,
                    plan='basic'  # Default plan
                )
                db.add(org)
                await db.flush()  # Get the ID without committing
                logger.debug(f"Created new organization: {org.name} with ID {org.id}")
                return org.id
            
        except Exception as e:
            logger.error(f"Failed to sync organization: {e}")
            return None


# Global middleware instance
clerk_auth = AuthMiddleware()


async def get_current_user(
    user: User = Depends(clerk_auth)
) -> User:
    """Dependency to get current authenticated user (required)"""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_user_optional(
    user: Optional[User] = Depends(clerk_auth)
) -> Optional[User]:
    """Dependency to get current user (optional)"""
    return user


# Compatibility functions for legacy code
def require_permissions(*permissions: str):
    """Decorator to require specific permissions for endpoint access"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract user from kwargs (should be injected by dependency)
            user = kwargs.get('current_user')
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Check permissions (simplified - extend as needed)
            for permission in permissions:
                if not hasattr(user, 'has_permission') or not user.has_permission(permission):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Missing required permission: {permission}"
                    )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# WebSocket auth compatibility
class WebSocketAuthMiddleware:
    """Authentication middleware for WebSocket connections"""
    
    def __init__(self):
        self.auth_service = clerk_auth
    
    async def authenticate_websocket_token(self, token: str, db) -> Optional[User]:
        """Authenticate WebSocket connection using JWT token"""
        try:
            return await clerk_auth._validate_clerk_token(token, None)
        except Exception as e:
            logger.warning(f"WebSocket authentication failed: {e}")
            return None


# Global instances
websocket_auth = WebSocketAuthMiddleware()

# Compatibility aliases for legacy imports
auth_middleware = clerk_auth
auth_service = clerk_auth