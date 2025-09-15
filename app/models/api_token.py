#!/usr/bin/env python3
"""
API Token model for organization-scoped programmatic access
"""

from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from uuid import uuid4

from app.models.base import BaseModel


class APIToken(BaseModel):
    """
    API Token model for organization-scoped programmatic access.
    Replaces the simple api_key_hash system with a more sophisticated token management system.
    """
    
    __tablename__ = "api_tokens"
    
    # Token metadata
    name = Column(
        String(255),
        nullable=False,
        comment="User-friendly name for the token"
    )
    
    token_hash = Column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="Hashed token value (raw token never stored)"
    )
    
    # Relationships
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        comment="User who owns this token"
    )
    
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey('organizations.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        comment="Organization this token is scoped to"
    )
    
    # Permissions and security
    permissions = Column(
        JSON,
        nullable=True,
        comment="JSON array of permissions for this token"
    )
    
    # Token lifecycle
    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
        comment="Token expiration timestamp"
    )
    
    last_used_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last time this token was used"
    )
    
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Whether token is active and can be used"
    )
    
    # Relationships
    user = relationship(
        "User",
        back_populates="api_tokens"
    )
    
    organization = relationship(
        "Organization",
        back_populates="api_tokens"
    )
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='unique_user_token_name'),
        UniqueConstraint('token_hash', name='unique_token_hash'),
    )
    
    def __repr__(self):
        return f"<APIToken(id={self.id}, name={self.name}, user_id={self.user_id}, org_id={self.organization_id})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if token has expired"""
        return datetime.now(timezone.utc) > self.expires_at.replace(tzinfo=timezone.utc)
    
    @property
    def can_be_used(self) -> bool:
        """Check if token can be used (active and not expired)"""
        return self.is_active and not self.is_expired
    
    def revoke(self):
        """Revoke the token (mark as inactive)"""
        self.is_active = False
    
    def update_last_used(self):
        """Update last used timestamp"""
        self.last_used_at = datetime.now(timezone.utc)
    
    def has_permission(self, permission: str) -> bool:
        """
        Check if token has specific permission.
        
        Args:
            permission: Permission string to check
            
        Returns:
            bool: True if token has permission
        """
        if not self.permissions:
            return False
        
        # Check for wildcard permission
        if "*" in self.permissions:
            return True
        
        # Check for specific permission
        return permission in self.permissions
    
    def to_dict(self, include_hash: bool = False) -> dict:
        """
        Convert token to dictionary, optionally excluding sensitive data.
        
        Args:
            include_hash: Include token hash (for internal use only)
            
        Returns:
            dict: Token data
        """
        data = super().to_dict()
        
        if not include_hash:
            # Remove sensitive fields
            data.pop('token_hash', None)
        
        # Add computed properties
        data['is_expired'] = self.is_expired
        data['can_be_used'] = self.can_be_used
        
        return data