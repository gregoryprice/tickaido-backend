#!/usr/bin/env python3
"""
Member Management API schemas for validation and serialization
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import Field, field_validator, model_validator
from enum import Enum

from app.schemas.base import BaseSchema, BaseResponse, EmailStr

# Import UserResponse directly  
from app.schemas.user import UserResponse


class OrganizationRoleSchema(str, Enum):
    """Organization role enum schema"""
    ADMIN = "admin"
    MEMBER = "member"


class InvitationStatusSchema(str, Enum):
    """Invitation status enum schema"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


# Member Management Schemas

class MemberListResponse(BaseResponse):
    """Organization member information for list views - matches UserMeResponse format"""
    email: str = Field(description="Member email")
    full_name: Optional[str] = Field(None, description="Member's full name")
    avatar_url: Optional[str] = Field(None, description="Avatar URL")
    user_role: str = Field(description="User role in system")
    role: OrganizationRoleSchema = Field(description="Role in organization")
    is_active: bool = Field(description="Whether member is active")
    timezone: str = Field(description="User timezone")
    language: str = Field(description="User language")
    preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences")
    is_verified: bool = Field(description="Whether email is verified")
    last_login_at: Optional[datetime] = Field(None, description="Last login timestamp")
    
    # Organization membership fields
    organization_id: Optional[UUID] = Field(None, description="Organization ID")
    organization_name: Optional[str] = Field(None, description="Organization name")
    organization_domain: Optional[str] = Field(None, description="Organization domain")
    organization_plan: Optional[str] = Field(None, description="Organization plan")
    organization_timezone: Optional[str] = Field(None, description="Organization timezone")
    invited_by_id: Optional[UUID] = Field(None, description="User who invited this member")
    invited_at: Optional[datetime] = Field(None, description="When user was invited to organization")
    joined_organization_at: Optional[datetime] = Field(None, description="When member joined organization")


class MemberInviteRequest(BaseSchema):
    """Request to invite new member to organization"""
    email: EmailStr = Field(description="Email address to invite")
    role: OrganizationRoleSchema = Field(
        OrganizationRoleSchema.MEMBER,
        description="Role to assign to invited member"
    )
    send_email: bool = Field(True, description="Whether to send invitation email")
    message: Optional[str] = Field(
        None, 
        max_length=1000, 
        description="Custom message to include in invitation"
    )
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        return v.lower().strip()


class MemberInviteResponse(BaseSchema):
    """Response for member invitation"""
    invitation_id: UUID = Field(description="Invitation ID")
    email: str = Field(description="Invited email address")
    role: OrganizationRoleSchema = Field(description="Assigned role")
    invitation_url: str = Field(description="URL for accepting invitation")
    expires_at: datetime = Field(description="Invitation expiration time")
    message: Optional[str] = Field(None, description="Custom invitation message")


class MemberRoleUpdateRequest(BaseSchema):
    """Request to update member's organization role"""
    role: OrganizationRoleSchema = Field(description="New organization role")


class MemberRoleUpdateResponse(BaseSchema):
    """Response for member role update"""
    message: str = Field(description="Success message")


class MemberUpdateResponse(BaseSchema):
    """Response for member update operations"""
    id: str = Field(description="Member ID")
    role: str = Field(description="Updated role")
    updated_fields: List[str] = Field(description="List of updated fields")
    message: str = Field(description="Success message")
    member: UserResponse = Field(description="Updated member information")


class MemberRemovalResponse(BaseSchema):
    """Response for member removal"""
    message: str = Field(description="Success message")


class UserDeleteResponse(BaseSchema):
    """Response for user account deletion"""
    message: str = Field(description="Success message")
    organization_deleted: bool = Field(description="Whether organization was also deleted")


class MemberListParams(BaseSchema):
    """Parameters for listing organization members"""
    role: Optional[OrganizationRoleSchema] = Field(None, description="Filter by role")
    active: Optional[bool] = Field(None, description="Filter by active status")
    page: int = Field(1, ge=1, description="Page number")
    limit: int = Field(50, ge=1, le=100, description="Results per page")


class MembersListResponse(BaseSchema):
    """Response for organization members list"""
    data: List[UserResponse] = Field(description="List of organization members")
    pagination: Dict[str, int] = Field(description="Pagination information")


