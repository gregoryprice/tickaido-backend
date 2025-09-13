#!/usr/bin/env python3
"""
Ticket schemas for API validation and serialization
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import Field, field_validator, model_validator, computed_field
from enum import Enum

from app.schemas.base import BaseSchema, BaseCreate, BaseUpdate, BaseResponse


class TicketStatusSchema(str, Enum):
    """Ticket status enum schema"""
    NEW = "new"
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    PENDING = "pending"
    RESOLVED = "resolved"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class TicketPrioritySchema(str, Enum):
    """Ticket priority enum schema"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TicketCategorySchema(str, Enum):
    """Ticket category enum schema"""
    TECHNICAL = "technical"
    BILLING = "billing"
    FEATURE_REQUEST = "feature_request"
    BUG = "bug"
    USER_ACCESS = "user_access"
    GENERAL = "general"
    INTEGRATION = "integration"
    PERFORMANCE = "performance"
    SECURITY = "security"


# Request schemas
class TicketCreateRequest(BaseCreate):
    """Schema for creating a new ticket"""
    title: str = Field(max_length=500, description="Ticket title/subject")
    description: str = Field(description="Detailed ticket description")
    category: TicketCategorySchema = Field(TicketCategorySchema.GENERAL, description="Issue category")
    priority: Optional[TicketPrioritySchema] = Field(None, description="Priority level")
    urgency: TicketPrioritySchema = Field(TicketPrioritySchema.MEDIUM, description="Urgency level")
    department: Optional[str] = Field(None, max_length=100, description="Target department")
    assigned_to_id: Optional[UUID] = Field(None, description="Assign to specific user")
    integration_id: Optional[UUID] = Field(None, description="Integration ID for external ticket creation")
    create_externally: bool = Field(True, description="Create ticket in external system when integration specified")
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="Custom field values")
    file_ids: Optional[List[UUID]] = Field(None, description="Attached file IDs")
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        if not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip()
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v):
        if not v.strip():
            raise ValueError('Description cannot be empty')
        return v.strip()


class TicketUpdateRequest(BaseUpdate):
    """Schema for updating a ticket"""
    title: Optional[str] = Field(None, max_length=500, description="Ticket title")
    description: Optional[str] = Field(None, description="Ticket description")
    category: Optional[TicketCategorySchema] = Field(None, description="Issue category")
    priority: Optional[TicketPrioritySchema] = Field(None, description="Priority level")
    urgency: Optional[TicketPrioritySchema] = Field(None, description="Urgency level")
    status: Optional[TicketStatusSchema] = Field(None, description="Ticket status")
    department: Optional[str] = Field(None, max_length=100, description="Department")
    assigned_to_id: Optional[UUID] = Field(None, description="Assigned user ID")
    integration_id: Optional[UUID] = Field(None, description="Integration ID for external ticket routing")
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="Custom field values")
    internal_notes: Optional[str] = Field(None, description="Internal notes")
    resolution_summary: Optional[str] = Field(None, description="Resolution summary")
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip() if v else None
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Description cannot be empty')
        return v.strip() if v else None


class TicketStatusUpdateRequest(BaseSchema):
    """Schema for updating ticket status"""
    status: TicketStatusSchema = Field(description="New ticket status")
    resolution_summary: Optional[str] = Field(None, description="Resolution summary for resolved tickets")
    internal_notes: Optional[str] = Field(None, description="Internal notes about status change")
    
    @model_validator(mode='after')
    def validate_resolution_summary(self):
        if self.status in [TicketStatusSchema.RESOLVED, TicketStatusSchema.CLOSED]:
            if not self.resolution_summary or not self.resolution_summary.strip():
                raise ValueError('Resolution summary required when resolving or closing ticket')
        return self


class TicketAssignmentRequest(BaseSchema):
    """Schema for ticket assignment"""
    assigned_to_id: Optional[UUID] = Field(None, description="User to assign ticket to (null to unassign)")
    reason: Optional[str] = Field(None, description="Reason for assignment change")


