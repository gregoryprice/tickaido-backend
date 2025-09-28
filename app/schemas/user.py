#!/usr/bin/env python3
"""
User schemas for API validation and serialization
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import Field, field_validator, model_validator
from enum import Enum

from app.schemas.base import BaseSchema, BaseCreate, BaseUpdate, BaseResponse, EmailStr


class UserRoleSchema(str, Enum):
    """User roles enum schema"""
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"


# Request schemas
class UserCreateRequest(BaseCreate):
    """Schema for creating a new user"""
    email: EmailStr = Field(description="User email address")
    full_name: Optional[str] = Field(None, max_length=255, description="User's full name")
    password: Optional[str] = Field(None, min_length=8, description="User password (for local auth)")
    role: UserRoleSchema = Field(UserRoleSchema.MEMBER, description="User role")
    department: Optional[str] = Field(None, max_length=100, description="User's department")
    timezone: str = Field("UTC", max_length=50, description="User's timezone")
    language: str = Field("en", max_length=10, description="Preferred language")
    is_active: bool = Field(True, description="Whether user is active")
    external_auth_provider: Optional[str] = Field(None, description="External auth provider")
    external_auth_id: Optional[str] = Field(None, description="External auth ID")
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        return v.lower().strip()
    
    @model_validator(mode='after')
    def validate_auth_requirements(self):
        # Either password or external auth required
        if not self.password and not self.external_auth_provider:
            raise ValueError('Either password or external authentication must be provided')
        
        if self.external_auth_provider and not self.external_auth_id:
            raise ValueError('External auth ID required when using external authentication')
        
        return self


class UserUpdateRequest(BaseUpdate):
    """Schema for updating a user"""
    full_name: Optional[str] = Field(None, max_length=255, description="Full name")
    role: Optional[UserRoleSchema] = Field(None, description="User role")
    department: Optional[str] = Field(None, max_length=100, description="Department")
    timezone: Optional[str] = Field(None, max_length=50, description="Timezone")
    language: Optional[str] = Field(None, max_length=10, description="Language")
    is_active: Optional[bool] = Field(None, description="Active status")
    avatar_url: Optional[str] = Field(None, max_length=500, description="Avatar URL")
    preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences")
    


class UserPasswordChangeRequest(BaseSchema):
    """Schema for changing user password"""
    current_password: str = Field(description="Current password")
    new_password: str = Field(min_length=8, description="New password")
    confirm_password: str = Field(description="Confirm new password")
    
    @model_validator(mode='after')
    def validate_passwords_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError('New password and confirmation do not match')
        return self


class UserPermissionsUpdateRequest(BaseSchema):
    """Schema for updating user permissions"""
    permissions: List[str] = Field(description="List of permissions to grant")
    role: Optional[UserRoleSchema] = Field(None, description="Update role as well")
    is_admin: Optional[bool] = Field(None, description="Admin status")


class UserAPIKeyRequest(BaseSchema):
    """Schema for API key operations"""
    action: str = Field(description="Action: generate, revoke, or regenerate")
    
    @field_validator('action')
    @classmethod
    def validate_action(cls, v):
        if v not in ['generate', 'revoke', 'regenerate']:
            raise ValueError('Action must be generate, revoke, or regenerate')
        return v


# Response schemas
class UserPublicResponse(BaseResponse):
    """Public user information (safe for external exposure)"""
    email: str = Field(description="User email")
    full_name: Optional[str] = Field(None, description="Full name")
    display_name: str = Field(description="Display name")
    avatar_url: Optional[str] = Field(None, description="Avatar URL")
    department: Optional[str] = Field(None, description="Department")
    role: UserRoleSchema = Field(description="User role")
    is_active: bool = Field(description="Whether user is active")
    timezone: str = Field(description="User timezone")
    language: str = Field(description="User language")


class UserPrivateResponse(UserPublicResponse):
    """Private user information (for authenticated users)"""
    is_verified: bool = Field(description="Whether email is verified")
    last_login_at: Optional[datetime] = Field(None, description="Last login timestamp")
    login_count: int = Field(description="Total login count")
    preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences")
    external_auth_provider: Optional[str] = Field(None, description="External auth provider")
    can_login: bool = Field(description="Whether user can login")
    is_locked: bool = Field(description="Whether account is locked")


class UserAdminResponse(UserPrivateResponse):
    """Admin user information (for administrators)"""
    is_admin: bool = Field(description="Admin status")
    permissions: Optional[List[str]] = Field(None, description="User permissions")
    failed_login_attempts: int = Field(description="Failed login attempts")
    locked_until: Optional[datetime] = Field(None, description="Account locked until")
    api_key_created_at: Optional[datetime] = Field(None, description="API key creation date")
    api_key_last_used_at: Optional[datetime] = Field(None, description="API key last used")
    rate_limit_override: Optional[str] = Field(None, description="Custom rate limit")


class UserListResponse(UserPublicResponse):
    """User information for list views"""
    ticket_count: Optional[int] = Field(None, description="Number of tickets created")
    assigned_ticket_count: Optional[int] = Field(None, description="Number of assigned tickets")


class UserProfileResponse(UserPrivateResponse):
    """User profile information"""
    ticket_stats: Optional[Dict[str, int]] = Field(None, description="Ticket statistics")
    recent_activity: Optional[List[Dict[str, Any]]] = Field(None, description="Recent activity")


class UserResponse(BaseResponse):
    """Standard user response format used across all endpoints"""
    email: str = Field(description="User email")
    full_name: Optional[str] = Field(None, description="Full name")
    avatar_url: Optional[str] = Field(None, description="Avatar URL")
    role: Optional[str] = Field(None, description="Role within organization")
    is_active: bool = Field(description="Whether user is active")
    timezone: str = Field(description="User timezone")
    language: str = Field(description="User language")
    preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences")
    is_verified: bool = Field(description="Whether email is verified")
    last_login_at: Optional[datetime] = Field(None, description="Last login timestamp")
    
    # Organization/Company fields
    organization_id: Optional[UUID] = Field(None, description="Organization ID")
    organization_name: Optional[str] = Field(None, description="Organization name")
    organization_domain: Optional[str] = Field(None, description="Organization domain")
    organization_plan: Optional[str] = Field(None, description="Organization plan")
    organization_timezone: Optional[str] = Field(None, description="Organization timezone")
    invited_by_id: Optional[UUID] = Field(None, description="User who invited this member")
    invited_at: Optional[datetime] = Field(None, description="When user was invited to organization")
    joined_organization_at: Optional[datetime] = Field(None, description="When user joined organization")


class UserAPIKeyResponse(BaseSchema):
    """API key information response"""
    has_api_key: bool = Field(description="Whether user has an API key")
    api_key_created_at: Optional[datetime] = Field(None, description="API key creation date")
    api_key_last_used_at: Optional[datetime] = Field(None, description="API key last used")
    api_key: Optional[str] = Field(None, description="API key (only shown once after generation)")


class UserPermissionsResponse(BaseSchema):
    """User permissions response"""
    role: UserRoleSchema = Field(description="User role")
    is_admin: bool = Field(description="Admin status")
    permissions: List[str] = Field(description="User permissions")
    role_permissions: List[str] = Field(description="Role-based permissions")


class UserStatsResponse(BaseSchema):
    """User statistics response"""
    total_tickets: int = Field(description="Total tickets created")
    open_tickets: int = Field(description="Open tickets")
    resolved_tickets: int = Field(description="Resolved tickets")
    assigned_tickets: int = Field(description="Currently assigned tickets")
    avg_resolution_time_hours: Optional[float] = Field(None, description="Average resolution time")
    satisfaction_rating: Optional[float] = Field(None, description="Average satisfaction rating")
    login_streak_days: Optional[int] = Field(None, description="Current login streak")


# Bulk operation schemas
class UserBulkCreateRequest(BaseSchema):
    """Schema for bulk user creation"""
    users: List[UserCreateRequest] = Field(description="List of users to create")
    send_invitations: bool = Field(True, description="Whether to send invitation emails")
    default_role: UserRoleSchema = Field(UserRoleSchema.MEMBER, description="Default role for users")


class UserBulkUpdateRequest(BaseSchema):
    """Schema for bulk user updates"""
    user_ids: List[UUID] = Field(description="List of user IDs to update")
    updates: UserUpdateRequest = Field(description="Updates to apply")


class UserBulkDeactivateRequest(BaseSchema):
    """Schema for bulk user deactivation"""
    user_ids: List[UUID] = Field(description="List of user IDs to deactivate")
    reason: Optional[str] = Field(None, description="Reason for deactivation")
    transfer_tickets_to: Optional[UUID] = Field(None, description="Transfer tickets to this user")


# Search and filter schemas
class UserSearchParams(BaseSchema):
    """User search parameters"""
    q: Optional[str] = Field(None, description="Search query (name, email)")
    role: Optional[UserRoleSchema] = Field(None, description="Filter by role")
    department: Optional[str] = Field(None, description="Filter by department")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    is_verified: Optional[bool] = Field(None, description="Filter by verification status")
    external_auth_provider: Optional[str] = Field(None, description="Filter by auth provider")
    created_after: Optional[datetime] = Field(None, description="Created after date")
    created_before: Optional[datetime] = Field(None, description="Created before date")
    last_login_after: Optional[datetime] = Field(None, description="Last login after date")
    last_login_before: Optional[datetime] = Field(None, description="Last login before date")


class UserSortParams(BaseSchema):
    """User sorting parameters"""
    sort_by: str = Field(
        "created_at",
        description="Sort field",
        pattern="^(created_at|updated_at|email|full_name|last_login_at|login_count)$"
    )
    sort_order: str = Field("desc", pattern="^(asc|desc)$", description="Sort order")


# Email availability schemas
class EmailCheckRequest(BaseSchema):
    """Email availability check request"""
    email: EmailStr = Field(description="Email to check availability")


class EmailCheckResponse(BaseSchema):
    """Email availability check response"""
    email: str = Field(description="Email that was checked")
    available: bool = Field(description="Whether email is available for registration")
    message: str = Field(description="Human readable message about availability")


# Authentication schemas
class UserLoginRequest(BaseSchema):
    """User login request"""
    email: EmailStr = Field(description="User email")
    password: str = Field(description="User password")
    remember_me: bool = Field(False, description="Remember login session")


class UserLoginResponse(BaseSchema):
    """User login response"""
    access_token: str = Field(description="JWT access token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(description="Token expiration in seconds")
    user: UserPrivateResponse = Field(description="User information")


# Simplified auth schemas for basic auth endpoints
class UserCreate(BaseSchema):
    """Simple user creation schema for auth"""
    email: EmailStr = Field(description="User email address")
    full_name: str = Field(description="User's full name")
    password: str = Field(min_length=8, description="User password")
    organization_name: Optional[str] = Field(None, max_length=255, description="Organization/company name")
    
    @field_validator('organization_name')
    @classmethod
    def validate_organization_name(cls, v):
        if v:
            v = v.strip()
            if not v:
                raise ValueError('Organization name cannot be empty')
        return v


class UserLogin(BaseSchema):
    """Simple user login schema"""
    email: EmailStr = Field(description="User email")
    password: str = Field(description="User password")




class RefreshTokenRequest(BaseSchema):
    """Refresh token request schema"""
    refresh_token: str = Field(description="JWT refresh token")


class TokenResponse(BaseSchema):
    """JWT token response schema"""
    access_token: str = Field(description="JWT access token")
    refresh_token: str = Field(description="JWT refresh token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(description="Token expiration in seconds")
    user: 'UserResponse' = Field(description="User information")


class UserUpdate(BaseSchema):
    """Simple user update schema"""
    full_name: Optional[str] = Field(None, description="User's full name")
    password: Optional[str] = Field(None, min_length=8, description="New password")
    timezone: Optional[str] = Field(None, max_length=50, description="User's timezone")
    language: Optional[str] = Field(None, max_length=10, description="User's preferred language")


class UserRegistrationRequest(UserCreateRequest):
    """User registration request"""
    agree_to_terms: bool = Field(description="Agreement to terms of service")
    
    @field_validator('agree_to_terms')
    @classmethod
    def validate_terms(cls, v):
        if not v:
            raise ValueError('Must agree to terms of service')
        return v


class UserPasswordResetRequest(BaseSchema):
    """Password reset request"""
    email: EmailStr = Field(description="User email address")


class UserPasswordResetConfirmRequest(BaseSchema):
    """Password reset confirmation"""
    reset_token: str = Field(description="Password reset token")
    new_password: str = Field(min_length=8, description="New password")
    confirm_password: str = Field(description="Confirm new password")
    
    @model_validator(mode='after')
    def validate_passwords_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError('Password and confirmation do not match')
        return self


class UserEmailVerificationRequest(BaseSchema):
    """Email verification request"""
    verification_token: str = Field(description="Email verification token")


# Activity and audit schemas
class UserActivityResponse(BaseSchema):
    """User activity response"""
    activity_type: str = Field(description="Type of activity")
    timestamp: datetime = Field(description="Activity timestamp")
    description: str = Field(description="Activity description")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional activity data")
    ip_address: Optional[str] = Field(None, description="IP address")
    user_agent: Optional[str] = Field(None, description="User agent")


class UserAuditLogResponse(BaseSchema):
    """User audit log response"""
    user_id: UUID = Field(description="User ID")
    action: str = Field(description="Action performed")
    timestamp: datetime = Field(description="Action timestamp")
    performed_by: UUID = Field(description="User who performed the action")
    changes: Optional[Dict[str, Any]] = Field(None, description="Changes made")
    reason: Optional[str] = Field(None, description="Reason for action")


# Avatar schemas
class AvatarUploadRequest(BaseSchema):
    """Schema for avatar upload request (metadata only)"""
    filename: Optional[str] = Field(None, max_length=255, description="Original filename")
    
    @field_validator('filename')
    @classmethod
    def validate_filename(cls, v):
        if v is not None:
            v = v.strip()
            if not v:
                return None
            # Basic filename validation
            if any(char in v for char in '<>:"|?*'):
                raise ValueError('Filename contains invalid characters')
            # Check for valid image extensions
            valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.heic', '.webp'}
            if not any(v.lower().endswith(ext) for ext in valid_extensions):
                raise ValueError(f'Invalid file extension. Allowed: {", ".join(valid_extensions)}')
        return v


class AvatarResponse(BaseResponse):
    """Schema for avatar response"""
    user_id: UUID = Field(description="User ID")
    avatar_url: str = Field(description="Avatar URL")
    filename: Optional[str] = Field(None, description="Original filename")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    upload_date: datetime = Field(description="Upload timestamp")
    thumbnail_sizes: Optional[Dict[str, str]] = Field(
        None,
        description="Available thumbnail sizes with their URLs"
    )


class AvatarDeleteResponse(BaseSchema):
    """Schema for avatar deletion response"""
    user_id: UUID = Field(description="User ID")
    deleted: bool = Field(description="Whether avatar was successfully deleted")
    message: str = Field(description="Status message")