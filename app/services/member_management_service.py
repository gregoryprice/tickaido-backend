#!/usr/bin/env python3
"""
Member Management Service - Business logic for organization member management,
invitations, and organization discovery
"""

import secrets
import hashlib
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
import re

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from app.models.user import User, UserRole
from app.models.organization import Organization
from app.models.organization_invitation import (
    OrganizationInvitation, 
    OrganizationRole, 
    InvitationStatus
)


class MemberManagementService:
    """
    Service for managing organization members, invitations, and domain discovery
    """
    
    def __init__(self):
        """Initialize member management service"""
        self.invitation_expiry_days = 7
    
    # Domain and Email Utilities
    
    def extract_domain_from_email(self, email: str) -> str:
        """
        Extract domain from email address.
        
        Args:
            email: Email address
            
        Returns:
            str: Domain part of email
        """
        if not email or not isinstance(email, str):
            raise ValueError("Invalid email format")
        
        email = email.strip()
        if not email or '@' not in email:
            raise ValueError("Invalid email format")
        
        parts = email.split('@')
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError("Invalid email format")
        
        domain = parts[1].lower().strip()
        if not domain:
            raise ValueError("Invalid email format")
            
        return domain
    
    async def find_organizations_by_domain(
        self, 
        db: AsyncSession, 
        domain: str
    ) -> List[Organization]:
        """
        Find organizations matching the given domain.
        
        Args:
            db: Database session
            domain: Domain to search for
            
        Returns:
            List of organizations with matching domain
        """
        domain = domain.lower().strip()
        
        query = select(Organization).where(
            and_(
                Organization.domain == domain,
                Organization.is_enabled == True,
                Organization.is_deleted == False
            )
        ).order_by(Organization.created_at.desc())
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def suggest_organization_for_email(
        self, 
        db: AsyncSession, 
        email: str
    ) -> Optional[Organization]:
        """
        Suggest organization for user based on email domain.
        
        Args:
            db: Database session
            email: User's email address
            
        Returns:
            Organization if domain match found, None otherwise
        """
        try:
            domain = self.extract_domain_from_email(email)
            organizations = await self.find_organizations_by_domain(db, domain)
            
            # Return the most recently created organization for this domain
            return organizations[0] if organizations else None
        except ValueError:
            return None
    
    # Member Management Operations
    
    async def get_organization_members(
        self,
        db: AsyncSession,
        organization_id: UUID,
        role_filter: Optional[OrganizationRole] = None,
        active_filter: Optional[bool] = None,
        offset: int = 0,
        limit: int = 50
    ) -> Tuple[List[User], int]:
        """
        Get members of an organization with filtering and pagination.
        
        Args:
            db: Database session
            organization_id: Organization ID
            role_filter: Filter by organization role
            active_filter: Filter by active status
            offset: Pagination offset
            limit: Results per page
            
        Returns:
            Tuple of (members list, total count)
        """
        # Base query
        query = select(User).where(
            and_(
                User.organization_id == organization_id,
                User.organization_role.is_not(None),  # Only users with actual organization roles
                User.is_deleted == False
            )
        ).options(
            selectinload(User.invited_by),
            selectinload(User.organization)
        )
        
        count_query = select(func.count(User.id)).where(
            and_(
                User.organization_id == organization_id,
                User.organization_role.is_not(None),  # Only users with actual organization roles
                User.is_deleted == False
            )
        )
        
        # Apply filters
        filters = []
        
        if role_filter is not None:
            filters.append(User.organization_role == role_filter)
        
        if active_filter is not None:
            filters.append(User.is_active == active_filter)
        
        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))
        
        # Apply ordering and pagination
        query = query.order_by(
            # Admins first, then by join date
            desc(User.organization_role == OrganizationRole.ADMIN),
            User.joined_organization_at.desc().nullslast(),
            User.created_at.desc()
        ).offset(offset).limit(limit)
        
        # Execute queries
        members_result = await db.execute(query)
        count_result = await db.execute(count_query)
        
        members = list(members_result.scalars().all())
        total = count_result.scalar() or 0
        
        return members, total
    
    async def update_member_role(
        self,
        db: AsyncSession,
        organization_id: UUID,
        user_id: UUID,
        new_role: OrganizationRole,
        admin_user_id: UUID
    ) -> bool:
        """
        Update member's organization role.
        
        Args:
            db: Database session
            organization_id: Organization ID
            user_id: User ID to update
            new_role: New organization role
            admin_user_id: ID of admin performing the action
            
        Returns:
            bool: True if successful
            
        Raises:
            PermissionError: If admin doesn't have permission
            ValueError: If user not found or validation fails
        """
        # Verify admin permissions
        admin_user = await db.get(User, admin_user_id)
        if not admin_user or not admin_user.is_organization_admin():
            raise PermissionError("Only organization admins can change member roles")
        
        if admin_user.organization_id != organization_id:
            raise PermissionError("Admin can only manage members of their own organization")
        
        # Prevent self-role modification
        if admin_user_id == user_id:
            raise ValueError("Users cannot modify their own role")
        
        # Get target user
        target_user = await db.get(User, user_id)
        if not target_user or target_user.organization_id != organization_id:
            raise ValueError("User not found in organization")
        
        # Update role
        target_user.organization_role = new_role
        await db.commit()
        
        return True
    
    async def remove_member(
        self,
        db: AsyncSession,
        organization_id: UUID,
        user_id: UUID,
        admin_user_id: UUID
    ) -> bool:
        """
        Remove member from organization with auto-admin promotion logic.
        
        Args:
            db: Database session
            organization_id: Organization ID
            user_id: User ID to remove
            admin_user_id: ID of admin performing the action
            
        Returns:
            bool: True if successful
            
        Raises:
            PermissionError: If admin doesn't have permission
            ValueError: If removal would violate business rules
        """
        # Verify admin permissions
        admin_user = await db.get(User, admin_user_id)
        if not admin_user or not admin_user.is_organization_admin():
            raise PermissionError("Only organization admins can remove members")
        
        if admin_user.organization_id != organization_id:
            raise PermissionError("Admin can only manage members of their own organization")
        
        # Get target user
        target_user = await db.get(User, user_id)
        if not target_user or target_user.organization_id != organization_id:
            raise ValueError("User not found in organization")
        
        # Check if this would leave organization empty
        member_count_query = select(func.count(User.id)).where(
            and_(
                User.organization_id == organization_id,
                User.organization_role.is_not(None),  # Only actual organization members
                User.is_active == True,
                User.is_deleted == False
            )
        )
        total_members = (await db.execute(member_count_query)).scalar() or 0
        
        if total_members <= 1:
            raise ValueError("Cannot delete last member of organization. Delete organization instead.")
        
        # If removing an admin, check admin count
        if target_user.organization_role == OrganizationRole.ADMIN:
            admin_count_query = select(func.count(User.id)).where(
                and_(
                    User.organization_id == organization_id,
                    User.organization_role == OrganizationRole.ADMIN,
                    User.is_active == True,
                    User.is_deleted == False
                )
            )
            admin_count = (await db.execute(admin_count_query)).scalar() or 0
            
            # If this is the last admin, promote the oldest member
            if admin_count <= 1:
                await self._auto_promote_member_to_admin(db, organization_id, exclude_user_id=user_id)
        
        # Remove user from organization
        target_user.leave_organization()
        await db.commit()
        
        return True
    
    async def _auto_promote_member_to_admin(
        self,
        db: AsyncSession,
        organization_id: UUID,
        exclude_user_id: Optional[UUID] = None
    ) -> Optional[User]:
        """
        Auto-promote oldest member to admin when no admins remain.
        
        Args:
            db: Database session
            organization_id: Organization ID
            exclude_user_id: User ID to exclude from promotion
            
        Returns:
            Promoted user or None if no eligible members
        """
        query = select(User).where(
            and_(
                User.organization_id == organization_id,
                User.organization_role == OrganizationRole.MEMBER,
                User.is_active == True,
                User.is_deleted == False
            )
        )
        
        if exclude_user_id:
            query = query.where(User.id != exclude_user_id)
        
        # Order by join date (oldest first)
        query = query.order_by(
            User.joined_organization_at.asc().nullslast(),
            User.created_at.asc()
        ).limit(1)
        
        result = await db.execute(query)
        member_to_promote = result.scalar_one_or_none()
        
        if member_to_promote:
            member_to_promote.promote_to_admin()
            await db.commit()
        
        return member_to_promote
    
    # Invitation Management
    
    async def create_invitation(
        self,
        db: AsyncSession,
        organization_id: UUID,
        email: str,
        role: OrganizationRole,
        admin_user_id: UUID,
        message: Optional[str] = None
    ) -> OrganizationInvitation:
        """
        Create organization invitation.
        
        Args:
            db: Database session
            organization_id: Organization ID
            email: Email to invite
            role: Role to assign
            admin_user_id: ID of admin sending invitation
            message: Custom invitation message
            
        Returns:
            Created invitation
            
        Raises:
            PermissionError: If admin doesn't have permission
            ValueError: If invitation already exists or validation fails
        """
        # Verify admin user exists and belongs to the organization
        admin_user = await db.get(User, admin_user_id)
        if not admin_user:
            raise ValueError("Admin user not found")
        
        if admin_user.organization_id != organization_id:
            raise PermissionError("Admin can only invite to their own organization")
        
        # Validate email
        email = email.lower().strip()
        if not email or '@' not in email:
            raise ValueError("Invalid email address")
        
        # Check if user already exists in organization
        existing_user = await self._get_user_by_email(db, email)
        if existing_user and existing_user.organization_id == organization_id:
            raise ValueError("User is already a member of this organization")
        
        # Check for duplicate pending invitation
        existing_invitation_query = select(OrganizationInvitation).where(
            and_(
                OrganizationInvitation.organization_id == organization_id,
                OrganizationInvitation.email == email,
                OrganizationInvitation.status == InvitationStatus.PENDING,
                OrganizationInvitation.is_deleted == False
            )
        )
        
        existing_invitation = (await db.execute(existing_invitation_query)).scalar_one_or_none()
        if existing_invitation and not existing_invitation.is_expired:
            raise ValueError("Pending invitation already exists for this email")
        
        # Generate secure invitation token
        invitation_token = self._generate_invitation_token()
        
        # Create invitation
        invitation = OrganizationInvitation(
            organization_id=organization_id,
            email=email,
            role=role,
            invited_by_id=admin_user_id,
            invitation_token=invitation_token,
            expires_at=datetime.now(timezone.utc) + timedelta(days=self.invitation_expiry_days),
            message=message
        )
        
        db.add(invitation)
        await db.commit()
        await db.refresh(invitation)
        
        return invitation
    
    async def get_invitation_by_token(
        self,
        db: AsyncSession,
        token: str
    ) -> Optional[OrganizationInvitation]:
        """
        Get invitation by token.
        
        Args:
            db: Database session
            token: Invitation token
            
        Returns:
            Invitation if found and valid
        """
        query = select(OrganizationInvitation).where(
            and_(
                OrganizationInvitation.invitation_token == token,
                OrganizationInvitation.is_deleted == False
            )
        ).options(
            selectinload(OrganizationInvitation.organization),
            selectinload(OrganizationInvitation.invited_by)
        )
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def accept_invitation(
        self,
        db: AsyncSession,
        invitation_token: str,
        user_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[User, OrganizationInvitation]:
        """
        Accept invitation and create/update user account.
        
        Args:
            db: Database session
            invitation_token: Invitation token
            user_data: User creation data (for new users)
            
        Returns:
            Tuple of (user, invitation)
            
        Raises:
            ValueError: If invitation is invalid or expired
        """
        invitation = await self.get_invitation_by_token(db, invitation_token)
        if not invitation:
            raise ValueError("Invalid invitation token")
        
        if not invitation.is_pending:
            raise ValueError("Invitation is no longer valid")
        
        if invitation.is_expired:
            invitation.expire()
            await db.commit()
            raise ValueError("Invitation has expired")
        
        # Check if user already exists
        user = await self._get_user_by_email(db, invitation.email)
        
        if user:
            # Existing user - add to organization
            if user.organization_id:
                raise ValueError("User is already a member of another organization")
            
            # Join organization
            user.join_organization(
                invitation.organization_id,
                invitation.role,
                invitation.invited_by_id
            )
            user.invited_at = invitation.created_at
        else:
            # New user - create account
            if not user_data:
                raise ValueError("User data required for new user registration")
            
            from app.services.user_service import UserService
            user_service = UserService()
            
            # Create user account
            user = User(
                email=invitation.email,
                full_name=user_data.get('full_name'),
                password_hash=user_service._hash_password(user_data['password']) if user_data.get('password') else None,
                organization_id=invitation.organization_id,
                organization_role=invitation.role,
                invited_by_id=invitation.invited_by_id,
                invited_at=invitation.created_at,
                joined_organization_at=datetime.now(timezone.utc),
                is_active=True,
                is_verified=True,  # Auto-verify invited users
                role=UserRole.USER
            )
            
            db.add(user)
        
        # Mark invitation as accepted
        invitation.accept()
        
        await db.commit()
        await db.refresh(user)
        await db.refresh(invitation)
        
        return user, invitation
    
    async def decline_invitation(
        self,
        db: AsyncSession,
        invitation_token: str
    ) -> OrganizationInvitation:
        """
        Decline invitation.
        
        Args:
            db: Database session
            invitation_token: Invitation token
            
        Returns:
            Updated invitation
            
        Raises:
            ValueError: If invitation is invalid
        """
        invitation = await self.get_invitation_by_token(db, invitation_token)
        if not invitation:
            raise ValueError("Invalid invitation token")
        
        if not invitation.is_pending:
            raise ValueError("Invitation is no longer valid")
        
        invitation.decline()
        await db.commit()
        await db.refresh(invitation)
        
        return invitation
    
    async def cancel_invitation(
        self,
        db: AsyncSession,
        invitation_id: UUID,
        admin_user_id: UUID
    ) -> OrganizationInvitation:
        """
        Cancel pending invitation.
        
        Args:
            db: Database session
            invitation_id: Invitation ID
            admin_user_id: ID of admin canceling invitation
            
        Returns:
            Updated invitation
            
        Raises:
            PermissionError: If admin doesn't have permission
            ValueError: If invitation is invalid
        """
        invitation = await db.get(OrganizationInvitation, invitation_id)
        if not invitation:
            raise ValueError("Invitation not found")
        
        # Verify admin permissions
        admin_user = await db.get(User, admin_user_id)
        if (not admin_user or 
            not admin_user.is_organization_admin() or
            admin_user.organization_id != invitation.organization_id):
            raise PermissionError("Only organization admins can cancel invitations")
        
        if not invitation.is_pending:
            raise ValueError("Can only cancel pending invitations")
        
        invitation.cancel()
        await db.commit()
        await db.refresh(invitation)
        
        return invitation
    
    async def get_organization_invitations(
        self,
        db: AsyncSession,
        organization_id: UUID,
        status_filter: Optional[InvitationStatus] = None,
        offset: int = 0,
        limit: int = 50
    ) -> Tuple[List[OrganizationInvitation], int]:
        """
        Get organization invitations with filtering and pagination.
        
        Args:
            db: Database session
            organization_id: Organization ID
            status_filter: Filter by status
            offset: Pagination offset
            limit: Results per page
            
        Returns:
            Tuple of (invitations list, total count)
        """
        query = select(OrganizationInvitation).where(
            and_(
                OrganizationInvitation.organization_id == organization_id,
                OrganizationInvitation.is_deleted == False
            )
        ).options(
            selectinload(OrganizationInvitation.invited_by)
        )
        
        count_query = select(func.count(OrganizationInvitation.id)).where(
            and_(
                OrganizationInvitation.organization_id == organization_id,
                OrganizationInvitation.is_deleted == False
            )
        )
        
        # Apply filters
        if status_filter is not None:
            query = query.where(OrganizationInvitation.status == status_filter)
            count_query = count_query.where(OrganizationInvitation.status == status_filter)
        
        # Apply ordering and pagination
        query = query.order_by(
            OrganizationInvitation.created_at.desc()
        ).offset(offset).limit(limit)
        
        # Execute queries
        invitations_result = await db.execute(query)
        count_result = await db.execute(count_query)
        
        invitations = list(invitations_result.scalars().all())
        total = count_result.scalar() or 0
        
        return invitations, total
    
    # Utility Methods
    
    def _generate_invitation_token(self) -> str:
        """Generate secure invitation token"""
        return secrets.token_urlsafe(32)
    
    async def _get_user_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """Get user by email address"""
        query = select(User).where(
            and_(
                User.email == email.lower(),
                User.is_deleted == False
            )
        )
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    # Organization Statistics
    
    async def get_organization_member_stats(
        self,
        db: AsyncSession,
        organization_id: UUID
    ) -> Dict[str, Any]:
        """
        Get organization member statistics.
        
        Args:
            db: Database session
            organization_id: Organization ID
            
        Returns:
            Statistics dictionary
        """
        # Member counts by role
        admin_count_query = select(func.count(User.id)).where(
            and_(
                User.organization_id == organization_id,
                User.organization_role == OrganizationRole.ADMIN,
                User.is_active == True,
                User.is_deleted == False
            )
        )
        
        member_count_query = select(func.count(User.id)).where(
            and_(
                User.organization_id == organization_id,
                User.organization_role == OrganizationRole.MEMBER,
                User.is_active == True,
                User.is_deleted == False
            )
        )
        
        # Pending invitations
        pending_invitations_query = select(func.count(OrganizationInvitation.id)).where(
            and_(
                OrganizationInvitation.organization_id == organization_id,
                OrganizationInvitation.status == InvitationStatus.PENDING,
                OrganizationInvitation.is_deleted == False
            )
        )
        
        # Execute queries
        admin_count = (await db.execute(admin_count_query)).scalar() or 0
        member_count = (await db.execute(member_count_query)).scalar() or 0
        pending_invitations = (await db.execute(pending_invitations_query)).scalar() or 0
        
        return {
            "total_members": admin_count + member_count,
            "admin_count": admin_count,
            "member_count": member_count,
            "pending_invitations": pending_invitations,
            "has_admin": admin_count > 0
        }