class TicketEscalationRequest(BaseSchema):
    """Schema for ticket escalation"""
    escalation_level: int = Field(ge=1, le=5, description="Escalation level (1-5)")
    reason: str = Field(description="Reason for escalation")
    escalated_to_id: Optional[UUID] = Field(None, description="User to escalate to")
    urgent: bool = Field(False, description="Mark as urgent escalation")


class TicketSatisfactionRequest(BaseSchema):
    """Schema for customer satisfaction rating"""
    rating: int = Field(ge=1, le=5, description="Satisfaction rating (1-5)")
    feedback: Optional[str] = Field(None, description="Additional feedback")


class TicketAIAnalysisRequest(BaseSchema):
    """Schema for requesting AI analysis of ticket"""
    analysis_types: List[str] = Field(
        default=["categorization", "priority", "sentiment"],
        description="Types of analysis to perform"
    )
    force_reanalysis: bool = Field(False, description="Force re-analysis even if already analyzed")
    
    @field_validator('analysis_types')
    @classmethod
    def validate_analysis_types(cls, v):
        valid_types = {"categorization", "priority", "sentiment", "summary", "routing"}
        if not all(t in valid_types for t in v):
            raise ValueError(f'Invalid analysis types. Must be one of: {valid_types}')
        return v


class TicketPatchRequest(BaseSchema):
    """
    Schema for flexible partial ticket updates.
    Any combination of fields can be updated in a single request.
    """
    
    # Core ticket fields
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="Update ticket title")
    description: Optional[str] = Field(None, min_length=1, max_length=10000, description="Update ticket description")
    status: Optional[TicketStatusSchema] = Field(None, description="Update ticket status")
    priority: Optional[TicketPrioritySchema] = Field(None, description="Update ticket priority")
    category: Optional[TicketCategorySchema] = Field(None, description="Update ticket category")
    
    # Assignment fields
    assigned_to_id: Optional[UUID] = Field(None, description="Assign ticket to user (null to unassign)")
    assignment_reason: Optional[str] = Field(None, max_length=500, description="Reason for assignment change")
    
    # Additional fields
    department: Optional[str] = Field(None, max_length=100, description="Update department")
    due_date: Optional[datetime] = Field(None, description="Set ticket due date")
    tags: Optional[List[str]] = Field(None, description="Update ticket tags")
    
    # Custom fields support
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="Update custom field values")
    internal_notes: Optional[str] = Field(None, description="Add internal notes")
    resolution_summary: Optional[str] = Field(None, description="Resolution summary")
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip() if v else None
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Description cannot be empty')
        return v.strip() if v else None
    
    @field_validator('assignment_reason')
    @classmethod
    def validate_assignment_reason(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Assignment reason cannot be empty')
        return v.strip() if v else None
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v):
        if v is not None:
            # Remove duplicates and empty strings
            return list(set(tag.strip() for tag in v if tag.strip()))
        return None
    
    @model_validator(mode='after')
    def validate_resolution_summary(self):
        """Require resolution summary when marking as resolved/closed"""
        if self.status in [TicketStatusSchema.RESOLVED, TicketStatusSchema.CLOSED]:
            if not self.resolution_summary or not self.resolution_summary.strip():
                raise ValueError('Resolution summary required when resolving or closing ticket')
        return self
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "description": "Update status only",
                    "value": {"status": "in_progress"}
                },
                {
                    "description": "Assign ticket with reason",
                    "value": {
                        "assigned_to_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                        "assignment_reason": "User has expertise in this area"
                    }
                },
                {
                    "description": "Multi-field update",
                    "value": {
                        "status": "in_progress",
                        "priority": "high",
                        "assigned_to_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                        "assignment_reason": "Escalating priority issue"
                    }
                },
                {
                    "description": "Update with tags and notes",
                    "value": {
                        "status": "resolved",
                        "priority": "low",
                        "tags": ["fixed", "tested"],
                        "resolution_summary": "Issue resolved by updating configuration",
                        "internal_notes": "Configuration updated in production environment"
                    }
                }
            ]
        }
    }


