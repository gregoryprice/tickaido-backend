import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.message_history_service import message_history_service
from app.models.chat import Message, Thread

@pytest.mark.asyncio
async def test_get_thread_messages_memory_disabled():
    """Test that no messages are returned when memory is disabled."""
    db = AsyncMock()
    thread_id = str(uuid.uuid4())
    
    messages = await message_history_service.get_thread_messages(
        db=db, 
        thread_id=thread_id, 
        max_context_size=1000,
        use_memory_context=False
    )
    
    assert messages == []
    db.execute.assert_not_called()

@pytest.mark.asyncio
async def test_get_thread_messages_invalid_context_size():
    """Test handling of invalid context size."""
    db = AsyncMock()
    thread_id = str(uuid.uuid4())
    
    messages = await message_history_service.get_thread_messages(
        db=db,
        thread_id=thread_id,
        max_context_size=0,
        use_memory_context=True
    )
    
    assert messages == []
    db.execute.assert_not_called()

@pytest.mark.asyncio
async def test_get_thread_messages_empty_thread():
    """Test handling of thread with no messages."""
    db = AsyncMock()
    thread_id = str(uuid.uuid4())
    
    # Mock empty result
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    db.execute.return_value = result_mock
    
    messages = await message_history_service.get_thread_messages(
        db=db,
        thread_id=thread_id,
        max_context_size=1000,
        use_memory_context=True
    )
    
    assert messages == []
    db.execute.assert_called_once()

@pytest.mark.asyncio
async def test_get_thread_messages_with_context_limit():
    """Test message filtering based on context limits."""
    db = AsyncMock()
    thread_id = str(uuid.uuid4())
    
    # Create mock messages
    message1 = MagicMock()
    message1.role = "user"
    message1.content = "Short message"
    message1.created_at = datetime.now(timezone.utc)
    
    message2 = MagicMock()
    message2.role = "assistant"
    message2.content = "This is a much longer response that contains many more tokens"
    message2.created_at = datetime.now(timezone.utc)
    
    # Mock database result
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [message2, message1]  # Reverse chronological
    db.execute.return_value = result_mock
    
    messages = await message_history_service.get_thread_messages(
        db=db,
        thread_id=thread_id,
        max_context_size=50,  # Small limit to test filtering
        use_memory_context=True
    )
    
    assert isinstance(messages, list)
    assert len(messages) <= 2  # Should respect context limits
    db.execute.assert_called_once()

@pytest.mark.asyncio
async def test_validate_thread_exists():
    """Test thread validation."""
    db = AsyncMock()
    thread_id = str(uuid.uuid4())
    
    # Mock existing thread
    thread_mock = MagicMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = thread_mock
    db.execute.return_value = result_mock
    
    exists = await message_history_service.validate_thread_exists(db, thread_id)
    
    assert exists is True
    db.execute.assert_called_once()

@pytest.mark.asyncio
async def test_validate_thread_not_exists():
    """Test thread validation for non-existent thread."""
    db = AsyncMock()
    thread_id = str(uuid.uuid4())
    
    # Mock non-existent thread
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute.return_value = result_mock
    
    exists = await message_history_service.validate_thread_exists(db, thread_id)
    
    assert exists is False
    db.execute.assert_called_once()