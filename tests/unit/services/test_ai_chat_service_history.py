import pytest
import uuid
from uuid import UUID
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.ai_chat_service import ai_chat_service, MessageFormat

@pytest.mark.asyncio
async def test_get_thread_history_simple_format():
    """Test thread history retrieval in simple format with context limits."""
    thread_id = str(uuid.uuid4())
    user_id = "test_user"
    agent_id = str(uuid.uuid4())
    
    with patch('app.services.ai_chat_service.get_async_db_session') as mock_db_session:
        # Mock database setup
        mock_db = AsyncMock()
        mock_db_session.return_value.__aenter__.return_value = mock_db
        
        # Mock thread verification
        thread_mock = MagicMock()
        thread_mock.id = UUID(thread_id)
        thread_result = MagicMock()
        thread_result.scalar_one_or_none.return_value = thread_mock
        
        # Mock messages
        message1 = MagicMock()
        message1.role = "user"
        message1.content = "Hello"
        message2 = MagicMock()
        message2.role = "assistant"
        message2.content = "Hi there!"
        
        messages_result = MagicMock()
        messages_result.scalars.return_value.all.return_value = [message1, message2]
        
        # Configure mock to return thread first, then messages
        mock_db.execute.side_effect = [thread_result, messages_result]
        
        # Test the method using the new consolidated API
        history = await ai_chat_service.get_thread_history(
            thread_id=thread_id,
            user_id=user_id,
            agent_id=agent_id,
            format_type=MessageFormat.SIMPLE,
            max_context_size=1000,
            use_memory_context=True
        )
        
        # Verify results
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello"
        assert history[1]["role"] == "assistant"
        assert history[1]["content"] == "Hi there!"

@pytest.mark.asyncio
async def test_apply_context_limits():
    """Test context limits are applied correctly."""
    # Create mock messages that exceed token limits
    messages = []
    for i in range(15):
        msg = MagicMock()
        msg.role = "user"
        msg.content = f"This is a long message number {i} with lots of content"
        messages.append(msg)
    
    # Test context limiting
    limited = await ai_chat_service._apply_context_limits(messages, 100)  # Small limit
    
    # Should return fewer messages due to token constraints
    assert len(limited) < len(messages)
    assert len(limited) > 0

@pytest.mark.asyncio
async def test_memory_context_disabled():
    """Test that empty list is returned when memory is disabled."""
    thread_id = str(uuid.uuid4())
    user_id = "test_user"
    agent_id = str(uuid.uuid4())
    
    history = await ai_chat_service.get_thread_history(
        thread_id=thread_id,
        user_id=user_id,
        agent_id=agent_id,
        format_type=MessageFormat.SIMPLE,
        use_memory_context=False
    )
    
    assert history == []

@pytest.mark.asyncio
async def test_context_limits_small_list():
    """Test that small message lists are returned unchanged."""
    # Create small list of messages
    messages = []
    for i in range(5):  # Only 5 messages
        msg = MagicMock()
        msg.role = "user"
        msg.content = f"Short message {i}"
        messages.append(msg)
    
    limited = await ai_chat_service._apply_context_limits(messages, 1000)
    
    # Should return all messages unchanged for small lists
    assert len(limited) == 5
    assert limited == messages

@pytest.mark.asyncio
async def test_context_limits_fallback():
    """Test fallback behavior when token counting fails."""
    # Create mock messages that will cause token counting to fail
    messages = []
    for i in range(15):
        msg = MagicMock()
        msg.role = "user"
        msg.content = f"Message {i}"
        messages.append(msg)
    
    # Mock token counting to fail
    with patch('app.services.token_counter_service.token_counter_service') as mock_token_service:
        mock_token_service.count_message_tokens.side_effect = Exception("Token counting failed")
        
        # Should fallback to keeping last 10 messages
        limited = await ai_chat_service._apply_context_limits(messages, 1000)
        
        assert len(limited) == 10  # Fallback limit

@pytest.mark.asyncio
async def test_get_thread_history_thread_not_found():
    """Test handling when thread is not found."""
    thread_id = str(uuid.uuid4())
    user_id = "test_user"
    agent_id = str(uuid.uuid4())
    
    with patch('app.services.ai_chat_service.get_async_db_session') as mock_db_session:
        # Mock database setup
        mock_db = AsyncMock()
        mock_db_session.return_value.__aenter__.return_value = mock_db
        
        # Mock thread not found
        thread_result = MagicMock()
        thread_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = thread_result
        
        # Test the method
        history = await ai_chat_service.get_thread_history(
            thread_id=thread_id,
            user_id=user_id,
            agent_id=agent_id,
            format_type=MessageFormat.SIMPLE,
            max_context_size=1000,
            use_memory_context=True
        )
        
        # Should return empty list
        assert history == []

@pytest.mark.asyncio
async def test_get_thread_history_with_context_limits():
    """Test message filtering with context limits."""
    thread_id = str(uuid.uuid4())
    user_id = "test_user"
    agent_id = str(uuid.uuid4())
    
    with patch('app.services.ai_chat_service.get_async_db_session') as mock_db_session, \
         patch.object(ai_chat_service, '_apply_context_limits') as mock_apply_limits:
        
        # Mock database setup
        mock_db = AsyncMock()
        mock_db_session.return_value.__aenter__.return_value = mock_db
        
        # Mock thread verification
        thread_mock = MagicMock()
        thread_mock.id = UUID(thread_id)
        thread_result = MagicMock()
        thread_result.scalar_one_or_none.return_value = thread_mock
        
        # Mock many messages
        messages = []
        for i in range(20):
            msg = MagicMock()
            msg.role = "user" if i % 2 == 0 else "assistant"
            msg.content = f"Message {i}"
            messages.append(msg)
        
        messages_result = MagicMock()
        messages_result.scalars.return_value.all.return_value = messages
        
        # Configure mock to return thread first, then messages
        mock_db.execute.side_effect = [thread_result, messages_result]
        
        # Mock context limits to return only first 5 messages
        limited_messages = messages[:5]
        mock_apply_limits.return_value = limited_messages
        
        # Test the method with context limits
        history = await ai_chat_service.get_thread_history(
            thread_id=thread_id,
            user_id=user_id,
            agent_id=agent_id,
            format_type=MessageFormat.SIMPLE,
            max_context_size=100,  # Small limit
            use_memory_context=True
        )
        
        # Verify context limits were applied
        mock_apply_limits.assert_called_once_with(messages, 100)
        assert len(history) == 5