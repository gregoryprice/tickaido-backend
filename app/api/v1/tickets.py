#!/usr/bin/env python3
"""
Ticket API endpoints
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.middleware.auth_middleware import get_current_user
from app.models.user import User
from app.schemas.base import PaginatedResponse, PaginationParams
from app.schemas.comment import CommentCreate, CommentListResponse, CommentResponse, CommentUpdate
from app.schemas.ticket import (
    TicketAICreateRequest,
    TicketAICreateResponse,
    TicketCreateRequest,
    TicketDetailResponse,
    TicketPatchRequest,
    TicketSearchParams,
    TicketSortParams,
    TicketStatsResponse,
    TicketUpdateRequest,
)
from app.services.ai_service import ai_service
from app.services.ticket_service import ticket_service

router = APIRouter(prefix="/tickets")


# Helper function removed - detailed file info should be fetched via GET /api/v1/files/{file_id}


async def create_comment_author_from_user(user: User, db: AsyncSession) -> dict:
    """Create CommentAuthor data from User model with Clerk integration"""
    try:
        # Try to get Clerk user data if available
        if user.clerk_id:
            from app.services.clerk_service import clerk_service
            clerk_user_data = await clerk_service.get_user(user.clerk_id)
            if clerk_user_data:
                return {
                    "id": user.id,
                    "email": user.email,
                    "first_name": clerk_user_data.get("first_name"),
                    "last_name": clerk_user_data.get("last_name"), 
                    "full_name": clerk_user_data.get("full_name") or user.full_name,
                    "image_url": clerk_user_data.get("image_url"),
                    "has_image": bool(clerk_user_data.get("image_url")),
                    "identifier": user.email,
                    "username": None,
                    "profile_image_url": clerk_user_data.get("image_url")
                }
    except Exception as e:
        # If Clerk lookup fails, fall back to local user data
        pass
    
    # Fall back to local user data
    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.full_name.split()[0] if user.full_name and ' ' in user.full_name else user.full_name,
        "last_name": user.full_name.split()[1] if user.full_name and ' ' in user.full_name else None,
        "full_name": user.full_name,
        "image_url": user.avatar_url,
        "has_image": bool(user.avatar_url),
        "identifier": user.email,
        "username": None,
        "profile_image_url": user.avatar_url
    }


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
        # Validate attachments format if provided
        if ticket_data.attachments:
            for attachment in ticket_data.attachments:
                try:
                    # attachment.file_id is already validated as UUID by Pydantic schema
                    pass
                except (ValueError, AttributeError):
                    raise HTTPException(status_code=400, detail="Invalid attachment format")
        
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
            
            # Return response with integration_result from database
            return TicketDetailResponse.model_validate(ticket)
        else:
            # Standard internal-only ticket creation
            # Add organization_id to ticket data
            ticket_data_dict = ticket_data.model_dump()
            ticket_data_dict['organization_id'] = current_user.organization_id
            ticket = await ticket_service.create_ticket(
                db=db,
                ticket_data=ticket_data_dict,
                created_by_id=current_user.id,
                organization_id=current_user.organization_id
            )
            
            response = TicketDetailResponse.model_validate(ticket)
            return response
        
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
        
        response = TicketDetailResponse.model_validate(ticket)
        return response
        
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
        # Don't exclude None values for nullable fields like assigned_to_id
        update_dict = update_data.model_dump()
        
        ticket = await ticket_service.update_ticket(
            db=db,
            ticket_id=ticket_id,
            organization_id=current_user.organization_id,
            update_data=update_dict
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
        # Special handling for attachments - empty array should be preserved
        update_data = patch_data.model_dump(exclude_unset=True, exclude_none=True)
        
        # Re-add attachments if it was explicitly set (even if empty)
        raw_data = patch_data.model_dump(exclude_unset=True)
        if 'attachments' in raw_data and 'attachments' not in update_data:
            update_data['attachments'] = raw_data['attachments']
        
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


@router.post("/{ticket_id}/attachments")
async def add_files_to_ticket(
    ticket_id: UUID,
    file_ids: dict,  # {"file_ids": ["uuid1", "uuid2"]}
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Add files to a ticket via file_ids array.
    """
    try:
        from app.services.ticket_attachment_service import TicketAttachmentService
        
        attachment_service = TicketAttachmentService()
        file_ids_list = [UUID(fid) for fid in file_ids.get("file_ids", [])]
        
        updated_ticket = await attachment_service.add_files_to_ticket(
            db=db,
            ticket_id=ticket_id,
            new_file_ids=file_ids_list,
            user=current_user
        )
        
        return {
            "message": "Files added to ticket successfully",
            "ticket_id": str(updated_ticket.id),
            "file_ids": updated_ticket.file_ids
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add files to ticket: {str(e)}"
        )


