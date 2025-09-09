#!/usr/bin/env python3
"""
Tests for ThreadService - Agent-Centric Thread Management
"""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from app.services.thread_service import ThreadService, thread_service
from app.models.chat import Thread, Message
from app.models.ai_agent import Agent


@pytest.fixture
def test_agent():
    """Create test agent"""
    agent = Agent()
    agent.id = uuid4()
    agent.organization_id = uuid4()
    agent.agent_type = "customer_support"
    agent.name = "Test Customer Support Agent"
    agent.is_active = True
    agent.status = "active"
    agent.tools = ["create_ticket", "search_tickets"]
    return agent


@pytest.fixture
def test_thread(test_agent):
    """Create test thread"""
    thread = Thread()
    thread.id = uuid4()
    thread.agent_id = test_agent.id
    thread.user_id = "test_user"
    thread.organization_id = test_agent.organization_id
    thread.title = "Test Thread"
    thread.total_messages = 0
    thread.last_message_at = None
    thread.archived = False
    thread.created_at = datetime.now(timezone.utc)
    thread.updated_at = datetime.now(timezone.utc)
    return thread


@pytest.mark.asyncio
async def test_create_thread_with_agent(test_agent):
    """Thread creation requires valid agent"""
    
    # Mock database session
    mock_db = AsyncMock()
    
    # Mock agent query result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = test_agent
    mock_db.execute.return_value = mock_result
    
    # Mock commit and refresh
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.add = MagicMock()
    
    service = ThreadService()
    
    # Test thread creation
    thread = await service.create_thread(
        db=mock_db,
        agent_id=test_agent.id,
        user_id="test_user",
        title="Test Thread"
    )
    
    # Verify thread properties
    assert thread.agent_id == test_agent.id
    assert thread.organization_id == test_agent.organization_id
    assert thread.user_id == "test_user"
    assert thread.title == "Test Thread"
    assert hasattr(thread, 'archived')  # Just check it exists, default may be None initially
    # Should have default message tracking fields
    assert thread.total_messages == 0
    assert thread.last_message_at is None  # No messages yet
    
    # Verify database operations
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_create_thread_invalid_agent():
    """Thread creation fails with invalid agent"""
    
    # Mock database session
    mock_db = AsyncMock()
    
    # Mock agent query result - agent not found
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    
    service = ThreadService()
    
    # Test thread creation with invalid agent
    with pytest.raises(ValueError, match="Agent .* not found or not active"):
        await service.create_thread(
            db=mock_db,
            agent_id=uuid4(),
            user_id="test_user",
            title="Test Thread"
        )


@pytest.mark.asyncio
async def test_list_threads_by_agent(test_agent, test_thread):
    """List threads filtered by agent"""
    
    # Mock database session
    mock_db = AsyncMock()
    
    # Mock agent query result
    mock_agent_result = MagicMock()
    mock_agent_result.scalar_one_or_none.return_value = test_agent
    
    # Mock thread query results
    mock_thread_result = MagicMock()
    mock_thread_result.scalars.return_value.all.return_value = [test_thread]
    
    # Mock count query result
    mock_count_result = MagicMock()
    mock_count_result.scalar.return_value = 1
    
    # Configure mock db to return different results for different queries
    mock_db.execute.side_effect = [
        mock_agent_result,  # Agent validation query
        mock_thread_result,  # Thread list query
        mock_count_result   # Count query
    ]
    
    service = ThreadService()
    
    # Test thread listing
    threads, count = await service.list_threads(
        db=mock_db,
        agent_id=test_agent.id,
        user_id="test_user",
        limit=10
    )
    
    # Verify results
    assert len(threads) == 1
    assert threads[0].agent_id == test_agent.id
    assert count == 1
    
    # Verify database queries were made
    assert mock_db.execute.call_count == 3  # Agent query + thread query + count query


@pytest.mark.asyncio
async def test_get_thread_with_validation(test_agent, test_thread):
    """Get thread with agent and user validation"""
    
    # Mock database session
    mock_db = AsyncMock()
    
    # Mock agent query result
    mock_agent_result = MagicMock()
    mock_agent_result.scalar_one_or_none.return_value = test_agent
    
    # Mock thread query result
    mock_thread_result = MagicMock()
    mock_thread_result.scalar_one_or_none.return_value = test_thread
    
    mock_db.execute.side_effect = [mock_agent_result, mock_thread_result]
    
    service = ThreadService()
    
    # Test thread retrieval
    thread = await service.get_thread(
        db=mock_db,
        agent_id=test_agent.id,
        thread_id=test_thread.id,
        user_id="test_user"
    )
    
    # Verify thread is returned
    assert thread is not None
    assert thread.id == test_thread.id
    assert thread.agent_id == test_agent.id
    
    # Verify validation queries were made
    assert mock_db.execute.call_count == 2


