"""
AI Chat Service for Agent-Centric Thread Management

This service provides AI-powered chat functionality using the new agent-centric
thread architecture. Each thread is associated with a specific AI agent and 
organization, enabling better tool calling and personalized AI interactions.

Key Features:
- Agent-centric processing with organization isolation
- Thread-based conversations instead of generic conversations  
- Enhanced MCP client integration for authenticated tool calls
- Tool call result recording in message metadata
- File attachment processing and AI analysis
- Real-time streaming responses
- AI-powered title generation
"""

import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, AsyncIterator, Union
from uuid import UUID
from enum import Enum
from pydantic import BaseModel, Field
from pydantic_ai import Agent as PydanticAgent
from pydantic_ai.usage import UsageLimits
from sqlalchemy import select

from app.models.chat import Thread, Message
from app.models.ai_agent import Agent as AgentModel
from app.database import get_async_db_session
from app.services.ai_agent_service import ai_agent_service
from app.schemas.ai_response import ChatResponse, CustomerSupportContext

logger = logging.getLogger(__name__)


class MessageFormat(Enum):
    """Supported message formats for thread history retrieval"""
    DETAILED = "detailed"  # Full message details with timestamps, tool_calls, attachments
    SIMPLE = "simple"      # Simple role/content format for AI agents
    MODEL_MESSAGE = "model_message"  # Pydantic AI ModelMessage format


async def get_organization_agent_model(organization_id: UUID):
    """
    Get organization's agent model (auto-creates if missing).
    
    This implements the "Agent Availability Guarantee" from the PRP - every organization
    gets a customer support agent automatically with defaults from ai_config.yaml.
    
    Args:
        organization_id: Organization UUID
        
    Returns:
        Agent: Organization's agent model from database
    """
    try:
        # Use service layer to ensure organization has an agent
        agent_model = await ai_agent_service.ensure_organization_agent(organization_id)
        
        if not agent_model:
            logger.error(f"Failed to ensure agent for organization {organization_id}")
            return None
        
        config = agent_model.get_configuration()
        tools_enabled = config.get("tools_enabled", [])
        
        logger.info(f"✅ Organization {organization_id} agent model ready: {agent_model.id} with {len(tools_enabled)} tools")
        return agent_model
        
    except Exception as e:
        logger.error(f"❌ Failed to get organization agent model: {e}")
        return None


class ThreadContext(BaseModel):
    """Enhanced context for thread-based chat operations with secure authentication"""
    user_id: str
    thread_id: str
    agent_id: str
    organization_id: str
    user_role: str = "user"
    session_history: List[Dict[str, str]] = Field(default_factory=list)
    user_metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Secure authentication - private attributes not included in serialization
    _auth_container: Optional[Any] = None
    _auth_provider: Optional[Any] = None
    _original_token: Optional[str] = None
    
    model_config = {"arbitrary_types_allowed": True}
    
    async def get_auth_headers(self) -> Optional[Dict[str, str]]:
        """Get authentication headers with live validation"""
        if not self._auth_container or not self._auth_provider or not self._original_token:
            return None
            
        # Check expiry and revocation
        if self._auth_container.is_expired:
            logger.warning(f"Token expired for user {self.user_id}")
            return None
            
        if await self._auth_provider.check_revocation(self._auth_container.token_hash):
            logger.warning(f"Token revoked for user {self.user_id}")
            return None
            
        return {"Authorization": f"Bearer {self._original_token}"}
    
    @property
    def has_valid_auth(self) -> bool:
        """Check if context has valid authentication"""
        return (self._auth_container is not None and 
                not self._auth_container.is_expired and 
                self._original_token is not None)


class TitleGenerationResponse(BaseModel):
    """Structured response for title generation"""
    title: str = Field(description="Generated thread title")
    confidence: float = Field(description="Confidence in title generation (0-1)", ge=0, le=1)


