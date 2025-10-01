#!/usr/bin/env python3
"""
Agent Action model for tracking agent operations and performance metrics
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import (
    DECIMAL,
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class AgentAction(BaseModel):
    """
    Track all actions performed by agents for analytics and performance monitoring.
    
    Records agent operations including chat responses, ticket creation,
    tool usage, and performance metrics for continuous improvement.
    """
    
    __tablename__ = "agent_actions"
    
    # Agent relationship
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Agent that performed the action"
    )
    
    # Action identification
    action_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Type of action (chat_response, ticket_creation, tool_call, etc.)"
    )
    
    action_subtype = Column(
        String(50),
        nullable=True,
        comment="Subtype for more specific action categorization"
    )
    
    # Action data and context
    action_data = Column(
        JSON,
        nullable=False,
        comment="Input data and parameters for the action"
    )
    
    action_context = Column(
        JSON,
        nullable=True,
        comment="Context information (conversation ID, user info, etc.)"
    )
    
    # Results and outcomes
    result_data = Column(
        JSON,
        nullable=True,
        comment="Action results and outputs"
    )
    
    success = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether the action completed successfully"
    )
    
    error_message = Column(
        Text,
        nullable=True,
        comment="Error message if action failed"
    )
    
    # Performance metrics
    execution_time_ms = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Execution time in milliseconds"
    )
    
    tokens_used = Column(
        Integer,
        nullable=True,
        comment="Number of AI model tokens consumed"
    )
    
    cost_cents = Column(
        DECIMAL(10, 4),
        nullable=True,
        comment="Estimated cost in cents for the action"
    )
    
    # Quality metrics
    confidence_score = Column(
        DECIMAL(5, 4),
        nullable=True,
        comment="Agent confidence in the action result (0.0 to 1.0)"
    )
    
    quality_score = Column(
        DECIMAL(5, 4),
        nullable=True,
        comment="Quality assessment score (0.0 to 1.0)"
    )
    
    user_feedback_score = Column(
        Integer,
        nullable=True,
        comment="User feedback score (1-5 stars) if available"
    )
    
    # Timing and context
    started_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
        comment="When the action started"
    )
    
    completed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="When the action completed"
    )
    
    # User and session context
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        comment="User who triggered the action (if applicable)"
    )
    
    session_id = Column(
        String(255),
        nullable=True,
        index=True,
        comment="Session ID for grouping related actions"
    )
    
    conversation_id = Column(
        String(255),
        nullable=True,
        index=True,
        comment="Conversation ID for chat-related actions"
    )
    
    # Source and channel information
    source_channel = Column(
        String(50),
        nullable=True,
        comment="Channel that triggered the action (api, slack, email, etc.)"
    )
    
    source_reference = Column(
        String(255),
        nullable=True,
        comment="External reference ID"
    )
    
    ip_address = Column(
        String(45),
        nullable=True,
        comment="IP address of the request (if applicable)"
    )
    
    user_agent = Column(
        Text,
        nullable=True,
        comment="User agent string (if from web request)"
    )
    
    # Tool and integration tracking
    tools_used = Column(
        JSON,
        nullable=True,
        comment="List of tools/integrations used in the action"
    )
    
    integration_calls = Column(
        JSON,
        nullable=True,
        comment="External API calls made during action"
    )
    
    # Content and output metadata
    input_length = Column(
        Integer,
        nullable=True,
        comment="Length of input content in characters"
    )
    
    output_length = Column(
        Integer,
        nullable=True,
        comment="Length of output content in characters"
    )
    
    media_processed = Column(
        JSON,
        nullable=True,
        comment="Information about processed media files"
    )
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0.0 AND confidence_score <= 1.0)",
            name='ck_agent_action_confidence_score'
        ),
        CheckConstraint(
            "quality_score IS NULL OR (quality_score >= 0.0 AND quality_score <= 1.0)",
            name='ck_agent_action_quality_score'
        ),
        CheckConstraint(
            "user_feedback_score IS NULL OR (user_feedback_score >= 1 AND user_feedback_score <= 5)",
            name='ck_agent_action_user_feedback'
        ),
        {'comment': 'Agent action tracking with performance metrics and analytics'}
    )
    
    # Relationships
    agent = relationship(
        "Agent",
        back_populates="actions",
        lazy="select"
    )
    
    user = relationship(
        "User",
        lazy="select"
    )
    
    def __repr__(self):
        return f"<AgentAction(id={self.id}, agent_id={self.agent_id}, action_type={self.action_type}, success={self.success})>"
    
    @property
    def duration_seconds(self) -> float:
        """Get action duration in seconds"""
        if self.completed_at and self.started_at:
            delta = self.completed_at - self.started_at
            return delta.total_seconds()
        return self.execution_time_ms / 1000.0 if self.execution_time_ms else 0.0
    
    @property
    def is_successful(self) -> bool:
        """Check if action was successful"""
        return self.success
    
    @property
    def has_user_feedback(self) -> bool:
        """Check if user feedback is available"""
        return self.user_feedback_score is not None
    
    @property
    def performance_category(self) -> str:
        """Categorize performance based on execution time"""
        duration_ms = self.execution_time_ms or 0
        
        if duration_ms < 1000:  # < 1 second
            return "fast"
        elif duration_ms < 5000:  # < 5 seconds
            return "normal"
        elif duration_ms < 15000:  # < 15 seconds
            return "slow"
        else:
            return "very_slow"
    
    @property
    def cost_dollars(self) -> Optional[float]:
        """Get cost in dollars"""
        if self.cost_cents is not None:
            return float(self.cost_cents) / 100.0
        return None
    
    @property
    def tokens_per_second(self) -> Optional[float]:
        """Calculate tokens processed per second"""
        if self.tokens_used and self.duration_seconds > 0:
            return self.tokens_used / self.duration_seconds
        return None
    
    def mark_completed(self, result_data: Dict[str, Any], 
                      success: bool = True, 
                      error_message: Optional[str] = None) -> None:
        """Mark action as completed with results"""
        self.completed_at = datetime.now(timezone.utc)
        self.result_data = result_data
        self.success = success
        
        if error_message:
            self.error_message = error_message
        
        # Calculate execution time
        if self.started_at and self.completed_at:
            duration = self.completed_at - self.started_at
            self.execution_time_ms = int(duration.total_seconds() * 1000)
    
    def set_performance_metrics(self, 
                              tokens_used: Optional[int] = None,
                              cost_cents: Optional[float] = None,
                              confidence_score: Optional[float] = None) -> None:
        """Set performance metrics for the action"""
        if tokens_used is not None:
            self.tokens_used = tokens_used
        
        if cost_cents is not None:
            self.cost_cents = cost_cents
        
        if confidence_score is not None:
            if not (0.0 <= confidence_score <= 1.0):
                raise ValueError("Confidence score must be between 0.0 and 1.0")
            self.confidence_score = confidence_score
    
    def set_quality_metrics(self, 
                          quality_score: Optional[float] = None,
                          user_feedback_score: Optional[int] = None) -> None:
        """Set quality metrics for the action"""
        if quality_score is not None:
            if not (0.0 <= quality_score <= 1.0):
                raise ValueError("Quality score must be between 0.0 and 1.0")
            self.quality_score = quality_score
        
        if user_feedback_score is not None:
            if not (1 <= user_feedback_score <= 5):
                raise ValueError("User feedback score must be between 1 and 5")
            self.user_feedback_score = user_feedback_score
    
    def add_tool_usage(self, tool_name: str, tool_data: Dict[str, Any]) -> None:
        """Add tool usage information"""
        tools = self.tools_used or []
        tools.append({
            "tool": tool_name,
            "data": tool_data,
            "used_at": datetime.now(timezone.utc).isoformat()
        })
        self.tools_used = tools
    
    def add_integration_call(self, integration: str, 
                           endpoint: str, 
                           duration_ms: int,
                           success: bool = True) -> None:
        """Add external integration call information"""
        calls = self.integration_calls or []
        calls.append({
            "integration": integration,
            "endpoint": endpoint,
            "duration_ms": duration_ms,
            "success": success,
            "called_at": datetime.now(timezone.utc).isoformat()
        })
        self.integration_calls = calls
    
    @classmethod
    def create_chat_response_action(cls, 
                                  agent_id: UUID,
                                  user_id: UUID,
                                  conversation_id: str,
                                  message_data: Dict[str, Any]) -> 'AgentAction':
        """Create an action for chat response"""
        return cls(
            agent_id=agent_id,
            action_type="chat_response",
            user_id=user_id,
            conversation_id=conversation_id,
            action_data=message_data,
            session_id=conversation_id,
            started_at=datetime.now(timezone.utc)
        )
    
    @classmethod
    def create_ticket_action(cls,
                           agent_id: UUID,
                           user_id: UUID,
                           action_subtype: str,
                           ticket_data: Dict[str, Any]) -> 'AgentAction':
        """Create an action for ticket operations"""
        return cls(
            agent_id=agent_id,
            action_type="ticket_operation",
            action_subtype=action_subtype,
            user_id=user_id,
            action_data=ticket_data,
            started_at=datetime.now(timezone.utc)
        )
    
    @classmethod
    def create_tool_call_action(cls,
                              agent_id: UUID,
                              tool_name: str,
                              tool_data: Dict[str, Any],
                              context: Optional[Dict[str, Any]] = None) -> 'AgentAction':
        """Create an action for tool calls"""
        return cls(
            agent_id=agent_id,
            action_type="tool_call",
            action_subtype=tool_name,
            action_data=tool_data,
            action_context=context or {},
            started_at=datetime.now(timezone.utc)
        )
    
    def to_dict(self, include_sensitive: bool = False) -> dict:
        """Convert action to dictionary"""
        data = super().to_dict()
        
        # Add computed properties
        data['duration_seconds'] = self.duration_seconds
        data['performance_category'] = self.performance_category
        data['cost_dollars'] = self.cost_dollars
        data['tokens_per_second'] = self.tokens_per_second
        data['has_user_feedback'] = self.has_user_feedback
        
        if not include_sensitive:
            # Remove sensitive information
            data.pop('ip_address', None)
            data.pop('user_agent', None)
            
            # Limit action_data and result_data for privacy
            if 'action_data' in data:
                # Keep only non-sensitive fields
                sensitive_fields = ['password', 'token', 'key', 'secret']
                action_data = data.get('action_data', {})
                if isinstance(action_data, dict):
                    data['action_data'] = {
                        k: v for k, v in action_data.items()
                        if not any(sensitive in k.lower() for sensitive in sensitive_fields)
                    }
        
        return data