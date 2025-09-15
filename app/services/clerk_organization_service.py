#!/usr/bin/env python3
"""
Clerk Organizations API integration service
"""

import logging
from typing import Optional, Dict, Any, List
from app.services.clerk_service import clerk_service

logger = logging.getLogger(__name__)


class ClerkOrganizationService:
    """Service for Clerk Organizations API integration"""
    
    def __init__(self):
        self.client = clerk_service.client
    
    async def create_organization(
        self,
        name: str,
        slug: str,
        created_by: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Create organization in Clerk"""
        if not self.client:
            logger.error("Clerk client not initialized")
            return None
            
        try:
            org = self.client.organizations.create(
                name=name,
                slug=slug,
                created_by=created_by,
                private_metadata=metadata or {}
            )
            return self._format_organization_data(org)
        except Exception as e:
            logger.error(f"Failed to create organization: {e}")
            return None
    
    async def get_organization(self, org_id: str) -> Optional[Dict[str, Any]]:
        """Get organization by ID from Clerk"""
        if not self.client:
            return None
            
        try:
            org = self.client.organizations.get(org_id)
            return self._format_organization_data(org)
        except Exception as e:
            logger.error(f"Failed to get organization {org_id}: {e}")
            return None
    
    async def update_organization(
        self,
        org_id: str,
        name: Optional[str] = None,
        slug: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update organization in Clerk"""
        if not self.client:
            return False
            
        try:
            update_data = {}
            if name:
                update_data['name'] = name
            if slug:
                update_data['slug'] = slug
            if metadata:
                update_data['private_metadata'] = metadata
            
            self.client.organizations.update(org_id, **update_data)
            return True
        except Exception as e:
            logger.error(f"Failed to update organization {org_id}: {e}")
            return False
    
    async def add_member(
        self,
        org_id: str,
        user_id: str,
        role: str = "basic_member"
    ) -> Optional[Dict[str, Any]]:
        """Add user to organization with role"""
        if not self.client:
            return None
            
        try:
            membership = self.client.organization_memberships.create(
                organization_id=org_id,
                user_id=user_id,
                role=role
            )
            return self._format_membership_data(membership)
        except Exception as e:
            logger.error(f"Failed to add member to organization: {e}")
            return None
    
    async def update_member_role(
        self,
        membership_id: str,
        role: str
    ) -> bool:
        """Update member role in organization"""
        if not self.client:
            return False
            
        try:
            self.client.organization_memberships.update(
                membership_id,
                role=role
            )
            return True
        except Exception as e:
            logger.error(f"Failed to update member role: {e}")
            return False
    
    async def remove_member(self, membership_id: str) -> bool:
        """Remove member from organization"""
        if not self.client:
            return False
            
        try:
            self.client.organization_memberships.delete(membership_id)
            return True
        except Exception as e:
            logger.error(f"Failed to remove member: {e}")
            return False
    
    async def list_members(self, org_id: str) -> List[Dict[str, Any]]:
        """List all members of organization"""
        if not self.client:
            return []
            
        try:
            response = self.client.organization_memberships.list(
                organization_id=org_id
            )
            return [self._format_membership_data(m) for m in response.data]
        except Exception as e:
            logger.error(f"Failed to list members: {e}")
            return []
    
    async def create_invitation(
        self,
        org_id: str,
        email: str,
        role: str = "basic_member",
        inviter_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Create organization invitation"""
        if not self.client:
            return None
            
        try:
            invitation = self.client.organization_invitations.create(
                organization_id=org_id,
                email_address=email,
                role=role,
                inviter_id=inviter_id
            )
            return self._format_invitation_data(invitation)
        except Exception as e:
            logger.error(f"Failed to create invitation: {e}")
            return None
    
    def _format_organization_data(self, org) -> Dict[str, Any]:
        """Format Clerk organization data"""
        return {
            'clerk_id': org.id,
            'name': org.name,
            'slug': org.slug,
            'image_url': getattr(org, 'image_url', None),
            'created_at': org.created_at,
            'updated_at': org.updated_at,
            'members_count': getattr(org, 'members_count', 0),
            'private_metadata': getattr(org, 'private_metadata', {}) or {},
            'public_metadata': getattr(org, 'public_metadata', {}) or {}
        }
    
    def _format_membership_data(self, membership) -> Dict[str, Any]:
        """Format Clerk membership data"""
        return {
            'clerk_id': membership.id,
            'organization_id': membership.organization.id if hasattr(membership, 'organization') else None,
            'user_id': membership.public_user_data.user_id if hasattr(membership, 'public_user_data') else None,
            'role': membership.role,
            'created_at': membership.created_at,
            'updated_at': membership.updated_at
        }
    
    def _format_invitation_data(self, invitation) -> Dict[str, Any]:
        """Format Clerk invitation data"""
        return {
            'clerk_id': invitation.id,
            'organization_id': invitation.organization.id if hasattr(invitation, 'organization') else None,
            'email': invitation.email_address,
            'role': invitation.role,
            'status': invitation.status,
            'created_at': invitation.created_at,
            'expires_at': getattr(invitation, 'expires_at', None)
        }


# Global service instance
clerk_org_service = ClerkOrganizationService()