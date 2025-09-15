#!/usr/bin/env python3
"""
Agent-Centric Chat API endpoints for thread management
"""

import logging
from typing import Optional
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.schemas.chat import (
    ThreadResponse, CreateThreadRequest, MessageResponse, SendMessageRequest, 
    GenerateTitleResponse, UpdateThreadRequest, ThreadUpdateResponse,
    ThreadListResponse, MessageListResponse
)
from app.models.user import User
from app.models.chat import Message
from app.services.thread_service import thread_service
from app.services.ai_chat_service import ai_chat_service
from app.middleware.auth_middleware import get_current_user
from app.services.auth_provider import decode_jwt_token

router = APIRouter(prefix="/chat", tags=["Agent-Centric Chat"])
logger = logging.getLogger(__name__)


@router.get("/{agent_id}/threads", response_model=ThreadListResponse)
async def list_threads(
    agent_id: UUID = Path(..., description="Agent ID"),
    archived: bool = Query(False, description="Filter by archive status"),
    q: Optional[str] = Query(None, description="Search threads by title and content"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """List user's chat threads for a specific agent with optional filtering and search"""
    
    logger.info(f"[CHAT_API] Listing threads for agent {agent_id}, user: {current_user.id}")
    
    try:
        # Calculate offset from page number
        offset = (page - 1) * page_size
        
        # Get threads for the agent and user
        user_id = str(current_user.id)
        threads, total = await thread_service.list_threads(
            db=db,
            agent_id=agent_id,
            user_id=user_id,
            offset=offset,
            limit=page_size,
            archived=archived,
            query=q
        )
        
        logger.debug(f"[CHAT_API] Found {len(threads)} threads for agent {agent_id}")
        
        # Convert to response format
        thread_responses = [ThreadResponse.model_validate(thread.__dict__) for thread in threads]
        
        return ThreadListResponse(
            threads=thread_responses,
            total=total,
            page=page,
            page_size=page_size,
            agent_id=agent_id
        )
        
    except Exception as e:
        logger.error(f"[CHAT_API] Error listing threads for agent {agent_id}: {e}")
        if "not found" in str(e).lower() or "not active" in str(e).lower():
            raise HTTPException(status_code=404, detail="Agent not found or not accessible")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{agent_id}/threads", response_model=ThreadResponse)
async def create_thread(
    agent_id: UUID = Path(..., description="Agent ID"),
    request: CreateThreadRequest = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new chat thread for a specific agent"""
    
    logger.info(f"[CHAT_API] Creating thread for agent {agent_id}, user: {current_user.id}")
    
    try:
        # Create thread for the agent and user
        user_id = str(current_user.id)
        thread = await thread_service.create_thread(
            db=db,
            agent_id=agent_id,
            user_id=user_id,
            title=request.title if request else None
        )
        
        logger.info(f"[CHAT_API] Created thread {thread.id} for agent {agent_id}")
        
        # Convert to response format
        return ThreadResponse.model_validate(thread.__dict__)
        
    except ValueError as e:
        logger.warning(f"[CHAT_API] Validation error creating thread: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[CHAT_API] Error creating thread for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to create thread")


@router.get("/{agent_id}/threads/{thread_id}", response_model=ThreadResponse)
async def get_thread(
    agent_id: UUID = Path(..., description="Agent ID"),
    thread_id: UUID = Path(..., description="Thread ID"),
    include_messages: bool = Query(True, description="Include messages in response"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get a specific thread with its messages"""
    
    logger.info(f"[CHAT_API] Getting thread {thread_id} for agent {agent_id}, user: {current_user.id}")
    
    try:
        # Get thread with validation
        user_id = str(current_user.id)
        thread = await thread_service.get_thread(
            db=db,
            agent_id=agent_id,
            thread_id=thread_id,
            user_id=user_id
        )
        
        if not thread:
            logger.warning(f"[CHAT_API] Thread {thread_id} not found for agent {agent_id}")
            raise HTTPException(status_code=404, detail="Thread not found")
        
        # Get messages if requested
        messages = []
        if include_messages:
            message_list = await thread_service.get_thread_messages(
                db=db,
                agent_id=agent_id,
                thread_id=thread_id,
                user_id=user_id
            )
            messages = [MessageResponse.model_validate(msg.__dict__) for msg in message_list]
        
        # Build response
        response_data = thread.__dict__.copy()
        response_data['messages'] = messages
        
        return ThreadResponse.model_validate(response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CHAT_API] Error getting thread {thread_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{agent_id}/threads/{thread_id}/messages", response_model=MessageResponse)
async def send_message(
    request: SendMessageRequest,
    http_request: Request,
    agent_id: UUID = Path(..., description="Agent ID"),
    thread_id: UUID = Path(..., description="Thread ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Send a message to a thread and get AI response"""
    
    logger.info(f"[CHAT_API] Sending message to thread {thread_id}, agent {agent_id}, user: {current_user.id}")
    logger.debug(f"[CHAT_API] Message content: {request.content[:100]}{'...' if len(request.content) > 100 else ''}")
    
    # Extract JWT token for MCP authentication
    auth_header = http_request.headers.get("authorization", "")
    jwt_token = None
    
    if auth_header.startswith("Bearer "):
        jwt_token = auth_header[7:]
        try:
            payload = decode_jwt_token(jwt_token)
            logger.debug("[CHAT_API] Extracted JWT token for MCP authentication")
        except Exception as e:
            logger.warning(f"[CHAT_API] Failed to decode JWT token: {e}")
            jwt_token = None
    
    try:
        # Verify thread exists and user has access
        user_id = str(current_user.id)
        thread = await thread_service.get_thread(
            db=db,
            agent_id=agent_id,
            thread_id=thread_id,
            user_id=user_id
        )
        
        if not thread:
            logger.warning(f"[CHAT_API] Thread {thread_id} not found for agent {agent_id}")
            raise HTTPException(status_code=404, detail="Thread not found")
        
        logger.debug("[CHAT_API] Thread validated, calling AI service with agent context")
        
        # Use AI chat service with agent-centric processing
        ai_response = await ai_chat_service.send_message_to_thread(
            agent_id=str(agent_id),
            thread_id=str(thread_id),
            user_id=user_id,
            message=request.content,
            attachments=request.attachments,
            auth_token=jwt_token
        )
        
        logger.info(f"[CHAT_API] AI response generated with confidence: {getattr(ai_response, 'confidence', 0.0)}")
        
        # Get the most recent messages from the thread (we need a custom query for this)
        from sqlalchemy import select, desc
        query = select(Message).where(
            Message.thread_id == thread_id
        ).order_by(desc(Message.created_at)).limit(10)
        
        result = await db.execute(query)
        recent_messages = result.scalars().all()
        
        # Find the most recent assistant message (messages are now in reverse chronological order)
        assistant_message = None
        for msg in recent_messages:
            if msg.role == "assistant":
                assistant_message = msg
                break
        
        if assistant_message:
            logger.info(f"[CHAT_API] Found stored assistant message with ID: {assistant_message.id}")
            return MessageResponse.model_validate(assistant_message.__dict__)
        else:
            # Create response from AI service output
            logger.warning("[CHAT_API] Could not find stored assistant message, creating response from AI output")
            return MessageResponse(
                id=UUID("00000000-0000-0000-0000-000000000000"),  # Placeholder
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                thread_id=thread_id,
                role="assistant",
                content=ai_response.content,
                content_html=None,
                tool_calls=getattr(ai_response, 'tools_used', []),
                attachments=[],
                message_metadata={},
                response_time_ms=None,
                confidence_score=getattr(ai_response, 'confidence', None)
            )
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"[CHAT_API] ValueError in send_message: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"[CHAT_API] Error in send_message endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.patch("/{agent_id}/threads/{thread_id}", response_model=ThreadUpdateResponse)
async def update_thread(
    request: UpdateThreadRequest,
    agent_id: UUID = Path(..., description="Agent ID"),
    thread_id: UUID = Path(..., description="Thread ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Update thread fields (title, archive status, metadata)"""
    
    logger.info(f"[CHAT_API] Updating thread {thread_id} for agent {agent_id}, user: {current_user.id}")
    
    # Validate request has at least one field
    if request.title is None and request.archived is None:
        logger.warning(f"[CHAT_API] Empty request body for thread {thread_id}")
        raise HTTPException(status_code=400, detail="At least one field must be provided")
    
    try:
        # Update thread with ownership validation
        user_id = str(current_user.id)
        result = await thread_service.update_thread(
            db=db,
            agent_id=agent_id,
            thread_id=thread_id,
            user_id=user_id,
            title=request.title,
            archived=request.archived
        )
        
        if not result:
            logger.warning(f"[CHAT_API] Thread {thread_id} not found for agent {agent_id}")
            raise HTTPException(status_code=404, detail="Thread not found")
        
        thread, updated_fields = result
        
        logger.info(f"[CHAT_API] Thread {thread_id} updated successfully, fields: {updated_fields}")
        
        # Convert to response format
        response_data = thread.__dict__.copy()
        response_data['updated_fields'] = updated_fields
        
        return ThreadUpdateResponse.model_validate(response_data)
        
    except ValueError as e:
        logger.warning(f"[CHAT_API] Validation error updating thread {thread_id}: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"[CHAT_API] Error updating thread {thread_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{agent_id}/threads/{thread_id}")
async def delete_thread(
    agent_id: UUID = Path(..., description="Agent ID"),
    thread_id: UUID = Path(..., description="Thread ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Delete a thread (soft delete by archiving)"""
    
    logger.info(f"[CHAT_API] Deleting thread {thread_id} for agent {agent_id}, user: {current_user.id}")
    
    try:
        # Delete with ownership validation
        user_id = str(current_user.id)
        deleted = await thread_service.delete_thread(
            db=db,
            agent_id=agent_id,
            thread_id=thread_id,
            user_id=user_id
        )
        
        if not deleted:
            logger.warning(f"[CHAT_API] Thread {thread_id} not found for agent {agent_id}")
            raise HTTPException(status_code=404, detail="Thread not found")
        
        logger.info(f"[CHAT_API] Thread {thread_id} deleted successfully")
        return {"detail": "Thread deleted successfully"}
        
    except Exception as e:
        logger.error(f"[CHAT_API] Error deleting thread {thread_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{agent_id}/threads/{thread_id}/generate_title", response_model=GenerateTitleResponse)
async def generate_thread_title(
    agent_id: UUID = Path(..., description="Agent ID"),
    thread_id: UUID = Path(..., description="Thread ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Generate a title for a thread and update it"""
    
    logger.info(f"[CHAT_API] Generating title for thread {thread_id}, agent {agent_id}, user: {current_user.id}")
    
    try:
        # Generate title suggestion with ownership validation
        user_id = str(current_user.id)
        suggestion = await thread_service.generate_title_suggestion(
            db=db,
            agent_id=agent_id,
            thread_id=thread_id,
            user_id=user_id
        )
        
        if not suggestion:
            logger.warning(f"[CHAT_API] Title generation failed for thread {thread_id}")
            raise HTTPException(status_code=404, detail="Thread not found")
        
        logger.info(f"[CHAT_API] Generated title suggestion: '{suggestion['title']}'")
        
        # Update the thread with the generated title
        update_result = await thread_service.update_thread(
            db=db,
            agent_id=agent_id,
            thread_id=thread_id,
            user_id=user_id,
            title=suggestion["title"]
        )
        
        if not update_result:
            logger.error(f"[CHAT_API] Failed to update thread {thread_id} with generated title")
            raise HTTPException(status_code=500, detail="Failed to update thread title")
        
        updated_thread, _ = update_result
        logger.info(f"[CHAT_API] Successfully updated thread {thread_id} title to: '{updated_thread.title}'")
        
        # Return structured response
        return GenerateTitleResponse(
            id=thread_id,
            title=updated_thread.title,
            current_title=suggestion["current_title"],
            generated_at=suggestion["generated_at"],
            confidence=suggestion["confidence"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CHAT_API] Error generating title for thread {thread_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{agent_id}/threads/{thread_id}/messages", response_model=MessageListResponse)
async def get_thread_messages(
    agent_id: UUID = Path(..., description="Agent ID"),
    thread_id: UUID = Path(..., description="Thread ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=200, description="Page size"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get all messages for a thread with pagination"""
    
    logger.info(f"[CHAT_API] Getting messages for thread {thread_id}, agent {agent_id}, user: {current_user.id}")
    
    try:
        # Calculate offset from page number
        offset = (page - 1) * page_size
        
        # Get messages with ownership validation
        user_id = str(current_user.id)
        messages = await thread_service.get_thread_messages(
            db=db,
            agent_id=agent_id,
            thread_id=thread_id,
            user_id=user_id,
            offset=offset,
            limit=page_size
        )
        
        if messages is None:  # Thread not found
            logger.warning(f"[CHAT_API] Thread {thread_id} not found for agent {agent_id}")
            raise HTTPException(status_code=404, detail="Thread not found")
        
        logger.debug(f"[CHAT_API] Found {len(messages)} messages for thread {thread_id}")
        
        # Convert to response format
        message_responses = [MessageResponse.model_validate(msg.__dict__) for msg in messages]
        
        return MessageListResponse(
            messages=message_responses,
            total=len(messages),  # Note: This is page total, not overall total
            thread_id=thread_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CHAT_API] Error getting messages for thread {thread_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")