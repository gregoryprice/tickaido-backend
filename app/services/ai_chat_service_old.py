"""
AI Chat Service for Customer Support

This service provides AI-powered chat functionality for customer support operations.
It integrates with the MCP server to provide access to customer support tools
including ticket creation, file analysis, knowledge base search, and integrations.

The service uses PydanticAI agents with MCP server integration to provide
intelligent responses to customer support queries.

For more information on PydanticAI, see: https://ai.pydantic.dev/
For more information on MCP, see: https://ai.pydantic.dev/mcp/
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, AsyncIterator
from uuid import UUID
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.usage import UsageLimits
from sqlalchemy import select

from app.services.ai_config_service import ai_config_service
from app.models.chat import Thread, Message
from app.database import get_async_db_session
# Legacy import - customer_support_agent is now organization-scoped
from app.agents.title_generation_agent import title_generation_agent
from mcp_client.client import mcp_client
from app.services.enhanced_mcp_service import enhanced_mcp_service
from app.services.ai_config_service import ai_config_service
from app.services.ai_agent_service import ai_agent_service
from app.schemas.ai_response import ChatResponse, CustomerSupportContext

logger = logging.getLogger(__name__)




class ChatContext(BaseModel):
    """Enhanced context for chat operations with secure authentication"""
    user_id: str
    conversation_id: str
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
    
    async def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission"""
        if not self._auth_container:
            return False
        return permission in self._auth_container.permissions
    
    @property
    def has_valid_auth(self) -> bool:
        """Check if context has valid authentication"""
        return (self._auth_container is not None and 
                not self._auth_container.is_expired and 
                self._original_token is not None)
    
    @classmethod
    async def create_with_auth(
        cls, 
        user_id: str, 
        conversation_id: str,
        token: str,
        auth_provider: Any,
        **kwargs
    ) -> "ChatContext":
        """Factory method with enhanced security validation"""
        container = await auth_provider.validate_token(token)
        if not container or container.user_id != user_id:
            raise ValueError("Invalid token for user")
            
        instance = cls(user_id=user_id, conversation_id=conversation_id, **kwargs)
        instance._auth_container = container
        instance._auth_provider = auth_provider
        instance._original_token = token
        return instance


class TitleGenerationResponse(BaseModel):
    """Structured response for title generation"""
    title: str = Field(description="Generated conversation title")
    confidence: float = Field(description="Confidence in title generation (0-1)", ge=0, le=1)


async def get_configured_chat_provider() -> str:
    """
    Get AI provider configured for chat using existing infrastructure.
    
    Returns:
        str: Provider string in format "provider:model" (e.g., "openai:gpt-4")
    """
    try:
        # Use the customer support agent's configuration
        ai_config = await ai_config_service.get_agent_config("customer_support_agent")
        
        if not ai_config:
            logger.warning("No customer support agent config found, using defaults")
            model_provider = "openai:gpt-4o-mini"
        else:
            # Build provider string from config
            provider = ai_config.get("model_provider", "openai")
            model = ai_config.get("model_name", "gpt-4o-mini")
            
            # Map model configuration names to actual model names
            if model == 'primary':
                model = 'gpt-4o-mini'
            elif model == 'fast':
                model = 'gpt-3.5-turbo'
                
            model_provider = f"{provider}:{model}"
        
    except Exception as e:
        logger.warning(f"Could not load AI config, using defaults: {e}")
        model_provider = "openai:gpt-4o-mini"
    
    logger.info(f"Using AI provider: {model_provider}")
    return model_provider


async def get_title_generation_provider() -> str:
    """
    Get AI provider configured for title generation.
    Uses a faster, more cost-effective model for title generation.
    
    Returns:
        str: Provider string in format "provider:model"
    """
    try:
        # Use faster model for title generation
        ai_config = await ai_config_service.get_agent_config("customer_support")
        
        if not ai_config:
            logger.warning("No customer support config found, using defaults for titles")
            title_provider = "openai:gpt-3.5-turbo"
        else:
            # Use a faster model for titles if available
            provider = ai_config.get("model_provider", "openai")
            # Default to a faster model for titles
            model = "gpt-3.5-turbo" if provider == "openai" else ai_config.get("model_name", "gpt-4")
            title_provider = f"{provider}:{model}"
        
    except Exception as e:
        logger.warning(f"Could not load AI config for titles, using defaults: {e}")
        title_provider = "openai:gpt-3.5-turbo"
    
    logger.info(f"Using AI provider for titles: {title_provider}")
    return title_provider


async def generate_conversation_title_comprehensive(
    conversation_id: str,
    user_id: str
) -> Optional[TitleGenerationResponse]:
    """
    Generate a comprehensive title suggestion for a conversation using the dedicated title generation agent.
    
    This method is READ-ONLY and does not modify the conversation in the database.
    It analyzes all messages in the conversation and returns a title suggestion.
    
    Args:
        conversation_id: ID of the conversation to generate title for
        user_id: ID of the user (for authorization)
        
    Returns:
        Optional[TitleGenerationResponse]: Title suggestion with confidence score, or None if conversation not found
    """
    from uuid import UUID
    from sqlalchemy import select
    
    try:
        async with get_async_db_session() as db:
            # Verify user owns conversation and get conversation data
            conversation_query = select(ChatConversation).where(
                ChatConversation.id == UUID(conversation_id),
                ChatConversation.user_id == user_id,
                ChatConversation.is_deleted.is_(False)
            )
            
            result = await db.execute(conversation_query)
            conversation = result.scalar_one_or_none()
            
            if not conversation:
                logger.warning(f"[AI_CHAT_SERVICE] Conversation {conversation_id} not found for user {user_id}")
                return None
            
            # Get all messages for the conversation
            messages_query = select(ChatMessage).where(
                ChatMessage.conversation_id == UUID(conversation_id)
            ).order_by(ChatMessage.created_at)
            
            result = await db.execute(messages_query)
            messages = result.scalars().all()
            
            logger.info(f"[AI_CHAT_SERVICE] Generating title for conversation {conversation_id} with {len(messages)} messages")
            
            # Use the dedicated title generation agent
            await title_generation_agent.ensure_initialized()
            title_result = await title_generation_agent.generate_title(
                messages=list(messages),
                current_title=conversation.title
            )
            
            logger.info(f"[AI_CHAT_SERVICE] Generated title suggestion: '{title_result.title}' (confidence: {title_result.confidence:.2f})")
            
            return TitleGenerationResponse(
                title=title_result.title,
                confidence=title_result.confidence
            )
            
    except Exception as e:
        logger.error(f"[AI_CHAT_SERVICE] Error generating title for conversation {conversation_id}: {e}")
        logger.error(f"[AI_CHAT_SERVICE] Error type: {type(e).__name__}")
        return None


