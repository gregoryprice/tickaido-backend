#!/usr/bin/env python3
"""
Organization Invitation model for managing member invitations
"""

import enum
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class InvitationStatus(enum.Enum):
    """Invitation status enum"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class OrganizationRole(enum.Enum):
    """Organization role enum for member permissions"""
    ADMIN = "admin"     # Full organization management
    MEMBER = "member"   # Standard member access


class OrganizationInvitation(BaseModel):
    """
    Organization invitation model for managing member invitations.
    Handles the invitation workflow from creation to acceptance/rejection.
    """
    
    __tablename__ = "organization_invitations"
    
    # Organization and target information
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey('organizations.id'),
        nullable=False,
        index=True,
        comment="Organization extending the invitation"
    )
    
    email = Column(
        String(255),
        nullable=False,
        index=True,
        comment="Email address of invited user"
    )
    
    role = Column(
        SQLEnum(OrganizationRole),
        default=OrganizationRole.MEMBER,
        nullable=False,
        comment="Role to assign upon acceptance"
    )
    
    # Invitation tracking
    invited_by_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id'),
        nullable=False,
        comment="User who sent the invitation"
    )
    
    invitation_token = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Secure token for invitation acceptance"
    )
    
    status = Column(
        SQLEnum(InvitationStatus),
        default=InvitationStatus.PENDING,
        nullable=False,
        index=True,
        comment="Current invitation status"
    )
    
    # Timing information
    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
        comment="When invitation expires (default 7 days)"
    )
    
    accepted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When invitation was accepted"
    )
    
    declined_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When invitation was declined"
    )
    
    cancelled_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When invitation was cancelled"
    )
    
    # Optional custom message
    message = Column(
        String(1000),
        nullable=True,
        comment="Custom invitation message from inviter"
    )
    
    # Relationships
    organization = relationship(
        "Organization",
        back_populates="invitations"
    )
    
    invited_by = relationship(
        "User",
        foreign_keys=[invited_by_id],
        back_populates="sent_invitations"
    )
    
    def __repr__(self):
        return f"<OrganizationInvitation(id={self.id}, email={self.email}, status={self.status})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if invitation has expired"""
        if self.status in [InvitationStatus.ACCEPTED, InvitationStatus.DECLINED, InvitationStatus.CANCELLED]:
            return False
        return datetime.now(timezone.utc) > self.expires_at.replace(tzinfo=timezone.utc)
    
    @property
    def is_pending(self) -> bool:
        """Check if invitation is pending and not expired"""
        return self.status == InvitationStatus.PENDING and not self.is_expired
    
    @property
    def days_until_expiry(self) -> int:
        """Get days until expiry (negative if expired)"""
        if self.expires_at:
            delta = self.expires_at.replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)
            return delta.days
        return 0
    
    def accept(self, user_id: Optional[UUID] = None) -> None:
        """Mark invitation as accepted"""
        self.status = InvitationStatus.ACCEPTED
        self.accepted_at = datetime.now(timezone.utc)
        if user_id:
            # Could add accepted_by_id field if needed for tracking
            pass
    
    def decline(self) -> None:
        """Mark invitation as declined"""
        self.status = InvitationStatus.DECLINED
        self.declined_at = datetime.now(timezone.utc)
    
    def cancel(self) -> None:
        """Mark invitation as cancelled"""
        self.status = InvitationStatus.CANCELLED
        self.cancelled_at = datetime.now(timezone.utc)
    
    def expire(self) -> None:
        """Mark invitation as expired"""
        self.status = InvitationStatus.EXPIRED
    
    @classmethod
    def create_default_expiry(cls) -> datetime:
        """Create default expiry date (7 days from now)"""
        return datetime.now(timezone.utc) + timedelta(days=7)
    
    def to_dict(self, include_token: bool = False) -> dict:
        """
        Convert invitation to dictionary.
        
        Args:
            include_token: Whether to include the invitation token
            
        Returns:
            dict: Invitation data
        """
        data = super().to_dict()
        
        # Add computed properties
        data['is_expired'] = self.is_expired
        data['is_pending'] = self.is_pending
        data['days_until_expiry'] = self.days_until_expiry
        
        # Optionally exclude sensitive token
        if not include_token:
            data.pop('invitation_token', None)
        
        return data