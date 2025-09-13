#!/usr/bin/env python3
"""
Invitation Management API endpoints
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.dependencies import get_current_user
from app.models.user import User
from app.models.organization_invitation import OrganizationInvitation, InvitationStatus
from app.services.member_management_service import MemberManagementService
from app.services.user_service import UserService
from app.schemas.member_management import (
    InvitationResponse,
    InvitationDetailsResponse,
    InvitationAcceptRequest,
    InvitationAcceptResponse,
    InvitationListParams,
    InvitationsListResponse,
    MemberInviteRequest,
    MemberManagementError,
    OrganizationRoleSchema,
    InvitationStatusSchema
)

logger = logging.getLogger(__name__)
router = APIRouter()
member_service = MemberManagementService()
user_service = UserService()

# Direct invitation endpoints expected by tests

@router.delete("/invitations/{invitation_id}", status_code=status.HTTP_200_OK)
async def revoke_invitation_by_id(
    invitation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Revoke/cancel invitation by ID.
    
    - **invitation_id**: Invitation ID to cancel
    - Requires: User must be an admin of the organization
    """
    try:
        if not current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must be part of an organization"
            )
        
        if not current_user.is_organization_admin():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organization admins can cancel invitations"
            )
        
        # Cancel the invitation
        invitation = await member_service.cancel_invitation(
            db=db,
            invitation_id=invitation_id,
            admin_user_id=current_user.id
        )
        
        return {
            "message": "Invitation cancelled successfully",
            "invitation_id": str(invitation.id),
            "cancelled_at": invitation.cancelled_at.isoformat() if invitation.cancelled_at else None
        }
        
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error cancelling invitation {invitation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel invitation"
        )


