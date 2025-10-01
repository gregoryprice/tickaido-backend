#!/usr/bin/env python3
"""
API Token schemas for request validation and response serialization
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.base import BaseSchema


class APITokenGenerationRequest(BaseSchema):
    """Schema for API token generation request"""
    name: str = Field(description="User-friendly name for the token", min_length=1, max_length=255)
    permissions: Optional[List[str]] = Field(default=None, description="List of permissions for the token")
    expires_days: int = Field(default=365, description="Token expiration in days", ge=1, le=365)
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Validate token name"""
        return v.strip()


class APITokenResponse(BaseSchema):
    """Schema for API token response (includes the actual token - shown only once)"""
    token: str = Field(description="The API token (shown only once)")
    id: UUID = Field(description="Token ID for management")
    name: str = Field(description="Token name")
    permissions: List[str] = Field(description="Token permissions")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last updated timestamp")
    expires_at: datetime = Field(description="Token expiration timestamp")
    last_used_at: Optional[datetime] = Field(description="Last used timestamp")
    is_active: bool = Field(description="Whether token is active")
    is_expired: bool = Field(description="Whether token has expired")
    organization_id: UUID = Field(description="Organization ID this token is scoped to")
    organization_name: str = Field(description="Organization name")
    warning: str = Field(default="Save this token securely - it will not be displayed again!", description="Security warning")


class APITokenListItem(BaseSchema):
    """Schema for API token list item (no actual token value)"""
    id: UUID = Field(description="Token ID")
    name: str = Field(description="Token name")
    permissions: List[str] = Field(description="Token permissions")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last updated timestamp")
    expires_at: datetime = Field(description="Expiration timestamp")
    last_used_at: Optional[datetime] = Field(description="Last used timestamp")
    is_active: bool = Field(description="Whether token is active")
    is_expired: bool = Field(description="Whether token has expired")
    organization_id: UUID = Field(description="Organization ID")
    organization_name: str = Field(description="Organization name")


class APITokenListResponse(BaseSchema):
    """Schema for API token list response"""
    tokens: List[APITokenListItem] = Field(description="List of user's API tokens")
    total_count: int = Field(description="Total number of tokens")
    active_count: int = Field(description="Number of active tokens")
    expired_count: int = Field(description="Number of expired tokens")


class APITokenRevokeResponse(BaseSchema):
    """Schema for API token revocation response"""
    message: str = Field(description="Success message")
    id: UUID = Field(description="Revoked token ID")
    revoked_at: datetime = Field(description="Revocation timestamp")


class APITokenUpdateRequest(BaseSchema):
    """Schema for full API token update (PUT) request"""
    name: str = Field(description="User-friendly name for the token", min_length=1, max_length=255)
    permissions: List[str] = Field(description="List of permissions for the token")
    expires_days: Optional[int] = Field(default=None, description="Token expiration in days from now", ge=1, le=365)
    is_active: bool = Field(default=True, description="Whether the token should be active")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Validate token name"""
        return v.strip()


class APITokenPartialUpdateRequest(BaseSchema):
    """Schema for partial API token update (PATCH) request"""
    name: Optional[str] = Field(default=None, description="User-friendly name for the token", min_length=1, max_length=255)
    permissions: Optional[List[str]] = Field(default=None, description="List of permissions for the token")
    expires_days: Optional[int] = Field(default=None, description="Token expiration in days from now", ge=1, le=365)
    is_active: Optional[bool] = Field(default=None, description="Whether the token should be active")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Validate token name"""
        if v is not None:
            return v.strip()
        return v


