#!/usr/bin/env python3
"""
Member Management API endpoints
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db_session
from app.dependencies import get_current_user
from app.models.user import User
from app.models.organization import Organization
from app.models.organization_invitation import OrganizationRole
from app.services.member_management_service import MemberManagementService
from app.schemas.user import UserResponse
from app.schemas.member_management import (
    MemberListParams,
    MemberInviteRequest,
    MemberInviteResponse,
    MemberRoleUpdateRequest,
    UserDeleteRequest,
    OrganizationMemberStatsResponse,
    MemberManagementError
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/organizations")
member_service = MemberManagementService()


async def build_user_response(user: User, db: AsyncSession) -> UserResponse:
    """Build standardized UserResponse Pydantic object"""
    # Load organization data if user has one
    organization = None
    if user.organization_id:
        org_result = await db.execute(
            select(Organization).where(Organization.id == user.organization_id)
        )
        organization = org_result.scalar_one_or_none()
    
    return UserResponse(
        id=user.id,
        created_at=user.created_at,
        updated_at=user.updated_at,
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        role=user.organization_role.value if user.organization_role else None,
        is_active=user.is_active,
        timezone=user.timezone,
        language=user.language,
        preferences=user.preferences,
        is_verified=user.is_verified,
        last_login_at=user.last_login_at,
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


@router.get("/{org_id}/members")
@router.get("/{org_id}/members/")
async def list_organization_members(
    org_id: UUID,
    role: Optional[str] = Query(None, description="Filter by role (admin, member)"),
    active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Results per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get all members of an organization.
    
    - **org_id**: Organization ID
    - **role**: Filter by role (admin, member) - optional
    - **active**: Filter by active status - optional
    - **page**: Page number for pagination
    - **limit**: Results per page (max 100)
    - Requires: User must be a member of the organization
    """
    try:
        # Verify user is member of the organization
        if current_user.organization_id != org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view members of your own organization"
            )
        
        # Parse role filter
        role_filter = None
        if role:
            try:
                role_filter = OrganizationRole(role)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid role. Must be one of: {[r.value for r in OrganizationRole]}"
                )
        
        # Calculate offset for pagination
        offset = (page - 1) * limit
        
        # Get members
        members, total = await member_service.get_organization_members(
            db=db,
            organization_id=org_id,
            role_filter=role_filter,
            active_filter=active,
            offset=offset,
            limit=limit
        )
        
        # Convert to response format (same as /auth/me endpoint)
        member_responses = []
        for member in members:
            member_response = await build_user_response(member, db)
            member_responses.append(member_response)
        
        return {
            "data": member_responses,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit if limit > 0 else 0
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing members for organization {org_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve organization members"
        )


@router.post("/{org_id}/members/invite", response_model=MemberInviteResponse)
async def invite_organization_member(
    org_id: UUID,
    invite_request: MemberInviteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Invite a new member to the organization.
    
    - **org_id**: Organization ID
    - **email**: Email address to invite
    - **role**: Role to assign (admin, member)
    - **send_email**: Whether to send invitation email
    - **message**: Optional custom message
    - Requires: User must be an admin of the organization
    """
    try:
        # Create invitation
        invitation = await member_service.create_invitation(
            db=db,
            organization_id=org_id,
            email=invite_request.email,
            role=invite_request.role,
            admin_user_id=current_user.id,
            message=invite_request.message
        )
        
        # Generate invitation URL
        invitation_url = f"/invitations/accept/{invitation.invitation_token}"
        
        # TODO: Send email if send_email is True
        if invite_request.send_email:
            # Email sending would be handled by background task
            pass
        
        return MemberInviteResponse(
            invitation_id=invitation.id,
            email=invitation.email,
            role=invitation.role,
            invitation_url=invitation_url,
            expires_at=invitation.expires_at,
            message=invitation.message
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
        logger.error(f"Error inviting member to organization {org_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send invitation"
        )


@router.put("/{org_id}/members/{user_id}/role", status_code=status.HTTP_200_OK)
async def update_member_role(
    org_id: UUID,
    user_id: UUID,
    role_update: MemberRoleUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Update member's role in the organization.
    
    - **org_id**: Organization ID
    - **user_id**: User ID to update
    - **role**: New role (admin, member)
    - Requires: User must be an admin of the organization
    - Restriction: Cannot change own role
    """
    try:
        success = await member_service.update_member_role(
            db=db,
            organization_id=org_id,
            user_id=user_id,
            new_role=role_update.role,
            admin_user_id=current_user.id
        )
        
        if success:
            return {"message": "Member role updated successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update member role"
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
        logger.error(f"Error updating member role for user {user_id} in org {org_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update member role"
        )


@router.delete("/{org_id}/members/{user_id}", status_code=status.HTTP_200_OK)
async def remove_organization_member(
    org_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Remove member from organization.
    
    - **org_id**: Organization ID
    - **user_id**: User ID to remove
    - Requires: User must be an admin of the organization
    - Business Rules:
      - Cannot delete user if they are the only member
      - If user being deleted is Admin and only one admin remains, 
        remaining member becomes Admin
    """
    try:
        success = await member_service.remove_member(
            db=db,
            organization_id=org_id,
            user_id=user_id,
            admin_user_id=current_user.id
        )
        
        if success:
            return {"message": "Member removed from organization successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to remove member from organization"
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
        logger.error(f"Error removing member {user_id} from org {org_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove member from organization"
        )


@router.get("/{org_id}/members/stats", response_model=OrganizationMemberStatsResponse)
async def get_organization_member_stats(
    org_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get organization member statistics.
    
    - **org_id**: Organization ID
    - Returns: Member counts, admin counts, pending invitations
    - Requires: User must be a member of the organization
    """
    try:
        # Verify user is member of the organization
        if current_user.organization_id != org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view stats for your own organization"
            )
        
        stats = await member_service.get_organization_member_stats(db, org_id)
        
        return OrganizationMemberStatsResponse(**stats)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting member stats for organization {org_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve member statistics"
        )


# User management endpoints

@router.delete("/users/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user_account(
    user_id: UUID,
    delete_request: UserDeleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Delete user account entirely.
    
    - **user_id**: User ID to delete
    - **delete_organization**: Whether to delete organization if user is the only member
    - **reason**: Optional reason for deletion
    - Requires: User must be admin or the user being deleted
    - Business Rules:
      - If user is only member of organization, must provide delete_organization=true
      - If user is Admin and other members exist, one remaining member is auto-promoted to Admin
    """
    try:
        # Check permissions - user can delete themselves or admin can delete others
        if current_user.id != user_id:
            if not current_user.is_organization_admin():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions to delete user"
                )
            
            # Admin can only delete users in their organization
            target_user = await db.get(User, user_id)
            if not target_user or target_user.organization_id != current_user.organization_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found in your organization"
                )
        
        # Get the target user
        target_user = await db.get(User, user_id)
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if this is the last member and handle organization deletion
        if target_user.organization_id:
            stats = await member_service.get_organization_member_stats(
                db, target_user.organization_id
            )
            
            if stats["total_members"] <= 1:
                if not delete_request.delete_organization:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "message": "User is the only member of the organization",
                            "action_required": "Set delete_organization=true to delete both user and organization"
                        }
                    )
                
                # Delete organization along with user
                organization = await db.get(Organization, target_user.organization_id)
                if organization:
                    organization.soft_delete()
        
        # Remove user from organization (handles auto-admin promotion if needed)
        if target_user.organization_id and target_user.organization_role:
            await member_service.remove_member(
                db=db,
                organization_id=target_user.organization_id,
                user_id=user_id,
                admin_user_id=current_user.id
            )
        
        # Soft delete the user
        target_user.soft_delete()
        await db.commit()
        
        return {
            "message": "User account deleted successfully",
            "organization_deleted": delete_request.delete_organization
        }
        
    except HTTPException:
        raise
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
        logger.error(f"Error deleting user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user account"
        )