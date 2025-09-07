#!/usr/bin/env python3
"""
Agent-Aware Chat WebSocket endpoints for real-time thread messaging
"""

import json
import logging
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio

from app.database import get_db_session
from app.services.thread_service import thread_service
from app.services.ai_chat_service import ai_chat_service
from app.dependencies import get_current_user_from_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws/chat", tags=["Agent-Aware Chat WebSocket"])


class AgentConnectionManager:
    """Manages agent-aware WebSocket connections for thread-based chat"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, connection_id: str, agent_id: UUID, thread_id: UUID, user_id: str):
        """Accept WebSocket connection with agent context"""
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        self.connection_metadata[connection_id] = {
            "agent_id": str(agent_id),
            "thread_id": str(thread_id),
            "user_id": user_id,
            "connected_at": asyncio.get_event_loop().time()
        }
        logger.info(f"Agent-aware WebSocket connection established: {connection_id} (agent: {agent_id}, thread: {thread_id})")
    
    def disconnect(self, connection_id: str):
        """Remove WebSocket connection and metadata"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        if connection_id in self.connection_metadata:
            del self.connection_metadata[connection_id]
        logger.info(f"Agent-aware WebSocket connection disconnected: {connection_id}")
    
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
    
    def get_connection_context(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get connection metadata"""
        return self.connection_metadata.get(connection_id)


# Global agent-aware connection manager instance
manager = AgentConnectionManager()


@router.websocket("/{agent_id}/threads/{thread_id}")
async def agent_chat_websocket_endpoint(
    websocket: WebSocket,
    agent_id: UUID,
    thread_id: UUID,
    token: str,
    db: AsyncSession = Depends(get_db_session)
):
    """WebSocket endpoint for real-time agent-aware chat streaming"""
    
    connection_id = None
    try:
        # Authenticate user from token
        current_user = await get_current_user_from_token(token, db)
        if not current_user:
            await websocket.close(code=1008, reason="Authentication failed")
            return
        
        # Validate user has access to the thread through the agent
        user_id = str(current_user.id)
        thread = await thread_service.get_thread(
            db=db,
            agent_id=agent_id,
            thread_id=thread_id,
            user_id=user_id
        )
        
        if not thread:
            await websocket.close(code=1008, reason="Thread not found or access denied")
            return
        
        # Create connection ID with agent context
        connection_id = f"{user_id}:{agent_id}:{thread_id}"
        await manager.connect(websocket, connection_id, agent_id, thread_id, user_id)
        
        # Send connection established message with agent context
        await manager.send_json_message({
            "type": "connection_established",
            "data": {
                "agent_id": str(agent_id),
                "thread_id": str(thread_id),
                "user_id": user_id,
                "thread_title": thread.title,
                "supported_features": [
                    "real_time_messaging", 
                    "ai_streaming", 
                    "agent_tool_calling",
                    "tool_call_progress",
                    "file_attachments"
                ]
            },
            "timestamp": datetime.now().isoformat()
        }, connection_id)
        
        # Message handling loop
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_json()
                await handle_agent_websocket_message(
                    data, connection_id, agent_id, thread_id, user_id, db
                )
                
            except WebSocketDisconnect:
                logger.info(f"Agent-aware WebSocket disconnected: {connection_id}")
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
                logger.error(f"Error in agent WebSocket message handling: {e}")
                await manager.send_json_message({
                    "type": "error",
                    "data": {
                        "error_code": "SERVER_ERROR", 
                        "error_message": "Internal server error"
                    }
                }, connection_id)
    
    except Exception as e:
        logger.error(f"Error in agent WebSocket connection: {e}")
        if websocket.client_state.name != "DISCONNECTED":
            await websocket.close(code=1011, reason="Internal server error")
    
    finally:
        if connection_id:
            manager.disconnect(connection_id)


async def handle_agent_websocket_message(
    data: Dict[Any, Any],
    connection_id: str,
    agent_id: UUID,
    thread_id: UUID,
    user_id: str,
    db: AsyncSession
):
    """Handle incoming WebSocket messages with agent context"""
    
    message_type = data.get("type")
    
    if message_type == "send_message":
        await handle_agent_send_message(data, connection_id, agent_id, thread_id, user_id, db)
    elif message_type == "ping":
        await handle_agent_ping(data, connection_id)
    elif message_type == "get_agent_status":
        await handle_get_agent_status(data, connection_id, agent_id, db)
    else:
        await manager.send_json_message({
            "type": "error",
            "data": {
                "error_code": "UNKNOWN_MESSAGE_TYPE",
                "error_message": f"Unknown message type: {message_type}"
            }
        }, connection_id)


async def handle_agent_send_message(
    data: Dict[Any, Any],
    connection_id: str,
    agent_id: UUID,
    thread_id: UUID,
    user_id: str,
    db: AsyncSession
):
    """Handle send_message WebSocket requests with agent context"""
    
    try:
        message_content = data.get("data", {}).get("content")
        attachments = data.get("data", {}).get("attachments", [])
        
        if not message_content:
            await manager.send_json_message({
                "type": "error",
                "data": {
                    "error_code": "MISSING_MESSAGE",
                    "error_message": "Message content is required"
                }
            }, connection_id)
            return
        
        # Validate thread access through thread service
        thread = await thread_service.get_thread(db, agent_id, thread_id, user_id)
        if not thread:
            await manager.send_json_message({
                "type": "error",
                "data": {
                    "error_code": "THREAD_ACCESS_DENIED",
                    "error_message": "Thread not found or access denied"
                }
            }, connection_id)
            return
        
        # Send user message confirmation
        await manager.send_json_message({
            "type": "user_message_sent",
            "data": {
                "content": message_content,
                "role": "user",
                "thread_id": str(thread_id),
                "agent_id": str(agent_id),
                "attachments_count": len(attachments),
                "timestamp": datetime.now().isoformat()
            }
        }, connection_id)
        
        # Generate AI response with streaming and tool call progress
        await stream_agent_ai_response(
            connection_id, agent_id, thread_id, user_id, message_content, attachments
        )
        
    except Exception as e:
        logger.error(f"Error handling agent send_message: {e}")
        await manager.send_json_message({
            "type": "error",
            "data": {
                "error_code": "MESSAGE_SEND_FAILED",
                "error_message": "Failed to send message"
            }
        }, connection_id)


async def stream_agent_ai_response(
    connection_id: str,
    agent_id: UUID,
    thread_id: UUID,
    user_id: str,
    user_message: str,
    attachments: List[Dict[str, Any]] = None
):
    """Stream AI response in real-time with tool call progress reporting"""
    
    try:
        # Send AI response start notification
        await manager.send_json_message({
            "type": "ai_response_start",
            "data": {
                "message": "Agent is processing your request...",
                "agent_id": str(agent_id),
                "thread_id": str(thread_id),
                "supports_tool_calls": True
            }
        }, connection_id)
        
        # Send tool call progress if agent might use tools
        await manager.send_json_message({
            "type": "tool_call_progress",
            "data": {
                "status": "analyzing_request",
                "message": "Analyzing your request and determining which tools to use...",
                "agent_id": str(agent_id)
            }
        }, connection_id)
        
        # Stream AI response using the agent-centric chat service
        full_response = ""
        tool_calls_used = []
        
        try:
            # Use streaming from the AI chat service
            async for chunk in ai_chat_service.stream_message_to_thread(
                agent_id=str(agent_id),
                thread_id=str(thread_id),
                user_id=user_id,
                message=user_message,
                attachments=attachments
            ):
                full_response += chunk
                
                # Send streaming chunk
                await manager.send_json_message({
                    "type": "ai_response_chunk",
                    "data": {
                        "content": full_response,
                        "is_complete": False,
                        "agent_id": str(agent_id),
                        "chunk": chunk
                    }
                }, connection_id)
                
                # Small delay for realistic streaming
                await asyncio.sleep(0.05)
        
        except Exception as stream_error:
            logger.error(f"Streaming error: {stream_error}")
            # Fallback to non-streaming response
            try:
                ai_response = await ai_chat_service.send_message_to_thread(
                    agent_id=str(agent_id),
                    thread_id=str(thread_id),
                    user_id=user_id,
                    message=user_message,
                    attachments=attachments
                )
                full_response = ai_response.content
                tool_calls_used = getattr(ai_response, 'tools_used', [])
            except Exception as fallback_error:
                logger.error(f"Fallback AI response failed: {fallback_error}")
                full_response = "I encountered an error processing your request."
                tool_calls_used = []
        
        # Send tool call completion if tools were used
        if tool_calls_used:
            await manager.send_json_message({
                "type": "tool_calls_complete",
                "data": {
                    "tools_used": tool_calls_used,
                    "tool_call_count": len(tool_calls_used),
                    "agent_id": str(agent_id)
                }
            }, connection_id)
        
        # Send final completion message
        await manager.send_json_message({
            "type": "ai_response_complete",
            "data": {
                "content": full_response,
                "role": "assistant",
                "thread_id": str(thread_id),
                "agent_id": str(agent_id),
                "tool_calls": tool_calls_used,
                "response_length": len(full_response),
                "timestamp": datetime.now().isoformat()
            }
        }, connection_id)
        
    except Exception as e:
        logger.error(f"Error streaming agent AI response: {e}")
        await manager.send_json_message({
            "type": "error",
            "data": {
                "error_code": "AI_RESPONSE_FAILED",
                "error_message": "Failed to generate AI response",
                "agent_id": str(agent_id)
            }
        }, connection_id)


async def handle_get_agent_status(
    data: Dict[Any, Any],
    connection_id: str,
    agent_id: UUID,
    db: AsyncSession
):
    """Handle agent status requests"""
    
    try:
        # Get agent information
        from sqlalchemy import select
        from app.models.ai_agent import Agent
        
        agent_query = select(Agent).where(Agent.id == agent_id)
        result = await db.execute(agent_query)
        agent = result.scalar_one_or_none()
        
        if agent:
            await manager.send_json_message({
                "type": "agent_status",
                "data": {
                    "agent_id": str(agent_id),
                    "name": agent.name,
                    "agent_type": agent.agent_type,
                    "is_active": agent.is_active,
                    "status": agent.status,
                    "tools_enabled": agent.tools or [],
                    "tools_count": len(agent.tools or [])
                }
            }, connection_id)
        else:
            await manager.send_json_message({
                "type": "error",
                "data": {
                    "error_code": "AGENT_NOT_FOUND",
                    "error_message": f"Agent {agent_id} not found"
                }
            }, connection_id)
            
    except Exception as e:
        logger.error(f"Error getting agent status: {e}")
        await manager.send_json_message({
            "type": "error",
            "data": {
                "error_code": "AGENT_STATUS_ERROR",
                "error_message": "Failed to get agent status"
            }
        }, connection_id)


async def handle_agent_ping(data: Dict[Any, Any], connection_id: str):
    """Handle ping messages for connection health with agent context"""
    
    context = manager.get_connection_context(connection_id)
    
    await manager.send_json_message({
        "type": "pong",
        "data": {
            "timestamp": datetime.now().isoformat(),
            "connection_id": connection_id,
            "agent_id": context.get("agent_id") if context else None,
            "uptime_seconds": round(asyncio.get_event_loop().time() - context.get("connected_at", 0), 2) if context else 0
        }
    }, connection_id)