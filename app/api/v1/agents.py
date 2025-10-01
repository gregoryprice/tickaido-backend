#!/usr/bin/env python3
"""
Simplified Agent Management API - 6 CRUD + History Endpoints
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.middleware.auth_middleware import get_current_user
from app.models.user import User
from app.schemas.agent import (
    AgentCreateRequest,
    AgentHistoryListResponse,
    AgentHistoryResponse,
    AgentListResponse,
    AgentResponse,
    AgentUpdateRequest,
    SuccessResponse,
)
from app.services.agent_history_service import agent_history_service
from app.services.agent_service import agent_service

router = APIRouter(prefix="/agents", tags=["Agent Management"])
logger = logging.getLogger(__name__)


def get_client_ip(request: Request) -> Optional[str]:
    """Get client IP address from request"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


@router.post("/", response_model=AgentResponse, status_code=201)
async def create_agent(
    agent_data: AgentCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new agent for the organization"""
    
    try:
        logger.info(f"Creating agent '{agent_data.name}' for organization {current_user.organization_id}")
        
        # Create agent
        agent = await agent_service.create_agent(
            organization_id=current_user.organization_id,
            name=agent_data.name,
            agent_type=agent_data.agent_type,
            avatar_url=None,  # Always null on creation, use avatar endpoints for avatar management
            configuration=agent_data.model_dump(exclude={'name', 'agent_type'}),
            created_by_user_id=current_user.id,
            reason="Agent creation via API",
            ip_address=get_client_ip(request),
            db=db
        )
        
        if not agent:
            raise HTTPException(status_code=500, detail="Failed to create agent")
        
        logger.info(f"✅ Created agent {agent.id} for organization {current_user.organization_id}")
        return AgentResponse.model_validate(agent)
        
    except Exception as e:
        logger.error(f"Error creating agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID = Path(..., description="Agent ID"),
    agent_data: AgentUpdateRequest = ...,
    request: Request = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Update an agent"""
    
    try:
        # Verify agent exists and belongs to organization
        agent = await agent_service.get_agent(agent_id, db=db)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        if agent.organization_id != current_user.organization_id:
            raise HTTPException(status_code=403, detail="Access denied to agent")
        
        # Prepare updates (exclude None values and avatar_url)
        updates = {k: v for k, v in agent_data.model_dump().items() if v is not None}
        
        # Filter out avatar_url if somehow provided - handled by dedicated avatar endpoints
        updates.pop('avatar_url', None)
        
        if not updates:
            # No updates provided, return current agent
            return AgentResponse.model_validate(agent)
        
        # Update agent
        updated_agent = await agent_service.update_agent(
            agent_id=agent_id,
            updates=updates,
            updated_by_user_id=current_user.id,
            reason=f"Agent update via API: {', '.join(updates.keys())}",
            ip_address=get_client_ip(request),
            db=db
        )
        
        if not updated_agent:
            raise HTTPException(status_code=500, detail="Failed to update agent")
        
        logger.info(f"✅ Updated agent {agent_id} with {len(updates)} changes")
        return AgentResponse.model_validate(updated_agent)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{agent_id}", response_model=SuccessResponse)
async def delete_agent(
    agent_id: UUID = Path(..., description="Agent ID"),
    request: Request = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Delete an agent (soft delete)"""
    
    try:
        # Verify agent exists and belongs to organization
        agent = await agent_service.get_agent(agent_id, db=db)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        if agent.organization_id != current_user.organization_id:
            raise HTTPException(status_code=403, detail="Access denied to agent")
        
        # Delete agent
        success = await agent_service.delete_agent(
            agent_id=agent_id,
            deleted_by_user_id=current_user.id,
            reason="Agent deletion via API",
            ip_address=get_client_ip(request),
            db=db
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete agent")
        
        logger.info(f"✅ Deleted agent {agent_id}")
        return SuccessResponse(
            message="Agent deleted successfully",
            data={"agent_id": str(agent_id)}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID = Path(..., description="Agent ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get a single agent by ID"""
    
    try:
        # Get agent
        agent = await agent_service.get_agent(agent_id, db=db)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Verify organization access
        if agent.organization_id != current_user.organization_id:
            raise HTTPException(status_code=403, detail="Access denied to agent")
        
        logger.debug(f"Retrieved agent {agent_id}")
        return AgentResponse.model_validate(agent)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=AgentListResponse)
async def list_agents(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    agent_type: Optional[str] = Query(None, description="Filter by agent type"),
    include_inactive: bool = Query(False, description="Include inactive agents"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """List agents for the organization with pagination and filtering"""
    
    try:
        # Get organization agents
        agents = await agent_service.get_organization_agents(
            organization_id=current_user.organization_id,
            agent_type=agent_type,
            include_inactive=include_inactive,
            db=db
        )
        
        # Apply pagination
        offset = (page - 1) * limit
        paginated_agents = agents[offset:offset + limit]
        
        # Convert to response models
        agent_responses = [AgentResponse.model_validate(agent) for agent in paginated_agents]
        
        logger.debug(f"Retrieved {len(paginated_agents)} agents for organization {current_user.organization_id}")
        return AgentListResponse(
            agents=agent_responses,
            total=len(agents),
            page=page,
            limit=limit
        )
        
    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{agent_id}/history", response_model=AgentHistoryListResponse)
async def get_agent_history(
    agent_id: UUID = Path(..., description="Agent ID"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    change_type: Optional[str] = Query(None, description="Filter by change type"),
    field_filter: Optional[str] = Query(None, description="Filter by field name"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get change history for an agent"""
    
    try:
        # Verify agent exists and belongs to organization
        agent = await agent_service.get_agent(agent_id, db=db)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        if agent.organization_id != current_user.organization_id:
            raise HTTPException(status_code=403, detail="Access denied to agent")
        
        # Get history with pagination
        offset = (page - 1) * limit
        history_records = await agent_history_service.get_agent_history(
            agent_id=agent_id,
            limit=limit,
            offset=offset,
            change_type=change_type,
            field_filter=field_filter,
            db=db
        )
        
        # Convert to response models
        history_responses = []
        for record in history_records:
            history_response = AgentHistoryResponse.model_validate(record)
            
            # Add user name if available
            if record.changed_by:
                history_response.changed_by_name = record.changed_by.full_name
            
            history_responses.append(history_response)
        
        logger.debug(f"Retrieved {len(history_responses)} history records for agent {agent_id}")
        return AgentHistoryListResponse(
            history=history_responses,
            total=len(history_responses),  # Would need count query for exact total
            page=page,
            limit=limit
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent history: {e}")
        raise HTTPException(status_code=500, detail=str(e))