# Organization Discovery Schemas

class OrganizationDiscoveryResponse(BaseSchema):
    """Response for organization discovery by domain"""
    organization: Dict[str, Any] = Field(description="Organization information")


class OrganizationDirectoryParams(BaseSchema):
    """Parameters for organization directory listing"""
    search: Optional[str] = Field(None, description="Search query for name/domain")
    page: int = Field(1, ge=1, description="Page number")
    limit: int = Field(50, ge=1, le=100, description="Results per page")


class OrganizationDirectoryResponse(BaseSchema):
    """Response for organization directory"""
    data: List[Dict[str, Any]] = Field(description="List of organizations")
    pagination: Dict[str, int] = Field(description="Pagination information")


# User Management Schemas

class UserTransferRequest(BaseSchema):
    """Request to transfer user to different organization"""
    organization_id: UUID = Field(description="Target organization ID")
    role: OrganizationRoleSchema = Field(
        OrganizationRoleSchema.MEMBER,
        description="Role in new organization"
    )
    reason: Optional[str] = Field(None, max_length=500, description="Reason for transfer")


class UserDeleteRequest(BaseSchema):
    """Request to delete user account"""
    delete_organization: bool = Field(
        False, 
        description="Whether to delete organization if user is the only member"
    )
    reason: Optional[str] = Field(None, max_length=500, description="Reason for deletion")


# Invitation Management Schemas

class InvitationResponse(BaseResponse):
    """Organization invitation response"""
    organization_id: UUID = Field(description="Organization ID")
    email: str = Field(description="Invited email address")
    role: OrganizationRoleSchema = Field(description="Role to be assigned")
    inviter_id: UUID = Field(description="ID of user who sent the invitation")
    invitation_token: Optional[str] = Field(None, description="Invitation token (only for creation)")
    token: Optional[str] = Field(None, description="Invitation token (alias for compatibility)")
    status: InvitationStatusSchema = Field(description="Invitation status")
    expires_at: datetime = Field(description="Expiration date")
    accepted_at: Optional[datetime] = Field(None, description="Acceptance date")
    declined_at: Optional[datetime] = Field(None, description="Decline date")
    cancelled_at: Optional[datetime] = Field(None, description="Cancellation date")
    message: Optional[str] = Field(None, description="Custom invitation message")
    is_expired: bool = Field(description="Whether invitation has expired")
    is_pending: bool = Field(description="Whether invitation is pending")


class InvitationDetailsResponse(InvitationResponse):
    """Detailed invitation response (for token-based lookup)"""
    organization: Dict[str, Any] = Field(description="Organization information")


class InvitationAcceptRequest(BaseSchema):
    """Request to accept invitation"""
    password: Optional[str] = Field(None, min_length=8, description="Password for new user account")
    full_name: Optional[str] = Field(None, max_length=255, description="Full name for new user")
    
    @model_validator(mode='after')
    def validate_new_user_fields(self):
        # If password is provided, full_name should be provided too for new users
        if self.password and not self.full_name:
            raise ValueError('Full name is required when creating new user account')
        return self


class InvitationAcceptResponse(BaseSchema):
    """Response for invitation acceptance"""
    user: Dict[str, Any] = Field(description="User information")
    organization: Dict[str, Any] = Field(description="Organization information")
    is_new_user: bool = Field(description="Whether this was a new user registration")
    access_token: Optional[str] = Field(None, description="JWT token for immediate login")


class InvitationListParams(BaseSchema):
    """Parameters for listing organization invitations"""
    status: Optional[InvitationStatusSchema] = Field(None, description="Filter by status")
    page: int = Field(1, ge=1, description="Page number")
    limit: int = Field(50, ge=1, le=100, description="Results per page")


class InvitationsListResponse(BaseSchema):
    """Response for organization invitations list"""
    data: List[InvitationResponse] = Field(description="List of invitations")
    pagination: Dict[str, int] = Field(description="Pagination information")


# Registration Enhancement Schemas

class RegistrationOptionsRequest(BaseSchema):
    """Request for registration options based on email"""
    email: EmailStr = Field(description="Email address to check")
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        return v.lower().strip()


