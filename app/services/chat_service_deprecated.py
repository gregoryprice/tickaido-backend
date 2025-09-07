#!/usr/bin/env python3
"""
Chat service for conversation business logic operations
"""

import logging
from typing import List, Tuple, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_


logger = logging.getLogger(__name__)


class ChatService:
    """Service for chat conversation operations"""
    
    async def create_conversation(
        self,
        db: AsyncSession,
        user_id: UUID,
        title: Optional[str] = None
    ) -> ChatConversation:
        """
        Create a new conversation for the user with race condition protection.
        
        Args:
            db: Database session
            user_id: ID of the user creating the conversation
            title: Optional conversation title
            
        Returns:
            ChatConversation: Newly created conversation
        """
        conversation_title = title or "New Conversation"
        
        try:
            logger.debug(f"[CHAT_SERVICE] Creating conversation for user {user_id}")
            logger.debug(f"[CHAT_SERVICE] Conversation title: {conversation_title}")
            
            # Create conversation with user ownership
            conversation = ChatConversation(
                user_id=str(user_id),
                title=conversation_title
            )
            
            db.add(conversation)
            await db.commit()
            await db.refresh(conversation)
            
            logger.info(f"[CHAT_SERVICE] Created conversation {conversation.id} for user {user_id}")
            logger.debug(f"[CHAT_SERVICE] Conversation created with title: {conversation.title}")
            return conversation
            
        except Exception as e:
            await db.rollback()
            logger.error(f"[CHAT_SERVICE] Error creating conversation: {e}")
            import traceback
            logger.error(f"[CHAT_SERVICE] Full traceback: {traceback.format_exc()}")
            raise
    
    async def list_conversations(
        self,
        db: AsyncSession,
        user_id: UUID,
        offset: int = 0,
        limit: int = 20,
        archived: Optional[bool] = False,
        query: Optional[str] = None
    ) -> Tuple[List[ChatConversation], int]:
        """
        List conversations for a user with pagination, archive filtering, and optional search.
        
        Args:
            db: Database session
            user_id: User ID to filter by
            offset: Number of records to skip
            limit: Maximum number of records to return
            archived: Filter by archive status (False=non-archived, True=archived, None=all)
            query: Optional search query for titles and message content
            
        Returns:
            Tuple of (conversations list, total count)
        """
        try:
            logger.debug(f"[CHAT_SERVICE] Listing conversations for user {user_id}, offset={offset}, limit={limit}, archived={archived}, query={query}")
            
            # Build base query conditions
            conditions = [
                ChatConversation.user_id == str(user_id),
                ChatConversation.is_deleted.is_(False)
            ]
            
            # Add archive filter condition if specified
            if archived is not None:
                conditions.append(ChatConversation.is_archived.is_(archived))
            
            # Add search condition if query provided
            if query and query.strip():
                search_term = f"%{query.strip()}%"
                logger.debug(f"[CHAT_SERVICE] Adding search condition for term: {search_term}")
                
                # Search in conversation titles
                title_condition = ChatConversation.title.ilike(search_term)
                
                # Search in message content (requires subquery)
                message_subquery = select(ChatMessage.conversation_id).where(
                    ChatMessage.content.ilike(search_term)
                ).distinct()
                content_condition = ChatConversation.id.in_(message_subquery)
                
                # Combine title and content search with OR logic
                search_condition = or_(title_condition, content_condition)
                conditions.append(search_condition)
                
                logger.debug("[CHAT_SERVICE] Search conditions added for title and message content")
            
            # Query conversations for user
            conversation_query = select(ChatConversation).where(*conditions).order_by(desc(ChatConversation.updated_at))
            
            # Count total
            count_query = select(func.count()).select_from(ChatConversation).where(*conditions)
            
            # Execute queries
            result = await db.execute(conversation_query.offset(offset).limit(limit))
            conversations = result.scalars().all()
            
            count_result = await db.execute(count_query)
            total = count_result.scalar()
            
            logger.debug(f"[CHAT_SERVICE] Found {len(conversations)} conversations, total={total}")
            
            return conversations, total or 0
            
        except Exception as e:
            logger.error(f"[CHAT_SERVICE] Error listing conversations for user {user_id}: {e}")
            import traceback
            logger.error(f"[CHAT_SERVICE] Full traceback: {traceback.format_exc()}")
            return [], 0
    
    async def get_conversation(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        user_id: UUID
    ) -> Optional[ChatConversation]:
        """
        Get a single conversation by ID with user ownership validation.
        
        Args:
            db: Database session
            conversation_id: ID of the conversation
            user_id: User ID for ownership validation
            
        Returns:
            ChatConversation if found and owned by user, None otherwise
        """
        try:
            logger.debug(f"[CHAT_SERVICE] Getting conversation {conversation_id} for user {user_id}")
            
            query = select(ChatConversation).where(
                ChatConversation.id == conversation_id,
                ChatConversation.user_id == str(user_id),
                ChatConversation.is_deleted.is_(False)
            )
            
            result = await db.execute(query)
            conversation = result.scalar_one_or_none()
            
            if conversation:
                logger.debug(f"[CHAT_SERVICE] Found conversation: {conversation.title}")
            else:
                logger.warning(f"[CHAT_SERVICE] Conversation {conversation_id} not found or not accessible for user {user_id}")
            
            return conversation
            
        except Exception as e:
            logger.error(f"[CHAT_SERVICE] Error getting conversation {conversation_id}: {e}")
            import traceback
            logger.error(f"[CHAT_SERVICE] Full traceback: {traceback.format_exc()}")
            return None
    
    async def get_conversation_messages(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        user_id: UUID,
        offset: int = 0,
        limit: int = 100
    ) -> List[ChatMessage]:
        """
        Get messages for a conversation with ownership validation.
        
        Args:
            db: Database session
            conversation_id: ID of the conversation
            user_id: User ID for ownership validation
            offset: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of messages in chronological order
        """
        try:
            logger.debug(f"[CHAT_SERVICE] Getting messages for conversation {conversation_id}, user {user_id}")
            
            # First verify user owns the conversation
            conversation = await self.get_conversation(db, conversation_id, user_id)
            if not conversation:
                logger.warning(f"[CHAT_SERVICE] Cannot get messages - conversation {conversation_id} not accessible")
                return []
            
            # Get messages for the conversation
            query = select(ChatMessage).where(
                ChatMessage.conversation_id == conversation_id
            ).order_by(ChatMessage.created_at).offset(offset).limit(limit)
            
            result = await db.execute(query)
            messages = result.scalars().all()
            
            logger.debug(f"[CHAT_SERVICE] Found {len(messages)} messages for conversation {conversation_id}")
            
            return messages
            
        except Exception as e:
            logger.error(f"[CHAT_SERVICE] Error getting messages for conversation {conversation_id}: {e}")
            import traceback
            logger.error(f"[CHAT_SERVICE] Full traceback: {traceback.format_exc()}")
            return []
    
    async def update_conversation_title(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        user_id: UUID,
        title: str
    ) -> Optional[ChatConversation]:
        """
        Update conversation title with ownership validation.
        
        Args:
            db: Database session
            conversation_id: ID of the conversation
            user_id: User ID for ownership validation
            title: New title
            
        Returns:
            Updated conversation if successful, None otherwise
        """
        try:
            # Get conversation with ownership validation
            conversation = await self.get_conversation(db, conversation_id, user_id)
            if not conversation:
                return None
            
            # Update title
            conversation.title = title
            await db.commit()
            await db.refresh(conversation)
            
            logger.info(f"Updated title for conversation {conversation_id}: {title}")
            return conversation
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating conversation title: {e}")
            return None
    
    async def delete_conversation(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        user_id: UUID
    ) -> bool:
        """
        Soft delete a conversation with ownership validation.
        
        Args:
            db: Database session
            conversation_id: ID of the conversation
            user_id: User ID for ownership validation
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            # Get conversation with ownership validation
            conversation = await self.get_conversation(db, conversation_id, user_id)
            if not conversation:
                return False
            
            # Soft delete
            conversation.is_deleted = True
            await db.commit()
            
            logger.info(f"Deleted conversation {conversation_id}")
            return True
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error deleting conversation: {e}")
            return False
    
    async def archive_conversation(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        user_id: UUID
    ) -> Optional[ChatConversation]:
        """
        Archive a conversation with ownership validation.
        
        Args:
            db: Database session
            conversation_id: ID of the conversation
            user_id: User ID for ownership validation
            
        Returns:
            Updated conversation if successful, None otherwise
        """
        try:
            logger.debug(f"[CHAT_SERVICE] Archiving conversation {conversation_id} for user {user_id}")
            
            # Get conversation with ownership validation
            conversation = await self.get_conversation(db, conversation_id, user_id)
            if not conversation:
                logger.warning(f"[CHAT_SERVICE] Cannot archive - conversation {conversation_id} not found or not accessible")
                return None
            
            # Archive the conversation
            conversation.is_archived = True
            await db.commit()
            await db.refresh(conversation)
            
            logger.info(f"[CHAT_SERVICE] Archived conversation {conversation_id}")
            return conversation
            
        except Exception as e:
            await db.rollback()
            logger.error(f"[CHAT_SERVICE] Error archiving conversation {conversation_id}: {e}")
            import traceback
            logger.error(f"[CHAT_SERVICE] Full traceback: {traceback.format_exc()}")
            return None
    
    async def unarchive_conversation(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        user_id: UUID
    ) -> Optional[ChatConversation]:
        """
        Unarchive a conversation with ownership validation.
        
        Args:
            db: Database session
            conversation_id: ID of the conversation
            user_id: User ID for ownership validation
            
        Returns:
            Updated conversation if successful, None otherwise
        """
        try:
            logger.debug(f"[CHAT_SERVICE] Unarchiving conversation {conversation_id} for user {user_id}")
            
            # Get conversation with ownership validation
            conversation = await self.get_conversation(db, conversation_id, user_id)
            if not conversation:
                logger.warning(f"[CHAT_SERVICE] Cannot unarchive - conversation {conversation_id} not found or not accessible")
                return None
            
            # Unarchive the conversation
            conversation.is_archived = False
            await db.commit()
            await db.refresh(conversation)
            
            logger.info(f"[CHAT_SERVICE] Unarchived conversation {conversation_id}")
            return conversation
            
        except Exception as e:
            await db.rollback()
            logger.error(f"[CHAT_SERVICE] Error unarchiving conversation {conversation_id}: {e}")
            import traceback
            logger.error(f"[CHAT_SERVICE] Full traceback: {traceback.format_exc()}")
            return None
    
    async def update_conversation(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        user_id: UUID,
        title: Optional[str] = None,
        is_archived: Optional[bool] = None
    ) -> Optional[tuple[ChatConversation, List[str]]]:
        """
        Update conversation fields with ownership validation.
        
        Args:
            db: Database session
            conversation_id: ID of the conversation
            user_id: User ID for ownership validation
            title: New title (optional)
            is_archived: Archive status (optional)
            
        Returns:
            Tuple of (updated conversation, list of updated fields) if successful, None otherwise
        """
        try:
            logger.debug(f"[CHAT_SERVICE] Updating conversation {conversation_id} for user {user_id}")
            
            # Validate at least one field is provided
            if title is None and is_archived is None:
                logger.warning("[CHAT_SERVICE] No fields provided for update")
                raise ValueError("At least one field must be provided")
            
            # Get conversation with ownership validation
            conversation = await self.get_conversation(db, conversation_id, user_id)
            if not conversation:
                logger.warning(f"[CHAT_SERVICE] Cannot update - conversation {conversation_id} not found or not accessible")
                return None
            
            # Track which fields are actually updated
            updated_fields = []
            
            # Update title if provided
            if title is not None:
                title = title.strip()
                if not title:
                    raise ValueError("Title cannot be empty after trimming whitespace")
                if title != conversation.title:
                    conversation.title = title
                    updated_fields.append("title")
                    logger.debug(f"[CHAT_SERVICE] Updated title: {title}")
            
            # Update archive status if provided
            if is_archived is not None:
                if is_archived != conversation.is_archived:
                    conversation.is_archived = is_archived
                    updated_fields.append("is_archived")
                    logger.debug(f"[CHAT_SERVICE] Updated archive status: {is_archived}")
            
            # Only commit if there are actual changes
            if updated_fields:
                await db.commit()
                await db.refresh(conversation)
                logger.info(f"[CHAT_SERVICE] Updated conversation {conversation_id}, fields: {updated_fields}")
            else:
                logger.debug(f"[CHAT_SERVICE] No changes needed for conversation {conversation_id}")
            
            return conversation, updated_fields
            
        except ValueError as e:
            # Don't rollback for validation errors
            logger.warning(f"[CHAT_SERVICE] Validation error updating conversation {conversation_id}: {e}")
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"[CHAT_SERVICE] Error updating conversation {conversation_id}: {e}")
            import traceback
            logger.error(f"[CHAT_SERVICE] Full traceback: {traceback.format_exc()}")
            return None

    async def generate_title_suggestion(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        user_id: UUID
    ) -> Optional[dict]:
        """
        Generate a title suggestion for a conversation using AI.
        
        This is a READ-ONLY operation that does not modify the conversation.
        It returns a suggestion that can be applied via the update_conversation_title method.
        
        Args:
            db: Database session
            conversation_id: ID of the conversation
            user_id: User ID for ownership validation
            
        Returns:
            Optional[dict]: Title suggestion with metadata, or None if conversation not found
        """
        try:
            logger.debug(f"[CHAT_SERVICE] Generating title suggestion for conversation {conversation_id}, user {user_id}")
            
            # Validate conversation ownership using existing method
            conversation = await self.get_conversation(db, conversation_id, user_id)
            if not conversation:
                logger.warning(f"[CHAT_SERVICE] Cannot generate title - conversation {conversation_id} not found or not accessible")
                return None
            
            # Use AI chat service for title generation
            from app.services.ai_chat_service import generate_conversation_title_comprehensive
            from datetime import datetime, timezone
            
            ai_result = await generate_conversation_title_comprehensive(
                conversation_id=str(conversation_id),
                user_id=str(user_id)
            )
            
            if not ai_result:
                logger.warning(f"[CHAT_SERVICE] AI title generation failed for conversation {conversation_id}")
                return None
            
            # Prepare response with current conversation context
            suggestion = {
                "id": conversation_id,
                "title": ai_result.title,
                "current_title": conversation.title,
                "generated_at": datetime.now(timezone.utc),
                "confidence": ai_result.confidence
            }
            
            logger.info(f"[CHAT_SERVICE] Generated title suggestion: '{ai_result.title}' (confidence: {ai_result.confidence:.2f})")
            logger.debug(f"[CHAT_SERVICE] Current title: '{conversation.title}' -> Suggested: '{ai_result.title}'")
            
            return suggestion
            
        except Exception as e:
            logger.error(f"[CHAT_SERVICE] Error generating title suggestion for conversation {conversation_id}: {e}")
            import traceback
            logger.error(f"[CHAT_SERVICE] Full traceback: {traceback.format_exc()}")
            return None


# Global service instance
chat_service = ChatService()