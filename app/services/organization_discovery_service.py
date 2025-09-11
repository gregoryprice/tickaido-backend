#!/usr/bin/env python3
"""
Organization Discovery Service - Public service for organization discovery 
during user registration and domain-based organization matching
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func

from app.models.organization import Organization
from app.models.user import User


class OrganizationDiscoveryService:
    """
    Service for organization discovery and domain-based matching.
    This service handles public endpoints that don't require authentication.
    """
    
    def __init__(self):
        """Initialize organization discovery service"""
        pass
    
    def extract_domain_from_email(self, email: str) -> str:
        """
        Extract domain from email address.
        
        Args:
            email: Email address
            
        Returns:
            str: Domain part of email
            
        Raises:
            ValueError: If email format is invalid
        """
        if not email or '@' not in email:
            raise ValueError("Invalid email format")
        
        return email.split('@')[1].lower().strip()
    
    async def get_organization_by_domain(
        self,
        db: AsyncSession,
        domain: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get organization information by domain (public endpoint).
        Returns limited, non-sensitive information suitable for public consumption.
        
        Args:
            db: Database session
            domain: Domain to search for
            
        Returns:
            Organization data or None if not found
        """
        domain = domain.lower().strip()
        
        if not domain:
            return None
        
        # Find organization by domain
        query = select(Organization).where(
            and_(
                Organization.domain == domain,
                Organization.is_enabled == True,
                Organization.is_deleted == False
            )
        ).order_by(Organization.created_at.desc()).limit(1)
        
        result = await db.execute(query)
        organization = result.scalar_one_or_none()
        
        if not organization:
            return None
        
        # Compute member_count via SQL to avoid lazy-loading relationships in async context
        count_result = await db.execute(
            select(func.count()).select_from(User).where(
                and_(
                    User.organization_id == organization.id,
                    User.is_active == True
                )
            )
        )
        member_count = int(count_result.scalar() or 0)

        # Return only public, non-sensitive information
        return {
            "id": str(organization.id),
            "name": organization.name,
            "domain": organization.domain,
            "display_name": organization.effective_display_name,
            "member_count": member_count,
            "logo_url": organization.logo_url,
            "created_at": organization.created_at.isoformat() if organization.created_at else None
        }
    
    async def find_organizations_by_domain(
        self,
        db: AsyncSession,
        domain: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find all organizations matching the given domain.
        This handles the case where multiple organizations can have the same domain.
        
        Args:
            db: Database session
            domain: Domain to search for
            limit: Maximum number of results
            
        Returns:
            List of organization data dictionaries
        """
        domain = domain.lower().strip()
        
        if not domain:
            return []
        
        query = select(Organization).where(
            and_(
                Organization.domain == domain,
                Organization.is_enabled == True,
                Organization.is_deleted == False
            )
        ).order_by(
            Organization.created_at.desc()
        ).limit(limit)
        
        result = await db.execute(query)
        organizations = list(result.scalars().all())

        # For each organization, compute member count explicitly to avoid lazy-load
        response: List[Dict[str, Any]] = []
        for org in organizations:
            cnt_result = await db.execute(
                select(func.count()).select_from(User).where(
                    and_(
                        User.organization_id == org.id,
                        User.is_active == True
                    )
                )
            )
            member_count = int(cnt_result.scalar() or 0)

            response.append({
                "id": str(org.id),
                "name": org.name,
                "domain": org.domain,
                "display_name": org.effective_display_name,
                "member_count": member_count,
                "logo_url": org.logo_url,
                "created_at": org.created_at.isoformat() if org.created_at else None
            })

        return response
    
    async def get_organization_directory(
        self,
        db: AsyncSession,
        search: Optional[str] = None,
        offset: int = 0,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Get organization directory with search and pagination.
        This is for admin-only access to browse all organizations.
        
        Args:
            db: Database session
            search: Search query for name or domain
            offset: Pagination offset
            limit: Results per page
            
        Returns:
            Dictionary with organizations list and pagination info
        """
        # Base query
        query = select(Organization).where(
            and_(
                Organization.is_enabled == True,
                Organization.is_deleted == False
            )
        )
        
        count_query = select(func.count(Organization.id)).where(
            and_(
                Organization.is_enabled == True,
                Organization.is_deleted == False
            )
        )
        
        # Apply search filter
        if search:
            search_term = f"%{search.lower()}%"
            search_filter = or_(
                Organization.name.ilike(search_term),
                Organization.domain.ilike(search_term),
                Organization.display_name.ilike(search_term)
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)
        
        # Apply ordering and pagination
        query = query.order_by(
            Organization.created_at.desc()
        ).offset(offset).limit(limit)
        
        # Execute queries
        orgs_result = await db.execute(query)
        count_result = await db.execute(count_query)
        
        organizations = list(orgs_result.scalars().all())
        total = count_result.scalar() or 0
        
        return {
            "data": [
                {
                    "id": str(org.id),
                    "name": org.name,
                    "domain": org.domain,
                    "display_name": org.effective_display_name,
                    "member_count": org.user_count,
                    "integration_count": org.integration_count,
                    "plan": org.plan,
                    "logo_url": org.logo_url,
                    "created_at": org.created_at.isoformat() if org.created_at else None
                }
                for org in organizations
            ],
            "pagination": {
                "offset": offset,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit if limit > 0 else 0
            }
        }
    
    async def suggest_organization_for_registration(
        self,
        db: AsyncSession,
        email: str
    ) -> Optional[Dict[str, Any]]:
        """
        Suggest organization for user registration based on email domain.
        
        Args:
            db: Database session
            email: User's email address
            
        Returns:
            Organization suggestion or None
        """
        try:
            domain = self.extract_domain_from_email(email)
            return await self.get_organization_by_domain(db, domain)
        except ValueError:
            return None
    
    async def check_domain_availability(
        self,
        db: AsyncSession,
        domain: str
    ) -> Dict[str, Any]:
        """
        Check if domain is available for new organization creation.
        
        Args:
            db: Database session
            domain: Domain to check
            
        Returns:
            Availability information
        """
        domain = domain.lower().strip()
        
        if not domain:
            return {
                "domain": domain,
                "available": False,
                "reason": "Invalid domain format"
            }
        
        # Check if any organizations use this domain
        existing_orgs = await self.find_organizations_by_domain(db, domain, limit=10)
        
        return {
            "domain": domain,
            "available": len(existing_orgs) == 0,
            "existing_count": len(existing_orgs),
            "existing_organizations": existing_orgs if existing_orgs else None,
            "reason": f"{len(existing_orgs)} organizations already use this domain" if existing_orgs else None
        }
    
    # Utility methods for registration flows
    
    def should_suggest_existing_organization(
        self,
        email: str,
        organization_data: Optional[Dict[str, Any]]
    ) -> bool:
        """
        Determine if we should suggest joining existing organization.
        
        Args:
            email: User's email
            organization_data: Organization found for domain
            
        Returns:
            True if should suggest joining existing org
        """
        if not organization_data:
            return False
        
        try:
            domain = self.extract_domain_from_email(email)
            return organization_data.get("domain") == domain
        except ValueError:
            return False
    
    def get_registration_options(
        self,
        email: str,
        organization_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Get registration options for user based on email and discovered organizations.
        
        Args:
            email: User's email
            organization_data: Organization found for domain
            
        Returns:
            Registration options
        """
        try:
            domain = self.extract_domain_from_email(email)
        except ValueError:
            return {
                "suggested_action": "create_new",
                "options": ["create_new"],
                "message": "Create a new organization"
            }
        
        if not organization_data:
            return {
                "suggested_action": "create_new",
                "options": ["create_new"],
                "domain": domain,
                "message": f"No organization found for {domain}. Create a new organization."
            }
        
        return {
            "suggested_action": "join_existing",
            "options": ["join_existing", "create_new"],
            "domain": domain,
            "existing_organization": organization_data,
            "message": f"Found organization '{organization_data['name']}' for {domain}. You can join it or create a new organization."
        }