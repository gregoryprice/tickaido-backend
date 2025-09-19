import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, UserPromptPart, TextPart
from pydantic_ai.usage import Usage
from datetime import datetime, timezone
from app.services.dynamic_agent_factory import dynamic_agent_factory
from app.services.ai_chat_service import MessageFormat
from app.schemas.ai_response import ChatResponse, CustomerSupportContext

@pytest.mark.asyncio
async def test_process_message_with_history():
    """Test processing message with proper message_history parameter."""
    
    # Mock agent model
    agent_model = MagicMock()
    agent_model.id = uuid.uuid4()
    agent_model.use_memory_context = True
    agent_model.max_context_size = 1000
    agent_model.max_iterations = 5
    
    thread_id = str(uuid.uuid4())
    
    # Mock message history as ModelMessage objects
    mock_history = [
        ModelRequest(parts=[UserPromptPart(content="Previous question", timestamp=datetime.now(timezone.utc))]),
        ModelResponse(parts=[TextPart(content="Previous answer")], usage=Usage(total_tokens=10), model_name="test-model", timestamp=datetime.now(timezone.utc))
    ]
    
    with patch.object(dynamic_agent_factory, 'create_agent_from_model') as mock_create, \
         patch('app.services.ai_chat_service.ai_chat_service') as mock_chat_service:
        
        # Mock Pydantic AI agent
        mock_agent = AsyncMock()
        mock_result = MagicMock()
        mock_result.output = ChatResponse(
            content="Response with context",
            confidence=0.9,
            requires_escalation=False,
            tools_used=[]
        )
        mock_agent.run.return_value = mock_result
        mock_create.return_value = mock_agent
        
        # Mock chat service history method - use correct method name
        mock_chat_service.get_thread_history = AsyncMock(return_value=mock_history)
        
        # Create context with user metadata
        context = CustomerSupportContext(
            user_input="Follow up question",
            user_metadata={"user_id": "test_user"}
        )
        
        # Process message
        response = await dynamic_agent_factory.process_message_with_agent(
            agent_model=agent_model,
            message="Follow up question",
            context=context,
            thread_id=thread_id
        )
        
        # Verify correct message_history parameter usage
        mock_agent.run.assert_called_once()
        call_args = mock_agent.run.call_args
        
        # Should be called with message_history parameter
        assert 'message_history' in call_args.kwargs
        assert call_args.kwargs['message_history'] == mock_history
        assert response.content == "Response with context"

@pytest.mark.asyncio 
async def test_process_message_without_history():
    """Test processing message without history (new conversation)."""
    
    agent_model = MagicMock()
    agent_model.id = uuid.uuid4()
    agent_model.use_memory_context = True
    agent_model.max_iterations = 5
    
    with patch.object(dynamic_agent_factory, 'create_agent_from_model') as mock_create, \
         patch('app.services.ai_chat_service.ai_chat_service') as mock_chat_service:
        
        mock_agent = AsyncMock()
        mock_result = MagicMock()
        mock_result.output = ChatResponse(
            content="Fresh conversation",
            confidence=0.9,
            requires_escalation=False,
            tools_used=[]
        )
        mock_agent.run.return_value = mock_result
        mock_create.return_value = mock_agent
        
        # Mock empty history
        mock_chat_service.get_thread_history = AsyncMock(return_value=[])
        
        # Process without thread_id (no history)
        context = CustomerSupportContext(user_input="Hello", user_metadata={"user_id": "test_user"})
        response = await dynamic_agent_factory.process_message_with_agent(
            agent_model=agent_model,
            message="Hello",
            context=context,
            thread_id=None
        )
        
        # Should call run without message_history
        mock_agent.run.assert_called_once()
        call_args = mock_agent.run.call_args
        
        # Should be simple message call without history
        assert call_args.args[0] == "Hello"
        assert 'message_history' not in call_args.kwargs
        
@pytest.mark.asyncio
async def test_memory_context_disabled():
    """Test that memory context can be disabled per agent."""
    
    agent_model = MagicMock()
    agent_model.id = uuid.uuid4()
    agent_model.use_memory_context = False  # Memory disabled
    agent_model.max_iterations = 5
    
    thread_id = str(uuid.uuid4())
    
    with patch.object(dynamic_agent_factory, 'create_agent_from_model') as mock_create, \
         patch('app.services.ai_chat_service.ai_chat_service') as mock_chat_service:
        
        mock_agent = AsyncMock()
        mock_result = MagicMock()
        mock_result.output = ChatResponse(
            content="No memory response",
            confidence=0.9,
            requires_escalation=False,
            tools_used=[]
        )
        mock_agent.run.return_value = mock_result
        mock_create.return_value = mock_agent
        
        context = CustomerSupportContext(user_input="Hello", user_metadata={"user_id": "test_user"})
        await dynamic_agent_factory.process_message_with_agent(
            agent_model=agent_model,
            message="Hello",
            context=context,
            thread_id=thread_id
        )
        
        # History service should not be called when memory is disabled
        mock_chat_service.get_thread_history.assert_not_called()