# Customer support chat prompt
CUSTOMER_SUPPORT_CHAT_PROMPT = """
You are an AI Customer Support Assistant for a comprehensive support ticket management system. You help users with:

1. **Issue Resolution**: Understand problems and provide step-by-step solutions
2. **Ticket Management**: Create, update, search, and manage support tickets with full lifecycle support
3. **Integration Discovery**: Find and work with third-party systems (Jira, ServiceNow, Salesforce, etc.)
4. **System Monitoring**: Check system health and integration status
5. **Analytics & Reporting**: Provide ticket statistics and insights
6. **Escalation Management**: Identify when issues need human expert attention

Guidelines:
- Be professional, empathetic, and solution-focused
- Ask clarifying questions to understand the full context
- Provide clear, actionable guidance with step-by-step instructions
- Always explain what tools you're using and why
- Escalate complex technical issues or when users explicitly request human assistance
- Maintain conversation context and reference previous interactions appropriately

**Available MCP Tools (13 tools organized by category):**

**🎫 TICKET MANAGEMENT TOOLS (10 tools):**
Complete ticket lifecycle management with full API schema support.

Ticket Creation:
  * create_ticket: Create support tickets with full schema (title, description, category, priority, urgency, department, assigned_to_id, integration, create_externally, custom_fields, file_ids)
  * create_ticket_with_ai: AI-powered ticket creation with automatic categorization

Ticket Retrieval & Management:
  * get_ticket: Retrieve specific ticket details by ID
  * update_ticket: Update existing ticket fields (title, description, status, priority, category)
  * delete_ticket: Delete specific tickets by ID
  * search_tickets: Search and filter tickets with pagination (query, status, category, priority, page, page_size)
  * list_tickets: List tickets with optional filtering and pagination

Ticket Operations:
  * update_ticket_status: Update ticket status (open, in_progress, resolved, closed)
  * assign_ticket: Assign tickets to specific users or teams
  * get_ticket_stats: Retrieve comprehensive ticket statistics and analytics

**🔗 INTEGRATION TOOLS (2 tools):**
Integration discovery and management for external system routing.

  * list_integrations: List available integrations (jira, servicenow, salesforce, zendesk, github, slack, teams, zoom, hubspot, freshdesk, asana, trello, webhook, email, sms)
  * get_active_integrations: Get active integrations with health status and capabilities

**🔍 SYSTEM TOOLS (1 tool):**
System health monitoring and status reporting.

  * get_system_health: Check backend system health and status

**Tool Usage Strategy:**

For Issue Reporting:
- Use create_ticket_with_ai for new issues (leverages AI categorization)
- Use create_ticket for specific routing needs or custom field requirements
- Use get_active_integrations to check available external systems before routing

For Issue Research:
- Use search_tickets to find related or existing tickets
- Use list_tickets with filters for broader exploration
- Use get_ticket for detailed ticket information

For Issue Management:
- Use update_ticket_status to change ticket status as issues progress
- Use assign_ticket to route tickets to appropriate teams
- Use update_ticket for general ticket field updates

For Analytics & Monitoring:
- Use get_ticket_stats for comprehensive analytics and reporting
- Use get_system_health to check backend system status
- Use list_integrations to understand available integration options

**Response Format:**
- Provide clear, conversational responses
- Use bullet points for multi-step instructions
- Include relevant ticket IDs or integration names when available
- Be concise but thorough in explanations
- Always mention which tools you're using and the results

**Example Tool Usage:**
- "What integrations are active?" → Use get_active_integrations
- "Create a ticket for login issues" → Use create_ticket_with_ai
- "Show recent high priority tickets" → Use search_tickets with priority filter
- "Get ticket T-12345 details" → Use get_ticket
- "Update ticket status to resolved" → Use update_ticket_status

Remember: Your goal is to resolve user issues efficiently while ensuring they feel heard and supported. Use the comprehensive tool set to provide thorough assistance with ticket management, integration routing, and system monitoring.
"""

# Title generation prompt
TITLE_GENERATION_PROMPT = """
You are a Customer Support Conversation Title Generator. Your task is to create concise, descriptive titles for customer support chat conversations.

Guidelines:
- Create titles that are 3-8 words long
- Focus on the main issue or request being discussed
- Use customer support terminology when appropriate
- Make titles searchable and meaningful for support staff
- Avoid generic titles like "Customer Support Chat"
- Consider the urgency and type of issue

Examples:
- "Login Issues with Password Reset"
- "Email Integration Setup Help"
- "Billing Discrepancy Resolution"
- "Feature Request: Export Functionality"
- "Bug Report: Dashboard Loading"
- "Account Access Troubleshooting"
- "Installation Guide Support"

Generate a title that captures the essence of the support conversation.
"""


async def get_organization_chat_agent(organization_id: UUID) -> Optional['CustomerSupportAgent']:
    """
    Get organization's customer support agent (auto-creates if missing).
    
    This implements the "Agent Availability Guarantee" from the PRP - every organization
    gets a customer support agent automatically with defaults from ai_config.yaml.
    
    Args:
        organization_id: Organization UUID
        
    Returns:
        CustomerSupportAgent: Organization's agent (existing or newly created)
    """
    try:
        # Use service layer to ensure organization has an agent
        agent_config = await ai_agent_service.ensure_organization_agent(organization_id)
        
        if not agent_config:
            logger.error(f"Failed to ensure agent for organization {organization_id}")
            return None
            
        # Import here to avoid circular imports
        # NOTE: CustomerSupportAgent removed per agent architecture refactor
        # from app.agents.customer_support_agent import CustomerSupportAgent
        
        # Create the refactored customer support agent
        # NOTE: CustomerSupportAgent removed per agent architecture refactor
        # agent = CustomerSupportAgent(str(organization_id), agent_config)
        # await agent.initialize()
        
        # if agent.is_active():
        # Placeholder return for now since CustomerSupportAgent is removed
        logger.info(f"✅ Organization {organization_id} agent placeholder (CustomerSupportAgent removed)")
        return None
        
    except Exception as e:
        logger.error(f"❌ Failed to get organization chat agent: {e}")
        return None


async def create_chat_agent() -> Agent:
    """
    Create chat agent with MCP server integration.
    
    This function creates a PydanticAI agent that can use MCP server tools
    for customer support operations. The agent is configured with:
    - AI model provider (OpenAI, Google, etc.)
    - Structured response format (ChatResponse)
    - System prompt for customer support
    - MCP server tools for ticket management, file analysis, etc.
    
    Returns:
        Agent: Configured PydanticAI agent with MCP server integration
    """
    try:
        # Load configuration from ai_config.yaml
        config = await ai_config_service.load_default_agent_configuration()
        logger.info("Loading agent configuration from ai_config.yaml")
        
        # Get MCP client from the global instance
        mcp_client_instance = mcp_client.get_mcp_client()
        
        # Create agent WITH MCP tools integration using config-driven approach
        mcp_server = mcp_client_instance
        
        if mcp_server and config.get("mcp_enabled", True):
            # Create agent with MCP toolset for comprehensive tool calling
            agent = Agent(
                await get_configured_chat_provider(),
                output_type=ChatResponse,
                system_prompt=config["system_prompt"],  # Load from ai_config.yaml
                toolsets=[mcp_server]  # Enable MCP tool integration
            )
            logger.info(f"✅ Customer Support chat agent created WITH MCP tools integrated ({len(config.get('tools_enabled', []))} tools from configuration)")
        else:
            # Fallback: Create agent without tools if MCP unavailable or disabled
            agent = Agent(
                await get_configured_chat_provider(),
                output_type=ChatResponse,
                system_prompt=config["system_prompt"]  # Still use config-driven prompt
            )
            if not config.get("mcp_enabled", True):
                logger.warning("⚠️ Customer Support chat agent created without MCP tools (disabled in configuration)")
            else:
                logger.warning("⚠️ Customer Support chat agent created without MCP tools (server unavailable)")
        
        # Log MCP integration status
        connection_info = mcp_client.get_connection_info()
        if mcp_client_instance and mcp_client.is_available():
            available_tools = mcp_client.get_available_tools()
            logger.info(f"🔧 Customer Support agent initialized with {len(available_tools)} MCP tools")
            logger.debug(f"🔧 Available MCP tools: {available_tools}")
        else:
            logger.warning("⚠️ Customer Support chat agent created without MCP server tools")
            logger.warning(f"⚠️ MCP connection info: {connection_info}")
            
        return agent
            
    except Exception as e:
        logger.error(f"❌ Failed to create customer support chat agent: {e}")
        # Emergency fallback
        return Agent(
            "openai:gpt-4o-mini",
            output_type=ChatResponse,
            system_prompt=CUSTOMER_SUPPORT_CHAT_PROMPT
        )


