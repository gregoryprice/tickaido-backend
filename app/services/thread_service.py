#!/usr/bin/env python3
"""
Thread service for agent-centric conversation management
"""

import logging
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import delete, desc, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_agent import Agent
from app.models.chat import Message, Thread

logger = logging.getLogger(__name__)


class ThreadService:
    """Service for agent-centric thread operations"""
    
    async def create_thread(
        self,
        db: AsyncSession,
        agent_id: UUID,
        user_id: str,
        title: Optional[str] = None
    ) -> Thread:
        """
        Create a new thread for an agent with organization validation.
        
        Args:
            db: Database session
            agent_id: ID of the agent this thread belongs to
            user_id: ID of the user creating the thread
            title: Optional thread title
            
        Returns:
            Thread: Newly created thread
            
        Raises:
            ValueError: If agent not found or access denied
        """
        try:
            logger.debug(f"[THREAD_SERVICE] Creating thread for agent {agent_id}, user {user_id}")
            
            # Validate agent exists and get organization
            agent_query = select(Agent).where(
                Agent.id == agent_id,
                Agent.is_active.is_(True)
            )
            result = await db.execute(agent_query)
            agent = result.scalar_one_or_none()
            
            if not agent:
                error_msg = f"Agent {agent_id} not found or not active"
                logger.warning(f"[THREAD_SERVICE] {error_msg}")
                raise ValueError(error_msg)
            
            # Extract organization from agent
            organization_id = agent.organization_id
            logger.debug(f"[THREAD_SERVICE] Agent belongs to organization {organization_id}")
            
            # Use default title if not provided
            thread_title = title or "New Thread"
            
            # Create thread
            thread = Thread(
                agent_id=agent_id,
                user_id=user_id,
                organization_id=organization_id,
                title=thread_title,
                total_messages=0
            )
            
            db.add(thread)
            await db.commit()
            await db.refresh(thread)
            
            logger.info(f"[THREAD_SERVICE] Created thread {thread.id} for agent {agent_id}")
            return thread
            
        except ValueError:
            # Re-raise validation errors
            raise
        except IntegrityError as e:
            await db.rollback()
            logger.error(f"[THREAD_SERVICE] Integrity error creating thread: {e}")
            raise ValueError("Failed to create thread due to data constraint violation")
        except Exception as e:
            await db.rollback()
            logger.error(f"[THREAD_SERVICE] Error creating thread: {e}")
            import traceback
            logger.error(f"[THREAD_SERVICE] Full traceback: {traceback.format_exc()}")
            raise
    
    async def list_threads(
        self,
        db: AsyncSession,
        agent_id: UUID,
        user_id: str,
        offset: int = 0,
        limit: int = 20,
        archived: Optional[bool] = False,
        query: Optional[str] = None
    ) -> Tuple[List[Thread], int]:
        """
        List threads for an agent with filtering and pagination.
        
        Args:
            db: Database session
            agent_id: Agent ID to filter by
            user_id: User ID for ownership validation
            offset: Number of records to skip
            limit: Maximum number of records to return
            archived: Filter by archive status (False=non-archived, True=archived, None=all)
            query: Optional search query for titles and message content
            
        Returns:
            Tuple of (threads list, total count)
        """
        try:
            logger.debug(f"[THREAD_SERVICE] Listing threads for agent {agent_id}, user {user_id}")
            
            # Validate agent exists and user has access
            agent_query = select(Agent).where(
                Agent.id == agent_id,
                Agent.is_active.is_(True)
            )
            result = await db.execute(agent_query)
            agent = result.scalar_one_or_none()
            
            if not agent:
                logger.warning(f"[THREAD_SERVICE] Agent {agent_id} not found or not active")
                return [], 0
            
            # Build base query conditions
            conditions = [
                Thread.agent_id == agent_id,
                Thread.user_id == user_id,
                Thread.organization_id == agent.organization_id
            ]
            
            # Add archive filter condition if specified
            if archived is not None:
                conditions.append(Thread.archived.is_(archived))
            
            # Add search condition if query provided
            if query and query.strip():
                search_term = f"%{query.strip()}%"
                logger.debug(f"[THREAD_SERVICE] Adding search condition for term: {search_term}")
                
                # Search in thread titles
                title_condition = Thread.title.ilike(search_term)
                
                # Search in message content (requires subquery)
                message_subquery = select(Message.thread_id).where(
                    Message.content.ilike(search_term)
                ).distinct()
                content_condition = Thread.id.in_(message_subquery)
                
                # Combine title and content search with OR logic
                search_condition = or_(title_condition, content_condition)
                conditions.append(search_condition)
                
                logger.debug("[THREAD_SERVICE] Search conditions added for title and message content")
            
            # Query threads
            thread_query = select(Thread).where(*conditions).order_by(desc(Thread.updated_at))
            
            # Count total
            count_query = select(func.count()).select_from(Thread).where(*conditions)
            
            # Execute queries
            result = await db.execute(thread_query.offset(offset).limit(limit))
            threads = result.scalars().all()
            
            count_result = await db.execute(count_query)
            total = count_result.scalar()
            
            logger.debug(f"[THREAD_SERVICE] Found {len(threads)} threads, total={total}")
            
            return threads, total or 0
            
        except Exception as e:
            logger.error(f"[THREAD_SERVICE] Error listing threads for agent {agent_id}: {e}")
            import traceback
            logger.error(f"[THREAD_SERVICE] Full traceback: {traceback.format_exc()}")
            return [], 0
    
    async def get_thread(
        self,
        db: AsyncSession,
        agent_id: UUID,
        thread_id: UUID,
        user_id: str
    ) -> Optional[Thread]:
        """
        Get a single thread by ID with agent and user ownership validation.
        
        Args:
            db: Database session
            agent_id: Agent ID for validation
            thread_id: ID of the thread
            user_id: User ID for ownership validation
            
        Returns:
            Thread if found and accessible, None otherwise
        """
        try:
            logger.debug(f"[THREAD_SERVICE] Getting thread {thread_id} for agent {agent_id}, user {user_id}")
            
            # Validate agent exists and is active
            agent_query = select(Agent).where(
                Agent.id == agent_id,
                Agent.is_active.is_(True)
            )
            result = await db.execute(agent_query)
            agent = result.scalar_one_or_none()
            
            if not agent:
                logger.warning(f"[THREAD_SERVICE] Agent {agent_id} not found or not active")
                return None
            
            # Get thread with all validation conditions
            query = select(Thread).where(
                Thread.id == thread_id,
                Thread.agent_id == agent_id,
                Thread.user_id == user_id,
                Thread.organization_id == agent.organization_id
            )
            
            result = await db.execute(query)
            thread = result.scalar_one_or_none()
            
            if thread:
                logger.debug(f"[THREAD_SERVICE] Found thread: {thread.title}")
            else:
                logger.warning(f"[THREAD_SERVICE] Thread {thread_id} not found or not accessible for user {user_id}")
            
            return thread
            
        except Exception as e:
            logger.error(f"[THREAD_SERVICE] Error getting thread {thread_id}: {e}")
            import traceback
            logger.error(f"[THREAD_SERVICE] Full traceback: {traceback.format_exc()}")
            return None
    
    async def get_thread_messages(
        self,
        db: AsyncSession,
        agent_id: UUID,
        thread_id: UUID,
        user_id: str,
        offset: int = 0,
        limit: int = 100
    ) -> List[Message]:
        """
        Get messages for a thread with ownership validation.
        
        Args:
            db: Database session
            agent_id: Agent ID for validation
            thread_id: ID of the thread
            user_id: User ID for ownership validation
            offset: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of messages in chronological order
        """
        try:
            logger.debug(f"[THREAD_SERVICE] Getting messages for thread {thread_id}, agent {agent_id}, user {user_id}")
            
            # First verify user has access to the thread
            thread = await self.get_thread(db, agent_id, thread_id, user_id)
            if not thread:
                logger.warning(f"[THREAD_SERVICE] Cannot get messages - thread {thread_id} not accessible")
                return []
            
            # Get messages for the thread
            query = select(Message).where(
                Message.thread_id == thread_id
            ).order_by(Message.created_at).offset(offset).limit(limit)
            
            result = await db.execute(query)
            messages = result.scalars().all()
            
            logger.debug(f"[THREAD_SERVICE] Found {len(messages)} messages for thread {thread_id}")
            
            return messages
            
        except Exception as e:
            logger.error(f"[THREAD_SERVICE] Error getting messages for thread {thread_id}: {e}")
            import traceback
            logger.error(f"[THREAD_SERVICE] Full traceback: {traceback.format_exc()}")
            return []
    
    async def update_thread(
        self,
        db: AsyncSession,
        agent_id: UUID,
        thread_id: UUID,
        user_id: str,
        title: Optional[str] = None,
        archived: Optional[bool] = None
    ) -> Optional[tuple[Thread, List[str]]]:
        """
        Update thread fields with ownership validation.
        
        Args:
            db: Database session
            agent_id: Agent ID for validation
            thread_id: ID of the thread
            user_id: User ID for ownership validation
            title: New title (optional)
            archived: Archive status (optional)
            
        Returns:
            Tuple of (updated thread, list of updated fields) if successful, None otherwise
        """
        try:
            logger.debug(f"[THREAD_SERVICE] Updating thread {thread_id} for agent {agent_id}, user {user_id}")
            
            # Validate at least one field is provided
            if title is None and archived is None:
                logger.warning("[THREAD_SERVICE] No fields provided for update")
                raise ValueError("At least one field must be provided")
            
            # Get thread with ownership validation
            thread = await self.get_thread(db, agent_id, thread_id, user_id)
            if not thread:
                logger.warning(f"[THREAD_SERVICE] Cannot update - thread {thread_id} not found or not accessible")
                return None
            
            # Track which fields are actually updated
            updated_fields = []
            
            # Update title if provided
            if title is not None:
                title = title.strip()
                if not title:
                    raise ValueError("Title cannot be empty after trimming whitespace")
                if title != thread.title:
                    thread.title = title
                    updated_fields.append("title")
                    logger.debug(f"[THREAD_SERVICE] Updated title: {title}")
            
            # Update archive status if provided
            if archived is not None:
                if archived != thread.archived:
                    thread.archived = archived
                    updated_fields.append("archived")
                    logger.debug(f"[THREAD_SERVICE] Updated archive status: {archived}")
            
            
            # Only commit if there are actual changes
            if updated_fields:
                await db.commit()
                await db.refresh(thread)
                logger.info(f"[THREAD_SERVICE] Updated thread {thread_id}, fields: {updated_fields}")
            else:
                logger.debug(f"[THREAD_SERVICE] No changes needed for thread {thread_id}")
            
            return thread, updated_fields
            
        except ValueError as e:
            # Don't rollback for validation errors
            logger.warning(f"[THREAD_SERVICE] Validation error updating thread {thread_id}: {e}")
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"[THREAD_SERVICE] Error updating thread {thread_id}: {e}")
            import traceback
            logger.error(f"[THREAD_SERVICE] Full traceback: {traceback.format_exc()}")
            return None
    
    async def delete_thread(
        self,
        db: AsyncSession,
        agent_id: UUID,
        thread_id: UUID,
        user_id: str
    ) -> bool:
        """
        Hard delete a thread and all its associated messages and attached files.
        
        Args:
            db: Database session
            agent_id: Agent ID for validation
            thread_id: ID of the thread
            user_id: User ID for ownership validation
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            logger.debug(f"[THREAD_SERVICE] Hard deleting thread {thread_id} for agent {agent_id}, user {user_id}")
            
            # Get thread with ownership validation
            thread = await self.get_thread(db, agent_id, thread_id, user_id)
            if not thread:
                logger.warning(f"[THREAD_SERVICE] Cannot delete - thread {thread_id} not found or not accessible")
                return False
            
            # Cascade delete all files attached to messages in this thread
            from app.services.file_cleanup_service import file_cleanup_service
            deleted_files = await file_cleanup_service.cascade_delete_thread_files(
                db, thread_id, thread.organization_id
            )
            
            # Delete all messages associated with this thread first
            delete_messages_query = delete(Message).where(Message.thread_id == thread_id)
            result = await db.execute(delete_messages_query)
            messages_deleted = result.rowcount
            
            # Delete the thread itself
            await db.delete(thread)
            await db.commit()
            
            logger.info(f"[THREAD_SERVICE] Hard deleted thread {thread_id}, {messages_deleted} messages, and {deleted_files} files")
            return True
            
        except Exception as e:
            await db.rollback()
            logger.error(f"[THREAD_SERVICE] Error deleting thread {thread_id}: {e}")
            import traceback
            logger.error(f"[THREAD_SERVICE] Full traceback: {traceback.format_exc()}")
            return False
    
    async def update_message_counters(
        self,
        db: AsyncSession,
        thread_id: UUID,
        increment_count: int = 1
    ) -> bool:
        """
        Update thread message counters when messages are added.
        
        Args:
            db: Database session
            thread_id: ID of the thread to update
            increment_count: Number to add to total_messages (default: 1)
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            logger.debug(f"[THREAD_SERVICE] Updating message counters for thread {thread_id}")
            
            # Get the thread
            query = select(Thread).where(Thread.id == thread_id)
            result = await db.execute(query)
            thread = result.scalar_one_or_none()
            
            if not thread:
                logger.warning(f"[THREAD_SERVICE] Thread {thread_id} not found for counter update")
                return False
            
            # Update counters
            thread.total_messages += increment_count
            thread.last_message_at = func.now()
            
            await db.commit()
            logger.debug(f"[THREAD_SERVICE] Updated message counters for thread {thread_id}: total={thread.total_messages}")
            return True
            
        except Exception as e:
            await db.rollback()
            logger.error(f"[THREAD_SERVICE] Error updating message counters for thread {thread_id}: {e}")
            return False

    async def generate_title_suggestion(
        self,
        db: AsyncSession,
        agent_id: UUID,
        thread_id: UUID,
        user_id: str
    ) -> Optional[dict]:
        """
        Generate a title suggestion for a thread using system title generation agent.
        
        This is a READ-ONLY operation that does not modify the thread.
        Uses the latest 6 messages to optimize token usage and response time.
        
        Args:
            db: Database session
            agent_id: Agent ID for validation
            thread_id: ID of the thread
            user_id: User ID for ownership validation
            
        Returns:
            Optional[dict]: Title suggestion with metadata, or None if thread not found
        """
        try:
            logger.debug(f"[THREAD_SERVICE] Generating title suggestion for thread {thread_id}, agent {agent_id}, user {user_id}")
            
            # Validate thread ownership
            thread = await self.get_thread(db, agent_id, thread_id, user_id)
            if not thread:
                logger.warning(f"[THREAD_SERVICE] Cannot generate title - thread {thread_id} not found or not accessible")
                return None
            
            # Get system title generation agent (single instance)
            from app.services.agent_service import agent_service
            title_agent = await agent_service.get_system_title_agent(db)
            if not title_agent:
                logger.error("[THREAD_SERVICE] System title generation agent not available")
                return None
            
            # Get latest 6 messages for title generation (optimize token usage)
            messages = await self.get_thread_messages(db, agent_id, thread_id, user_id, offset=0, limit=6)
            if not messages:
                logger.warning(f"[THREAD_SERVICE] No messages found for title generation in thread {thread_id}")
                return None
            
            # Use title agent runner to generate title
            from datetime import datetime, timezone

            from app.services.title_generation_runner import TitleGenerationAgentRunner
            
            title_runner = TitleGenerationAgentRunner(title_agent)
            result = await title_runner.generate_title(messages, thread.title)
            
            # Prepare response with current thread context
            suggestion = {
                "id": thread_id,
                "title": result.title,
                "current_title": thread.title,
                "confidence": result.confidence,
                "generated_at": datetime.now(timezone.utc),
                "messages_analyzed": len(messages),
                "system_agent_used": True
            }
            
            logger.info(f"[THREAD_SERVICE] Generated title suggestion: '{result.title}' (confidence: {result.confidence:.2f}, {len(messages)} messages)")
            
            return suggestion
            
        except Exception as e:
            logger.error(f"[THREAD_SERVICE] Error generating title suggestion for thread {thread_id}: {e}")
            import traceback
            logger.error(f"[THREAD_SERVICE] Full traceback: {traceback.format_exc()}")
            return None


# Global service instance
thread_service = ThreadService()