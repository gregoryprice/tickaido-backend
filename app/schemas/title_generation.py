#!/usr/bin/env python3
"""
Title Generation Schemas

Pydantic models for title generation functionality.
Moved from standalone agent to shared location for better architecture.
"""

from pydantic import BaseModel, Field


class TitleGenerationResult(BaseModel):
    """Structured output from title generation operations"""
    title: str = Field(description="Generated title", max_length=500)
    confidence: float = Field(description="Confidence score (0-1)", ge=0, le=1)


class TitleGenerationRequest(BaseModel):
    """Request schema for title generation"""
    current_title: str | None = Field(None, description="Current conversation title")
    message_limit: int = Field(default=6, ge=1, le=20, description="Maximum messages to analyze")


class TitleGenerationResponse(BaseModel):
    """Response schema for title generation API"""
    id: str = Field(description="Thread or conversation ID")
    title: str = Field(description="Generated title")
    current_title: str | None = Field(description="Previous title")
    confidence: float = Field(description="Confidence score (0-1)", ge=0, le=1)
    generated_at: str = Field(description="ISO timestamp of generation")
    messages_analyzed: int = Field(description="Number of messages analyzed")
    system_agent_used: bool = Field(description="Whether system title agent was used")