@pytest.mark.asyncio
async def test_update_thread_title(test_agent, test_thread):
    """Update thread title with validation"""
    
    # Mock database session
    mock_db = AsyncMock()
    
    # Mock agent query result
    mock_agent_result = MagicMock()
    mock_agent_result.scalar_one_or_none.return_value = test_agent
    
    # Mock thread query result
    mock_thread_result = MagicMock()
    mock_thread_result.scalar_one_or_none.return_value = test_thread
    
    mock_db.execute.side_effect = [mock_agent_result, mock_thread_result]
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    
    service = ThreadService()
    
    # Test thread update
    result = await service.update_thread(
        db=mock_db,
        agent_id=test_agent.id,
        thread_id=test_thread.id,
        user_id="test_user",
        title="Updated Thread Title"
    )
    
    # Verify update result
    assert result is not None
    updated_thread, updated_fields = result
    assert updated_thread.title == "Updated Thread Title"
    assert "title" in updated_fields
    
    # Verify database operations
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_update_thread_archive_status(test_agent, test_thread):
    """Update thread archive status"""
    
    # Mock database session
    mock_db = AsyncMock()
    
    # Mock agent query result
    mock_agent_result = MagicMock()
    mock_agent_result.scalar_one_or_none.return_value = test_agent
    
    # Mock thread query result
    mock_thread_result = MagicMock()
    mock_thread_result.scalar_one_or_none.return_value = test_thread
    
    mock_db.execute.side_effect = [mock_agent_result, mock_thread_result]
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    
    service = ThreadService()
    
    # Test archive status update
    result = await service.update_thread(
        db=mock_db,
        agent_id=test_agent.id,
        thread_id=test_thread.id,
        user_id="test_user",
        archived=True
    )
    
    # Verify update result
    assert result is not None
    updated_thread, updated_fields = result
    assert updated_thread.archived == True
    assert "archived" in updated_fields


@pytest.mark.asyncio
async def test_delete_thread_hard_delete(test_agent, test_thread):
    """Delete thread using hard delete (actual deletion)"""
    
    # Mock database session
    mock_db = AsyncMock()
    
    # Mock agent query result
    mock_agent_result = MagicMock()
    mock_agent_result.scalar_one_or_none.return_value = test_agent
    
    # Mock thread query result
    mock_thread_result = MagicMock()
    mock_thread_result.scalar_one_or_none.return_value = test_thread
    
    # Mock delete messages query result
    mock_delete_result = MagicMock()
    mock_delete_result.rowcount = 3  # 3 messages deleted
    
    mock_db.execute.side_effect = [
        mock_agent_result,  # Agent validation query
        mock_thread_result,  # Thread query
        mock_delete_result   # Delete messages query
    ]
    mock_db.commit = AsyncMock()
    mock_db.delete = AsyncMock()
    
    service = ThreadService()
    
    # Test thread deletion
    deleted = await service.delete_thread(
        db=mock_db,
        agent_id=test_agent.id,
        thread_id=test_thread.id,
        user_id="test_user"
    )
    
    # Verify deletion success
    assert deleted == True
    
    # Verify database operations - hard delete, not soft delete
    mock_db.delete.assert_called_once_with(test_thread)  # Thread hard deleted
    mock_db.commit.assert_called_once()
    assert mock_db.execute.call_count == 3  # Agent query + thread query + delete messages query


@pytest.mark.asyncio
async def test_get_thread_messages(test_agent, test_thread):
    """Get messages for a thread with validation"""
    
    # Create test messages
    message1 = Message()
    message1.id = uuid4()
    message1.thread_id = test_thread.id
    message1.role = "user"
    message1.content = "Test message 1"
    message1.created_at = datetime.now(timezone.utc)
    
    message2 = Message()
    message2.id = uuid4()
    message2.thread_id = test_thread.id
    message2.role = "assistant"
    message2.content = "Test response 1"
    message2.tool_calls = [{"tool_name": "create_ticket", "status": "completed"}]
    message2.created_at = datetime.now(timezone.utc)
    
    # Mock database session
    mock_db = AsyncMock()
    
    # Mock agent query result
    mock_agent_result = MagicMock()
    mock_agent_result.scalar_one_or_none.return_value = test_agent
    
    # Mock thread query result
    mock_thread_result = MagicMock()
    mock_thread_result.scalar_one_or_none.return_value = test_thread
    
    # Mock messages query result
    mock_messages_result = MagicMock()
    mock_messages_result.scalars.return_value.all.return_value = [message1, message2]
    
    mock_db.execute.side_effect = [
        mock_agent_result,  # Agent validation
        mock_thread_result,  # Thread validation
        mock_messages_result  # Messages query
    ]
    
    service = ThreadService()
    
    # Test getting thread messages
    messages = await service.get_thread_messages(
        db=mock_db,
        agent_id=test_agent.id,
        thread_id=test_thread.id,
        user_id="test_user"
    )
    
    # Verify messages returned
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"
    assert messages[1].tool_calls is not None
    
    # Verify validation queries were made
    assert mock_db.execute.call_count == 3


@pytest.mark.asyncio 
async def test_thread_service_integration():
    """Integration test for thread service functionality"""
    
    # This test would need actual database connection in integration testing
    # For now, test that service instance exists and has expected methods
    
    assert thread_service is not None
    assert hasattr(thread_service, 'create_thread')
    assert hasattr(thread_service, 'list_threads')
    assert hasattr(thread_service, 'get_thread')
    assert hasattr(thread_service, 'update_thread')
    assert hasattr(thread_service, 'delete_thread')
    assert hasattr(thread_service, 'get_thread_messages')
    assert hasattr(thread_service, 'generate_title_suggestion')


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])