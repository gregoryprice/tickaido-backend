#!/usr/bin/env python3
"""
Agent File model for managing file attachments and context processing
"""

import hashlib
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class AgentFile(BaseModel):
    """
    Relationship model between agents and files for context processing.
    
    Manages up to 20 files per agent with text extraction, processing status,
    and order management for context window assembly.
    """
    
    __tablename__ = "agent_files"
    
    # Agent relationship
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Agent this file belongs to"
    )
    
    # File relationship
    file_id = Column(
        UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="File attached to agent"
    )
    
    # Processing status and metadata
    processing_status = Column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
        comment="Processing status (pending, processing, completed, failed)"
    )
    
    # Extracted content for context
    extracted_content = Column(
        Text,
        nullable=True,
        comment="Text content extracted from file for agent context"
    )
    
    # Content metadata
    content_hash = Column(
        String(64),
        nullable=True,
        index=True,
        comment="SHA-256 hash of extracted content for deduplication"
    )
    
    content_length = Column(
        Integer,
        nullable=True,
        comment="Length of extracted content in characters"
    )
    
    # File order and priority
    order_index = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Order of file in agent context (0 = first)"
    )
    
    priority = Column(
        String(10),
        nullable=False,
        default="normal",
        comment="File priority for context inclusion (high, normal, low)"
    )
    
    # Processing metadata
    processing_started_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When processing started"
    )
    
    processing_completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When processing completed"
    )
    
    processing_error = Column(
        Text,
        nullable=True,
        comment="Error message if processing failed"
    )
    
    # File metadata at attachment time
    attached_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        comment="When file was attached to agent"
    )
    
    attached_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        comment="User who attached the file"
    )
    
    # Context usage metadata
    last_used_in_context = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When this file was last used in agent context"
    )
    
    usage_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of times file content was used in context"
    )
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "processing_status IN ('pending', 'processing', 'completed', 'failed')",
            name='ck_agent_file_processing_status'
        ),
        CheckConstraint(
            "priority IN ('high', 'normal', 'low')",
            name='ck_agent_file_priority'
        ),
        {'comment': 'Agent file relationships with processing status and context metadata'}
    )
    
    # Relationships
    agent = relationship(
        "Agent",
        back_populates="files",
        lazy="select"
    )
    
    file = relationship(
        "File",
        lazy="select"
    )
    
    attached_by = relationship(
        "User",
        lazy="select"
    )
    
    def __repr__(self):
        return f"<AgentFile(id={self.id}, agent_id={self.agent_id}, file_id={self.file_id}, status={self.processing_status})>"
    
    @property
    def is_processed(self) -> bool:
        """Check if file has been successfully processed"""
        return self.processing_status == "completed"
    
    @property
    def is_processing(self) -> bool:
        """Check if file is currently being processed"""
        return self.processing_status == "processing"
    
    @property
    def has_content(self) -> bool:
        """Check if extracted content is available"""
        return self.extracted_content is not None and len(self.extracted_content.strip()) > 0
    
    @property
    def processing_duration_seconds(self) -> Optional[float]:
        """Get processing duration in seconds if available"""
        if self.processing_started_at and self.processing_completed_at:
            delta = self.processing_completed_at - self.processing_started_at
            return delta.total_seconds()
        return None
    
    @property
    def context_preview(self) -> str:
        """Get a preview of the content for display"""
        if not self.extracted_content:
            return ""
        
        preview_length = 200
        content = self.extracted_content.strip()
        
        if len(content) <= preview_length:
            return content
        
        return content[:preview_length] + "..."
    
    def mark_processing_started(self) -> None:
        """Mark file as processing started"""
        self.processing_status = "processing"
        self.processing_started_at = datetime.now(timezone.utc)
        self.processing_error = None
    
    def mark_processing_completed(self, extracted_content: str) -> None:
        """Mark file as processing completed with extracted content"""
        self.processing_status = "completed"
        self.processing_completed_at = datetime.now(timezone.utc)
        self.extracted_content = extracted_content
        self.content_length = len(extracted_content) if extracted_content else 0
        
        # Generate content hash for deduplication
        if extracted_content:
            self.content_hash = hashlib.sha256(
                extracted_content.encode('utf-8')
            ).hexdigest()
        
        self.processing_error = None
    
    def mark_processing_failed(self, error_message: str) -> None:
        """Mark file as processing failed with error"""
        self.processing_status = "failed"
        self.processing_completed_at = datetime.now(timezone.utc)
        self.processing_error = error_message
        self.extracted_content = None
        self.content_length = None
        self.content_hash = None
    
    def record_context_usage(self) -> None:
        """Record that this file was used in agent context"""
        self.last_used_in_context = datetime.now(timezone.utc)
        self.usage_count = (self.usage_count or 0) + 1
    
    def update_order(self, new_order: int) -> None:
        """Update the order index for this file"""
        self.order_index = new_order
    
    def set_priority(self, priority: str) -> None:
        """Set the priority for context inclusion"""
        valid_priorities = ["high", "normal", "low"]
        if priority not in valid_priorities:
            raise ValueError(f"Priority must be one of: {valid_priorities}")
        
        self.priority = priority
    
    @classmethod
    def get_max_files_per_agent(cls) -> int:
        """Get maximum number of files allowed per agent"""
        return 20
    
    def to_dict(self, include_content: bool = False) -> dict:
        """Convert agent file to dictionary"""
        data = super().to_dict()
        
        # Add computed properties
        data['is_processed'] = self.is_processed
        data['is_processing'] = self.is_processing
        data['has_content'] = self.has_content
        data['processing_duration_seconds'] = self.processing_duration_seconds
        data['context_preview'] = self.context_preview
        
        if not include_content:
            # Remove full content for lighter responses
            data.pop('extracted_content', None)
        
        return data