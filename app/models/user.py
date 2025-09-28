#!/usr/bin/env python3
"""
User model for authentication and user management
"""

import enum
from datetime import datetime, timezone
from typing import List
from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


# Import OrganizationRole from organization_invitation module
from app.models.organization_invitation import OrganizationRole


class UserRole(enum.Enum):
    """User roles for access control"""
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"


class User(BaseModel):
    """
    User model for authentication and authorization.
    Supports both human users and API users.
    """
    
    __tablename__ = "users"
    
    # Basic user information
    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="User email address"
    )
    
    
    full_name = Column(
        String(255),
        nullable=True,
        comment="User's full name"
    )
    
    # Authentication
    password_hash = Column(
        String(255),
        nullable=True,
        comment="Hashed password (null for external auth)"
    )
    
    # User status
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Whether user account is active"
    )
    
    is_verified = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether email is verified"
    )
    
    is_admin = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="Admin privileges"
    )
    
    # Role and permissions
    role = Column(
        SQLEnum(UserRole),
        default=UserRole.MEMBER,
        nullable=False,
        index=True,
        comment="User role"
    )
    
    permissions = Column(
        JSON,
        nullable=True,
        comment="JSON array of specific permissions"
    )
    
    # Authentication tracking
    last_login_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last login timestamp"
    )
    
    login_count = Column(
        String(50),
        default="0",
        nullable=False,
        comment="Total number of logins"
    )
    
    failed_login_attempts = Column(
        String(50),
        default="0",
        nullable=False,
        comment="Failed login attempts counter"
    )
    
    locked_until = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Account locked until timestamp"
    )
    
    # External authentication
    external_auth_provider = Column(
        String(50),
        nullable=True,
        comment="External auth provider (google, microsoft, etc.)"
    )
    
    external_auth_id = Column(
        String(255),
        nullable=True,
        index=True,
        comment="External authentication ID"
    )
    
    # Clerk integration
    clerk_id = Column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
        comment="Clerk user ID for authentication service integration"
    )
    
    # User preferences
    preferences = Column(
        JSON,
        nullable=True,
        comment="User preferences as JSON"
    )
    
    timezone = Column(
        String(50),
        default="UTC",
        nullable=False,
        comment="User's timezone"
    )
    
    language = Column(
        String(10),
        default="en",
        nullable=False,
        comment="Preferred language code"
    )
    
    # API usage for API users
    api_key_hash = Column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
        comment="Hashed API key for programmatic access"
    )
    
    api_key_created_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="API key creation timestamp"
    )
    
    api_key_last_used_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="API key last used timestamp"
    )
    
    rate_limit_override = Column(
        String(50),
        nullable=True,
        comment="Custom rate limit for this user"
    )
    
    # Profile information
    avatar_url = Column(
        String(500),
        nullable=True,
        comment="Profile picture URL"
    )
    
    
    department = Column(
        String(100),
        nullable=True,
        comment="User's department or team"
    )
    
    # Organization relationship
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey('organizations.id'),
        nullable=True,  # Users can exist without organization during invitation
        index=True,
        comment="Organization/company this user belongs to"
    )
    
    # Organization membership tracking
    organization_role = Column(
        SQLEnum(OrganizationRole),
        default=OrganizationRole.MEMBER,
        nullable=True,  # Null when not part of any organization
        comment="Role within the user's organization"
    )
    
    # Membership tracking
    invited_by_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id'),
        nullable=True,
        comment="User who invited this member"
    )
    
    invited_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When user was invited to organization"
    )
    
    joined_organization_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When user joined the organization"
    )
    
    # Relationships
    tickets = relationship(
        "Ticket",
        back_populates="creator",
        foreign_keys="Ticket.created_by_id"
    )
    
    assigned_tickets = relationship(
        "Ticket",
        foreign_keys="Ticket.assigned_to_id"
    )
    
    uploaded_files = relationship(
        "File",
        back_populates="uploader"
    )
    
    organization = relationship(
        "Organization",
        back_populates="users"
    )
    
    # Member management relationships
    invited_by = relationship(
        "User", 
        remote_side="User.id",
        back_populates="invited_members"
    )
    
    invited_members = relationship(
        "User", 
        remote_side="User.invited_by_id",
        back_populates="invited_by"
    )
    
    sent_invitations = relationship(
        "OrganizationInvitation",
        back_populates="invited_by",
        foreign_keys="OrganizationInvitation.invited_by_id"
    )
    
    # API token management
    api_tokens = relationship(
        "APIToken",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
    
    @property
    def display_name(self) -> str:
        """Get display name for user"""
        return self.full_name or self.email.split('@')[0]
    
    @property
    def is_locked(self) -> bool:
        """Check if account is locked"""
        if not self.locked_until:
            return False
        return datetime.now(timezone.utc) < self.locked_until.replace(tzinfo=timezone.utc)
    
    @property
    def can_login(self) -> bool:
        """Check if user can login"""
        return self.is_active and self.is_verified and not self.is_locked
    
    def has_permission(self, permission: str) -> bool:
        """
        Check if user has specific permission.
        
        Args:
            permission: Permission string to check
            
        Returns:
            bool: True if user has permission
        """
        # Admin users have all permissions
        if self.is_admin:
            return True
        
        # Check role-based permissions
        role_permissions = self._get_role_permissions()
        if permission in role_permissions:
            return True
        
        # Check specific permissions
        if self.permissions and permission in self.permissions:
            return True
        
        return False
    
    def _get_role_permissions(self) -> List[str]:
        """Get permissions for user's role"""
        role_permissions = {
            UserRole.ADMIN: ["*"],  # All permissions
            UserRole.MEMBER: [
                "tickets:create", "tickets:read", "tickets:update",
                "files:upload", "files:download", "files:read",
                "chat:access", "websocket:connect", "api:access"
            ]
        }
        
        return role_permissions.get(self.role, [])
    
    def record_login(self):
        """Record successful login"""
        self.last_login_at = datetime.now(timezone.utc)
        self.login_count = str(int(self.login_count) + 1)
        self.failed_login_attempts = "0"
        self.locked_until = None
    
    def record_failed_login(self, max_attempts: int = 5, lockout_minutes: int = 30):
        """
        Record failed login attempt and lock account if needed.
        
        Args:
            max_attempts: Maximum failed attempts before lockout
            lockout_minutes: Minutes to lock account
        """
        self.failed_login_attempts = str(int(self.failed_login_attempts) + 1)
        
        if int(self.failed_login_attempts) >= max_attempts:
            from datetime import timedelta
            self.locked_until = datetime.now(timezone.utc) + timedelta(minutes=lockout_minutes)
    
    def unlock_account(self):
        """Unlock user account"""
        self.failed_login_attempts = "0"
        self.locked_until = None
    
    def update_api_key_usage(self):
        """Update API key last used timestamp"""
        self.api_key_last_used_at = datetime.now(timezone.utc)
    
    def can_generate_api_token(self) -> bool:
        """Check if user can generate API tokens"""
        return self.has_permission("api:generate") and self.is_active and not self.is_locked
    
    # Organization membership methods
    def is_organization_admin(self) -> bool:
        """Check if user is an admin in their organization"""
        return self.organization_role == OrganizationRole.ADMIN
    
    def is_organization_member(self) -> bool:
        """Check if user is a member of an organization"""
        return self.organization_id is not None and self.organization_role is not None
    
    
    def join_organization(self, organization_id: UUID, role: OrganizationRole = OrganizationRole.MEMBER, invited_by_id: UUID = None):
        """Join an organization with specified role"""
        self.organization_id = organization_id
        self.organization_role = role
        self.joined_organization_at = datetime.now(timezone.utc)
        if invited_by_id:
            self.invited_by_id = invited_by_id
            # invited_at should already be set when invitation was created
    
    def leave_organization(self):
        """Leave current organization"""
        self.organization_id = None
        self.organization_role = None
        self.invited_by_id = None
        self.invited_at = None
        self.joined_organization_at = None
    
    def promote_to_admin(self):
        """Promote user to organization admin"""
        if self.is_organization_member():
            self.organization_role = OrganizationRole.ADMIN
    
    def demote_to_member(self):
        """Demote user to organization member"""
        if self.is_organization_member():
            self.organization_role = OrganizationRole.MEMBER
    
    def to_dict(self, include_sensitive: bool = False) -> dict:
        """
        Convert user to dictionary, optionally excluding sensitive data.
        
        Args:
            include_sensitive: Include password hash and API keys
            
        Returns:
            dict: User data
        """
        data = super().to_dict()
        
        if not include_sensitive:
            # Remove sensitive fields
            sensitive_fields = [
                'password_hash', 'api_key_hash', 'failed_login_attempts'
            ]
            for field in sensitive_fields:
                data.pop(field, None)
        
        # Add computed properties
        data['display_name'] = self.display_name
        data['can_login'] = self.can_login
        data['is_locked'] = self.is_locked
        
        # Add status field for backward compatibility with tests
        data['status'] = 'active' if self.is_active else 'inactive'
        
        return data