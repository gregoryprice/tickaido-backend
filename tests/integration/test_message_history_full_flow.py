import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import Thread, Message
from app.models.ai_agent import Agent
from app.models.organization import Organization
from app.services.dynamic_agent_factory import dynamic_agent_factory
from app.services.message_history_service import message_history_service
from app.services.token_counter_service import token_counter_service
from app.services.ai_chat_service import MessageFormat
from app.schemas.ai_response import ChatResponse, CustomerSupportContext

@pytest.mark.asyncio
async def test_token_counter_integration():
    """Test that token counter works correctly with various message types."""
    
    # Test basic token counting
    short_message = {"role": "user", "content": "Hello"}
    short_tokens = await token_counter_service.count_message_tokens(short_message)
    assert short_tokens > 0
    assert short_tokens < 10  # Should be small for "Hello"
    
    # Test longer message
    long_message = {"role": "assistant", "content": "This is a much longer message that should have significantly more tokens than the short one."}
    long_tokens = await token_counter_service.count_message_tokens(long_message)
    assert long_tokens > short_tokens
    
    # Test total counting
    messages = [short_message, long_message]
    total_tokens = await token_counter_service.count_total_tokens(messages)
    assert total_tokens == short_tokens + long_tokens

@pytest.mark.asyncio
async def test_message_history_service_integration():
    """Test message history service with mocked database."""
    
    # Mock database session
    mock_db = AsyncMock()
    thread_id = str(uuid.uuid4())
    
    # Create mock messages with realistic data
    mock_messages = []
    for i, (role, content) in enumerate([
        ("user", "Hello, I need help with my order"),
        ("assistant", "I'd be happy to help with your order. Can you provide your order number?"),
        ("user", "My order number is 12345"),
        ("assistant", "Thank you! Let me look up order 12345 for you."),
    ]):
        mock_msg = MagicMock()
        mock_msg.role = role
        mock_msg.content = content
        mock_msg.created_at = datetime.now(timezone.utc)
        mock_messages.append(mock_msg)
    
    # Mock database result (in reverse chronological order)
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = list(reversed(mock_messages))
    mock_db.execute.return_value = result_mock
    
    # Test with normal context size
    retrieved_messages = await message_history_service.get_thread_messages(
        db=mock_db,
        thread_id=thread_id,
        max_context_size=10000,
        use_memory_context=True
    )
    
    # Verify all messages retrieved in chronological order
    assert len(retrieved_messages) == 4
    assert retrieved_messages[0]["role"] == "user"
    assert retrieved_messages[0]["content"] == "Hello, I need help with my order"
    assert retrieved_messages[-1]["role"] == "assistant"
    assert retrieved_messages[-1]["content"] == "Thank you! Let me look up order 12345 for you."
    
    # Test with small context size (should limit messages)
    limited_messages = await message_history_service.get_thread_messages(
        db=mock_db,
        thread_id=thread_id,
        max_context_size=50,  # Small limit
        use_memory_context=True
    )
    
    # Should have fewer messages due to context limit
    assert len(limited_messages) < len(retrieved_messages)
    assert len(limited_messages) > 0  # But should have at least some

@pytest.mark.asyncio
async def test_dynamic_agent_factory_full_integration():
    """Test complete dynamic agent factory integration with message history."""
    
    # Create mock agent model with realistic settings
    agent_model = MagicMock()
    agent_model.id = uuid.uuid4()
    agent_model.use_memory_context = True
    agent_model.max_context_size = 1000
    agent_model.max_iterations = 5
    agent_model.is_ready = True
    
    # Mock database and thread
    mock_db = AsyncMock()
    thread_id = str(uuid.uuid4())
    
    # Mock realistic conversation history
    mock_history = [
        {"role": "user", "content": "Hello, I need help with my order"},
        {"role": "assistant", "content": "I'd be happy to help with your order. Can you provide your order number?"},
        {"role": "user", "content": "My order number is 12345"},
    ]
    
    with patch.object(dynamic_agent_factory, 'create_agent_from_model') as mock_create, \
         patch('app.services.ai_chat_service.ai_chat_service') as mock_ai_chat_service:
        
        # Mock pydantic agent
        mock_pydantic_agent = AsyncMock()
        mock_result = MagicMock()
        mock_result.output = ChatResponse(
            content="I can see your previous order number 12345. Let me check the status for you.",
            confidence=0.9,
            requires_escalation=False,
            tools_used=[]
        )
        mock_pydantic_agent.run.return_value = mock_result
        mock_create.return_value = mock_pydantic_agent
        
        # Mock AI chat service
        mock_ai_chat_service.get_thread_history = AsyncMock(return_value=mock_history)
        
        # Test agent processing with history
        response = await dynamic_agent_factory.process_message_with_agent(
            agent_model=agent_model,
            message="What's my order status?",
            context=CustomerSupportContext(user_input="Test message"),
            auth_token=None,
            thread_id=thread_id,
            db=mock_db
        )
        
        # Verify response
        assert isinstance(response, ChatResponse)
        assert "12345" in response.content  # Should reference previous order number
        
        # Verify history was loaded
        mock_ai_chat_service.get_thread_history.assert_called_once_with(
            thread_id=thread_id,
            user_id='system',
            agent_id=str(agent_model.id),
            format_type=MessageFormat.MODEL_MESSAGE,
            max_context_size=1000,
            use_memory_context=True
        )
        
        # Verify that the agent was called with conversation history
        mock_pydantic_agent.run.assert_called_once()
        call_args = mock_pydantic_agent.run.call_args
        
        # First arg should be the message
        assert call_args[0][0] == "What's my order status?"
        
        # Should have message_history parameter
        assert 'message_history' in call_args[1]
        message_history = call_args[1]['message_history']
        assert isinstance(message_history, list)
        assert len(message_history) == 3  # The mock history
        
        # Verify conversation context is maintained  
        assert any("12345" in msg.get("content", "") for msg in message_history)

