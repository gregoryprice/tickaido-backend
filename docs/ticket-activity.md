# PRP: Ticket Activity & Comments System

**Status**: Planning  
**Priority**: High  
**Assignee**: Development Team  
**Created**: 2025-09-19  

## Overview

This PRP outlines the implementation of a comprehensive ticket activity tracking system that includes field change history and commenting capabilities. The system will enable users and AI agents to track ticket modifications and add comments, with full integration support for external systems like Jira.

## Background & Motivation

Currently, the ticketing system lacks visibility into:
- Who changed ticket fields and when
- Historical view of ticket progression
- Ability for users and AI agents to add contextual comments
- Comment synchronization with integrated platforms (Jira, ServiceNow, etc.)

## Features

### 1. Ticket History Tracking
- Track all field changes on tickets with timestamps
- Record the user or system that made each change
- Store before/after values for field modifications
- Provide comprehensive audit trail for compliance

### 2. Comment System
- Allow users to add comments to tickets
- Enable AI agents to create comments via tool interface
- Support rich text formatting for comments
- Maintain comment threads and replies
- **User Mentions**: @ mention functionality to notify specific users

### 3. User Mention System
- **Mention Parsing**: Automatically detect @user mentions in comment content
- **User Validation**: Validate mentioned users exist and have access to the ticket
- **Notification Delivery**: Send notifications to mentioned users via email/in-app
- **Mention Storage**: Store mentions as array of user UUIDs in `mentions` JSON column
- **Access Control**: Only allow mentioning users within the same organization
- **Frontend Integration**: Provide autocomplete for user mentions in comment editor

### 4. Integration Synchronization
- Push comments to external systems (Jira, ServiceNow, etc.)
- Sync comment updates and deletions where supported
- Handle bidirectional comment synchronization
- Maintain comment attribution across systems
- **Note**: External systems may not support user mentions - mentions are internal only

## Technical Design

### Database Models

#### TicketHistory Model
```python
class TicketHistoryAction(enum.Enum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    ASSIGNED = "assigned"
    ESCALATED = "escalated"
    COMMENTED = "commented"
    ATTACHED = "attached"
    SYNCED = "synced"
    RESOLVED = "resolved"
    REOPENED = "reopened"

class TicketHistory(BaseModel):
    __tablename__ = "ticket_history"
    
    # Core identification
    ticket_id = Column(UUID, ForeignKey("tickets.id"), nullable=False, index=True)
    action = Column(SQLEnum(TicketHistoryAction), nullable=False, index=True)
    
    # Change tracking
    field_name = Column(String(100), nullable=True, comment="Name of field that changed")
    old_value = Column(JSON, nullable=True, comment="Previous field value")
    new_value = Column(JSON, nullable=True, comment="New field value")
    
    # Attribution - polymorphic approach for users, systems, or agents
    changed_by_type = Column(String(20), nullable=False, default="user", comment="Type of entity that made change: user, system, agent")
    changed_by_id = Column(String(255), nullable=False, index=True, comment="ID of entity: user UUID, system name, or agent identifier")
    changed_by_name = Column(String(255), nullable=True, comment="Display name for the entity (cached for performance)")
    
    # Context
    description = Column(Text, nullable=True, comment="Human-readable description of change")
    metadata = Column(JSON, nullable=True, comment="Additional change metadata")
    
    # Integration tracking
    synced_to_external = Column(Boolean, default=False, comment="Whether change was synced to external system")
    external_sync_details = Column(JSON, nullable=True, comment="Details of external sync")
    
    # Relationships
    ticket = relationship("Ticket", back_populates="history")
    
    # No direct relationship for changed_by since it's polymorphic
    # Use service layer methods to resolve the actual entity
    
    # Performance optimizations
    @property
    def changed_by_display(self) -> str:
        """Get display name for the entity that made the change (cached)"""
        return self.changed_by_name or self.changed_by_id
    
    def set_changed_by_user(self, user_id: UUID, user_name: str = None):
        """Set change attribution to a user"""
        self.changed_by_type = "user"
        self.changed_by_id = str(user_id)
        self.changed_by_name = user_name
    
    def set_changed_by_system(self, system_name: str):
        """Set change attribution to a system"""
        self.changed_by_type = "system" 
        self.changed_by_id = system_name
        self.changed_by_name = system_name
        
    def set_changed_by_agent(self, agent_id: str, agent_name: str = None):
        """Set change attribution to an AI agent"""
        self.changed_by_type = "agent"
        self.changed_by_id = agent_id
        self.changed_by_name = agent_name or f"AI Agent ({agent_id})"

# Performance indexes for scalability
__table_args__ = (
    Index('ix_ticket_history_ticket_created', 'ticket_id', 'created_at'),
    Index('ix_ticket_history_action_created', 'action', 'created_at'),
    Index('ix_ticket_history_changed_by', 'changed_by_type', 'changed_by_id'),
    Index('ix_ticket_history_field_name', 'field_name', 'created_at'),
)
```

