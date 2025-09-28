#!/usr/bin/env python3
"""
Authentication API Routes for AI Ticket Creator Backend
Handles user registration, login, token refresh, and profile management
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from ..database import get_db_session
from ..models.user import User
from ..models.organization import Organization
from ..models.organization_invitation import OrganizationRole
from ..schemas.user import (
    UserCreate, UserLogin, UserResponse, TokenResponse, RefreshTokenRequest, 
    UserUpdate, EmailCheckRequest, EmailCheckResponse
)
from ..middleware.auth_middleware import (
    auth_middleware, 
    get_current_user, 
    get_current_user_optional
)
from ..middleware.rate_limiting import auth_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


async def build_user_response(user: User, db: AsyncSession) -> UserResponse:
    """Build standardized UserResponse object"""
    # Load organization data if user has one
    organization = None
    if user.organization_id:
        org_result = await db.execute(
            select(Organization).where(Organization.id == user.organization_id)
        )
        organization = org_result.scalar_one_or_none()
    
    # Get medium variant avatar URL using avatar service
    from app.services.avatar_service import AvatarService
    avatar_service = AvatarService()
    medium_avatar_url = await avatar_service.get_user_avatar_url(user.id, "medium") if user.avatar_url else None
    
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        avatar_url=medium_avatar_url,  # Use medium variant URL
        role=user.organization_role.value if user.organization_role else None,
        is_active=user.is_active,
        timezone=user.timezone,
        language=user.language,
        preferences=user.preferences,
        is_verified=user.is_verified,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
        # Organization fields
        organization_id=user.organization_id,
        organization_name=organization.name if organization else None,
        organization_domain=organization.domain if organization else None,
        organization_plan=organization.plan if organization else None,
        organization_timezone=organization.timezone if organization else None,
        # Organization membership fields
        invited_by_id=user.invited_by_id,
        invited_at=user.invited_at,
        joined_organization_at=user.joined_organization_at
    )


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

        # Infer organization from email domain
        try:
            email_domain = user_data.email.split('@')[1].lower().strip()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format"
            )

        organization_id = None
        organization = None

        # Primary: find organization by domain
        org_by_domain_result = await db.execute(
            select(Organization).where(Organization.domain == email_domain)
        )
        organization = org_by_domain_result.scalar_one_or_none()

        # Fallback: if not found by domain and a name was provided, try to find by name
        # (We don't use name for selection preference; only to opportunistically set domain.)
        if not organization and getattr(user_data, "organization_name", None):
            org_by_name_result = await db.execute(
                select(Organization).where(Organization.name == user_data.organization_name)
            )
            organization = org_by_name_result.scalar_one_or_none()

            # If an existing org has no domain, set it to the registrant's email domain
            if organization and not organization.domain:
                organization.domain = email_domain
                await db.commit()
                await db.refresh(organization)
                logger.info(
                    f"🏷️ Set domain for existing organization '{organization.name}' to {email_domain}"
                )

        # If still not found, create a new organization with the inferred domain
        if not organization:
            derived_name = getattr(user_data, "organization_name", None) or email_domain
            organization = Organization(
                name=derived_name,
                domain=email_domain,
                is_enabled=True,
                plan="basic",
                timezone="UTC",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            db.add(organization)
            await db.commit()
            await db.refresh(organization)
            logger.info(f"✅ New organization created: {derived_name} ({email_domain})")

        organization_id = organization.id

        # Check if this user should be an admin 
        # If an organization_name was provided, this is likely a new org and user should be admin
        # Otherwise, check if this is the first user in the organization
        organization_role = OrganizationRole.MEMBER  # Default
        
        if getattr(user_data, "organization_name", None):
            # Organization name provided - user is creating/founding this org, make them admin
            organization_role = OrganizationRole.ADMIN
            logger.info(f"Setting {user_data.email} as admin for new organization {user_data.organization_name}")
        else:
            # No org name provided, check if first user in existing org
            existing_members_result = await db.execute(
                select(User).where(
                    User.organization_id == organization_id,
                    User.organization_role.is_not(None),  # Only count users with actual organization roles
                    User.is_deleted == False
                )
            )
            existing_members = existing_members_result.scalars().all()
            
            # First user in organization becomes admin
            organization_role = OrganizationRole.ADMIN if len(existing_members) == 0 else OrganizationRole.MEMBER

        # Create new user
        db_user = User(
            email=user_data.email,
            full_name=user_data.full_name,
            password_hash=password_hash,
            organization_id=organization_id,
            organization_role=organization_role,  # ✅ Now properly set
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)

        logger.info(f"✅ New user registered: {user_data.email}")

        return await build_user_response(db_user, db)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ User registration failed: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/generate-api-key")
async def generate_api_key_for_testing(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    _rate_limit: Dict[str, Any] = Depends(auth_rate_limit)
):
    """
    Generate API key for authenticated Clerk user for API testing.
    
    This endpoint allows Clerk-authenticated users to generate API keys
    for use in Postman, Insomnia, or other API testing tools.
    
    **Workflow:**
    1. User authenticates via Clerk in frontend
    2. User calls this endpoint with Clerk JWT token
    3. System generates long-lived API key for testing
    4. User uses API key in Postman/testing tools
    """
    try:
        if not current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must be part of an organization to generate API keys"
            )
        
        # Check for existing active API tokens
        from app.models.api_token import APIToken
        from sqlalchemy import func
        
        existing_count = await db.scalar(
            select(func.count(APIToken.id)).where(
                and_(
                    APIToken.user_id == current_user.id,
                    APIToken.is_active == True,
                    APIToken.name == "Postman Testing"
                )
            )
        )
        
        if existing_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Postman testing API key already exists. Use /api/v1/api-tokens to manage existing keys."
            )
        
        # Generate secure token  
        import secrets
        import hashlib
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        
        # Get environment prefix
        from app.config.settings import get_settings
        settings = get_settings()
        env_prefix = settings.environment[:4]  # pro, san, dev
        
        # Create API token record
        api_token = APIToken(
            user_id=current_user.id,
            organization_id=current_user.organization_id,
            name="Postman Testing",
            token_hash=token_hash,
            permissions=["*"],  # Full permissions for testing
            expires_at=datetime.now(timezone.utc) + timedelta(days=90),  # 90 days
            is_active=True
        )
        
        db.add(api_token)
        await db.commit()
        await db.refresh(api_token)
        
        # Format token with environment prefix
        formatted_token = f"ai_{env_prefix}_{raw_token}"
        
        logger.info(f"✅ API key generated for testing: {current_user.email}")
        
        return {
            "api_key": formatted_token,
            "id": str(api_token.id),
            "name": api_token.name,
            "expires_at": api_token.expires_at,
            "organization_id": str(current_user.organization_id),
            "instructions": {
                "postman_setup": "1. Copy the api_key value above\n2. In Postman, set Authorization to 'Bearer Token'\n3. Paste the api_key as the Bearer Token value\n4. Use this for all API requests",
                "security_note": "This API key has full permissions and expires in 90 days. Store it securely."
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ API key generation failed for {current_user.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate API key"
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
            user=await build_user_response(user, db)
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


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get current user's profile information"""
    return await build_user_response(current_user, db)


@router.put("/me", response_model=UserResponse)
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
        
        return await build_user_response(current_user, db)
        
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
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db_session)
):
    """Verify if current token is valid"""
    if current_user:
        return {
            "valid": True,
            "user": await build_user_response(current_user, db)
        }
    else:
        return {"valid": False, "user": None}