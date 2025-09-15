#!/usr/bin/env python3
"""
FastAPI dependency injection functions
"""

import logging
from typing import Optional, Generator
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from app.database import get_db_session, SessionLocal
from app.config.settings import get_settings
from app.models import User  # Will be created later

logger = logging.getLogger(__name__)
security = HTTPBearer()

def get_current_settings():
    """Dependency to get current settings"""
    return get_settings()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db_session),
    settings = Depends(get_current_settings)
) -> User:
    """
    Get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Bearer token credentials
        db: Database session
        settings: Application settings
        
    Returns:
        User: Current authenticated user
        
    Raises:
        HTTPException: If authentication fails
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode JWT token
        payload = jwt.decode(
            credentials.credentials, 
            settings.jwt_secret_key,  # Use jwt_secret_key instead of secret_key
            algorithms=settings.algorithms
        )
        
        # Extract user ID from token
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
            
    except JWTError as e:
        logger.error(f"JWT decode error: {e}")
        raise credentials_exception
    
    # Get user from database using async SQLAlchemy 2.0 syntax
    try:
        from sqlalchemy import select
        stmt = select(User).where(
            User.id == user_id,
            User.is_deleted == False
        )
        
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user is None:
            logger.warning(f"User not found for token: {user_id}")
            raise credentials_exception
        
        if not user.is_active:
            logger.warning(f"Inactive user attempted access: {user.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user
        
    except Exception as e:
        logger.error(f"Database error getting user: {e}")
        raise credentials_exception

async def get_optional_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    settings = Depends(get_current_settings)
) -> Optional[User]:
    """
    Get current user if authentication token is provided, otherwise None.
    Used for endpoints that work with or without authentication.
    
    Args:
        request: FastAPI request object
        db: Database session
        settings: Application settings
        
    Returns:
        Optional[User]: Current user if authenticated, None otherwise
    """
    try:
        # Check for Authorization header
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            return None
        
        # Extract token
        token = authorization.split(" ")[1]
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        
        # Try to get current user
        return await get_current_user(credentials, db, settings)
        
    except Exception as e:
        logger.debug(f"Optional authentication failed: {e}")
        return None

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Get current active user (must be authenticated and active).
    
    Args:
        current_user: Current user from authentication
        
    Returns:
        User: Current active user
        
    Raises:
        HTTPException: If user is inactive
    """
    if not getattr(current_user, 'is_active', True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user

def get_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Get current user with admin privileges.
    
    Args:
        current_user: Current active user
        
    Returns:
        User: Current admin user
        
    Raises:
        HTTPException: If user is not an admin
    """
    if not getattr(current_user, 'is_admin', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user

class DatabaseDependency:
    """Database dependency class for custom session management"""
    
    def __init__(self):
        self.db_session: Optional[Session] = None
    
    def __call__(self) -> Generator[Session, None, None]:
        """Get database session with custom error handling"""
        self.db_session = SessionLocal()
        try:
            yield self.db_session
        except Exception as e:
            logger.error(f"Database dependency error: {e}")
            self.db_session.rollback()
            raise
        finally:
            self.db_session.close()
    
    def commit(self):
        """Commit current transaction"""
        if self.db_session:
            self.db_session.commit()
    
    def rollback(self):
        """Rollback current transaction"""
        if self.db_session:
            self.db_session.rollback()

# Create database dependency instance
db_dependency = DatabaseDependency()

async def verify_api_key(
    request: Request,
    settings = Depends(get_current_settings)
) -> bool:
    """
    Verify API key from request headers.
    Used for external API access.
    
    Args:
        request: FastAPI request object
        settings: Application settings
        
    Returns:
        bool: True if API key is valid
        
    Raises:
        HTTPException: If API key is invalid or missing
    """
    # Check for API key in headers
    api_key = request.headers.get("X-API-Key") or request.headers.get("API-Key")
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # TODO: Implement API key validation
    # For now, accept any non-empty API key
    # This should be replaced with actual API key validation from database
    if len(api_key) < 10:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format"
        )
    
    return True

async def get_client_ip(request: Request) -> str:
    """
    Get client IP address from request.
    Handles X-Forwarded-For header for reverse proxy setups.
    
    Args:
        request: FastAPI request object
        
    Returns:
        str: Client IP address
    """
    # Check X-Forwarded-For header first (for reverse proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP in the chain
        return forwarded_for.split(",")[0].strip()
    
    # Check X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fall back to client host
    return request.client.host if request.client else "unknown"

async def get_user_agent(request: Request) -> str:
    """
    Get user agent from request headers.
    
    Args:
        request: FastAPI request object
        
    Returns:
        str: User agent string
    """
    return request.headers.get("User-Agent", "unknown")

# Pagination dependencies
class PaginationParams:
    """Pagination parameters for API endpoints"""
    
    def __init__(self, page: int = 1, page_size: int = 20):
        self.page = max(1, page)  # Ensure page is at least 1
        self.page_size = min(100, max(1, page_size))  # Clamp between 1 and 100
        self.offset = (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        return self.page_size

def get_pagination_params(page: int = 1, page_size: int = 20) -> PaginationParams:
    """Dependency for pagination parameters"""
    return PaginationParams(page=page, page_size=page_size)


async def get_current_user_from_token(
    token: str,
    db: AsyncSession
) -> Optional[User]:
    """
    Get current user from raw JWT token string.
    Used for WebSocket authentication where we can't use HTTPBearer.
    
    Args:
        token: JWT token string
        db: Database session
        
    Returns:
        Optional[User]: Current user if token is valid, None otherwise
    """
    try:
        settings = get_settings()
        # Decode JWT token
        payload = jwt.decode(
            token, 
            settings.jwt_secret_key,
            algorithms=settings.algorithms
        )
        
        # Extract user ID from token
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        
        # Get user from database using async SQLAlchemy 2.0 syntax
        from sqlalchemy import select
        stmt = select(User).where(
            User.id == user_id,
            User.is_deleted == False
        )
        
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user is None or not user.is_active:
            return None
        
        return user
        
    except JWTError as e:
        logger.debug(f"WebSocket JWT decode error: {e}")
        return None
    except Exception as e:
        logger.error(f"Database error in get_current_user_from_token: {e}")
        return None