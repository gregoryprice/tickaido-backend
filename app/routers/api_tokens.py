#!/usr/bin/env python3
"""
API Token management routes for organization-scoped programmatic access
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.database import get_db_session
from app.middleware.organization_middleware import OrganizationContext, get_organization_context
from app.models.api_token import APIToken
from app.schemas.api_token import (
    APITokenGenerationRequest,
    APITokenListItem,
    APITokenListResponse,
    APITokenPartialUpdateRequest,
    APITokenResponse,
    APITokenRevokeResponse,
    APITokenUpdateRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api-tokens", tags=["API Token Management"])


@router.post("/", response_model=APITokenResponse, status_code=status.HTTP_201_CREATED)
async def generate_api_token(
    token_request: APITokenGenerationRequest,
    context: OrganizationContext = Depends(get_organization_context),
    db: AsyncSession = Depends(get_db_session)
):
    """Generate organization-scoped API token for programmatic access"""
    
    # Check permission to generate API tokens
    if not context.has_permission("api:generate"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to generate API tokens"
        )
    
    # Check token limits per user
    existing_tokens_count = await db.scalar(
        select(func.count(APIToken.id)).where(
            and_(
                APIToken.user_id == context.user.id,
                APIToken.is_active == True
            )
        )
    )
    
    if existing_tokens_count >= 10:  # Max 10 active tokens per user
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum number of API tokens reached (10). Please revoke unused tokens."
        )
    
    # Check for duplicate token name
    existing_name = await db.scalar(
        select(APIToken.id).where(
            and_(
                APIToken.user_id == context.user.id,
                APIToken.name == token_request.name,
                APIToken.is_active == True
            )
        )
    )
    
    if existing_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Token with name '{token_request.name}' already exists"
        )
    
    # Validate requested permissions are subset of user permissions
    user_permissions = context._get_role_permissions()
    requested_permissions = token_request.permissions or user_permissions
    
    if not set(requested_permissions).issubset(set(user_permissions)) and "*" not in user_permissions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Requested permissions exceed user's current permissions"
        )
    
    # Generate secure token
    raw_token = secrets.token_urlsafe(32)
    import hashlib
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    
    # Get environment prefix
    settings = get_settings()
    env_prefix = settings.environment[:3]  # pro, sta, dev
    
    # Create token record
    api_token = APIToken(
        user_id=context.user.id,
        organization_id=context.organization.id,
        name=token_request.name,
        token_hash=token_hash,
        permissions=requested_permissions,
        expires_at=datetime.now(timezone.utc) + timedelta(days=token_request.expires_days),
        is_active=True
    )
    
    db.add(api_token)
    await db.commit()
    await db.refresh(api_token)
    
    # Log token generation for audit
    logger.info(f"API token generated: user={context.user.email}, org={context.organization.name}, name={token_request.name}")
    
    return APITokenResponse(
        token=f"ai_{env_prefix}_{raw_token}",  # Environment-prefixed token
        id=api_token.id,
        name=api_token.name,
        permissions=api_token.permissions,
        created_at=api_token.created_at,
        updated_at=api_token.updated_at,
        expires_at=api_token.expires_at,
        last_used_at=api_token.last_used_at,
        is_active=api_token.is_active,
        is_expired=api_token.is_expired,
        organization_id=context.organization.id,
        organization_name=context.organization.name
    )


@router.get("/", response_model=APITokenListResponse)
async def list_api_tokens(
    context: OrganizationContext = Depends(get_organization_context),
    db: AsyncSession = Depends(get_db_session)
):
    """List user's API tokens for the current organization"""
    
    # Get all tokens for user in current organization
    result = await db.execute(
        select(APIToken).where(
            and_(
                APIToken.user_id == context.user.id,
                APIToken.organization_id == context.organization.id
            )
        ).order_by(APIToken.created_at.desc())
    )
    
    tokens = result.scalars().all()
    
    # Format tokens for response
    token_items = []
    active_count = 0
    expired_count = 0
    
    for token in tokens:
        is_expired = token.is_expired
        if token.is_active and not is_expired:
            active_count += 1
        elif is_expired:
            expired_count += 1
        
        token_items.append(APITokenListItem(
            id=token.id,
            name=token.name,
            permissions=token.permissions or [],
            created_at=token.created_at,
            updated_at=token.updated_at,
            expires_at=token.expires_at,
            last_used_at=token.last_used_at,
            is_active=token.is_active,
            is_expired=is_expired,
            organization_id=context.organization.id,
            organization_name=context.organization.name
        ))
    
    return APITokenListResponse(
        tokens=token_items,
        total_count=len(tokens),
        active_count=active_count,
        expired_count=expired_count
    )


