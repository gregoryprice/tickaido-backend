#!/usr/bin/env python3
"""
Agent model for organization-scoped multi-agent management
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, Text, JSON, Integer, ForeignKey, DECIMAL, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class Agent(BaseModel):
    """
    Organization-scoped multi-agent with embedded configuration management.
    
    Organizations can have multiple agents of different types without
    singleton constraints, enabling specialized agent deployment.
    """
    
    __tablename__ = "agents"
    
    # Organization relationship
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Organization this agent belongs to"
    )
    
    # Agent type and identification
    agent_type = Column(
        String(50),
        nullable=False,
        default="customer_support",
        index=True,
        comment="Type of agent (customer_support, categorization, etc.)"
    )
    
    name = Column(
        String(255),
        nullable=False,
        default="AI Agent",
        comment="Human-readable name for the agent"
    )
    
    # Agent personalization
    avatar_url = Column(
        String(500),
        nullable=True,
        comment="URL for agent avatar image"
    )
    
    has_custom_avatar = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether agent has a custom uploaded avatar"
    )
    
    # Agent status
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether agent is active and ready to handle requests"
    )
    
    status = Column(
        String(20),
        nullable=False,
        default="active",
        index=True,
        comment="Current agent status (active, inactive, error, maintenance)"
    )
    
    # Configuration fields embedded directly (no separate table)
    # Agent behavior configuration
    role = Column(
        String(255),
        nullable=True,
        comment="Agent role and responsibility description"
    )
    
    prompt = Column(
        Text,
        nullable=True,
        comment="System prompt for Pydantic AI agent initialization"
    )
    
    initial_context = Column(
        Text,
        nullable=True,
        comment="Initial context provided to agent conversations"
    )
    
    initial_ai_msg = Column(
        Text,
        nullable=True,
        comment="Initial AI message for conversation start"
    )
    
    tone = Column(
        String(100),
        nullable=True,
        comment="Communication tone (formal, casual, professional, etc.)"
    )
    
    communication_style = Column(
        String(100),
        nullable=False,
        default="formal",
        comment="Communication style preference"
    )
    
    # Processing configuration
    use_streaming = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether to use streaming responses"
    )
    
    response_length = Column(
        String(20),
        nullable=False,
        default="moderate",
        comment="Preferred response length (brief, moderate, detailed)"
    )
    
    memory_retention = Column(
        Integer,
        nullable=False,
        default=5,
        comment="Number of previous messages to retain in memory"
    )
    
    show_suggestions_after_each_message = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether to show suggested responses"
    )
    
    suggestions_prompt = Column(
        Text,
        nullable=True,
        comment="Custom prompt for generating suggestions"
    )
    
    max_context_size = Column(
        Integer,
        nullable=False,
        default=100000,
        comment="Maximum context window size in tokens"
    )
    
    use_memory_context = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether to use conversation memory in context"
    )
    
    max_iterations = Column(
        Integer,
        nullable=False,
        default=5,
        comment="Maximum number of tool call iterations"
    )
    
    timeout_seconds = Column(
        Integer,
        nullable=True,
        comment="Timeout for agent responses in seconds"
    )
    
    tools = Column(
        JSON,
        nullable=False,
        default=list,
        comment="List of enabled tool names"
    )
    
    # Usage tracking
    last_used_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When agent was last used to process a message"
    )
    
    
    # Additional metadata
    extra_metadata = Column(
        JSON,
        nullable=True,
        comment="Additional metadata and custom fields"
    )
    
    # Table configuration (removed unique constraint to allow multiple agents per org)
    __table_args__ = (
        {'comment': 'Multi-agent system for organization-scoped automation and support'}
    )
    
    # Relationships
    organization = relationship(
        "Organization",
        back_populates="agents",
        lazy="select"
    )
    
    usage_stats = relationship(
        "AgentUsageStats",
        back_populates="agent",
        cascade="all, delete-orphan",
        order_by="AgentUsageStats.period_start.desc()"
    )
    
    history = relationship(
        "AgentHistory",
        back_populates="agent",
        cascade="all, delete-orphan",
        order_by="AgentHistory.change_timestamp.desc()"
    )
    
    files = relationship(
        "AgentFile",
        back_populates="agent",
        cascade="all, delete-orphan"
    )
    
    tasks = relationship(
        "AgentTask",
        back_populates="agent",
        cascade="all, delete-orphan"
    )
    
    actions = relationship(
        "AgentAction",
        back_populates="agent",
        cascade="all, delete-orphan"
    )
    
    threads = relationship(
        "Thread",
        back_populates="agent",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<Agent(id={self.id}, organization_id={self.organization_id}, agent_type={self.agent_type}, name={self.name})>"
    
    @property
    def effective_name(self) -> str:
        """Get effective display name for the agent"""
        return str(self.name or f"{self.agent_type.replace('_', ' ').title()} Agent")
    
    @property
    def is_customer_support(self) -> bool:
        """Check if this is a customer support agent"""
        return str(self.agent_type) == "customer_support"
    
    @property
    def is_ready(self) -> bool:
        """Check if agent is ready to handle requests"""
        return self.is_active and self.status == "active"
    
    @property
    def tools_count(self) -> int:
        """Get count of enabled tools"""
        return len(self.tools or [])
    
    @property
    def mcp_enabled(self) -> bool:
        """Check if MCP integration is enabled"""
        # MCP is enabled by default for all agents in new architecture
        return True
    
    def get_configuration(self) -> Dict[str, Any]:
        """
        Get agent configuration assembled from embedded fields.
        
        Returns:
            Dict[str, Any]: Agent configuration dictionary
        """
        return {
            "role": self.role,
            "prompt": self.prompt,
            "initial_context": self.initial_context,
            "initial_ai_msg": self.initial_ai_msg,
            "tone": self.tone,
            "communication_style": self.communication_style,
            "use_streaming": self.use_streaming,
            "response_length": self.response_length,
            "memory_retention": self.memory_retention,
            "show_suggestions_after_each_message": self.show_suggestions_after_each_message,
            "suggestions_prompt": self.suggestions_prompt,
            "max_context_size": self.max_context_size,
            "use_memory_context": self.use_memory_context,
            "max_iterations": self.max_iterations,
            "timeout_seconds": self.timeout_seconds,
            "tools_enabled": self.tools or []
        }
    
    def update_configuration(self, updates: Dict[str, Any]) -> None:
        """
        Update agent configuration fields directly.
        
        Args:
            updates: Dictionary of configuration updates
        """
        field_mapping = {
            "role": "role",
            "prompt": "prompt",
            "initial_context": "initial_context",
            "initial_ai_msg": "initial_ai_msg",
            "tone": "tone",
            "communication_style": "communication_style",
            "use_streaming": "use_streaming",
            "response_length": "response_length",
            "memory_retention": "memory_retention",
            "show_suggestions_after_each_message": "show_suggestions_after_each_message",
            "suggestions_prompt": "suggestions_prompt",
            "max_context_size": "max_context_size",
            "use_memory_context": "use_memory_context",
            "max_iterations": "max_iterations",
            "timeout_seconds": "timeout_seconds",
            "tools_enabled": "tools"
        }
        
        for config_key, value in updates.items():
            field_name = field_mapping.get(config_key)
            if field_name and hasattr(self, field_name):
                setattr(self, field_name, value)
    
    def activate(self) -> None:
        """Activate the agent"""
        self.is_active = True
        self.status = "active"
    
    def deactivate(self) -> None:
        """Deactivate the agent"""
        self.is_active = False
        self.status = "inactive"
    
    def mark_error(self, error_details: Optional[str] = None) -> None:
        """Mark agent as having an error"""
        self.is_active = False
        self.status = "error"
        if error_details:
            metadata = self.extra_metadata or {}
            metadata['last_error'] = error_details
            metadata['last_error_at'] = datetime.now(timezone.utc).isoformat()
            self.extra_metadata = metadata
    
    def mark_maintenance(self) -> None:
        """Mark agent as under maintenance"""
        self.is_active = False
        self.status = "maintenance"
    
    def record_usage(self) -> None:
        """Record that the agent was used"""
        self.last_used_at = datetime.now(timezone.utc)
    
    def reset_to_defaults(self, default_config: Dict[str, Any]) -> None:
        """
        Reset agent configuration to defaults from ai_config.yaml
        
        Args:
            default_config: Default configuration to apply
        """
        self.update_configuration(default_config)
        self.activate()  # Ensure agent is active after reset
    
    def get_enabled_tools(self) -> List[str]:
        """
        Get list of enabled tools for this agent.
        
        Returns:
            List[str]: List of enabled tool names
        """
        return self.tools or []
    
    def enable_tool(self, tool_name: str) -> None:
        """
        Enable a specific tool for this agent.
        
        Args:
            tool_name: Name of the tool to enable
        """
        tools = self.tools or []
        if tool_name not in tools:
            tools.append(tool_name)
            self.tools = tools
    
    def disable_tool(self, tool_name: str) -> None:
        """
        Disable a specific tool for this agent.
        
        Args:
            tool_name: Name of the tool to disable
        """
        tools = self.tools or []
        if tool_name in tools:
            tools.remove(tool_name)
            self.tools = tools
    
    def to_dict(self, include_config: bool = True) -> dict:
        """
        Convert agent to dictionary.
        
        Args:
            include_config: Include full configuration in output
            
        Returns:
            dict: Agent data
        """
        data = super().to_dict()
        
        if not include_config:
            # Remove configuration for lighter responses
            data.pop('configuration', None)
        
        # Add computed properties
        data['effective_name'] = self.effective_name
        data['is_customer_support'] = self.is_customer_support
        data['is_ready'] = self.is_ready
        data['tools_count'] = self.tools_count
        data['mcp_enabled'] = self.mcp_enabled
        data['avatar_url'] = self.avatar_url
        
        return data


class AgentUsageStats(BaseModel):
    """
    Usage statistics for AI agents to track performance and usage patterns.
    """
    
    __tablename__ = "agent_usage_stats"
    
    # Agent relationship
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Agent these stats belong to"
    )
    
    # Usage metrics
    total_messages = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Total messages processed by agent"
    )
    
    successful_responses = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of successful responses"
    )
    
    failed_responses = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of failed responses"
    )
    
    tools_called = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Total number of MCP tool calls made"
    )
    
    avg_response_time_ms = Column(
        DECIMAL(10, 2),
        nullable=True,
        comment="Average response time in milliseconds"
    )
    
    # Time period these stats cover
    period_start = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Start of statistics period"
    )
    
    period_end = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="End of statistics period"
    )
    
    # Additional metrics
    unique_users = Column(
        Integer,
        nullable=True,
        comment="Number of unique users who interacted with agent"
    )
    
    confidence_scores = Column(
        JSON,
        nullable=True,
        comment="Array of confidence scores for responses"
    )
    
    tool_usage = Column(
        JSON,
        nullable=True,
        comment="Breakdown of tool usage by tool name"
    )
    
    error_types = Column(
        JSON,
        nullable=True,
        comment="Breakdown of error types encountered"
    )
    
    # Relationships
    agent = relationship(
        "Agent",
        back_populates="usage_stats",
        lazy="select"
    )
    
    def __repr__(self):
        return f"<AgentUsageStats(id={self.id}, agent_id={self.agent_id}, period={self.period_start} to {self.period_end})>"
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as a percentage"""
        total = self.total_messages
        if total == 0:
            return 0.0
        return (self.successful_responses / total) * 100.0
    
    @property
    def failure_rate(self) -> float:
        """Calculate failure rate as a percentage"""
        total = self.total_messages
        if total == 0:
            return 0.0
        return (self.failed_responses / total) * 100.0
    
    @property
    def avg_tools_per_message(self) -> float:
        """Calculate average tools called per message"""
        if self.total_messages == 0:
            return 0.0
        return self.tools_called / self.total_messages
    
    @property
    def period_duration_hours(self) -> float:
        """Get the duration of the statistics period in hours"""
        delta = self.period_end - self.period_start
        return delta.total_seconds() / 3600.0
    
    def to_dict(self) -> dict:
        """Convert usage stats to dictionary"""
        data = super().to_dict()
        
        # Add computed properties
        data['success_rate'] = round(self.success_rate, 2)
        data['failure_rate'] = round(self.failure_rate, 2)
        data['avg_tools_per_message'] = round(self.avg_tools_per_message, 2)
        data['period_duration_hours'] = round(self.period_duration_hours, 2)
        
        return data