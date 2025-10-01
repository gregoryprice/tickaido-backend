#!/usr/bin/env python3
"""
Dynamic Agent Factory for creating Pydantic AI agents from Agent models

This factory replaces the hardcoded CustomerSupportAgent by creating Pydantic AI
agents dynamically based on Agent model configuration, with direct MCP integration.
"""
import logging
from typing import Any, Dict, List, Optional

from pydantic_ai import Agent as PydanticAgent
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.messages import ModelMessage
from pydantic_ai.usage import UsageLimits
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.models.ai_agent import Agent as AgentModel
from app.schemas.ai_response import AgentContext, ChatResponse
from app.schemas.principal import Principal
from app.services.agent_service import agent_service
from mcp_client.client import mcp_client

logger = logging.getLogger(__name__)


class DynamicAgentFactory:
    """
    Factory for creating Pydantic AI agents from Agent model configurations.
    
    This replaces the hardcoded CustomerSupportAgent approach with a dynamic
    system that works with any Agent model configuration.
    """
    
    def __init__(self):
        """Initialize the dynamic agent factory."""
        self._agent_cache = {}  # Cache created agents
    
    async def create_agent(self, agent_model: AgentModel, principal: Optional['Principal'] = None) -> Optional[PydanticAgent]:
        """
        Create a Pydantic AI agent from Agent model configuration with Principal-based authorization.
        
        Args:
            agent_model: Agent database model with configuration
            principal: Principal object for authorization (from AuthMiddleware)
            
        Returns:
            PydanticAgent: Configured agent with MCP tools and Principal context
        """
        try:
            # Check cache first - include principal status in cache key
            # cache_key = None
            # if principal:
            #     cache_key = principal.get_cache_hash()

            # if cache_key in self._agent_cache:
            #     auth_status = "authenticated" if principal else "non-authenticated"
            #     logger.debug(f"Using cached {auth_status} agent for {agent_model.id}")
            #     return self._agent_cache[cache_key]
            
            if not agent_model.is_ready:
                logger.error(f"Agent {agent_model.id} is not ready")
                return None
            
            # Get agent configuration
            config = agent_model.get_configuration()
            tools = config.get("tools", [])
            
            logger.info(f"Creating Pydantic AI agent for {agent_model.id} with {len(tools)} tools")
            
            # Get model string
            model_string = self._get_model_string(agent_model, config)
            
            # Get prompt
            agent_prompt = agent_model.prompt or "You are a helpful AI assistant."
            
            # Create authenticated MCP client with Principal integration
            toolsets = []
            if tools:
                logger.info(f"🔍 [TRACE] Tools enabled: {tools}")
                
                if principal:
                    try:
                        # Get agent-specific authenticated MCP client from global mcp_client
                        agent_mcp_client = mcp_client.create_agent_client(
                            agent_id=str(agent_model.id),
                            tools=tools,
                            principal=principal
                        )
                        
                        if agent_mcp_client:
                            toolsets = [agent_mcp_client]
                            logger.info(f"✅ Created authenticated MCP toolset for {agent_model.id} with {len(tools)} tools")
                        else:
                            logger.error(f"❌ Failed to create authenticated MCP toolset for {agent_model.id}")
                            toolsets = []
                            
                    except Exception as e:
                        logger.error(f"❌ Failed to create authenticated FastMCP client for agent {agent_model.id}: {e}")
                        toolsets = []
                else:
                    # No principal provided - cannot create authenticated MCP client
                    logger.warning(f"⚠️ No principal provided for agent {agent_model.id} - cannot create authenticated MCP toolset")
                    # Fallback to unauthenticated mode for backward compatibility
                    try:
                        # Use the global mcp_client's server URL but without authentication
                        unauthenticated_client = mcp_client.create_mcp_client(principal=None)
                        if unauthenticated_client:
                            toolsets = [unauthenticated_client]
                            logger.info(f"⚠️ Created unauthenticated MCP toolset for {agent_model.id} as fallback")
                        else:
                            toolsets = []
                    except Exception as e:
                        logger.error(f"❌ Failed to create fallback unauthenticated MCP client: {e}")
                        toolsets = []
            else:
                logger.info(f"ℹ️ No tools configured for agent {agent_model.id}")
            
            # Create Pydantic AI agent with Principal dependencies support
            # Follow official PydanticAI dependencies pattern: https://ai.pydantic.dev/dependencies/
            # Use instructions instead of system_prompt as recommended: https://ai.pydantic.dev/agents/#instructions
            if toolsets:
                pydantic_agent = PydanticAgent(
                    model=model_string,
                    deps_type=Principal,  # Define dependencies type
                    output_type=ChatResponse,
                    instructions=agent_prompt,
                    toolsets=toolsets,
                    end_strategy="exhaustive"
                )
                logger.info(f"✅ Created Pydantic AI agent with FastMCP tools and Principal dependencies for {agent_model.id}")
            else:
                pydantic_agent = PydanticAgent(
                    model=model_string,
                    deps_type=Principal,  # Define dependencies type
                    output_type=ChatResponse,
                    instructions=agent_prompt,
                    end_strategy="exhaustive"
                )
                logger.info(f"✅ Created Pydantic AI agent with Principal dependencies (no FastMCP tools) for {agent_model.id}")
            
            # Cache the agent
            # self._agent_cache[cache_key] = pydantic_agent
            
            return pydantic_agent
            
        except Exception as e:
            logger.error(f"❌ Failed to create agent from model {agent_model.id}: {e}")
            return None
    
    def _get_model_string(self, agent_model: AgentModel, config: Dict[str, Any]) -> str:
        """
        Get model string for Pydantic AI from Agent configuration.
        
        Args:
            agent_model: Agent model
            config: Agent configuration
            
        Returns:
            str: Model string (e.g., "openai:gpt-4o-mini")
        """
        # Use agent model fields if available, fallback to config
        provider = getattr(agent_model, 'model_provider', None) or config.get("model_provider", "openai")
        model_name = getattr(agent_model, 'model_name', None) or config.get("model_name", "primary")
        
        # Map model names to actual models
        model_mapping = {
            "primary": "gpt-4o-mini",
            "backup": "gpt-4", 
            "fast": "gpt-3.5-turbo"
        }
        
        actual_model = model_mapping.get(model_name, model_name)
        return f"{provider}:{actual_model}"
    
    async def build_context(
        self,
        agent_type: str,
        message: str,
        conversation_history: List[Dict[str, Any]],
        file_context: str,
        user_metadata: Dict[str, Any],
        session_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        file_ids: Optional[List[str]] = None
    ) -> Any:
        """
        Build appropriate context based on agent type.
        
        This replaces the hardcoded CustomerSupportContext approach with a generic
        system that can create different context types for different agents.
        
        Args:
            agent_type: Type of agent (customer_support, technical_support, etc.)
            message: User input message
            conversation_history: Previous messages in conversation
            file_context: Processed file attachment context
            user_metadata: User information and session data
            session_id: Optional session/thread ID
            organization_id: Optional organization ID
            file_ids: Optional list of file IDs for tool calls
            
        Returns:
            Context object appropriate for the agent type
        """
        try:
            # Prepare common context data
            base_context = {
                "user_input": message,
                "conversation_history": conversation_history,
                "user_metadata": user_metadata,
                "session_id": session_id or user_metadata.get("thread_id"),
                "organization_id": organization_id or user_metadata.get("organization_id")
            }
            
            # Add file context and IDs if available
            if file_context or file_ids:
                base_context["attachments"] = [file_context] if file_context else []
                base_context["file_ids"] = file_ids or []
                base_context["has_attachments"] = True
            else:
                base_context["attachments"] = []
                base_context["file_ids"] = []
                base_context["has_attachments"] = False
            
            # Apply agent-specific customizations to base context
            context_customizations = self._get_agent_context_customizations(agent_type, base_context)
            
            # Build and return the agent context
            return self._create_agent_context(base_context, context_customizations)
                
        except Exception as e:
            logger.error(f"Failed to build context for agent type '{agent_type}': {e}")
            # Return minimal fallback context
            return AgentContext(
                user_input=message,
                attachments=[],
                file_ids=file_ids or [],
                conversation_history=[],
                user_metadata=user_metadata,
                session_id=session_id,
                organization_id=organization_id
            )
    
    def _get_agent_context_customizations(self, agent_type: str, base_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get agent-specific context customizations.
        
        Args:
            agent_type: Type of agent (customer_support, technical_support, etc.)
            base_context: Base context dictionary
            
        Returns:
            Dict containing customizations to apply
        """
        if agent_type in ["customer_support", "support", "customer_service"]:
            # Default customer support - no special customizations
            return {}
        
        elif agent_type in ["technical_support", "tech", "developer"]:
            # Technical support context - add context type
            return {
                "user_metadata": {**base_context["user_metadata"], "context_type": "technical"}
            }
        
        elif agent_type in ["document_analysis", "document", "analysis"]:
            # Document analysis context - shorter history, add context type
            return {
                "conversation_history": base_context["conversation_history"][:5],  # Shorter history for document focus
                "user_metadata": {**base_context["user_metadata"], "context_type": "document_analysis"}
            }
        
        else:
            # Generic/fallback context for unknown agent types
            logger.warning(f"Unknown agent type '{agent_type}', using generic context")
            return {
                "user_metadata": {**base_context["user_metadata"], "context_type": "generic"}
            }
    
    def _create_agent_context(self, base_context: Dict[str, Any], customizations: Dict[str, Any]) -> AgentContext:
        """
        Create an AgentContext with base context and customizations applied.
        
        Args:
            base_context: Base context dictionary
            customizations: Agent-specific customizations to apply
            
        Returns:
            AgentContext with customizations applied
        """
        # Apply customizations to base context
        final_context = base_context.copy()
        final_context.update(customizations)
        
        # Create and return AgentContext
        return AgentContext(
            user_input=final_context["user_input"],
            attachments=final_context["attachments"],
            file_ids=final_context["file_ids"],
            conversation_history=final_context["conversation_history"],
            user_metadata=final_context["user_metadata"],
            session_id=final_context["session_id"],
            organization_id=final_context["organization_id"]
        )
    
    async def process_message_with_agent(
        self,
        agent_model: AgentModel,
        message: str,
        context: AgentContext,
        principal: Optional['Principal'] = None,
        thread_id: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> ChatResponse:
        """
        Process message with conversation history support and Principal-based authorization.
        
        Args:
            agent_model: Agent configuration
            message: User message
            context: Chat context
            principal: Principal object for authorization (from AuthMiddleware)
            thread_id: Thread ID for message history (optional)
            db: Database session for history retrieval (optional)
            
        Returns:
            ChatResponse: Agent response with tool usage
        """
        try:
            # Create agent from model with Principal support
            pydantic_agent = await self.create_agent(agent_model, principal=principal)
            
            if not pydantic_agent:
                logger.error(f"Failed to create agent from model {agent_model.id}")
                return ChatResponse(
                    content="I'm temporarily unavailable. Please try again shortly.",
                    confidence=0.0,
                    requires_escalation=True,
                    tools_used=[]
                )
            
            # Retrieve message history in proper ModelMessage format  
            message_history: List[ModelMessage] = []
            # Temporarily disable memory context to test FastMCP integration
            if False and thread_id and agent_model.use_memory_context:
                try:
                    from app.services.ai_chat_service import MessageFormat, ai_chat_service
                    
                    # Get user info from context if available
                    user_id = context.user_metadata.get('user_id', 'system')
                    
                    # Use consolidated method to get ModelMessage format
                    message_history = await ai_chat_service.get_thread_history(
                        thread_id=thread_id,
                        user_id=user_id,
                        agent_id=str(agent_model.id),
                        format_type=MessageFormat.MODEL_MESSAGE,
                        max_context_size=agent_model.max_context_size,
                        use_memory_context=agent_model.use_memory_context
                    )
                    
                    logger.info(
                        f"Loaded {len(message_history)} ModelMessages for context "
                        f"(thread: {thread_id})"
                    )
                except Exception as e:
                    logger.error(f"Failed to load ModelMessages for thread {thread_id}: {e}")
                    # Continue without history rather than failing completely
                    message_history = []
            
            # Configure usage limits based on agent configuration with settings defaults
            
            settings = get_settings()
            
            # TODO: token limits in agents instead of hardcoded settings
            usage_limits = UsageLimits(
                request_limit=max(settings.ai_request_limit, agent_model.max_iterations),  # Ensure minimum requests for FastMCP
                total_tokens_limit=max(settings.ai_total_tokens_limit, 250000)  # Ensure minimum for FastMCP tool calls
            )
            logger.info(f"🔍 [TRACE] Usage limits: request_limit={usage_limits.request_limit}, total_tokens_limit={usage_limits.total_tokens_limit}")
            
            # Enhance message with file ID information if attachments are present
            enhanced_message = message
            file_ids = context.file_ids or []
            if file_ids:
                file_ids_str = ','.join(file_ids)
                enhanced_message = f"{message}\n\n[CONTEXT: User has uploaded {len(file_ids)} file(s) with IDs: {file_ids_str}. When creating tickets or using tools that support file attachments, use these file IDs with the file_ids parameter.]"
                logger.info(f"🔍 [TRACE] Enhanced message with file_ids: {file_ids}")
            
            # CORRECT PYDANTIC AI USAGE - Use message_history and deps for Principal context
            if message_history:
                # Run agent with conversation history and Principal context
                result = await pydantic_agent.run(
                    enhanced_message,
                    message_history=message_history,  # Conversation history
                    usage_limits=usage_limits,
                    deps=principal  # Principal context for tools
                )
            else:
                # Run agent without history but with Principal context
                result = await pydantic_agent.run(
                    enhanced_message,
                    usage_limits=usage_limits,
                    deps=principal  # Principal context for tools
                )
            
            # Extract response and tools used
            if hasattr(result, 'output'):
                response = result.output
            else:
                response = result
            
            # Extract actual tool calls from messages
            tool_calls = []
            tools_used = []
            
            try:
                messages = result.all_messages()
                for msg in messages:
                    if hasattr(msg, 'parts'):
                        for part in msg.parts:
                            part_type = type(part).__name__
                            
                            if 'ToolCall' in part_type:
                                tool_info = {
                                    'tool_name': getattr(part, 'tool_name', None),
                                    'args': getattr(part, 'args', None),
                                    'tool_call_id': getattr(part, 'tool_call_id', None),
                                    'called_at': str(msg.timestamp) if hasattr(msg, 'timestamp') else None,
                                    'status': 'pending'
                                }
                                tool_calls.append(tool_info)
                                tools_used.append(tool_info['tool_name'])
                                
                            elif 'ToolReturn' in part_type:
                                # Update status of matching tool call
                                tool_call_id = getattr(part, 'tool_call_id', None)
                                for tool_call in tool_calls:
                                    if tool_call['tool_call_id'] == tool_call_id:
                                        tool_call['status'] = 'completed'
                                        tool_call['result'] = getattr(part, 'content', None)
                                        
            except Exception as e:
                logger.warning(f"Failed to extract tool calls from result: {e}")
            
            # Add tool information to response
            if hasattr(response, 'tools_used'):
                response.tools_used = tools_used
            else:
                # If response is a string, create a ChatResponse object
                if isinstance(response, str):
                    response = ChatResponse(
                        content=response,
                        confidence=1.0,
                        requires_escalation=False,
                        tools_used=tools_used
                    )
            
            # Store tool calls for later use in service layer
            if hasattr(result, '_tool_calls_data'):
                result._tool_calls_data = tool_calls
            else:
                # Add as a new attribute
                result._tool_calls_data = tool_calls
            
            if tools_used:
                logger.info(f"🔧 FastMCP Tools used: {tools_used}")
            if tool_calls:
                logger.debug(f"🔧 Tool calls data: {tool_calls}")
            
            
            # Record usage statistics
            try:
                await agent_service.record_agent_usage(
                    agent_id=agent_model.id,
                    success=True,
                    tools_called=len(tools_used)
                )
            except Exception as usage_error:
                logger.warning(f"Failed to record agent usage: {usage_error}")
            
            # Add tool calls data to response for service layer access
            if hasattr(response, '_tool_calls_data'):
                response._tool_calls_data = tool_calls
            else:
                # Add as a new attribute to response
                try:
                    response._tool_calls_data = tool_calls
                except AttributeError:
                    # If response is immutable, that's fine - service layer will use tools_used fallback
                    pass
            
            return response
            
        except UsageLimitExceeded as e:
            # Handle tool count limit specifically
            logger.error(f"❌ Tool usage limit exceeded: {e}")
            
            # Record failed usage
            try:
                await agent_service.record_agent_usage(
                    agent_id=agent_model.id,
                    success=False
                )
            except Exception as usage_error:
                logger.warning(f"Failed to record failed agent usage: {usage_error}")
            
            return ChatResponse(
                content="This request exceeded the tool usage limit. Please try with a more specific request or increase the limits of this agent.",
                confidence=0.0,
                requires_escalation=True,
                tools_used=[]
            )
        except Exception as e:
            # Enhanced error logging for TaskGroup and other async issues
            import traceback
            logger.error(f"❌ Error processing message with dynamic agent: {e}")
            logger.error(f"❌ Exception type: {type(e).__name__}")
            logger.error(f"❌ Full traceback:\n{traceback.format_exc()}")
            
            # Check for specific TaskGroup exception details
            if hasattr(e, '__cause__') and e.__cause__:
                logger.error(f"❌ Root cause: {e.__cause__}")
            if hasattr(e, 'exceptions'):
                logger.error(f"❌ Sub-exceptions: {e.exceptions}")
                
            # Record failed usage
            try:
                await agent_service.record_agent_usage(
                    agent_id=agent_model.id,
                    success=False
                )
            except Exception as usage_error:
                logger.warning(f"Failed to record failed agent usage: {usage_error}")
            
            return ChatResponse(
                content="I encountered an error processing your request. Please try again or contact support if the issue persists.",
                confidence=0.0,
                requires_escalation=True,
                tools_used=[]
            )
    


# Global dynamic agent factory
dynamic_agent_factory = DynamicAgentFactory()