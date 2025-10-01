#!/usr/bin/env python3
"""
Chat WebSocket endpoints for real-time messaging
"""

import asyncio
import json
import logging
from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.dependencies import get_current_user_from_token

# MessageRole is no longer needed since we use string constants
from app.services.chat_service import chat_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws/chat", tags=["Chat WebSocket"])


class ConnectionManager:
    """Manages WebSocket connections for chat"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, connection_id: str):
        """Accept WebSocket connection"""
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        logger.info(f"WebSocket connection established: {connection_id}")
    
    def disconnect(self, connection_id: str):
        """Remove WebSocket connection"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
            logger.info(f"WebSocket connection disconnected: {connection_id}")
    
    async def send_personal_message(self, message: str, connection_id: str):
        """Send message to specific connection"""
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            await websocket.send_text(message)
    
    async def send_json_message(self, data: Dict[Any, Any], connection_id: str):
        """Send JSON message to specific connection"""
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            await websocket.send_json(data)


# Global connection manager instance
manager = ConnectionManager()


@router.websocket("/stream/{conversation_id}")
async def chat_websocket_endpoint(
    websocket: WebSocket,
    conversation_id: UUID,
    token: str,
    db: AsyncSession = Depends(get_db_session)
):
    """WebSocket endpoint for real-time chat streaming"""
    
    connection_id = None
    try:
        # Authenticate user from token
        current_user = await get_current_user_from_token(token, db)
        if not current_user:
            await websocket.close(code=1008, reason="Authentication failed")
            return
        
        # Validate user owns the conversation
        user_id: UUID = current_user.id  # type: ignore
        conversation = await chat_service.get_conversation(db, conversation_id, user_id)
        if not conversation:
            await websocket.close(code=1008, reason="Conversation not found or access denied")
            return
        
        # Create connection ID and connect
        connection_id = f"{user_id}:{conversation_id}"
        await manager.connect(websocket, connection_id)
        
        # Send connection established message
        await manager.send_json_message({
            "type": "connection_established",
            "data": {
                "conversation_id": str(conversation_id),
                "user_id": str(user_id),
                "supported_features": ["real_time_messaging", "ai_streaming"]
            },
            "timestamp": "2024-01-01T12:00:00Z"
        }, connection_id)
        
        # Message handling loop
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_json()
                await handle_websocket_message(data, connection_id, conversation_id, user_id, db)
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected: {connection_id}")
                break
            except json.JSONDecodeError:
                await manager.send_json_message({
                    "type": "error",
                    "data": {
                        "error_code": "INVALID_JSON",
                        "error_message": "Invalid JSON format"
                    }
                }, connection_id)
            except Exception as e:
                logger.error(f"Error in WebSocket message handling: {e}")
                await manager.send_json_message({
                    "type": "error",
                    "data": {
                        "error_code": "SERVER_ERROR", 
                        "error_message": "Internal server error"
                    }
                }, connection_id)
    
    except Exception as e:
        logger.error(f"Error in WebSocket connection: {e}")
        if websocket.client_state.name != "DISCONNECTED":
            await websocket.close(code=1011, reason="Internal server error")
    
    finally:
        if connection_id:
            manager.disconnect(connection_id)


async def handle_websocket_message(
    data: Dict[Any, Any],
    connection_id: str,
    conversation_id: UUID,
    user_id: UUID,
    db: AsyncSession
):
    """Handle incoming WebSocket messages"""
    
    message_type = data.get("type")
    
    if message_type == "send_message":
        await handle_send_message(data, connection_id, conversation_id, user_id, db)
    elif message_type == "ping":
        await handle_ping(data, connection_id)
    else:
        await manager.send_json_message({
            "type": "error",
            "data": {
                "error_code": "UNKNOWN_MESSAGE_TYPE",
                "error_message": f"Unknown message type: {message_type}"
            }
        }, connection_id)


async def handle_send_message(
    data: Dict[Any, Any],
    connection_id: str,
    conversation_id: UUID,
    user_id: UUID,
    db: AsyncSession
):
    """Handle send_message WebSocket requests"""
    
    try:
        message_content = data.get("data", {}).get("message")
        if not message_content:
            await manager.send_json_message({
                "type": "error",
                "data": {
                    "error_code": "MISSING_MESSAGE",
                    "error_message": "Message content is required"
                }
            }, connection_id)
            return
        
        # Save user message to database
        user_message = await chat_service.send_message(
            db=db,
            conversation_id=conversation_id,
            user_id=user_id,
            content=message_content
        )
        
        # Send user message confirmation
        await manager.send_json_message({
            "type": "user_message_sent",
            "data": {
                "message_id": str(user_message.id),
                "content": user_message.content,
                "role": user_message.role.value,
                "created_at": user_message.created_at.isoformat()
            }
        }, connection_id)
        
        # Generate AI response with streaming
        await stream_ai_response(connection_id, conversation_id, str(user_message.content), db)
        
    except Exception as e:
        logger.error(f"Error handling send_message: {e}")
        await manager.send_json_message({
            "type": "error",
            "data": {
                "error_code": "MESSAGE_SEND_FAILED",
                "error_message": "Failed to send message"
            }
        }, connection_id)


async def stream_ai_response(
    connection_id: str,
    conversation_id: UUID,
    user_message: str,
    db: AsyncSession
):
    """Stream AI response in real-time"""
    
    try:
        # Send AI response start notification
        await manager.send_json_message({
            "type": "ai_response_start",
            "data": {
                "message": "AI is generating response..."
            }
        }, connection_id)
        
        # Simulate AI response generation (in real app, this would call AI service)
        ai_response = "I understand your message. Let me help you with that. This is a simulated AI response."
        
        # Stream response word by word
        words = ai_response.split()
        accumulated_response = ""
        
        for i, word in enumerate(words):
            accumulated_response += word + " "
            
            # Send streaming chunk
            await manager.send_json_message({
                "type": "ai_response_chunk",
                "data": {
                    "content": accumulated_response.strip(),
                    "is_complete": False,
                    "word_count": i + 1
                }
            }, connection_id)
            
            # Small delay to simulate streaming
            await asyncio.sleep(0.1)
        
        # Save complete AI response to database
        from app.models.chat import ChatMessage
        ai_message = ChatMessage(
            conversation_id=conversation_id,
            role="assistant",
            content=ai_response.strip()
        )
        
        db.add(ai_message)
        await db.commit()
        await db.refresh(ai_message)
        
        # Send final completion message
        await manager.send_json_message({
            "type": "ai_response_complete",
            "data": {
                "message_id": str(ai_message.id),
                "content": ai_message.content,
                "role": ai_message.role.value,
                "created_at": ai_message.created_at.isoformat(),
                "total_words": len(words)
            }
        }, connection_id)
        
    except Exception as e:
        logger.error(f"Error streaming AI response: {e}")
        await manager.send_json_message({
            "type": "error",
            "data": {
                "error_code": "AI_RESPONSE_FAILED",
                "error_message": "Failed to generate AI response"
            }
        }, connection_id)


async def handle_ping(data: Dict[Any, Any], connection_id: str):
    """Handle ping messages for connection health"""
    
    await manager.send_json_message({
        "type": "pong",
        "timestamp": data.get("timestamp", "2024-01-01T12:00:00Z")
    }, connection_id)