#!/usr/bin/env python3
"""
Title Generation Agent Runner

Runner for title generation using the Agent infrastructure instead of standalone agents.
Integrates with the multi-agent system to provide system-wide title generation as a utility service.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from pydantic_ai import Agent as PydanticAgent
except ImportError:
    # Mock for testing environments
    class PydanticAgent:
        def __init__(self, *args, **kwargs):
            self.model = kwargs.get('model', 'mock')
        async def run(self, *args, **kwargs):
            from unittest.mock import MagicMock
            result = MagicMock()
            result.output = MagicMock()
            result.output.title = "Mock Generated Title"
            result.output.confidence = 0.8
            return result

from app.models.ai_agent import Agent
from app.models.chat import Message
from app.schemas.title_generation import TitleGenerationResult
from app.services.ai_config_service import ai_config_service

logger = logging.getLogger(__name__)

# Constants from PRP specification
MAX_MESSAGES_FOR_TITLE = 6  # Process only latest 6 messages to optimize token usage
DEFAULT_TITLE_PROMPT = """You are an expert at creating concise, descriptive titles for customer support conversations.

Analyze the conversation and generate a clear, specific title that captures the essence of the discussion.

TITLE GENERATION RULES:
1. Maximum 8 words, ideally 4-6 words
2. Use specific, descriptive terms
3. Avoid generic words: "Help", "Support", "Question", "Issue"
4. Include technical terms when relevant
5. Capture the primary topic/problem
6. Use title case formatting

Focus on the main issue or request being discussed."""


class TitleGenerationAgentRunner:
    """
    Runner for title generation using Agent infrastructure.
    
    This class bridges the Agent model with Pydantic AI agents to provide
    system-wide title generation as a utility service. It replaces the
    standalone TitleGenerationAgent with an integrated approach.
    """
    
    def __init__(self, agent: Agent):
        """
        Initialize the runner with an Agent instance.
        
        Args:
            agent: Agent model instance configured for title generation
        """
        self.agent = agent
        self.pydantic_agent: Optional[PydanticAgent] = None
        self._initialized = False
        
        # Validate that this is a title generation agent
        if agent.agent_type != "title_generation":
            logger.warning(f"Agent {agent.id} is not a title_generation agent (type: {agent.agent_type})")
    
    async def ensure_initialized(self):
        """Initialize Pydantic AI agent from Agent configuration"""
        if self._initialized and self.pydantic_agent:
            return
            
        try:
            logger.debug(f"Initializing title generation runner for agent {self.agent.id}")
            
            # Get agent configuration
            config = self.agent.get_configuration()
            
            # Determine model to use - prioritize agent config, fallback to ai_config service
            model_provider = "openai"  # Default provider for title generation
            model_name = "gpt-3.5-turbo"  # Default fast model
            
            try:
                # Try to get configuration from ai_config service
                agent_config = await ai_config_service.get_agent_config("title_generation_agent")
                if agent_config:
                    model_provider = agent_config.get("model_provider", "openai")
                    configured_model = agent_config.get("model_name", "fast")
                    
                    # Map configuration model names to actual model names
                    if configured_model == "primary":
                        model_name = "gpt-4o-mini"  # Use mini for cost efficiency
                    elif configured_model == "fast":
                        model_name = "gpt-3.5-turbo"
                    elif configured_model == "backup":
                        model_name = "gpt-4"
                    else:
                        model_name = configured_model
                        
                    logger.debug(f"Using ai_config model: {model_provider}:{model_name}")
                else:
                    logger.debug("No ai_config found, using default fast model")
                    
            except Exception as e:
                logger.warning(f"Failed to load ai_config, using defaults: {e}")
            
            # Get system prompt from agent configuration or use default
            system_prompt = config.get('prompt') or DEFAULT_TITLE_PROMPT
            
            # Initialize Pydantic AI agent
            self.pydantic_agent = PydanticAgent(
                model=f"{model_provider}:{model_name}",
                system_prompt=system_prompt,
                output_type=TitleGenerationResult,
                retries=2
            )
            
            self._initialized = True
            logger.info(f"✅ Title generation runner initialized with {model_provider}:{model_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize title generation runner: {e}")
            # Emergency fallback with simple configuration
            self.pydantic_agent = PydanticAgent(
                model="openai:gpt-3.5-turbo",
                system_prompt=DEFAULT_TITLE_PROMPT,
                output_type=TitleGenerationResult,
                retries=1
            )
            self._initialized = True
    
    async def generate_title(
        self,
        messages: List[Message], 
        current_title: Optional[str] = None
    ) -> TitleGenerationResult:
        """
        Generate title using agent configuration and latest messages only.
        
        Args:
            messages: List of Message objects from the thread
            current_title: Current thread title (optional)
            
        Returns:
            TitleGenerationResult: Generated title with confidence score
        """
        try:
            # Ensure agent is initialized
            await self.ensure_initialized()
            if not self.pydantic_agent:
                logger.error("Title generation agent not available")
                return TitleGenerationResult(
                    title="Conversation",
                    confidence=0.0
                )
            
            # Use only the latest MAX_MESSAGES_FOR_TITLE messages (optimize token usage)
            recent_messages = messages[-MAX_MESSAGES_FOR_TITLE:] if len(messages) > MAX_MESSAGES_FOR_TITLE else messages
            
            # Prepare message content for analysis
            message_contents = []
            for msg in recent_messages:
                if msg.content and len(msg.content.strip()) > 0:
                    role_prefix = "User: " if msg.role == "user" else "Assistant: "
                    message_contents.append(f"{role_prefix}{msg.content.strip()}")
            
            if not message_contents:
                logger.warning("No message content available for title generation")
                return TitleGenerationResult(
                    title="Empty Conversation",
                    confidence=0.5
                )
            
            # Create optimized prompt for latest messages
            conversation_text = "\n".join(message_contents)
            prompt = f"""
