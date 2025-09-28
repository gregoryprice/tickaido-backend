#!/usr/bin/env python3
"""
Agent Schemas for API request/response validation
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class AgentCreateRequest(BaseModel):
    """Schema for creating a new agent"""
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True
    )
    
    # Required fields
    name: str = Field(..., min_length=1, max_length=255, description="Human-readable name for the agent")
    agent_type: str = Field(default="customer_support", description="Type of agent")
    
    # Optional personalization - avatar_url removed, now handled by dedicated avatar endpoints
    
    # Optional configuration fields
    role: Optional[str] = Field(None, max_length=255, description="Agent role and responsibility description")
    prompt: Optional[str] = Field(None, description="System prompt for Pydantic AI agent initialization")
    initial_context: Optional[str] = Field(None, description="Initial context provided to agent conversations")
    initial_ai_msg: Optional[str] = Field(None, description="Initial AI message for conversation start")
    tone: Optional[str] = Field(None, max_length=100, description="Communication tone")
    communication_style: str = Field(default="formal", description="Communication style preference")
    
    # Processing configuration
    use_streaming: bool = Field(default=False, description="Whether to use streaming responses")
    response_length: str = Field(default="moderate", description="Preferred response length")
    memory_retention: int = Field(default=5, ge=1, le=20, description="Number of previous messages to retain")
    show_suggestions_after_each_message: bool = Field(default=True, description="Whether to show suggested responses")
    suggestions_prompt: Optional[str] = Field(None, description="Custom prompt for generating suggestions")
    max_context_size: int = Field(default=100000, ge=1000, le=1000000, description="Maximum context window size in tokens")
    use_memory_context: bool = Field(default=True, description="Whether to use conversation memory in context")
    max_iterations: int = Field(default=5, ge=1, le=10, description="Maximum number of tool call iterations")
    timeout_seconds: Optional[int] = Field(None, ge=1, le=300, description="Timeout for agent responses")
    tools: List[str] = Field(default_factory=list, description="List of enabled tool names")


class AgentUpdateRequest(BaseModel):
    """Schema for updating an agent"""
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True
    )
    
    # All fields are optional for updates
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Human-readable name for the agent")
    is_active: Optional[bool] = Field(None, description="Whether agent is active")
    # avatar_url removed - now handled by dedicated avatar endpoints
    
    # Configuration fields
    role: Optional[str] = Field(None, max_length=255, description="Agent role and responsibility description")
    prompt: Optional[str] = Field(None, description="System prompt for Pydantic AI agent initialization")
    initial_context: Optional[str] = Field(None, description="Initial context provided to agent conversations")
    initial_ai_msg: Optional[str] = Field(None, description="Initial AI message for conversation start")
    tone: Optional[str] = Field(None, max_length=100, description="Communication tone")
    communication_style: Optional[str] = Field(None, description="Communication style preference")
    
    # Processing configuration
    use_streaming: Optional[bool] = Field(None, description="Whether to use streaming responses")
    response_length: Optional[str] = Field(None, description="Preferred response length")
    memory_retention: Optional[int] = Field(None, ge=1, le=20, description="Number of previous messages to retain")
    show_suggestions_after_each_message: Optional[bool] = Field(None, description="Whether to show suggested responses")
    suggestions_prompt: Optional[str] = Field(None, description="Custom prompt for generating suggestions")
    max_context_size: Optional[int] = Field(None, ge=1000, le=1000000, description="Maximum context window size in tokens")
    use_memory_context: Optional[bool] = Field(None, description="Whether to use conversation memory in context")
    max_iterations: Optional[int] = Field(None, ge=1, le=10, description="Maximum number of tool call iterations")
    timeout_seconds: Optional[int] = Field(None, ge=1, le=300, description="Timeout for agent responses")
    tools: Optional[List[str]] = Field(None, description="List of enabled tool names")


class AgentResponse(BaseModel):
    """Schema for agent API responses"""
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True
    )
    
    # Core fields
    id: UUID
    organization_id: UUID
    name: str
    agent_type: str
    avatar_url: Optional[str] = None
    is_active: bool
    status: str
    
    # Configuration fields embedded
    role: Optional[str] = None
    prompt: Optional[str] = None
    initial_context: Optional[str] = None
    initial_ai_msg: Optional[str] = None
    tone: Optional[str] = None
    communication_style: str
    
    # Processing configuration
    use_streaming: bool
    response_length: str
    memory_retention: int
    show_suggestions_after_each_message: bool
    suggestions_prompt: Optional[str] = None
    max_context_size: int
    use_memory_context: bool
    max_iterations: int
    timeout_seconds: Optional[int] = None
    tools: List[str] = Field(default_factory=list)
    
    # Metadata
    last_used_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    # Computed properties
    is_ready: bool
    tools_count: int


class AgentListResponse(BaseModel):
    """Schema for agent list API responses"""
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True
    )
    
    agents: List[AgentResponse]
    total: int
    page: int = 1
    limit: int = 50


class AgentHistoryResponse(BaseModel):
    """Schema for agent change history responses"""
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True
    )
    
    id: UUID
    agent_id: UUID
    changed_by_user_id: UUID
    change_type: str
    field_changed: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    change_timestamp: datetime
    change_reason: Optional[str] = None
    ip_address: Optional[str] = None
    
    # Computed properties  
    change_summary: str = ""
    parsed_old_value: Any = None
    parsed_new_value: Any = None
    
    # User info if available
    changed_by_name: Optional[str] = None


class AgentHistoryListResponse(BaseModel):
    """Schema for agent history list responses"""
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True
    )
    
    history: List[AgentHistoryResponse]
    total: int
    page: int = 1
    limit: int = 50


class AgentFileAttachRequest(BaseModel):
    """Schema for attaching files to agents"""
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True
    )
    
    file_id: UUID
    priority: str = Field(default="normal", description="File priority for context inclusion")


class AgentTaskCreateRequest(BaseModel):
    """Schema for creating agent tasks"""
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True
    )
    
    task_type: str
    task_data: Dict[str, Any]
    priority: int = Field(default=5, ge=1, le=10, description="Task priority")
    task_subtype: Optional[str] = None
    source_channel: Optional[str] = None
    source_reference: Optional[str] = None
    scheduled_at: Optional[datetime] = None


class AgentConfigurationResponse(BaseModel):
    """Schema for agent configuration responses"""
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True
    )
    
    agent_id: UUID
    configuration: Dict[str, Any]
    last_updated: datetime
    
    # Summary information
    total_tools: int
    active_integrations: List[str]
    performance_mode: str  # "standard", "optimized", "custom"


class AgentStatsResponse(BaseModel):
    """Schema for agent statistics responses"""
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True
    )
    
    agent_id: UUID
    agent_name: str
    
    # Usage statistics
    total_actions: int
    successful_actions: int
    success_rate: float
    avg_response_time_ms: float
    
    # Time-based metrics
    actions_today: int
    actions_this_week: int
    actions_this_month: int
    
    # Quality metrics
    avg_user_feedback: Optional[float] = None
    feedback_count: int = 0
    
    # File and context metrics
    attached_files: int
    processed_files: int
    context_size_bytes: int
    
    # Task queue metrics
    pending_tasks: int
    processing_tasks: int
    completed_tasks_today: int
    
    # Health status
    health_status: str  # "healthy", "degraded", "error"
    last_health_check: Optional[datetime] = None
    
    # Analysis metadata
    stats_period_days: int = 30
    generated_at: datetime


class ErrorResponse(BaseModel):
    """Schema for error responses"""
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True
    )
    
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now())


class AgentAvatarResponse(BaseModel):
    """Schema for agent avatar responses"""
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True
    )
    
    agent_id: Optional[UUID] = Field(None, description="Agent ID")
    avatar_url: Optional[str] = Field(None, description="Avatar URL")
    message: str = Field(description="Response message")
    filename: Optional[str] = Field(None, description="Original filename")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    upload_date: Optional[datetime] = Field(None, description="Upload timestamp")
    has_custom_avatar: Optional[bool] = Field(None, description="Whether agent has custom avatar")


class AgentAvatarDeleteResponse(BaseModel):
    """Schema for agent avatar deletion response"""
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True
    )
    
    agent_id: UUID = Field(description="Agent ID")
    deleted: bool = Field(description="Whether avatar was deleted")
    message: str = Field(description="Response message")


class AgentAvatarInfoResponse(BaseModel):
    """Schema for agent avatar info response - aligned with user avatar info"""
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True
    )
    
    id: UUID = Field(description="Agent ID")
    agent_id: UUID = Field(description="Agent ID")
    avatar_url: Optional[str] = Field(None, description="Avatar URL")
    filename: Optional[str] = Field(None, description="Original filename")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    upload_date: Optional[datetime] = Field(None, description="Upload timestamp")
    thumbnail_sizes: Optional[Dict[str, str]] = Field(
        None,
        description="Available thumbnail sizes with their URLs"
    )
    created_at: datetime = Field(description="Agent creation timestamp")
    updated_at: datetime = Field(description="Agent last update timestamp")


class SuccessResponse(BaseModel):
    """Schema for success responses"""
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True
    )
    
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now())