#### Comment Model
```python
class CommentType(enum.Enum):
    USER = "user"
    AI_AGENT = "ai_agent" 
    SYSTEM = "system"
    EXTERNAL = "external"

class Comment(BaseModel):
    __tablename__ = "comments"
    
    # Core fields
    ticket_id = Column(UUID, ForeignKey("tickets.id"), nullable=False, index=True)
    content = Column(Text, nullable=False, comment="Comment content")
    content_type = Column(String(20), default="text", comment="Content type (text, markdown, html)")
    
    # Attribution
    author_id = Column(UUID, ForeignKey("users.id"), nullable=True, comment="User who created comment")
    author_type = Column(SQLEnum(CommentType), nullable=False, default=CommentType.USER)
    author_system = Column(String(100), nullable=True, comment="System/agent identifier for non-user comments")
    
    # Threading
    parent_comment_id = Column(UUID, ForeignKey("comments.id"), nullable=True, comment="Parent comment for replies")
    thread_position = Column(Integer, default=0, comment="Position in comment thread")
    
    # Visibility
    is_internal = Column(Boolean, default=False, comment="Whether comment is internal only")
    is_public = Column(Boolean, default=True, comment="Whether comment is visible to ticket creator")
    
    # Integration tracking
    external_comment_id = Column(String(255), nullable=True, comment="ID in external system (Jira, etc.)")
    external_comment_url = Column(String(500), nullable=True, comment="URL to comment in external system")
    synced_to_external = Column(Boolean, default=False, comment="Whether comment was synced to external system")
    sync_status = Column(String(50), default="pending", comment="Sync status (pending, synced, failed)")
    sync_error = Column(Text, nullable=True, comment="Error message if sync failed")
    
    # Metadata
    mentions = Column(JSON, nullable=True, comment="User mentions in comment - array of user IDs")
    tags = Column(JSON, nullable=True, comment="Tags associated with comment")
    
    # Relationships
    ticket = relationship("Ticket", back_populates="comments")
    author = relationship("User", foreign_keys=[author_id])
    parent_comment = relationship("Comment", remote_side="Comment.id", backref="replies")
```

### API Endpoints & Pydantic Models

#### Pydantic Request/Response Models
```python
# app/schemas/ticket_history.py
class TicketHistoryResponse(BaseModel):
    id: UUID
    ticket_id: UUID
    action: TicketHistoryAction
    field_name: Optional[str] = None
    old_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None
    changed_by_type: str  # "user", "system", or "agent"
    changed_by_id: str    # UUID for users, identifier for systems/agents
    changed_by_name: Optional[str] = None  # Cached display name
    changed_by_display: str  # Computed display name
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    synced_to_external: bool = False
    external_sync_details: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    # Dynamic field populated by service layer based on changed_by_type
    changed_by_details: Optional[Dict[str, Any]] = None  # Full user/agent details when needed

class TicketHistoryListResponse(BaseModel):
    items: List[TicketHistoryResponse]
    total: int
    page: int
    limit: int
    total_pages: int

# app/schemas/comment.py
class CommentCreateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    content_type: str = Field(default="text", pattern="^(text|markdown)$")
    parent_comment_id: Optional[UUID] = None
    is_internal: bool = False
    mentions: Optional[List[UUID]] = Field(default_factory=list)
    tags: Optional[List[str]] = Field(default_factory=list)

class CommentUpdateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    mentions: Optional[List[UUID]] = Field(default_factory=list)
    tags: Optional[List[str]] = Field(default_factory=list)

class CommentResponse(BaseModel):
    id: UUID
    ticket_id: UUID
    content: str
    content_type: str
    author_id: Optional[UUID] = None
    author_type: CommentType
    author_system: Optional[str] = None
    parent_comment_id: Optional[UUID] = None
    thread_position: int
    is_internal: bool
    is_public: bool
    mentions: List[UUID]
    tags: List[str]
    external_comment_id: Optional[str] = None
    external_comment_url: Optional[str] = None
    synced_to_external: bool
    sync_status: str
    sync_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    author: Optional[UserResponse] = None
    mentioned_users: List[UserResponse]
    replies_count: int

class CommentListResponse(BaseModel):
    items: List[CommentResponse]
    total: int
    page: int
    limit: int
    total_pages: int
```