Analyze this recent conversation and generate a concise, descriptive title.

Current title: "{current_title or 'New Conversation'}"
Recent messages ({len(message_contents)} messages, latest {MAX_MESSAGES_FOR_TITLE}):

{conversation_text}

Generate a title that captures the main topic or issue being discussed.
"""
            
            logger.info(f"🎯 Generating title for conversation with {len(recent_messages)} recent messages (from {len(messages)} total)")
            logger.debug(f"Message content preview: {conversation_text[:200]}...")
            
            # Run the AI agent
            result = await self.pydantic_agent.run(prompt)
            
            if result and result.output:
                # Ensure title complies with length requirements
                validated_title = self._validate_title_length(result.output.title)
                logger.info(f"✅ Generated title: '{validated_title}' (confidence: {result.output.confidence:.2f})")
                return TitleGenerationResult(
                    title=validated_title,
                    confidence=result.output.confidence
                )
            else:
                logger.warning("❌ No result from title generation agent")
                return TitleGenerationResult(
                    title=self._generate_fallback_title(message_contents),
                    confidence=0.3
                )
                
        except Exception as e:
            logger.error(f"❌ Title generation failed: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            
            # Fallback to simple title generation
            return TitleGenerationResult(
                title=self._generate_fallback_title(message_contents if 'message_contents' in locals() else []),
                confidence=0.1
            )
    
    def _validate_title_length(self, title: str) -> str:
        """
        Validate and enforce title length requirements (max 8 words).
        
        Args:
            title: Title to validate
            
        Returns:
            str: Validated title (truncated if necessary)
        """
        if not title or not title.strip():
            return "Conversation"
            
        # Split into words and limit to 8
        words = title.strip().split()
        if len(words) <= 8:
            return title.strip()
        
        # Truncate to 8 words
        truncated = " ".join(words[:8])
        logger.debug(f"Truncated title from {len(words)} words to 8: '{title}' -> '{truncated}'")
        return truncated
    
    def _generate_fallback_title(self, message_contents: List[str]) -> str:
        """
        Generate a fallback title when AI generation fails.
        
        Args:
            message_contents: List of message content strings
            
        Returns:
            str: Fallback conversation title (max 8 words)
        """
        if not message_contents:
            return "Empty Conversation"
        
        # Use the first user message to generate a title
        first_user_message = None
        for msg_content in message_contents:
            if msg_content.startswith("User: "):
                first_user_message = msg_content[6:].strip()  # Remove "User: " prefix
                break
        
        if not first_user_message:
            return "Support Conversation"
        
        # Clean and format the message for title use
        clean_message = first_user_message.lower()
        
        # Extract important keywords
        important_keywords = [
            "database", "api", "authentication", "login", "password", "email", "server", 
            "error", "connection", "timeout", "billing", "payment", "account", "access"
        ]
        
        found_keywords = []
        for keyword in important_keywords:
            if keyword in clean_message:
                found_keywords.append(keyword.title())
        
        # Remove common prefixes
        prefixes_to_remove = ["hi", "hello", "hey", "can you", "please", "i need", "help me", "help with"]
        for prefix in prefixes_to_remove:
            if clean_message.startswith(prefix):
                clean_message = clean_message[len(prefix):].strip()
        
        # Build title from keywords or clean message
        if found_keywords:
            title = " ".join(found_keywords[:3]) + " Issue"  # Max 4 words including "Issue"
        else:
            # Capitalize first letter and limit length
            if clean_message:
                title = clean_message[0].upper() + clean_message[1:] if len(clean_message) > 1 else clean_message.upper()
                # Limit to 8 words max
                words = title.split()[:8]
                title = " ".join(words)
                
                if len(title) > 50:
                    title = title[:47] + "..."
            else:
                title = "Support Request"
        
        # Ensure title is ≤8 words
        words = title.split()
        if len(words) > 8:
            title = " ".join(words[:8])
            
        return title
    
    async def get_runner_status(self) -> Dict[str, Any]:
        """
        Get the current status of the title generation runner.
        
        Returns:
            Dict[str, Any]: Runner status information
        """
        try:
            config = self.agent.get_configuration()
            
            return {
                "agent_id": str(self.agent.id),
                "agent_type": self.agent.agent_type,
                "agent_name": self.agent.name,
                "initialized": self._initialized,
                "system_agent": self.agent.organization_id is None,
                "configuration": {
                    "timeout_seconds": config.get("timeout_seconds", 15),
                    "communication_style": config.get("communication_style", "professional"),
                    "max_messages_processed": MAX_MESSAGES_FOR_TITLE
                },
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting title generation runner status: {e}")
            return {
                "agent_id": str(self.agent.id) if self.agent else None,
                "error": str(e),
                "initialized": False
            }