# Response schemas
class TicketUserInfo(BaseSchema):
    """User information for ticket responses"""
    id: UUID = Field(description="User ID")
    email: str = Field(description="User email")
    full_name: Optional[str] = Field(None, description="User full name")
    display_name: str = Field(description="User display name")
    avatar_url: Optional[str] = Field(None, description="User avatar URL")


class TicketFileInfo(BaseSchema):
    """File information for ticket responses"""
    id: UUID = Field(description="File ID")
    filename: str = Field(description="File name")
    file_size: int = Field(description="File size in bytes")
    file_type: str = Field(description="File type")
    mime_type: str = Field(description="MIME type")
    status: str = Field(description="Processing status")
    created_at: datetime = Field(description="Upload timestamp")


class TicketAIAnalysis(BaseSchema):
    """AI analysis information for tickets"""
    confidence_score: Optional[float] = Field(None, description="AI confidence score")
    reasoning: Optional[str] = Field(None, description="AI reasoning")
    tags: Optional[List[str]] = Field(None, description="AI-generated tags")
    keywords: Optional[List[str]] = Field(None, description="Detected keywords")
    similar_patterns: Optional[List[str]] = Field(None, description="Similar patterns")
    sentiment: Optional[str] = Field(None, description="Sentiment analysis")
    business_impact: Optional[str] = Field(None, description="Business impact assessment")


class TicketBaseResponse(BaseResponse):
    """Base ticket response with common fields"""
    title: str = Field(description="Ticket title")
    
    @computed_field
    @property  
    def display_title(self) -> str:
        """Display title (truncated)"""
        return self.title[:100] + "..." if len(self.title) > 100 else self.title
    category: TicketCategorySchema = Field(description="Issue category")
    subcategory: Optional[str] = Field(None, description="Issue subcategory")
    priority: TicketPrioritySchema = Field(description="Priority level")
    urgency: TicketPrioritySchema = Field(description="Urgency level")
    status: TicketStatusSchema = Field(description="Current status")
    department: Optional[str] = Field(None, description="Assigned department")
    source_channel: str = Field(description="Source channel")
    created_by: TicketUserInfo = Field(alias="creator", description="Ticket creator")
    assigned_to_id: Optional[UUID] = Field(None, description="ID of assigned user")


class TicketListResponse(TicketBaseResponse):
    """Ticket information for list views"""
    last_activity_at: datetime = Field(description="Last activity timestamp")
    communication_count: int = Field(description="Number of communications")
    file_count: Optional[int] = Field(None, description="Number of attachments")
    is_overdue: bool = Field(description="Whether ticket is overdue")
    is_high_priority: bool = Field(description="Whether ticket is high priority")
    age_in_hours: float = Field(description="Ticket age in hours")
    escalation_level: int = Field(description="Current escalation level")


class TicketDetailResponse(TicketBaseResponse):
    """Detailed ticket information"""
    description: str = Field(description="Ticket description")
    resolution_summary: Optional[str] = Field(None, description="Resolution summary")
    internal_notes: Optional[str] = Field(None, description="Internal notes")
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="Custom field values")
    
    # Timestamps
    first_response_at: Optional[datetime] = Field(None, description="First response timestamp")
    resolved_at: Optional[datetime] = Field(None, description="Resolution timestamp")
    closed_at: Optional[datetime] = Field(None, description="Closure timestamp")
    last_activity_at: datetime = Field(description="Last activity timestamp")
    
    # Metrics
    communication_count: int = Field(description="Communication count")
    resolution_time_minutes: Optional[int] = Field(None, description="Resolution time in minutes")
    
    # SLA and escalation
    sla_due_date: Optional[datetime] = Field(None, description="SLA due date")
    sla_breached: bool = Field(description="Whether SLA was breached")
    escalation_level: int = Field(description="Escalation level")
    escalated_at: Optional[datetime] = Field(None, description="Escalation timestamp")
    escalation_reason: Optional[str] = Field(None, description="Escalation reason")
    
    # External integration
    integration_routing: Optional[str] = Field(None, description="Integration routing (legacy)")
    external_ticket_id: Optional[str] = Field(None, description="External ticket ID")
    external_ticket_url: Optional[str] = Field(None, description="External ticket URL")
    
    # Customer satisfaction
    satisfaction_rating: Optional[int] = Field(None, description="Customer satisfaction rating")
    satisfaction_feedback: Optional[str] = Field(None, description="Satisfaction feedback")
    
    # Files and attachments
    files: List[TicketFileInfo] = Field(default=[], description="Attached files")
    
    # AI analysis
    ai_analysis: Optional[TicketAIAnalysis] = Field(None, description="AI analysis results")
    
    # Integration result
    integration_result: Optional[Dict[str, Any]] = Field(None, description="External integration creation result")
    
    # Computed properties
    @computed_field
    @property
    def is_overdue(self) -> bool:
        """Whether ticket is overdue"""
        return False  # TODO: Implement SLA logic
    
    @computed_field
    @property
    def is_high_priority(self) -> bool:
        """Whether ticket is high priority"""
        return self.priority in ["high", "critical"]
    
    @computed_field
    @property
    def can_be_closed(self) -> bool:
        """Whether ticket can be closed"""
        return self.status in ["resolved", "pending"]
    
    @computed_field
    @property
    def age_in_hours(self) -> float:
        """Ticket age in hours"""
        delta = datetime.now(timezone.utc) - self.created_at
        return delta.total_seconds() / 3600.0
    
    @computed_field
    @property
    def resolution_time_hours(self) -> Optional[float]:
        """Resolution time in hours"""
        return self.resolution_time_minutes / 60.0 if self.resolution_time_minutes else None