@pytest.mark.asyncio
async def test_process_message_history_service_error():
    """Test handling when message history service fails."""
    
    agent_model = MagicMock()
    agent_model.id = uuid.uuid4()
    agent_model.use_memory_context = True
    agent_model.max_context_size = 1000
    agent_model.max_iterations = 5
    
    thread_id = str(uuid.uuid4())
    
    with patch.object(dynamic_agent_factory, 'create_agent_from_model') as mock_create, \
         patch('app.services.ai_chat_service.ai_chat_service') as mock_chat_service:
        
        # Mock Pydantic AI agent
        mock_agent = AsyncMock()
        mock_result = MagicMock()
        mock_result.output = ChatResponse(
            content="Response without history due to error",
            confidence=0.8,
            requires_escalation=False,
            tools_used=[]
        )
        mock_agent.run.return_value = mock_result
        mock_create.return_value = mock_agent
        
        # Mock chat service to raise exception
        mock_chat_service.get_thread_history = AsyncMock(side_effect=Exception("Database error"))
        
        # Create context
        context = CustomerSupportContext(
            user_input="Hello",
            user_metadata={"user_id": "test_user"}
        )
        
        # Process message - should handle error gracefully
        response = await dynamic_agent_factory.process_message_with_agent(
            agent_model=agent_model,
            message="Hello",
            context=context,
            thread_id=thread_id
        )
        
        # Should still get a response, just without history
        assert isinstance(response, ChatResponse)
        
        # Should call run without message_history due to error
        mock_agent.run.assert_called_once()
        call_args = mock_agent.run.call_args
        assert call_args.args[0] == "Hello"
        assert 'message_history' not in call_args.kwargs

@pytest.mark.asyncio
async def test_process_message_with_context_user_id():
    """Test that user_id is properly extracted from context."""
    
    agent_model = MagicMock()
    agent_model.id = uuid.uuid4()
    agent_model.use_memory_context = True
    agent_model.max_context_size = 1000
    agent_model.max_iterations = 5
    
    thread_id = str(uuid.uuid4())
    test_user_id = "specific_test_user"
    
    with patch.object(dynamic_agent_factory, 'create_agent_from_model') as mock_create, \
         patch('app.services.ai_chat_service.ai_chat_service') as mock_chat_service:
        
        mock_agent = AsyncMock()
        mock_result = MagicMock()
        mock_result.output = ChatResponse(
            content="Response",
            confidence=0.9,
            requires_escalation=False,
            tools_used=[]
        )
        mock_agent.run.return_value = mock_result
        mock_create.return_value = mock_agent
        
        mock_chat_service.get_thread_history = AsyncMock(return_value=[])
        
        # Create context with specific user_id
        context = CustomerSupportContext(
            user_input="Hello",
            user_metadata={"user_id": test_user_id}
        )
        
        # Process message
        await dynamic_agent_factory.process_message_with_agent(
            agent_model=agent_model,
            message="Hello",
            context=context,
            thread_id=thread_id
        )
        
        # Verify the correct user_id was passed to get_thread_history
        mock_chat_service.get_thread_history.assert_called_once_with(
            thread_id=thread_id,
            user_id=test_user_id,  # Should use the specific user_id from context
            agent_id=str(agent_model.id),
            format_type=MessageFormat.MODEL_MESSAGE,
            max_context_size=agent_model.max_context_size,
            use_memory_context=agent_model.use_memory_context
        )

@pytest.mark.asyncio
async def test_process_message_fallback_user_id():
    """Test fallback user_id when not provided in context."""
    
    agent_model = MagicMock()
    agent_model.id = uuid.uuid4()
    agent_model.use_memory_context = True
    agent_model.max_iterations = 5
    
    thread_id = str(uuid.uuid4())
    
    with patch.object(dynamic_agent_factory, 'create_agent_from_model') as mock_create, \
         patch('app.services.ai_chat_service.ai_chat_service') as mock_chat_service:
        
        mock_agent = AsyncMock()
        mock_result = MagicMock()
        mock_result.output = ChatResponse(content="Response", confidence=0.9, requires_escalation=False, tools_used=[])
        mock_agent.run.return_value = mock_result
        mock_create.return_value = mock_agent
        
        mock_chat_service.get_thread_history = AsyncMock(return_value=[])
        
        # Create context without user_id in metadata
        context = CustomerSupportContext(
            user_input="Hello",
            user_metadata={}  # No user_id
        )
        
        # Process message
        await dynamic_agent_factory.process_message_with_agent(
            agent_model=agent_model,
            message="Hello",
            context=context,
            thread_id=thread_id
        )
        
        # Verify fallback user_id 'system' was used
        mock_chat_service.get_thread_history.assert_called_once()
        call_args = mock_chat_service.get_thread_history.call_args
        assert call_args.kwargs['user_id'] == 'system'