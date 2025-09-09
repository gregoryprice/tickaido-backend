from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models.chat import Message, Thread
from app.services.token_counter_service import token_counter_service
import logging

logger = logging.getLogger(__name__)

class MessageHistoryService:
    async def get_thread_messages(
        self,
        db: AsyncSession,
        thread_id: str,
        max_context_size: int,
        use_memory_context: bool = True
    ) -> List[dict]:
        """
        Retrieve and filter thread messages based on context size limits.
        
        Args:
            db: Database session
            thread_id: Thread ID to retrieve messages from
            max_context_size: Maximum tokens allowed in context
            use_memory_context: Whether to include message history
            
        Returns:
            List of message dictionaries formatted for Pydantic AI
        """
        try:
            if not use_memory_context:
                logger.debug(f"Memory context disabled for thread {thread_id}")
                return []
            
            if max_context_size <= 0:
                logger.warning(f"Invalid max_context_size: {max_context_size}")
                return []
                
            # Get messages in reverse chronological order (most recent first)
            result = await db.execute(
                select(Message)
                .where(Message.thread_id == thread_id)
                .order_by(desc(Message.created_at))
                .limit(1000)  # Safety limit to prevent massive queries
            )
            messages = result.scalars().all()
            
            if not messages:
                logger.debug(f"No messages found for thread {thread_id}")
                return []
            
            # Convert to Pydantic AI format and count tokens
            formatted_messages = []
            total_tokens = 0
            
            # Process messages from most recent to oldest
            for message in messages:
                msg_dict = {
                    "role": str(message.role),
                    "content": str(message.content),
                    "timestamp": message.created_at.isoformat() if message.created_at else None
                }
                
                # Count tokens for this message
                message_tokens = await token_counter_service.count_message_tokens(msg_dict)
                
                # Check if adding this message would exceed context limit
                if total_tokens + message_tokens > max_context_size:
                    logger.debug(f"Context limit reached: {total_tokens} + {message_tokens} > {max_context_size}")
                    break
                    
                formatted_messages.append(msg_dict)
                total_tokens += message_tokens
                
            # Return messages in chronological order (oldest first)
            result_messages = formatted_messages[::-1]
            logger.info(f"Loaded {len(result_messages)} messages ({total_tokens} tokens) for thread {thread_id}")
            
            return result_messages
            
        except Exception as e:
            logger.error(f"Error retrieving thread messages for {thread_id}: {e}")
            return []
    
    async def validate_thread_exists(self, db: AsyncSession, thread_id: str) -> bool:
        """Validate that a thread exists."""
        try:
            result = await db.execute(
                select(Thread).where(Thread.id == thread_id)
            )
            thread = result.scalar_one_or_none()
            return thread is not None
        except Exception as e:
            logger.error(f"Error validating thread {thread_id}: {e}")
            return False

message_history_service = MessageHistoryService()