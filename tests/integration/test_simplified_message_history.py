import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.dynamic_agent_factory import dynamic_agent_factory
from app.services.ai_chat_service import ai_chat_service, MessageFormat
from app.schemas.ai_response import ChatResponse, CustomerSupportContext

@pytest.mark.asyncio
async def test_simplified_message_history_flow():
    """Test simplified message history flow with proper service integration."""
    
    # Create mock agent model
    agent_model = MagicMock()
    agent_model.id = uuid.uuid4()
    agent_model.use_memory_context = True
    agent_model.max_context_size = 1000
    agent_model.max_iterations = 5
    
    thread_id = str(uuid.uuid4())
    
    # Test the integration between dynamic_agent_factory and ai_chat_service
    with patch.object(dynamic_agent_factory, 'create_agent_from_model') as mock_create, \
         patch.object(ai_chat_service, 'get_thread_history') as mock_get_history:
        
        # Mock Pydantic AI agent behavior
        mock_agent = AsyncMock()
        mock_result = MagicMock()
        mock_result.output = ChatResponse(
            content="Based on our conversation history, I can help you with your account.",
            confidence=0.9,
            requires_escalation=False,
            tools_used=[]
        )
        mock_agent.run.return_value = mock_result
        mock_create.return_value = mock_agent
        
        # Mock history retrieval to return ModelMessage objects
        from pydantic_ai.messages import ModelRequest, ModelResponse, UserPromptPart, TextPart
        from pydantic_ai.usage import Usage
        from datetime import datetime, timezone
        
        mock_history = [
            ModelRequest(parts=[UserPromptPart(content="Hello, I need help", timestamp=datetime.now(timezone.utc))]),
            ModelResponse(parts=[TextPart(content="Hi! I'm happy to help. What can I do for you?")], usage=Usage(total_tokens=10), model_name="test-model", timestamp=datetime.now(timezone.utc))
        ]
        mock_get_history.return_value = mock_history
        
        # Process new message with history
        context = CustomerSupportContext(
            user_input="I have a question about my account",
            user_metadata={"user_id": "test_user"}
        )
        
        response = await dynamic_agent_factory.process_message_with_agent(
            agent_model=agent_model,
            message="I have a question about my account",
            context=context,
            thread_id=thread_id
        )
        
        # Verify response
        assert isinstance(response, ChatResponse)
        assert "account" in response.content.lower()
        
        # Verify history service was called correctly
        mock_get_history.assert_called_once_with(
            thread_id=thread_id,
            user_id="test_user",
            agent_id=str(agent_model.id),
            format_type=MessageFormat.MODEL_MESSAGE,
            max_context_size=agent_model.max_context_size,
            use_memory_context=agent_model.use_memory_context
        )
        
        # Verify agent was called with message_history parameter
        mock_agent.run.assert_called_once()
        call_args = mock_agent.run.call_args
        
        # Check if message_history was provided
        assert 'message_history' in call_args.kwargs
        assert len(call_args.kwargs['message_history']) == 2
        assert call_args.kwargs['message_history'] == mock_history

@pytest.mark.asyncio
async def test_memory_disabled_flow():
    """Test flow when memory context is disabled."""
    
    # Create mock agent model with memory disabled
    agent_model = MagicMock()
    agent_model.id = uuid.uuid4()
    agent_model.use_memory_context = False  # Memory disabled
    agent_model.max_context_size = 1000
    agent_model.max_iterations = 3
    
    thread_id = str(uuid.uuid4())
    
    with patch.object(dynamic_agent_factory, 'create_agent_from_model') as mock_create, \
         patch.object(ai_chat_service, 'get_thread_history') as mock_get_history:
        
        mock_agent = AsyncMock()
        mock_result = MagicMock()
        mock_result.output = ChatResponse(
            content="Fresh response without history",
            confidence=0.8,
            requires_escalation=False,
            tools_used=[]
        )
        mock_agent.run.return_value = mock_result
        mock_create.return_value = mock_agent
        
        # History service should return empty list when memory is disabled
        mock_get_history.return_value = []
        
        # Create context
        context = CustomerSupportContext(
            user_input="Hello",
            user_metadata={"user_id": "test_user"}
        )
        
        # Process message
        response = await dynamic_agent_factory.process_message_with_agent(
            agent_model=agent_model,
            message="Hello",
            context=context,
            thread_id=thread_id
        )
        
        # Verify response
        assert isinstance(response, ChatResponse)
        assert "fresh" in response.content.lower()
        
        # Verify agent called without history (since memory is disabled)
        mock_agent.run.assert_called_once()
        call_args = mock_agent.run.call_args
        
        # Should be simple message call without history
        assert call_args.args[0] == "Hello"
        assert 'message_history' not in call_args.kwargs

@pytest.mark.asyncio
async def test_context_limits_applied_integration():
    """Test that context limits work correctly in the integration flow."""
    
    # Create mock agent model with small context size
    agent_model = MagicMock()
    agent_model.id = uuid.uuid4()
    agent_model.use_memory_context = True
    agent_model.max_context_size = 100  # Small context limit for testing
    agent_model.max_iterations = 5
    
    thread_id = str(uuid.uuid4())
    
    # Test that context limits are respected in the integration
    with patch.object(dynamic_agent_factory, 'create_agent_from_model') as mock_create, \
         patch.object(ai_chat_service, 'get_thread_history') as mock_get_history:
        
        mock_agent = AsyncMock()
        mock_result = MagicMock()
        mock_result.output = ChatResponse(
            content="I can see our conversation history but it's been limited by context size.",
            confidence=0.9,
            requires_escalation=False,
            tools_used=[]
        )
        mock_agent.run.return_value = mock_result
        mock_create.return_value = mock_agent
        
        # Mock history to return limited messages (simulating context limiting)
        from pydantic_ai.messages import ModelRequest, UserPromptPart
        from datetime import datetime, timezone
        
        # Return only 3 messages instead of many (simulating context limiting)
        mock_history = [
            ModelRequest(parts=[UserPromptPart(content=f"Message {i}", timestamp=datetime.now(timezone.utc))])
            for i in range(3)  # Only 3 messages due to context limits
        ]
        mock_get_history.return_value = mock_history
        
        # Create context
        context = CustomerSupportContext(
            user_input="What did we discuss earlier?",
            user_metadata={"user_id": "test_user"}
        )
        
        # Process message
        response = await dynamic_agent_factory.process_message_with_agent(
            agent_model=agent_model,
            message="What did we discuss earlier?",
            context=context,
            thread_id=thread_id
        )
        
        # Verify response
        assert isinstance(response, ChatResponse)
        assert "context" in response.content.lower() or "history" in response.content.lower()
        
        # Verify history service was called with context limits
        mock_get_history.assert_called_once_with(
            thread_id=thread_id,
            user_id="test_user",
            agent_id=str(agent_model.id),
            format_type=MessageFormat.MODEL_MESSAGE,
            max_context_size=100,  # Small limit should be passed through
            use_memory_context=True
        )
        
        # Verify agent received limited history
        mock_agent.run.assert_called_once()
        call_args = mock_agent.run.call_args
        assert 'message_history' in call_args.kwargs
        assert len(call_args.kwargs['message_history']) == 3  # Limited by context
        
        # Verify messages are ModelRequest objects (correct format)
        history_messages = call_args.kwargs['message_history']
        assert all(hasattr(msg, 'parts') for msg in history_messages)  # ModelRequest format