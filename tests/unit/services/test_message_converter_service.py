import pytest
import uuid
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, UserPromptPart, TextPart
from pydantic_ai.usage import Usage
from pydantic_core import to_jsonable_python
from app.services.message_converter_service import message_converter_service, ModelMessagesTypeAdapter
from app.models.chat import Message

@pytest.mark.asyncio
async def test_convert_db_messages_to_model_messages():
    """Test converting database messages to ModelMessage format."""
    
    # Create mock database messages
    user_msg = MagicMock()
    user_msg.role = "user"
    user_msg.content = "Hello, how are you?"
    user_msg.created_at = datetime.now(timezone.utc)
    
    assistant_msg = MagicMock()
    assistant_msg.role = "assistant"  
    assistant_msg.content = "I'm doing well, thanks for asking!"
    assistant_msg.created_at = datetime.now(timezone.utc)
    
    db_messages = [user_msg, assistant_msg]
    
    # Convert to ModelMessage format
    model_messages = await message_converter_service.convert_db_messages_to_model_messages(db_messages)
    
    # Verify results
    assert len(model_messages) == 2
    assert isinstance(model_messages[0], ModelRequest)
    assert isinstance(model_messages[1], ModelResponse)
    
    # Check user message
    user_part = model_messages[0].parts[0]
    assert isinstance(user_part, UserPromptPart)
    assert user_part.content == "Hello, how are you?"
    
    # Check assistant message
    assistant_part = model_messages[1].parts[0]
    assert isinstance(assistant_part, TextPart)
    assert assistant_part.content == "I'm doing well, thanks for asking!"

@pytest.mark.asyncio
async def test_serialize_model_messages_to_json():
    """Test serializing ModelMessages to JSON."""
    
    # Create test ModelMessage objects
    model_request = ModelRequest(
        parts=[
            UserPromptPart(
                content="Test message",
                timestamp=datetime.now(timezone.utc)
            )
        ]
    )
    
    model_response = ModelResponse(
        parts=[TextPart(content="Test response")],
        usage=Usage(total_tokens=15, details=None),
        model_name="gpt-4o-mini",
        timestamp=datetime.now(timezone.utc)
    )
    
    model_messages = [model_request, model_response]
    
    # Serialize to JSON
    json_string = await message_converter_service.serialize_model_messages_to_json(model_messages)
    
    # Verify JSON is valid
    assert isinstance(json_string, str)
    json_data = json.loads(json_string)
    assert isinstance(json_data, list)
    assert len(json_data) == 2

@pytest.mark.asyncio
async def test_deserialize_json_to_model_messages():
    """Test deserializing JSON back to ModelMessages."""
    
    # Create test data and serialize
    model_messages = [
        ModelRequest(
            parts=[UserPromptPart(content="Test", timestamp=datetime.now(timezone.utc))]
        )
    ]
    
    json_string = await message_converter_service.serialize_model_messages_to_json(model_messages)
    
    # Deserialize back
    deserialized = await message_converter_service.deserialize_json_to_model_messages(json_string)
    
    # Verify deserialization
    assert len(deserialized) == 1
    assert isinstance(deserialized[0], ModelRequest)
    assert deserialized[0].parts[0].content == "Test"

@pytest.mark.asyncio
async def test_convert_empty_messages():
    """Test handling empty message lists."""
    
    db_messages = []
    model_messages = await message_converter_service.convert_db_messages_to_model_messages(db_messages)
    
    assert model_messages == []

@pytest.mark.asyncio
async def test_convert_invalid_role():
    """Test handling messages with invalid roles."""
    
    invalid_msg = MagicMock()
    invalid_msg.role = "system"  # Unsupported role
    invalid_msg.content = "System message"
    invalid_msg.created_at = datetime.now(timezone.utc)
    
    db_messages = [invalid_msg]
    model_messages = await message_converter_service.convert_db_messages_to_model_messages(db_messages)
    
    # Should skip invalid roles
    assert len(model_messages) == 0

@pytest.mark.asyncio
async def test_convert_messages_with_none_timestamp():
    """Test handling messages with None created_at timestamp."""
    
    msg = MagicMock()
    msg.role = "user"
    msg.content = "Hello"
    msg.created_at = None  # None timestamp
    
    db_messages = [msg]
    model_messages = await message_converter_service.convert_db_messages_to_model_messages(db_messages)
    
    # Should handle None timestamp gracefully
    assert len(model_messages) == 1
    assert isinstance(model_messages[0], ModelRequest)
    assert model_messages[0].parts[0].content == "Hello"

@pytest.mark.asyncio
async def test_model_messages_type_adapter():
    """Test ModelMessagesTypeAdapter directly."""
    
    # Create test ModelMessage
    model_request = ModelRequest(
        parts=[UserPromptPart(content="Direct test", timestamp=datetime.now(timezone.utc))]
    )
    
    # Test serialization/deserialization cycle
    json_data = to_jsonable_python([model_request])
    deserialized = ModelMessagesTypeAdapter.validate_python(json_data)
    
    assert len(deserialized) == 1
    assert isinstance(deserialized[0], ModelRequest)
    assert deserialized[0].parts[0].content == "Direct test"

@pytest.mark.asyncio
async def test_serialize_empty_list():
    """Test serializing empty ModelMessage list."""
    
    json_string = await message_converter_service.serialize_model_messages_to_json([])
    
    assert json_string == "[]"

@pytest.mark.asyncio
async def test_deserialize_empty_json():
    """Test deserializing empty JSON."""
    
    model_messages = await message_converter_service.deserialize_json_to_model_messages("[]")
    
    assert model_messages == []

@pytest.mark.asyncio
async def test_deserialize_invalid_json():
    """Test error handling for invalid JSON."""
    
    model_messages = await message_converter_service.deserialize_json_to_model_messages("invalid json")
    
    # Should return empty list on error
    assert model_messages == []