@router.post("/invitations", response_model=InvitationResponse)
async def create_organization_invitation(
    invite_request: MemberInviteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Create invitation for current user's organization.
    
    - **email**: Email address to invite
    - **role**: Role to assign (admin, member)
    - **send_email**: Whether to send invitation email
    - **message**: Optional custom message
    - Requires: User must be an admin of their organization
    """
    try:
        if not current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must be part of an organization to send invitations"
            )
        
        # Check admin permissions before calling service
        if not current_user.is_organization_admin():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organization admins can invite members"
            )
        
        # Convert schema enum to model enum
        from app.models.organization_invitation import OrganizationRole
        role_value = invite_request.role.value if hasattr(invite_request.role, 'value') else str(invite_request.role)
        model_role = OrganizationRole(role_value)
        
        # Create invitation
        invitation = await member_service.create_invitation(
            db=db,
            organization_id=current_user.organization_id,
            email=invite_request.email,
            role=model_role,
            admin_user_id=current_user.id,
            message=invite_request.message
        )
        
        return InvitationResponse(
            id=invitation.id,
            created_at=invitation.created_at,
            updated_at=invitation.updated_at,
            organization_id=invitation.organization_id,
            email=invitation.email,
            role=OrganizationRoleSchema(invitation.role.value),
            inviter_id=current_user.id,
            invitation_token=invitation.invitation_token,
            token=invitation.invitation_token,  # Alias for compatibility
            status=InvitationStatusSchema(invitation.status.value),
            expires_at=invitation.expires_at,
            accepted_at=invitation.accepted_at,
            declined_at=invitation.declined_at,
            cancelled_at=invitation.cancelled_at,
            message=invitation.message,
            is_expired=invitation.is_expired,
            is_pending=invitation.is_pending
        )
        
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating invitation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send invitation"
        )


@router.get("/invitations", response_model=InvitationsListResponse)
async def list_current_user_invitations(
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Results per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    List invitations for current user's organization.
    
    - **status**: Filter by status (pending, accepted, declined, expired, cancelled) - optional
    - **page**: Page number for pagination
    - **limit**: Results per page (max 100)
    - Requires: User must be an admin of their organization
    """
    try:
        if not current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must be part of an organization"
            )
        
        # Verify admin permissions
        if not current_user.is_organization_admin():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organization admins can view invitations"
            )
        
        # Parse status filter
        parsed_status = None
        if status_filter:
            try:
                parsed_status = InvitationStatus(status_filter)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status. Must be one of: {[s.value for s in InvitationStatus]}"
                )
        
        # Calculate offset
        offset = (page - 1) * limit
        
        # Get invitations
        invitations, total = await member_service.get_organization_invitations(
            db=db,
            organization_id=current_user.organization_id,
            status_filter=parsed_status,
            offset=offset,
            limit=limit
        )
        
        # Convert to response format
        invitation_responses = []
        for invitation in invitations:
            invitation_responses.append(InvitationResponse(
                id=invitation.id,
                created_at=invitation.created_at,
                updated_at=invitation.updated_at,
                organization_id=invitation.organization_id,
                email=invitation.email,
                role=OrganizationRoleSchema(invitation.role.value),
                inviter_id=invitation.invited_by_id,
                invitation_token=invitation.invitation_token,
                token=invitation.invitation_token,
                status=InvitationStatusSchema(invitation.status.value),
                expires_at=invitation.expires_at,
                accepted_at=invitation.accepted_at,
                declined_at=invitation.declined_at,
                cancelled_at=invitation.cancelled_at,
                message=invitation.message,
                is_expired=invitation.is_expired,
                is_pending=invitation.is_pending
            ))
        
        return InvitationsListResponse(
            data=invitation_responses,
            pagination={
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit if limit > 0 else 0
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing invitations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve invitations"
        )


# Public invitation endpoints (no auth required)

@router.get("/invitations/token/{token}", response_model=InvitationDetailsResponse)
async def get_invitation_by_token_alias(
    token: str,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get invitation details by token (alias endpoint).
    
    **Public endpoint - No authentication required**
    
    - **token**: Invitation token
    - Alias for /invitations/{token} endpoint
    """
    return await get_invitation_details(token, db)


@router.get("/invitations/{invitation_id}", response_model=InvitationDetailsResponse) 
async def get_invitation_by_id(
    invitation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get invitation details by ID.
    
    **Requires authentication**
    
    - **invitation_id**: Invitation ID (UUID format)
    - Returns invitation details for the user's organization
    """
    try:
        if not current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must be part of an organization"
            )
        
        # Load invitation with relationships
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        stmt = select(OrganizationInvitation).options(
            selectinload(OrganizationInvitation.invited_by),
            selectinload(OrganizationInvitation.organization)
        ).where(OrganizationInvitation.id == invitation_id)
        
        result = await db.execute(stmt)
        invitation = result.scalar_one_or_none()
        
        if not invitation or invitation.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation not found"
            )
        
        # Prepare organization info
        organization_info = {
            "id": str(invitation.organization.id),
            "name": invitation.organization.name,
            "domain": invitation.organization.domain,
            "display_name": invitation.organization.effective_display_name,
            "logo_url": invitation.organization.logo_url
        }
        
        # Return using same format as get_invitation_details
        return InvitationDetailsResponse(
            id=invitation.id,
            created_at=invitation.created_at,
            updated_at=invitation.updated_at,
            organization_id=invitation.organization_id,
            email=invitation.email,
            role=OrganizationRoleSchema(invitation.role.value),
            inviter_id=invitation.invited_by_id,
            invitation_token=invitation.invitation_token,
            token=invitation.invitation_token,
            status=InvitationStatusSchema(invitation.status.value),
            expires_at=invitation.expires_at,
            accepted_at=invitation.accepted_at,
            declined_at=invitation.declined_at,
            cancelled_at=invitation.cancelled_at,
            message=invitation.message,
            is_expired=invitation.is_expired,
            is_pending=invitation.is_pending,
            organization=organization_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting invitation by ID {invitation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve invitation"
        )


@router.get("/invitations/{token}", response_model=InvitationDetailsResponse)
async def get_invitation_details(
    token: str,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get invitation details by token.
    
    **Public endpoint - No authentication required**
    
    - **token**: Invitation token
    - Returns invitation details including organization information
    - Used to display invitation details before acceptance/decline
    """
    try:
        invitation = await member_service.get_invitation_by_token(db, token)
        
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation not found or invalid"
            )
        
        # Prepare organization info
        organization_info = {
            "id": str(invitation.organization.id),
            "name": invitation.organization.name,
            "domain": invitation.organization.domain,
            "display_name": invitation.organization.effective_display_name,
            "logo_url": invitation.organization.logo_url
        }
        
        return InvitationDetailsResponse(
            id=invitation.id,
            created_at=invitation.created_at,
            updated_at=invitation.updated_at,
            organization_id=invitation.organization_id,
            email=invitation.email,
            role=OrganizationRoleSchema(invitation.role.value),
            inviter_id=invitation.invited_by_id,
            invitation_token=invitation.invitation_token,
            token=invitation.invitation_token,
            status=InvitationStatusSchema(invitation.status.value),
            expires_at=invitation.expires_at,
            accepted_at=invitation.accepted_at,
            declined_at=invitation.declined_at,
            cancelled_at=invitation.cancelled_at,
            message=invitation.message,
            is_expired=invitation.is_expired,
            is_pending=invitation.is_pending,
            organization=organization_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting invitation details for token {token}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve invitation details"
        )


@router.post("/invitations/{token}/accept", response_model=InvitationAcceptResponse)
async def accept_invitation(
    token: str,
    accept_request: InvitationAcceptRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Accept invitation and create/link user account.
    
    **Public endpoint - No authentication required**
    
    - **token**: Invitation token
    - **password**: Password for new user account (required for new users)
    - **full_name**: Full name for new user (required for new users)
    - Creates user account if user doesn't exist
    - Joins existing user to organization if user exists
    - Returns user info and JWT token for immediate login
    """
    try:
        # Prepare user data for new user creation if needed
        user_data = None
        if accept_request.password:
            user_data = {
                "password": accept_request.password,
                "full_name": accept_request.full_name
            }
        
        # Accept the invitation
        user, invitation = await member_service.accept_invitation(
            db=db,
            invitation_token=token,
            user_data=user_data
        )
        
        # Determine if this was a new user
        is_new_user = user_data is not None
        
        # Prepare response data
        user_info = {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "organization_role": user.organization_role.value if user.organization_role else None,
            "is_active": user.is_active,
            "is_verified": user.is_verified
        }
        
        organization_info = {
            "id": str(user.organization.id),
            "name": user.organization.name,
            "domain": user.organization.domain,
            "display_name": user.organization.effective_display_name
        }
        
        # Generate access token for immediate login
        access_token = None
        if is_new_user or user.can_login:
            # Create login token
            token_data = {
                "sub": str(user.id),
                "email": user.email,
                "role": user.role.value if user.role else "user"
            }
            access_token = user_service._create_access_token(token_data)
        
        return InvitationAcceptResponse(
            user=user_info,
            organization=organization_info,
            is_new_user=is_new_user,
            access_token=access_token
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error accepting invitation {token}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to accept invitation"
        )


@router.post("/invitations/{token}/decline", status_code=status.HTTP_200_OK)
async def decline_invitation(
    token: str,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Decline invitation.
    
    **Public endpoint - No authentication required**
    
    - **token**: Invitation token
    - Marks invitation as declined
    - Returns confirmation message
    """
    try:
        invitation = await member_service.decline_invitation(db, token)
        
        return {
            "message": "Invitation declined successfully",
            "invitation_id": str(invitation.id),
            "declined_at": invitation.declined_at
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error declining invitation {token}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to decline invitation"
        )


# Organization invitation management endpoints (auth required)

@router.get("/organizations/{org_id}/invitations", response_model=InvitationsListResponse)
async def list_organization_invitations(
    org_id: UUID,
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Results per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    List pending invitations for organization.
    
    - **org_id**: Organization ID
    - **status**: Filter by status (pending, accepted, declined, expired, cancelled) - optional
    - **page**: Page number for pagination
    - **limit**: Results per page (max 100)
    - Requires: User must be an admin of the organization
    """
    try:
        # Verify admin permissions
        if not current_user.is_organization_admin() or current_user.organization_id != org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organization admins can view invitations"
            )
        
        # Parse status filter
        parsed_status = None
        if status_filter:
            try:
                parsed_status = InvitationStatus(status_filter)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status. Must be one of: {[s.value for s in InvitationStatus]}"
                )
        
        # Calculate offset
        offset = (page - 1) * limit
        
        # Get invitations
        invitations, total = await member_service.get_organization_invitations(
            db=db,
            organization_id=org_id,
            status_filter=parsed_status,
            offset=offset,
            limit=limit
        )
        
        # Convert to response format
        invitation_responses = []
        for invitation in invitations:
            invitation_responses.append(InvitationResponse(
                id=invitation.id,
                created_at=invitation.created_at,
                updated_at=invitation.updated_at,
                organization_id=invitation.organization_id,
                email=invitation.email,
                role=OrganizationRoleSchema(invitation.role.value),
                inviter_id=invitation.invited_by_id,
                invitation_token=invitation.invitation_token,
                token=invitation.invitation_token,
                status=InvitationStatusSchema(invitation.status.value),
                expires_at=invitation.expires_at,
                accepted_at=invitation.accepted_at,
                declined_at=invitation.declined_at,
                cancelled_at=invitation.cancelled_at,
                message=invitation.message,
                is_expired=invitation.is_expired,
                is_pending=invitation.is_pending
            ))
        
        return InvitationsListResponse(
            data=invitation_responses,
            pagination={
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit if limit > 0 else 0
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing invitations for organization {org_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve invitations"
        )


@router.delete("/organizations/{org_id}/invitations/{invitation_id}", status_code=status.HTTP_200_OK)
async def cancel_organization_invitation(
    org_id: UUID,
    invitation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Cancel pending invitation.
    
    - **org_id**: Organization ID
    - **invitation_id**: Invitation ID to cancel
    - Can only cancel pending invitations
    - Requires: User must be an admin of the organization
    """
    try:
        invitation = await member_service.cancel_invitation(
            db=db,
            invitation_id=invitation_id,
            admin_user_id=current_user.id
        )
        
        return {
            "message": "Invitation cancelled successfully",
            "invitation_id": str(invitation.id),
            "cancelled_at": invitation.cancelled_at
        }
        
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error cancelling invitation {invitation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel invitation"
        )


# Invitation utility endpoints

@router.get("/invitations/{token}/status")
async def get_invitation_status(
    token: str,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get invitation status (lightweight endpoint).
    
    **Public endpoint - No authentication required**
    
    - **token**: Invitation token
    - Returns basic status information
    - Useful for quick status checks
    """
    try:
        invitation = await member_service.get_invitation_by_token(db, token)
        
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation not found"
            )
        
        return {
            "status": invitation.status.value,
            "is_expired": invitation.is_expired,
            "is_pending": invitation.is_pending,
            "expires_at": invitation.expires_at,
            "organization_name": invitation.organization.name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting invitation status for token {token}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get invitation status"
        )


@router.post("/invitations/resend/{invitation_id}", status_code=status.HTTP_200_OK)
async def resend_invitation_email(
    invitation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Resend invitation email.
    
    - **invitation_id**: Invitation ID to resend
    - Can only resend pending invitations
    - Requires: User must be an admin of the organization
    - TODO: Integrate with email sending service
    """
    try:
        invitation = await db.get(OrganizationInvitation, invitation_id)
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation not found"
            )
        
        # Verify admin permissions
        if (not current_user.is_organization_admin() or 
            current_user.organization_id != invitation.organization_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organization admins can resend invitations"
            )
        
        if not invitation.is_pending:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only resend pending invitations"
            )
        
        # TODO: Implement email sending
        # This would trigger a background task to send the invitation email
        
        return {
            "message": "Invitation email resent successfully",
            "invitation_id": str(invitation.id),
            "email": invitation.email
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resending invitation {invitation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resend invitation"
        )