@router.put("/{token_id}", response_model=APITokenListItem)
async def update_api_token(
    token_id: UUID,
    update_request: APITokenUpdateRequest,
    context: OrganizationContext = Depends(get_organization_context),
    db: AsyncSession = Depends(get_db_session)
):
    """Update an API token (full update)"""
    
    # Get token and verify ownership
    result = await db.execute(
        select(APIToken).where(
            and_(
                APIToken.id == token_id,
                APIToken.user_id == context.user.id,
                APIToken.organization_id == context.organization.id
            )
        )
    )
    
    api_token = result.scalar_one_or_none()
    if not api_token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API token not found"
        )
    
    # Validate requested permissions are subset of user permissions
    user_permissions = context._get_role_permissions()
    if not set(update_request.permissions).issubset(set(user_permissions)) and "*" not in user_permissions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Requested permissions exceed user's current permissions"
        )
    
    # Update token fields
    api_token.name = update_request.name
    api_token.permissions = update_request.permissions
    api_token.is_active = update_request.is_active
    
    # Update expiration if specified
    if update_request.expires_days is not None:
        api_token.expires_at = datetime.now(timezone.utc) + timedelta(days=update_request.expires_days)
    
    await db.commit()
    await db.refresh(api_token)
    
    # Log token update for audit
    logger.info(f"API token updated: user={context.user.email}, org={context.organization.name}, name={api_token.name}, id={token_id}")
    
    # Return token in standard format
    return APITokenListItem(
        id=api_token.id,
        name=api_token.name,
        permissions=api_token.permissions or [],
        created_at=api_token.created_at,
        updated_at=api_token.updated_at,
        expires_at=api_token.expires_at,
        last_used_at=api_token.last_used_at,
        is_active=api_token.is_active,
        is_expired=api_token.is_expired,
        organization_id=context.organization.id,
        organization_name=context.organization.name
    )


@router.patch("/{token_id}", response_model=APITokenListItem)
async def partially_update_api_token(
    token_id: UUID,
    update_request: APITokenPartialUpdateRequest,
    context: OrganizationContext = Depends(get_organization_context),
    db: AsyncSession = Depends(get_db_session)
):
    """Partially update an API token (PATCH)"""
    
    # Get token and verify ownership
    result = await db.execute(
        select(APIToken).where(
            and_(
                APIToken.id == token_id,
                APIToken.user_id == context.user.id,
                APIToken.organization_id == context.organization.id
            )
        )
    )
    
    api_token = result.scalar_one_or_none()
    if not api_token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API token not found"
        )
    
    # Track what was updated for logging
    updated_fields = []
    
    # Update only provided fields
    if update_request.name is not None:
        api_token.name = update_request.name
        updated_fields.append("name")
    
    if update_request.permissions is not None:
        # Validate requested permissions are subset of user permissions
        user_permissions = context._get_role_permissions()
        if not set(update_request.permissions).issubset(set(user_permissions)) and "*" not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Requested permissions exceed user's current permissions"
            )
        api_token.permissions = update_request.permissions
        updated_fields.append("permissions")
    
    if update_request.is_active is not None:
        api_token.is_active = update_request.is_active
        updated_fields.append("is_active")
    
    if update_request.expires_days is not None:
        api_token.expires_at = datetime.now(timezone.utc) + timedelta(days=update_request.expires_days)
        updated_fields.append("expires_at")
    
    # Check if any fields were actually updated
    if not updated_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided to update"
        )
    
    await db.commit()
    await db.refresh(api_token)
    
    # Log token update for audit
    logger.info(f"API token partially updated: user={context.user.email}, org={context.organization.name}, name={api_token.name}, id={token_id}, fields={updated_fields}")
    
    # Return token in standard format
    return APITokenListItem(
        id=api_token.id,
        name=api_token.name,
        permissions=api_token.permissions or [],
        created_at=api_token.created_at,
        updated_at=api_token.updated_at,
        expires_at=api_token.expires_at,
        last_used_at=api_token.last_used_at,
        is_active=api_token.is_active,
        is_expired=api_token.is_expired,
        organization_id=context.organization.id,
        organization_name=context.organization.name
    )


@router.delete("/{token_id}", response_model=APITokenRevokeResponse)
async def delete_api_token(
    token_id: UUID,
    context: OrganizationContext = Depends(get_organization_context),
    db: AsyncSession = Depends(get_db_session)
):
    """Delete an API token (revoke and permanently remove from database)"""
    
    # Get token and verify ownership
    result = await db.execute(
        select(APIToken).where(
            and_(
                APIToken.id == token_id,
                APIToken.user_id == context.user.id,
                APIToken.organization_id == context.organization.id
            )
        )
    )
    
    api_token = result.scalar_one_or_none()
    if not api_token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API token not found"
        )
    
    # Log token deletion for audit (before deletion)
    token_name = api_token.name
    deleted_at = datetime.now(timezone.utc)
    logger.info(f"API token deleted: user={context.user.email}, org={context.organization.name}, name={token_name}, id={token_id}")
    
    # Delete the token from database (this also revokes it)
    await db.delete(api_token)
    await db.commit()
    
    return APITokenRevokeResponse(
        message=f"API token '{token_name}' has been deleted",
        id=token_id,
        revoked_at=deleted_at
    )


@router.get("/{token_id}", response_model=APITokenListItem)
async def get_api_token(
    token_id: UUID,
    context: OrganizationContext = Depends(get_organization_context),
    db: AsyncSession = Depends(get_db_session)
):
    """Get details of a specific API token"""
    
    # Get token and verify ownership
    result = await db.execute(
        select(APIToken).where(
            and_(
                APIToken.id == token_id,
                APIToken.user_id == context.user.id,
                APIToken.organization_id == context.organization.id
            )
        )
    )
    
    api_token = result.scalar_one_or_none()
    if not api_token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API token not found"
        )
    
    return APITokenListItem(
        id=api_token.id,
        name=api_token.name,
        permissions=api_token.permissions or [],
        created_at=api_token.created_at,
        updated_at=api_token.updated_at,
        expires_at=api_token.expires_at,
        last_used_at=api_token.last_used_at,
        is_active=api_token.is_active,
        is_expired=api_token.is_expired,
        organization_id=context.organization.id,
        organization_name=context.organization.name
    )