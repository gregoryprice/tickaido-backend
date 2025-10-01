#!/usr/bin/env python3
"""
Organization context middleware for multi-tenant request handling
"""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import and_, select

from app.middleware.auth_middleware import get_current_user
from app.models.organization import Organization
from app.models.organization_invitation import OrganizationRole
from app.models.user import User

logger = logging.getLogger(__name__)


class OrganizationContext:
    """Container for organization context information"""
    
    def __init__(
        self, 
        organization: Organization,
        user: User,
        role: OrganizationRole,
        permissions: Optional[dict] = None
    ):
        self.organization = organization
        self.user = user
        self.role = role
        self.permissions = permissions or {}
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission in this organization"""
        # Simplified permission model - both Admin and Member have all permissions
        if self.role in [OrganizationRole.ADMIN, OrganizationRole.MEMBER]:
            return True
        
        # Check custom permissions for API tokens
        if isinstance(self.permissions, list):
            return "*" in self.permissions or permission in self.permissions
        elif isinstance(self.permissions, dict):
            return self.permissions.get(permission, False)
        
        return False
    
    def _get_role_permissions(self) -> list[str]:
        """Get permissions for current role"""
        permissions_map = {
            OrganizationRole.ADMIN: ["*"],   # All permissions
            OrganizationRole.MEMBER: ["*"]  # All permissions  
        }
        return permissions_map.get(self.role, ["*"])  # Default to all permissions


class OrganizationMiddleware:
    """Middleware to handle organization context for requests"""
    
    async def __call__(
        self,
        request: Request,
        user: User = Depends(get_current_user)
    ) -> Optional[OrganizationContext]:
        """Extract and validate organization context"""
        
        # Check if organization context already set by API token authentication
        if hasattr(request.state, 'organization') and hasattr(request.state, 'user_permissions'):
            return OrganizationContext(
                organization=request.state.organization,
                user=user,
                role=OrganizationRole.MEMBER,  # Default for API tokens
                permissions=request.state.user_permissions
            )
        
        # Get organization ID from header, query param, or path
        org_id = (
            request.headers.get("X-Organization-ID") or
            request.query_params.get("org_id") or
            request.path_params.get("org_id")
        )
        
        if not org_id:
            # Try to get user's organization from their profile
            if user.organization_id:
                org_id = str(user.organization_id)
            else:
                # For endpoints that don't require organization context
                return None
        
        from app.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            # Get organization and verify user has access
            result = await db.execute(
                select(Organization).where(
                    and_(
                        Organization.id == org_id,
                        Organization.is_enabled == True
                    )
                )
            )
            organization = result.scalar_one_or_none()
            
            if not organization:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Organization not found"
                )
            
            # Check if user has access to this organization
            if user.organization_id != organization.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User does not have access to this organization"
                )
            
            # Determine user's role in the organization
            user_role = user.organization_role or OrganizationRole.MEMBER
            
            return OrganizationContext(
                organization=organization,
                user=user,
                role=user_role,
                permissions={}
            )


# Global middleware instance
org_middleware = OrganizationMiddleware()


async def get_organization_context(
    context: OrganizationContext = Depends(org_middleware)
) -> OrganizationContext:
    """Dependency to get organization context (required)"""
    if not context:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization context required"
        )
    return context


async def get_organization_context_optional(
    context: Optional[OrganizationContext] = Depends(org_middleware)
) -> Optional[OrganizationContext]:
    """Dependency to get organization context (optional)"""
    return context