class TicketPublicResponse(BaseSchema):
    """Public ticket information (for customer portal)"""
    id: UUID = Field(description="Ticket ID")
    title: str = Field(description="Ticket title")
    category: TicketCategorySchema = Field(description="Issue category")
    status: TicketStatusSchema = Field(description="Current status")
    priority: TicketPrioritySchema = Field(description="Priority level")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
    resolution_summary: Optional[str] = Field(None, description="Resolution summary")
    satisfaction_rating: Optional[int] = Field(None, description="Satisfaction rating")
    external_ticket_id: Optional[str] = Field(None, description="External reference ID")


class TicketStatsResponse(BaseSchema):
    """Ticket statistics response"""
    total_tickets: int = Field(description="Total number of tickets")
    open_tickets: int = Field(description="Number of open tickets")
    resolved_tickets: int = Field(description="Number of resolved tickets")
    overdue_tickets: int = Field(description="Number of overdue tickets")
    high_priority_tickets: int = Field(description="Number of high priority tickets")
    avg_resolution_time_hours: Optional[float] = Field(None, description="Average resolution time")
    avg_first_response_time_hours: Optional[float] = Field(None, description="Average first response time")
    satisfaction_score: Optional[float] = Field(None, description="Average satisfaction score")
    category_distribution: Dict[str, int] = Field(description="Tickets by category")
    priority_distribution: Dict[str, int] = Field(description="Tickets by priority")
    status_distribution: Dict[str, int] = Field(description="Tickets by status")


class TicketActivityResponse(BaseSchema):
    """Ticket activity/history response"""
    activity_type: str = Field(description="Type of activity")
    timestamp: datetime = Field(description="Activity timestamp")
    user: Optional[TicketUserInfo] = Field(None, description="User who performed activity")
    description: str = Field(description="Activity description")
    changes: Optional[Dict[str, Any]] = Field(None, description="Changes made")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional activity data")


