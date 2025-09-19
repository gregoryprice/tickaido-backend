import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, UserPromptPart, TextPart
from pydantic_ai.usage import Usage

from app.models.chat import Thread, Message
from app.models.ai_agent import Agent
from app.models.organization import Organization
from app.services.dynamic_agent_factory import dynamic_agent_factory
from app.services.ai_chat_service import ai_chat_service
from app.services.message_converter_service import message_converter_service
from app.schemas.ai_response import ChatResponse, CustomerSupportContext

@pytest.mark.asyncio
async def test_message_converter_integration():
    """Test ModelMessage conversion with real Message objects."""
    
    # Create mock database messages that simulate real Message objects
    user_msg = MagicMock()
    user_msg.role = "user"
    user_msg.content = "Hello, can you help me?"
    user_msg.created_at = datetime.now(timezone.utc)
    
    assistant_msg = MagicMock()
    assistant_msg.role = "assistant"
    assistant_msg.content = "Of course! I'm here to help. What do you need assistance with?"
    assistant_msg.created_at = datetime.now(timezone.utc)
    
    db_messages = [user_msg, assistant_msg]
    
    # Test conversion to ModelMessage format
    model_messages = await message_converter_service.convert_db_messages_to_model_messages(db_messages)
    
    # Verify proper conversion
    assert len(model_messages) == 2
    assert isinstance(model_messages[0], ModelRequest)
    assert isinstance(model_messages[1], ModelResponse)
    
    # Verify content is preserved
    assert model_messages[0].parts[0].content == "Hello, can you help me?"
    assert model_messages[1].parts[0].content == "Of course! I'm here to help. What do you need assistance with?"
    
    # Test serialization round-trip
    json_string = await message_converter_service.serialize_model_messages_to_json(model_messages)
    assert isinstance(json_string, str)
    assert len(json_string) > 0
    
    # Test deserialization
    deserialized = await message_converter_service.deserialize_json_to_model_messages(json_string)
    assert len(deserialized) == 2
    assert isinstance(deserialized[0], ModelRequest)
    assert isinstance(deserialized[1], ModelResponse)
    
    # Verify content is preserved through serialization
    assert deserialized[0].parts[0].content == "Hello, can you help me?"
    assert deserialized[1].parts[0].content == "Of course! I'm here to help. What do you need assistance with?"

@pytest.mark.asyncio
async def test_model_message_format_validation():
    """Test that ModelMessage format meets Pydantic AI requirements."""
    
    # Create ModelMessages in the format Pydantic AI expects
    user_request = ModelRequest(
        parts=[
            UserPromptPart(
                content="What can you do?",
                timestamp=datetime.now(timezone.utc)
            )
        ]
    )
    
    assistant_response = ModelResponse(
        parts=[
            TextPart(content="I can help with various tasks including...")
        ],
        usage=Usage(total_tokens=25, details=None),
        model_name="gpt-4o-mini",
        timestamp=datetime.now(timezone.utc)
    )
    
    model_messages = [user_request, assistant_response]
    
    # Test that this format can be serialized and used with Pydantic AI
    from app.services.message_converter_service import ModelMessagesTypeAdapter
    
    # This should work without errors - validates the format is correct
    serialized = await message_converter_service.serialize_model_messages_to_json(model_messages)
    deserialized = await message_converter_service.deserialize_json_to_model_messages(serialized)
    
    assert len(deserialized) == 2
    assert isinstance(deserialized[0], ModelRequest)
    assert isinstance(deserialized[1], ModelResponse)

@pytest.mark.asyncio
async def test_dynamic_agent_factory_model_message_integration():
    """Test complete Dynamic Agent Factory integration with ModelMessages."""
    
    # This test verifies the complete flow but uses mocks
    # since we need to avoid real database/agent calls
    
    agent_model = MagicMock()
    agent_model.id = uuid.uuid4()
    agent_model.use_memory_context = True
    agent_model.max_context_size = 1000
    agent_model.max_iterations = 5
    
    # Mock the complete chain: AI Chat Service -> Message Converter -> Dynamic Agent Factory
    mock_model_messages = [
        ModelRequest(parts=[UserPromptPart(content="Previous message", timestamp=datetime.now(timezone.utc))])
    ]
    
    with patch.object(dynamic_agent_factory, 'create_agent_from_model') as mock_create, \
         patch('app.services.ai_chat_service.ai_chat_service') as mock_chat_service:
        
        # Mock Pydantic AI agent
        mock_agent = AsyncMock()
        mock_result = MagicMock()
        mock_result.output = ChatResponse(content="Integration test response", confidence=0.9, requires_escalation=False, tools_used=[])
        mock_result.all_messages.return_value = mock_model_messages
        mock_agent.run.return_value = mock_result
        mock_create.return_value = mock_agent
        
        # Mock AI Chat Service to return ModelMessage format
        mock_chat_service.get_thread_history = AsyncMock(return_value=mock_model_messages)
        
        # Test the integration
        context = CustomerSupportContext(
            user_input="Test message",
            user_metadata={"user_id": "integration_test_user"}
        )
        
        response = await dynamic_agent_factory.process_message_with_agent(
            agent_model=agent_model,
            message="Test message",
            context=context,
            thread_id="integration_test_thread"
        )
        
        # Verify the complete chain worked
        assert isinstance(response, ChatResponse)
        assert response.content == "Integration test response"
        
        # Verify ModelMessage format was passed to agent
        mock_agent.run.assert_called_once()
        call_args = mock_agent.run.call_args
        assert 'message_history' in call_args.kwargs
        assert isinstance(call_args.kwargs['message_history'][0], ModelRequest)