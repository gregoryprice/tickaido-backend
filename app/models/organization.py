#!/usr/bin/env python3
"""
Organization model for multi-tenant company isolation
"""

from typing import Optional, Dict, Any
from sqlalchemy import Column, String, Boolean, Text, JSON
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class Organization(BaseModel):
    """
    Organization model for company isolation and multi-tenancy.
    Each organization represents a company with independent integrations and users.
    """
    
    __tablename__ = "organizations"
    
    # Basic organization information
    name = Column(
        String(255),
        nullable=False,
        index=True,
        comment="Company/organization name"
    )
    
    domain = Column(
        String(255),
        nullable=True,
        index=True,
        comment="Primary domain for the organization (e.g., company.com) - multiple orgs can share domains"
    )
    
    display_name = Column(
        String(255),
        nullable=True,
        comment="Display name for UI (defaults to name if not set)"
    )
    
    # Clerk integration
    clerk_organization_id = Column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
        comment="Clerk organization ID for authentication service integration"
    )
    
    clerk_metadata = Column(
        JSON,
        nullable=True,
        comment="Synced Clerk organization data and metadata"
    )
    
    # Organization status (note: is_active is inherited from BaseModel via soft delete)
    is_enabled = Column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Whether organization is enabled for use"
    )
    
    # Organization settings and configuration
    settings = Column(
        JSON,
        nullable=True,
        comment="Organization-specific settings and preferences"
    )
    
    # Contact information
    contact_email = Column(
        String(255),
        nullable=True,
        comment="Primary contact email for the organization"
    )
    
    contact_phone = Column(
        String(50),
        nullable=True,
        comment="Primary contact phone number"
    )
    
    # Address information
    address = Column(
        Text,
        nullable=True,
        comment="Organization address"
    )
    
    city = Column(
        String(100),
        nullable=True,
        comment="City"
    )
    
    state_province = Column(
        String(100),
        nullable=True,
        comment="State or province"
    )
    
    postal_code = Column(
        String(20),
        nullable=True,
        comment="Postal/ZIP code"
    )
    
    country = Column(
        String(100),
        nullable=True,
        comment="Country"
    )
    
    # Business information
    industry = Column(
        String(100),
        nullable=True,
        comment="Industry or business sector"
    )
    
    size = Column(
        String(50),
        nullable=True,
        comment="Organization size (small, medium, large, enterprise)"
    )
    
    timezone = Column(
        String(50),
        default="UTC",
        nullable=False,
        comment="Default timezone for the organization"
    )
    
    # Subscription and billing
    plan = Column(
        String(50),
        default="basic",
        nullable=False,
        comment="Subscription plan (basic, professional, enterprise)"
    )
    
    billing_email = Column(
        String(255),
        nullable=True,
        comment="Billing contact email"
    )
    
    # Feature flags and limits
    feature_flags = Column(
        JSON,
        nullable=True,
        comment="Enabled features for this organization"
    )
    
    limits = Column(
        JSON,
        nullable=True,
        comment="Usage limits and quotas"
    )
    
    # Branding and customization
    logo_url = Column(
        String(500),
        nullable=True,
        comment="Organization logo URL"
    )
    
    brand_colors = Column(
        JSON,
        nullable=True,
        comment="Brand colors for UI customization"
    )
    
    custom_domain = Column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
        comment="Custom domain for white-labeling"
    )
    
    # Relationships
    users = relationship(
        "User",
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    
    integrations = relationship(
        "Integration",
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    
    agents = relationship(
        "Agent",
        back_populates="organization",
        cascade="all, delete-orphan",
        order_by="Agent.created_at.desc()"
    )
    
    tickets = relationship(
        "Ticket",
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    
    invitations = relationship(
        "OrganizationInvitation",
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    
    # API token management
    api_tokens = relationship(
        "APIToken",
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<Organization(id={self.id}, name={self.name}, domain={self.domain})>"
    
    @property
    def effective_display_name(self) -> str:
        """Get effective display name (display_name or name)"""
        return str(self.display_name or self.name)
    
    @property
    def user_count(self) -> int:
        """Get count of active users in organization"""
        if not hasattr(self, 'users') or self.users is None:
            return 0
        return len([user for user in self.users if user.is_active])
    
    @property
    def integration_count(self) -> int:
        """Get count of active integrations in organization"""
        if not hasattr(self, 'integrations') or self.integrations is None:
            return 0
        return len([integration for integration in self.integrations if not integration.is_deleted])
    
    @property
    def is_enterprise(self) -> bool:
        """Check if organization is on enterprise plan"""
        return str(self.plan) == "enterprise"
    
    def has_feature(self, feature_name: str) -> bool:
        """
        Check if organization has a specific feature enabled.
        
        Args:
            feature_name: Name of the feature to check
            
        Returns:
            bool: True if feature is enabled
        """
        if not self.feature_flags:
            return False
        return self.feature_flags.get(feature_name, False)
    
    def get_limit(self, limit_name: str) -> Optional[int]:
        """
        Get a specific usage limit for the organization.
        
        Args:
            limit_name: Name of the limit to get
            
        Returns:
            int: Limit value or None if not set
        """
        if not self.limits:
            return None
        return self.limits.get(limit_name)
    
    def activate(self):
        """Activate the organization"""
        self.is_enabled = True
    
    def deactivate(self):
        """Deactivate the organization"""  
        self.is_enabled = False
    
    def update_settings(self, settings: dict):
        """
        Update organization settings.
        
        Args:
            settings: Dictionary of settings to update
        """
        current_settings: Dict[str, Any] = self.settings or {}  # type: ignore
        current_settings.update(settings)
        self.settings = current_settings  # type: ignore
        # updated_at is automatically handled by the BaseModel
    
    def add_feature(self, feature_name: str):
        """
        Enable a feature for the organization.
        
        Args:
            feature_name: Name of the feature to enable
        """
        current_flags: Dict[str, bool] = self.feature_flags or {}  # type: ignore
        current_flags[feature_name] = True
        self.feature_flags = current_flags  # type: ignore
    
    def remove_feature(self, feature_name: str):
        """
        Disable a feature for the organization.
        
        Args:
            feature_name: Name of the feature to disable
        """
        current_flags: Dict[str, bool] = self.feature_flags or {}  # type: ignore
        if feature_name in current_flags:
            current_flags.pop(feature_name, None)
            self.feature_flags = current_flags  # type: ignore
    
    def set_limit(self, limit_name: str, limit_value: int):
        """
        Set a usage limit for the organization.
        
        Args:
            limit_name: Name of the limit
            limit_value: Limit value
        """
        current_limits: Dict[str, int] = self.limits or {}  # type: ignore
        current_limits[limit_name] = limit_value
        self.limits = current_limits  # type: ignore
    
    # Member management helper methods
    @property 
    def admin_count(self) -> int:
        """Get count of admin users in organization"""
        if not hasattr(self, 'users') or self.users is None:
            return 0
        from app.models.organization_invitation import OrganizationRole
        return len([user for user in self.users 
                   if user.is_active and user.organization_role == OrganizationRole.ADMIN])
    
    @property
    def member_count(self) -> int:
        """Get count of member users in organization"""
        if not hasattr(self, 'users') or self.users is None:
            return 0
        from app.models.organization_invitation import OrganizationRole
        return len([user for user in self.users 
                   if user.is_active and user.organization_role == OrganizationRole.MEMBER])
    
    @property
    def active_member_count(self) -> int:
        """Get count of all active members (admins + members)"""
        return self.admin_count + self.member_count
    
    @property
    def pending_invitations_count(self) -> int:
        """Get count of pending invitations"""
        if not hasattr(self, 'invitations') or self.invitations is None:
            return 0
        from app.models.organization_invitation import InvitationStatus
        return len([inv for inv in self.invitations 
                   if inv.status == InvitationStatus.PENDING and not inv.is_expired])
    
    def has_domain_match(self, email_domain: str) -> bool:
        """Check if organization domain matches email domain"""
        return self.domain is not None and self.domain.lower() == email_domain.lower()
    
    def to_dict(self, include_sensitive: bool = False) -> dict:
        """
        Convert organization to dictionary.
        
        Args:
            include_sensitive: Include sensitive billing information
            
        Returns:
            dict: Organization data
        """
        data = super().to_dict()
        
        if not include_sensitive:
            # Remove sensitive fields
            sensitive_fields = ['billing_email', 'limits']
            for field in sensitive_fields:
                data.pop(field, None)
        
        # Add computed properties
        data['effective_display_name'] = self.effective_display_name
        data['user_count'] = self.user_count
        data['integration_count'] = self.integration_count
        data['is_enterprise'] = self.is_enterprise
        
        return data