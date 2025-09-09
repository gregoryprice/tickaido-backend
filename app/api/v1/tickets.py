#!/usr/bin/env python3
"""
Ticket API endpoints
"""

from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.schemas.ticket import (
    TicketCreateRequest,
    TicketUpdateRequest,
    TicketPatchRequest,
    TicketDetailResponse,
    TicketSearchParams,
    TicketSortParams,
    TicketAICreateRequest,
    TicketAICreateResponse,
    TicketStatsResponse
)
from app.schemas.base import PaginationParams, PaginatedResponse
from app.services.ticket_service import ticket_service
from app.services.ai_service import ai_service
from app.middleware.auth_middleware import get_current_user
from app.models.user import User

router = APIRouter(prefix="/tickets")


@router.get("/", response_model=PaginatedResponse)
async def list_tickets(
    pagination: PaginationParams = Depends(),
    search_params: TicketSearchParams = Depends(),
    sort_params: TicketSortParams = Depends(),
    current_user: User = Depends(get_current_user),
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
            organization_id=current_user.organization_id,
            offset=pagination.offset,
            limit=pagination.size,
            filters=filters,
            sort_by=sort_params.sort_by,
            sort_order=sort_params.sort_order
        )
        
        # Convert Ticket models to TicketDetailResponse
        ticket_responses = []
        for ticket in tickets:
            ticket_response = TicketDetailResponse.model_validate(ticket)
            ticket_responses.append(ticket_response)
        
        return PaginatedResponse.create(
            items=ticket_responses,
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Create a new support ticket.
    """
    try:
        # Check if integration is specified for external creation
        if ticket_data.integration_id and ticket_data.create_externally:
            # Add organization_id to ticket data
            ticket_data_dict = ticket_data.model_dump()
            ticket_data_dict['organization_id'] = current_user.organization_id
            ticket, integration_result = await ticket_service.create_ticket_with_integration(
                db=db,
                ticket_data=ticket_data_dict,
                created_by_id=current_user.id
            )
            
            # Include integration result in response
            response_data = TicketDetailResponse.model_validate(ticket)
            response_data.integration_result = integration_result
            return response_data
        else:
            # Standard internal-only ticket creation
            # Add organization_id to ticket data
            ticket_data_dict = ticket_data.model_dump()
            ticket_data_dict['organization_id'] = current_user.organization_id
            ticket = await ticket_service.create_ticket(
                db=db,
                ticket_data=ticket_data_dict,
                created_by_id=current_user.id
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Create a support ticket using AI analysis of user input.
    """
    try:
        result = await ai_service.create_ticket_with_ai(
            db=db,
            current_user=current_user,
            user_input=ai_request.user_input,
            uploaded_files=ai_request.uploaded_files or [],
            conversation_context=ai_request.conversation_context or [],
            user_preferences=ai_request.user_preferences or {},
            integration_preference=ai_request.integration_id
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get a specific ticket by ID.
    """
    try:
        ticket = await ticket_service.get_ticket(
            db=db,
            ticket_id=ticket_id,
            organization_id=current_user.organization_id,
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Update a ticket.
    """
    try:
        ticket = await ticket_service.update_ticket(
            db=db,
            ticket_id=ticket_id,
            organization_id=current_user.organization_id,
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


@router.patch("/{ticket_id}", response_model=TicketDetailResponse)
async def patch_ticket(
    ticket_id: UUID,
    patch_data: TicketPatchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Update specific fields of a ticket with flexible partial updates.
    
    Supports updating any combination of ticket fields:
    - Status: {"status": "in_progress"}
    - Assignment: {"assigned_to_id": "uuid", "assignment_reason": "reason"}
    - Priority: {"priority": "high"}
    - Multiple fields: {"status": "resolved", "priority": "low", "tags": ["fixed"]}
    """
    try:
        # Get only the fields that were actually provided (exclude None values)
        update_data = patch_data.model_dump(exclude_unset=True, exclude_none=True)
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one field must be provided for update"
            )
        
        # Update ticket with organization context
        updated_ticket = await ticket_service.patch_ticket(
            db=db,
            ticket_id=ticket_id,
            organization_id=current_user.organization_id,
            update_data=update_data,
            updated_by_user=current_user
        )
        
        if not updated_ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found or not accessible"
            )
        
        return TicketDetailResponse.model_validate(updated_ticket)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update ticket: {str(e)}"
        )





@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ticket(
    ticket_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Soft delete a ticket.
    """
    try:
        success = await ticket_service.delete_ticket(db=db, ticket_id=ticket_id, organization_id=current_user.organization_id)
        
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get ticket statistics overview.
    """
    try:
        stats = await ticket_service.get_ticket_stats(db=db, organization_id=current_user.organization_id)
        return TicketStatsResponse.model_validate(stats)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get ticket stats: {str(e)}"
        )