#### Ticket History API
```python
# GET /api/v1/tickets/{ticket_id}/history
# Query Parameters (validated via Pydantic):
# - page: int = 1
# - limit: int = 50  
# - action: TicketHistoryAction = None
# - field_name: str = None
# - user_id: UUID = None
# - start_date: datetime = None
# - end_date: datetime = None

# Response: TicketHistoryListResponse
{
  "items": [
    {
      "id": "uuid",
      "ticket_id": "uuid", 
      "action": "updated",
      "field_name": "status",
      "old_value": {"value": "open", "display": "Open"},
      "new_value": {"value": "in_progress", "display": "In Progress"},
      "changed_by_type": "user",
      "changed_by_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
      "changed_by_name": "John Doe",
      "changed_by_display": "John Doe",
      "description": "Status changed from Open to In Progress",
      "metadata": {"reason": "user_action", "source": "web_ui"},
      "synced_to_external": true,
      "external_sync_details": {"jira_updated": true, "jira_status": "In Progress"},
      "created_at": "2025-09-19T10:30:00Z",
      "updated_at": "2025-09-19T10:30:00Z",
      "changed_by_details": {
        "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
        "email": "user@example.com",
        "first_name": "John",
        "last_name": "Doe"
      }
    }
  ],
  "total": 25,
  "page": 1,
  "limit": 50,
  "total_pages": 1
}

# GET /api/v1/tickets/{ticket_id}/history/{history_id}
# Response: TicketHistoryResponse
{
  "id": "uuid",
  "ticket_id": "uuid",
  "action": "updated", 
  "field_name": "priority",
  "old_value": {"value": "medium", "display": "Medium"},
  "new_value": {"value": "high", "display": "High"},
  "changed_by_type": "agent",
  "changed_by_id": "categorization_agent_v2.1",
  "changed_by_name": "AI Categorization Agent",
  "changed_by_display": "AI Categorization Agent",
  "description": "Priority escalated to High based on urgency keywords",
  "metadata": {
    "reason": "ai_escalation", 
    "confidence_score": 0.95,
    "keywords_detected": ["urgent", "critical", "asap"],
    "agent_version": "v2.1"
  },
  "synced_to_external": true,
  "external_sync_details": {"jira_priority_updated": true},
  "created_at": "2025-09-19T10:30:00Z",
  "updated_at": "2025-09-19T10:30:00Z",
  "changed_by_details": {
    "agent_id": "categorization_agent_v2.1",
    "agent_name": "AI Categorization Agent",
    "agent_type": "categorization",
    "version": "v2.1"
  }
}
```

#### Comments API  
```python
# GET /api/v1/tickets/{ticket_id}/comments
# Query Parameters (validated via Pydantic):
# - page: int = 1
# - limit: int = 50
# - author_type: CommentType = None
# - is_internal: bool = None
# - parent_comment_id: UUID = None

# Response: CommentListResponse
{
  "items": [
    {
      "id": "uuid",
      "ticket_id": "uuid",
      "content": "This issue needs immediate attention",
      "content_type": "text",
      "author_id": "uuid", 
      "author_type": "user",
      "author_system": null,
      "parent_comment_id": null,
      "thread_position": 0,
      "is_internal": false,
      "is_public": true,
      "mentions": ["uuid1", "uuid2"],
      "tags": ["urgent", "escalation"],
      "external_comment_id": "10001",
      "external_comment_url": "https://jira.company.com/browse/ISSUE-123#comment-10001",
      "synced_to_external": true,
      "sync_status": "synced",
      "sync_error": null,
      "created_at": "2025-09-19T10:30:00Z",
      "updated_at": "2025-09-19T10:30:00Z",
      "author": {
        "id": "uuid",
        "email": "user@example.com",
        "first_name": "John", 
        "last_name": "Doe"
      },
      "mentioned_users": [
        {
          "id": "uuid1",
          "email": "manager@example.com",
          "first_name": "Jane",
          "last_name": "Smith"
        }
      ],
      "replies_count": 2
    }
  ],
  "total": 15,
  "page": 1,
  "limit": 50, 
  "total_pages": 1
}

# POST /api/v1/tickets/{ticket_id}/comments
# Request Body: CommentCreateRequest
{
  "content": "This is my comment on the ticket",
  "content_type": "text",
  "parent_comment_id": null,
  "is_internal": false,
  "mentions": ["uuid1", "uuid2"],
  "tags": ["urgent"]
}

# Response: CommentResponse (201 Created)
{
  "id": "uuid",
  "ticket_id": "uuid", 
  "content": "This is my comment on the ticket",
  "content_type": "text",
  "author_id": "uuid",
  "author_type": "user",
  "author_system": null,
  "parent_comment_id": null,
  "thread_position": 0,
  "is_internal": false,
  "is_public": true,
  "mentions": ["uuid1", "uuid2"],
  "tags": ["urgent"],
  "external_comment_id": null,
  "external_comment_url": null,
  "synced_to_external": false,
  "sync_status": "pending",
  "sync_error": null,
  "created_at": "2025-09-19T10:30:00Z",
  "updated_at": "2025-09-19T10:30:00Z",
  "author": {
    "id": "uuid",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe"
  },
  "mentioned_users": [
    {
      "id": "uuid1", 
      "email": "manager@example.com",
      "first_name": "Jane",
      "last_name": "Smith"
    }
  ],
  "replies_count": 0
}

# GET /api/v1/tickets/{ticket_id}/comments/{comment_id}
# Response: CommentResponse (200 OK)

# PUT /api/v1/tickets/{ticket_id}/comments/{comment_id}  
# Request Body: CommentUpdateRequest
{
  "content": "Updated comment content",
  "mentions": ["uuid3"],
  "tags": ["updated"]
}

# Response: CommentResponse (200 OK)

# DELETE /api/v1/tickets/{ticket_id}/comments/{comment_id}
# Response: (204 No Content)
```

