#!/usr/bin/env python3
"""
Agent Task model for autonomous task processing and queue management
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from sqlalchemy import Column, String, Text, Integer, ForeignKey, DateTime, JSON, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class AgentTask(BaseModel):
    """
    Task queue model for autonomous agent processing.
    
    Manages tasks from multiple channels (Slack, email, API) with priority
    scheduling, retry logic, and comprehensive status tracking.
    """
    
    __tablename__ = "agent_tasks"
    
    # Agent relationship
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Agent assigned to process this task"
    )
    
    # Task identification and type
    task_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Type of task (slack_message, email, api_request, health_check, etc.)"
    )
    
    task_subtype = Column(
        String(50),
        nullable=True,
        comment="Subtype for more granular task categorization"
    )
    
    # Task data and metadata
    task_data = Column(
        JSON,
        nullable=False,
        comment="Task input data and parameters"
    )
    
    task_metadata = Column(
        JSON,
        nullable=True,
        comment="Additional metadata about the task source and context"
    )
    
    # Task status and processing
    status = Column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
        comment="Task status (pending, assigned, processing, completed, failed, cancelled)"
    )
    
    priority = Column(
        Integer,
        nullable=False,
        default=5,
        index=True,
        comment="Task priority (1=highest, 10=lowest)"
    )
    
    # Scheduling and timing
    scheduled_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
        comment="When the task should be processed"
    )
    
    assigned_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When task was assigned to an agent"
    )
    
    started_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When task processing started"
    )
    
    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When task was completed"
    )
    
    # Celery integration
    celery_task_id = Column(
        String(255),
        nullable=True,
        index=True,
        comment="Celery task ID for tracking background processing"
    )
    
    # Retry and error handling
    retry_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of retry attempts made"
    )
    
    max_retries = Column(
        Integer,
        nullable=False,
        default=3,
        comment="Maximum number of retry attempts allowed"
    )
    
    last_error = Column(
        Text,
        nullable=True,
        comment="Last error message if task failed"
    )
    
    error_history = Column(
        JSON,
        nullable=True,
        comment="History of all error attempts"
    )
    
    # Results and output
    result_data = Column(
        JSON,
        nullable=True,
        comment="Task processing results and output"
    )
    
    result_metadata = Column(
        JSON,
        nullable=True,
        comment="Metadata about task processing (duration, resources used, etc.)"
    )
    
    # Task context and dependencies
    parent_task_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agent_tasks.id"),
        nullable=True,
        comment="Parent task if this is a subtask"
    )
    
    correlation_id = Column(
        String(255),
        nullable=True,
        index=True,
        comment="Correlation ID for grouping related tasks"
    )
    
    # Performance tracking
    estimated_duration_seconds = Column(
        Integer,
        nullable=True,
        comment="Estimated processing duration in seconds"
    )
    
    actual_duration_seconds = Column(
        Integer,
        nullable=True,
        comment="Actual processing duration in seconds"
    )
    
    # Source tracking
    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        comment="User who created the task (if applicable)"
    )
    
    source_channel = Column(
        String(50),
        nullable=True,
        comment="Channel that generated the task (slack, email, api, etc.)"
    )
    
    source_reference = Column(
        String(255),
        nullable=True,
        comment="External reference ID (slack message ID, email ID, etc.)"
    )
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'assigned', 'processing', 'completed', 'failed', 'cancelled')",
            name='ck_agent_task_status'
        ),
        CheckConstraint(
            "priority >= 1 AND priority <= 10",
            name='ck_agent_task_priority'
        ),
        {'comment': 'Agent task queue with autonomous processing and retry logic'}
    )
    
    # Relationships
    agent = relationship(
        "Agent",
        back_populates="tasks",
        lazy="select"
    )
    
    created_by = relationship(
        "User",
        lazy="select"
    )
    
    parent_task = relationship(
        "AgentTask",
        remote_side="AgentTask.id",
        lazy="select"
    )
    
    subtasks = relationship(
        "AgentTask",
        cascade="all, delete-orphan",
        lazy="select",
        overlaps="parent_task"
    )
    
    def __repr__(self):
        return f"<AgentTask(id={self.id}, agent_id={self.agent_id}, type={self.task_type}, status={self.status})>"
    
    @property
    def is_pending(self) -> bool:
        """Check if task is pending execution"""
        return self.status == "pending"
    
    @property
    def is_processing(self) -> bool:
        """Check if task is currently being processed"""
        return self.status in ("assigned", "processing")
    
    @property
    def is_completed(self) -> bool:
        """Check if task completed successfully"""
        return self.status == "completed"
    
    @property
    def is_failed(self) -> bool:
        """Check if task failed"""
        return self.status == "failed"
    
    @property
    def can_retry(self) -> bool:
        """Check if task can be retried"""
        return (self.status == "failed" and 
                self.retry_count < self.max_retries)
    
    @property
    def is_overdue(self) -> bool:
        """Check if task is overdue for processing"""
        if self.status not in ("pending", "assigned"):
            return False
        
        return datetime.now(timezone.utc) > self.scheduled_at
    
    @property
    def processing_duration(self) -> Optional[timedelta]:
        """Get task processing duration"""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None
    
    @property
    def wait_duration(self) -> Optional[timedelta]:
        """Get time task waited before processing"""
        if self.scheduled_at and self.started_at:
            return self.started_at - self.scheduled_at
        return None
    
    @property
    def queue_position(self) -> str:
        """Get estimated queue position (would be computed by service)"""
        return "unknown"  # This would be computed by the task service
    
    def assign_to_agent(self, agent_id: UUID) -> None:
        """Assign task to a specific agent"""
        self.agent_id = agent_id
        self.status = "assigned"
        self.assigned_at = datetime.now(timezone.utc)
    
    def mark_processing_started(self, celery_task_id: Optional[str] = None) -> None:
        """Mark task as processing started"""
        self.status = "processing"
        self.started_at = datetime.now(timezone.utc)
        
        if celery_task_id:
            self.celery_task_id = celery_task_id
    
    def mark_completed(self, result_data: Dict[str, Any], 
                      result_metadata: Optional[Dict[str, Any]] = None) -> None:
        """Mark task as completed successfully"""
        self.status = "completed"
        self.completed_at = datetime.now(timezone.utc)
        self.result_data = result_data
        self.result_metadata = result_metadata or {}
        
        # Calculate actual duration
        if self.started_at and self.completed_at:
            duration = self.completed_at - self.started_at
            self.actual_duration_seconds = int(duration.total_seconds())
    
    def mark_failed(self, error_message: str, 
                   retry_allowed: bool = True) -> None:
        """Mark task as failed with error details"""
        # Add error to history
        error_history = self.error_history or []
        error_history.append({
            "attempt": self.retry_count + 1,
            "error": error_message,
            "failed_at": datetime.now(timezone.utc).isoformat(),
            "processing_duration_seconds": (
                int((datetime.now(timezone.utc) - self.started_at).total_seconds())
                if self.started_at else None
            )
        })
        self.error_history = error_history
        
        self.last_error = error_message
        self.retry_count += 1
        
        # Determine if task should be retried or marked as failed
        if retry_allowed and self.can_retry:
            self.status = "pending"
            # Schedule retry with exponential backoff
            backoff_minutes = min(2 ** self.retry_count, 60)  # Max 1 hour
            self.scheduled_at = datetime.now(timezone.utc) + timedelta(minutes=backoff_minutes)
        else:
            self.status = "failed"
            self.completed_at = datetime.now(timezone.utc)
    
    def cancel(self, reason: Optional[str] = None) -> None:
        """Cancel the task"""
        self.status = "cancelled"
        self.completed_at = datetime.now(timezone.utc)
        
        if reason:
            cancellation_data = self.result_metadata or {}
            cancellation_data['cancellation_reason'] = reason
            self.result_metadata = cancellation_data
    
    def reschedule(self, new_time: datetime, reason: Optional[str] = None) -> None:
        """Reschedule task for a different time"""
        if self.status not in ("pending", "assigned"):
            raise ValueError(f"Cannot reschedule task with status: {self.status}")
        
        self.scheduled_at = new_time
        self.status = "pending"  # Reset to pending if it was assigned
        
        if reason:
            metadata = self.task_metadata or {}
            metadata['reschedule_reason'] = reason
            metadata['reschedule_count'] = metadata.get('reschedule_count', 0) + 1
            self.task_metadata = metadata
    
    def update_priority(self, new_priority: int) -> None:
        """Update task priority"""
        if not (1 <= new_priority <= 10):
            raise ValueError("Priority must be between 1 and 10")
        
        self.priority = new_priority
    
    def add_subtask(self, subtask_data: Dict[str, Any], 
                   task_type: str, priority: Optional[int] = None) -> 'AgentTask':
        """Create a subtask for this task"""
        subtask = AgentTask(
            agent_id=self.agent_id,
            task_type=task_type,
            task_data=subtask_data,
            priority=priority or self.priority,
            parent_task_id=self.id,
            correlation_id=self.correlation_id,
            source_channel=self.source_channel
        )
        
        return subtask
    
    @classmethod
    def create_health_check_task(cls, agent_id: UUID) -> 'AgentTask':
        """Create a health check task for an agent"""
        return cls(
            agent_id=agent_id,
            task_type="health_check",
            task_data={
                "check_type": "routine",
                "checks": ["configuration", "database", "file_access"]
            },
            priority=8,  # Lower priority
            max_retries=1,  # Limited retries for health checks
            scheduled_at=datetime.now(timezone.utc)
        )
    
    def to_dict(self, include_results: bool = True, 
               include_errors: bool = True) -> dict:
        """Convert task to dictionary"""
        data = super().to_dict()
        
        # Add computed properties
        data['is_pending'] = self.is_pending
        data['is_processing'] = self.is_processing
        data['is_completed'] = self.is_completed
        data['is_failed'] = self.is_failed
        data['can_retry'] = self.can_retry
        data['is_overdue'] = self.is_overdue
        data['queue_position'] = self.queue_position
        
        # Add duration information
        if self.processing_duration:
            data['processing_duration_seconds'] = self.processing_duration.total_seconds()
        if self.wait_duration:
            data['wait_duration_seconds'] = self.wait_duration.total_seconds()
        
        if not include_results:
            data.pop('result_data', None)
            data.pop('result_metadata', None)
        
        if not include_errors:
            data.pop('last_error', None)
            data.pop('error_history', None)
        
        return data