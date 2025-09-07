#!/usr/bin/env python3
"""
Chat schemas for API validation and serialization - Agent-Centric Thread Architecture
"""

from datetime import datetime
from typing import Optional, List, Union, Dict, Any
from uuid import UUID
from pydantic import Field
from enum import Enum

from app.schemas.base import BaseSchema, BaseResponse


class MessageRoleSchema(str, Enum):
    """Message role enum schema"""
    USER = "user"
    ASSISTANT = "assistant"


class ThreadResponse(BaseResponse):
    """Response schema for thread data"""
    
    agent_id: UUID = Field(
        description="Agent ID associated with this thread"
    )
    user_id: Union[str, UUID] = Field(
        description="User ID who owns this thread"
    )
    organization_id: UUID = Field(
        description="Organization ID this thread belongs to"
    )
    title: Optional[str] = Field(
        None, 
        description="Thread title (auto-generated or user-provided)",
        max_length=500
    )
    thread_metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Thread metadata"
    )
    archived: bool = Field(
        default=False,
        description="Whether the thread is archived"
    )
    messages: List["MessageResponse"] = Field(
        default_factory=list,
        description="Messages in this thread"
    )


class MessageResponse(BaseResponse):
    """Response schema for message data"""
    
    thread_id: Union[str, UUID] = Field(
        description="ID of the thread this message belongs to"
    )
    role: str = Field(
        description="Role of the message sender (user or assistant)"
    )
    content: str = Field(
        description="Message content"
    )
    content_html: Optional[str] = Field(
        None,
        description="HTML content for rich message formatting"
    )
    tool_calls: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Array of tool call objects used by the agent"
    )
    attachments: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Array of attachment references"
    )
    message_metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Message metadata and context"
    )
    response_time_ms: Optional[int] = Field(
        None,
        description="Response time in milliseconds for assistant messages"
    )
    confidence_score: Optional[float] = Field(
        None,
        description="AI confidence score (0-1) for assistant messages"
    )


class CreateThreadRequest(BaseSchema):
    """Request schema for creating a thread"""
    
    title: Optional[str] = Field(
        None,
        description="Optional thread title",
        max_length=500
    )
    thread_metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional thread metadata"
    )


class SendMessageRequest(BaseSchema):
    """Request schema for sending a message"""
    
    content: str = Field(
        min_length=1,
        description="Message content to send"
    )
    role: str = Field(
        default="user",
        description="Message role (user or assistant)"
    )
    attachments: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Optional message attachments"
    )
    message_metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional message metadata"
    )


class UpdateThreadTitleRequest(BaseSchema):
    """Request schema for updating thread title"""
    
    title: str = Field(
        min_length=1,
        max_length=500,
        description="New thread title"
    )


class ArchiveThreadRequest(BaseSchema):
    """Request schema for archiving a thread"""
    
    archived: bool = Field(
        description="Whether to archive or unarchive the thread"
    )


class ArchiveThreadResponse(BaseSchema):
    """Response schema for archive/unarchive operations"""
    
    id: UUID = Field(
        description="Thread ID"
    )
    archived: bool = Field(
        description="Current archive status"
    )
    updated_at: datetime = Field(
        description="Last updated timestamp"
    )
    message: str = Field(
        description="Operation success message"
    )


class UpdateThreadRequest(BaseSchema):
    """Unified request schema for thread updates"""
    
    title: Optional[str] = Field(
        None,
        min_length=1,
        max_length=500,
        description="New thread title"
    )
    archived: Optional[bool] = Field(
        None,
        description="Archive status - true to archive, false to unarchive"
    )
    thread_metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Thread metadata updates"
    )


class ThreadUpdateResponse(BaseResponse):
    """Unified response schema for thread updates"""
    
    agent_id: UUID = Field(
        description="Agent ID associated with this thread"
    )
    user_id: Union[str, UUID] = Field(
        description="Owner user ID"
    )
    organization_id: UUID = Field(
        description="Organization ID"
    )
    title: Optional[str] = Field(
        description="Current thread title"
    )
    archived: bool = Field(
        description="Current archive status"
    )
    updated_fields: List[str] = Field(
        description="List of fields that were updated"
    )


class GenerateTitleResponse(BaseSchema):
    """Response schema for title generation (read-only)"""
    
    id: UUID = Field(
        description="Thread ID"
    )
    title: str = Field(
        description="AI-generated title suggestion"
    )
    current_title: str = Field(
        description="Current thread title"
    )
    generated_at: datetime = Field(
        description="When title was generated"
    )
    confidence: float = Field(
        description="AI confidence score (0-1)",
        ge=0,
        le=1
    )


class ThreadListResponse(BaseSchema):
    """Response schema for thread list"""
    
    threads: List[ThreadResponse] = Field(
        description="List of threads"
    )
    total: int = Field(
        description="Total number of threads"
    )
    page: int = Field(
        description="Current page number"
    )
    page_size: int = Field(
        description="Number of items per page"
    )
    agent_id: UUID = Field(
        description="Agent ID these threads belong to"
    )


class MessageListResponse(BaseSchema):
    """Response schema for message list"""
    
    messages: List[MessageResponse] = Field(
        description="List of messages"
    )
    total: int = Field(
        description="Total number of messages"
    )
    thread_id: Union[str, UUID] = Field(
        description="ID of the thread"
    )


# End of clean agent-centric thread schemas