## Performance & Scalability Considerations

### Attribution System Design
The polymorphic attribution system (`changed_by_type`, `changed_by_id`, `changed_by_name`) is designed for high performance and flexibility:

#### Benefits:
- **Single Table**: No joins required for basic history queries
- **Cached Names**: `changed_by_name` eliminates need to join user table for display
- **Flexible IDs**: Supports any entity type without schema changes
- **Indexed**: Composite index on `(changed_by_type, changed_by_id)` for fast filtering

#### Usage Patterns:
```python
# User change - store UUID as string, cache display name
history.set_changed_by_user(user_id=user.id, user_name=f"{user.first_name} {user.last_name}")

# System change - simple string identifier
history.set_changed_by_system("integration_sync_service")

# Agent change - agent identifier with cached name
history.set_changed_by_agent("customer_support_agent_v1.2", "Customer Support AI")
```

### Database Performance Optimizations

#### Composite Indexes for Common Query Patterns:
```sql
-- Most common: history for specific ticket, recent first
CREATE INDEX ix_ticket_history_ticket_created ON ticket_history (ticket_id, created_at DESC);

-- Filter by action type with time ordering
CREATE INDEX ix_ticket_history_action_created ON ticket_history (action, created_at DESC);

-- Attribution filtering (e.g., "show all changes by this user")
CREATE INDEX ix_ticket_history_changed_by ON ticket_history (changed_by_type, changed_by_id, created_at DESC);

-- Field-specific history (e.g., "show all status changes")
CREATE INDEX ix_ticket_history_field_name ON ticket_history (field_name, created_at DESC);

-- External sync status for batch operations
CREATE INDEX ix_ticket_history_sync_status ON ticket_history (synced_to_external, created_at);
```

#### Query Performance Targets:
- **Single Ticket History**: <50ms for 1,000+ history records
- **Filtered Queries**: <100ms with proper index usage
- **Bulk Operations**: <500ms for 10,000+ records
- **Concurrent Load**: Support 1,000+ simultaneous history reads

#### Memory & Storage Optimization:
- **JSON Compression**: Use JSONB in PostgreSQL for efficient storage
- **Field Value Limits**: Limit `old_value`/`new_value` to 10KB each
- **Archival Strategy**: Archive history >1 year to separate tables
- **Partitioning**: Consider monthly partitioning for high-volume systems

### Scalability Patterns

#### Horizontal Scaling:
```python
# Service layer handles entity resolution efficiently
class TicketHistoryService:
    async def get_history_with_attribution(self, ticket_id: UUID, 
                                         include_details: bool = False) -> List[TicketHistoryResponse]:
        """
        Optimized history retrieval with optional detail loading.
        
        Performance optimizations:
        - Use cached names when include_details=False
        - Batch load user details when include_details=True 
        - Separate queries for different entity types
        """
        histories = await self.get_raw_history(ticket_id)
        
        if not include_details:
            # Fast path - use cached names only
            return [self._to_response_cached(h) for h in histories]
        
        # Batch load full details by type
        user_ids = [h.changed_by_id for h in histories if h.changed_by_type == "user"]
        agent_ids = [h.changed_by_id for h in histories if h.changed_by_type == "agent"]
        
        # Single batch query per entity type
        users = await self.user_service.get_users_by_ids(user_ids) if user_ids else {}
        agents = await self.agent_service.get_agents_by_ids(agent_ids) if agent_ids else {}
        
        return [self._to_response_with_details(h, users, agents) for h in histories]
```

#### Caching Strategy:
```python
# Redis caching for frequently accessed data
@cached(ttl=300)  # 5 minute cache
async def get_recent_history(self, ticket_id: UUID, limit: int = 50):
    """Cache recent history for active tickets"""
    
@cached(ttl=3600)  # 1 hour cache  
async def get_user_display_name(self, user_id: UUID) -> str:
    """Cache user display names for attribution"""
```

