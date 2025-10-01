#!/usr/bin/env python3
"""
Chat models for agent-centric thread management
"""

import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import BaseModel


class Thread(BaseModel):
    """
    Thread model for agent-centric chat functionality.
    Each thread is associated with a specific AI agent and organization.
    """
    
    __tablename__ = 'threads'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey('agents.id'), nullable=False)
    user_id = Column(String(255), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=False)
    
    title = Column(String(500))  # Thread title
    
    # Message tracking fields
    total_messages = Column(Integer, default=0, nullable=False)
    last_message_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    archived = Column(Boolean, default=False)
    
    # Relationships
    agent = relationship("Agent", back_populates="threads")
    messages = relationship("Message", back_populates="thread", order_by="Message.created_at")
    organization = relationship("Organization")
    
    __table_args__ = (
        Index('idx_threads_agent_org', 'agent_id', 'organization_id'),
        Index('idx_threads_user_archived', 'user_id', 'archived'),
        Index('idx_threads_created_at', 'created_at'),
        Index('idx_threads_updated_at', 'updated_at'),
    )


class Message(BaseModel):
    """
    Message model for chat messages within threads.
    Supports tool calls, attachments, and enhanced metadata.
    """
    
    __tablename__ = 'messages'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id = Column(UUID(as_uuid=True), ForeignKey('threads.id'), nullable=False)
    
    # Message content
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    content_html = Column(Text, nullable=True)  # HTML content support
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Tool calling support
    tool_calls = Column(JSON, nullable=True)  # Array of tool call objects
    
    # Attachments support  
    attachments = Column(JSON, nullable=True, comment="Array of file references: [{'file_id':'uuid'}]")
    
    # Message metadata matches migration column
    message_metadata = Column("message_metadata", JSON, nullable=True)
    
    # Performance tracking (model_used and tokens_used removed)
    response_time_ms = Column(Integer, nullable=True)
    confidence_score = Column(Float, nullable=True)
    
    # Relationships
    thread = relationship("Thread", back_populates="messages")
    
    __table_args__ = (
        Index('idx_messages_thread_id', 'thread_id'),
        Index('idx_messages_created_at', 'created_at'),
        Index('idx_messages_role', 'role'),
    )


# Clean agent-centric thread architecture - no legacy models