async def create_title_generation_agent() -> Agent:
    """
    Create a specialized agent for generating conversation titles.
    
    This agent uses a faster, more cost-effective model and is optimized
    for generating concise, descriptive titles.
    
    Returns:
        Agent: Configured PydanticAI agent for title generation
    """
    try:
        agent = Agent(
            await get_title_generation_provider(),
            output_type=TitleGenerationResponse,
            system_prompt=TITLE_GENERATION_PROMPT
        )
        logger.info("✅ Title generation agent created")
        return agent
    except Exception as e:
        logger.error(f"❌ Failed to create title generation agent: {e}")
        # Emergency fallback
        return Agent(
            "openai:gpt-3.5-turbo",
            output_type=TitleGenerationResponse,
            system_prompt=TITLE_GENERATION_PROMPT
        )


async def process_organization_chat_message(
    organization_id: UUID,
    message: str,
    conversation_id: Optional[UUID] = None,
    user_id: Optional[UUID] = None,
    files: List[str] = None
) -> ChatResponse:
    """
    Process chat message using organization's scoped agent.
    
    This implements the new chat service integration with organization-scoped agents
    as described in the PRP Phase 6.
    
    Args:
        organization_id: Organization UUID
        message: User message to process
        conversation_id: Optional conversation ID for context
        user_id: Optional user ID for tracking
        files: Optional list of uploaded files
        
    Returns:
        ChatResponse: AI response with tool usage and confidence
    """
    try:
        # Get organization's agent (auto-creates if missing)
        agent = await get_organization_chat_agent(organization_id)
        
        if not agent:
            logger.error(f"Failed to get agent for organization {organization_id}")
            return ChatResponse(
                content="I'm currently unavailable. Please try again later.",
                confidence=0.0,
                requires_escalation=True,
                tools_used=[]
            )
        
        # Build context for the agent
        context = CustomerSupportContext(
            user_input=message,
            uploaded_files=files or [],
            conversation_history=[],  # TODO: Load from conversation_id
            user_metadata={
                "user_id": str(user_id) if user_id else None,
                "organization_id": str(organization_id),
                "conversation_id": str(conversation_id) if conversation_id else None
            },
            organization_id=str(organization_id)
        )
        
        # Process message with organization's agent
        response = await agent.process_message(message, context)
        
        # Log successful processing
        if isinstance(response, ChatResponse) and response.tools_used:
            logger.info(f"🔧 Organization {organization_id} agent used tools: {response.tools_used}")
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Error processing organization chat message: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        
        return ChatResponse(
            content="I encountered an error processing your request. Please try again later.",
            confidence=0.0,
            requires_escalation=True,
            tools_used=[]
        )


