#!/usr/bin/env python3
"""
Modern Authentication Service for AI Ticket Creator Backend
Using async SQLAlchemy 2.0, Pydantic v2, and pure asyncio patterns
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta

from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models.user import User
from ..database import get_db_session
from ..config.settings import get_settings

logger = logging.getLogger(__name__)

# Password hashing context with modern configuration
pwd_context = CryptContext(
    schemes=["bcrypt"], 
    deprecated="auto",
    bcrypt__default_rounds=12,
    # Explicitly avoid deprecated schemes that use crypt module
    bcrypt__min_rounds=4,
    bcrypt__max_rounds=31
)

# JWT Bearer token handler
security = HTTPBearer(auto_error=False)


class AuthenticationError(Exception):
    """Custom authentication error"""
    pass


class AuthService:
    """Modern authentication service using async SQLAlchemy 2.0 patterns"""
    
    def __init__(self):
        self.settings = get_settings()
        self.pwd_context = pwd_context
        self.secret_key = self.settings.JWT_SECRET_KEY
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
        self.refresh_token_expire_days = 7
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash using bcrypt"""
        try:
            return self.pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    def get_password_hash(self, password: str) -> str:
        """Generate secure password hash"""
        return self.pwd_context.hash(password)
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire, "type": "access"})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days)
        
        to_encode.update({"exp": expire, "type": "refresh"})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """Verify JWT token and return payload"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            if payload.get("type") != token_type:
                raise AuthenticationError(f"Invalid token type. Expected {token_type}")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except JWTError as e:
            raise AuthenticationError(f"Token validation failed: {str(e)}")
    
    async def authenticate_user(self, email: str, password: str, db: AsyncSession) -> Optional[User]:
        """Authenticate user using modern async SQLAlchemy 2.0 patterns"""
        try:
            # Query user with proper async SQLAlchemy 2.0 syntax
            stmt = select(User).where(
                User.email == email,
                User.is_deleted == False
            )
            
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                logger.warning(f"Authentication failed: User not found for email {email}")
                return None
            
            if not user.is_active:
                logger.warning(f"Authentication failed: User {email} is inactive")
                return None
            
            # Verify password (pure synchronous operation)
            if not self.verify_password(password, user.password_hash):
                logger.warning(f"Authentication failed: Invalid password for user {email}")
                return None
            
            # Update last login - with expire_on_commit=False, this is safe
            user.last_login_at = datetime.now(timezone.utc)
            await db.commit()
            
            logger.info(f"✅ User authenticated successfully: {email}")
            return user
            
        except Exception as e:
            logger.error(f"❌ Authentication error for {email}: {e}")
            await db.rollback()
            return None
    
    async def get_user_by_token(self, token: str, db: AsyncSession) -> Optional[User]:
        """Get user by JWT token using async SQLAlchemy 2.0"""
        try:
            payload = self.verify_token(token)
            user_id = payload.get("sub")
            
            if not user_id:
                raise AuthenticationError("Token missing user ID")
            
            
            # Query user with proper async patterns - user_id is UUID string
            stmt = select(User).where(
                User.id == user_id,
                User.is_deleted == False
            )
            
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                raise AuthenticationError("User not found")
            
            if not user.is_active:
                raise AuthenticationError("User account is inactive")
            
            return user
            
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"❌ Token verification error: {e}")
            raise AuthenticationError("Token validation failed")


# Global authentication service instance
auth_service = AuthService()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> User:
    """FastAPI dependency to get current authenticated user"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        user = await auth_service.get_user_by_token(credentials.credentials, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user
        
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> Optional[User]:
    """FastAPI dependency to get current user (optional)"""
    if not credentials:
        return None
    
    try:
        return await auth_service.get_user_by_token(credentials.credentials, db)
    except (AuthenticationError, HTTPException):
        return None


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
            
            # Check permissions
            for permission in permissions:
                if not hasattr(user, 'has_permission') or not user.has_permission(permission):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Missing required permission: {permission}"
                    )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


class WebSocketAuthMiddleware:
    """Authentication middleware for WebSocket connections"""
    
    def __init__(self):
        self.auth_service = auth_service
    
    async def authenticate_websocket_token(self, token: str, db: AsyncSession) -> Optional[User]:
        """Authenticate WebSocket connection using JWT token"""
        try:
            return await self.auth_service.get_user_by_token(token, db)
        except AuthenticationError as e:
            logger.warning(f"WebSocket authentication failed: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ WebSocket authentication error: {e}")
            return None


# Global instances
websocket_auth = WebSocketAuthMiddleware()

# Backward compatibility aliases
auth_middleware = auth_service
AuthMiddleware = AuthService