#!/usr/bin/env python3
"""
Dynamic Agent Factory for creating Pydantic AI agents from Agent models

This factory replaces the hardcoded CustomerSupportAgent by creating Pydantic AI
agents dynamically based on Agent model configuration, with direct MCP integration.
"""

import logging
from typing import Optional, Dict, Any, List
from pydantic_ai import Agent as PydanticAgent
from pydantic_ai.usage import UsageLimits
from pydantic_ai.messages import ModelMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_agent import Agent as AgentModel
from app.schemas.ai_response import ChatResponse, AgentContext
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
    
    async def create_agent_from_model(self, agent_model: AgentModel, auth_token: Optional[str] = None) -> Optional[PydanticAgent]:
        """
        Create a Pydantic AI agent from Agent model configuration with optional authentication.
        
        Args:
            agent_model: Agent database model with configuration
            auth_token: JWT token for MCP authentication (optional)
            
        Returns:
            PydanticAgent: Configured agent with MCP tools if enabled
        """
        try:
            # Check cache first - include auth status in cache key
            auth_hash = hash(auth_token) if auth_token else "no_auth"
            cache_key = f"{agent_model.id}_{agent_model.updated_at}_{auth_hash}"
            if cache_key in self._agent_cache:
                auth_status = "authenticated" if auth_token else "non-authenticated"
                logger.debug(f"Using cached {auth_status} agent for {agent_model.id}")
                return self._agent_cache[cache_key]
            
            if not agent_model.is_ready:
                logger.error(f"Agent {agent_model.id} is not ready")
                return None
            
            # Get agent configuration
            config = agent_model.get_configuration()
            tools_enabled = config.get("tools_enabled", [])
            
            logger.info(f"Creating Pydantic AI agent for {agent_model.id} with {len(tools_enabled)} tools")
            
            # Get model string
            model_string = self._get_model_string(agent_model, config)
            
            # Get system prompt
            system_prompt = agent_model.prompt or "You are a helpful AI assistant."
            
            # Create MCP client if agent has tools enabled
            toolsets = []
            if agent_model.mcp_enabled and tools_enabled:
                # Create authenticated MCP client if token provided
                agent_client = mcp_client.get_agent_client(
                    agent_id=str(agent_model.id),
                    tools_enabled=tools_enabled,
                    organization_id=str(agent_model.organization_id),
                    auth_token=auth_token
                )
                
                if agent_client:
                    toolsets = [agent_client]
                    auth_status = "authenticated" if auth_token else "non-authenticated"
                    logger.info(f"Agent {agent_model.id} configured with {auth_status} MCP tools: {tools_enabled}")
                else:
                    auth_status = "authenticated" if auth_token else "non-authenticated"
                    logger.warning(f"Failed to create {auth_status} MCP client for agent {agent_model.id}")
            else:
                logger.info(f"🚨 MCP tools temporarily disabled for debugging - agent {agent_model.id} will run without tools")
            
            # Create Pydantic AI agent
            if toolsets:
                pydantic_agent = PydanticAgent(
                    model=model_string,
                    output_type=ChatResponse,
                    system_prompt=system_prompt,
                    toolsets=toolsets
                )
                logger.info(f"✅ Created Pydantic AI agent with MCP tools for {agent_model.id}")
            else:
                pydantic_agent = PydanticAgent(
                    model=model_string,
                    output_type=ChatResponse,
                    system_prompt=system_prompt
                )
                logger.info(f"✅ Created Pydantic AI agent without tools for {agent_model.id}")
            
            # Cache the agent
            self._agent_cache[cache_key] = pydantic_agent
            
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
        organization_id: Optional[str] = None
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
            
            # Add file context if available
            if file_context:
                base_context["uploaded_files"] = [file_context]
                base_context["has_attachments"] = True
            else:
                base_context["uploaded_files"] = []
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
                uploaded_files=[],
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
            uploaded_files=final_context["uploaded_files"],
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
        auth_token: Optional[str] = None,
        thread_id: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> ChatResponse:
        """
        Process message with conversation history support.
        
        Args:
            agent_model: Agent configuration
            message: User message
            context: Chat context
            auth_token: JWT token for MCP authentication (optional)
            thread_id: Thread ID for message history (optional)
            db: Database session for history retrieval (optional)
            
        Returns:
            ChatResponse: Agent response with tool usage
        """
        try:
            # Create agent from model with authentication support
            pydantic_agent = await self.create_agent_from_model(agent_model, auth_token=auth_token)
            
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
            if thread_id and agent_model.use_memory_context:
                try:
                    from app.services.ai_chat_service import ai_chat_service, MessageFormat
                    
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
            
            # Configure usage limits
            usage_limits = UsageLimits(request_limit=agent_model.max_iterations)
            
            # CORRECT PYDANTIC AI USAGE - Use message_history parameter
            if message_history:
                # Run agent with conversation history
                result = await pydantic_agent.run(
                    message,
                    message_history=message_history,  # Correct parameter usage
                    usage_limits=usage_limits
                )
            else:
                # Run agent without history
                result = await pydantic_agent.run(
                    message,
                    usage_limits=usage_limits
                )
            
            # Extract response and tools used
            if hasattr(result, 'output'):
                response = result.output
            else:
                response = result
            
            tools_used = getattr(result, 'tools_used', []) or []
            if tools_used:
                logger.info(f"🔧 MCP Tools used: {tools_used}")
            
            
            # Record usage statistics
            from app.services.ai_agent_service import ai_agent_service
            await ai_agent_service.record_agent_usage(
                agent_id=agent_model.id,
                success=True,
                tools_called=len(tools_used)
            )
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error processing message with dynamic agent: {e}")
            
            # Record failed usage
            try:
                from app.services.ai_agent_service import ai_agent_service
                await ai_agent_service.record_agent_usage(
                    agent_id=agent_model.id,
                    success=False
                )
            except:
                pass
            
            return ChatResponse(
                content="I encountered an error processing your request. Please try again or contact support if the issue persists.",
                confidence=0.0,
                requires_escalation=True,
                tools_used=[]
            )
    


# Global dynamic agent factory
dynamic_agent_factory = DynamicAgentFactory()