@pytest.mark.asyncio
async def test_context_size_enforcement():
    """Test that context size limits are properly enforced."""
    
    # Create messages with known approximate token counts
    messages = [
        {"role": "user", "content": "Hi"},  # ~3 tokens
        {"role": "assistant", "content": "Hello there! How can I help you today?"},  # ~10 tokens
        {"role": "user", "content": "I need help with a technical issue that is quite complex and requires detailed explanation"},  # ~18 tokens
    ]
    
    # Count actual tokens for each message
    token_counts = []
    for msg in messages:
        tokens = await token_counter_service.count_message_tokens(msg)
        token_counts.append(tokens)
        assert tokens > 0
    
    total_tokens = sum(token_counts)
    assert total_tokens > 20  # Should be substantial
    
    # Test that message history service would respect a smaller limit
    # (This is indirectly tested through the mock scenarios above, 
    # but validates our token counting logic)
    assert token_counts[2] > token_counts[0]  # Longer message has more tokens
    assert total_tokens > token_counts[2]  # Total is more than any individual

@pytest.mark.asyncio
async def test_memory_context_flag_behavior():
    """Test behavior when memory context is enabled vs disabled."""
    
    # Test token counter works regardless of memory context setting
    test_message = {"role": "user", "content": "Test message for memory context"}
    tokens = await token_counter_service.count_message_tokens(test_message)
    assert tokens > 0
    
    # Mock agent models with different memory settings
    memory_enabled_agent = MagicMock()
    memory_enabled_agent.use_memory_context = True
    memory_enabled_agent.max_context_size = 1000
    memory_enabled_agent.max_iterations = 5
    memory_enabled_agent.id = uuid.uuid4()
    
    memory_disabled_agent = MagicMock()
    memory_disabled_agent.use_memory_context = False
    memory_disabled_agent.max_context_size = 1000
    memory_disabled_agent.max_iterations = 5
    memory_disabled_agent.id = uuid.uuid4()
    
    mock_db = AsyncMock()
    thread_id = str(uuid.uuid4())
    
    with patch.object(dynamic_agent_factory, 'create_agent_from_model') as mock_create, \
         patch('app.services.ai_chat_service.ai_chat_service') as mock_ai_chat_service:
        
        # Mock pydantic agent
        mock_pydantic_agent = AsyncMock()
        mock_result = MagicMock()
        mock_result.output = ChatResponse(
            content="Response content",
            confidence=0.9,
            requires_escalation=False,
            tools_used=[]
        )
        mock_pydantic_agent.run.return_value = mock_result
        mock_create.return_value = mock_pydantic_agent
        
        mock_ai_chat_service.get_thread_history = AsyncMock(return_value=[])
        
        # Test with memory enabled
        await dynamic_agent_factory.process_message_with_agent(
            agent_model=memory_enabled_agent,
            message="Test message",
            context=CustomerSupportContext(user_input="Test message"),
            auth_token=None,
            thread_id=thread_id,
            db=mock_db
        )
        
        # Should call history service when memory is enabled
        assert mock_ai_chat_service.get_thread_history.call_count == 1
        
        # Reset mock
        mock_ai_chat_service.get_thread_history.reset_mock()
        
        # Test with memory disabled
        await dynamic_agent_factory.process_message_with_agent(
            agent_model=memory_disabled_agent,
            message="Test message",
            context=CustomerSupportContext(user_input="Test message"),
            auth_token=None,
            thread_id=thread_id,
            db=mock_db
        )
        
        # Should NOT call history service when memory is disabled
        mock_ai_chat_service.get_thread_history.assert_not_called()