#### Background Processing:
- **Async Sync**: Use Celery tasks for external system synchronization
- **Batch Attribution**: Update cached names in background when users change
- **Cleanup Tasks**: Periodic cleanup of old sync status and metadata

### Performance Monitoring

#### Key Metrics:
- History query response times (p50, p95, p99)
- Attribution resolution performance 
- External sync success rates and latency
- Cache hit rates for user/agent names
- Database index usage statistics

#### Alerting Thresholds:
- History queries >200ms (p95)
- Sync failures >5% rate
- Cache hit rate <80%
- Database connection pool >80% usage

### Services

#### TicketHistoryService
```python
class TicketHistoryService:
    async def record_field_change(self, ticket_id: UUID, field_name: str, 
                                 old_value: Any, new_value: Any, 
                                 user_id: UUID = None, system: str = None) -> TicketHistory
    
    async def record_status_change(self, ticket_id: UUID, old_status: str, 
                                  new_status: str, user_id: UUID, reason: str = None) -> TicketHistory
    
    async def get_ticket_history(self, ticket_id: UUID, 
                                filters: HistoryFilters = None, 
                                pagination: Pagination = None) -> List[TicketHistory]
    
    async def get_field_history(self, ticket_id: UUID, field_name: str) -> List[TicketHistory]
```

#### CommentService  
```python
class CommentService:
    async def create_comment(self, ticket_id: UUID, content: str,
                           author_id: UUID = None, author_type: CommentType = CommentType.USER,
                           parent_comment_id: UUID = None, is_internal: bool = False) -> Comment
    
    async def update_comment(self, comment_id: UUID, content: str, 
                           user_id: UUID) -> Comment
    
    async def delete_comment(self, comment_id: UUID, user_id: UUID) -> bool
    
    async def get_ticket_comments(self, ticket_id: UUID, 
                                 filters: CommentFilters = None,
                                 pagination: Pagination = None) -> List[Comment]
    
    async def sync_comment_to_integration(self, comment: Comment, 
                                        integration: Integration) -> bool
```

#### IntegrationCommentService
```python
class IntegrationCommentService:
    """
    Service for synchronizing comments with external integrations.
    Uses the existing JiraIntegration service for all Jira operations.
    """
    
    def __init__(self):
        self.integration_service = IntegrationService()
    
    async def sync_comment_to_integration(self, comment: Comment, ticket: Ticket, 
                                        db: AsyncSession) -> Dict[str, Any]:
        """
        Sync comment to the ticket's integration platform (if any).
        Uses the existing integration service and routing.
        """
        
    async def update_comment_in_integration(self, comment: Comment, ticket: Ticket,
                                          db: AsyncSession) -> Dict[str, Any]:
        """
        Update comment in external integration system.
        """
        
    async def delete_comment_in_integration(self, comment: Comment, ticket: Ticket,
                                          db: AsyncSession) -> bool:
        """
        Delete comment from external integration system.
        """
        
    async def sync_all_comments_for_ticket(self, ticket_id: UUID, 
                                         db: AsyncSession) -> Dict[str, Any]:
        """
        Sync all pending comments for a ticket to its integration.
        """
```

### Integration Enhancements

#### Jira Integration Updates
The existing `JiraIntegration` service in `app/integrations/jira/jira_integration.py` already has an `add_comment` method. We need to extend it with update and delete capabilities:

```python
# Add to existing JiraIntegration class:

async def update_comment(self, issue_key: str, comment_id: str, comment_text: str) -> Dict[str, Any]:
    """
    Update existing comment in Jira issue using PUT /rest/api/3/issue/{issueIdOrKey}/comment/{id}
    
    Args:
        issue_key: JIRA issue key (e.g., "TEST-123")  
        comment_id: External comment ID from Jira
        comment_text: Updated comment content
        
    Returns:
        Dict containing updated comment information
    """
    payload = {
        "body": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": str(comment_text)
                        }
                    ]
                }
            ]
        }
    }
    
    response = await self.client.put(
        f"{self.base_url}/rest/api/3/issue/{issue_key}/comment/{comment_id}",
        json=payload
    )
    response.raise_for_status()
    return response.json()

async def delete_comment(self, issue_key: str, comment_id: str) -> bool:
    """
    Delete comment from Jira issue using DELETE /rest/api/3/issue/{issueIdOrKey}/comment/{id}
    """
    response = await self.client.delete(
        f"{self.base_url}/rest/api/3/issue/{issue_key}/comment/{comment_id}"
    )
    response.raise_for_status()
    return True

async def get_comments(self, issue_key: str) -> List[Dict[str, Any]]:
    """
    Get all comments for Jira issue using GET /rest/api/3/issue/{issueIdOrKey}/comment
    """
    response = await self.client.get(
        f"{self.base_url}/rest/api/3/issue/{issue_key}/comment"
    )
    response.raise_for_status()
    data = response.json()
    
    return [
        {
            "id": comment.get("id"),
            "body": self._extract_text_from_adf(comment.get("body")),
            "author": comment.get("author", {}).get("displayName"),
            "created": comment.get("created"),
            "updated": comment.get("updated"),
            "self": comment.get("self")
        }
        for comment in data.get("comments", [])
    ]
```