@router.get("/{ticket_id}/attachments")
async def get_ticket_attachments(
    ticket_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get all attachments associated with a ticket.
    """
    try:
        from app.services.ticket_attachment_service import TicketAttachmentService
        
        attachment_service = TicketAttachmentService()
        files = await attachment_service.get_ticket_files(db, ticket_id)
        
        # Convert to response format
        file_responses = []
        for file_obj in files:
            file_responses.append({
                "id": str(file_obj.id),
                "filename": file_obj.filename,
                "file_size": file_obj.file_size,
                "mime_type": file_obj.mime_type,
                "file_type": file_obj.file_type.value,
                "status": file_obj.status.value,
                "content_summary": file_obj.content_summary,
                "extraction_method": file_obj.extraction_method,
                "created_at": file_obj.created_at,
                "updated_at": file_obj.updated_at
            })
        
        return file_responses
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get ticket files: {str(e)}"
        )


# Comment Management Endpoints for Enhanced Jira Integration

@router.post("/{ticket_id}/comments")
async def create_comment(
    ticket_id: UUID,
    comment: "CommentCreate",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> "CommentResponse":
    """
    Create a new comment on a ticket.
    Supports both plain text and ADF (Atlassian Document Format) content.
    """
    try:
        from app.services.comment_service import comment_service
        
        # Get the ticket to inherit its integration_id
        ticket = await ticket_service.get_ticket(
            db=db,
            ticket_id=ticket_id,
            organization_id=current_user.organization_id
        )
        
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found"
            )
        
        # Create comment with current user as author and inherit ticket's integration_id
        new_comment = await comment_service.create_comment(
            db=db,
            ticket_id=ticket_id,
            author_email=current_user.email,
            author_display_name=current_user.full_name or current_user.email,
            body=comment.body,
            is_internal=comment.is_internal,
            integration_id=ticket.integration_id,  # Always inherit from ticket
            user=current_user
        )
        
        # Convert to response format
        from app.schemas.comment import CommentResponse, CommentAuthor
        author_data = await create_comment_author_from_user(current_user, db)
        return CommentResponse(
            id=new_comment.id,
            ticket_id=new_comment.ticket_id,
            author=CommentAuthor(**author_data),
            body=new_comment.body,
            body_html=new_comment.render_html(),
            body_plain_text=new_comment.body_plain_text,
            created_at=new_comment.created_at,
            updated_at=new_comment.updated_at,
            external_comment_id=new_comment.external_comment_id,
            integration_id=new_comment.integration_id,
            is_internal=new_comment.is_internal,
            is_synchronized=new_comment.is_synchronized
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create comment: {str(e)}"
        )


@router.get("/{ticket_id}/comments")
async def list_comments(
    ticket_id: UUID,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=50, description="Items per page"),
    include_internal: bool = Query(False, description="Include internal comments"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> "CommentListResponse":
    """
    List comments for a ticket with pagination.
    Internal comments are only visible to authorized users.
    """
    try:
        from app.services.comment_service import comment_service
        
        comments, total = await comment_service.list_comments(
            db=db,
            ticket_id=ticket_id,
            page=page,
            per_page=per_page,
            include_internal=include_internal,
            user=current_user
        )
        
        # Convert to response format
        from app.schemas.comment import CommentListResponse, CommentResponse, CommentAuthor
        from sqlalchemy import select
        comment_responses = []
        
        # Get unique author emails and fetch user data
        author_emails = list(set(comment.author_email for comment in comments))
        users_by_email = {}
        
        # Fetch user data for all authors in batch
        if author_emails:
            user_stmt = select(User).where(User.email.in_(author_emails))
            user_result = await db.execute(user_stmt)
            for user in user_result.scalars().all():
                users_by_email[user.email] = user
        
        for comment in comments:
            # Get author data
            comment_user = users_by_email.get(comment.author_email)
            if comment_user:
                author_data = await create_comment_author_from_user(comment_user, db)
            else:
                # Fallback for comments by users not found in database
                author_data = {
                    "id": None,  # Will need to handle this case
                    "email": comment.author_email,
                    "first_name": comment.author_display_name.split()[0] if comment.author_display_name and ' ' in comment.author_display_name else comment.author_display_name,
                    "last_name": comment.author_display_name.split()[1] if comment.author_display_name and ' ' in comment.author_display_name else None,
                    "full_name": comment.author_display_name,
                    "image_url": None,
                    "has_image": False,
                    "identifier": comment.author_email,
                    "username": None,
                    "profile_image_url": None
                }
            
            comment_responses.append(CommentResponse(
                id=comment.id,
                ticket_id=comment.ticket_id,
                author=CommentAuthor(**author_data),
                body=comment.body,
                body_html=comment.render_html(),
                body_plain_text=comment.body_plain_text,
                created_at=comment.created_at,
                updated_at=comment.updated_at,
                external_comment_id=comment.external_comment_id,
                integration_id=comment.integration_id,
                is_internal=comment.is_internal,
                is_synchronized=comment.is_synchronized
            ))
        
        return CommentListResponse(
            comments=comment_responses,
            total=total,
            page=page,
            per_page=per_page,
            has_next=(page * per_page) < total,
            has_prev=page > 1
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list comments: {str(e)}"
        )


@router.put("/{ticket_id}/comments/{comment_id}")
async def update_comment(
    ticket_id: UUID,
    comment_id: UUID,
    comment_update: "CommentUpdate",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> "CommentResponse":
    """
    Update an existing comment.
    Users can only update their own comments unless they have admin privileges.
    """
    try:
        from app.services.comment_service import comment_service
        
        updated_comment = await comment_service.update_comment(
            db=db,
            comment_id=comment_id,
            body=comment_update.body,
            is_internal=comment_update.is_internal,
            user=current_user
        )
        
        # Convert to response format
        from app.schemas.comment import CommentResponse, CommentAuthor
        from sqlalchemy import select
        
        # Get user data for the comment author
        user_stmt = select(User).where(User.email == updated_comment.author_email)
        user_result = await db.execute(user_stmt)
        comment_user = user_result.scalar_one_or_none()
        
        if comment_user:
            author_data = await create_comment_author_from_user(comment_user, db)
        else:
            # Fallback for comments by users not found in database
            author_data = {
                "id": None,
                "email": updated_comment.author_email,
                "first_name": updated_comment.author_display_name.split()[0] if updated_comment.author_display_name and ' ' in updated_comment.author_display_name else updated_comment.author_display_name,
                "last_name": updated_comment.author_display_name.split()[1] if updated_comment.author_display_name and ' ' in updated_comment.author_display_name else None,
                "full_name": updated_comment.author_display_name,
                "image_url": None,
                "has_image": False,
                "identifier": updated_comment.author_email,
                "username": None,
                "profile_image_url": None
            }
        
        return CommentResponse(
            id=updated_comment.id,
            ticket_id=updated_comment.ticket_id,
            author=CommentAuthor(**author_data),
            body=updated_comment.body,
            body_html=updated_comment.render_html(),
            body_plain_text=updated_comment.body_plain_text,
            created_at=updated_comment.created_at,
            updated_at=updated_comment.updated_at,
            external_comment_id=updated_comment.external_comment_id,
            integration_id=updated_comment.integration_id,
            is_internal=updated_comment.is_internal,
            is_synchronized=updated_comment.is_synchronized
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update comment: {str(e)}"
        )


@router.delete("/{ticket_id}/comments/{comment_id}")
async def delete_comment(
    ticket_id: UUID,
    comment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> dict:
    """
    Delete a comment.
    Users can only delete their own comments unless they have admin privileges.
    """
    try:
        from app.services.comment_service import comment_service
        
        await comment_service.delete_comment(
            db=db,
            comment_id=comment_id,
            user=current_user
        )
        
        return {
            "message": "Comment deleted successfully",
            "comment_id": str(comment_id)
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete comment: {str(e)}"
        )