class RegistrationOptionsResponse(BaseSchema):
    """Response with registration options"""
    suggested_action: str = Field(description="Suggested action (join_existing or create_new)")
    options: List[str] = Field(description="Available options")
    domain: Optional[str] = Field(None, description="Email domain")
    existing_organization: Optional[Dict[str, Any]] = Field(
        None, 
        description="Existing organization for domain"
    )
    message: str = Field(description="Human-readable message about options")


class EnhancedUserRegistrationRequest(BaseSchema):
    """Enhanced user registration with organization choice"""
    email: EmailStr = Field(description="User email address")
    full_name: str = Field(max_length=255, description="User's full name")
    password: str = Field(min_length=8, description="User password")
    
    # Organization choice
    action: str = Field(description="Registration action (join_existing or create_new)")
    organization_id: Optional[UUID] = Field(None, description="Organization ID to join")
    organization_name: Optional[str] = Field(None, max_length=255, description="New organization name")
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        return v.lower().strip()
    
    @model_validator(mode='after')
    def validate_organization_choice(self):
        if self.action == "join_existing":
            if not self.organization_id:
                raise ValueError('Organization ID required when joining existing organization')
        elif self.action == "create_new":
            if not self.organization_name:
                raise ValueError('Organization name required when creating new organization')
        else:
            raise ValueError('Action must be join_existing or create_new')
        
        return self


class EnhancedUserRegistrationResponse(BaseSchema):
    """Response for enhanced user registration"""
    user: Dict[str, Any] = Field(description="Created user information")
    organization: Dict[str, Any] = Field(description="Organization information")
    is_new_organization: bool = Field(description="Whether organization was newly created")
    access_token: str = Field(description="JWT token for login")
    message: str = Field(description="Success message")


# Organization Member Statistics

class OrganizationMemberStatsResponse(BaseSchema):
    """Organization member statistics"""
    total_members: int = Field(description="Total active members")
    admin_count: int = Field(description="Number of admin members")
    member_count: int = Field(description="Number of regular members")
    pending_invitations: int = Field(description="Number of pending invitations")
    has_admin: bool = Field(description="Whether organization has at least one admin")


# Domain Validation Schemas

class DomainCheckRequest(BaseSchema):
    """Request to check domain availability"""
    domain: str = Field(description="Domain to check")
    
    @field_validator('domain')
    @classmethod
    def validate_domain(cls, v):
        domain = v.lower().strip()
        if not domain:
            raise ValueError('Domain cannot be empty')
        
        # Basic domain validation
        if not all(c.isalnum() or c in '.-' for c in domain):
            raise ValueError('Domain contains invalid characters')
        
        return domain


class DomainCheckResponse(BaseSchema):
    """Response for domain availability check"""
    domain: str = Field(description="Checked domain")
    available: bool = Field(description="Whether domain is available")
    existing_count: int = Field(description="Number of existing organizations using domain")
    existing_organizations: Optional[List[Dict[str, Any]]] = Field(
        None, 
        description="Existing organizations using domain"
    )
    reason: Optional[str] = Field(None, description="Reason if not available")


# Error Response Schemas

class MemberManagementError(BaseSchema):
    """Error response for member management operations"""
    error: Dict[str, Any] = Field(description="Error details")
    
    @classmethod
    def create_error(
        cls, 
        code: str, 
        message: str, 
        details: Optional[Dict[str, Any]] = None
    ):
        """Create standardized error response"""
        return cls(
            error={
                "code": code,
                "message": message,
                "details": details or {}
            }
        )


# Bulk Operations Schemas (for future extensibility)

class BulkInviteRequest(BaseSchema):
    """Request for bulk member invitations"""
    invitations: List[MemberInviteRequest] = Field(
        max_length=50,
        description="List of invitations to send"
    )
    
    @field_validator('invitations')
    @classmethod
    def validate_invitations(cls, v):
        if len(v) > 50:
            raise ValueError('Cannot send more than 50 invitations at once')
        
        # Check for duplicate emails
        emails = [inv.email for inv in v]
        if len(emails) != len(set(emails)):
            raise ValueError('Duplicate email addresses found')
        
        return v


class BulkInviteResponse(BaseSchema):
    """Response for bulk member invitations"""
    successful: List[MemberInviteResponse] = Field(description="Successfully created invitations")
    failed: List[Dict[str, Any]] = Field(description="Failed invitations with errors")
    summary: Dict[str, int] = Field(description="Summary statistics")