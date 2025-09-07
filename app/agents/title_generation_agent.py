#!/usr/bin/env python3
"""
Title Generation Agent

Specialized Pydantic AI agent for generating conversation titles from chat messages.
Focuses on creating concise, descriptive titles that summarize conversation content.
"""

import logging
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
try:
    from pydantic_ai import Agent
except ImportError:
    # Mock for testing
    class Agent:
        def __init__(self, *args, **kwargs):
            self.model = kwargs.get('model', 'mock')
        async def run(self, *args, **kwargs):
            from unittest.mock import MagicMock
            result = MagicMock()
            result.output = MagicMock()
            result.output.title = "Mock Title"
            result.output.confidence = 0.8
            return result

from app.services.ai_config_service import ai_config_service
from app.models.chat import Message

logger = logging.getLogger(__name__)


class TitleGenerationContext(BaseModel):
    """Context for title generation operations"""
    messages: List[str] = Field(description="Conversation messages for analysis")
    current_title: Optional[str] = Field(None, description="Current conversation title")
    message_count: int = Field(description="Total number of messages")
    conversation_length_chars: int = Field(description="Total character count of conversation")


class TitleGenerationResult(BaseModel):
    """Structured output from title generation agent"""
    title: str = Field(description="Generated title", max_length=500)
    confidence: float = Field(description="Confidence score (0-1)", ge=0, le=1)


class TitleGenerationAgent:
    """
    Specialized Pydantic AI agent for conversation title generation.
    Uses fast, cost-effective models optimized for summarization tasks.
    """
    
    def __init__(self):
        """Initialize the title generation agent"""
        self.agent_type = "title_generation_agent"
        self.agent: Optional[Agent] = None
        self._initialized = False
    
    async def ensure_initialized(self):
        """Ensure the agent is initialized"""
        if not self._initialized:
            await self._initialize_agent()
            self._initialized = True
    
    async def _initialize_agent(self):
        """Initialize the Pydantic AI agent for title generation"""
        try:
            # Get agent configuration with fallback to fast/cost-effective models
            agent_config = await ai_config_service.get_agent_config(self.agent_type)
            if not agent_config:
                logger.warning(f"No configuration found for {self.agent_type}, using fast model defaults")
                agent_config = {
                    "model_provider": "openai",
                    "model_name": "gpt-3.5-turbo",  # Faster model for title generation
                    "temperature": 0.3,
                    "max_tokens": 50,  # Short responses for titles
                    "timeout": 15  # Shorter timeout for quick responses
                }
            
            # Use faster model for title generation
            model_provider = agent_config.get("model_provider", "openai")
            model_name = agent_config.get("model_name", "gpt-3.5-turbo")
            
            # Map model configuration names to actual model names
            if model_name == "primary":
                model_name = "gpt-4o-mini"  # Use mini for cost efficiency
            elif model_name == "fast":
                model_name = "gpt-3.5-turbo"
            
            self.agent = Agent(
                model=f"{model_provider}:{model_name}",
                output_type=TitleGenerationResult,
                system_prompt=self._get_system_prompt()
            )
            
            logger.info(f"✅ Title generation agent initialized with {model_provider}:{model_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize title generation agent: {e}")
            # Emergency fallback with simple configuration
            self.agent = Agent(
                model="openai:gpt-3.5-turbo",
                output_type=TitleGenerationResult,
                system_prompt=self._get_system_prompt()
            )
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for title generation"""
        return """
You are an expert at creating concise, descriptive titles for customer support conversations.

Analyze the conversation and generate a clear, specific title that captures the essence of the discussion.

TITLE GENERATION RULES:
1. Maximum 8 words, ideally 4-6 words
2. Use specific, descriptive terms
3. Avoid generic words: "Help", "Support", "Question", "Issue" 
4. Include technical terms when relevant
5. Capture the primary topic/problem
6. Use title case formatting

EXAMPLES OF GOOD TITLES:
- "Password Reset Email Delivery"
- "API Authentication Token Expiry"
- "Database Connection Pool Timeout" 
- "Feature Request: Dark Mode"
- "Billing Invoice Payment Error"

Focus on the main issue or request being discussed and create a professional, searchable title.
"""
    
    async def generate_title(
        self,
        messages: List[Message],
        current_title: Optional[str] = None
    ) -> TitleGenerationResult:
        """
        Generate a conversation title from chat messages.
        
        Args:
            messages: List of Message objects
            current_title: Current conversation title (optional)
            
        Returns:
            TitleGenerationResult: Generated title with confidence score
        """
        try:
            # Prepare message content for analysis first (needed for fallback)
            message_contents = []
            for msg in messages:
                if msg.content and len(msg.content.strip()) > 0:
                    # Include role context for better understanding
                    role_prefix = "User: " if msg.role == "user" else "Assistant: "
                    message_contents.append(f"{role_prefix}{msg.content.strip()}")
            
            if not message_contents:
                logger.warning("No message content available for title generation")
                return TitleGenerationResult(
                    title="Empty Conversation",
                    confidence=0.5
                )
            
            # Ensure agent is initialized
            await self.ensure_initialized()
            if not self.agent:
                logger.error("Title generation agent not available")
                return TitleGenerationResult(
                    title=self._generate_fallback_title(message_contents),
                    confidence=0.0
                )
            
            # Create context for the AI agent
            conversation_text = "\n".join(message_contents)
            
            # Truncate if too long (keep first and last messages for context)
            max_chars = 3000
            if len(conversation_text) > max_chars:
                first_messages = message_contents[:2]  # Keep first 2 messages
                last_messages = message_contents[-2:]  # Keep last 2 messages
                truncated_content = "\n".join(first_messages + ["...[conversation continues]..."] + last_messages)
                # Ensure the truncated content is actually shorter
                if len(truncated_content) > max_chars:
                    # Further truncate by limiting individual message length
                    truncated_first = [msg[:500] + "..." if len(msg) > 500 else msg for msg in first_messages]
                    truncated_last = [msg[:500] + "..." if len(msg) > 500 else msg for msg in last_messages]
                    truncated_content = "\n".join(truncated_first + ["...[conversation continues]..."] + truncated_last)
                conversation_text = truncated_content
            
            # Prepare the prompt
            prompt = f"""
Analyze this customer support conversation and generate a concise, descriptive title.

Current title: "{current_title or 'New Conversation'}"
Message count: {len(messages)}
Conversation length: {len(conversation_text)} characters

CONVERSATION CONTENT:
{conversation_text}

Generate a title that is more specific and descriptive than the current one.
"""
            
            logger.info(f"🎯 Generating title for conversation with {len(messages)} messages")
            logger.debug(f"Message content preview: {conversation_text[:200]}...")
            
            # Run the AI agent
            result = await self.agent.run(prompt)
            
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
    
    async def get_agent_status(self) -> dict:
        """
        Get the current status of the title generation agent.
        
        Returns:
            dict: Agent status information
        """
        try:
            agent_config = await ai_config_service.get_agent_config(self.agent_type)
            
            return {
                "agent_type": self.agent_type,
                "initialized": self.agent is not None,
                "configuration": {
                    "model_provider": agent_config.get("model_provider") if agent_config else "openai",
                    "model_name": agent_config.get("model_name") if agent_config else "gpt-3.5-turbo",
                    "temperature": agent_config.get("temperature") if agent_config else 0.3
                },
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting title generation agent status: {e}")
            return {
                "agent_type": self.agent_type,
                "error": str(e),
                "initialized": False
            }


# Global title generation agent instance
title_generation_agent = TitleGenerationAgent()