### AI Agent Tool Integration

#### Comment Tool for AI Agents
```python
class CommentTool(PydanticAITool):
    """Tool for AI agents to add comments to tickets"""
    
    name = "add_comment"
    description = "Add a comment to a ticket with context and reasoning"
    
    async def run(self, ticket_id: str, content: str, 
                 is_internal: bool = False, tags: List[str] = None) -> Dict[str, Any]:
        """
        Add comment to ticket as an AI agent
        
        Args:
            ticket_id: UUID of the ticket
            content: Comment content (markdown supported)
            is_internal: Whether comment is internal only
            tags: Optional tags for categorization
        """
        # Implementation to create comment with author_type=AI_AGENT
```

## Implementation Plan

### Phase 1: Core Models & History Tracking (Week 1-2)
1. **Database Migrations**
   - Create TicketHistory table
   - Create Comment table  
   - Add necessary indexes for performance

2. **History Service Implementation**
   - Implement TicketHistoryService
   - Add history recording to ticket update operations
   - Create history API endpoints

3. **Testing**
   - Unit tests for history tracking
   - Integration tests for field change recording
   - Performance tests for history queries

### Phase 2: Comment System & AI Tools (Week 2-3)
1. **Comment Service Implementation** 
   - Implement CommentService
   - Add comment CRUD operations
   - Implement comment threading
   - Implement user mention system and notifications

2. **API Development**
   - Create comment REST endpoints
   - Add authentication and authorization
   - Implement comment validation
   - Add mention parsing and validation

3. **AI Agent Tool Integration**
   - Create CommentTool for Pydantic AI agents
   - Integrate with existing agent framework
   - Add comment creation capabilities for agents
   - Test agent comment functionality

4. **Testing**
   - Unit tests for comment operations
   - API endpoint testing
   - Permission and security testing
   - AI agent tool integration testing
   - Mention system testing

### Phase 3: Integration Synchronization (Week 3-4)
1. **Jira Comment Integration**
   - Extend JiraIntegration with comment methods
   - Implement comment synchronization service
   - Add error handling and retry logic

2. **Integration Service Updates**
   - Create IntegrationCommentService
   - Implement bidirectional sync
   - Add sync status tracking

3. **Testing**
   - Integration tests with Jira
   - Sync error handling tests
   - Performance tests for bulk sync

### Phase 4: Frontend & Polish (Week 4-5)
1. **Frontend Integration** 
   - Add comment UI components
   - Implement history timeline view
   - Add real-time updates via WebSocket
   - Implement user mention functionality (@user)
   - Add comment threading UI

2. **User Experience Enhancements**
   - Add comment notifications for mentions
   - Implement comment search and filtering
   - Add comment templates and shortcuts
   - Mobile-responsive comment interface

3. **Testing**
   - End-to-end testing
   - User acceptance testing
   - Cross-browser compatibility testing
   - Mobile responsiveness testing

### Phase 5: Performance & Polish (Week 5-6)
1. **Performance Optimization**
   - Optimize history and comment queries
   - Add caching where appropriate
   - Database query optimization

2. **Monitoring & Observability**
   - Add metrics for comment and history operations
   - Implement alerting for sync failures
   - Add performance monitoring

## Validation & Testing

### Unit Tests
- **Models**: Test model validation, relationships, and methods
- **Services**: Test all service methods with various scenarios  
- **Pydantic Schemas**: Test request/response validation and serialization
- **Business Logic**: Test history recording, comment threading, mention parsing

### Integration Tests  
- **Database**: Test migrations and model relationships
- **External APIs**: Test Jira integration with mock and real APIs
- **Service Integration**: Test service layer interactions
- **Celery Tasks**: Test async comment synchronization tasks

### End-to-End API Tests with Developer Key
**Authentication**: All E2E tests must use the developer API key:
```
Authorization: Bearer ai_dev_MwUVUygQboY9yIeXQ539PYTJfv9Y7yeexWL4TrELMB8
```

#### Required E2E Test Scenarios:

