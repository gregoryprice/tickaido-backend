#!/usr/bin/env python3
"""
Chat API endpoints
"""

import logging
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.schemas.chat import ConversationResponse, CreateConversationRequest, MessageResponse, SendMessageRequest, GenerateTitleResponse, UpdateConversationRequest, ConversationUpdateResponse
from app.models.user import User
from app.services.chat_service import chat_service
from app.services.ai_chat_service import ai_chat_service
from app.dependencies import get_current_active_user
from app.services.auth_provider import decode_jwt_token

router = APIRouter(prefix="/chat", tags=["Chat Assistant"])
logger = logging.getLogger(__name__)


@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    archived: bool = Query(False, description="Filter by archive status"),
    q: Optional[str] = Query(None, description="Search conversations by title and content"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    """List user's chat conversations with optional archive filter and search"""
    
    logger.info(f"[CHAT_API] Listing conversations for user_id: {current_user.id}, archived={archived}, query={q}")
    
    # Get conversations for current user only
    from uuid import UUID
    user_id: UUID = current_user.id  # type: ignore
    conversations, _ = await chat_service.list_conversations(
        db=db,
        user_id=user_id,
        offset=0,
        limit=20,
        archived=archived,
        query=q
    )
    
    logger.debug(f"[CHAT_API] Found {len(conversations)} conversations for user {user_id} with archived={archived}")
    
    # Convert to response format
    result = [ConversationResponse.model_validate(conv) for conv in conversations]
    logger.debug(f"[CHAT_API] Returning {len(result)} conversation responses")
    
    return result


@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    request: CreateConversationRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new chat conversation"""
    
    logger.info(f"[CHAT_API] Creating conversation for user_id: {current_user.id}")
    logger.debug(f"[CHAT_API] Request data: title={request.title}")
    
    # Create conversation for current user
    from uuid import UUID
    user_id: UUID = current_user.id  # type: ignore
    conversation = await chat_service.create_conversation(
        db=db,
        user_id=user_id,
        title=request.title
    )
    
    logger.info(f"[CHAT_API] Created conversation {conversation.id} for user {user_id}")
    
    # Convert to response format
    result = ConversationResponse.model_validate(conversation)
    logger.debug(f"[CHAT_API] Returning conversation response: {result.id}")
    
    return result


@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    conversation_id: UUID = Path(..., description="Conversation ID"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get all messages for a conversation"""
    
    logger.info(f"[CHAT_API] Getting messages for conversation {conversation_id}, user_id: {current_user.id}")
    
    # Get messages with ownership validation
    user_id: UUID = current_user.id  # type: ignore
    messages = await chat_service.get_conversation_messages(
        db=db,
        conversation_id=conversation_id,
        user_id=user_id
    )
    
    logger.debug(f"[CHAT_API] Found {len(messages)} messages for conversation {conversation_id}")
    
    # Convert to response format
    result = [MessageResponse.model_validate(msg) for msg in messages]
    logger.debug(f"[CHAT_API] Returning {len(result)} message responses")
    
    return result


@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse)
async def send_message(
    request: SendMessageRequest,
    http_request: Request,
    conversation_id: UUID = Path(..., description="Conversation ID"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Send a message to a conversation and get AI response"""
    
    logger.info(f"[CHAT_API] Sending message to conversation {conversation_id}, user_id: {current_user.id}")
    logger.debug(f"[CHAT_API] Message content: {request.message[:100]}{'...' if len(request.message) > 100 else ''}")
    
    # Extract JWT token from Authorization header
    auth_header = http_request.headers.get("authorization", "")
    jwt_token = None
    token_expires_at = None
    
    if auth_header.startswith("Bearer "):
        jwt_token = auth_header[7:]  # Remove "Bearer " prefix
        # Decode token to get expiry time
        try:
            payload = decode_jwt_token(jwt_token)
            token_expires_at = datetime.fromtimestamp(payload.get("exp", 0), tz=timezone.utc)
            logger.debug(f"[CHAT_API] Extracted JWT token for MCP authentication, expires at: {token_expires_at}")
        except Exception as e:
            logger.warning(f"[CHAT_API] Failed to decode JWT token for MCP context: {e}")
    else:
        logger.warning("[CHAT_API] No Bearer token found in Authorization header")
    
    try:
        # Verify conversation ownership first using basic chat service
        user_id: UUID = current_user.id  # type: ignore
        conversation = await chat_service.get_conversation(
            db=db,
            conversation_id=conversation_id,
            user_id=user_id
        )
        
        if not conversation:
            logger.warning(f"[CHAT_API] Conversation {conversation_id} not found for user {user_id}")
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        logger.debug("[CHAT_API] Conversation validated, calling AI service with authentication")
        
        # Use AI chat service with authentication context
        ai_response = await ai_chat_service.send_message_with_auth(
            conversation_id=str(conversation_id),
            user_id=str(user_id),
            message=request.message,
            auth_token=jwt_token,
            token_expires_at=token_expires_at
        )
        
        logger.info(f"[CHAT_API] AI response generated with confidence: {ai_response.confidence}")
        logger.debug(f"[CHAT_API] AI response content: {ai_response.content[:100]}{'...' if len(ai_response.content) > 100 else ''}")
        
        # Now get the actual stored assistant message from the database
        # The AI service should have stored both user and assistant messages
        messages = await chat_service.get_conversation_messages(
            db=db,
            conversation_id=conversation_id,
            user_id=user_id,
            offset=0,
            limit=10  # Get recent messages
        )
        
        # Find the most recent assistant message (should be the one just created)
        assistant_message = None
        for msg in reversed(messages):
            if msg.role == "assistant":
                assistant_message = msg
                break
        
        if assistant_message:
            logger.info(f"[CHAT_API] Found stored assistant message with ID: {assistant_message.id}")
            # Return the actual stored message
            return MessageResponse(
                id=assistant_message.id,
                created_at=assistant_message.created_at,
                updated_at=assistant_message.created_at,  # messages don't have updated_at
                conversation_id=conversation_id,
                role="assistant",
                content=assistant_message.content,
                model_used=assistant_message.model_used,
                tokens_used=assistant_message.tokens_used,
                response_time_ms=assistant_message.response_time_ms,
                confidence_score=assistant_message.confidence_score
            )
        else:
            logger.warning("[CHAT_API] Could not find stored assistant message, creating fallback response")
            # Fallback to creating a response based on AI service output
            import uuid
            return MessageResponse(
                id=uuid.uuid4(),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                conversation_id=conversation_id,
                role="assistant",
                content=ai_response.content,
                model_used=None,
                tokens_used=None,
                response_time_ms=None,
                confidence_score=ai_response.confidence
            )
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 404) without modification
        raise
    except ValueError as e:
        # Conversation not found or not accessible
        logger.warning(f"[CHAT_API] ValueError in send_message: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # General error handling with better classification
        error_msg = str(e).lower()
        logger.error(f"[CHAT_API] Error in send_message endpoint: {e}")
        logger.error(f"[CHAT_API] Error type: {type(e).__name__}")
        
        # Check if it's a database-related error that should be a 404
        if "not found" in error_msg or "not accessible" in error_msg:
            logger.warning(f"[CHAT_API] Converting database error to 404: {e}")
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Check for other specific error types
        if "connection" in error_msg or "database" in error_msg:
            logger.error(f"[CHAT_API] Database connection error: {e}")
            raise HTTPException(status_code=503, detail="Service temporarily unavailable")
        
        raise HTTPException(status_code=500, detail="Internal server error")


@router.patch("/conversations/{conversation_id}", response_model=ConversationUpdateResponse)
async def update_conversation(
    request: UpdateConversationRequest,
    conversation_id: UUID = Path(..., description="Conversation ID"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Update conversation fields (title, archive status)"""
    
    logger.info(f"[CHAT_API] Updating conversation {conversation_id} for user_id: {current_user.id}")
    
    # Validate request body has at least one field
    if request.title is None and request.is_archived is None:
        logger.warning(f"[CHAT_API] Empty request body for conversation {conversation_id}")
        raise HTTPException(status_code=400, detail="At least one field must be provided")
    
    try:
        # Update conversation with ownership validation
        user_id: UUID = current_user.id  # type: ignore
        result = await chat_service.update_conversation(
            db=db,
            conversation_id=conversation_id,
            user_id=user_id,
            title=request.title,
            is_archived=request.is_archived
        )
        
        if not result:
            logger.warning(f"[CHAT_API] Conversation {conversation_id} not found for user {user_id}")
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        conversation, updated_fields = result
        
        logger.info(f"[CHAT_API] Conversation {conversation_id} updated successfully, fields: {updated_fields}")
        
        # Convert to unified response format
        return ConversationUpdateResponse.model_validate({
            **conversation.__dict__,
            "updated_fields": updated_fields
        })
        
    except ValueError as e:
        # Handle validation errors (empty title, etc.)
        logger.warning(f"[CHAT_API] Validation error updating conversation {conversation_id}: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        # General error handling
        error_msg = str(e).lower()
        logger.error(f"[CHAT_API] Error updating conversation {conversation_id}: {e}")
        
        # Check if it's a database-related error that should be a 404
        if "not found" in error_msg or "not accessible" in error_msg:
            logger.warning(f"[CHAT_API] Converting database error to 404: {e}")
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Check for other specific error types
        if "connection" in error_msg or "database" in error_msg:
            logger.error(f"[CHAT_API] Database connection error: {e}")
            raise HTTPException(status_code=503, detail="Service temporarily unavailable")
        
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/conversations/{conversation_id}/generate_title", response_model=GenerateTitleResponse)
async def generate_conversation_title(
    conversation_id: UUID = Path(..., description="Conversation ID"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Generate a title for a conversation and update it"""
    
    logger.info(f"[CHAT_API] Generating and updating title for conversation {conversation_id}, user_id: {current_user.id}")
    
    # Generate title suggestion with ownership validation
    user_id: UUID = current_user.id  # type: ignore
    suggestion = await chat_service.generate_title_suggestion(
        db=db,
        conversation_id=conversation_id,
        user_id=user_id
    )
    
    if not suggestion:
        logger.warning(f"[CHAT_API] Title generation failed for conversation {conversation_id}")
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    logger.info(f"[CHAT_API] Generated title suggestion: '{suggestion['title']}' (confidence: {suggestion['confidence']:.2f})")
    
    # Update the conversation with the generated title
    update_result = await chat_service.update_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=user_id,
        title=suggestion["title"]
    )
    
    if not update_result:
        logger.error(f"[CHAT_API] Failed to update conversation {conversation_id} with generated title")
        raise HTTPException(status_code=500, detail="Failed to update conversation title")
    
    updated_conversation, _ = update_result
    logger.info(f"[CHAT_API] Successfully updated conversation {conversation_id} title to: '{updated_conversation.title}'")
    
    # Return structured response with the updated title
    return GenerateTitleResponse(
        id=conversation_id,
        title=updated_conversation.title,
        current_title=suggestion["current_title"],  # This was the title before the update
        generated_at=suggestion["generated_at"],
        confidence=suggestion["confidence"]
    )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: UUID = Path(..., description="Conversation ID"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Delete a conversation (soft delete)"""
    
    # Delete with ownership validation
    user_id: UUID = current_user.id  # type: ignore
    deleted = await chat_service.delete_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=user_id
    )
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Return success status
    return {"detail": "Conversation deleted successfully"}