class AIChatService:
    """
    Agent-centric AI chat service for thread management.
    
    This service provides comprehensive chat functionality using the new 
    agent-centric architecture where every thread is associated with a 
    specific AI agent and organization.
    """
    
    def __init__(self):
        """Initialize the AI chat service."""
        self.agent = None  # Will be initialized async
        self.title_agent = None  # Will be initialized async
        self._agent_initialized = False
        self._title_agent_initialized = False
    
    async def _ensure_title_agent_initialized(self):
        """Ensure the title agent is initialized"""
        if not self._title_agent_initialized:
            self.title_agent = await self._create_title_generation_agent()
            self._title_agent_initialized = True
    
    async def _create_title_generation_agent(self) -> PydanticAgent:
        """Create a specialized agent for generating thread titles"""
        try:
            agent = PydanticAgent(
                "openai:gpt-3.5-turbo",
                output_type=TitleGenerationResponse,
                system_prompt="""You are a Customer Support Thread Title Generator. Create concise, 
                descriptive titles for customer support chat threads. Guidelines:
                - Create titles that are 3-8 words long
                - Focus on the main issue or request being discussed
                - Use customer support terminology when appropriate
                - Make titles searchable and meaningful for support staff
                - Avoid generic titles like "Customer Support Chat"
                Examples: "Login Issues with Password Reset", "Email Integration Setup Help", 
                "Billing Discrepancy Resolution", "Feature Request: Export Functionality"""
            )
            logger.info("✅ Title generation agent created")
            return agent
        except Exception as e:
            logger.error(f"❌ Failed to create title generation agent: {e}")
            # Emergency fallback
            return PydanticAgent(
                "openai:gpt-3.5-turbo",
                output_type=TitleGenerationResponse,
                system_prompt="Generate a concise title for this customer support thread."
            )
    
    async def get_thread_history(
        self, 
        thread_id: str, 
        user_id: str, 
        agent_id: str,
        format_type: MessageFormat = MessageFormat.DETAILED,
        max_context_size: Optional[int] = None,
        use_memory_context: bool = True
    ) -> Union[List[Dict[str, Any]], List]:
        """
        Consolidated method to get thread history in various formats.
        
        Args:
            thread_id: ID of the thread
            user_id: ID of the user (for authorization)
            agent_id: ID of the agent (for validation)
            format_type: Type of format to return (DETAILED, SIMPLE, or MODEL_MESSAGE)
            max_context_size: Maximum tokens allowed in context (for SIMPLE and MODEL_MESSAGE)
            use_memory_context: Whether to include message history
            
        Returns:
            Union[List[Dict], List]: Messages in the requested format
        """
        if not use_memory_context:
            logger.debug(f"Memory context disabled for thread {thread_id}")
            return []
        
        async with get_async_db_session() as db:
            try:
                # Verify user owns thread and agent is valid
                thread_query = select(Thread).where(
                    Thread.id == UUID(thread_id),
                    Thread.user_id == user_id,
                    Thread.agent_id == UUID(agent_id)
                )
                
                result = await db.execute(thread_query)
                thread = result.scalar_one_or_none()
                
                if not thread:
                    logger.warning(f"[AI_CHAT_SERVICE] Thread {thread_id} not found for user {user_id} and agent {agent_id}")
                    return []
                
                # Get messages in chronological order
                messages_query = select(Message).where(
                    Message.thread_id == UUID(thread_id)
                ).order_by(Message.created_at)
                
                result = await db.execute(messages_query)
                messages = result.scalars().all()
                
                # Apply context limits if specified (for SIMPLE and MODEL_MESSAGE formats)
                if max_context_size and max_context_size > 0 and format_type != MessageFormat.DETAILED:
                    messages = await self._apply_context_limits(messages, max_context_size)
                
                # Format messages based on requested type
                if format_type == MessageFormat.DETAILED:
                    # Full message details with metadata
                    formatted_messages = []
                    for msg in messages:
                        formatted_messages.append({
                            "role": msg.role,
                            "content": msg.content,
                            "created_at": msg.created_at.isoformat(),
                            "tool_calls": json.dumps(msg.tool_calls) if msg.tool_calls else "[]",
                            "attachments": json.dumps(msg.attachments) if msg.attachments else "[]"
                        })
                    
                    logger.info(f"Retrieved {len(formatted_messages)} detailed messages")
                    return formatted_messages
                
                elif format_type == MessageFormat.SIMPLE:
                    # Simple role/content format for Pydantic AI
                    formatted_messages = []
                    for msg in messages:
                        formatted_messages.append({
                            "role": msg.role,
                            "content": msg.content
                        })
                    
                    logger.info(f"Retrieved {len(formatted_messages)} simple messages for Pydantic AI agent")
                    return formatted_messages
                
                elif format_type == MessageFormat.MODEL_MESSAGE:
                    # Convert to ModelMessage format using converter service
                    from app.services.message_converter_service import message_converter_service
                    model_messages = await message_converter_service.convert_db_messages_to_model_messages(messages)
                    
                    logger.info(f"Retrieved {len(model_messages)} ModelMessages for Pydantic AI agent")
                    return model_messages
                
                else:
                    logger.error(f"Unknown message format type: {format_type}")
                    return []
                
            except Exception as e:
                logger.error(f"[AI_CHAT_SERVICE] Error getting thread history ({format_type.value}): {e}")
                return []

    async def _apply_context_limits(
        self,
        messages: List[Message],
        max_context_size: int
    ) -> List[Message]:
        """Apply token-based context limits to raw messages."""
        try:
            if not messages or max_context_size <= 0:
                return messages
            
            # If we have a reasonable number of messages, just return them
            if len(messages) <= 10:
                return messages
            
            # Apply token-based filtering (process from newest to oldest)
            filtered_messages = []
            total_tokens = 0
            
            # Work backwards through messages (newest first)
            for message in reversed(messages):
                # Convert to dict format for token counting
                msg_dict = {
                    "role": message.role,
                    "content": message.content,
                }
                
                # Count tokens for this message using existing token service
                from app.services.token_counter_service import token_counter_service
                message_tokens = await token_counter_service.count_message_tokens(msg_dict)
                
                # Check if adding this message would exceed context limit
                if total_tokens + message_tokens > max_context_size:
                    logger.debug(f"Context limit reached at {total_tokens} tokens, skipping older messages")
                    break
                
                filtered_messages.append(message)
                total_tokens += message_tokens
            
            # Return messages in chronological order (oldest first)
            result = filtered_messages[::-1]
            
            logger.info(f"Applied context limits: {len(result)}/{len(messages)} messages, {total_tokens} tokens")
            return result
            
        except Exception as e:
            logger.error(f"Error applying context limits: {e}")
            # Fallback: return last 10 messages if token counting fails
            return messages[-10:] if len(messages) > 10 else messages
    
    async def send_message_to_thread(
        self, 
        agent_id: str,
        thread_id: str, 
        user_id: str, 
        message: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
        auth_token: Optional[str] = None
    ) -> ChatResponse:
        """
        Send message to a thread with agent-centric processing.
        
        Args:
            agent_id: ID of the agent handling this thread
            thread_id: ID of the thread
            user_id: ID of the user sending the message
            message: User's message content
            attachments: Optional file attachments in format [{"file_id": "uuid"}]
            auth_token: Optional JWT token for MCP authentication
            
        Returns:
            ChatResponse: Structured AI response with tool calls and metadata
        """
        
        async with get_async_db_session() as db:
            # Validate file attachments if provided
            validated_file_ids = []
            if attachments:
                from app.services.file_validation_service import FileValidationService
                
                # Get organization_id from agent model
                agent_model = await self._get_agent_model(UUID(agent_id))
                if not agent_model:
                    raise Exception("Agent not found")
                    
                file_validator = FileValidationService()
                validated_file_ids = await file_validator.validate_file_attachments(
                    db, attachments, agent_model.organization_id
                )
                logger.info(f"Validated {len(validated_file_ids)} file attachments")
        
        # Get thread history for context in simple format
        message_history = await self.get_thread_history(thread_id, user_id, agent_id, format_type=MessageFormat.SIMPLE)
        
        # Create context for agent-centric processing
        context = ThreadContext(
            user_id=user_id,
            thread_id=thread_id,
            agent_id=agent_id,
            organization_id="",  # Will be populated from agent
            session_history=message_history
        )
        
        # Handle authentication if token provided
        # Validate auth token if provided, otherwise use non-authenticated processing
        validated_auth_token = None
        if auth_token:
            try:
                from app.middleware.auth_middleware import auth_service
                payload = auth_service.verify_token(auth_token)
                if payload:  # Use the payload to check if token is valid
                    logger.info(f"[AI_CHAT_SERVICE] Valid JWT token for user {user_id} in thread {thread_id}")
                    validated_auth_token = auth_token
                else:
                    logger.warning(f"[AI_CHAT_SERVICE] JWT token verification returned None")
            except Exception as e:
                logger.warning(f"[AI_CHAT_SERVICE] JWT token validation failed: {e}")
        
        # Use consolidated message processing with optional authentication
        return await self._send_message(context, message, attachments, auth_token=validated_auth_token)
    
    async def _send_message(self, context: ThreadContext, message: str, attachments: List[dict] = None, auth_token: Optional[str] = None) -> ChatResponse:
        """
        Consolidated method for processing thread messages with optional authentication.
        
        Handles both authenticated and non-authenticated message processing with
        intelligent file processing, error handling, and response time tracking.
        
        Args:
            context: Thread context with user and agent information
            message: User's message content
            attachments: Optional file attachments
            auth_token: Optional JWT token for MCP authentication
            
        Returns:
            ChatResponse: AI response with tool calls and metadata
        """
        async with get_async_db_session() as db:
            try:
                start_time = datetime.now(timezone.utc)
                auth_status = "authenticated" if auth_token else "non-authenticated"
                logger.info(f"[AI_CHAT_SERVICE] Processing {auth_status} message for thread {context.thread_id}")
                
                # Get agent model
                agent_model = await self._get_agent_model(UUID(context.agent_id))
                
                if not agent_model:
                    logger.error(f"[AI_CHAT_SERVICE] Agent {context.agent_id} not available")
                    ai_response = await self._create_fallback_response("I'm currently unavailable. Please try again later.")
                elif not agent_model.is_active:
                    logger.warning(f"[AI_CHAT_SERVICE] Organization agent {context.agent_id} not active")
                    ai_response = ChatResponse(
                        content="I'm temporarily unavailable for maintenance. Please try again shortly.",
                        confidence=0.0,
                        requires_escalation=True,
                        tools_used=[]
                    )
                else:
                    # Process file attachments if provided using enhanced processing
                    file_context = ""
                    if attachments:
                        file_context = await self._process_attachments(attachments)
                    
                    # Use dynamic agent factory for generic context building and MCP integration
                    from app.services.dynamic_agent_factory import dynamic_agent_factory
                    
                    # Build generic context based on agent type
                    agent_type = agent_model.agent_type or "customer_support"  # Default to customer support
                    agent_context = await dynamic_agent_factory.build_context(
                        agent_type=agent_type,
                        message=message,
                        conversation_history=context.session_history,
                        file_context=file_context,
                        user_metadata={
                            "user_id": context.user_id,
                            "organization_id": context.organization_id,
                            "thread_id": context.thread_id
                        },
                        session_id=context.thread_id,
                        organization_id=context.organization_id
                    )
                    
                    logger.info(f"[AI_CHAT_SERVICE] Processing with dynamic agent for {agent_model.id}")
                    logger.info(f"[AI_CHAT_SERVICE] Agent context: {agent_context}")
                    
                    try:
                        ai_response = await dynamic_agent_factory.process_message_with_agent(
                            agent_model=agent_model, 
                            message=message, 
                            context=agent_context,
                            auth_token=auth_token,  # Pass through auth token (may be None)
                            thread_id=context.thread_id,  # Enable message history
                            db=db  # Pass database session
                        )
                        
                    except Exception as agent_error:
                        logger.error(f"[AI_CHAT_SERVICE] Dynamic agent processing failed: {agent_error}")
                        ai_response = await self._create_fallback_response(
                            "I encountered an error processing your request. Please try again or contact support if the issue persists."
                        )
                
                response_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                logger.info(f"[AI_CHAT_SERVICE] ✅ Agent processing completed in {response_time:.2f}ms ({auth_status})")
                
                # Store the interaction (this is critical and must always happen)
                await self._store_thread_interaction(context, message, ai_response, attachments, response_time)
                
                return ai_response
                
            except Exception as e:
                logger.error(f"[AI_CHAT_SERVICE] Message processing failed: {e}")
                import traceback
                logger.error(f"[AI_CHAT_SERVICE] Full traceback: {traceback.format_exc()}")
                
                return ChatResponse(
                    content="I encountered an error processing your request. Please try again.",
                    confidence=0.0,
                    requires_escalation=True,
                    tools_used=[]
                )

    
    async def _build_file_context(self, db, validated_file_ids: List[UUID]) -> str:
        """Build file context from validated file IDs for AI processing"""
        if not validated_file_ids:
            return ""
        
        try:
            from app.models.file import File
            
            # Get file information
            query = select(File).where(File.id.in_(validated_file_ids))
            result = await db.execute(query)
            files = result.scalars().all()
            
            file_context_parts = []
            for file in files:
                context_part = f"File: {file.filename} ({file.file_type.value})"
                
                # Add extracted content if available
                if file.has_content:
                    content = file.get_all_content()
                    if content:
                        context_part += f"\nContent: {content[:1000]}..."  # Limit content size
                elif file.content_summary:
                    context_part += f"\nSummary: {file.content_summary}"
                    
                file_context_parts.append(context_part)
            
            return "\n\n---FILE ATTACHMENTS---\n" + "\n\n".join(file_context_parts) + "\n---END ATTACHMENTS---"
            
        except Exception as e:
            logger.warning(f"Failed to build file context: {e}")
            return ""
    
    async def _process_attachments(self, attachments: List[dict]) -> str:
        """
        Process file attachments with intelligent reprocessing and optimized content extraction.
        
        Returns consolidated file context string for AI consumption.
        """
        if not attachments:
            return ""
            
        file_contexts = []
        try:
            async with get_async_db_session() as db:
                from app.models.file import File, FileStatus
                from app.services.file_service import FileService
                from sqlalchemy import select
                
                file_service = FileService()
                
                for attachment in attachments:
                    file_id = attachment.get("file_id")
                    if not file_id:
                        continue
                    
                    try:
                        # Validate UUID format
                        from uuid import UUID
                        file_uuid = UUID(file_id)
                        
                        # Get file from database
                        query = select(File).where(File.id == file_uuid)
                        result = await db.execute(query)
                        file_obj = result.scalar_one_or_none()
                    except ValueError:
                        logger.warning(f"[AI_CHAT_SERVICE] Invalid file_id UUID format: {file_id}")
                        continue
                    except Exception as db_error:
                        logger.warning(f"[AI_CHAT_SERVICE] Database error fetching file {file_id}: {db_error}")
                        continue
                    
                    if file_obj:
                        # Check file status and reprocess if needed (intelligent processing)
                        if file_obj.status != FileStatus.PROCESSED:
                            logger.info(f"[AI_CHAT_SERVICE] File {file_id} needs reprocessing (status: {file_obj.status})")
                            reprocess_success = await file_service.reprocess_file(db, file_uuid)
                            
                            if reprocess_success:
                                # Refresh file object to get updated content
                                await db.refresh(file_obj)
                                logger.info(f"[AI_CHAT_SERVICE] Successfully reprocessed file {file_id}")
                            else:
                                logger.warning(f"[AI_CHAT_SERVICE] Failed to reprocess file {file_id}")
                        
                        # Extract optimized text content for AI model using new method
                        ai_context = file_obj.get_text_for_ai_model(max_length=2000)
                        
                        # Build rich file context entry
                        file_context = f"File: {file_obj.filename} ({file_obj.file_type.value})\n{ai_context}"
                        file_contexts.append(file_context)
                        
                        logger.debug(f"[AI_CHAT_SERVICE] Processed attachment: {file_obj.filename} ({len(ai_context)} chars)")
                    
            # Consolidate all file contexts into single string
            if file_contexts:
                consolidated_context = "\n\n---FILE ATTACHMENTS---\n" + "\n\n".join(file_contexts) + "\n---END ATTACHMENTS---"
                logger.info(f"[AI_CHAT_SERVICE] Built file context for {len(file_contexts)} attachments ({len(consolidated_context)} chars total)")
                return consolidated_context
            else:
                return ""
                
        except Exception as e:
            logger.error(f"[AI_CHAT_SERVICE] Attachment processing failed: {e}")
            return ""
    
    async def _store_thread_interaction(
        self, 
        context: ThreadContext, 
        user_message: str, 
        ai_response: ChatResponse, 
        attachments: List[dict] = None,
        response_time_ms: float = None
    ):
        """Store user message and AI response in the thread"""
        
        async with get_async_db_session() as db:
            try:
                # Store user message
                user_msg = Message(
                    thread_id=UUID(context.thread_id),
                    role="user",
                    content=user_message,
                    attachments=attachments or []
                )
                db.add(user_msg)
                
                # Prepare tool calls data
                tool_calls_data = None
                if hasattr(ai_response, 'tools_used') and ai_response.tools_used:
                    tool_calls_data = [
                        {
                            "tool_name": tool_name,
                            "called_at": datetime.now(timezone.utc).isoformat(),
                            "status": "completed"
                        }
                        for tool_name in ai_response.tools_used
                    ]
                
                # Store AI response with tool calls
                ai_msg = Message(
                    thread_id=UUID(context.thread_id),
                    role="assistant",
                    content=ai_response.content,
                    tool_calls=tool_calls_data,
                    message_metadata={
                        "agent_id": context.agent_id,
                        "tools_used": ai_response.tools_used if hasattr(ai_response, 'tools_used') else [],
                        "confidence": ai_response.confidence if hasattr(ai_response, 'confidence') else None,
                        "requires_escalation": ai_response.requires_escalation if hasattr(ai_response, 'requires_escalation') else False,
                        "attachments_count": len(attachments) if attachments else 0,
                        "generation_timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    response_time_ms=int(response_time_ms) if response_time_ms else None,
                    confidence_score=ai_response.confidence if hasattr(ai_response, 'confidence') else None
                )
                db.add(ai_msg)
                
                # Commit the messages first
                await db.commit()
                
                # Update thread counters (2 messages added: user + assistant)
                from app.services.thread_service import thread_service
                await thread_service.update_message_counters(db, UUID(context.thread_id), increment_count=2)
                
                logger.debug("[AI_CHAT_SERVICE] Thread interaction stored successfully")
                
            except Exception as e:
                await db.rollback()
                logger.error(f"[AI_CHAT_SERVICE] Error storing thread interaction: {e}")
                raise
    
    async def generate_thread_title(self, message: str, context: Optional[str] = None) -> str:
        """Generate an AI-powered title for a thread"""
        try:
            await self._ensure_title_agent_initialized()
            
            prompt = f"User Message: {message}"
            if context:
                prompt += f"\n\nContext: {context}"
            prompt += "\n\nGenerate a concise, descriptive title for this customer support thread."
            
            usage_limits = UsageLimits(request_limit=3)
            result = await self.title_agent.run(prompt, usage_limits=usage_limits)
            
            if result.output and result.output.title:
                logger.info(f"✅ Generated title: '{result.output.title}' (confidence: {result.output.confidence:.2f})")
                return result.output.title
            else:
                return self._generate_fallback_title(message)
                
        except Exception as e:
            logger.error(f"❌ Title generation failed: {e}")
            return self._generate_fallback_title(message)
    
    def _generate_fallback_title(self, message: str) -> str:
        """Generate a fallback title when AI generation fails"""
        clean_message = message.strip()
        
        # Remove common prefixes
        prefixes_to_remove = ["hi", "hello", "hey", "can you", "please", "i need", "help me", "help with"]
        for prefix in prefixes_to_remove:
            if clean_message.lower().startswith(prefix):
                clean_message = clean_message[len(prefix):].strip()
        
        # Capitalize and truncate
        if clean_message:
            title = clean_message[0].upper() + clean_message[1:]
            if len(title) > 50:
                title = title[:47] + "..."
            return title
        else:
            return "Customer Support Thread"
    
    async def stream_message_to_thread(
        self,
        agent_id: str,
        thread_id: str,
        user_id: str,
        message: str,
        attachments: List[dict] = None
    ) -> AsyncIterator[str]:
        """
        Stream AI response for a thread message in real-time.
        
        Args:
            agent_id: ID of the agent handling this thread
            thread_id: ID of the thread
            user_id: ID of the user sending the message
            message: User's message content
            attachments: Optional file attachments
            
        Yields:
            str: Response chunks as they become available
        """
        
        # Get thread history and create context
        message_history = await self.get_thread_history(thread_id, user_id, agent_id, format_type=MessageFormat.SIMPLE)
        context = ThreadContext(
            user_id=user_id,
            thread_id=thread_id,
            agent_id=agent_id,
            organization_id="",
            session_history=message_history
        )
        
        try:
            # Get agent model
            agent_model = await self._get_agent_model(UUID(agent_id))
            if not agent_model or not agent_model.is_active:
                yield "Error: Agent not available. Please try again later."
                return
            
            # Store user message first
            await self._store_user_message(context, message, attachments)
            
            # For now, streaming is not supported with task-based processing
            # TODO: Implement streaming support for task-based agents
            yield "Processing your request with agent tools..."
            
            # Process message via task system (non-streaming for now)
            if agent_model.mcp_enabled:
                response = await self._process_message_via_task(context, message, agent_model, attachments)
            else:
                response = await self._process_message_direct(context, message, agent_model, attachments)
            
            # Stream the final response
            yield response.content
            
            # Store the complete AI response
            await self._store_ai_response(context, response)
            
        except Exception as e:
            logger.error(f"[AI_CHAT_SERVICE] Streaming failed: {e}")
            yield "I encountered an error. Please try again."
    
    async def _store_user_message(self, context: ThreadContext, message: str, attachments: List[dict] = None):
        """Store user message in thread"""
        async with get_async_db_session() as db:
            try:
                user_msg = Message(
                    thread_id=UUID(context.thread_id),
                    role="user",
                    content=message,
                    attachments=attachments or []
                )
                db.add(user_msg)
                await db.commit()
            except Exception as e:
                await db.rollback()
                logger.error(f"Error storing user message: {e}")
                raise
    
    async def _store_ai_response(self, context: ThreadContext, response: ChatResponse):
        """Store AI response in thread"""
        async with get_async_db_session() as db:
            try:
                ai_msg = Message(
                    thread_id=UUID(context.thread_id),
                    role="assistant",
                    content=response.content,
                    confidence_score=response.confidence if hasattr(response, 'confidence') else None
                )
                db.add(ai_msg)
                await db.commit()

                # Update thread metadata to reflect this interaction (user + assistant)
                try:
                    thread_query = select(Thread).where(Thread.id == UUID(context.thread_id))
                    result = await db.execute(thread_query)
                    thread = result.scalar_one_or_none()
                    if thread:
                        current_metadata = thread.thread_metadata or {}
                        current_metadata.update({
                            "last_message_at": datetime.now(timezone.utc).isoformat(),
                            "total_messages": current_metadata.get("total_messages", 0) + 2,
                            "last_agent_used": context.agent_id,
                            "last_tools_used": response.tools_used if hasattr(response, 'tools_used') else []
                        })
                        thread.thread_metadata = current_metadata
                        await db.commit()
                except Exception as meta_err:
                    logger.warning(f"[AI_CHAT_SERVICE] Failed to update thread metadata after streaming response: {meta_err}")
            except Exception as e:
                await db.rollback()
                logger.error(f"Error storing AI response: {e}")
    
    # Task-based agent processing methods
    async def _get_agent_model(self, agent_id: UUID):
        """Get agent model from database"""
        try:
            async with get_async_db_session() as db:
                agent_query = select(AgentModel).where(
                    AgentModel.id == agent_id,
                    AgentModel.is_active.is_(True)
                )
                result = await db.execute(agent_query)
                agent = result.scalar_one_or_none()
                
                if not agent:
                    logger.error(f"Agent {agent_id} not found or not active")
                    return None
                
                return agent
                
        except Exception as e:
            logger.error(f"Failed to get agent model: {e}")
            return None
    
    
    async def _create_fallback_response(self, error_message: str) -> ChatResponse:
        """Create fallback response for error cases"""
        return ChatResponse(
            content=error_message,
            confidence=0.0,
            requires_escalation=True,
            tools_used=[]
        )


# Global service instance
ai_chat_service = AIChatService()