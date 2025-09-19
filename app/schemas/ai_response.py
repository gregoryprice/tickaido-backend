#!/usr/bin/env python3
"""
Shared AI Response Schemas

This module contains shared response models used across AI services
to avoid circular imports and code duplication.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ChatResponse(BaseModel):
    """Structured response from customer support chat agent"""
    content: str = Field(description="Response content to user")
    confidence: float = Field(description="Confidence in response (0-1)", ge=0, le=1)
    requires_escalation: bool = Field(default=False, description="Needs human expert review")
    suggested_actions: List[str] = Field(default_factory=list, description="Suggested follow-up actions")
    ticket_references: List[str] = Field(default_factory=list, description="Referenced ticket IDs")
    tools_used: List[str] = Field(default_factory=list, description="MCP tools that were used")


class ElicitationRequest(BaseModel):
    """Request for additional information from user"""
    message: str = Field(description="Message asking for clarification")
    required_fields: List[str] = Field(description="List of required field names")
    field_descriptions: Dict[str, str] = Field(description="Descriptions of required fields")
    elicitation_type: str = Field(default="missing_parameters", description="Type of elicitation needed")


class AgentHealthStatus(BaseModel):
    """Health status of an AI agent"""
    is_healthy: bool = Field(description="Whether agent is healthy and ready")
    status: str = Field(description="Current agent status")
    mcp_connected: bool = Field(description="Whether MCP client is connected")
    tools_available: int = Field(description="Number of available tools")
    last_used_at: Optional[str] = Field(None, description="When agent was last used (ISO format)")
    error_details: Optional[str] = Field(None, description="Error details if unhealthy")


class TicketCreationResult(BaseModel):
    """Structured output from customer support agent for ticket creation"""
    ticket_title: str = Field(description="Generated ticket title")
    ticket_description: str = Field(description="Detailed ticket description")
    category: str = Field(description="Ticket category")
    priority: str = Field(description="Priority level (low, medium, high, critical)")
    urgency: Optional[str] = Field(None, description="Urgency level (low, medium, high, critical)")
    department: Optional[str] = Field(None, description="Recommended department")
    confidence_score: float = Field(description="Confidence in analysis (0-1)", ge=0, le=1)
    recommended_integration: Optional[str] = Field(None, description="Recommended integration platform")
    file_analysis_summary: str = Field(default="", description="Summary of file analysis if files were processed")
    next_actions: List[str] = Field(default_factory=list, description="Suggested next actions")
    knowledge_base_matches: List[Dict[str, Any]] = Field(default_factory=list, description="Matching knowledge base articles")
    estimated_resolution_time: Optional[str] = Field(None, description="Estimated resolution time")
    tags: List[str] = Field(default_factory=list, description="Relevant tags for the issue")


class AgentContext(BaseModel):
    """Generic context for AI agent operations"""
    user_input: str = Field(description="User's input/request")
    uploaded_files: List[str] = Field(default=[], description="List of uploaded file paths")
    conversation_history: List[Dict[str, Any]] = Field(default=[], description="Previous conversation")
    user_metadata: Dict[str, Any] = Field(default={}, description="User information and context")
    organization_id: Optional[str] = Field(None, description="Organization ID for scoped operations")
    session_id: Optional[str] = Field(None, description="Session identifier")
    integration_preference: Optional[str] = Field(None, description="Preferred integration for routing")


# Backward compatibility alias
CustomerSupportContext = AgentContext