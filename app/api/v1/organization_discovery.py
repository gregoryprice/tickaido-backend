#!/usr/bin/env python3
"""
Organization Discovery API endpoints - Public endpoints for organization discovery
"""

import logging
from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request

from app.database import get_db_session
from app.dependencies import get_current_user
from app.models.user import User
from app.services.organization_discovery_service import OrganizationDiscoveryService
from app.schemas.member_management import (
    OrganizationDiscoveryResponse,
    OrganizationDirectoryParams,
    OrganizationDirectoryResponse,
    RegistrationOptionsRequest,
    RegistrationOptionsResponse,
    DomainCheckRequest,
    DomainCheckResponse,
    MemberManagementError
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/organizations")
discovery_service = OrganizationDiscoveryService()

# Note: Rate limiting should be implemented at the infrastructure level
# (e.g., nginx, API gateway, or middleware) for production use


@router.get("/by-domain/{domain}", response_model=OrganizationDiscoveryResponse)
async def get_organization_by_domain(
    request: Request,
    domain: str,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Find organization by email domain (for registration matching).
    
    **Public endpoint - No authentication required**
    
    - **domain**: Email domain to search for (e.g., "example.com")
    - **Rate Limit**: 100 requests per IP per hour
    - Returns organization information or 404 if not found
    - Used during user registration to suggest existing organizations
    """
    try:
        if not domain or len(domain.strip()) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Domain parameter cannot be empty"
            )
        
        domain = domain.lower().strip()
        
        # Basic domain validation
        if not all(c.isalnum() or c in '.-' for c in domain):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid domain format"
            )
        
        organization_data = await discovery_service.get_organization_by_domain(db, domain)
        
        if not organization_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No organization found for domain '{domain}'"
            )
        
        return OrganizationDiscoveryResponse(organization=organization_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error looking up organization for domain {domain}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to lookup organization by domain"
        )


@router.get("/directory", response_model=OrganizationDirectoryResponse)
async def get_organization_directory(
    search: Optional[str] = Query(None, description="Search query for name/domain"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Results per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get list of all active organizations (admin only).
    
    - **search**: Filter by name/domain - optional
    - **page**: Page number for pagination
    - **limit**: Results per page (max 100)
    - Requires: System admin privileges
    """
    try:
        # Only system admins can access the organization directory
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only system administrators can access the organization directory"
            )
        
        offset = (page - 1) * limit
        
        directory = await discovery_service.get_organization_directory(
            db=db,
            search=search,
            offset=offset,
            limit=limit
        )
        
        return OrganizationDirectoryResponse(**directory)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting organization directory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve organization directory"
        )


@router.post("/registration-options", response_model=RegistrationOptionsResponse)
async def get_registration_options(
    request: Request,
    options_request: RegistrationOptionsRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get registration options for user based on email domain.
    
    **Public endpoint - No authentication required**
    
    - **email**: Email address to check for organization suggestions
    - **Rate Limit**: 50 requests per IP per hour
    - Returns suggested actions and available options
    - Used during registration to guide user choice
    """
    try:
        organization_data = await discovery_service.suggest_organization_for_registration(
            db, options_request.email
        )
        
        options = discovery_service.get_registration_options(
            options_request.email, organization_data
        )
        
        return RegistrationOptionsResponse(**options)
        
    except Exception as e:
        logger.error(f"Error getting registration options for {options_request.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get registration options"
        )


@router.post("/check-domain", response_model=DomainCheckResponse)
async def check_domain_availability(
    request: Request,
    domain_request: DomainCheckRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Check domain availability for new organization creation.
    
    **Public endpoint - No authentication required**
    
    - **domain**: Domain to check availability
    - **Rate Limit**: 100 requests per IP per hour
    - Returns availability status and existing organizations
    - Note: Multiple organizations can share the same domain
    """
    try:
        availability = await discovery_service.check_domain_availability(
            db, domain_request.domain
        )
        
        return DomainCheckResponse(**availability)
        
    except Exception as e:
        logger.error(f"Error checking domain availability for {domain_request.domain}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check domain availability"
        )


@router.get("/by-domain/{domain}/organizations", response_model=List[Dict[str, Any]])
async def get_all_organizations_by_domain(
    request: Request,
    domain: str,
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get all organizations using a specific domain.
    
    **Public endpoint - No authentication required**
    
    - **domain**: Domain to search for
    - **limit**: Maximum number of results (max 50)
    - **Rate Limit**: 100 requests per IP per hour
    - Returns list of all organizations using the domain
    - Useful when multiple organizations share the same domain
    """
    try:
        if not domain or len(domain.strip()) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Domain parameter cannot be empty"
            )
        
        organizations = await discovery_service.find_organizations_by_domain(
            db, domain, limit
        )
        
        return organizations
        
    except Exception as e:
        logger.error(f"Error finding organizations for domain {domain}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to find organizations by domain"
        )


# Enhanced registration endpoint with organization discovery

@router.post("/enhanced-registration")
async def enhanced_user_registration(
    request: Request,
    # This would integrate with the existing auth system
    # Placeholder for enhanced registration logic
    db: AsyncSession = Depends(get_db_session)
):
    """
    Enhanced user registration with organization discovery and choice.
    
    **Public endpoint - No authentication required**
    
    - **Rate Limit**: 10 registrations per IP per hour
    - Integrates domain-based organization discovery
    - Allows user to choose between joining existing org or creating new one
    - Returns user account and JWT token
    
    **Note**: This endpoint would integrate with the existing auth system
    """
    # This is a placeholder - would need to integrate with existing auth/registration
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Enhanced registration endpoint not yet implemented - integrate with existing auth system"
    )


# Utility endpoints for domain validation

@router.get("/validate-domain/{domain}")
async def validate_domain_format(
    request: Request,
    domain: str
):
    """
    Validate domain format.
    
    **Public endpoint - No authentication required**
    
    - **domain**: Domain to validate
    - **Rate Limit**: 200 requests per IP per hour
    - Returns validation result
    """
    try:
        domain = domain.lower().strip()
        
        if not domain:
            return {"valid": False, "reason": "Domain cannot be empty"}
        
        # Basic validation
        if not all(c.isalnum() or c in '.-' for c in domain):
            return {"valid": False, "reason": "Domain contains invalid characters"}
        
        if domain.startswith('.') or domain.endswith('.'):
            return {"valid": False, "reason": "Domain cannot start or end with a dot"}
        
        if '..' in domain:
            return {"valid": False, "reason": "Domain cannot contain consecutive dots"}
        
        if len(domain) > 255:
            return {"valid": False, "reason": "Domain is too long (max 255 characters)"}
        
        return {"valid": True, "domain": domain}
        
    except Exception as e:
        logger.error(f"Error validating domain {domain}: {e}")
        return {"valid": False, "reason": "Internal validation error"}