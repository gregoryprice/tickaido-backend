#!/usr/bin/env python3
"""
Ticket API endpoints
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.schemas.ticket import (
    TicketCreateRequest,
    TicketUpdateRequest,
    TicketDetailResponse,
    TicketListResponse,
    TicketSearchParams,
    TicketSortParams,
    TicketStatusUpdateRequest,
    TicketAssignmentRequest,
    TicketAICreateRequest,
    TicketAICreateResponse,
    TicketStatsResponse
)
from app.schemas.base import PaginationParams, PaginatedResponse
from app.models.ticket import DBTicket
from app.models.user import DBUser
from app.services.ticket_service import ticket_service
from app.services.ai_service import ai_service

router = APIRouter(prefix="/tickets")


@router.get("/", response_model=PaginatedResponse)
async def list_tickets(
    pagination: PaginationParams = Depends(),
    search_params: TicketSearchParams = Depends(),
    sort_params: TicketSortParams = Depends(),
    db: AsyncSession = Depends(get_db_session)
):
    """
    List tickets with search, filtering, and pagination.
    """
    try:
        # Convert search params to filters dict
        filters = {}
        if search_params.q:
            filters['search'] = search_params.q
        if search_params.status:
            filters['status'] = [s.value for s in search_params.status]
        if search_params.category:
            filters['category'] = [c.value for c in search_params.category]
        if search_params.priority:
            filters['priority'] = [p.value for p in search_params.priority]
        if search_params.department:
            filters['department'] = search_params.department
        if search_params.created_by_id:
            filters['created_by_id'] = search_params.created_by_id
        if search_params.assigned_to_id:
            filters['assigned_to_id'] = search_params.assigned_to_id
        if search_params.is_overdue is not None:
            filters['is_overdue'] = search_params.is_overdue
        
        # Add date filters
        if search_params.created_after:
            filters['created_after'] = search_params.created_after
        if search_params.created_before:
            filters['created_before'] = search_params.created_before
        
        tickets, total = await ticket_service.list_tickets(
            db=db,
            offset=pagination.offset,
            limit=pagination.size,
            filters=filters,
            sort_by=sort_params.sort_by,
            sort_order=sort_params.sort_order
        )
        
        return PaginatedResponse.create(
            items=[TicketListResponse.model_validate(ticket) for ticket in tickets],
            total=total,
            page=pagination.page,
            size=pagination.size
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tickets: {str(e)}"
        )


@router.post("/", response_model=TicketDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    ticket_data: TicketCreateRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Create a new support ticket.
    """
    try:
        ticket = await ticket_service.create_ticket(
            db=db,
            ticket_data=ticket_data.model_dump()
        )
        
        return TicketDetailResponse.model_validate(ticket)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create ticket: {str(e)}"
        )


@router.post("/ai-create", response_model=TicketAICreateResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket_with_ai(
    ai_request: TicketAICreateRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Create a support ticket using AI analysis of user input.
    """
    try:
        result = await ai_service.create_ticket_with_ai(
            db=db,
            user_input=ai_request.user_input,
            uploaded_files=ai_request.uploaded_files or [],
            conversation_context=ai_request.conversation_context or [],
            user_preferences=ai_request.user_preferences or {},
            integration_preference=ai_request.integration_preference
        )
        
        return TicketAICreateResponse.model_validate(result)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create ticket with AI: {str(e)}"
        )


@router.get("/{ticket_id}", response_model=TicketDetailResponse)
async def get_ticket(
    ticket_id: UUID,
    include_ai_data: bool = Query(True, description="Include AI analysis data"),
    include_internal: bool = Query(False, description="Include internal notes"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get a specific ticket by ID.
    """
    try:
        ticket = await ticket_service.get_ticket(
            db=db,
            ticket_id=ticket_id,
            include_ai_data=include_ai_data,
            include_internal=include_internal
        )
        
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found"
            )
        
        return TicketDetailResponse.model_validate(ticket)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get ticket: {str(e)}"
        )


@router.put("/{ticket_id}", response_model=TicketDetailResponse)
async def update_ticket(
    ticket_id: UUID,
    update_data: TicketUpdateRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Update a ticket.
    """
    try:
        ticket = await ticket_service.update_ticket(
            db=db,
            ticket_id=ticket_id,
            update_data=update_data.model_dump(exclude_none=True)
        )
        
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found"
            )
        
        return TicketDetailResponse.model_validate(ticket)
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update ticket: {str(e)}"
        )


@router.patch("/{ticket_id}/status", response_model=TicketDetailResponse)
async def update_ticket_status(
    ticket_id: UUID,
    status_update: TicketStatusUpdateRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Update ticket status.
    """
    try:
        ticket = await ticket_service.update_ticket_status(
            db=db,
            ticket_id=ticket_id,
            new_status=status_update.status.value,
            resolution_summary=status_update.resolution_summary,
            internal_notes=status_update.internal_notes
        )
        
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found"
            )
        
        return TicketDetailResponse.model_validate(ticket)
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update ticket status: {str(e)}"
        )


@router.patch("/{ticket_id}/assign", response_model=TicketDetailResponse)
async def assign_ticket(
    ticket_id: UUID,
    assignment: TicketAssignmentRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Assign or unassign a ticket.
    """
    try:
        ticket = await ticket_service.assign_ticket(
            db=db,
            ticket_id=ticket_id,
            assigned_to_id=assignment.assigned_to_id,
            reason=assignment.reason
        )
        
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found"
            )
        
        return TicketDetailResponse.model_validate(ticket)
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign ticket: {str(e)}"
        )


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ticket(
    ticket_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Soft delete a ticket.
    """
    try:
        success = await ticket_service.delete_ticket(db=db, ticket_id=ticket_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete ticket: {str(e)}"
        )


@router.get("/stats/overview", response_model=TicketStatsResponse)
async def get_ticket_stats(
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get ticket statistics overview.
    """
    try:
        stats = await ticket_service.get_ticket_stats(db=db)
        return TicketStatsResponse.model_validate(stats)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get ticket stats: {str(e)}"
        )