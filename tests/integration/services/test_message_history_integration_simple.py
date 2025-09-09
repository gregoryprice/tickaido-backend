import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
from app.services.message_history_service import message_history_service
from app.services.token_counter_service import token_counter_service

@pytest.mark.asyncio
async def test_message_history_service_integration():
    """Test integration between message history and token counter services."""
    
    # Test that the services integrate properly
    mock_db = AsyncMock()
    thread_id = str(uuid.uuid4())
    
    # Mock a simple database result
    mock_message = MagicMock()
    mock_message.role = "user"
    mock_message.content = "Hello world"
    mock_message.created_at = MagicMock()
    mock_message.created_at.isoformat.return_value = "2023-01-01T00:00:00"
    
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [mock_message]
    mock_db.execute.return_value = result_mock
    
    # Test the integration
    messages = await message_history_service.get_thread_messages(
        db=mock_db,
        thread_id=thread_id,
        max_context_size=1000,
        use_memory_context=True
    )
    
    # Verify results
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Hello world"
    assert "timestamp" in messages[0]
    
    # Verify token counting integration works
    token_count = await token_counter_service.count_message_tokens(messages[0])
    assert token_count > 0
    
@pytest.mark.asyncio
async def test_service_imports_successfully():
    """Test that all services import without errors."""
    from app.services.message_history_service import message_history_service
    from app.services.token_counter_service import token_counter_service
    
    # Test basic functionality
    test_message = {"role": "user", "content": "Test message"}
    token_count = await token_counter_service.count_message_tokens(test_message)
    assert isinstance(token_count, int)
    assert token_count > 0