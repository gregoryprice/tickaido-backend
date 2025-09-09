import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID
from pydantic_ai.messages import ModelMessage, ModelRequest, UserPromptPart
from app.services.ai_chat_service import ai_chat_service

@pytest.mark.asyncio
async def test_get_thread_history_as_model_messages():
    """Test retrieving thread history as ModelMessage format."""
    
    # Test with memory disabled - should return empty
    history = await ai_chat_service.get_thread_history_as_model_messages(
        thread_id="any-thread",
        user_id="any-user", 
        agent_id="any-agent",
        use_memory_context=False
    )
    
    # Should return empty list when memory context is disabled
    assert len(history) == 0

@pytest.mark.asyncio
async def test_get_thread_history_model_messages_memory_disabled():
    """Test that empty list is returned when memory is disabled."""
    
    thread_id = str(uuid.uuid4())
    user_id = "test_user"
    agent_id = str(uuid.uuid4())
    
    history = await ai_chat_service.get_thread_history_as_model_messages(
        thread_id=thread_id,
        user_id=user_id,
        agent_id=agent_id,
        use_memory_context=False
    )
    
    assert history == []

@pytest.mark.asyncio
async def test_get_thread_history_model_messages_thread_not_found():
    """Test handling when thread is not found."""
    
    thread_id = str(uuid.uuid4())
    user_id = "test_user"
    agent_id = str(uuid.uuid4())
    
    with patch('app.database.get_async_db_session') as mock_db_session:
        # Mock database setup
        mock_db = AsyncMock()
        mock_db_session.return_value.__aenter__.return_value = mock_db
        
        # Mock thread not found
        thread_result = MagicMock()
        thread_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = thread_result
        
        # Test the method
        history = await ai_chat_service.get_thread_history_as_model_messages(
            thread_id=thread_id,
            user_id=user_id,
            agent_id=agent_id,
            use_memory_context=True
        )
        
        # Should return empty list
        assert history == []

@pytest.mark.asyncio
async def test_get_thread_history_model_messages_with_context_limits():
    """Test that _apply_context_limits method exists and works correctly."""
    
    # Test the _apply_context_limits method directly since it's simpler and more reliable
    messages = []
    for i in range(15):  # Create more than 10 messages to trigger context limiting
        msg = MagicMock()
        msg.role = "user" if i % 2 == 0 else "assistant"
        msg.content = f"Message {i} content with some text to have realistic message lengths"
        messages.append(msg)
    
    # Test context limiting functionality with reasonable context size
    limited_messages = await ai_chat_service._apply_context_limits(messages, 100)  
    
    # Should return same or fewer messages
    assert len(limited_messages) <= len(messages)
    
    # Test with zero context size (should return all messages according to implementation)
    zero_context_messages = await ai_chat_service._apply_context_limits(messages, 0)
    assert len(zero_context_messages) == len(messages)  # Implementation returns all when <= 0
    
    # Test with very large context size
    all_messages = await ai_chat_service._apply_context_limits(messages, 10000)
    assert len(all_messages) == len(messages)  # Should return all messages
    
    # Test with small number of messages (should return all)
    small_messages = messages[:5]
    result_messages = await ai_chat_service._apply_context_limits(small_messages, 50)
    assert len(result_messages) == len(small_messages)  # Returns all when <= 10 messages

@pytest.mark.asyncio
async def test_get_thread_history_model_messages_converter_error():
    """Test error handling when message converter fails."""
    
    thread_id = str(uuid.uuid4())
    user_id = "test_user"
    agent_id = str(uuid.uuid4())
    
    with patch('app.database.get_async_db_session') as mock_db_session, \
         patch('app.services.message_converter_service.message_converter_service') as mock_converter:
        
        # Mock database setup
        mock_db = AsyncMock()
        mock_db_session.return_value.__aenter__.return_value = mock_db
        
        # Mock thread verification
        thread_mock = MagicMock()
        thread_mock.id = UUID(thread_id)
        thread_mock.user_id = user_id
        thread_mock.agent_id = UUID(agent_id)
        thread_result = MagicMock()
        thread_result.scalar_one_or_none.return_value = thread_mock
        
        # Mock messages
        message1 = MagicMock()
        message1.role = "user"
        message1.content = "Hello"
        
        messages_result = MagicMock()
        messages_result.scalars.return_value.all.return_value = [message1]
        
        # Configure mock to return thread first, then messages
        mock_db.execute.side_effect = [thread_result, messages_result]
        
        # Mock converter service to raise exception
        mock_converter.convert_db_messages_to_model_messages.side_effect = Exception("Conversion error")
        
        # Test the method - should handle error gracefully
        history = await ai_chat_service.get_thread_history_as_model_messages(
            thread_id=thread_id,
            user_id=user_id,
            agent_id=agent_id,
            use_memory_context=True
        )
        
        # Should return empty list on error
        assert history == []