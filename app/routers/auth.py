#!/usr/bin/env python3
"""
Authentication API Routes for AI Ticket Creator Backend
Handles user registration, login, token refresh, and profile management
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_db_session
from ..models.user import User
from ..models.organization import Organization
from ..schemas.user import (
    UserCreate, UserLogin, UserResponse, TokenResponse, RefreshTokenRequest, 
    UserUpdate, UserMeResponse, EmailCheckRequest, EmailCheckResponse
)
from ..middleware.auth_middleware import (
    auth_middleware, 
    get_current_user, 
    get_current_user_optional
)
from ..middleware.rate_limiting import auth_rate_limit
from ..services.ai_agent_service import ai_agent_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/check-email", response_model=EmailCheckResponse)
async def check_email_availability(
    email_check: EmailCheckRequest,
    db: AsyncSession = Depends(get_db_session),
    _rate_limit: Dict[str, Any] = Depends(auth_rate_limit)
):
    """Check if email is available for registration"""
    try:
        # Check if user with email already exists
        existing_user = await db.execute(
            select(User).where(User.email == email_check.email.lower())
        )
        user_exists = existing_user.scalar_one_or_none() is not None
        
        if user_exists:
            return EmailCheckResponse(
                email=email_check.email,
                available=False,
                message="Email is already registered"
            )
        else:
            return EmailCheckResponse(
                email=email_check.email,
                available=True,
                message="Email is available for registration"
            )
            
    except Exception as e:
        logger.error(f"❌ Email check failed for {email_check.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email availability check failed"
        )


@router.post("/register", response_model=UserResponse)
async def register_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db_session),
    _rate_limit: Dict[str, Any] = Depends(auth_rate_limit)
):
    """Register a new user account"""
    try:
        # Check if user already exists
        existing_user = await db.execute(
            select(User).where(User.email == user_data.email)
        )
        if existing_user.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        # Create password hash
        password_hash = auth_middleware.get_password_hash(user_data.password)
        
        # Handle organization - create or find existing
        organization_id = None
        if user_data.organization_name:
            # Try to find existing organization by name
            existing_org = await db.execute(
                select(Organization).where(Organization.name == user_data.organization_name)
            )
            organization = existing_org.scalar_one_or_none()
            
            # Create new organization if doesn't exist
            if not organization:
                organization = Organization(
                    name=user_data.organization_name,
                    is_enabled=True,
                    plan="basic",
                    timezone="UTC",
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                db.add(organization)
                # Commit the organization first to ensure it exists for foreign key
                await db.commit()
                await db.refresh(organization)
                logger.info(f"✅ New organization created: {user_data.organization_name}")
                
                # Auto-create Customer Support Agent for new organization
                try:
                    agent = await ai_agent_service.create_organization_agent(
                        organization_id=organization.id,
                        agent_type="customer_support",
                        name=f"{organization.name} - Customer Support Agent",
                        auto_created=True,
                        db=db
                    )
                    if agent:
                        logger.info(f"🤖 Auto-created Customer Support Agent for organization {organization.name}")
                    else:
                        logger.warning(f"⚠️ Failed to auto-create agent for organization {organization.name}")
                except Exception as e:
                    logger.error(f"❌ Error auto-creating agent for organization {organization.name}: {e}")
                    # Don't fail registration if agent creation fails
            
            organization_id = organization.id
        
        # Create new user
        db_user = User(
            email=user_data.email,
            full_name=user_data.full_name,
            password_hash=password_hash,
            organization_id=organization_id,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        
        logger.info(f"✅ New user registered: {user_data.email}")
        
        return UserResponse(
            id=db_user.id,
            email=db_user.email,
            full_name=db_user.full_name,
            is_active=db_user.is_active,
            created_at=db_user.created_at,
            last_login_at=db_user.last_login_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ User registration failed: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=TokenResponse)
async def login_user(
    user_data: UserLogin,
    db: AsyncSession = Depends(get_db_session),
    _rate_limit: Dict[str, Any] = Depends(auth_rate_limit)
):
    """Authenticate user and return JWT tokens"""
    try:
        # Authenticate user
        user = await auth_middleware.authenticate_user(
            user_data.email, 
            user_data.password, 
            db
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create tokens
        token_data = {"sub": str(user.id), "email": user.email}
        access_token = auth_middleware.create_access_token(token_data)
        refresh_token = auth_middleware.create_refresh_token(token_data)
        
        logger.info(f"✅ User logged in successfully: {user.email}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=1800,  # 30 minutes
            user=UserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                is_active=user.is_active,
                created_at=user.created_at,
                last_login_at=user.last_login_at
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Login failed for {user_data.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db_session),
    _rate_limit: Dict[str, Any] = Depends(auth_rate_limit)
):
    """Refresh JWT access token using refresh token"""
    if not refresh_data.refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Verify refresh token
        payload = auth_middleware.verify_token(refresh_data.refresh_token, "refresh")
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get user from database
        result = await db.execute(select(User).where(User.id == UUID(user_id)))
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create new tokens
        token_data = {"sub": str(user.id), "email": user.email}
        access_token = auth_middleware.create_access_token(token_data)
        new_refresh_token = auth_middleware.create_refresh_token(token_data)
        
        logger.info(f"✅ Token refreshed for user: {user.email}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=1800,  # 30 minutes
            user=UserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                is_active=user.is_active,
                created_at=user.created_at,
                last_login_at=user.last_login_at
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token refresh failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get("/me", response_model=UserMeResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get current user's profile information"""
    # Load organization data if user has one
    organization = None
    if current_user.organization_id:
        org_result = await db.execute(
            select(Organization).where(Organization.id == current_user.organization_id)
        )
        organization = org_result.scalar_one_or_none()
    
    return UserMeResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        avatar_url=current_user.avatar_url,
        role=current_user.role.value,
        is_active=current_user.is_active,
        timezone=current_user.timezone,
        language=current_user.language,
        preferences=current_user.preferences,
        is_verified=current_user.is_verified,
        last_login_at=current_user.last_login_at,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        # Organization fields
        organization_id=current_user.organization_id,
        organization_name=organization.name if organization else None,
        organization_domain=organization.domain if organization else None,
        organization_plan=organization.plan if organization else None,
        organization_timezone=organization.timezone if organization else None
    )