# Search and filter schemas
class TicketSearchParams(BaseSchema):
    """Ticket search parameters"""
    q: Optional[str] = Field(None, description="Search query (title, description)")
    status: Optional[List[TicketStatusSchema]] = Field(None, description="Filter by status")
    category: Optional[List[TicketCategorySchema]] = Field(None, description="Filter by category")
    priority: Optional[List[TicketPrioritySchema]] = Field(None, description="Filter by priority")
    urgency: Optional[List[TicketPrioritySchema]] = Field(None, description="Filter by urgency")
    department: Optional[str] = Field(None, description="Filter by department")
    created_by_id: Optional[UUID] = Field(None, description="Filter by creator")
    assigned_to_id: Optional[UUID] = Field(None, description="Filter by assignee")
    integration_id: Optional[UUID] = Field(None, description="Filter by integration ID")
    has_attachments: Optional[bool] = Field(None, description="Filter by file attachments")
    is_overdue: Optional[bool] = Field(None, description="Filter by overdue status")
    escalation_level: Optional[int] = Field(None, description="Filter by escalation level")
    satisfaction_rating: Optional[int] = Field(None, description="Filter by satisfaction rating")
    created_after: Optional[datetime] = Field(None, description="Created after date")
    created_before: Optional[datetime] = Field(None, description="Created before date")
    updated_after: Optional[datetime] = Field(None, description="Updated after date")
    updated_before: Optional[datetime] = Field(None, description="Updated before date")
    resolved_after: Optional[datetime] = Field(None, description="Resolved after date")
    resolved_before: Optional[datetime] = Field(None, description="Resolved before date")
    tags: Optional[List[str]] = Field(None, description="Filter by AI tags")
    source_channel: Optional[str] = Field(None, description="Filter by source channel")


class TicketSortParams(BaseSchema):
    """Ticket sorting parameters"""
    sort_by: str = Field(
        "created_at",
        description="Sort field",
        pattern="^(created_at|updated_at|title|priority|status|last_activity_at|resolution_time_minutes)$"
    )
    sort_order: str = Field("desc", pattern="^(asc|desc)$", description="Sort order")


# Bulk operation schemas
class TicketBulkUpdateRequest(BaseSchema):
    """Schema for bulk ticket updates"""
    ticket_ids: List[UUID] = Field(description="List of ticket IDs to update")
    updates: TicketUpdateRequest = Field(description="Updates to apply")
    reason: Optional[str] = Field(None, description="Reason for bulk update")


class TicketBulkStatusUpdateRequest(BaseSchema):
    """Schema for bulk status updates"""
    ticket_ids: List[UUID] = Field(description="List of ticket IDs")
    status: TicketStatusSchema = Field(description="New status")
    resolution_summary: Optional[str] = Field(None, description="Resolution summary")
    reason: Optional[str] = Field(None, description="Reason for status change")


class TicketBulkAssignRequest(BaseSchema):
    """Schema for bulk ticket assignment"""
    ticket_ids: List[UUID] = Field(description="List of ticket IDs")
    assigned_to_id: Optional[UUID] = Field(None, description="User to assign to")
    reason: Optional[str] = Field(None, description="Reason for assignment")


class TicketBulkCategoryRequest(BaseSchema):
    """Schema for bulk categorization"""
    ticket_ids: List[UUID] = Field(description="List of ticket IDs")
    category: TicketCategorySchema = Field(description="New category")
    subcategory: Optional[str] = Field(None, description="New subcategory")
    reason: Optional[str] = Field(None, description="Reason for recategorization")


# AI integration schemas
class TicketAICreateRequest(BaseSchema):
    """Schema for AI-powered ticket creation"""
    user_input: str = Field(description="User's natural language input")
    uploaded_files: Optional[List[UUID]] = Field(None, description="Uploaded file IDs")
    conversation_context: Optional[List[Dict[str, Any]]] = Field(None, description="Conversation history")
    user_preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences")
    integration_id: Optional[UUID] = Field(None, description="Integration ID for external ticket creation")


class TicketAICreateResponse(BaseSchema):
    """Response from AI ticket creation"""
    ticket: TicketDetailResponse = Field(description="Created ticket")
    ai_analysis: TicketAIAnalysis = Field(description="AI analysis results")
    confidence_score: float = Field(description="Overall confidence score")
    suggested_actions: List[str] = Field(description="Suggested next actions")
    file_analysis_summary: Optional[str] = Field(None, description="File analysis summary")


class TicketAIAnalysisResponse(BaseSchema):
    """Response from AI analysis"""
    analysis_type: str = Field(description="Type of analysis performed")
    results: Dict[str, Any] = Field(description="Analysis results")
    confidence_score: float = Field(description="Confidence in analysis")
    suggestions: List[str] = Field(description="AI suggestions")
    updated_fields: Optional[Dict[str, Any]] = Field(None, description="Suggested field updates")