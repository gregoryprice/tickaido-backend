import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, UserPromptPart, TextPart
from pydantic_ai.usage import Usage
from app.services.dynamic_agent_factory import dynamic_agent_factory
from app.services.ai_chat_service import MessageFormat
from app.schemas.ai_response import ChatResponse, CustomerSupportContext

@pytest.mark.asyncio
async def test_process_message_with_model_message_history():
    """Test processing message with proper ModelMessage format."""
    
    # Mock agent model
    agent_model = MagicMock()
    agent_model.id = uuid.uuid4()
    agent_model.use_memory_context = True
    agent_model.max_context_size = 1000
    agent_model.max_iterations = 5
    
    thread_id = str(uuid.uuid4())
    
    # Mock ModelMessage history
    mock_model_request = ModelRequest(
        parts=[UserPromptPart(content="Previous question", timestamp=datetime.now(timezone.utc))]
    )
    mock_model_response = ModelResponse(
        parts=[TextPart(content="Previous answer")],
        usage=Usage(total_tokens=20, details=None),
        model_name="gpt-4o-mini",
        timestamp=datetime.now(timezone.utc)
    )
    mock_history = [mock_model_request, mock_model_response]
    
    with patch.object(dynamic_agent_factory, 'create_agent_from_model') as mock_create, \
         patch('app.services.ai_chat_service.ai_chat_service') as mock_chat_service:
        
        # Mock Pydantic AI agent
        mock_agent = AsyncMock()
        mock_result = MagicMock()
        mock_result.output = ChatResponse(
            content="Response with ModelMessage context",
            confidence=0.9,
            requires_escalation=False,
            tools_used=[]
        )
        mock_result.all_messages.return_value = [mock_model_request, mock_model_response]
        mock_agent.run.return_value = mock_result
        mock_create.return_value = mock_agent
        
        # Mock chat service to return ModelMessage format
        mock_chat_service.get_thread_history = AsyncMock(return_value=mock_history)
        
        # Create context
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
        
        # Verify ModelMessage format was used
        mock_agent.run.assert_called_once()
        call_args = mock_agent.run.call_args
        
        # Should be called with ModelMessage history
        assert 'message_history' in call_args.kwargs
        history_param = call_args.kwargs['message_history']
        assert len(history_param) == 2
        assert isinstance(history_param[0], ModelRequest)
        assert isinstance(history_param[1], ModelResponse)
        assert response.content == "Response with ModelMessage context"

@pytest.mark.asyncio
async def test_process_message_without_model_message_history():
    """Test processing message without history using ModelMessage format."""
    
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
        
        # Mock empty ModelMessage history
        mock_chat_service.get_thread_history = AsyncMock(return_value=[])
        
        # Process without thread_id (no history)
        context = CustomerSupportContext(
            user_input="Hello",
            user_metadata={"user_id": "test_user"}
        )
        
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
async def test_memory_context_disabled_with_model_messages():
    """Test that memory context can be disabled with ModelMessage format."""
    
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
        
        context = CustomerSupportContext(
            user_input="Hello",
            user_metadata={"user_id": "test_user"}
        )
        
        await dynamic_agent_factory.process_message_with_agent(
            agent_model=agent_model,
            message="Hello",
            context=context,
            thread_id=thread_id
        )
        
        # ModelMessage history service should not be called when memory is disabled
        mock_chat_service.get_thread_history.assert_not_called()

@pytest.mark.asyncio
async def test_model_message_conversion_error_handling():
    """Test handling when ModelMessage conversion fails."""
    
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
            content="Response without ModelMessage history due to error",
            confidence=0.8,
            requires_escalation=False,
            tools_used=[]
        )
        mock_agent.run.return_value = mock_result
        mock_create.return_value = mock_agent
        
        # Mock chat service to raise exception
        mock_chat_service.get_thread_history = AsyncMock(
            side_effect=Exception("ModelMessage conversion error")
        )
        
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
        
        # Should still get a response, just without ModelMessage history
        assert isinstance(response, ChatResponse)
        
        # Should call run without message_history due to error
        mock_agent.run.assert_called_once()
        call_args = mock_agent.run.call_args
        assert call_args.args[0] == "Hello"
        assert 'message_history' not in call_args.kwargs

@pytest.mark.asyncio
async def test_model_message_user_id_extraction():
    """Test that user_id is properly extracted for ModelMessage retrieval."""
    
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