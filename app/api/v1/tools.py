#!/usr/bin/env python3
"""
Tools API Endpoints

This module provides REST endpoints for MCP tool discovery, enabling the frontend
to dynamically list available tools for agent configuration.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.middleware.auth_middleware import get_current_user
from app.models.user import User
from app.schemas.tools import ToolListResponse
from app.services.mcp_tool_service import mcp_tool_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tools", tags=["Tools"])


@router.get("/", response_model=ToolListResponse)
async def get_available_tools(
    request: Request,
    category: Optional[str] = Query(None, description="Filter by tool category"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get available MCP tools for agent configuration.
    
    This endpoint calls the MCP server's built-in tools/list operation via the existing
    Pydantic AI agent infrastructure to discover available tools with their schemas.
    
    Args:
        request: FastAPI request object
        category: Optional category filter
        current_user: Authenticated user from middleware
        db: Database session
        
    Returns:
        ToolListResponse: List of available tools with metadata
    """
    try:
        logger.info(f"[TOOLS_API] Tool discovery request from user {current_user.email}")
        
        # Get tools from MCP service
        tools = await mcp_tool_service.get_available_tools(
            request=request,
            current_user=current_user,
            db=db,
            category_filter=category
        )
        
        # Get categories and server status
        categories = list(set(tool.category for tool in tools))
        server_status = await mcp_tool_service.get_mcp_server_status(
            request=request,
            current_user=current_user,
            db=db
        )
        
        response = ToolListResponse(
            tools=tools,
            categories=sorted(categories),
            total_count=len(tools),
            mcp_server_status=server_status
        )
        
        logger.info(f"[TOOLS_API] Returning {len(tools)} tools across {len(categories)} categories")
        return response
        
    except Exception as e:
        logger.error(f"[TOOLS_API] Failed to get available tools: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to fetch tools from MCP server: {str(e)}"
        )


@router.get("/categories")
async def get_tool_categories(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get available tool categories.
    
    Args:
        request: FastAPI request object
        current_user: Authenticated user from middleware
        db: Database session
        
    Returns:
        List[str]: Available tool categories
    """
    try:
        logger.info(f"[TOOLS_API] Categories request from user {current_user.email}")
        
        # Get categories from MCP service
        categories = await mcp_tool_service.get_tool_categories(
            request=request,
            current_user=current_user,
            db=db
        )
        
        logger.info(f"[TOOLS_API] Returning {len(categories)} categories")
        return {"categories": categories, "total_count": len(categories)}
        
    except Exception as e:
        logger.error(f"[TOOLS_API] Failed to get tool categories: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch tool categories: {str(e)}"
        )


@router.get("/status")
async def get_mcp_server_status(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get MCP server connection status.
    
    Args:
        request: FastAPI request object
        current_user: Authenticated user from middleware
        db: Database session
        
    Returns:
        Dict: MCP server status information
    """
    try:
        logger.info(f"[TOOLS_API] Status request from user {current_user.email}")
        
        # Get server status
        status = await mcp_tool_service.get_mcp_server_status(
            request=request,
            current_user=current_user,
            db=db
        )
        
        return {
            "mcp_server_status": status,
            "message": f"MCP server is {status}",
            "user": current_user.email
        }
        
    except Exception as e:
        logger.error(f"[TOOLS_API] Failed to get MCP server status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check MCP server status: {str(e)}"
        )