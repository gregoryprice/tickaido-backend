#!/usr/bin/env python3
"""
Tool Schemas for MCP Tool Discovery API
"""

from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ToolParameter(BaseModel):
    """Schema for tool parameter information"""
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True
    )
    
    name: str = Field(..., description="Parameter name")
    type: str = Field(default="string", description="Parameter type (string, int, bool, etc.)")
    required: bool = Field(default=False, description="Whether parameter is required")
    description: Optional[str] = Field(None, description="Parameter description")
    default_value: Optional[Any] = Field(None, description="Default value if any")


class ToolInfo(BaseModel):
    """Schema for tool information"""
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True
    )
    
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    category: str = Field(..., description="Tool category")
    parameters: List[ToolParameter] = Field(default_factory=list, description="Tool parameters")
    requires_auth: bool = Field(default=True, description="Whether tool requires authentication")
    organization_scope: bool = Field(default=True, description="Whether tool is scoped to organization")


class ToolListResponse(BaseModel):
    """Schema for tool list API response"""
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True
    )
    
    tools: List[ToolInfo] = Field(..., description="List of available tools")
    categories: List[str] = Field(..., description="Available tool categories")
    total_count: int = Field(..., description="Total number of tools")
    mcp_server_status: str = Field(default="connected", description="MCP server connection status")