@router.put("/me", response_model=UserMeResponse)
async def update_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Update current user's profile information"""
    try:
        # Update user fields
        update_data = user_update.model_dump(exclude_unset=True)
        
        # Handle password update separately
        if "password" in update_data:
            password_hash = auth_middleware.get_password_hash(update_data["password"])
            update_data["password_hash"] = password_hash
            del update_data["password"]
        
        # Update user
        for field, value in update_data.items():
            if hasattr(current_user, field):
                setattr(current_user, field, value)
        
        current_user.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(current_user)
        
        logger.info(f"✅ User profile updated: {current_user.email}")
        
        # Load organization data if user has one
        organization = None
        if current_user.organization_id:
            org_result = await db.execute(
                select(Organization).where(Organization.id == current_user.organization_id)
            )
            organization = org_result.scalar_one_or_none()
        
        return UserMeResponse(
            id=current_user.id,
            email=current_user.email,
            full_name=current_user.full_name,
            avatar_url=current_user.avatar_url,
            role=current_user.role.value,
            is_active=current_user.is_active,
            timezone=current_user.timezone,
            language=current_user.language,
            preferences=current_user.preferences,
            is_verified=current_user.is_verified,
            last_login_at=current_user.last_login_at,
            created_at=current_user.created_at,
            updated_at=current_user.updated_at,
            # Organization fields
            organization_id=current_user.organization_id,
            organization_name=organization.name if organization else None,
            organization_domain=organization.domain if organization else None,
            organization_plan=organization.plan if organization else None,
            organization_timezone=organization.timezone if organization else None
        )
        
    except Exception as e:
        logger.error(f"❌ Profile update failed for {current_user.email}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile update failed"
        )


@router.post("/logout")
async def logout_user(
    current_user: User = Depends(get_current_user)
):
    """Logout user (client-side token invalidation)"""
    # In a production system, you might want to maintain a blacklist of tokens
    # For now, we just return success and rely on client-side token removal
    logger.info(f"✅ User logged out: {current_user.email}")
    
    return {
        "message": "Successfully logged out",
        "detail": "Please remove the token from your client storage"
    }


@router.get("/verify")
async def verify_token(
    current_user: User = Depends(get_current_user_optional)
):
    """Verify if current token is valid"""
    if current_user:
        return {
            "valid": True,
            "user": UserResponse(
                id=current_user.id,
                email=current_user.email,
                full_name=current_user.full_name,
                is_active=current_user.is_active,
                created_at=current_user.created_at,
                last_login_at=current_user.last_login_at
            )
        }
    else:
        return {"valid": False, "user": None}