##### Ticket History E2E Tests
```python
# tests/test_e2e_ticket_history.py

class TestTicketHistoryE2E:
    HEADERS = {"Authorization": "Bearer ai_dev_MwUVUygQboY9yIeXQ539PYTJfv9Y7yeexWL4TrELMB8"}
    
    async def test_ticket_field_change_creates_history(self):
        """Test that changing ticket fields automatically creates history records"""
        # 1. Create ticket via API
        # 2. Update ticket status via PUT /api/v1/tickets/{id}
        # 3. Verify history record created via GET /api/v1/tickets/{id}/history
        # 4. Validate history data matches field change
    
    async def test_history_pagination_and_filtering(self):
        """Test history API pagination and filtering capabilities"""
        # 1. Create ticket and make multiple field changes
        # 2. Test pagination with different page sizes
        # 3. Test filtering by action, field_name, user_id, date ranges
        # 4. Validate response structure matches TicketHistoryListResponse
    
    async def test_history_permissions(self):
        """Test history access permissions for different user types"""
        # 1. Create ticket as user A
        # 2. Try to access history as user B (different org)
        # 3. Verify 403 Forbidden response
        # 4. Access as user in same org, verify 200 OK
```

##### Comments E2E Tests  
```python
# tests/test_e2e_comments.py

class TestCommentsE2E:
    HEADERS = {"Authorization": "Bearer ai_dev_MwUVUygQboY9yIeXQ539PYTJfv9Y7yeexWL4TrELMB8"}
    
    async def test_comment_crud_operations(self):
        """Test complete comment CRUD lifecycle"""
        # 1. Create ticket via API
        # 2. POST comment via /api/v1/tickets/{id}/comments
        # 3. GET comment via /api/v1/tickets/{id}/comments/{comment_id}
        # 4. PUT update comment content
        # 5. DELETE comment
        # 6. Verify 404 on subsequent GET
    
    async def test_comment_mentions_and_notifications(self):
        """Test user mentions in comments trigger notifications"""
        # 1. Create ticket and users for mentioning
        # 2. POST comment with mentions: ["user1_uuid", "user2_uuid"] 
        # 3. Verify mentioned_users populated in response
        # 4. Verify notification records created (if notification system exists)
        # 5. Test mention validation (invalid UUIDs, users from other orgs)
    
    async def test_comment_threading(self):
        """Test nested comment replies and threading"""
        # 1. Create parent comment
        # 2. Create reply with parent_comment_id set
        # 3. Verify thread_position and replies_count updated
        # 4. Test deep nesting (reply to reply)
        # 5. Test thread filtering via parent_comment_id query param
    
    async def test_internal_comments_visibility(self):
        """Test internal comment visibility controls"""
        # 1. Create internal comment (is_internal=true)
        # 2. Test visibility for different user roles
        # 3. Verify external sync skips internal comments
        # 4. Test API filtering by is_internal parameter
```

##### Integration Sync E2E Tests
```python
# tests/test_e2e_integration_sync.py

class TestIntegrationSyncE2E:
    HEADERS = {"Authorization": "Bearer ai_dev_MwUVUygQboY9yIeXQ539PYTJfv9Y7yeexWL4TrELMB8"}
    
    async def test_comment_sync_to_jira(self):
        """Test comment synchronization with Jira integration"""
        # 1. Create ticket with Jira integration
        # 2. POST comment to ticket
        # 3. Verify sync_status changes from 'pending' to 'synced'
        # 4. Verify external_comment_id populated
        # 5. Test sync failure scenarios and error handling
        
    async def test_comment_update_sync(self):
        """Test comment updates sync to external systems"""
        # 1. Create and sync comment to Jira
        # 2. PUT update comment content
        # 3. Verify comment updated in Jira
        # 4. Test sync failure recovery
        
    async def test_comment_delete_sync(self):
        """Test comment deletion sync to external systems"""
        # 1. Create and sync comment
        # 2. DELETE comment via API
        # 3. Verify comment deleted in Jira
        # 4. Test soft delete vs hard delete behavior
```

##### AI Agent Tool E2E Tests
```python
# tests/test_e2e_ai_agent_comments.py

class TestAIAgentCommentsE2E:
    HEADERS = {"Authorization": "Bearer ai_dev_MwUVUygQboY9yIeXQ539PYTJfv9Y7yeexWL4TrELMB8"}
    
    async def test_ai_agent_comment_creation(self):
        """Test AI agent creating comments via tool interface"""
        # 1. Create ticket
        # 2. Trigger AI agent comment creation (simulate agent tool call)
        # 3. Verify comment created with author_type='ai_agent'
        # 4. Verify author_system populated with agent identifier
        # 5. Test comment sync behavior for AI comments
        
    async def test_ai_agent_comment_permissions(self):
        """Test AI agent comment permissions and validation"""
        # 1. Test AI agent can only comment on accessible tickets
        # 2. Test organization-scoped access for AI comments
        # 3. Verify AI comments follow same sync rules as user comments
```

