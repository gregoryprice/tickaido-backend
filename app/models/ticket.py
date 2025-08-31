#!/usr/bin/env python3
"""
Ticket model for support ticket management
"""

import enum
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, String, Boolean, DateTime, Text, Enum as SQLEnum, JSON, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class TicketStatus(enum.Enum):
    """Ticket status options"""
    NEW = "new"
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    PENDING = "pending"
    RESOLVED = "resolved"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class TicketPriority(enum.Enum):
    """Ticket priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TicketCategory(enum.Enum):
    """Ticket categories for classification"""
    TECHNICAL = "technical"
    BILLING = "billing"
    FEATURE_REQUEST = "feature_request"
    BUG = "bug"
    USER_ACCESS = "user_access"
    GENERAL = "general"
    INTEGRATION = "integration"
    PERFORMANCE = "performance"
    SECURITY = "security"


class DBTicket(BaseModel):
    """
    Support ticket model with AI-powered categorization and routing.
    Supports file attachments, integration routing, and comprehensive metadata.
    """
    
    __tablename__ = "tickets"
    
    # Basic ticket information
    title = Column(
        String(500),
        nullable=False,
        index=True,
        comment="Ticket title/subject"
    )
    
    description = Column(
        Text,
        nullable=False,
        comment="Detailed ticket description"
    )
    
    # Ticket classification
    status = Column(
        SQLEnum(TicketStatus),
        default=TicketStatus.NEW,
        nullable=False,
        index=True,
        comment="Current ticket status"
    )
    
    priority = Column(
        SQLEnum(TicketPriority),
        default=TicketPriority.MEDIUM,
        nullable=False,
        index=True,
        comment="Ticket priority level"
    )
    
    category = Column(
        SQLEnum(TicketCategory),
        default=TicketCategory.GENERAL,
        nullable=False,
        index=True,
        comment="Issue category"
    )
    
    subcategory = Column(
        String(100),
        nullable=True,
        comment="Specific subcategory within main category"
    )
    
    # User relationships
    created_by_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        comment="User who created the ticket"
    )
    
    assigned_to_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        index=True,
        comment="User assigned to handle the ticket"
    )
    
    # Department and routing
    department = Column(
        String(100),
        nullable=True,
        index=True,
        comment="Department responsible for ticket"
    )
    
    integration_routing = Column(
        String(100),
        nullable=True,
        index=True,
        comment="Integration platform for routing (jira, servicenow, etc.)"
    )
    
    external_ticket_id = Column(
        String(255),
        nullable=True,
        index=True,
        comment="External ticket ID in integration system"
    )
    
    external_ticket_url = Column(
        String(500),
        nullable=True,
        comment="URL to external ticket"
    )
    
    # AI analysis metadata
    ai_confidence_score = Column(
        String(10),
        nullable=True,
        comment="AI confidence score for categorization (0-1)"
    )
    
    ai_reasoning = Column(
        Text,
        nullable=True,
        comment="AI explanation for categorization decisions"
    )
    
    ai_tags = Column(
        JSON,
        nullable=True,
        comment="AI-generated tags for the ticket"
    )
    
    ai_keywords = Column(
        JSON,
        nullable=True,
        comment="Key terms detected by AI"
    )
    
    ai_similar_patterns = Column(
        JSON,
        nullable=True,
        comment="Similar issue patterns identified by AI"
    )
    
    # Business impact assessment
    urgency = Column(
        SQLEnum(TicketPriority),
        default=TicketPriority.MEDIUM,
        nullable=False,
        comment="Urgency level for resolution"
    )
    
    business_impact = Column(
        String(50),
        default="low",
        nullable=False,
        comment="Assessed business impact level"
    )
    
    customer_segment = Column(
        String(100),
        nullable=True,
        comment="Affected customer segment"
    )
    
    estimated_effort = Column(
        String(50),
        nullable=True,
        comment="Estimated effort level (minimal, moderate, significant, major)"
    )
    
    estimated_resolution_time = Column(
        String(100),
        nullable=True,
        comment="Estimated time to resolve"
    )
    
    # Resolution tracking
    resolution_summary = Column(
        Text,
        nullable=True,
        comment="Summary of how the ticket was resolved"
    )
    
    resolution_time_minutes = Column(
        Integer,
        nullable=True,
        comment="Actual resolution time in minutes"
    )
    
    first_response_at = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Timestamp of first response"
    )
    
    resolved_at = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Timestamp when ticket was resolved"
    )
    
    closed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Timestamp when ticket was closed"
    )
    
    # Communication tracking
    last_activity_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
        comment="Last activity timestamp"
    )
    
    communication_count = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of communications on this ticket"
    )
    
    # Customer satisfaction
    satisfaction_rating = Column(
        Integer,
        nullable=True,
        comment="Customer satisfaction rating (1-5)"
    )
    
    satisfaction_feedback = Column(
        Text,
        nullable=True,
        comment="Customer feedback on resolution"
    )
    
    # Escalation tracking
    escalation_level = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Current escalation level"
    )
    
    escalated_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when ticket was escalated"
    )
    
    escalated_by_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        comment="User who escalated the ticket"
    )
    
    escalation_reason = Column(
        Text,
        nullable=True,
        comment="Reason for escalation"
    )
    
    # Source tracking
    source_channel = Column(
        String(50),
        default="web",
        nullable=False,
        comment="Channel where ticket was created (web, email, phone, chat)"
    )
    
    source_details = Column(
        JSON,
        nullable=True,
        comment="Additional source-specific details"
    )
    
    # Custom fields and metadata
    custom_fields = Column(
        JSON,
        nullable=True,
        comment="Custom fields for organization-specific data"
    )
    
    internal_notes = Column(
        Text,
        nullable=True,
        comment="Internal notes not visible to customer"
    )
    
    # SLA tracking
    sla_due_date = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="SLA due date for resolution"
    )
    
    sla_breached = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether SLA has been breached"
    )
    
    # Knowledge base integration
    related_kb_articles = Column(
        JSON,
        nullable=True,
        comment="Related knowledge base articles"
    )
    
    # Relationships
    creator = relationship(
        "DBUser",
        back_populates="tickets",
        foreign_keys=[created_by_id]
    )
    
    assignee = relationship(
        "DBUser",
        back_populates="assigned_tickets", 
        foreign_keys=[assigned_to_id]
    )
    
    escalated_by = relationship(
        "DBUser",
        foreign_keys=[escalated_by_id]
    )
    
    files = relationship(
        "DBFile",
        back_populates="ticket",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<DBTicket(id={self.id}, title={self.title[:50]}, status={self.status})>"
    
    @property
    def display_title(self) -> str:
        """Get display title with truncation"""
        return self.title[:100] + "..." if len(self.title) > 100 else self.title
    
    @property
    def is_overdue(self) -> bool:
        """Check if ticket is overdue based on SLA"""
        if not self.sla_due_date:
            return False
        return datetime.now(timezone.utc) > self.sla_due_date.replace(tzinfo=timezone.utc)
    
    @property
    def is_high_priority(self) -> bool:
        """Check if ticket is high priority"""
        return self.priority in [TicketPriority.HIGH, TicketPriority.CRITICAL]
    
    @property
    def resolution_time_hours(self) -> Optional[float]:
        """Get resolution time in hours"""
        if self.resolution_time_minutes:
            return self.resolution_time_minutes / 60.0
        return None
    
    @property
    def age_in_hours(self) -> float:
        """Get ticket age in hours"""
        if self.created_at:
            delta = datetime.now(timezone.utc) - self.created_at.replace(tzinfo=timezone.utc)
            return delta.total_seconds() / 3600.0
        return 0.0
    
    def can_be_closed(self) -> bool:
        """Check if ticket can be closed"""
        return self.status in [TicketStatus.RESOLVED, TicketStatus.PENDING]
    
    def update_status(self, new_status: TicketStatus, user_id: Optional[str] = None):
        """Update ticket status with timestamp tracking"""
        old_status = self.status
        self.status = new_status
        self.last_activity_at = datetime.now(timezone.utc)
        
        # Set specific timestamps based on status
        if new_status == TicketStatus.RESOLVED and old_status != TicketStatus.RESOLVED:
            self.resolved_at = datetime.now(timezone.utc)
            if self.created_at:
                delta = self.resolved_at - self.created_at.replace(tzinfo=timezone.utc)
                self.resolution_time_minutes = int(delta.total_seconds() / 60)
        
        elif new_status == TicketStatus.CLOSED and old_status != TicketStatus.CLOSED:
            self.closed_at = datetime.now(timezone.utc)
    
    def escalate(self, level: int, reason: str, user_id: str):
        """Escalate ticket to higher level"""
        self.escalation_level = level
        self.escalated_at = datetime.now(timezone.utc)
        self.escalated_by_id = user_id
        self.escalation_reason = reason
        self.last_activity_at = datetime.now(timezone.utc)
    
    def record_first_response(self):
        """Record timestamp of first response"""
        if not self.first_response_at:
            self.first_response_at = datetime.now(timezone.utc)
    
    def increment_communication(self):
        """Increment communication counter"""
        self.communication_count += 1
        self.last_activity_at = datetime.now(timezone.utc)
    
    def set_satisfaction(self, rating: int, feedback: Optional[str] = None):
        """Set customer satisfaction rating"""
        if 1 <= rating <= 5:
            self.satisfaction_rating = rating
            if feedback:
                self.satisfaction_feedback = feedback
    
    def to_dict(self, include_ai_data: bool = True, include_internal: bool = False) -> dict:
        """
        Convert ticket to dictionary with optional field filtering.
        
        Args:
            include_ai_data: Include AI analysis data
            include_internal: Include internal notes and metadata
            
        Returns:
            dict: Ticket data
        """
        data = super().to_dict()
        
        # Remove sensitive fields if not internal
        if not include_internal:
            internal_fields = [
                'internal_notes', 'escalation_reason', 'custom_fields'
            ]
            for field in internal_fields:
                data.pop(field, None)
        
        # Remove AI data if not requested
        if not include_ai_data:
            ai_fields = [
                'ai_confidence_score', 'ai_reasoning', 'ai_tags', 
                'ai_keywords', 'ai_similar_patterns'
            ]
            for field in ai_fields:
                data.pop(field, None)
        
        # Add computed properties
        data['display_title'] = self.display_title
        data['is_overdue'] = self.is_overdue
        data['is_high_priority'] = self.is_high_priority
        data['resolution_time_hours'] = self.resolution_time_hours
        data['age_in_hours'] = self.age_in_hours
        data['can_be_closed'] = self.can_be_closed()
        
        return data