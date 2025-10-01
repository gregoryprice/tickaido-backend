#!/usr/bin/env python3
"""
Organization schemas for API validation and serialization
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.base import BaseCreate, BaseResponse, BaseSchema, BaseUpdate, EmailStr


class OrganizationSizeSchema(str, Enum):
    """Organization size enum schema"""
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    ENTERPRISE = "enterprise"


class OrganizationPlanSchema(str, Enum):
    """Organization plan enum schema"""
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


# Request schemas
class OrganizationCreateRequest(BaseCreate):
    """Schema for creating a new organization"""
    name: str = Field(max_length=255, description="Organization name")
    domain: Optional[str] = Field(None, max_length=255, description="Primary domain")
    display_name: Optional[str] = Field(None, max_length=255, description="Display name")
    contact_email: Optional[EmailStr] = Field(None, description="Contact email")
    contact_phone: Optional[str] = Field(None, max_length=50, description="Contact phone")
    
    # Address
    address: Optional[str] = Field(None, description="Organization address")
    city: Optional[str] = Field(None, max_length=100, description="City")
    state_province: Optional[str] = Field(None, max_length=100, description="State or province")
    postal_code: Optional[str] = Field(None, max_length=20, description="Postal code")
    country: Optional[str] = Field(None, max_length=100, description="Country")
    
    # Business info
    industry: Optional[str] = Field(None, max_length=100, description="Industry")
    size: Optional[OrganizationSizeSchema] = Field(None, description="Organization size")
    timezone: str = Field("UTC", max_length=50, description="Default timezone")
    
    # Subscription
    plan: OrganizationPlanSchema = Field(OrganizationPlanSchema.BASIC, description="Subscription plan")
    billing_email: Optional[EmailStr] = Field(None, description="Billing email")
    
    # Configuration
    settings: Optional[Dict[str, Any]] = Field(None, description="Organization settings")
    feature_flags: Optional[Dict[str, bool]] = Field(None, description="Feature flags")
    
    # Branding
    logo_url: Optional[str] = Field(None, max_length=500, description="Logo URL")
    brand_colors: Optional[Dict[str, str]] = Field(None, description="Brand colors")
    custom_domain: Optional[str] = Field(None, max_length=255, description="Custom domain")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Organization name cannot be empty')
        return v.strip()
    
    @field_validator('domain', 'custom_domain')
    @classmethod
    def validate_domain(cls, v):
        if v:
            v = v.lower().strip()
            # Basic domain validation
            if not v.replace('-', '').replace('.', '').isalnum():
                raise ValueError('Domain contains invalid characters')
        return v
    
    @field_validator('contact_phone')
    @classmethod
    def validate_phone(cls, v):
        if v:
            # Remove common phone formatting characters
            v = v.replace(' ', '').replace('-', '').replace('(', '').replace(')', '').replace('+', '')
            if not v.isdigit():
                raise ValueError('Phone number can only contain digits and basic formatting')
        return v


class OrganizationUpdateRequest(BaseUpdate):
    """Schema for updating an organization"""
    name: Optional[str] = Field(None, max_length=255, description="Organization name")
    display_name: Optional[str] = Field(None, max_length=255, description="Display name")
    contact_email: Optional[EmailStr] = Field(None, description="Contact email")
    contact_phone: Optional[str] = Field(None, max_length=50, description="Contact phone")
    
    # Address
    address: Optional[str] = Field(None, description="Address")
    city: Optional[str] = Field(None, max_length=100, description="City")
    state_province: Optional[str] = Field(None, max_length=100, description="State/province")
    postal_code: Optional[str] = Field(None, max_length=20, description="Postal code")
    country: Optional[str] = Field(None, max_length=100, description="Country")
    
    # Business info
    industry: Optional[str] = Field(None, max_length=100, description="Industry")
    size: Optional[OrganizationSizeSchema] = Field(None, description="Size")
    timezone: Optional[str] = Field(None, max_length=50, description="Timezone")
    
    # Subscription
    billing_email: Optional[EmailStr] = Field(None, description="Billing email")
    
    # Configuration
    settings: Optional[Dict[str, Any]] = Field(None, description="Settings")
    
    # Branding
    logo_url: Optional[str] = Field(None, max_length=500, description="Logo URL")
    brand_colors: Optional[Dict[str, str]] = Field(None, description="Brand colors")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Organization name cannot be empty')
        return v.strip() if v else None


class OrganizationStatusUpdateRequest(BaseSchema):
    """Schema for updating organization status"""
    is_enabled: bool = Field(description="Enabled status")
    reason: Optional[str] = Field(None, description="Reason for status change")


class OrganizationFeatureUpdateRequest(BaseSchema):
    """Schema for updating organization features"""
    feature_flags: Dict[str, bool] = Field(description="Feature flags to set")
    limits: Optional[Dict[str, int]] = Field(None, description="Usage limits to set")


class OrganizationPlanUpdateRequest(BaseSchema):
    """Schema for updating organization plan"""
    plan: OrganizationPlanSchema = Field(description="New subscription plan")
    effective_date: Optional[datetime] = Field(None, description="When plan change takes effect")
    reason: Optional[str] = Field(None, description="Reason for plan change")


# Response schemas
class OrganizationBaseResponse(BaseResponse):
    """Base organization response with common fields"""
    name: str = Field(description="Organization name")
    display_name: Optional[str] = Field(None, description="Display name")
    effective_display_name: str = Field(description="Effective display name")
    domain: Optional[str] = Field(None, description="Primary domain")
    is_enabled: bool = Field(description="Enabled status")
    plan: OrganizationPlanSchema = Field(description="Subscription plan")
    timezone: str = Field(description="Default timezone")


class OrganizationListResponse(OrganizationBaseResponse):
    """Organization information for list views"""
    industry: Optional[str] = Field(None, description="Industry")
    size: Optional[OrganizationSizeSchema] = Field(None, description="Size")
    country: Optional[str] = Field(None, description="Country")
    user_count: int = Field(description="Number of users")
    integration_count: int = Field(description="Number of integrations")
    logo_url: Optional[str] = Field(None, description="Logo URL")


class OrganizationDetailResponse(OrganizationBaseResponse):
    """Detailed organization information"""
    contact_email: Optional[str] = Field(None, description="Contact email")
    contact_phone: Optional[str] = Field(None, description="Contact phone")
    
    # Address
    address: Optional[str] = Field(None, description="Address")
    city: Optional[str] = Field(None, description="City")
    state_province: Optional[str] = Field(None, description="State/province")
    postal_code: Optional[str] = Field(None, description="Postal code")
    country: Optional[str] = Field(None, description="Country")
    
    # Business info
    industry: Optional[str] = Field(None, description="Industry")
    size: Optional[OrganizationSizeSchema] = Field(None, description="Size")
    
    # Subscription (sensitive info excluded)
    billing_email: Optional[str] = Field(None, description="Billing email")
    
    # Configuration (non-sensitive)
    settings: Optional[Dict[str, Any]] = Field(None, description="Settings")
    feature_flags: Optional[Dict[str, bool]] = Field(None, description="Feature flags")
    
    # Branding
    logo_url: Optional[str] = Field(None, description="Logo URL")
    brand_colors: Optional[Dict[str, str]] = Field(None, description="Brand colors")
    custom_domain: Optional[str] = Field(None, description="Custom domain")
    
    # Statistics
    user_count: int = Field(description="Number of users")
    integration_count: int = Field(description="Number of integrations")
    is_enterprise: bool = Field(description="Is enterprise plan")
    
    # Member management statistics
    admin_count: Optional[int] = Field(None, description="Number of admin members")
    member_count: Optional[int] = Field(None, description="Number of regular members")
    pending_invitations_count: Optional[int] = Field(None, description="Number of pending invitations")


class OrganizationAdminResponse(OrganizationDetailResponse):
    """Admin organization information (includes sensitive data)"""
    limits: Optional[Dict[str, int]] = Field(None, description="Usage limits")


class OrganizationStatsResponse(BaseSchema):
    """Organization statistics response"""
    total_users: int = Field(description="Total users")
    active_users: int = Field(description="Active users")
    total_integrations: int = Field(description="Total integrations")
    active_integrations: int = Field(description="Active integrations")
    total_tickets: int = Field(description="Total tickets created")
    tickets_this_month: int = Field(description="Tickets created this month")
    storage_used_mb: Optional[int] = Field(None, description="Storage used in MB")
    api_requests_this_month: int = Field(description="API requests this month")


# Search and filter schemas
class OrganizationSearchParams(BaseSchema):
    """Organization search parameters"""
    q: Optional[str] = Field(None, description="Search query (name, domain)")
    plan: Optional[List[OrganizationPlanSchema]] = Field(None, description="Filter by plan")
    size: Optional[List[OrganizationSizeSchema]] = Field(None, description="Filter by size")
    industry: Optional[str] = Field(None, description="Filter by industry")
    country: Optional[str] = Field(None, description="Filter by country")
    is_enabled: Optional[bool] = Field(None, description="Filter by enabled status")
    has_custom_domain: Optional[bool] = Field(None, description="Has custom domain")
    created_after: Optional[datetime] = Field(None, description="Created after date")
    created_before: Optional[datetime] = Field(None, description="Created before date")
    user_count_min: Optional[int] = Field(None, ge=0, description="Minimum user count")
    user_count_max: Optional[int] = Field(None, ge=0, description="Maximum user count")


class OrganizationSortParams(BaseSchema):
    """Organization sorting parameters"""
    sort_by: str = Field(
        "created_at",
        description="Sort field",
        pattern="^(created_at|updated_at|name|user_count|integration_count|plan)$"
    )
    sort_order: str = Field("desc", pattern="^(asc|desc)$", description="Sort order")


# Bulk operations
class OrganizationBulkStatusUpdateRequest(BaseSchema):
    """Schema for bulk status updates"""
    organization_ids: List[UUID] = Field(description="Organization IDs")
    is_enabled: bool = Field(description="New enabled status")
    reason: Optional[str] = Field(None, description="Reason for change")
    
    @field_validator('organization_ids')
    @classmethod
    def validate_organization_ids(cls, v):
        if len(v) > 50:  # Limit bulk operations
            raise ValueError('Cannot update more than 50 organizations at once')
        return v


class OrganizationBulkPlanUpdateRequest(BaseSchema):
    """Schema for bulk plan updates"""
    organization_ids: List[UUID] = Field(description="Organization IDs")
    plan: OrganizationPlanSchema = Field(description="New plan")
    effective_date: Optional[datetime] = Field(None, description="Effective date")
    reason: Optional[str] = Field(None, description="Reason for change")


# Domain and branding schemas
class OrganizationDomainValidationRequest(BaseSchema):
    """Schema for domain validation"""
    domain: str = Field(description="Domain to validate")
    
    @field_validator('domain')
    @classmethod
    def validate_domain(cls, v):
        v = v.lower().strip()
        if not v.replace('-', '').replace('.', '').isalnum():
            raise ValueError('Domain contains invalid characters')
        return v


class OrganizationDomainValidationResponse(BaseSchema):
    """Domain validation response"""
    domain: str = Field(description="Validated domain")
    is_available: bool = Field(description="Whether domain is available")
    is_valid: bool = Field(description="Whether domain format is valid")
    suggestions: Optional[List[str]] = Field(None, description="Alternative domains")
    error_message: Optional[str] = Field(None, description="Error if invalid")


class OrganizationBrandingUpdateRequest(BaseSchema):
    """Schema for branding updates"""
    logo_url: Optional[str] = Field(None, max_length=500, description="Logo URL")
    brand_colors: Optional[Dict[str, str]] = Field(None, description="Brand colors")
    custom_domain: Optional[str] = Field(None, max_length=255, description="Custom domain")
    
    @field_validator('brand_colors')
    @classmethod
    def validate_brand_colors(cls, v):
        if v:
            # Validate hex color codes
            for key, color in v.items():
                if color and not (color.startswith('#') and len(color) in [4, 7]):
                    raise ValueError(f'Invalid color format for {key}: {color}')
        return v


# Usage and limits schemas  
class OrganizationUsageResponse(BaseSchema):
    """Organization usage response"""
    current_period_start: datetime = Field(description="Current billing period start")
    current_period_end: datetime = Field(description="Current billing period end")
    
    # Usage metrics
    users_used: int = Field(description="Current user count")
    users_limit: Optional[int] = Field(None, description="User limit")
    
    integrations_used: int = Field(description="Current integration count")
    integrations_limit: Optional[int] = Field(None, description="Integration limit")
    
    storage_used_mb: int = Field(description="Storage used in MB")
    storage_limit_mb: Optional[int] = Field(None, description="Storage limit in MB")
    
    api_requests_used: int = Field(description="API requests this period")
    api_requests_limit: Optional[int] = Field(None, description="API request limit")
    
    # Computed fields
    users_usage_percent: Optional[float] = Field(None, description="User usage percentage")
    storage_usage_percent: Optional[float] = Field(None, description="Storage usage percentage")
    api_requests_usage_percent: Optional[float] = Field(None, description="API usage percentage")


# Invitation schemas
class OrganizationInvitationRequest(BaseSchema):
    """Schema for inviting users to organization"""
    email: EmailStr = Field(description="Email to invite")
    role: str = Field("user", description="Role to assign")
    full_name: Optional[str] = Field(None, description="Full name of invitee")
    department: Optional[str] = Field(None, description="Department")
    send_email: bool = Field(True, description="Send invitation email")
    message: Optional[str] = Field(None, description="Custom invitation message")


class OrganizationInvitationResponse(BaseSchema):
    """Organization invitation response"""
    invitation_id: UUID = Field(description="Invitation ID")
    email: str = Field(description="Invited email")
    role: str = Field(description="Assigned role")
    invited_by: UUID = Field(description="User who sent invitation")
    expires_at: datetime = Field(description="Invitation expiration")
    status: str = Field(description="Invitation status")
    invitation_url: Optional[str] = Field(None, description="Invitation URL")