### Performance Tests
- **History Queries**: Test with 10,000+ history records per ticket
- **Comment Threading**: Test with 100+ nested comment levels
- **Bulk Sync Operations**: Test syncing 1,000+ comments simultaneously
- **Database Query Optimization**: Profile query performance under load
- **Memory Usage**: Test memory consumption with large comment threads

### Security Tests
- **Authorization**: Test comment visibility and editing permissions
- **Input Validation**: Test against XSS and injection attacks  
- **Data Privacy**: Test that internal comments are not exposed
- **API Key Validation**: Test authentication with invalid/expired keys
- **Cross-Organization Access**: Verify strict organization isolation

### Validation Criteria
- All E2E tests must pass with 100% success rate
- Response times <200ms for 95% of comment operations  
- History queries complete within 500ms for 99% of requests
- Zero data leakage between organizations
- Complete audit trail for all operations
- Graceful degradation when external integrations fail

## Error Handling

### Comment Sync Failures
- Retry logic with exponential backoff
- Queue failed syncs for later retry
- Alert administrators for persistent failures
- Graceful degradation when external systems are unavailable

### History Recording Failures
- Ensure history recording doesn't block main operations
- Log failures for later investigation
- Provide fallback mechanisms for critical changes

### Integration API Errors
- Handle rate limiting from external APIs
- Manage authentication token expiration
- Provide meaningful error messages to users

## Monitoring & Observability

### Metrics
- Comment creation/update/delete rates
- History record creation rates
- Integration sync success/failure rates
- API response times
- Database query performance

### Logging
- All comment operations with user context
- All history recording events
- Integration sync attempts and results
- Error conditions with full context

### Alerts
- High comment sync failure rates
- Database performance degradation
- External API quota exhaustion
- Security events (unauthorized access attempts)

## Migration Strategy

### Data Migration
- Existing ticket data will not have history records (acceptable)
- Provide option to generate initial history records for current state
- Ensure backward compatibility during rollout

### Feature Rollout
- Phase 1: History tracking (low risk)
- Phase 2: Comments (medium risk, user-facing)
- Phase 3: Integration sync (high risk, external dependencies)
- Use feature flags to control rollout

### Rollback Plan
- Database migrations are reversible
- Feature flags allow quick disable
- Comment sync can be disabled without affecting core functionality
- Full rollback procedures documented

## Success Criteria

### Functional Requirements
- ✅ Users can view complete ticket history
- ✅ Users can add, edit, and delete comments
- ✅ AI agents can create comments via tool interface  
- ✅ Comments sync bidirectionally with Jira
- ✅ All changes are properly attributed and timestamped

### Performance Requirements
- History queries return in <500ms for 95th percentile
- Comment operations complete in <200ms
- Integration sync completes in <5 seconds for 95% of operations
- System supports 1000+ concurrent users

### Quality Requirements  
- >95% test coverage for new code
- Zero data loss during sync operations
- <0.1% error rate for comment operations
- Complete audit trail for all changes

## Risks & Mitigation

### High Risk
- **External API Rate Limits**: Implement proper throttling and queuing
- **Data Consistency**: Use database transactions and proper locking
- **Performance Impact**: Optimize queries and add appropriate indexes

### Medium Risk
- **User Adoption**: Provide clear UI/UX and training materials
- **Integration Complexity**: Start with simple sync and iterate
- **Scalability**: Design with horizontal scaling in mind

### Low Risk
- **Browser Compatibility**: Use standard web technologies
- **Mobile Support**: Ensure responsive design
- **Accessibility**: Follow WCAG guidelines

## Dependencies

### Internal
- User authentication system
- Existing ticket management system
- Integration framework
- WebSocket infrastructure
- AI agent framework

### External
- Jira Cloud API v3
- ServiceNow API (future)
- Database (PostgreSQL)
- Redis for caching/queuing

## Future Enhancements

### Phase 2 Features
- Comment reactions/voting
- Advanced comment search
- Comment templates
- Automated comment generation based on ticket changes

### Integration Expansions  
- ServiceNow comment sync
- Slack comment integration
- Email-to-comment functionality
- Microsoft Teams integration

### Analytics & Reporting
- Comment sentiment analysis
- Response time analytics
- User engagement metrics  
- Trend analysis for ticket patterns

## Conclusion

This PRP provides a comprehensive plan for implementing ticket activity tracking and commenting functionality. The phased approach ensures manageable development cycles while delivering value incrementally. The integration synchronization capabilities will significantly enhance the system's utility for organizations using external ticketing platforms.

The implementation will provide full visibility into ticket evolution, enable rich communication around tickets, and maintain synchronization with external systems - addressing all the key requirements outlined in the initial request.