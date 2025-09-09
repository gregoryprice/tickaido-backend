from typing import List, Dict, Any
import json
from datetime import datetime, timezone
from pydantic import TypeAdapter
from pydantic_ai.messages import (
    ModelMessage, 
    ModelRequest, 
    ModelResponse,
    UserPromptPart,
    TextPart
)
from pydantic_ai.usage import Usage
from pydantic_core import to_jsonable_python
from app.models.chat import Message
import logging

logger = logging.getLogger(__name__)

# Create TypeAdapter for ModelMessage serialization
ModelMessagesTypeAdapter = TypeAdapter(List[ModelMessage])

class MessageConverterService:
    """Service for converting database messages to Pydantic AI ModelMessage format."""
    
    async def convert_db_messages_to_model_messages(
        self,
        db_messages: List[Message]
    ) -> List[ModelMessage]:
        """
        Convert database Message objects to Pydantic AI ModelMessage format.
        
        Args:
            db_messages: List of Message objects from database
            
        Returns:
            List[ModelMessage]: Properly formatted messages for Pydantic AI
        """
        try:
            model_messages: List[ModelMessage] = []
            
            for msg in db_messages:
                if msg.role == "user":
                    # Create ModelRequest for user messages
                    model_request = ModelRequest(
                        parts=[
                            UserPromptPart(
                                content=msg.content,
                                timestamp=msg.created_at or datetime.now(timezone.utc)
                            )
                        ]
                    )
                    model_messages.append(model_request)
                    
                elif msg.role == "assistant":
                    # Create ModelResponse for assistant messages
                    model_response = ModelResponse(
                        parts=[
                            TextPart(content=msg.content)
                        ],
                        usage=Usage(
                            total_tokens=0,  # Would need to calculate or store
                            details=None
                        ),
                        model_name="gpt-4o-mini",  # Default model name
                        timestamp=msg.created_at or datetime.now(timezone.utc)
                    )
                    model_messages.append(model_response)
            
            logger.info(f"Converted {len(db_messages)} messages to ModelMessage format")
            return model_messages
            
        except Exception as e:
            logger.error(f"Error converting messages to ModelMessage format: {e}")
            return []
    
    async def serialize_model_messages_to_json(
        self,
        model_messages: List[ModelMessage]
    ) -> str:
        """Serialize ModelMessages to JSON using TypeAdapter."""
        try:
            json_data = to_jsonable_python(model_messages)
            return json.dumps(json_data)
        except Exception as e:
            logger.error(f"Error serializing ModelMessages: {e}")
            return "[]"
    
    async def deserialize_json_to_model_messages(
        self,
        json_string: str
    ) -> List[ModelMessage]:
        """Deserialize JSON to ModelMessages using TypeAdapter."""
        try:
            json_data = json.loads(json_string)
            return ModelMessagesTypeAdapter.validate_python(json_data)
        except Exception as e:
            logger.error(f"Error deserializing ModelMessages: {e}")
            return []

message_converter_service = MessageConverterService()