class AIChatService:
    """
    Service for managing AI chat conversations with customer support tools.
    
    This service provides:
    - Conversation management (create, retrieve, update)
    - AI-powered chat responses using Customer Support AI agents
    - Integration with MCP server tools for customer support operations
    - Message history and context management
    - Error handling and fallback mechanisms
    - AI-powered conversation title generation
    
    The service uses the MCP client to access customer support tools
    including ticket creation, file analysis, knowledge base search, and integrations.
    """
    
    def __init__(self):
        """Initialize the AI chat service with configured agents."""
        self.agent = None  # Will be initialized async
        self.title_agent = None  # Will be initialized async
        # Legacy support_agent removed - now using organization-scoped agents
        self._agent_initialized = False
        self._title_agent_initialized = False
    
    async def _ensure_agent_initialized(self):
        """Ensure the chat agent is initialized"""
        if not self._agent_initialized:
            self.agent = await create_chat_agent()
            self._agent_initialized = True
    
    async def _ensure_title_agent_initialized(self):
        """Ensure the title agent is initialized"""
        if not self._title_agent_initialized:
            self.title_agent = await create_title_generation_agent()
            self._title_agent_initialized = True
        
    async def generate_conversation_title(self, message: str, conversation_context: Optional[str] = None) -> str:
        """
        Generate an AI-powered title for a conversation based on the user's message.
        
        This method uses a specialized AI agent to create meaningful, descriptive
        titles that capture the essence of the customer support conversation.
        
        Args:
            message: The user's message content
            conversation_context: Optional additional context from conversation history
            
        Returns:
            str: Generated conversation title
        """
        try:
            # Ensure title agent is initialized
            await self._ensure_title_agent_initialized()
            
            # Prepare the prompt for title generation
            if conversation_context:
                prompt = f"""
                User Message: {message}
                
                Conversation Context: {conversation_context}
                
                Generate a concise, descriptive title for this customer support conversation.
                """
            else:
                prompt = f"""
                User Message: {message}
                
                Generate a concise, descriptive title for this customer support conversation.
                """
            
            # Use the title generation agent with usage limits
            usage_limits = UsageLimits(request_limit=5)
            result = await self.title_agent.run(prompt, usage_limits=usage_limits)
            
            if result.output and result.output.title:
                logger.info(f"✅ Generated title: '{result.output.title}' (confidence: {result.output.confidence:.2f})")
                return result.output.title
            else:
                logger.warning("⚠️ Title generation returned empty result, using fallback")
                return self._generate_fallback_title(message)
                
        except Exception as e:
            logger.error(f"❌ Title generation failed: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error details: {str(e)}")
            
            # Fallback to simple title generation
            return self._generate_fallback_title(message)
    
    def _generate_fallback_title(self, message: str) -> str:
        """
        Generate a fallback title when AI generation fails.
        
        This method provides a simple but effective title generation
        when the AI service is unavailable.
        
        Args:
            message: The user's message content
            
        Returns:
            str: Fallback conversation title
        """
        # Clean and truncate the message
        clean_message = message.strip()
        
        # Remove common prefixes and clean up
        prefixes_to_remove = ["hi", "hello", "hey", "can you", "please", "i need", "help me", "help with"]
        for prefix in prefixes_to_remove:
            if clean_message.lower().startswith(prefix):
                clean_message = clean_message[len(prefix):].strip()
        
        # Capitalize first letter and truncate
        if clean_message:
            title = clean_message[0].upper() + clean_message[1:]
            if len(title) > 50:
                title = title[:47] + "..."
            return title
        else:
            return "Customer Support Chat"
        
    async def create_conversation(self, user_id: str, title: Optional[str] = None) -> ChatConversation:
        """
        Create a new chat conversation.
        
        Args:
            user_id: ID of the user creating the conversation
            title: Optional title for the conversation
            
        Returns:
            ChatConversation: Created conversation object
        """
        
        async with get_async_db_session() as db:
            try:
                # If title is provided and not empty, use it; otherwise use default
                final_title = title if title and title.strip() else "Customer Support Chat"
                
                conversation = ChatConversation(
                    user_id=user_id,  # Now string type
                    title=final_title
                )
                db.add(conversation)
                await db.commit()
                await db.refresh(conversation)
                
                logger.info(f"Created conversation {conversation.id} for user {user_id}")
                logger.info(f"Title: '{final_title}' (user_provided: {bool(title and title.strip())})")
                return conversation
            except Exception as e:
                await db.rollback()
                logger.error(f"Error creating conversation for user {user_id}: {e}")
                raise
    
    async def get_thread_history(self, thread_id: str, user_id: str, agent_id: str) -> List[Any]:
        """
        Get thread history as PydanticAI messages for agent-centric processing.
        
        Args:
            thread_id: ID of the thread
            user_id: ID of the user (for authorization)
            agent_id: ID of the agent (for validation)
            
        Returns:
            List[Any]: List of messages in PydanticAI format
        """
        from uuid import UUID
        from sqlalchemy import select
        
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
                
                messages_query = select(Message).where(
                    Message.thread_id == UUID(thread_id)
                ).order_by(Message.created_at)
                
                result = await db.execute(messages_query)
                messages = result.scalars().all()
                
                # Convert to PydanticAI message format
                pydantic_messages = []
                for msg in messages:
                    if msg.role == "user":
                        pydantic_messages.append({"role": "user", "content": msg.content})
                    elif msg.role == "assistant":
                        pydantic_messages.append({"role": "assistant", "content": msg.content})
                
                return pydantic_messages
            except Exception as e:
                logger.error(f"[AI_CHAT_SERVICE] Error getting thread history: {e}")
                return []

    async def get_conversation_history(self, conversation_id: str, user_id: str) -> List[Any]:
        """
        Get conversation history as PydanticAI messages.
        
        Args:
            conversation_id: ID of the conversation
            user_id: ID of the user (for authorization)
            
        Returns:
            List[Any]: List of messages in PydanticAI format
        """
        from uuid import UUID
        from sqlalchemy import select
        
        async with get_async_db_session() as db:
            try:
                # Verify user owns conversation
                conversation_query = select(ChatConversation).where(
                    ChatConversation.id == UUID(conversation_id),
                    ChatConversation.user_id == user_id,  # Now string comparison
                    ChatConversation.is_deleted.is_(False)
                )
                
                result = await db.execute(conversation_query)
                conversation = result.scalar_one_or_none()
                
                if not conversation:
                    return []
                
                messages_query = select(ChatMessage).where(
                    ChatMessage.conversation_id == UUID(conversation_id)
                ).order_by(ChatMessage.created_at)
                
                result = await db.execute(messages_query)
                messages = result.scalars().all()
                
                # Convert to PydanticAI message format
                pydantic_messages = []
                for msg in messages:
                    if msg.role == "user":
                        pydantic_messages.append({"role": "user", "content": msg.content})
                    elif msg.role == "assistant":
                        pydantic_messages.append({"role": "assistant", "content": msg.content})
                
                return pydantic_messages
            except Exception as e:
                logger.error(f"Error getting conversation history: {e}")
                return []
    
    async def send_message_with_auth(
        self, 
        conversation_id: str, 
        user_id: str, 
        message: str,
        auth_token: Optional[str] = None,
        token_expires_at: Optional[datetime] = None
    ) -> ChatResponse:
        """Send message with authentication context for MCP tools"""
        
        # Get conversation history
        message_history = await self.get_conversation_history(conversation_id, user_id)
        
        # Simplified JWT token validation and context creation
        context = ChatContext(
            user_id=user_id,
            conversation_id=conversation_id,
            session_history=message_history
        )
        
        if auth_token:
            try:
                # Validate token using existing auth service
                from app.middleware.auth_middleware import auth_service
                payload = auth_service.verify_token(auth_token)
                logger.info(f"[AI_CHAT_SERVICE] Valid JWT token for user {user_id}")
                
                # Store token in context for MCP tools
                context._original_token = auth_token
                
                # Use authenticated MCP approach
                return await self._send_message_with_jwt_auth(conversation_id, user_id, message, context)
                
            except Exception as e:
                logger.warning(f"[AI_CHAT_SERVICE] JWT token validation failed: {e}")
                # Fallback to non-authenticated
        
        logger.info("[AI_CHAT_SERVICE] Using non-authenticated message sending")
        return await self._send_message_internal(conversation_id, user_id, message, context)
    
    async def _send_message_with_jwt_auth(self, conversation_id: str, user_id: str, message: str, context: ChatContext) -> ChatResponse:
        """Send message using JWT token authentication for MCP tools"""
        
        logger.info("[AI_CHAT_SERVICE] Using JWT token authentication for MCP tools")
        
        try:
            # Use the authenticated MCP client with JWT token
            authenticated_client = mcp_client.create_authenticated_mcp_client(context._original_token)
            
            if not authenticated_client:
                logger.warning("[AI_CHAT_SERVICE] Failed to create authenticated MCP client")
                return await self._send_message_internal(conversation_id, user_id, message, context)
            
            # Create agent with authenticated MCP tools
            config = await ai_config_service.load_default_agent_configuration()
            
            agent = Agent(
                await get_configured_chat_provider(),
                output_type=ChatResponse,
                system_prompt=config["system_prompt"],
                toolsets=[authenticated_client]  # Use authenticated MCP client
            )
            
            # Run agent with JWT authentication context
            from pydantic_ai.usage import UsageLimits
            max_iterations = ai_config_service.get_max_iterations()
            usage_limits = UsageLimits(request_limit=max_iterations)
            
            result = await agent.run(
                message,
                deps=context,
                usage_limits=usage_limits
            )
            
            logger.info("[AI_CHAT_SERVICE] ✅ JWT authenticated MCP response generated")
            
            return result.output
            
        except Exception as e:
            logger.error(f"[AI_CHAT_SERVICE] JWT authenticated MCP service failed: {e}")
            # Fallback to standard service
            return await self._send_message_internal(conversation_id, user_id, message, context)

    async def _send_message_with_enhanced_mcp(self, conversation_id: str, user_id: str, message: str, context: ChatContext) -> ChatResponse:
        """Send message using enhanced MCP service with user authentication"""
        
        logger.info("[AI_CHAT_SERVICE] Using enhanced MCP service with user authentication")
        
        try:
            # Initialize enhanced MCP service
            await enhanced_mcp_service.initialize_oauth()
            
            # Create authenticated tools
            auth_tools = enhanced_mcp_service.create_authenticated_mcp_tools(context._original_token)
            
            # Create agent with authenticated tools
            config = await ai_config_service.load_default_agent_configuration()
            
            agent = Agent(
                await get_configured_chat_provider(),
                output_type=ChatResponse,
                system_prompt=config["system_prompt"],
                tools=list(auth_tools.values())  # Use authenticated tools
            )
            
            # Run agent with authenticated context
            from pydantic_ai.usage import UsageLimits
            max_iterations = ai_config_service.get_max_iterations()
            usage_limits = UsageLimits(request_limit=max_iterations)
            
            result = await agent.run(
                message,
                deps=context,
                usage_limits=usage_limits
            )
            
            logger.info("[AI_CHAT_SERVICE] ✅ Enhanced MCP response generated with user auth")
            
            return result.output
            
        except Exception as e:
            logger.error(f"[AI_CHAT_SERVICE] Enhanced MCP service failed: {e}")
            # Fallback to standard MCP service
            return await self._send_message_internal(conversation_id, user_id, message, context)
    
    async def send_message(
        self, 
        conversation_id: str, 
        user_id: str, 
        message: str
    ) -> ChatResponse:
        """
        Send a message and get AI response with customer support tools (legacy method).
        
        This method calls send_message_with_auth with no authentication for backward compatibility.
        For new implementations, use send_message_with_auth directly.
        
        Args:
            conversation_id: ID of the conversation
            user_id: ID of the user sending the message
            message: User's message content
            
        Returns:
            ChatResponse: Structured AI response with content and metadata
        """
        # Call the new authenticated method without authentication for backward compatibility
        return await self.send_message_with_auth(
            conversation_id=conversation_id,
            user_id=user_id,
            message=message,
            auth_token=None,
            token_expires_at=None
        )
    
    async def send_message_to_thread(
        self, 
        agent_id: str,
        thread_id: str, 
        user_id: str, 
        message: str,
        attachments: List[dict] = None,
        auth_token: Optional[str] = None,
        token_expires_at: Optional[datetime] = None
    ) -> ChatResponse:
        """
        Send message to a thread with agent-centric processing.
        
        This is the new agent-centric method that replaces conversation-based processing.
        
        Args:
            agent_id: ID of the agent handling this thread
            thread_id: ID of the thread
            user_id: ID of the user sending the message
            message: User's message content
            attachments: Optional file attachments
            auth_token: Optional JWT token for MCP authentication
            token_expires_at: Optional token expiration time
            
        Returns:
            ChatResponse: Structured AI response with content and metadata
        """
        
        # Get thread history for context
        message_history = await self.get_thread_history(thread_id, user_id, agent_id)
        
        # Create context for agent-centric processing
        context = ChatContext(
            user_id=user_id,
            conversation_id=thread_id,  # Use thread_id as conversation_id for compatibility
            session_history=message_history
        )
        
        if auth_token:
            try:
                # Validate token using existing auth service
                from app.middleware.auth_middleware import auth_service
                payload = auth_service.verify_token(auth_token)
                logger.info(f"[AI_CHAT_SERVICE] Valid JWT token for user {user_id} in thread {thread_id}")
                
                # Store token in context for MCP tools
                context._original_token = auth_token
                
                # Use authenticated MCP approach
                return await self._send_message_to_thread_with_auth(agent_id, thread_id, user_id, message, context, attachments)
                
            except Exception as e:
                logger.warning(f"[AI_CHAT_SERVICE] JWT token validation failed: {e}")
                # Fallback to non-authenticated
        
        logger.info("[AI_CHAT_SERVICE] Using non-authenticated thread message sending")
        return await self._send_message_to_thread_internal(agent_id, thread_id, user_id, message, context, attachments)
    
    async def _send_message_to_thread_with_auth(self, agent_id: str, thread_id: str, user_id: str, message: str, context: ChatContext, attachments: List[dict] = None) -> ChatResponse:
        """Send message to thread using JWT token authentication for MCP tools"""
        
        logger.info(f"[AI_CHAT_SERVICE] Using JWT token authentication for MCP tools in thread {thread_id}")
        
        try:
            # Use the authenticated MCP client with JWT token
            authenticated_client = mcp_client.create_authenticated_mcp_client(context._original_token)
            
            if not authenticated_client:
                logger.warning("[AI_CHAT_SERVICE] Failed to create authenticated MCP client")
                return await self._send_message_to_thread_internal(agent_id, thread_id, user_id, message, context, attachments)
            
            # Get organization-scoped agent for this thread
            from uuid import UUID
            try:
                organization_agent = await get_organization_chat_agent(UUID(agent_id))
                if not organization_agent:
                    logger.error(f"[AI_CHAT_SERVICE] Could not get organization agent for agent_id {agent_id}")
                    # Fallback to legacy agent creation
                    agent = await create_chat_agent()
                else:
                    # Use the organization agent's underlying PydanticAI agent
                    agent = organization_agent.get_pydantic_agent()
            except Exception as e:
                logger.warning(f"[AI_CHAT_SERVICE] Could not get organization agent, falling back to default: {e}")
                agent = await create_chat_agent()
            
            # Process file attachments if provided
            processed_attachments = []
            if attachments:
                try:
                    from app.services.file_service import file_service
                    for attachment in attachments:
                        processed_file = await file_service.process_attachment_for_agent(attachment)
                        processed_attachments.append(processed_file)
                    logger.info(f"[AI_CHAT_SERVICE] Processed {len(processed_attachments)} attachments")
                except Exception as e:
                    logger.warning(f"[AI_CHAT_SERVICE] File attachment processing failed: {e}")
            
            # Run agent with JWT authentication context
            from pydantic_ai.usage import UsageLimits
            max_iterations = ai_config_service.get_max_iterations()
            usage_limits = UsageLimits(request_limit=max_iterations)
            
            result = await agent.run(
                message,
                deps=context,
                usage_limits=usage_limits
            )
            
            logger.info("[AI_CHAT_SERVICE] ✅ JWT authenticated thread response generated")
            
            return result.output
            
        except Exception as e:
            logger.error(f"[AI_CHAT_SERVICE] JWT authenticated thread service failed: {e}")
            # Fallback to standard service
            return await self._send_message_to_thread_internal(agent_id, thread_id, user_id, message, context, attachments)
    
    async def _send_message_to_thread_internal(
        self, 
        agent_id: str,
        thread_id: str, 
        user_id: str, 
        message: str,
        context: ChatContext,
        attachments: List[dict] = None
    ) -> ChatResponse:
        """
        Internal method for sending messages to threads with agent-centric processing.
        
        This method contains the core logic for:
        1. Storing the user message in the database
        2. Calling the organization-scoped AI agent with MCP server tools
        3. Storing the AI response with tool calls in the database
        4. Generating AI-powered thread title if needed
        5. Returning the structured response
        """
        from uuid import UUID
        
        # Store user message
        logger.info(f"[AI_CHAT_SERVICE] Storing user message for thread {thread_id}")
        logger.debug(f"[AI_CHAT_SERVICE] User message: {message[:200]}{'...' if len(message) > 200 else ''}")
        
        async with get_async_db_session() as db:
            try:
                # Verify thread exists and user owns it
                thread_query = select(Thread).where(
                    Thread.id == UUID(thread_id),
                    Thread.user_id == user_id,
                    Thread.agent_id == UUID(agent_id)
                )
                result = await db.execute(thread_query)
                thread = result.scalar_one_or_none()
                
                if not thread:
                    error_msg = f"Thread {thread_id} not found or not accessible for agent {agent_id}"
                    logger.error(f"[AI_CHAT_SERVICE] {error_msg} for user {user_id}")
                    raise ValueError(error_msg)
                
                logger.debug(f"[AI_CHAT_SERVICE] Thread verified: {thread.title}")
                
                # Process attachments for message
                processed_attachments_data = []
                if attachments:
                    for attachment in attachments:
                        processed_attachments_data.append({
                            "id": attachment.get("id"),
                            "filename": attachment.get("filename"),
                            "content_type": attachment.get("content_type"),
                            "size": attachment.get("size"),
                            "processed_at": datetime.now(timezone.utc).isoformat()
                        })
                
                user_msg = Message(
                    thread_id=UUID(thread_id),
                    role="user",
                    content=message,
                    attachments=processed_attachments_data if processed_attachments_data else None
                )
                db.add(user_msg)
                await db.commit()
                logger.debug(f"[AI_CHAT_SERVICE] User message stored with ID: {user_msg.id}")
            except Exception as e:
                await db.rollback()
                logger.error(f"[AI_CHAT_SERVICE] Error storing user message: {e}")
                raise
        
        # Get AI response using organization-scoped agent with proper async context manager
        try:
            start_time = datetime.now(timezone.utc)
            
            # Get organization-scoped agent for this thread
            try:
                organization_agent = await get_organization_chat_agent(UUID(agent_id))
                if organization_agent and organization_agent.is_active():
                    logger.info(f"[AI_CHAT_SERVICE] ✅ Using organization agent for agent_id {agent_id}")
                    # Process message with organization agent (includes MCP tools and context)
                    response = await organization_agent.process_message(message, context)
                    
                    if isinstance(response, ChatResponse):
                        ai_response = response
                    else:
                        # Convert if needed
                        ai_response = ChatResponse(
                            content=str(response),
                            confidence=0.8,
                            requires_escalation=False,
                            tools_used=[]
                        )
                else:
                    raise Exception("Organization agent not available or not active")
                    
            except Exception as e:
                logger.warning(f"[AI_CHAT_SERVICE] Organization agent failed, falling back to default: {e}")
                # Fallback to legacy agent approach
                await self._ensure_agent_initialized()
                
                logger.info(f"[AI_CHAT_SERVICE] 🔍 Starting agent run for thread {thread_id}")
                logger.info(f"[AI_CHAT_SERVICE] 📝 Message: {message[:100]}...")
                
                # Run the agent with usage limits
                max_iterations = ai_config_service.get_max_iterations()
                logger.debug(f"[AI_CHAT_SERVICE] Using max iterations: {max_iterations}")
                usage_limits = UsageLimits(request_limit=max_iterations)
                
                result = await self.agent.run(
                    message,
                    deps=context,
                    usage_limits=usage_limits
                )
                
                ai_response = result.output
            
            response_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            logger.info(f"[AI_CHAT_SERVICE] ✅ Agent processing completed in {response_time:.2f}ms")
            
            # Store AI response with tool calls
            logger.debug("[AI_CHAT_SERVICE] Storing AI response to database")
            async with get_async_db_session() as db:
                try:
                    # Prepare tool calls data for storage
                    tool_calls_data = None
                    if hasattr(ai_response, 'tools_used') and ai_response.tools_used:
                        tool_calls_data = []
                        for tool_name in ai_response.tools_used:
                            tool_calls_data.append({
                                "tool_name": tool_name,
                                "called_at": datetime.now(timezone.utc).isoformat(),
                                "status": "completed"
                            })
                    
                    # Prepare message metadata
                    message_metadata = {
                        "response_time_ms": int(response_time),
                        "agent_id": agent_id,
                        "tools_used": ai_response.tools_used if hasattr(ai_response, 'tools_used') else [],
                        "requires_escalation": ai_response.requires_escalation if hasattr(ai_response, 'requires_escalation') else False,
                        "attachments_processed": len(attachments) if attachments else 0,
                        "generation_timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
                    ai_msg = Message(
                        thread_id=UUID(thread_id),
                        role="assistant",
                        content=ai_response.content,
                        tool_calls=tool_calls_data,
                        message_metadata=message_metadata,
                        response_time_ms=int(response_time),
                        confidence_score=ai_response.confidence if hasattr(ai_response, 'confidence') else None
                    )
                    db.add(ai_msg)
                    logger.debug(f"[AI_CHAT_SERVICE] AI message created with tool_calls: {bool(tool_calls_data)}")
                    
                    # Update thread metadata
                    thread_query = select(Thread).where(Thread.id == UUID(thread_id))
                    result_thread = await db.execute(thread_query)
                    thread = result_thread.scalar_one_or_none()
                    
                    if thread:
                        logger.debug(f"[AI_CHAT_SERVICE] Updating thread metadata: {thread.title}")
                        # Update thread metadata
                        current_metadata = thread.thread_metadata or {}
                        current_metadata.update({
                            "last_message_at": datetime.now(timezone.utc).isoformat(),
                            "total_messages": (current_metadata.get("total_messages", 0) + 2),  # User + AI message
                            "last_agent_used": agent_id,
                            "last_tools_used": ai_response.tools_used if hasattr(ai_response, 'tools_used') else []
                        })
                        thread.thread_metadata = current_metadata
                        
                        # Generate AI-powered title only if current title is the default title
                        if thread.title == "New Chat Thread":
                            logger.debug("[AI_CHAT_SERVICE] Generating AI title for thread")
                            # Generate AI-powered title
                            ai_title = await self.generate_conversation_title(message)
                            thread.title = ai_title
                            logger.info(f"[AI_CHAT_SERVICE] 🎯 Updated thread title to: '{ai_title}' (AI-generated)")
                    
                    await db.commit()
                    logger.debug("[AI_CHAT_SERVICE] AI response and thread metadata stored successfully")
                except Exception as e:
                    await db.rollback()
                    logger.error(f"[AI_CHAT_SERVICE] Error storing AI response: {e}")
                    import traceback
                    logger.error(f"[AI_CHAT_SERVICE] Full traceback: {traceback.format_exc()}")
            
            return ai_response
            
        except ValueError as ve:
            # Handle thread not found errors - don't try to store error message
            logger.warning(f"[AI_CHAT_SERVICE] Thread validation failed: {ve}")
            raise ve  # Re-raise to let the API layer handle as 404
            
        except Exception as e:
            logger.error(f"[AI_CHAT_SERVICE] Thread processing failed: {e}")
            logger.error(f"[AI_CHAT_SERVICE] Error type: {type(e).__name__}")
            
            # Try to get more details about the error
            import traceback
            logger.error(f"[AI_CHAT_SERVICE] Full traceback: {traceback.format_exc()}")
            
            return ChatResponse(
                content="I'm sorry, I encountered an error processing your request. Please try again or contact support if the issue persists.",
                confidence=0.0,
                requires_escalation=True,
                tools_used=[]
            )
    
    async def _send_message_internal(
        self, 
        conversation_id: str, 
        user_id: str, 
        message: str,
        context: ChatContext
    ) -> ChatResponse:
        """
        Internal method for sending messages with a given context.
        
        This method contains the core logic for:
        1. Storing the user message in the database
        2. Calling the AI agent with MCP server tools
        3. Storing the AI response in the database
        4. Generating AI-powered conversation title if needed
        5. Returning the structured response
        """
        from uuid import UUID
        
        # Store user message
        logger.info(f"[AI_CHAT_SERVICE] Storing user message for conversation {conversation_id}")
        logger.debug(f"[AI_CHAT_SERVICE] User message: {message[:200]}{'...' if len(message) > 200 else ''}")
        
        async with get_async_db_session() as db:
            try:
                # Verify conversation exists and user owns it
                conversation_query = select(ChatConversation).where(
                    ChatConversation.id == UUID(conversation_id),
                    ChatConversation.user_id == user_id,
                    ChatConversation.is_deleted.is_(False)
                )
                result = await db.execute(conversation_query)
                conversation = result.scalar_one_or_none()
                
                if not conversation:
                    error_msg = f"Conversation {conversation_id} not found or not accessible"
                    logger.error(f"[AI_CHAT_SERVICE] {error_msg} for user {user_id}")
                    raise ValueError(error_msg)
                
                logger.debug(f"[AI_CHAT_SERVICE] Conversation verified: {conversation.title}")
                
                user_msg = ChatMessage(
                    conversation_id=UUID(conversation_id),
                    role="user",
                    content=message
                )
                db.add(user_msg)
                await db.commit()
                logger.debug(f"[AI_CHAT_SERVICE] User message stored with ID: {user_msg.id}")
            except Exception as e:
                await db.rollback()
                logger.error(f"[AI_CHAT_SERVICE] Error storing user message: {e}")
                raise
        
        # Get AI response using MCP server integration with proper async context manager
        try:
            start_time = datetime.now(timezone.utc)
            
            # Ensure agent is properly initialized
            await self._ensure_agent_initialized()
            
            # Log MCP client status before running agent
            mcp_info = mcp_client.get_connection_info()
            logger.info(f"[AI_CHAT_SERVICE] 🔍 Starting customer support agent run for user {user_id}")
            logger.info(f"[AI_CHAT_SERVICE] 📝 Message: {message[:100]}...")
            logger.info(f"[AI_CHAT_SERVICE] 🔗 MCP client status: {mcp_info}")
            logger.debug(f"[AI_CHAT_SERVICE] Agent model: {self.agent.model}")
            logger.debug(f"[AI_CHAT_SERVICE] Message history length: {len(context.session_history)} messages")
            
            # Log authentication context status
            if context.has_valid_auth:
                logger.info("[AI_CHAT_SERVICE] 🔐 Using authenticated context for MCP tools")
            else:
                logger.warning("[AI_CHAT_SERVICE] ⚠️ Using non-authenticated context for MCP tools")
            
            # Log authentication context status
            if context.has_valid_auth:
                logger.info("[AI_CHAT_SERVICE] 🔐 Using authenticated context for MCP tools")
            else:
                logger.warning("[AI_CHAT_SERVICE] ⚠️ Using non-authenticated context for MCP tools")
            
            # Run the agent directly with usage limits to prevent runaway tool calling
            logger.debug("[AI_CHAT_SERVICE] Calling agent.run() with message and context")
            max_iterations = ai_config_service.get_max_iterations()
            logger.debug(f"[AI_CHAT_SERVICE] Using max iterations: {max_iterations}")
            usage_limits = UsageLimits(request_limit=max_iterations)
            
            result = await self.agent.run(
                message,
                deps=context,
                usage_limits=usage_limits
            )
            
            response_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            logger.info(f"[AI_CHAT_SERVICE] ✅ Customer support agent run completed in {response_time:.2f}ms")
            logger.debug(f"[AI_CHAT_SERVICE] Agent response confidence: {result.output.confidence}")
            logger.debug(f"[AI_CHAT_SERVICE] Agent response content: {result.output.content[:200]}{'...' if len(result.output.content) > 200 else ''}")
            logger.debug(f"[AI_CHAT_SERVICE] Tools used: {result.output.tools_used}")
            logger.debug(f"[AI_CHAT_SERVICE] Requires escalation: {result.output.requires_escalation}")
            
            # Create enhanced response
            enhanced_response = ChatResponse(
                content=result.output.content,
                confidence=result.output.confidence,
                requires_escalation=result.output.requires_escalation,
                suggested_actions=result.output.suggested_actions,
                ticket_references=result.output.ticket_references,
                tools_used=result.output.tools_used
            )
            
            # Store AI response
            logger.debug("[AI_CHAT_SERVICE] Storing AI response to database")
            async with get_async_db_session() as db:
                try:
                    ai_msg = ChatMessage(
                        conversation_id=UUID(conversation_id),
                        role="assistant",
                        content=result.output.content,
                        model_used=str(self.agent.model),
                        response_time_ms=int(response_time),
                        confidence_score=result.output.confidence
                    )
                    db.add(ai_msg)
                    logger.debug(f"[AI_CHAT_SERVICE] AI message created with model: {ai_msg.model_used}")
                    
                    # Update conversation metadata
                    conversation_query = select(ChatConversation).where(
                        ChatConversation.id == UUID(conversation_id)
                    )
                    result_conv = await db.execute(conversation_query)
                    conversation = result_conv.scalar_one_or_none()
                    
                    if conversation:
                        logger.debug(f"[AI_CHAT_SERVICE] Updating conversation metadata: {conversation.title}")
                        # Update counters and timestamp
                        conversation.total_messages = conversation.total_messages + 2  # User + AI message
                        conversation.updated_at = datetime.now(timezone.utc)
                        
                        # Add token usage if available
                        try:
                            usage = result.usage()
                            if usage and hasattr(usage, 'input_tokens') and hasattr(usage, 'output_tokens'):
                                tokens_used = usage.input_tokens + usage.output_tokens
                                conversation.total_tokens_used += tokens_used
                                # Also store token usage in the message
                                ai_msg.tokens_used = tokens_used
                                logger.debug(f"[AI_CHAT_SERVICE] Updated token count: {conversation.total_tokens_used} (+{tokens_used})")
                        except Exception as token_error:
                            logger.debug(f"[AI_CHAT_SERVICE] Could not get token usage: {token_error}")
                        
                        # Generate AI-powered title only if current title is the default title
                        if conversation.title == "Customer Support Chat":
                            logger.debug("[AI_CHAT_SERVICE] Generating AI title for conversation")
                            # Get conversation context for title generation
                            conversation_context = None
                            if len(context.session_history) > 2:  # More than just the current exchange
                                # Use recent messages as context
                                recent_messages = context.session_history[-4:]  # Last 4 messages
                                conversation_context = " ".join([msg.get("content", "") for msg in recent_messages])
                            
                            # Generate AI-powered title
                            ai_title = await self.generate_conversation_title(message, conversation_context)
                            conversation.title = ai_title
                            logger.info(f"[AI_CHAT_SERVICE] 🎯 Updated conversation title to: '{ai_title}' (AI-generated)")
                    
                    await db.commit()
                    logger.debug("[AI_CHAT_SERVICE] AI response and conversation metadata stored successfully")
                except Exception as e:
                    await db.rollback()
                    logger.error(f"[AI_CHAT_SERVICE] Error storing AI response: {e}")
                    import traceback
                    logger.error(f"[AI_CHAT_SERVICE] Full traceback: {traceback.format_exc()}")
            
            return enhanced_response
            
        except ValueError as ve:
            # Handle conversation not found errors - don't try to store error message
            logger.warning(f"[AI_CHAT_SERVICE] Conversation validation failed: {ve}")
            logger.warning("[AI_CHAT_SERVICE] Re-raising ValueError for proper 404 handling")
            raise ve  # Re-raise to let the API layer handle as 404
            
        except Exception as e:
            logger.error(f"[AI_CHAT_SERVICE] Customer support chat response failed: {e}")
            logger.error(f"[AI_CHAT_SERVICE] Error type: {type(e).__name__}")
            logger.error(f"[AI_CHAT_SERVICE] Error details: {str(e)}")
            
            # Try to get more details about the error
            import traceback
            logger.error(f"[AI_CHAT_SERVICE] Full traceback: {traceback.format_exc()}")
            
            # Try to reset MCP connection if it's a connection issue
            if "MCP server is not running" in str(e) or "connection" in str(e).lower():
                logger.info("[AI_CHAT_SERVICE] 🔄 Attempting to reset MCP connection...")
                if mcp_client.reset_connection():
                    logger.info("[AI_CHAT_SERVICE] ✅ MCP connection reset, you may want to retry the request")
            
            # Only try to store error response if we have a valid conversation
            # Skip if the error might be conversation-related
            error_msg_lower = str(e).lower()
            if not ("not found" in error_msg_lower or "not accessible" in error_msg_lower):
                try:
                    async with get_async_db_session() as db:
                        error_msg = ChatMessage(
                            conversation_id=UUID(conversation_id),
                            role="assistant",
                            content="I'm sorry, I encountered an error processing your request. Please try again or contact support.",
                            model_used="error"
                        )
                        db.add(error_msg)
                        await db.commit()
                        logger.debug(f"[AI_CHAT_SERVICE] Stored error message to conversation {conversation_id}")
                except Exception as db_error:
                    logger.warning(f"[AI_CHAT_SERVICE] Could not store error message: {db_error}")
            else:
                logger.debug("[AI_CHAT_SERVICE] Skipping error message storage due to conversation access issue")
            
            return ChatResponse(
                content="I'm sorry, I encountered an error processing your request. Please try again or contact support if the issue persists.",
                confidence=0.0,
                requires_escalation=True
            )
    
    async def stream_message(
        self, 
        conversation_id: str, 
        user_id: str, 
        message: str
    ) -> AsyncIterator[str]:
        """
        Stream AI response in real-time.
        
        This method provides streaming responses for real-time chat interactions.
        It works similarly to send_message but streams the response chunks.
        
        Args:
            conversation_id: ID of the conversation
            user_id: ID of the user sending the message
            message: User's message content
            
        Yields:
            str: Response chunks as they become available
        """
        from uuid import UUID
        
        # Get message history and context
        message_history = await self.get_conversation_history(conversation_id, user_id)
        context = ChatContext(
            user_id=user_id,
            conversation_id=conversation_id,
            session_history=message_history
        )
        
        # Store user message
        async with get_async_db_session() as db:
            try:
                # Verify conversation exists and user owns it
                conversation_query = select(ChatConversation).where(
                    ChatConversation.id == UUID(conversation_id),
                    ChatConversation.user_id == user_id,
                    ChatConversation.is_deleted.is_(False)
                )
                result = await db.execute(conversation_query)
                conversation = result.scalar_one_or_none()
                
                if not conversation:
                    raise ValueError(f"Conversation {conversation_id} not found or not accessible")
                
                user_msg = ChatMessage(
                    conversation_id=UUID(conversation_id),
                    role="user",
                    content=message
                )
                db.add(user_msg)
                await db.commit()
            except Exception as e:
                await db.rollback()
                logger.error(f"Error storing user message for streaming: {e}")
                yield "Error: Could not process your message. Please try again."
                return
        
        # Stream AI response with MCP server integration using proper async context manager
        full_response = ""
        try:
            # Ensure agent is properly initialized
            await self._ensure_agent_initialized()
            
            logger.info(f"🚀 Starting PydanticAI streaming for customer support: {message[:50]}...")
            
            # Stream response directly with usage limits to prevent runaway tool calling
            max_iterations = ai_config_service.get_max_iterations()
            logger.debug(f"[AI_CHAT_SERVICE] Using max iterations for streaming: {max_iterations}")
            usage_limits = UsageLimits(request_limit=max_iterations)
            async with self.agent.run_stream(
                message,
                deps=context,
                usage_limits=usage_limits
            ) as result:
                    logger.info("📡 Stream result obtained, starting to iterate chunks...")
                    
                    chunk_count = 0
                    async for chunk in result.stream():
                        chunk_count += 1
                        logger.debug(f"🧩 Received chunk #{chunk_count}: {str(chunk)[:50]}...")
                        
                        # Ensure chunk is a string
                        if isinstance(chunk, str):
                            full_response += chunk
                            yield chunk
                        else:
                            # If chunk is not a string, convert it
                            chunk_str = str(chunk)
                            full_response += chunk_str
                            yield chunk_str
                    
                    logger.info(f"✅ Streaming completed with {chunk_count} chunks, full response length: {len(full_response)}")
                    
                    # Store complete response
                    final_result = await result.get_output()
                    
                    async with get_async_db_session() as db:
                        try:
                            ai_msg = ChatMessage(
                                conversation_id=UUID(conversation_id),
                                role="assistant",
                                content=final_result.content,
                                model_used=str(self.agent.model),
                                confidence_score=final_result.confidence
                            )
                            db.add(ai_msg)
                            
                            # Update conversation metadata and generate title if needed
                            conversation_query = select(ChatConversation).where(
                                ChatConversation.id == UUID(conversation_id)
                            )
                            result_conv = await db.execute(conversation_query)
                            conversation = result_conv.scalar_one_or_none()
                            
                            if conversation:
                                # Update counters and timestamp
                                conversation.total_messages = conversation.total_messages + 2  # User + AI message
                                conversation.updated_at = datetime.now(timezone.utc)
                                
                                # Add token usage if available
                                try:
                                    # In streaming, get usage from the stream result object
                                    usage = result.usage()
                                    if usage and hasattr(usage, 'input_tokens') and hasattr(usage, 'output_tokens'):
                                        tokens_used = usage.input_tokens + usage.output_tokens
                                        conversation.total_tokens_used += tokens_used
                                        # Also store token usage in the message
                                        ai_msg.tokens_used = tokens_used
                                        logger.debug(f"[AI_CHAT_SERVICE] Streaming token count: {conversation.total_tokens_used} (+{tokens_used})")
                                except Exception as token_error:
                                    logger.debug(f"[AI_CHAT_SERVICE] Could not get streaming token usage: {token_error}")
                                
                                # Generate AI-powered title only if current title is the default title
                                if conversation.title == "Customer Support Chat":
                                    # Generate AI-powered title
                                    ai_title = await self.generate_conversation_title(message)
                                    conversation.title = ai_title
                                    logger.info(f"🎯 Updated conversation title to: '{ai_title}' (AI-generated)")
                            
                            await db.commit()
                        except Exception as e:
                            await db.rollback()
                            logger.error(f"Error storing streaming AI response: {e}")
                    
        except Exception as e:
            logger.error(f"Streaming failed: {e}")
            error_msg = "I encountered an error. Please try again."
            yield error_msg
            
            # Store error
            async with get_async_db_session() as db:
                try:
                    ai_msg = ChatMessage(
                        conversation_id=UUID(conversation_id),
                        role="assistant",
                        content=error_msg,
                        model_used="error"
                    )
                    db.add(ai_msg)
                    await db.commit()
                except Exception:
                    pass  # Don't fail on error logging


    async def process_message_with_organization_agent(
        self,
        organization_id: UUID,
        message: str,
        conversation_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        files: List[str] = None
    ) -> ChatResponse:
        """
        Process chat message using organization's scoped agent (new approach).
        
        This method uses the new organization-scoped agent architecture instead
        of the old stateless agent creation. Implements PRP Phase 6 requirements.
        
        Args:
            organization_id: Organization UUID
            message: User message
            conversation_id: Optional conversation ID
            user_id: Optional user ID
            files: Optional uploaded files
            
        Returns:
            ChatResponse: AI response with tool usage
        """
        return await process_organization_chat_message(
            organization_id=organization_id,
            message=message,
            conversation_id=conversation_id,
            user_id=user_id,
            files=files
        )


# Global service instance
ai_chat_service = AIChatService()